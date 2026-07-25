"""
Deterministic Agent Trace Replay Engine for RelayBench.
Replays JSONL tool traces in isolated sandbox environments to evaluate context handoff objectively.
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.schemas.checkpoint import KnowledgeCheckpoint, WhyNotItem, DecisionItem, RetrievedChunk
from relay.schemas.benchmark import BenchmarkMetric
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.retrieval.hybrid_reranker import HybridReranker
from relay.handoff.runner import LangGraphHandoffRunner
from relay.handoff.hooks import AgentExecutionHook
from relay.benchmark.tasks import BenchmarkTask
from relay.benchmark.metrics import ObjectiveMetricsCalculator

logger = get_logger("relay.benchmark.trace_replay")


class AgentTraceStep(BaseModel):
    """Single tool or reasoning step in an agent trace log."""

    step_index: int = Field(description="Step index")
    tool_name: str = Field(description="read_file, edit_file, why_not, decision, run_tests, etc.")
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output: str = Field(default="")
    exit_code: int = Field(default=0)
    is_failure: bool = Field(default=False)


class AgentTrace(BaseModel):
    """Complete recorded trace for an agent session."""

    session_id: str = Field(description="Recorded agent session ID")
    task_id: str = Field(description="Benchmark task ID")
    steps: List[AgentTraceStep] = Field(default_factory=list)

    @classmethod
    def load_jsonl(cls, filepath: str) -> "AgentTrace":
        """Loads an AgentTrace from a JSONL file."""
        steps: List[AgentTraceStep] = []
        session_id = "sess-jsonl"
        task_id = "task-unknown"

        with open(filepath, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if "session_id" in data:
                    session_id = data["session_id"]
                if "task_id" in data:
                    task_id = data["task_id"]

                steps.append(AgentTraceStep(
                    step_index=data.get("step_index", idx + 1),
                    tool_name=data.get("tool_name", "unknown"),
                    input_params=data.get("input_params", {}),
                    output=data.get("output", ""),
                    exit_code=data.get("exit_code", 0),
                    is_failure=data.get("is_failure", False)
                ))

        return cls(session_id=session_id, task_id=task_id, steps=steps)


class TraceReplayExecutor:
    """
    Executes an AgentTrace deterministically in a temporary sandbox directory.
    Evaluates real file modifications, context handoff triggers, and actual unit test execution.
    """

    def __init__(
        self,
        runner: Optional[LangGraphHandoffRunner] = None,
        calculator: Optional[ObjectiveMetricsCalculator] = None
    ):
        self.runner = runner or LangGraphHandoffRunner()
        self.calculator = calculator or ObjectiveMetricsCalculator()

    def execute_trace_replay(
        self,
        scenario: str,
        task: BenchmarkTask,
        trace: AgentTrace,
        sandbox_dir: str,
        iteration: int = 1
    ) -> BenchmarkMetric:
        """
        Replays trace steps in sandbox_dir and produces objective BenchmarkMetric.
        """
        start_time = time.time()
        logger.info(f"Replaying trace for scenario '{scenario}', task '{task.task_id}' in sandbox...")

        # 1. Materialize initial codebase into sandbox directory
        task.materialize_initial_codebase(sandbox_dir)

        # 1b. Automatically index sandbox codebase into vector store for hybrid retrieval
        indexed_chunks: List[RetrievedChunk] = []
        sandbox_abs = os.path.abspath(sandbox_dir)
        for root, _, files in os.walk(sandbox_abs):
            for fname in files:
                if fname.endswith((".py", ".js", ".css", ".md", ".json", ".yaml")):
                    fpath = os.path.join(root, fname)
                    rel_fpath = os.path.relpath(fpath, sandbox_abs)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            fcontent = f.read()
                        if fcontent.strip():
                            indexed_chunks.append(RetrievedChunk(
                                chunk_id=f"chk-{rel_fpath}",
                                file_path=rel_fpath,
                                content=fcontent,
                                score=1.0,
                                retrieval_source="initial_index"
                            ))
                    except Exception as e:
                        logger.warning(f"Could not index file '{fpath}': {e}")

        if indexed_chunks:
            self.runner.reranker.vector_store.upsert_chunks(indexed_chunks)
            logger.info(f"Indexed {len(indexed_chunks)} workspace chunks into Qdrant for task '{task.task_id}'.")

        # 2. Setup session state & hook with scenario-appropriate initial token load.
        #
        # Relay (full): starts at 87% utilization — above the 85% checkpoint_threshold —
        #   so the LangGraph handoff fires on the first recorded tool step. This produces
        #   real retrieved_context, real checkpoint data, and real handoff latency.
        #
        # Naive truncation: starts at 87% so the truncation event fires at the same
        #   point as relay_full, giving a fair comparison of handoff strategies.
        #
        # No-limit baseline: starts at a low token count (~5%) simulating a session
        #   running without artificial context constraints.
        token_limit = 128000
        if scenario == "no_limit_baseline":
            initial_tokens = max(5000, sum(len(c) for c in task.initial_codebase.values()) // 3)
        else:
            # Above 85% checkpoint threshold so handoff fires immediately
            initial_tokens = int(token_limit * 0.87)

        session = AgentSessionState(
            session_id=f"sess-replay-{scenario}-{task.task_id}-{iteration}",
            task_goal=task.description,
            tokens_consumed=initial_tokens,
            token_limit=token_limit,
            active_files=list(task.target_files)
        )

        hook = AgentExecutionHook(session_state=session)
        checkpoint: Optional[KnowledgeCheckpoint] = None
        handoff_latency = 0.0
        handoff_executed = False

        # 3. Process trace steps sequentially
        for step in trace.steps:
            # Handle special reasoning events
            if step.tool_name == "why_not":
                hook.record_why_not(
                    attempted_idea=step.input_params.get("attempted_idea", "Failed approach"),
                    rationale_rejected=step.input_params.get("rationale_rejected", "Syntax/logic error"),
                    error_traceback=step.input_params.get("error_traceback"),
                    files_involved=step.input_params.get("files_involved", task.target_files)
                )
                continue
            elif step.tool_name == "decision":
                hook.record_decision(
                    choice_made=step.input_params.get("choice_made", "Selected design"),
                    justification=step.input_params.get("justification", "Best fit"),
                    alternatives=step.input_params.get("alternatives", []),
                    files_affected=step.input_params.get("files_affected", task.target_files)
                )
                continue

            # Handle file modifications in sandbox with strict path traversal containment
            if step.tool_name in ("edit_file", "write_file"):
                rel_path = step.input_params.get("path", step.input_params.get("target_file"))
                content = step.input_params.get("content", step.input_params.get("code"))
                if rel_path and content is not None:
                    abs_path = os.path.abspath(os.path.join(sandbox_dir, rel_path))
                    if not abs_path.startswith(sandbox_abs):
                        raise ValueError(f"Sandbox containment violation: '{rel_path}' is outside '{sandbox_dir}'")

                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    old_text = ""
                    if os.path.exists(abs_path):
                        with open(abs_path, "r", encoding="utf-8") as f:
                            old_text = f.read()

                    with open(abs_path, "w", encoding="utf-8") as f:
                        f.write(content)

                    hook.update_file_diff(rel_path, old_text, content)

            # Record step and evaluate threshold
            should_trigger = hook.record_tool_step(
                tool_name=step.tool_name,
                input_params=step.input_params,
                output=step.output,
                exit_code=step.exit_code,
                is_failure=step.is_failure
            )

            # Trigger handoff if threshold crossed and not yet executed
            if should_trigger and not handoff_executed and scenario != "no_limit_baseline":
                h_start = time.time()

                if scenario == "naive_truncation":
                    # Naive truncation clears context & history without structured checkpointing
                    checkpoint = KnowledgeCheckpoint(
                        checkpoint_id=f"chk-trunc-{iteration}",
                        session_id=session.session_id,
                        task_goal=task.description,
                        narrative_progress="Truncated context window",
                    )
                else:
                    # Execute full LangGraph handoff
                    final_state = self.runner.execute_handoff(session_state=session, hook=hook)
                    checkpoint = final_state.get("checkpoint")

                handoff_latency = time.time() - h_start
                handoff_executed = True

        # Ensure a checkpoint object exists for evaluation
        if not checkpoint:
            checkpoint = KnowledgeCheckpoint(
                checkpoint_id=f"chk-final-{iteration}",
                session_id=session.session_id,
                task_goal=task.description,
                narrative_progress="Session complete",
                why_not_store=hook.why_not_store,
                decision_log=hook.decision_log
            )

        # 4. Run actual pytest test suite in sandbox directory
        tests_passed, tests_total, task_completed = task.run_verification_tests(sandbox_dir)
        total_duration = time.time() - start_time

        # 5. Calculate derived, honest objective metrics
        metric = self.calculator.evaluate_session(
            scenario=scenario,
            task=task,
            session_state=session,
            checkpoint=checkpoint,
            tests_passed=tests_passed,
            tests_total=tests_total,
            task_completed=task_completed,
            duration_seconds=total_duration,
            handoff_latency=handoff_latency,
            iteration=iteration
        )

        logger.info(
            f"Replay completed [{scenario}]: Passed {tests_passed}/{tests_total} tests "
            f"(Rate: {metric.completion_rate:.1%}, Precision: {metric.retrieval_precision:.2f})"
        )

        return metric
