"""
Unit tests for Relay Agent Adapters and TraceRecorder (Sprint 3).
"""

import os
import tempfile
import pytest
from relay.adapters.claude_code import ClaudeCodeAdapter
from relay.adapters.codex import CodexCLIAdapter
from relay.adapters.openhands import OpenHandsAdapter
from relay.adapters.trace_recorder import TraceRecorder


def test_claude_code_adapter():
    with tempfile.TemporaryDirectory() as tmp_trace:
        adapter = ClaudeCodeAdapter(
            session_id="sess-claude-test",
            task_goal="Refactor auth manager",
            trace_dir=tmp_trace
        )

        assert adapter.translate_tool_name("View") == "read_file"
        assert adapter.translate_tool_name("Edit") == "edit_file"
        assert adapter.translate_tool_name("Bash") == "bash"

        should_trigger = adapter.intercept_tool_call(
            raw_tool_name="Edit",
            input_params={"path": "src/auth/manager.py", "content": "code"},
            output="Updated file"
        )
        assert not should_trigger
        assert len(adapter.recorder.entries) == 1
        assert adapter.recorder.entries[0].tool_name == "edit_file"


def test_codex_adapter():
    with tempfile.TemporaryDirectory() as tmp_trace:
        adapter = CodexCLIAdapter(
            session_id="sess-codex-test",
            task_goal="Implement PKCE verifier",
            trace_dir=tmp_trace
        )

        assert adapter.translate_tool_name("read") == "read_file"
        assert adapter.translate_tool_name("patch") == "edit_file"
        assert adapter.translate_tool_name("exec") == "bash"

        adapter.record_why_not(
            attempted_idea="Plain text PKCE challenge",
            rationale_rejected="Security violation"
        )
        assert len(adapter.hook.why_not_store) == 1
        assert len(adapter.recorder.entries) == 1


def test_openhands_adapter():
    with tempfile.TemporaryDirectory() as tmp_trace:
        adapter = OpenHandsAdapter(
            session_id="sess-openhands-test",
            task_goal="Fix queue leak",
            trace_dir=tmp_trace
        )

        assert adapter.translate_tool_name("FileReadAction") == "read_file"
        assert adapter.translate_tool_name("FileEditAction") == "edit_file"
        assert adapter.translate_tool_name("CmdRunAction") == "bash"


def test_trace_recorder_export():
    with tempfile.TemporaryDirectory() as tmp_trace:
        recorder = TraceRecorder(session_id="sess-rec-test", trace_dir=tmp_trace)
        recorder.record_step(
            step_index=1,
            tool_name="read_file",
            input_params={"path": "main.py"},
            output_summary="ok"
        )

        export_path = os.path.join(tmp_trace, "exported_trace.jsonl")
        exported = recorder.export_full_trace(export_path)
        assert os.path.exists(exported)
