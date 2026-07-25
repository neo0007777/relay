"""
Codex CLI Adapter for Relay Middleware.
Intercepts tool executions, token boundaries, and prompt injections for OpenAI Codex CLI sessions.
"""

from typing import Dict, Any, Optional
from relay.core.logger import get_logger
from relay.adapters.base import BaseAgentAdapter

logger = get_logger("relay.adapters.codex")


class CodexCLIAdapter(BaseAgentAdapter):
    """Adapter for OpenAI Codex CLI AI coding agent."""

    def __init__(self, session_id: str, task_goal: str, token_limit: int = 128000, trace_dir: str = ".relay/traces"):
        super().__init__(
            session_id=session_id,
            task_goal=task_goal,
            agent_type="codex_cli",
            token_limit=token_limit,
            trace_dir=trace_dir,
        )

    def translate_tool_name(self, raw_tool_name: str) -> str:
        """
        Translates Codex CLI tool names (read, patch, exec) to Relay standard names.
        """
        name_lower = raw_tool_name.lower().strip()
        if name_lower in ("read", "cat", "read_file"):
            return "read_file"
        elif name_lower in ("patch", "write", "edit", "edit_file"):
            return "edit_file"
        elif name_lower in ("exec", "bash", "run", "cmd"):
            return "bash"
        elif "test" in name_lower or "pytest" in name_lower:
            return "pytest"
        return raw_tool_name
