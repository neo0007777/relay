"""
Pydantic Schemas for Live Agent Session and Execution State.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ToolExecutionLog(BaseModel):
    """Log record of a tool execution (file edit, shell command, test run)."""

    timestamp: datetime = Field(default_factory=datetime.now)
    tool_name: str = Field(description="Name of the tool executed (e.g. bash, read_file, edit_file)")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="Parameters passed to the tool")
    output_summary: str = Field(description="Summarized text output or stdout/stderr")
    exit_code: int = Field(default=0, description="Command exit code (0 for success, non-zero for error)")
    is_failure: bool = Field(default=False, description="Whether tool execution resulted in failure/error")


class AgentSessionState(BaseModel):
    """Active runtime state of an AI coding agent session."""

    session_id: str = Field(description="Unique agent session ID")
    agent_type: str = Field(default="openhands", description="Type of agent (e.g. openhands, claude_code, codex)")
    task_goal: str = Field(description="Original user task prompt/goal")
    current_step: int = Field(default=0, description="Step counter in current session")
    tokens_consumed: int = Field(default=0, description="Accumulated token count in current context window")
    token_limit: int = Field(default=128000, description="Max token capacity of context window")
    tool_logs: List[ToolExecutionLog] = Field(default_factory=list, description="Sequence of tool execution events")
    active_files: List[str] = Field(default_factory=list, description="Paths of files touched or read during session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom agent metadata")

    @property
    def context_usage_ratio(self) -> float:
        """Returns context token usage as a ratio [0.0, 1.0]."""
        if self.token_limit <= 0:
            return 0.0
        return min(1.0, self.tokens_consumed / self.token_limit)
