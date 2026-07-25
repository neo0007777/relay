"""
BenchmarkRunner Engine for RelayBench.
Orchestrates dataset discovery, sandbox workspace materialization, trace execution, test execution, metric derivation, and JSON/CSV reporting.
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

logger = get_logger("relay.benchmark.runner")


class BenchmarkRunner:
    """Production-grade benchmark runner for executing real software engineering tasks."""

    def __init__(
        self,
        datasets_dir: Optional[str] = None,
        output_dir: str = settings.BENCHMARK_RESULTS_DIR,
    ):
        self.loader = DatasetLoader(datasets_dir=datasets_dir)
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def run_full_evaluation(
        self,
        repetitions: int = 3,
        include_ablations: bool = True,
        limit_tasks: Optional[int] = None
    ) -> BenchmarkRunResult:
        """
        Executes complete comparative evaluation across dataset tasks for N repetitions.

        Args:
            repetitions: Number of trial iterations per task/scenario.
            include_ablations: Whether to include ablation matrix scenarios.
            limit_tasks: Optional cap on total tasks to execute.

        Returns:
            BenchmarkRunResult container with full statistical summaries.
        """
        run_id = f"run-s2-{uuid.uuid4().hex[:8]}"
        tasks = self.loader.load_all_tasks()

        if limit_tasks:
            tasks = tasks[:limit_tasks]

        logger.info(
            f"Starting BenchmarkRunner Evaluation '{run_id}' across {len(tasks)} tasks "
            f"({repetitions} repetitions, ablations={include_ablations})..."
        )

        scenarios = ["relay_full", "naive_truncation", "no_limit_baseline"]
        if include_ablations:
            scenarios.extend(["no_why_not", "no_ast", "no_graph", "vector_only"])

        all_metrics: List[BenchmarkMetric] = []

        for task in tasks:
            logger.info(f"Evaluating Task '{task.task_id}' [{task.title}]...")

            for scenario in scenarios:
                if scenario in ABLATION_MATRIX:
                    runner_instance = build_ablation_runner(ABLATION_MATRIX[scenario])
                else:
                    runner_instance = LangGraphHandoffRunner()

                executor = TraceReplayExecutor(runner=runner_instance)
                trace = generate_task_trace(task.task_id, scenario, task=task)

                for rep in range(1, repetitions + 1):
                    with tempfile.TemporaryDirectory() as sandbox_dir:
                        metric = executor.execute_trace_replay(
                            scenario=scenario,
                            task=task,
                            trace=trace,
                            sandbox_dir=sandbox_dir,
                            iteration=rep
                        )
                        all_metrics.append(metric)

        # Compute statistical summaries
        scenario_summaries: Dict[str, Dict[str, Any]] = {}
        ablation_matrix_summary: Dict[str, Dict[str, Any]] = {}

        for scenario in scenarios:
            scen_metrics = [m for m in all_metrics if m.scenario == scenario]
            stats = self._compute_statistical_summary(scen_metrics)
            scenario_summaries[scenario] = stats

            if scenario in ABLATION_MATRIX:
                ablation_matrix_summary[scenario] = stats

        result = BenchmarkRunResult(
            run_id=run_id,
            timestamp=datetime.now(),
            tasks_evaluated=len(tasks),
            iterations_per_task=repetitions,
            scenario_summaries=scenario_summaries,
            ablation_matrix=ablation_matrix_summary,
            relay_summary=self._flatten_mean_summary(scenario_summaries.get("relay_full", {})),
            naive_truncation_summary=self._flatten_mean_summary(scenario_summaries.get("naive_truncation", {})),
            no_limit_baseline_summary=self._flatten_mean_summary(scenario_summaries.get("no_limit_baseline", {})),
            metrics_per_task=all_metrics,
        )

        self.export_results(result)
        logger.info(f"BenchmarkRunner Run '{run_id}' complete. Output written to {self.output_dir}.")
        return result

    def _compute_statistical_summary(self, metrics: List[BenchmarkMetric]) -> Dict[str, Any]:
        """Computes mean, median, std_dev, and 95% confidence intervals for metrics."""
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
        """Extracts mean values for backward compatibility."""
        return {f"avg_{k}": v["mean"] for k, v in stats_dict.items() if isinstance(v, dict) and "mean" in v}

    def export_results(self, result: BenchmarkRunResult) -> None:
        """
        Exports evidence package via EvidenceGenerator.
        """
        from relay.benchmark.evidence_generator import EvidenceGenerator
        generator = EvidenceGenerator()
        generator.generate_evidence_package(result, self.output_dir)
        logger.info(f"Exported complete evidence package to directory '{self.output_dir}'.")
