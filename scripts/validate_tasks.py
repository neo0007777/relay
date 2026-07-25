#!/usr/bin/env python3
"""
Task Validation Script for RelayBench Sprint 8.

For each benchmark task verifies:
1. Repository files exist on disk
2. Verification tests FAIL on the initial (broken) codebase
3. Expected solution exists on disk
4. Verification tests PASS after applying the expected solution

Generates: artifacts/task_validation_report.md
"""

import os
import sys
import json
import tempfile
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from relay.benchmark.dataset_loader import DatasetLoader
from relay.benchmark.tasks import BenchmarkTask


DATASET_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "relay", "benchmark", "datasets"
)
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "artifacts")


def run_pytest_in_dir(sandbox_dir: str, test_path: str) -> Dict[str, Any]:
    """Runs pytest and returns dict with passed, failed, exit_code, output."""
    cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"]
    try:
        res = subprocess.run(
            cmd,
            cwd=sandbox_dir,
            capture_output=True,
            text=True,
            timeout=15
        )
        output = res.stdout + res.stderr
        passed = 0
        failed = 0
        for line in output.splitlines():
            import re
            m_pass = re.search(r'(\d+)\s+passed', line)
            m_fail = re.search(r'(\d+)\s+failed', line)
            if m_pass:
                passed = int(m_pass.group(1))
            if m_fail:
                failed = int(m_fail.group(1))
        if passed == 0 and failed == 0:
            # fallback
            passed = 1 if res.returncode == 0 else 0
            failed = 0 if res.returncode == 0 else 1
        return {"passed": passed, "failed": failed, "exit_code": res.returncode, "output": output[-800:]}
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 1, "exit_code": -1, "output": "TIMEOUT"}
    except Exception as e:
        return {"passed": 0, "failed": 1, "exit_code": -1, "output": str(e)}


def validate_task(task: BenchmarkTask) -> Dict[str, Any]:
    """Validates a single task. Returns structured validation result."""
    result = {
        "task_id": task.task_id,
        "title": task.title,
        "status": "UNKNOWN",
        "initial_files_exist": False,
        "test_file_exists": False,
        "solution_files_exist": False,
        "initial_tests_fail": False,
        "solution_tests_pass": False,
        "initial_result": {},
        "solution_result": {},
        "rejection_reason": None,
    }

    # Find task directory on disk
    task_dir = None
    for cat in os.listdir(DATASET_ROOT):
        candidate = os.path.join(DATASET_ROOT, cat, task.task_id)
        if os.path.isdir(candidate):
            task_dir = candidate
            break

    if not task_dir:
        result["status"] = "REJECTED"
        result["rejection_reason"] = "Task directory not found on disk"
        return result

    repo_dir = os.path.join(task_dir, "repository")
    expected_dir = os.path.join(task_dir, "expected_outputs")
    tests_dir = os.path.join(task_dir, "tests")

    result["initial_files_exist"] = os.path.isdir(repo_dir)
    result["test_file_exists"] = os.path.exists(os.path.join(tests_dir, "test_task.py"))
    result["solution_files_exist"] = os.path.isdir(expected_dir)

    if not result["initial_files_exist"]:
        result["status"] = "REJECTED"
        result["rejection_reason"] = "repository/ directory missing"
        return result

    if not result["test_file_exists"]:
        result["status"] = "REJECTED"
        result["rejection_reason"] = "tests/test_task.py missing"
        return result

    if not result["solution_files_exist"]:
        result["status"] = "REJECTED"
        result["rejection_reason"] = "expected_outputs/ directory missing"
        return result

    # Step 1: Verify initial codebase makes tests FAIL
    with tempfile.TemporaryDirectory() as tmp:
        # Copy initial codebase
        shutil.copytree(repo_dir, tmp, dirs_exist_ok=True)
        # Copy tests
        test_target = os.path.join(tmp, "tests")
        os.makedirs(test_target, exist_ok=True)
        shutil.copy(os.path.join(tests_dir, "test_task.py"), os.path.join(test_target, "test_task.py"))

        init_res = run_pytest_in_dir(tmp, "tests/test_task.py")
        result["initial_result"] = init_res
        # Tests should FAIL on broken initial codebase
        result["initial_tests_fail"] = (init_res["exit_code"] != 0 or init_res["failed"] > 0)

    # Step 2: Verify expected solution makes tests PASS
    with tempfile.TemporaryDirectory() as tmp:
        # Copy initial codebase first
        shutil.copytree(repo_dir, tmp, dirs_exist_ok=True)
        # Apply solution on top
        shutil.copytree(expected_dir, tmp, dirs_exist_ok=True)
        # Copy tests
        test_target = os.path.join(tmp, "tests")
        os.makedirs(test_target, exist_ok=True)
        shutil.copy(os.path.join(tests_dir, "test_task.py"), os.path.join(test_target, "test_task.py"))

        sol_res = run_pytest_in_dir(tmp, "tests/test_task.py")
        result["solution_result"] = sol_res
        result["solution_tests_pass"] = (sol_res["exit_code"] == 0 and sol_res["failed"] == 0)

    if result["initial_tests_fail"] and result["solution_tests_pass"]:
        result["status"] = "VALID"
    elif not result["initial_tests_fail"]:
        result["status"] = "REJECTED"
        result["rejection_reason"] = "Initial codebase already passes tests — no challenge to solve"
    elif not result["solution_tests_pass"]:
        result["status"] = "REJECTED"
        result["rejection_reason"] = "Expected solution does not pass verification tests"

    return result


