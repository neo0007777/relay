"""
Agent Execution Hooks and Context Interceptors for Relay.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState, ToolExecutionLog
from relay.schemas.checkpoint import WhyNotItem, DecisionItem
from relay.checkpointing.monitor import ContextMonitor

logger = get_logger("relay.handoff.hooks")


class AgentExecutionHook:
    """Intercepts agent steps, records tool execution events, and updates token usage."""

    def __init__(self, session_state: AgentSessionState, monitor: Optional[ContextMonitor] = None):
        self.session_state = session_state
        self.monitor = monitor or ContextMonitor()
        self.why_not_store: List[WhyNotItem] = []
        self.decision_log: List[DecisionItem] = []
        self.file_diff_map: Dict[str, tuple[str, str]] = {}

    def record_tool_step(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output: str,
        exit_code: int = 0,
        is_failure: bool = False,
    ) -> bool:
        """
        Records a tool execution step, updates token count, and checks if context threshold is crossed.

        Returns:
            should_checkpoint (bool)
        """
        self.session_state.current_step += 1

        # Estimate tokens consumed by input/output
        step_text = f"{tool_name} {str(input_params)} {output}"
        tokens_added = self.monitor.estimate_tokens(step_text)
        self.session_state.tokens_consumed += tokens_added

        # Track active files if path parameter present
        for key in ("path", "file_path", "target_file"):
            if key in input_params and isinstance(input_params[key], str):
                rel_path = input_params[key]
                if rel_path not in self.session_state.active_files:
                    self.session_state.active_files.append(rel_path)

        # Record log entry
        log_entry = ToolExecutionLog(
            timestamp=datetime.now(),
            tool_name=tool_name,
            input_params=input_params,
            output_summary=output[:500],  # Truncate long outputs
            exit_code=exit_code,
            is_failure=is_failure,
        )
        self.session_state.tool_logs.append(log_entry)

        logger.debug(
            f"Step {self.session_state.current_step}: [{tool_name}] "
            f"+{tokens_added} tokens (Total: {self.session_state.tokens_consumed}/{self.session_state.token_limit})"
        )

        should_trigger, _ = self.monitor.should_trigger_checkpoint(self.session_state)
        return should_trigger

    def record_why_not(
        self,
        attempted_idea: str,
        rationale_rejected: str,
        error_traceback: Optional[str] = None,
        files_involved: Optional[List[str]] = None,
    ) -> None:
        """Explicitly records a dead end or rejected approach."""
        item = WhyNotItem(
            approach_id=f"wn-{len(self.why_not_store) + 1}",
            attempted_idea=attempted_idea,
            rationale_rejected=rationale_rejected,
            error_traceback=error_traceback,
            files_involved=files_involved or [],
            timestamp=datetime.now(),
        )
        self.why_not_store.append(item)
        logger.info(f"Recorded Why-Not Dead End #{item.approach_id}: '{attempted_idea}'")

    def record_decision(
        self,
        choice_made: str,
        justification: str,
        alternatives: Optional[List[str]] = None,
        files_affected: Optional[List[str]] = None,
    ) -> None:
        """Explicitly records a architectural/code design decision."""
        item = DecisionItem(
            decision_id=f"dec-{len(self.decision_log) + 1}",
            choice_made=choice_made,
            alternatives_considered=alternatives or [],
            justification=justification,
            files_affected=files_affected or [],
        )
        self.decision_log.append(item)
        logger.info(f"Recorded Decision #{item.decision_id}: '{choice_made}'")

    def update_file_diff(self, file_path: str, old_content: str, new_content: str) -> None:
        """Updates modified file diff map."""
        self.file_diff_map[file_path] = (old_content, new_content)
