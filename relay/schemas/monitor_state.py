"""
Data schemas for ContextMonitor lifecycle states, trigger policies, and multi-signal trigger reasons.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MonitorState(str, Enum):
    """Lifecycle states of the ContextMonitor during an agent session."""

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CHECKPOINT_REQUIRED = "CHECKPOINT_REQUIRED"
    HANDOFF_IN_PROGRESS = "HANDOFF_IN_PROGRESS"
    RESUMED = "RESUMED"


class TriggerReason(str, Enum):
    """Signal category that triggered the checkpoint or warning state."""

    CONTEXT_USAGE = "CONTEXT_USAGE"
    RAPID_FILE_EDITS = "RAPID_FILE_EDITS"
    TOOL_DENSITY = "TOOL_DENSITY"
    REASONING_CHAIN = "REASONING_CHAIN"
    REPEATED_FAILURES = "REPEATED_FAILURES"
    USER_MANUAL = "USER_MANUAL"
    NONE = "NONE"


class TriggerPolicy(BaseModel):
    """Configurable multi-signal trigger rules for autonomous context handoff."""

    warning_threshold: float = Field(default=0.70, description="Warning threshold ratio (e.g. 0.70 for 70%)")
    checkpoint_threshold: float = Field(default=0.85, description="Checkpoint required threshold ratio (e.g. 0.85 for 85%)")
    max_rapid_edits: int = Field(default=8, description="Max file edit actions within rapid edit window")
    rapid_edit_window_steps: int = Field(default=10, description="Step window for detecting rapid file edits")
    max_consecutive_failures: int = Field(default=3, description="Max consecutive tool failure exit codes")
    max_reasoning_steps: int = Field(default=25, description="Max consecutive steps without file modifications")
    
    # Provider-specific token budgets
    provider_limits: Dict[str, int] = Field(
        default_factory=lambda: {
            "claude": 128000,
            "claude_code": 128000,
            "codex": 128000,
            "codex_cli": 128000,
            "openhands": 128000,
            "generic": 128000,
        },
        description="Provider-agnostic token context limits"
    )


class TriggerEvaluationResult(BaseModel):
    """Result container for multi-signal trigger evaluation."""

    should_trigger: bool = Field(description="True if checkpoint is required")
    warning_active: bool = Field(default=False, description="True if warning threshold reached")
    state: MonitorState = Field(description="Current ContextMonitor lifecycle state")
    primary_reason: TriggerReason = Field(default=TriggerReason.NONE)
    details: str = Field(description="Detailed explanation of trigger evaluation")
    metrics: Dict[str, Any] = Field(default_factory=dict)
