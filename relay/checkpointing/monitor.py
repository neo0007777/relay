"""
Real-time Token and Context Window Monitor for Relay.
Provides lifecycle state management (NORMAL -> WARNING -> CHECKPOINT_REQUIRED -> HANDOFF_IN_PROGRESS -> RESUMED)
and multi-signal intelligent trigger evaluation.
"""

from typing import Tuple, List, Dict, Any, Callable, Optional
from datetime import datetime

from relay.core.config import settings
from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.schemas.monitor_state import (
    MonitorState,
    TriggerReason,
    TriggerPolicy,
    TriggerEvaluationResult,
)

logger = get_logger("relay.checkpointing.monitor")


class ContextMonitor:
    """
    Monitors agent session context usage, evaluates multi-signal intelligent triggers,
    and manages state transitions across the handoff lifecycle.
    """

    def __init__(
        self,
        threshold_ratio: float = settings.CHECKPOINT_THRESHOLD_RATIO,
        policy: Optional[TriggerPolicy] = None,
    ):
        self.threshold_ratio = threshold_ratio
        self.policy = policy or TriggerPolicy(checkpoint_threshold=threshold_ratio)
        self.state = MonitorState.NORMAL
        self.listeners: List[Callable[[MonitorState, TriggerEvaluationResult], None]] = []

    def register_listener(self, listener: Callable[[MonitorState, TriggerEvaluationResult], None]) -> None:
        """Registers a callback listener for ContextMonitor state transition events."""
        self.listeners.append(listener)

    def transition_to(self, new_state: MonitorState, result: Optional[TriggerEvaluationResult] = None) -> None:
        """Transitions monitor to a new state and notifies registered listeners."""
        old_state = self.state
        self.state = new_state
        logger.info(f"ContextMonitor transition: {old_state.value} -> {new_state.value}")

        if result:
            for listener in self.listeners:
                try:
                    listener(new_state, result)
                except Exception as e:
                    logger.error(f"Listener error during ContextMonitor transition: {e}")

    def resolve_provider_limit(self, agent_type: str) -> int:
        """Resolves maximum token budget for specific provider agent."""
        norm_type = agent_type.lower()
        return self.policy.provider_limits.get(norm_type, 128000)

    def evaluate_triggers(
        self,
        session_state: AgentSessionState,
        manual_trigger: bool = False
    ) -> TriggerEvaluationResult:
        """
        Evaluates multi-signal intelligent triggers across:
        1. Context ratio (threshold vs warning)
        2. Rapid file edit velocity
        3. Consecutive tool failures
        4. Long reasoning chains without edit
        5. Manual user trigger
        """
        # Ensure token limit is resolved if generic
        provider_limit = self.resolve_provider_limit(session_state.agent_type)
        if session_state.token_limit <= 0:
            session_state.token_limit = provider_limit

        usage_ratio = session_state.context_usage_ratio
        tokens = session_state.tokens_consumed
        limit = session_state.token_limit

        # Signal 1: Manual Trigger
        if manual_trigger:
            res = TriggerEvaluationResult(
                should_trigger=True,
                warning_active=True,
                state=MonitorState.CHECKPOINT_REQUIRED,
                primary_reason=TriggerReason.USER_MANUAL,
                details="Manual user checkpoint requested",
                metrics={"tokens": tokens, "usage_ratio": usage_ratio}
            )
            self.transition_to(MonitorState.CHECKPOINT_REQUIRED, res)
            return res

        # Signal 2: Context Usage Ratio
        if usage_ratio >= self.policy.checkpoint_threshold:
            details = (
                f"Context usage ratio {usage_ratio:.2%} ({tokens}/{limit} tokens) "
                f"exceeds threshold of {self.policy.checkpoint_threshold:.2%}"
            )
            res = TriggerEvaluationResult(
                should_trigger=True,
                warning_active=True,
                state=MonitorState.CHECKPOINT_REQUIRED,
                primary_reason=TriggerReason.CONTEXT_USAGE,
                details=details,
                metrics={"tokens": tokens, "usage_ratio": usage_ratio}
            )
            self.transition_to(MonitorState.CHECKPOINT_REQUIRED, res)
            return res

        # Signal 3: Rapid File Modifications
        recent_logs = session_state.tool_logs[-self.policy.rapid_edit_window_steps:] if session_state.tool_logs else []
        edit_count = sum(1 for log in recent_logs if "edit" in log.tool_name.lower() or "write" in log.tool_name.lower())
        if edit_count >= self.policy.max_rapid_edits:
            details = f"Rapid edit velocity detected: {edit_count} edits in last {len(recent_logs)} steps"
            res = TriggerEvaluationResult(
                should_trigger=True,
                warning_active=True,
                state=MonitorState.CHECKPOINT_REQUIRED,
                primary_reason=TriggerReason.RAPID_FILE_EDITS,
                details=details,
                metrics={"edit_count": edit_count, "window": len(recent_logs)}
            )
            self.transition_to(MonitorState.CHECKPOINT_REQUIRED, res)
            return res

        # Signal 4: Repeated Consecutive Failures
        consecutive_failures = 0
        for log in reversed(session_state.tool_logs):
            if log.is_failure or log.exit_code != 0:
                consecutive_failures += 1
            else:
                break
        if consecutive_failures >= self.policy.max_consecutive_failures:
            details = f"Repeated tool failures detected: {consecutive_failures} consecutive failures"
            res = TriggerEvaluationResult(
                should_trigger=True,
                warning_active=True,
                state=MonitorState.CHECKPOINT_REQUIRED,
                primary_reason=TriggerReason.REPEATED_FAILURES,
                details=details,
                metrics={"consecutive_failures": consecutive_failures}
            )
            self.transition_to(MonitorState.CHECKPOINT_REQUIRED, res)
            return res

        # Signal 5: Warning Threshold Ratio
        if usage_ratio >= self.policy.warning_threshold:
            details = f"Context usage ratio {usage_ratio:.2%} reached warning threshold ({self.policy.warning_threshold:.2%})"
            res = TriggerEvaluationResult(
                should_trigger=False,
                warning_active=True,
                state=MonitorState.WARNING,
                primary_reason=TriggerReason.CONTEXT_USAGE,
                details=details,
                metrics={"tokens": tokens, "usage_ratio": usage_ratio}
            )
            if self.state != MonitorState.WARNING:
                self.transition_to(MonitorState.WARNING, res)
            return res

        # Normal State
        res = TriggerEvaluationResult(
            should_trigger=False,
            warning_active=False,
            state=MonitorState.NORMAL,
            primary_reason=TriggerReason.NONE,
            details=f"Context usage ratio {usage_ratio:.2%} within limits ({tokens}/{limit})",
            metrics={"tokens": tokens, "usage_ratio": usage_ratio}
        )
        if self.state != MonitorState.NORMAL:
            self.transition_to(MonitorState.NORMAL, res)
        return res

    def should_trigger_checkpoint(self, session_state: AgentSessionState) -> Tuple[bool, str]:
        """
        Evaluates whether context consumption or multi-signal triggers have reached checkpoint boundary.
        Provides backward compatibility with original API.
        """
        eval_result = self.evaluate_triggers(session_state)
        return eval_result.should_trigger, eval_result.details

    def estimate_tokens(self, text: str) -> int:
        """Estimates token count for arbitrary text using standard ~4 chars/token heuristic."""
        if not text:
            return 0
        return max(1, len(text) // 4)
