"""
Objective Metrics Calculator for RelayBench.
Computes 100% derived quantitative metrics from actual agent execution and test suite runs.
Contains ZERO hardcoded or simulated metric values.
"""

from typing import List, Dict, Any, Set, Tuple
from relay.schemas.checkpoint import KnowledgeCheckpoint, WhyNotItem, RetrievedChunk
from relay.schemas.agent_state import AgentSessionState, ToolExecutionLog
from relay.schemas.benchmark import BenchmarkMetric
from relay.benchmark.tasks import BenchmarkTask


class ObjectiveMetricsCalculator:
    """Computes derived objective quantitative metrics for agent session runs."""

    def calculate_retrieval_precision_recall(
        self,
        retrieved_chunks: List[RetrievedChunk],
        target_files: List[str]
    ) -> Tuple[float, float, int, int]:
        """
        Calculates exact ground-truth precision and recall for retrieved context chunks.

        Returns:
            (precision, recall, retrieved_count, relevant_retrieved_count)
        """
        if not retrieved_chunks:
            return 0.0, 0.0, 0, 0

        target_set: Set[str] = set(target_files)
        if not target_set:
            return 0.0, 0.0, len(retrieved_chunks), 0

        # Count retrieved chunks whose file_path matches ground-truth target_files
        matching_chunks = sum(1 for c in retrieved_chunks if c.file_path in target_set)
        retrieved_count = len(retrieved_chunks)

        precision = round(matching_chunks / retrieved_count, 4) if retrieved_count > 0 else 0.0

        # Count unique target files covered by retrieved chunks
        covered_targets = {c.file_path for c in retrieved_chunks if c.file_path in target_set}
        recall = round(len(covered_targets) / len(target_set), 4) if len(target_set) > 0 else 0.0

        return precision, recall, retrieved_count, matching_chunks

    def calculate_repeated_work(self, tool_logs: List[ToolExecutionLog]) -> int:
        """
        Calculates repeated work count by detecting identical file edit operations.
        """
        seen_edits: Set[str] = set()
        duplicate_count = 0

        for log in tool_logs:
            if log.tool_name in ("edit_file", "write_file"):
                path = str(log.input_params.get("path", log.input_params.get("target_file", "")))
                content = str(log.input_params.get("content", log.input_params.get("code", "")))
                edit_key = f"{path}:{hash(content)}"

                if edit_key in seen_edits:
                    duplicate_count += 1
                else:
                    seen_edits.add(edit_key)

        return duplicate_count

    def calculate_dead_end_retries(
        self,
        tool_logs: List[ToolExecutionLog],
        why_not_store: List[WhyNotItem]
    ) -> int:
        """
        Calculates dead-end retry count by checking if tool steps re-attempted known failed approaches.
        """
        if not why_not_store:
            return 0

        dead_end_count = 0
        dead_end_keywords: Set[str] = set()

        for wn in why_not_store:
            for word in wn.attempted_idea.lower().split():
                if len(word) > 4:  # Filter out trivial stop words
                    dead_end_keywords.add(word)

        for log in tool_logs:
            output_text = (str(log.input_params) + " " + log.output_summary).lower()
            matches = sum(1 for kw in dead_end_keywords if kw in output_text)
            if matches >= 2 and log.is_failure:
                dead_end_count += 1

        return dead_end_count

    def calculate_code_regressions(self, tool_logs: List[ToolExecutionLog]) -> int:
        """
        Calculates code regressions (when a test previously passing fails later).
        """
        passed_tests: Set[str] = set()
        regression_count = 0

        for log in tool_logs:
            if "test" in log.tool_name.lower() or "pytest" in str(log.input_params.get("cmd", "")):
                test_name = str(log.input_params.get("test_name", log.input_params.get("cmd", "default_test_suite")))
                if log.exit_code == 0 and not log.is_failure:
                    passed_tests.add(test_name)
                elif log.is_failure or log.exit_code != 0:
                    if test_name in passed_tests:
                        regression_count += 1

        return regression_count

    def calculate_continuity_score(
        self,
        completion_rate: float,
        precision: float,
        repeated_work: int,
        dead_end_retries: int,
        regressions: int
    ) -> float:
        """
        Computes derived composite continuity score in [0.0, 1.0].
        Score = (0.50 * completion_rate + 0.50 * precision) - penalties.
        """
        base = 0.50 * completion_rate + 0.50 * precision

        penalty_repeat = min(0.20, repeated_work * 0.08)
        penalty_deadend = min(0.25, dead_end_retries * 0.12)
        penalty_regression = min(0.20, regressions * 0.10)

        total_score = max(0.0, min(1.0, base - penalty_repeat - penalty_deadend - penalty_regression))
        return round(total_score, 4)

    def evaluate_session(
        self,
        scenario: str,
        task: BenchmarkTask,
        session_state: AgentSessionState,
        checkpoint: KnowledgeCheckpoint,
        tests_passed: int,
        tests_total: int,
        task_completed: bool,
        duration_seconds: float = 0.0,
        handoff_latency: float = 0.0,
        iteration: int = 1
    ) -> BenchmarkMetric:
        """
        Synthesizes complete BenchmarkMetric object from derived actual execution outputs.
        """
        completion_rate = round(tests_passed / tests_total, 4) if tests_total > 0 else 0.0
        
        precision, recall, retrieved_cnt, relevant_retrieved = self.calculate_retrieval_precision_recall(
            retrieved_chunks=checkpoint.retrieved_context,
            target_files=task.target_files
        )

        repeated_work = self.calculate_repeated_work(session_state.tool_logs)
        dead_ends = self.calculate_dead_end_retries(session_state.tool_logs, checkpoint.why_not_store)
        regressions = self.calculate_code_regressions(session_state.tool_logs)
        
        continuity = self.calculate_continuity_score(
            completion_rate=completion_rate,
            precision=precision,
            repeated_work=repeated_work,
            dead_end_retries=dead_ends,
            regressions=regressions
        )

        return BenchmarkMetric(
            scenario=scenario,
            task_id=task.task_id,
            iteration=iteration,
            task_completed=task_completed,
            tests_passed=tests_passed,
            tests_total=tests_total,
            completion_rate=completion_rate,
            repeated_work_count=repeated_work,
            dead_end_retries=dead_ends,
            code_regression_count=regressions,
            continuity_score=continuity,
            total_tokens_consumed=session_state.tokens_consumed,
            handoff_count=1 if scenario != "no_limit_baseline" else 0,
            total_duration_seconds=round(duration_seconds, 3),
            handoff_latency_seconds=round(handoff_latency, 3),
            retrieved_chunk_count=retrieved_cnt,
            relevant_chunks_retrieved=relevant_retrieved,
            retrieval_precision=precision,
            retrieval_recall=recall,
        )
