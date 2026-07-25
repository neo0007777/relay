"""
Comprehensive Test Suite for Sprint 6 Evidence & Evaluation Engine.
Tests: RetrievalExplainer, CheckpointAnalyzer, RegressionDetector, EvidenceValidator, and EvidenceGenerator pipeline.
"""

import os
import json
import pytest
from datetime import datetime

from relay.schemas.benchmark import BenchmarkMetric, BenchmarkRunResult
from relay.schemas.checkpoint import KnowledgeCheckpoint, RetrievedChunk, DecisionItem, WhyNotItem, FileDiffSummary
from relay.benchmark.retrieval_explainer import RetrievalExplainer
from relay.benchmark.checkpoint_analyzer import CheckpointAnalyzer
from relay.benchmark.regression_detector import RegressionDetector
from relay.benchmark.evidence_validator import EvidenceValidator, EvidenceValidationError
from relay.benchmark.evidence_generator import EvidenceGenerator


@pytest.fixture
def sample_result():
    metric = BenchmarkMetric(
        task_id="api-rate-limiter",
        scenario="relay_full",
        iteration=1,
        task_completed=True,
        tests_passed=1,
        tests_total=1,
        completion_rate=1.0,
        continuity_score=0.85,
        retrieval_precision=0.90,
        retrieval_recall=0.88,
        dead_end_retries=0.0,
        total_tokens_consumed=10500,
        handoff_latency_seconds=1.2,
        total_duration_seconds=3.5,
    )
    return BenchmarkRunResult(
        run_id="run-s6-test",
        timestamp=datetime.now(),
        tasks_evaluated=1,
        iterations_per_task=1,
        metrics_per_task=[metric],
        relay_summary={"avg_completion_rate": 1.0, "avg_continuity_score": 0.85, "avg_dead_end_retries": 0.0, "avg_handoff_latency_seconds": 1.2},
        naive_truncation_summary={"avg_completion_rate": 0.4, "avg_continuity_score": 0.3, "avg_dead_end_retries": 5.0, "avg_handoff_latency_seconds": 0.0},
        no_limit_baseline_summary={"avg_completion_rate": 1.0, "avg_continuity_score": 1.0, "avg_dead_end_retries": 0.0, "avg_handoff_latency_seconds": 0.0},
        scenario_summaries={
            "relay_full": {"completion_rate": {"mean": 1.0}, "dead_end_retries": {"mean": 0.0}}
        }
    )


@pytest.fixture
def sample_checkpoint():
    return KnowledgeCheckpoint(
        checkpoint_id="chk-s6-test",
        session_id="sess-s6-test",
        task_goal="Implement Rate Limiting",
        narrative_progress="Added TokenBucketLimiter class.",
        decision_log=[DecisionItem(decision_id="d1", choice_made="TokenBucket", justification="Low memory overhead")],
        why_not_store=[WhyNotItem(approach_id="w1", attempted_idea="Fixed window", rationale_rejected="Burst traffic flaw")],
        file_diffs=[FileDiffSummary(file_path="src/api/limiter.py", status="modified", additions=20, deletions=5, patch_summary="Added limiter")],
        retrieved_context=[
            RetrievedChunk(chunk_id="c1", file_path="src/api/limiter.py", content="class TokenBucket: pass", score=0.92, retrieval_source="hybrid_blended"),
            RetrievedChunk(chunk_id="c2", file_path="src/config.py", content="rate_limit = 100", score=0.70, retrieval_source="hybrid_blended")
        ]
    )


def test_retrieval_explainer(sample_checkpoint, tmp_path):
    explainer = RetrievalExplainer()
    explanations = explainer.explain_chunks(sample_checkpoint.retrieved_context, sample_checkpoint)
    
    assert len(explanations) == 2
    assert explanations[0].file_path == "src/api/limiter.py"
    assert "dense vector" in explanations[0].selection_rationale or "active file" in explanations[0].selection_rationale

    paths = explainer.export_retrieval_reports(explanations, str(tmp_path))
    assert os.path.exists(paths["chunks_json"])
    assert os.path.exists(paths["scores_json"])
    assert os.path.exists(paths["report_md"])

    md_content = open(paths["report_md"]).read()
    assert "Relay Hybrid Retrieval Explanation Report" in md_content
    assert "src/api/limiter.py" in md_content


def test_checkpoint_analyzer(sample_checkpoint, tmp_path):
    analyzer = CheckpointAnalyzer()
    analysis = analyzer.analyze_checkpoint(sample_checkpoint)

    assert analysis.checkpoint_id == "chk-s6-test"
    assert analysis.size_bytes > 0
    assert analysis.compression_ratio > 1.0
    assert analysis.decision_count == 1
    assert analysis.why_not_count == 1

    paths = analyzer.export_checkpoint_reports([analysis], str(tmp_path))
    assert os.path.exists(paths["metadata_json"])
    assert os.path.exists(paths["sizes_json"])
    assert os.path.exists(paths["report_md"])

    md_content = open(paths["report_md"]).read()
    assert "Relay Knowledge Checkpoint Analysis Report" in md_content
    assert "chk-s6-test" in md_content


def test_regression_detector(sample_result, tmp_path):
    detector = RegressionDetector()
    
    # 1. First run (no history)
    report_no_hist = detector.detect_regressions(sample_result, history_file_path=None)
    assert not report_no_hist.has_critical_regression

    # 2. Setup historical run file with higher completion rate
    history_file = tmp_path / "dashboards" / "benchmark_history.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    past_run = json.loads(sample_result.model_dump_json())
    past_run["scenario_summaries"]["relay_full"]["completion_rate"]["mean"] = 1.0
    past_run["scenario_summaries"]["relay_full"]["dead_end_retries"]["mean"] = 0.0
    history_file.write_text(json.dumps([past_run]))

    # Modify current result to simulate regression
    sample_result.scenario_summaries["relay_full"]["completion_rate"]["mean"] = 0.5
    sample_result.scenario_summaries["relay_full"]["dead_end_retries"]["mean"] = 2.0

    report_reg = detector.detect_regressions(sample_result, history_file_path=str(history_file))
    assert len(report_reg.regressions) > 0

    reg_md_path = detector.export_regression_report(report_reg, str(tmp_path))
    assert os.path.exists(reg_md_path)
    md_content = open(reg_md_path).read()
    assert "Regression Analysis Report" in md_content


def test_evidence_validator_enforcement(tmp_path):
    validator = EvidenceValidator()

    # Empty dir should fail validation
    with pytest.raises(EvidenceValidationError):
        validator.validate_package(str(tmp_path), raise_on_error=True)

    res = validator.validate_package(str(tmp_path), raise_on_error=False)
    assert not res.is_valid
    assert len(res.missing_files) == 15


def test_evidence_generator_pipeline(sample_result, sample_checkpoint, tmp_path):
    generator = EvidenceGenerator()
    out = generator.generate_evidence_package(
        result=sample_result,
        output_dir=str(tmp_path),
        sample_checkpoint=sample_checkpoint
    )

    assert out["run_id"] == sample_result.run_id

    # Verify all 15 required evidence package files exist and pass validator
    validator = EvidenceValidator()
    val_res = validator.validate_package(str(tmp_path), raise_on_error=True)
    assert val_res.is_valid
    assert val_res.checked_files_count == 15
