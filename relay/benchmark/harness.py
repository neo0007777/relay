"""
RelayBenchmarkHarness for RelayBench Evaluation Framework.
Executes multi-iteration, sandbox-isolated comparative evaluations and ablation studies.
Computes sample mean, median, standard deviation, and 95% confidence intervals.
Exports benchmark_results.json and benchmark_results.csv.
"""

import os
import csv
import json
import time
import math
import uuid
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime

from relay.core.config import settings
from relay.core.logger import get_logger
from relay.schemas.benchmark import BenchmarkMetric, BenchmarkRunResult
from relay.benchmark.tasks import BenchmarkTask
from relay.benchmark.dataset_loader import DatasetLoader
from relay.benchmark.trace_replay import TraceReplayExecutor
from relay.benchmark.sample_traces import generate_task_trace
from relay.benchmark.ablations import ABLATION_MATRIX, build_ablation_runner
from relay.handoff.runner import LangGraphHandoffRunner

logger = get_logger("relay.benchmark.harness")


class RelayBenchmarkHarness:
    """Automated research harness for running statistically rigorous RelayBench evaluations."""

    def __init__(
        self,
        tasks: Optional[List[BenchmarkTask]] = None,
        output_dir: str = settings.BENCHMARK_RESULTS_DIR,
    ):
        self.tasks = tasks or DatasetLoader().load_all_tasks()
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def run_benchmark_suite(
        self,
        iterations: int = 3,
        include_ablations: bool = True
    ) -> BenchmarkRunResult:
        """
        Runs full benchmark suite across all tasks, scenarios, and ablations for N iterations.

        Returns:
            Aggregated BenchmarkRunResult with complete statistical distributions.
        """
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        logger.info(
            f"Starting RelayBench Evaluation Run '{run_id}' "
            f"({len(self.tasks)} tasks, {iterations} iterations/task, ablations={include_ablations})..."
        )

        # Scenarios to evaluate
        scenarios = ["relay_full", "naive_truncation", "no_limit_baseline"]
        if include_ablations:
            scenarios.extend(["no_why_not", "no_ast", "no_graph", "vector_only"])

        all_metrics: List[BenchmarkMetric] = []

        for task in self.tasks:
            logger.info(f"Evaluating Task '{task.task_id}' [{task.title}]...")

            for scenario in scenarios:
                # Build configured runner if ablation
                if scenario in ABLATION_MATRIX:
                    runner = build_ablation_runner(ABLATION_MATRIX[scenario])
                else:
                    runner = LangGraphHandoffRunner()

                executor = TraceReplayExecutor(runner=runner)
                trace = generate_task_trace(task.task_id, scenario, task=task)

                for it in range(1, iterations + 1):
                    with tempfile.TemporaryDirectory() as sandbox_dir:
                        metric = executor.execute_trace_replay(
                            scenario=scenario,
                            task=task,
                            trace=trace,
                            sandbox_dir=sandbox_dir,
                            iteration=it
                        )
                        all_metrics.append(metric)

        # Compute statistical summaries per scenario
        scenario_summaries: Dict[str, Dict[str, Any]] = {}
        ablation_matrix_summary: Dict[str, Dict[str, Any]] = {}

        for scenario in scenarios:
            scen_metrics = [m for m in all_metrics if m.scenario == scenario]
            stats = self._compute_statistical_summary(scen_metrics)
            scenario_summaries[scenario] = stats

            if scenario in ABLATION_MATRIX:
                ablation_matrix_summary[scenario] = stats

        # Build result container
        result = BenchmarkRunResult(
            run_id=run_id,
            timestamp=datetime.now(),
            tasks_evaluated=len(self.tasks),
            iterations_per_task=iterations,
            scenario_summaries=scenario_summaries,
            ablation_matrix=ablation_matrix_summary,
            relay_summary=self._flatten_mean_summary(scenario_summaries.get("relay_full", {})),
            naive_truncation_summary=self._flatten_mean_summary(scenario_summaries.get("naive_truncation", {})),
            no_limit_baseline_summary=self._flatten_mean_summary(scenario_summaries.get("no_limit_baseline", {})),
            metrics_per_task=all_metrics,
        )

        # Export results to JSON and CSV
        self.export_results(result)

        logger.info(f"RelayBench Run '{run_id}' completed successfully. Results exported to {self.output_dir}.")
        return result

    def _compute_statistical_summary(self, metrics: List[BenchmarkMetric]) -> Dict[str, Any]:
        """
        Computes mean, median, standard deviation, and 95% confidence intervals for a metric set.
        """
        if not metrics:
            return {}

        fields = [
            "completion_rate",
            "continuity_score",
            "retrieval_precision",
            "retrieval_recall",
            "repeated_work_count",
            "dead_end_retries",
            "code_regression_count",
            "total_tokens_consumed",
            "handoff_latency_seconds",
            "total_duration_seconds",
        ]

        summary: Dict[str, Any] = {"count": len(metrics)}

        for field in fields:
            values = [float(getattr(m, field)) for m in metrics]
            summary[field] = self._calculate_stats(values)

        return summary

    @staticmethod
    def _calculate_stats(values: List[float]) -> Dict[str, float]:
        """Calculates mean, median, std_dev, and 95% confidence interval half-width."""
        n = len(values)
        if n == 0:
            return {"mean": 0.0, "median": 0.0, "std_dev": 0.0, "ci95": 0.0}

        mean_val = sum(values) / n

        sorted_vals = sorted(values)
        if n % 2 == 1:
            median_val = sorted_vals[n // 2]
        else:
            median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

        if n > 1:
            variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
            std_dev = math.sqrt(variance)
            ci95 = 1.96 * (std_dev / math.sqrt(n))
        else:
            std_dev = 0.0
            ci95 = 0.0

        return {
            "mean": round(mean_val, 4),
            "median": round(median_val, 4),
            "std_dev": round(std_dev, 4),
            "ci95": round(ci95, 4),
        }

    @staticmethod
    def _flatten_mean_summary(stats_dict: Dict[str, Any]) -> Dict[str, float]:
        """Extracts mean values for backward compatibility summaries."""
        flat: Dict[str, float] = {}
        for key, val in stats_dict.items():
            if isinstance(val, dict) and "mean" in val:
                flat[f"avg_{key}"] = val["mean"]
        return flat

    def export_results(self, result: BenchmarkRunResult) -> None:
        """
        Exports benchmark results to benchmark_results.json and benchmark_results.csv.
        """
        json_path = os.path.join(self.output_dir, "benchmark_results.json")
        csv_path = os.path.join(self.output_dir, "benchmark_results.csv")

        # 1. Export JSON
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        # 2. Export CSV
        fieldnames = [
            "run_id",
            "scenario",
            "task_id",
            "iteration",
            "task_completed",
            "tests_passed",
            "tests_total",
            "completion_rate",
            "continuity_score",
            "retrieval_precision",
            "retrieval_recall",
            "repeated_work_count",
            "dead_end_retries",
            "code_regression_count",
            "total_tokens_consumed",
            "handoff_latency_seconds",
            "total_duration_seconds",
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for m in result.metrics_per_task:
                row = {
                    "run_id": result.run_id,
                    "scenario": m.scenario,
                    "task_id": m.task_id,
                    "iteration": m.iteration,
                    "task_completed": m.task_completed,
                    "tests_passed": m.tests_passed,
                    "tests_total": m.tests_total,
                    "completion_rate": m.completion_rate,
                    "continuity_score": m.continuity_score,
                    "retrieval_precision": m.retrieval_precision,
                    "retrieval_recall": m.retrieval_recall,
                    "repeated_work_count": m.repeated_work_count,
                    "dead_end_retries": m.dead_end_retries,
                    "code_regression_count": m.code_regression_count,
                    "total_tokens_consumed": m.total_tokens_consumed,
                    "handoff_latency_seconds": m.handoff_latency_seconds,
                    "total_duration_seconds": m.total_duration_seconds,
                }
                writer.writerow(row)

        logger.info(f"Successfully exported {json_path} and {csv_path}.")
