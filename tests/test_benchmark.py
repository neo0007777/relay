"""
Unit and Integration tests for RelayBench Research Framework.
"""

import os
import tempfile
import pytest
from relay.schemas.agent_state import AgentSessionState, ToolExecutionLog
from relay.schemas.checkpoint import KnowledgeCheckpoint, WhyNotItem, RetrievedChunk
from relay.benchmark.dataset_loader import DatasetLoader
from relay.benchmark.metrics import ObjectiveMetricsCalculator
from relay.benchmark.harness import RelayBenchmarkHarness
from relay.benchmark.ablations import ABLATION_MATRIX, build_ablation_runner
from relay.benchmark.trace_replay import TraceReplayExecutor
from relay.benchmark.sample_traces import generate_task_trace


def test_benchmark_dataset_loader():
    tasks = DatasetLoader().load_all_tasks()
    assert len(tasks) >= 30
    task_ids = {t.task_id for t in tasks}
    assert "auth-jwt-refresh" in task_ids
    assert "api-rate-limiter" in task_ids


def test_objective_metrics_calculator():
    calc = ObjectiveMetricsCalculator()

    chunks = [
        RetrievedChunk(chunk_id="c1", file_path="src/auth/manager.py", content="code", score=0.9, retrieval_source="v"),
        RetrievedChunk(chunk_id="c2", file_path="src/unrelated.py", content="code", score=0.5, retrieval_source="v"),
    ]
    target_files = ["src/auth/manager.py", "src/auth/tokens.py"]

    prec, rec, ret_cnt, rel_cnt = calc.calculate_retrieval_precision_recall(chunks, target_files)
    assert prec == 0.5  # 1 matching / 2 retrieved
    assert rec == 0.5   # 1 unique target matched / 2 targets
    assert ret_cnt == 2
    assert rel_cnt == 1

    continuity = calc.calculate_continuity_score(
        completion_rate=1.0,
        precision=prec,
        repeated_work=0,
        dead_end_retries=0,
        regressions=0
    )
    assert 0.0 <= continuity <= 1.0


def test_ablation_matrix_configuration():
    assert "relay_full" in ABLATION_MATRIX
    assert "no_why_not" in ABLATION_MATRIX
    assert "vector_only" in ABLATION_MATRIX

    runner = build_ablation_runner(ABLATION_MATRIX["vector_only"])
    assert runner.reranker.w_graph == 0.0
    assert runner.reranker.w_recency == 0.0
    assert runner.reranker.w_ast == 0.0
    assert runner.reranker.w_vector == 1.0


def test_relay_benchmark_harness():
    with tempfile.TemporaryDirectory() as tmp_out:
        harness = RelayBenchmarkHarness(
            tasks=DatasetLoader().load_all_tasks()[:1],
            output_dir=tmp_out
        )
        result = harness.run_benchmark_suite(iterations=1, include_ablations=False)

        assert result.tasks_evaluated == 1
        assert "relay_full" in result.scenario_summaries
        assert "naive_truncation" in result.scenario_summaries
        assert os.path.exists(os.path.join(tmp_out, "benchmark_results.json"))
        assert os.path.exists(os.path.join(tmp_out, "benchmark_results.csv"))
