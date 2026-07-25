"""
Unit and Integration tests for RelayBench Dataset Loader and BenchmarkRunner (Sprint 2).
"""

import os
import tempfile
import pytest
from relay.benchmark.dataset_loader import DatasetLoader
from relay.benchmark.runner import BenchmarkRunner


def test_dataset_loader_discovers_tasks():
    loader = DatasetLoader()
    tasks = loader.load_all_tasks()

    assert len(tasks) >= 30
    categories = {os.path.basename(os.path.dirname(tdir)) for tdir in loader.discover_task_directories()}
    assert "authentication" in categories
    assert "backend" in categories
    assert "database" in categories
    assert "frontend" in categories
    assert "debugging" in categories


def test_benchmark_runner_execution():
    with tempfile.TemporaryDirectory() as tmp_out:
        runner = BenchmarkRunner(output_dir=tmp_out)
        result = runner.run_full_evaluation(
            repetitions=1,
            include_ablations=False,
            limit_tasks=2
        )

        assert result.tasks_evaluated == 2
        assert "relay_full" in result.scenario_summaries
        assert "naive_truncation" in result.scenario_summaries
        assert os.path.exists(os.path.join(tmp_out, "benchmark_results.json"))
        assert os.path.exists(os.path.join(tmp_out, "benchmark_results.csv"))
