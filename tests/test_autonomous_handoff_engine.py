"""
Comprehensive Test Suite for Sprint 5 Autonomous Context Handoff Engine.
Tests: ContextMonitor states & multi-signal triggers, CheckpointValidator integrity,
ResumeVerifier preservation reports, RecoveryManager fallbacks, HandoffTelemetry, and HandoffOrchestrator pipeline.
"""

import os
import json
import tempfile
import pytest
from datetime import datetime

from relay.schemas.agent_state import AgentSessionState, ToolExecutionLog
from relay.schemas.checkpoint import KnowledgeCheckpoint, DecisionItem, WhyNotItem, FileDiffSummary, RetrievedChunk
from relay.schemas.monitor_state import MonitorState, TriggerReason, TriggerPolicy
from relay.checkpointing.monitor import ContextMonitor
from relay.checkpointing.validator import CheckpointValidator
from relay.checkpointing.manager import CheckpointManager
from relay.handoff.verifier import ResumeVerifier
from relay.handoff.recovery import RecoveryManager
from relay.core.telemetry import HandoffTelemetry
from relay.handoff.hooks import AgentExecutionHook
from relay.handoff.orchestrator import HandoffOrchestrator


@pytest.fixture
def sample_session():
    return AgentSessionState(
        session_id="sess-test-sprint5",
        agent_type="claude_code",
        task_goal="Refactor OAuth Token Renewal Flow",
        tokens_consumed=110000,
        token_limit=128000,
        active_files=["src/auth/tokens.py", "src/auth/jwt.py"]
    )


@pytest.fixture
def sample_checkpoint():
    return KnowledgeCheckpoint(
        checkpoint_id="chk-sprint5-001",
        session_id="sess-test-sprint5",
        task_goal="Refactor OAuth Token Renewal Flow",
        narrative_progress="Extracted TokenService and updated verification signatures.",
        decision_log=[
            DecisionItem(
                decision_id="dec-1",
                choice_made="Use RS256 asymmetric signatures",
                justification="Allows public key verification across microservices"
            )
        ],
        why_not_store=[
            WhyNotItem(
                approach_id="wn-1",
                attempted_idea="Shared secret HMAC key",
                rationale_rejected="Exposes secret key in distributed containers",
                error_traceback="SecurityViolationError: Secret exposed"
            )
        ],
        file_diffs=[
            FileDiffSummary(
                file_path="src/auth/tokens.py",
                status="modified",
                additions=12,
                deletions=3,
                patch_summary="def verify_jwt(): pass"
            )
        ],
        tokens_at_checkpoint=110000,
        context_limit=128000
    )


def test_context_monitor_lifecycle_states(sample_session):
    monitor = ContextMonitor()
    assert monitor.state == MonitorState.NORMAL

    # Normal usage (50%)
    sample_session.tokens_consumed = 64000
    res_normal = monitor.evaluate_triggers(sample_session)
    assert res_normal.state == MonitorState.NORMAL
    assert not res_normal.should_trigger

    # Warning usage (75%)
    sample_session.tokens_consumed = 96000
    res_warn = monitor.evaluate_triggers(sample_session)
    assert res_warn.state == MonitorState.WARNING
    assert res_warn.warning_active
    assert not res_warn.should_trigger

    # Checkpoint required usage (86%)
    sample_session.tokens_consumed = 110100
    res_chk = monitor.evaluate_triggers(sample_session)
    assert res_chk.state == MonitorState.CHECKPOINT_REQUIRED
    assert res_chk.should_trigger
    assert res_chk.primary_reason == TriggerReason.CONTEXT_USAGE


def test_multi_signal_triggers(sample_session):
    monitor = ContextMonitor()
    sample_session.tokens_consumed = 50000  # Within ratio limits

    # Trigger via Rapid File Edits
    for i in range(10):
        sample_session.tool_logs.append(
            ToolExecutionLog(
                timestamp=datetime.now(),
                tool_name="edit_file",
                input_params={"path": "src/auth/tokens.py"},
                output_summary="File updated"
            )
        )
    res_edits = monitor.evaluate_triggers(sample_session)
    assert res_edits.should_trigger
    assert res_edits.primary_reason == TriggerReason.RAPID_FILE_EDITS

    # Trigger via Consecutive Failures
    sample_session.tool_logs.clear()
    for i in range(4):
        sample_session.tool_logs.append(
            ToolExecutionLog(
                timestamp=datetime.now(),
                tool_name="run_tests",
                input_params={},
                output_summary="Error",
                exit_code=1,
                is_failure=True
            )
        )
    res_fail = monitor.evaluate_triggers(sample_session)
    assert res_fail.should_trigger
    assert res_fail.primary_reason == TriggerReason.REPEATED_FAILURES


