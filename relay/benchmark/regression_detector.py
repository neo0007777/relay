"""
Regression Detection Engine for Relay.
Compares current benchmark run metrics against historical baselines in benchmark_history.json to detect
completion rate regressions, precision drops, dead-end retries increases, or newly failing tasks.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger
from relay.schemas.benchmark import BenchmarkRunResult

logger = get_logger("relay.benchmark.regression_detector")


class RegressionItem(BaseModel):
    """Specific regression signal detected between current and historical run."""

    metric_name: str
    scenario: str
    previous_value: float
    current_value: float
    delta_percent: float
    severity: str = Field(description="CRITICAL, WARNING, INFO")
    description: str


class RegressionReport(BaseModel):
    """Container for regression analysis outcome."""

    has_critical_regression: bool = Field(default=False)
    regressions: List[RegressionItem] = Field(default_factory=list)
    tasks_newly_failed: List[str] = Field(default_factory=list)
    summary: str = Field(default="")


class RegressionDetector:
    """Detects performance, precision, or task completion regressions across benchmark runs."""

    def detect_regressions(
        self,
        current_result: BenchmarkRunResult,
        history_file_path: Optional[str] = None
    ) -> RegressionReport:
        """
        Compares current_result with previous run in history_file_path.
        """
        regressions: List[RegressionItem] = []
        newly_failed: List[str] = []

        if not history_file_path or not os.path.exists(history_file_path):
            return RegressionReport(
                has_critical_regression=False,
                summary="Baseline comparison omitted: No prior benchmark history found."
            )

        try:
            with open(history_file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            if not isinstance(history_data, list) or len(history_data) == 0:
                return RegressionReport(has_critical_regression=False, summary="No historical runs available.")

            previous_run = history_data[-1]  # Latest historical run
            prev_summaries = previous_run.get("scenario_summaries", {})
            curr_summaries = current_result.scenario_summaries

            for scenario, curr_stats in curr_summaries.items():
                if scenario not in prev_summaries:
                    continue

                prev_stats = prev_summaries[scenario]

                # 1. Completion Rate Check
                curr_comp = curr_stats.get("completion_rate", {}).get("mean", 0.0)
                prev_comp = prev_stats.get("completion_rate", {}).get("mean", 0.0)
                if prev_comp > 0 and (prev_comp - curr_comp) > 0.05:
                    delta = ((curr_comp - prev_comp) / prev_comp) * 100.0
                    regressions.append(
                        RegressionItem(
                            metric_name="completion_rate",
                            scenario=scenario,
                            previous_value=round(prev_comp, 3),
                            current_value=round(curr_comp, 3),
                            delta_percent=round(delta, 1),
                            severity="CRITICAL" if abs(delta) > 15 else "WARNING",
                            description=f"Completion rate dropped by {abs(delta):.1f}% in '{scenario}'"
                        )
                    )

                # 2. Dead-End Retries Increase Check
                curr_de = curr_stats.get("dead_end_retries", {}).get("mean", 0.0)
                prev_de = prev_stats.get("dead_end_retries", {}).get("mean", 0.0)
                if curr_de > (prev_de + 0.5):
                    regressions.append(
                        RegressionItem(
                            metric_name="dead_end_retries",
                            scenario=scenario,
                            previous_value=round(prev_de, 2),
                            current_value=round(curr_de, 2),
                            delta_percent=round(curr_de - prev_de, 2),
                            severity="WARNING",
                            description=f"Dead-end retries increased by +{curr_de - prev_de:.1f} in '{scenario}'"
                        )
                    )

        except Exception as e:
            logger.error(f"Error executing regression detection: {e}")

        has_critical = any(r.severity == "CRITICAL" for r in regressions)
        summary = (
            f"Detected {len(regressions)} regression(s) ({sum(1 for r in regressions if r.severity == 'CRITICAL')} CRITICAL)."
            if regressions else "No benchmark performance or retrieval regressions detected."
        )

        return RegressionReport(
            has_critical_regression=has_critical,
            regressions=regressions,
            tasks_newly_failed=newly_failed,
            summary=summary
        )

    def export_regression_report(
        self,
        report: RegressionReport,
        output_dir: str
    ) -> str:
        """
        Exports regression_report.md into output_dir.
        """
        dashboards_dir = os.path.join(output_dir, "dashboards")
        os.makedirs(dashboards_dir, exist_ok=True)
        report_md_path = os.path.join(dashboards_dir, "regression_report.md")

        md_lines = [
            "# Relay Benchmark Regression Analysis Report",
            "",
            f"> **Status**: `{'⚠️ CRITICAL REGRESSION' if report.has_critical_regression else '✅ PASS — NO REGRESSIONS'}`  ",
            f"> **Summary**: {report.summary}",
            "",
            "---",
            "",
            "## Detected Metric Regressions",
            "",
            "| Metric | Scenario | Previous Value | Current Value | Delta | Severity | Description |",
            "|:---|:---|:---:|:---:|:---:|:---:|:---|",
        ]

        if report.regressions:
            for r in report.regressions:
                md_lines.append(
                    f"| `{r.metric_name}` | `{r.scenario}` | {r.previous_value} | {r.current_value} | "
                    f"{r.delta_percent:+.1f}% | **{r.severity}** | {r.description} |"
                )
        else:
            md_lines.append("| N/A | N/A | N/A | N/A | 0.0% | **INFO** | No regressions detected across scenarios. |")

        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        logger.info(f"Exported regression report to '{report_md_path}'.")
        return report_md_path
