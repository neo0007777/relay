"""
Dedicated HandoffOrchestrator for Relay Autonomous Context Handoff Engine.
Coordinates: Session Freeze -> Event Flush -> State Capture -> Checkpoint Creation -> Validation -> Hybrid Retrieval -> Prompt Assembly -> Resume Verification -> Recovery & Telemetry.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.schemas.checkpoint import KnowledgeCheckpoint, RetrievedChunk
from relay.schemas.monitor_state import MonitorState, TriggerEvaluationResult
from relay.checkpointing.monitor import ContextMonitor
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.checkpointing.validator import CheckpointValidator, ValidationResult
from relay.retrieval.hybrid_reranker import HybridReranker
from relay.retrieval.vector_store import QdrantVectorStore
from relay.handoff.hooks import AgentExecutionHook
from relay.handoff.prompt_builder import PromptBuilder
from relay.handoff.verifier import ResumeVerifier, ResumeVerificationReport
from relay.handoff.recovery import RecoveryManager
from relay.core.telemetry import HandoffTelemetry

logger = get_logger("relay.handoff.orchestrator")


class AutonomousHandoffResult(Dict[str, Any]):
    """Result dictionary returned by HandoffOrchestrator."""
    pass


class HandoffOrchestrator:
    """
    Dedicated Orchestrator executing the complete, deterministic, fault-tolerant handoff pipeline.
    """

    def __init__(
        self,
        monitor: Optional[ContextMonitor] = None,
        compressor: Optional[KnowledgeCompressor] = None,
        manager: Optional[CheckpointManager] = None,
        validator: Optional[CheckpointValidator] = None,
        reranker: Optional[HybridReranker] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        verifier: Optional[ResumeVerifier] = None,
        recovery: Optional[RecoveryManager] = None,
    ):
        self.monitor = monitor or ContextMonitor()
        self.compressor = compressor or KnowledgeCompressor()
        self.manager = manager or CheckpointManager()
        self.validator = validator or CheckpointValidator()
        self.reranker = reranker or HybridReranker()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.verifier = verifier or ResumeVerifier()
        self.recovery = recovery or RecoveryManager()

    def execute_autonomous_handoff(
        self,
        session_state: AgentSessionState,
        hook: Optional[AgentExecutionHook] = None,
        workspace_dir: Optional[str] = None,
        manual_trigger: bool = False,
    ) -> AutonomousHandoffResult:
        """
        Executes the 9-stage autonomous handoff pipeline with full validation, recovery, and telemetry logging.
        """
        telemetry = HandoffTelemetry(session_id=session_state.session_id)
        telemetry.start_stage("Session Started")
        telemetry.record_stage("Session Started", {"agent_type": session_state.agent_type, "tokens": session_state.tokens_consumed})

        # Stage 1: Evaluate Multi-Signal Trigger & Transition State
        telemetry.start_stage("Trigger Evaluation")
        eval_result = self.monitor.evaluate_triggers(session_state, manual_trigger=manual_trigger)
        telemetry.record_stage("Trigger Evaluation", {
            "should_trigger": eval_result.should_trigger,
            "reason": eval_result.primary_reason.value,
            "details": eval_result.details
        })

        if not eval_result.should_trigger and not manual_trigger:
            return AutonomousHandoffResult({
                "status": "normal_execution",
                "should_handoff": False,
                "monitor_state": self.monitor.state.value,
                "session_state": session_state,
                "telemetry_timeline": telemetry.format_timeline(),
            })

        # Stage 2: Freeze Session & Set State
        telemetry.start_stage("Freeze Session")
        self.monitor.transition_to(MonitorState.HANDOFF_IN_PROGRESS, eval_result)
        telemetry.record_stage("Freeze Session", {"state": MonitorState.HANDOFF_IN_PROGRESS.value})

        # Stage 3: Flush Pending Events & Capture Working State
        telemetry.start_stage("State Capture")
        why_not_store = hook.why_not_store if hook else session_state.metadata.get("why_not_store", [])
        decision_log = hook.decision_log if hook else session_state.metadata.get("decision_log", [])
        file_diff_map = hook.file_diff_map if hook else session_state.metadata.get("file_diff_map", {})
        telemetry.record_stage("State Capture", {
            "why_not_count": len(why_not_store),
            "decisions_count": len(decision_log),
            "file_diffs_count": len(file_diff_map)
        })

        # Stage 4: Create Knowledge Checkpoint
        telemetry.start_stage("Checkpoint Creation")
        try:
            checkpoint = self.compressor.compress_session(
                session_state=session_state,
                why_not_store=why_not_store,
                decision_log=decision_log,
                file_diff_map=file_diff_map,
                workspace_dir=workspace_dir
            )
        except Exception as e:
            logger.error(f"Error compressing session into checkpoint: {e}")
            checkpoint = self.recovery.recover_corrupted_checkpoint(None, session_state)
        telemetry.record_stage("Checkpoint Created", {"checkpoint_id": checkpoint.checkpoint_id})

        # Stage 5: Validate Checkpoint & Checksum Integrity
        telemetry.start_stage("Checkpoint Validation")
        val_result = self.validator.validate(checkpoint, workspace_dir=workspace_dir)
        if not val_result.is_valid:
            logger.warning(f"Checkpoint validation failed: {val_result.errors}. Invoking recovery.")
            checkpoint = self.recovery.recover_corrupted_checkpoint(None, session_state)
            val_result = self.validator.validate(checkpoint, workspace_dir=workspace_dir)

        chk_path = self.manager.save_checkpoint(checkpoint)
        telemetry.record_stage("Checkpoint Validated", {
            "checksum": val_result.checksum[:8],
            "is_valid": val_result.is_valid,
            "path": chk_path
        })

        # Stage 6: Repository Indexing & Hybrid Retrieval
        telemetry.start_stage("Hybrid Retrieval")
        retrieved_chunks: List[RetrievedChunk] = []
        try:
            retrieved_chunks = self.reranker.retrieve_hybrid_context(
                query=f"{session_state.task_goal} {' '.join(session_state.active_files)}",
                checkpoint=checkpoint,
                top_k=5
            )
            telemetry.record_stage("Hybrid Retrieval", {"retrieved_count": len(retrieved_chunks)})
        except Exception as e:
            logger.error(f"Hybrid retrieval failed: {e}. Invoking recovery fallback.")
            retrieved_chunks = self.recovery.recover_retrieval_failure(checkpoint, workspace_dir)
            telemetry.record_stage("Hybrid Retrieval (Recovered)", {"retrieved_count": len(retrieved_chunks)})

        checkpoint.retrieved_context = retrieved_chunks

        # Stage 7: Assemble Resume System Prompt
        telemetry.start_stage("Resume Prompt Assembly")
        try:
            resumed_prompt = self.prompt_builder.build(
                checkpoint=checkpoint,
                retrieved_context=[f"// File: {c.file_path}\n{c.content}" for c in retrieved_chunks],
                agent_type=session_state.agent_type
            )
        except Exception as e:
            logger.error(f"Prompt assembly failed: {e}. Invoking emergency partial resume recovery.")
            resumed_prompt = self.recovery.recover_partial_resume(session_state, e)
        telemetry.record_stage("Resume Prompt Assembly", {"prompt_length": len(resumed_prompt)})

        # Stage 8: Verify Resume Integrity & Export Report
        telemetry.start_stage("Resume Verification")
        verification_report = self.verifier.verify_resume(
            original_session=session_state,
            checkpoint=checkpoint,
            resumed_prompt=resumed_prompt,
            output_report_path="artifacts/validation_report.json"
        )
        telemetry.record_stage("Resume Verification", {
            "verification_score": verification_report.verification_score,
            "fully_preserved": verification_report.is_fully_preserved
        })

        # Stage 9: Set State to RESUMED & Return Result
        self.monitor.transition_to(MonitorState.RESUMED)
        telemetry.start_stage("Session Continued")
        telemetry.record_stage("Session Continued", {"status": "resumed_ready"})

        timeline_output = telemetry.format_timeline()
        logger.info(f"\n{timeline_output}")

        return AutonomousHandoffResult({
            "status": "resumed_ready",
            "should_handoff": True,
            "monitor_state": self.monitor.state.value,
            "checkpoint": checkpoint,
            "checkpoint_id": checkpoint.checkpoint_id,
            "checkpoint_path": chk_path,
            "resumed_prompt": resumed_prompt,
            "retrieved_context": retrieved_chunks,
            "validation_result": val_result,
            "verification_report": verification_report,
            "telemetry_timeline": timeline_output,
        })
