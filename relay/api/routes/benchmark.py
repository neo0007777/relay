"""
FastAPI Routes for RelayBench Evaluation Framework.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from relay.schemas.benchmark import BenchmarkRunResult
from relay.benchmark.tasks import BenchmarkTask
from relay.benchmark.dataset_loader import DatasetLoader
from relay.benchmark.harness import RelayBenchmarkHarness
from relay.api.dependencies import get_benchmark_harness

router = APIRouter(prefix="/api/v1/benchmark", tags=["RelayBench Evaluation"])


@router.get("/tasks", response_model=List[BenchmarkTask])
def get_benchmark_tasks():
    """Lists available coding tasks in the RelayBench task suite."""
    return DatasetLoader().load_all_tasks()


@router.post("/run", response_model=BenchmarkRunResult)
def trigger_benchmark_run(
    limit_tasks: Optional[int] = None,
    harness: RelayBenchmarkHarness = Depends(get_benchmark_harness),
):
    """Executes a full RelayBench evaluation run across tasks and scenarios."""
    try:
        all_tasks = DatasetLoader().load_all_tasks()
        tasks_to_run = all_tasks[:limit_tasks] if limit_tasks else all_tasks
        custom_harness = RelayBenchmarkHarness(tasks=tasks_to_run)
        result = custom_harness.run_benchmark_suite()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark execution failed: {str(e)}")
