"""
Unit tests for Relay Knowledge Checkpointing Engine (Phase 1).
"""

import os
import shutil
import tempfile
import pytest
from datetime import datetime

from relay.schemas.agent_state import AgentSessionState, ToolExecutionLog
from relay.schemas.checkpoint import WhyNotItem, DecisionItem, KnowledgeCheckpoint
from relay.checkpointing.monitor import ContextMonitor
from relay.checkpointing.git_ast_analyzer import GitASTAnalyzer
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager


@pytest.fixture
def temp_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath, ignore_errors=True)


def test_context_monitor_threshold():
    monitor = ContextMonitor(threshold_ratio=0.80)

    # Below threshold (50k / 100k = 50%)
    state_below = AgentSessionState(
        session_id="sess-1",
        task_goal="Refactor auth",
        tokens_consumed=50000,
        token_limit=100000,
    )
    should_trigger, reason = monitor.should_trigger_checkpoint(state_below)
    assert not should_trigger

    # Above threshold (85k / 100k = 85%)
    state_above = AgentSessionState(
        session_id="sess-1",
        task_goal="Refactor auth",
        tokens_consumed=85000,
        token_limit=100000,
    )
    should_trigger, reason = monitor.should_trigger_checkpoint(state_above)
    assert should_trigger
    assert "85.00%" in reason


def test_git_ast_analyzer_diff():
    analyzer = GitASTAnalyzer()

    old_code = """
def authenticate_user(username, password):
    return True
"""
    new_code = """
def authenticate_user(username, password, mfa_token=None):
    return True

async def verify_jwt(token):
    return True

class SessionManager:
    pass
"""
    changes = analyzer.diff_ast_symbols("auth.py", old_code, new_code)
    symbol_names = {c.symbol_name: c.change_type for c in changes}

    assert "authenticate_user" in symbol_names
    assert symbol_names["authenticate_user"] == "modified"

    assert "verify_jwt" in symbol_names
    assert symbol_names["verify_jwt"] == "added"

    assert "SessionManager" in symbol_names
    assert symbol_names["SessionManager"] == "added"


def test_git_ast_analyzer_dependency_graph(temp_dir):
    # Create sample Python files
    file_a = os.path.join(temp_dir, "module_a.py")
    file_b = os.path.join(temp_dir, "module_b.py")

    with open(file_a, "w") as f:
        f.write("import os\nimport sys\n")

    with open(file_b, "w") as f:
        f.write("from module_a import func\nimport math\n")

    analyzer = GitASTAnalyzer(repo_root=temp_dir)
    graph = analyzer.build_file_dependency_graph(["module_a.py", "module_b.py"])

    assert "module_a.py" in graph
    assert "os" in graph["module_a.py"]
    assert "sys" in graph["module_a.py"]

    assert "module_b.py" in graph
    assert "module_a" in graph["module_b.py"]
    assert "math" in graph["module_b.py"]


def test_knowledge_compressor():
    compressor = KnowledgeCompressor()

    session = AgentSessionState(
        session_id="sess-test",
        task_goal="Fix race condition in TokenService",
        tokens_consumed=105000,
        token_limit=128000,
        tool_logs=[
            ToolExecutionLog(tool_name="edit_file", input_params={"path": "TokenService.py"}, output_summary="Updated refresh logic", exit_code=0),
            ToolExecutionLog(tool_name="pytest", input_params={"cmd": "pytest tests/"}, output_summary="1 failed, 4 passed", exit_code=1, is_failure=True),
        ],
        active_files=["TokenService.py"]
    )

    why_not = [
        WhyNotItem(
            approach_id="wn-1",
            attempted_idea="Mutex lock around refresh queue",
            rationale_rejected="Caused deadlock in async execution",
            error_traceback="DeadlockError: lock timeout after 5s",
            files_involved=["TokenService.py"]
        )
    ]

    decisions = [
        DecisionItem(
            decision_id="dec-1",
            choice_made="Atomic redis key swap",
            alternatives_considered=["Mutex lock"],
            justification="Avoids thread deadlock in async runtime",
            files_affected=["TokenService.py"]
        )
    ]

    diff_map = {
        "TokenService.py": (
            "class TokenService:\n    def refresh(self): pass",
            "class TokenService:\n    async def refresh(self, redis_cli): pass"
        )
    }

    checkpoint = compressor.compress_session(
        session_state=session,
        why_not_store=why_not,
        decision_log=decisions,
        file_diff_map=diff_map
    )

    assert checkpoint.session_id == "sess-test"
    assert checkpoint.task_goal == "Fix race condition in TokenService"
    assert len(checkpoint.why_not_store) == 1
    assert checkpoint.why_not_store[0].attempted_idea == "Mutex lock around refresh queue"
    assert len(checkpoint.decision_log) == 1
    assert len(checkpoint.ast_changes) > 0
    assert len(checkpoint.important_tool_outputs) == 1


def test_checkpoint_manager_persistence(temp_dir):
    manager = CheckpointManager(checkpoint_dir=temp_dir)

    checkpoint = KnowledgeCheckpoint(
        checkpoint_id="chk-1001",
        session_id="sess-persistence",
        task_goal="Add MFA support",
        narrative_progress="Implemented OTP generator",
        why_not_store=[
            WhyNotItem(
                approach_id="wn-101",
                attempted_idea="SMS OTP provider",
                rationale_rejected="SMS latency too high",
            )
        ]
    )

    # Save
    path = manager.save_checkpoint(checkpoint)
    assert os.path.exists(path)

    # Load
    loaded = manager.load_checkpoint("chk-1001")
    assert loaded is not None
    assert loaded.checkpoint_id == "chk-1001"
    assert loaded.session_id == "sess-persistence"
    assert len(loaded.why_not_store) == 1
    assert loaded.why_not_store[0].attempted_idea == "SMS OTP provider"

    # List
    listed = manager.list_checkpoints(session_id="sess-persistence")
    assert len(listed) == 1
    assert listed[0].checkpoint_id == "chk-1001"


def test_corrupt_checkpoint_file(temp_dir):
    manager = CheckpointManager(checkpoint_dir=temp_dir)
    corrupt_filepath = os.path.join(temp_dir, "chk-corrupt.json")

    with open(corrupt_filepath, "w") as f:
        f.write("{ invalid json string ... ")

    loaded = manager.load_checkpoint("chk-corrupt")
    assert loaded is None


def test_checkpoint_deletion(temp_dir):
    manager = CheckpointManager(checkpoint_dir=temp_dir)
    chk = KnowledgeCheckpoint(
        checkpoint_id="chk-to-delete",
        session_id="sess-del",
        task_goal="Delete test",
        narrative_progress="Testing deletion"
    )

    manager.save_checkpoint(chk)
    assert manager.load_checkpoint("chk-to-delete") is not None

    deleted = manager.delete_checkpoint("chk-to-delete")
    assert deleted is True
    assert manager.load_checkpoint("chk-to-delete") is None

    # Deleting non-existent returns False
    assert manager.delete_checkpoint("chk-non-existent") is False
