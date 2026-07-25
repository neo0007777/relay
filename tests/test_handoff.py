"""
Unit and Integration tests for Relay LangGraph Agent Handoff (Phase 3).
"""

import tempfile
import shutil
import pytest
from relay.schemas.agent_state import AgentSessionState
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.retrieval.hybrid_reranker import HybridReranker
from relay.handoff.hooks import AgentExecutionHook
from relay.handoff.runner import LangGraphHandoffRunner


@pytest.fixture
def temp_dir():
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath, ignore_errors=True)


def test_agent_execution_hook():
    session = AgentSessionState(
        session_id="sess-hook",
        task_goal="Fix CORS error in API",
        tokens_consumed=1000,
        token_limit=10000,
    )
    hook = AgentExecutionHook(session_state=session)

    # Record tool steps
    should_trigger = hook.record_tool_step(
        tool_name="edit_file",
        input_params={"path": "src/cors.py"},
        output="Added Access-Control-Allow-Origin header"
    )
    assert not should_trigger
    assert session.current_step == 1
    assert "src/cors.py" in session.active_files

    # Record dead end
    hook.record_why_not(
        attempted_idea="Allow all origins '*'",
        rationale_rejected="Security violation in production settings",
        error_traceback="SecurityAuditError: Wildcard origin forbidden",
        files_involved=["src/cors.py"]
    )
    assert len(hook.why_not_store) == 1
    assert hook.why_not_store[0].attempted_idea == "Allow all origins '*'"

    # Record decision
    hook.record_decision(
        choice_made="Whitelist specified domains from config",
        justification="Complies with security policy"
    )
    assert len(hook.decision_log) == 1


def test_langgraph_handoff_runner(temp_dir):
    manager = CheckpointManager(checkpoint_dir=temp_dir)
    compressor = KnowledgeCompressor()
    reranker = HybridReranker()

    runner = LangGraphHandoffRunner(
        compressor=compressor,
        manager=manager,
        reranker=reranker
    )

    session = AgentSessionState(
        session_id="sess-handoff",
        task_goal="Refactor DB Connector to connection pool",
        tokens_consumed=90000,  # 90k / 100k = 90% -> Trigger handoff
        token_limit=100000,
        active_files=["src/db.py"]
    )

    hook = AgentExecutionHook(session_state=session)
    hook.record_why_not(
        attempted_idea="Single global connection object",
        rationale_rejected="Not thread safe for concurrent requests",
        error_traceback="ThreadConcurrencyError"
    )
    hook.record_decision(
        choice_made="SQLAlchemy AsyncEngine pool",
        justification="Handles async concurrency smoothly"
    )

    final_state = runner.execute_handoff(session_state=session, hook=hook)

    assert final_state["should_handoff"] is True
    assert final_state["checkpoint"] is not None
    assert final_state["checkpoint"].session_id == "sess-handoff"
    assert len(final_state["checkpoint"].why_not_store) == 1

    prompt = final_state["resumed_prompt"]
    assert "RELAY CONTEXT HANDOFF" in prompt
    assert "Single global connection object" in prompt
    assert "WHY-NOT STORE" in prompt
    assert "SQLAlchemy AsyncEngine pool" in prompt


def test_prompt_builder():
    from relay.handoff.prompt_builder import PromptBuilder
    from relay.schemas.checkpoint import KnowledgeCheckpoint, WhyNotItem

    builder = PromptBuilder()
    chk = KnowledgeCheckpoint(
        checkpoint_id="chk-builder-test",
        session_id="sess-pb",
        task_goal="Fix OAuth flow",
        narrative_progress="In progress",
        why_not_store=[
            WhyNotItem(
                approach_id="wn-pb-1",
                attempted_idea="Implicit grant flow",
                rationale_rejected="Deprecated by OAuth 2.1"
            )
        ]
    )

    prompt = builder.build_resume_prompt(chk)
    assert "PRIMARY TASK GOAL: Fix OAuth flow" in prompt
    assert "Implicit grant flow" in prompt
    assert "Deprecated by OAuth 2.1" in prompt
