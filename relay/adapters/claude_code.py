"""
Claude Code Adapter for Relay Middleware.
Intercepts tool executions, token boundaries, and prompt injections for Claude Code CLI sessions.
"""

from typing import Dict, Any, Optional
from relay.core.logger import get_logger
from relay.adapters.base import BaseAgentAdapter

logger = get_logger("relay.adapters.claude_code")


class ClaudeCodeAdapter(BaseAgentAdapter):
    """Adapter for Claude Code AI coding agent."""

    def __init__(self, session_id: str, task_goal: str, token_limit: int = 128000, trace_dir: str = ".relay/traces"):
        super().__init__(
            session_id=session_id,
            task_goal=task_goal,
            agent_type="claude_code",
            token_limit=token_limit,
            trace_dir=trace_dir,
        )

    def translate_tool_name(self, raw_tool_name: str) -> str:
        """
        Translates Claude Code tool names (View, Edit, Replace, Bash) to Relay standard names.
        """
        name_lower = raw_tool_name.lower().strip()
        if name_lower in ("view", "read", "read_file"):
            return "read_file"
        elif name_lower in ("edit", "replace", "write", "write_file"):
            return "edit_file"
        elif name_lower in ("bash", "command", "exec"):
            return "bash"
        elif "test" in name_lower or "pytest" in name_lower:
            return "pytest"
        return raw_tool_name