def main():
    print("=" * 70)
    print("⚡ RELAYBENCH TASK VALIDATION AUDIT — Sprint 8")
    print("=" * 70)

    loader = DatasetLoader()
    tasks = loader.load_all_tasks()
    print(f"\nLoaded {len(tasks)} benchmark tasks.\n")

    results: List[Dict[str, Any]] = []
    valid_count = 0
    rejected_count = 0

    for task in tasks:
        print(f"  Validating [{task.task_id}]...", end=" ", flush=True)
        r = validate_task(task)
        results.append(r)
        if r["status"] == "VALID":
            valid_count += 1
            print("✅ VALID")
        else:
            rejected_count += 1
            print(f"❌ REJECTED — {r['rejection_reason']}")

    print(f"\nSummary: {valid_count} valid / {rejected_count} rejected out of {len(tasks)} tasks.\n")

    # Generate task_validation_report.md
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    report_path = os.path.join(ARTIFACTS_DIR, "task_validation_report.md")

    lines = [
        "# RelayBench Task Validation Report — Sprint 8",
        "",
        f"> **Validation Date**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ",
        f"> **Tasks Audited**: {len(tasks)}  ",
        f"> **Valid Tasks**: {valid_count}  ",
        f"> **Rejected Tasks**: {rejected_count}",
        "",
        "---",
        "",
        "## Validation Criteria",
        "",
        "Each task must satisfy all four conditions to be accepted:",
        "1. `repository/` directory with initial (broken) codebase exists on disk",
        "2. `tests/test_task.py` verification script exists",
        "3. `expected_outputs/` directory with reference solution exists",
        "4. Initial codebase causes tests to **FAIL**; expected solution causes tests to **PASS**",
        "",
        "---",
        "",
        "## Per-Task Validation Results",
        "",
        "| Task ID | Title | Repo | Tests | Solution | Init Fail | Sol Pass | Status |",
        "|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for r in results:
        icon = "✅" if r["status"] == "VALID" else "❌"
        lines.append(
            f"| `{r['task_id']}` | {r['title']} "
            f"| {'✓' if r['initial_files_exist'] else '✗'} "
            f"| {'✓' if r['test_file_exists'] else '✗'} "
            f"| {'✓' if r['solution_files_exist'] else '✗'} "
            f"| {'✓' if r['initial_tests_fail'] else '✗'} "
            f"| {'✓' if r['solution_tests_pass'] else '✗'} "
            f"| {icon} {r['status']} |"
        )

    if rejected_count > 0:
        lines += ["", "---", "", "## Rejected Tasks — Details", ""]
        for r in results:
            if r["status"] == "REJECTED":
                lines += [
                    f"### ❌ `{r['task_id']}`",
                    f"- **Reason**: {r['rejection_reason']}",
                    "",
                ]

    lines += [
        "---",
        "",
        f"**{valid_count} tasks accepted for benchmark execution.**",
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ Validation report written to: {report_path}")

    # Return exit code based on whether we have enough valid tasks
    if valid_count == 0:
        print("\n❌ ERROR: No valid tasks — benchmark cannot proceed.")
        sys.exit(1)
    else:
        print(f"\n✅ {valid_count} valid tasks ready for benchmark execution.")


if __name__ == "__main__":
    main()
