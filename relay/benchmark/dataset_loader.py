"""
Benchmark Dataset Loader for RelayBench.
Scans and loads task definitions from relay/benchmark/datasets/ directory.
"""

import os
import json
import yaml
from typing import List, Dict, Any, Optional
from relay.core.logger import get_logger
from relay.benchmark.tasks import BenchmarkTask

logger = get_logger("relay.benchmark.dataset_loader")


class DatasetLoader:
    """Discovers and loads benchmark task packages from relay/benchmark/datasets/."""

    def __init__(self, datasets_dir: Optional[str] = None):
        if datasets_dir is None:
            # Default to relay/benchmark/datasets/ relative to package root
            base_dir = os.path.dirname(os.path.abspath(__file__))
            datasets_dir = os.path.join(base_dir, "datasets")
        self.datasets_dir = os.path.abspath(datasets_dir)

    def discover_task_directories(self) -> List[str]:
        """
        Recursively scans datasets_dir for subdirectories containing task.yaml or metadata.json.
        """
        task_dirs: List[str] = []
        if not os.path.exists(self.datasets_dir):
            logger.warning(f"Datasets directory '{self.datasets_dir}' does not exist.")
            return task_dirs

        for root, dirs, files in os.walk(self.datasets_dir):
            if "task.yaml" in files or "metadata.json" in files:
                task_dirs.append(root)

        task_dirs.sort()
        return task_dirs

    def load_task_from_dir(self, task_dir: str) -> Optional[BenchmarkTask]:
        """
        Parses a single task directory into a BenchmarkTask object.
        """
        yaml_path = os.path.join(task_dir, "task.yaml")
        json_meta_path = os.path.join(task_dir, "metadata.json")
        problem_path = os.path.join(task_dir, "problem.md")

        meta: Dict[str, Any] = {}

        if os.path.exists(yaml_path):
            with open(yaml_path, "r", encoding="utf-8") as f:
                meta = yaml.safe_load(f) or {}
        elif os.path.exists(json_meta_path):
            with open(json_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)

        if not meta:
            return None

        # Load problem description
        problem_desc = meta.get("description", "")
        if os.path.exists(problem_path):
            with open(problem_path, "r", encoding="utf-8") as f:
                problem_desc = f.read()

        # Load initial codebase files from repository/ subdirectory if present
        repo_dir = os.path.join(task_dir, "repository")
        initial_codebase: Dict[str, str] = {}

        if os.path.exists(repo_dir):
            for root, _, files in os.walk(repo_dir):
                for fname in files:
                    full_p = os.path.join(root, fname)
                    rel_p = os.path.relpath(full_p, repo_dir)
                    with open(full_p, "r", encoding="utf-8") as f:
                        initial_codebase[rel_p] = f.read()

        # Fallback to inline initial_codebase in metadata if repository/ is empty
        if not initial_codebase and "initial_codebase" in meta:
            initial_codebase = meta["initial_codebase"]

        # Load verification test script from tests/ subdirectory
        tests_dir = os.path.join(task_dir, "tests")
        test_script_content = meta.get("test_script_content", "")
        test_script_path = meta.get("test_script_path", "tests/test_task.py")

        if os.path.exists(tests_dir):
            for root, _, files in os.walk(tests_dir):
                for fname in files:
                    if fname.startswith("test_") and fname.endswith(".py"):
                        full_p = os.path.join(root, fname)
                        test_script_path = os.path.join("tests", fname)
                        with open(full_p, "r", encoding="utf-8") as f:
                            test_script_content = f.read()
                        break

        task_id = meta.get("task_id", os.path.basename(task_dir))
        title = meta.get("title", task_id)
        difficulty = meta.get("difficulty", "medium")
        target_files = meta.get("target_files", [])

        return BenchmarkTask(
            task_id=task_id,
            title=title,
            description=problem_desc,
            difficulty=difficulty,
            estimated_steps=meta.get("estimated_steps", 20),
            target_files=target_files,
            initial_codebase=initial_codebase,
            test_script_path=test_script_path,
            test_script_content=test_script_content,
        )

    def load_all_tasks(self) -> List[BenchmarkTask]:
        """
        Loads all discovered benchmark tasks from datasets directory.
        """
        task_dirs = self.discover_task_directories()
        tasks: List[BenchmarkTask] = []

        for tdir in task_dirs:
            task = self.load_task_from_dir(tdir)
            if task:
                tasks.append(task)

        logger.info(f"Loaded {len(tasks)} benchmark tasks from '{self.datasets_dir}'.")
        return tasks
