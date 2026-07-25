"""
LangGraph State Machine Orchestrator for Relay Agent Handoff.
Manages boundary checking, checkpoint serialization, hybrid context retrieval, and fresh agent resumption.
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from relay.core.config import settings
from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.schemas.checkpoint import KnowledgeCheckpoint, RetrievedChunk
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.retrieval.hybrid_reranker import HybridReranker
from relay.handoff.hooks import AgentExecutionHook

from relay.handoff.prompt_builder import PromptBuilder

logger = get_logger("relay.handoff.runner")


class AgentHandoffState(TypedDict):
    """LangGraph State representation for Relay agent orchestrator."""

    session_state: AgentSessionState
    checkpoint: Optional[KnowledgeCheckpoint]
    retrieved_context: List[RetrievedChunk]
    should_handoff: bool
    resumed_prompt: str
    status: str


class LangGraphHandoffRunner:
    """Orchestrates agent handoff workflows using a compiled LangGraph state machine."""

    def __init__(
        self,
        compressor: Optional[KnowledgeCompressor] = None,
        manager: Optional[CheckpointManager] = None,
        reranker: Optional[HybridReranker] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ):
        self.compressor = compressor or KnowledgeCompressor()
        self.manager = manager or CheckpointManager()
        self.reranker = reranker or HybridReranker()
        self.prompt_builder = prompt_builder or PromptBuilder()

        # Build and compile state graph
        self.graph = self._build_state_graph()

    def _build_state_graph(self) -> StateGraph:
        """Constructs the LangGraph state graph for Relay handoff transitions."""
        builder = StateGraph(AgentHandoffState)

        # Register nodes
        builder.add_node("evaluate_boundary", self._node_evaluate_boundary)
        builder.add_node("create_checkpoint", self._node_create_checkpoint)
        builder.add_node("retrieve_context", self._node_retrieve_context)
        builder.add_node("resume_agent", self._node_resume_agent)

        # Entry point
        builder.set_entry_point("evaluate_boundary")

        # Conditional edges
        builder.add_conditional_edges(
            "evaluate_boundary",
            self._route_boundary,
            {
                "checkpoint": "create_checkpoint",
                "retrieve": "retrieve_context",
                "continue": END,
            }
        )

        builder.add_edge("create_checkpoint", "retrieve_context")
        builder.add_edge("retrieve_context", "resume_agent")
        builder.add_edge("resume_agent", END)

        return builder.compile()

    def _node_evaluate_boundary(self, state: AgentHandoffState) -> Dict[str, Any]:
        """Evaluates whether agent session has reached context limit boundary or has existing checkpoint."""
        session = state["session_state"]
        has_checkpoint = state.get("checkpoint") is not None
        should_trigger = has_checkpoint or session.context_usage_ratio >= settings.CHECKPOINT_THRESHOLD_RATIO

        logger.info(
            f"LangGraph [evaluate_boundary]: Usage={session.context_usage_ratio:.2%}, HasChk={has_checkpoint} "
            f"-> Trigger={should_trigger}"
        )

        return {
            "should_handoff": should_trigger,
            "status": "boundary_evaluated"
        }

    def _route_boundary(self, state: AgentHandoffState) -> str:
        """Routes next graph step based on boundary evaluation."""
        if state.get("checkpoint") is not None:
            return "retrieve"
        return "checkpoint" if state.get("should_handoff", False) else "continue"

    def _node_create_checkpoint(self, state: AgentHandoffState) -> Dict[str, Any]:
        """Node: Synthesizes and persists a KnowledgeCheckpoint."""
        session = state["session_state"]

        # Pull hook data attached to session metadata if present
        why_not = session.metadata.get("why_not_store", [])
        decisions = session.metadata.get("decision_log", [])
        diff_map = session.metadata.get("file_diff_map", {})

        checkpoint = self.compressor.compress_session(
            session_state=session,
            why_not_store=why_not,
            decision_log=decisions,
            file_diff_map=diff_map
        )

        self.manager.save_checkpoint(checkpoint)

        logger.info(f"LangGraph [create_checkpoint]: Checkpoint '{checkpoint.checkpoint_id}' saved.")
        return {
            "checkpoint": checkpoint,
            "status": "checkpoint_created"
        }

    def _node_retrieve_context(self, state: AgentHandoffState) -> Dict[str, Any]:
        """Node: Retrieves hybrid context (vector + AST graph + recency) for handoff."""
        checkpoint = state.get("checkpoint")
        if not checkpoint:
            return {"retrieved_context": [], "status": "retrieval_skipped"}

        query = f"{checkpoint.task_goal} {' '.join(checkpoint.pending_todos)}"
        retrieved = self.reranker.retrieve_hybrid_context(
            query=query,
            checkpoint=checkpoint,
            top_k=5
        )

        checkpoint.retrieved_context = retrieved

        logger.info(f"LangGraph [retrieve_context]: Retrieved {len(retrieved)} context chunks.")
        return {
            "retrieved_context": retrieved,
            "status": "context_retrieved"
        }

    def _node_resume_agent(self, state: AgentHandoffState) -> Dict[str, Any]:
        """Node: Constructs structured system prompt for the resumed fresh agent instance."""
        checkpoint = state.get("checkpoint")
        if not checkpoint:
            return {"resumed_prompt": "", "status": "resume_failed"}

        full_prompt = self.prompt_builder.build_resume_prompt(checkpoint)

        logger.info("LangGraph [resume_agent]: Resumed agent prompt successfully synthesized.")
        return {
            "resumed_prompt": full_prompt,
            "status": "resumed_ready"
        }

    def execute_handoff(
        self,
        session_state: AgentSessionState,
        hook: Optional[AgentExecutionHook] = None
    ) -> AgentHandoffState:
        """
        Executes the LangGraph handoff state machine for a session.
        """
        if hook:
            session_state.metadata["why_not_store"] = hook.why_not_store
            session_state.metadata["decision_log"] = hook.decision_log
            session_state.metadata["file_diff_map"] = hook.file_diff_map

        initial_state: AgentHandoffState = {
            "session_state": session_state,
            "checkpoint": None,
            "retrieved_context": [],
            "should_handoff": False,
            "resumed_prompt": "",
            "status": "initialized"
        }

        final_state = self.graph.invoke(initial_state)
        return final_state

    def resume_from_checkpoint(self, checkpoint: KnowledgeCheckpoint) -> AgentHandoffState:
        """
        Resumes an agent handoff workflow directly from an existing KnowledgeCheckpoint object.
        """
        session_state = AgentSessionState(
            session_id=checkpoint.session_id,
            task_goal=checkpoint.task_goal,
            tokens_consumed=checkpoint.tokens_at_checkpoint,
            token_limit=checkpoint.context_limit,
        )

        initial_state: AgentHandoffState = {
            "session_state": session_state,
            "checkpoint": checkpoint,
            "retrieved_context": [],
            "should_handoff": True,
            "resumed_prompt": "",
            "status": "initialized"
        }

        final_state = self.graph.invoke(initial_state)
        return final_state
