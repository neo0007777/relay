"""
OpenHands Adapter for Relay Middleware.
Intercepts action events and prompt injections for OpenHands agent event streams.
"""

from typing import Dict, Any, Optional
from relay.core.logger import get_logger
from relay.adapters.base import BaseAgentAdapter

logger = get_logger("relay.adapters.openhands")


class OpenHandsAdapter(BaseAgentAdapter):
    """Adapter for OpenHands (formerly OpenDevin) AI coding agent."""

    def __init__(self, session_id: str, task_goal: str, token_limit: int = 128000, trace_dir: str = ".relay/traces"):
        super().__init__(
            session_id=session_id,
            task_goal=task_goal,
            agent_type="openhands",
            token_limit=token_limit,
            trace_dir=trace_dir,
        )

    def translate_tool_name(self, raw_tool_name: str) -> str:
        """
        Translates OpenHands event actions (CmdRunAction, FileEditAction, FileReadAction) to Relay standard names.
        """
        name_lower = raw_tool_name.lower().strip()
        if "filereadaction" in name_lower or name_lower in ("read", "read_file"):
            return "read_file"
        elif "fileeditaction" in name_lower or name_lower in ("edit", "write", "edit_file"):
            return "edit_file"
        elif "cmdrunaction" in name_lower or name_lower in ("bash", "exec", "run"):
            return "bash"
        elif "test" in name_lower or "pytest" in name_lower:
            return "pytest"
        return raw_tool_name
