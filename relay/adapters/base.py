"""
Abstract Base Agent Adapter for Relay Middleware.
Provides unified tool interception, token monitoring, dead-end logging, handoff orchestration, and trace recording.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.schemas.checkpoint import KnowledgeCheckpoint
from relay.checkpointing.monitor import ContextMonitor
from relay.handoff.hooks import AgentExecutionHook
from relay.handoff.runner import LangGraphHandoffRunner, AgentHandoffState
from relay.adapters.trace_recorder import TraceRecorder

logger = get_logger("relay.adapters.base")


class BaseAgentAdapter(ABC):
    """
    Abstract Base Class for agent adapters (Claude Code, Codex CLI, OpenHands).
    Enforces a common interface for monitoring, tool interception, handoff, and trace logging.
    """

    def __init__(
        self,
        session_id: str,
        task_goal: str,
        agent_type: str = "generic",
        token_limit: int = 128000,
        runner: Optional[LangGraphHandoffRunner] = None,
        trace_dir: str = ".relay/traces",
    ):
        self.session_state = AgentSessionState(
            session_id=session_id,
            agent_type=agent_type,
            task_goal=task_goal,
            tokens_consumed=0,
            token_limit=token_limit,
        )
        self.monitor = ContextMonitor()
        self.hook = AgentExecutionHook(session_state=self.session_state, monitor=self.monitor)
        self.runner = runner or LangGraphHandoffRunner()
        self.recorder = TraceRecorder(session_id=session_id, trace_dir=trace_dir)
        self.checkpoint: Optional[KnowledgeCheckpoint] = None

    @abstractmethod
    def translate_tool_name(self, raw_tool_name: str) -> str:
        """Translates agent-specific raw tool name to Relay standard tool name."""
        pass

    def intercept_tool_call(
        self,
        raw_tool_name: str,
        input_params: Dict[str, Any],
        output: str,
        exit_code: int = 0,
        is_failure: bool = False,
    ) -> bool:
        """
        Intercepts a tool execution step, records state, appends to JSONL trace, and checks handoff boundary.

        Returns:
            should_trigger_checkpoint (bool)
        """
        std_tool = self.translate_tool_name(raw_tool_name)
        should_trigger = self.hook.record_tool_step(
            tool_name=std_tool,
            input_params=input_params,
            output=output,
            exit_code=exit_code,
            is_failure=is_failure,
        )

        # Record to trace recorder
        self.recorder.record_step(
            step_index=self.session_state.current_step,
            tool_name=std_tool,
            input_params=input_params,
            output_summary=output,
            exit_code=exit_code,
            is_failure=is_failure,
            tokens_consumed=self.session_state.tokens_consumed,
            checkpoint_id=self.checkpoint.checkpoint_id if self.checkpoint else None
        )

        if should_trigger:
            logger.info(f"Adapter trigger checkpoint reached for agent '{self.session_state.agent_type}'.")

        return should_trigger

    def record_why_not(
        self,
        attempted_idea: str,
        rationale_rejected: str,
        error_traceback: Optional[str] = None,
        files_involved: Optional[List[str]] = None,
    ) -> None:
        """Explicitly records a dead end or rejected approach."""
        self.hook.record_why_not(attempted_idea, rationale_rejected, error_traceback, files_involved)
        params = {"attempted_idea": attempted_idea, "rationale_rejected": rationale_rejected, "error_traceback": error_traceback, "files_involved": files_involved or []}
        self.recorder.record_step(self.session_state.current_step, "why_not", params, f"Why-Not Dead End: {attempted_idea}", tokens_consumed=self.session_state.tokens_consumed)

    def record_decision(
        self,
        choice_made: str,
        justification: str,
        alternatives: Optional[List[str]] = None,
        files_affected: Optional[List[str]] = None,
    ) -> None:
        """Explicitly records an architectural or code design decision."""
        self.hook.record_decision(choice_made, justification, alternatives, files_affected)
        params = {"choice_made": choice_made, "justification": justification, "alternatives": alternatives or [], "files_affected": files_affected or []}
        self.recorder.record_step(self.session_state.current_step, "decision", params, f"Decision: {choice_made}", tokens_consumed=self.session_state.tokens_consumed)

    def trigger_handoff(self) -> AgentHandoffState:
        """
        Executes LangGraph agent handoff workflow and returns fresh agent system prompt.
        """
        final_state = self.runner.execute_handoff(session_state=self.session_state, hook=self.hook)
        self.checkpoint = final_state.get("checkpoint")
        logger.info(f"Handoff executed for adapter. Checkpoint ID: '{self.checkpoint.checkpoint_id if self.checkpoint else None}'")
        return final_state

    def export_trace(self, filepath: str) -> str:
        """Exports full agent session trace log to specified JSONL file."""
        return self.recorder.export_full_trace(filepath)