def test_checkpoint_validator_and_checksum(sample_checkpoint, tmp_path):
    validator = CheckpointValidator()
    
    # Checksum computation
    checksum = validator.compute_checksum(sample_checkpoint)
    assert isinstance(checksum, str)
    assert len(checksum) == 64  # SHA-256 length

    # Valid checkpoint validation
    res = validator.validate(sample_checkpoint, workspace_dir=str(tmp_path))
    assert res.is_valid
    assert res.checksum == checksum
    assert len(res.errors) == 0

    # Invalid checkpoint validation
    sample_checkpoint.task_goal = ""
    res_invalid = validator.validate(sample_checkpoint)
    assert not res_invalid.is_valid
    assert "Missing required field: 'task_goal'" in res_invalid.errors


def test_resume_verifier_report(sample_session, sample_checkpoint, tmp_path):
    verifier = ResumeVerifier()
    prompt = (
        "=================== RELAY CONTEXT HANDOFF ===================\n"
        "PRIMARY TASK GOAL: Refactor OAuth Token Renewal Flow\n"
        "CHECKPOINT ID: chk-sprint5-001\n"
        "Active File: src/auth/tokens.py\n"
        "Decision: Use RS256 asymmetric signatures\n"
        "❌ DEAD END: Shared secret HMAC key\n"
    )
    report_file = tmp_path / "artifacts" / "validation_report.json"
    
    report = verifier.verify_resume(
        original_session=sample_session,
        checkpoint=sample_checkpoint,
        resumed_prompt=prompt,
        output_report_path=str(report_file)
    )

    assert report.is_fully_preserved
    assert report.verification_score == 1.0
    assert report_file.exists()
    
    saved_json = json.loads(report_file.read_text())
    assert saved_json["session_id"] == "sess-test-sprint5"
    assert saved_json["is_fully_preserved"] is True


def test_recovery_manager_fallbacks(sample_session, sample_checkpoint, tmp_path):
    recovery = RecoveryManager()

    # Create dummy file in workspace to exist
    existing_file = tmp_path / "src" / "auth" / "tokens.py"
    existing_file.parent.mkdir(parents=True, exist_ok=True)
    existing_file.write_text("def verify(): pass")

    # Corrupted checkpoint recovery
    recovered_chk = recovery.recover_corrupted_checkpoint(None, sample_session)
    assert recovered_chk.session_id == sample_session.session_id
    assert "sess-test-sprint5" in recovered_chk.narrative_progress

    # Missing files recovery
    sample_checkpoint.file_diffs.append(
        FileDiffSummary(file_path="non_existent_file.py", status="deleted", patch_summary="")
    )
    cleaned_chk = recovery.recover_missing_files(sample_checkpoint, workspace_dir=str(tmp_path))
    assert any(d.file_path == "src/auth/tokens.py" for d in cleaned_chk.file_diffs)
    assert all(d.file_path != "non_existent_file.py" for d in cleaned_chk.file_diffs)

    # Retrieval failure recovery
    fallback_chunks = recovery.recover_retrieval_failure(cleaned_chk, workspace_dir=str(tmp_path))
    assert len(fallback_chunks) > 0
    assert fallback_chunks[0].retrieval_source.startswith("recovery")

    # Partial resume recovery
    recovered_prompt = recovery.recover_partial_resume(sample_session, RuntimeError("Qdrant connection lost"))
    assert "EMERGENCY RECOVERY" in recovered_prompt
    assert "Refactor OAuth Token Renewal Flow" in recovered_prompt


def test_telemetry_timeline():
    telemetry = HandoffTelemetry(session_id="sess-telemetry-test")
    telemetry.start_stage("Session Started")
    telemetry.record_stage("Session Started", {"tokens": 100})
    
    telemetry.start_stage("Checkpoint Created")
    telemetry.record_stage("Checkpoint Created", {"checkpoint_id": "chk-1"})

    formatted = telemetry.format_timeline()
    assert "RELAY TELEMETRY TIMELINE" in formatted
    assert "Session Started" in formatted
    assert "Checkpoint Created" in formatted


def test_handoff_orchestrator_autonomous_pipeline(sample_session, tmp_path):
    orchestrator = HandoffOrchestrator(
        manager=CheckpointManager(checkpoint_dir=str(tmp_path))
    )
    hook = AgentExecutionHook(session_state=sample_session)
    hook.record_decision("Use RS256 signature", "Asymmetric verification")
    hook.record_why_not("HMAC secret key", "Security risk")

    sample_session.tokens_consumed = 110000  # Triggers >85% threshold

    result = orchestrator.execute_autonomous_handoff(
        session_state=sample_session,
        hook=hook,
        workspace_dir=str(tmp_path)
    )

    assert result["should_handoff"] is True
    assert result["status"] == "resumed_ready"
    assert result["monitor_state"] == "RESUMED"
    assert result["validation_result"].is_valid
    assert result["verification_report"].is_fully_preserved
    assert "RELAY CONTEXT HANDOFF" in result["resumed_prompt"]
    assert "RELAY TELEMETRY TIMELINE" in result["telemetry_timeline"]
