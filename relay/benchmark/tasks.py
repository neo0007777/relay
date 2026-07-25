"""
Standardized Executable Coding Benchmark Task Suite for RelayBench.
Provides initial codebases, failing unit tests, expected solutions, and ground-truth relevant file manifests.
"""

import os
import re
import sys
import subprocess
from typing import List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class BenchmarkTask(BaseModel):
    """Definition of an executable coding task evaluated in RelayBench."""

    task_id: str = Field(description="Unique task ID")
    title: str = Field(description="Short human-readable task title")
    description: str = Field(description="Detailed coding objective description")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    estimated_steps: int = Field(default=20, description="Estimated total tool steps to complete")
    target_files: List[str] = Field(default_factory=list, description="Ground-truth relevant files for retrieval evaluation")
    initial_codebase: Dict[str, str] = Field(default_factory=dict, description="Relative file path to initial content map")
    test_script_path: str = Field(default="tests/test_task.py", description="Relative path where pytest test file will be placed")
    test_script_content: str = Field(description="Pytest test suite content evaluating task completion")

    def materialize_initial_codebase(self, target_dir: str) -> None:
        """
        Materializes initial codebase files and verification test script into target_dir.
        """
        for rel_path, content in self.initial_codebase.items():
            abs_path = os.path.join(target_dir, rel_path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)

        test_abs_path = os.path.join(target_dir, self.test_script_path)
        os.makedirs(os.path.dirname(test_abs_path), exist_ok=True)
        with open(test_abs_path, "w", encoding="utf-8") as f:
            f.write(self.test_script_content)

    def run_verification_tests(self, sandbox_dir: str) -> Tuple[int, int, bool]:
        """
        Executes pytest in sandbox_dir and returns (tests_passed, tests_total, all_passed).
        """
        test_file = os.path.join(sandbox_dir, self.test_script_path)
        if not os.path.exists(test_file):
            return 0, 0, False

        cmd = [sys.executable, "-m", "pytest", self.test_script_path, "-v", "--tb=no"]
        try:
            res = subprocess.run(
                cmd,
                cwd=sandbox_dir,
                capture_output=True,
                text=True,
                timeout=15
            )
            stdout = res.stdout + res.stderr

            # Parse pytest output for pass/fail counts
            passed = 0
            failed = 0
            for line in stdout.splitlines():
                if "passed" in line or "failed" in line:
                    match_passed = re.search(r'(\d+)\s+passed', line)
                    match_failed = re.search(r'(\d+)\s+failed', line)
                    if match_passed:
                        passed = int(match_passed.group(1))
                    if match_failed:
                        failed = int(match_failed.group(1))

            total = passed + failed
            if total == 0:
                # If pytest output format couldn't be parsed, fallback to exit code
                all_passed = (res.returncode == 0)
                return (1 if all_passed else 0), 1, all_passed

            all_passed = (res.returncode == 0 and failed == 0 and passed > 0)
            return passed, total, all_passed

        except Exception as e:
            return 0, 1, False

