"""Relay Agent Adapters Package."""
from relay.adapters.base import BaseAgentAdapter
from relay.adapters.claude_code import ClaudeCodeAdapter
from relay.adapters.codex import CodexCLIAdapter
from relay.adapters.openhands import OpenHandsAdapter
from relay.adapters.trace_recorder import TraceRecorder, TraceRecordEntry

__all__ = [
    "BaseAgentAdapter",
    "ClaudeCodeAdapter",
    "CodexCLIAdapter",
    "OpenHandsAdapter",
    "TraceRecorder",
    "TraceRecordEntry",
]
