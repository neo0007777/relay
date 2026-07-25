"""
Pydantic Schemas for RelayBench Evaluation and Metrics.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BenchmarkMetric(BaseModel):
    """Objective evaluation metrics for a single agent session run."""

    scenario: str = Field(description="relay_full, naive_truncation, no_limit_baseline, or ablation name")
    task_id: str = Field(description="Benchmark task ID")
    iteration: int = Field(default=1, description="Iteration/trial index for statistical runs")
    
    # Executable Test Suite Metrics
    task_completed: bool = Field(default=False, description="Whether all unit tests passed")
    tests_passed: int = Field(default=0, description="Count of passing unit tests")
    tests_total: int = Field(default=0, description="Total count of unit tests in task suite")
    completion_rate: float = Field(default=0.0, description="Ratio of tests passed / total tests [0.0 - 1.0]")
    
    # Continuity & Duplicate Work Metrics
    repeated_work_count: int = Field(default=0, description="Number of duplicate edits on identical code lines")
    dead_end_retries: int = Field(default=0, description="Number of times agent re-attempted a known failed approach")
    code_regression_count: int = Field(default=0, description="Number of previously passing tests broken")
    continuity_score: float = Field(default=0.0, description="Composite continuity quality score [0.0 - 1.0]")
    
    # Efficiency & Overhead
    total_tokens_consumed: int = Field(default=0, description="Total input + output tokens across sessions")
    handoff_count: int = Field(default=0, description="Number of context handoffs executed")
    total_duration_seconds: float = Field(default=0.0, description="Total execution time in seconds")
    handoff_latency_seconds: float = Field(default=0.0, description="Total time spent checkpointing & resuming")
    
    # Derived Ground-Truth Retrieval Metrics
    retrieved_chunk_count: int = Field(default=0, description="Total chunks retrieved during handoff")
    relevant_chunks_retrieved: int = Field(default=0, description="Count of retrieved chunks matching relevant files")
    retrieval_precision: float = Field(default=0.0, description="Precision of retrieved code chunks")
    retrieval_recall: float = Field(default=0.0, description="Recall of retrieved code chunks")


class BenchmarkRunResult(BaseModel):
    """Aggregated results across a benchmark suite execution with statistical measures."""

    run_id: str = Field(description="Unique benchmark run ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    tasks_evaluated: int = Field(default=0)
    iterations_per_task: int = Field(default=1)
    
    # Statistical summaries per scenario/ablation (mean, median, std_dev, ci95)
    scenario_summaries: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    ablation_matrix: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Backward compatible fields
    relay_summary: Dict[str, float] = Field(default_factory=dict)
    naive_truncation_summary: Dict[str, float] = Field(default_factory=dict)
    no_limit_baseline_summary: Dict[str, float] = Field(default_factory=dict)
    
    metrics_per_task: List[BenchmarkMetric] = Field(default_factory=list)
