"""
Evidence Validation Engine for Relay.
Enforces strict integrity, presence, non-emptiness, and valid structure across all generated evidence files.
"""

import os
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from relay.core.logger import get_logger

logger = get_logger("relay.benchmark.evidence_validator")


class EvidenceValidationError(Exception):
    """Raised when benchmark evidence package validation fails."""
    pass


class EvidenceValidationResult(BaseModel):
    """Container for evidence package validation outcome."""

    is_valid: bool = Field(description="True if all evidence package files exist and are valid")
    checked_files_count: int = Field(default=0)
    missing_files: List[str] = Field(default_factory=list)
    corrupted_files: List[str] = Field(default_factory=list)


class EvidenceValidator:
    """Validates complete evidence package directory structure and file integrity."""

    REQUIRED_ARTIFACT_PATHS = [
        "benchmark/summary.json",
        "benchmark/summary.csv",
        "benchmark/summary.md",
        "retrieval/retrieved_chunks.json",
        "retrieval/retrieval_scores.json",
        "retrieval/retrieval_report.md",
        "checkpoints/checkpoint_metadata.json",
        "checkpoints/checkpoint_sizes.json",
        "checkpoints/checkpoint_report.md",
        "traces/execution_trace.jsonl",
        "prompts/resume_prompt.txt",
        "dashboards/benchmark_results.json",
        "dashboards/benchmark_history.json",
        "dashboards/experiment_metadata.json",
        "dashboards/regression_report.md",
    ]

    def validate_package(
        self,
        output_dir: str,
        raise_on_error: bool = True
    ) -> EvidenceValidationResult:
        """
        Validates presence and non-emptiness of all 15 required evidence package files.
        """
        missing: List[str] = []
        corrupted: List[str] = []

        for rel_path in self.REQUIRED_ARTIFACT_PATHS:
            full_path = os.path.join(output_dir, rel_path)
            if not os.path.exists(full_path):
                missing.append(rel_path)
                continue

            if os.path.getsize(full_path) == 0:
                corrupted.append(f"{rel_path} (empty file)")
                continue

            if rel_path.endswith(".json"):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        json.load(f)
                except Exception as e:
                    corrupted.append(f"{rel_path} (invalid JSON: {e})")

        is_valid = (len(missing) == 0 and len(corrupted) == 0)
        result = EvidenceValidationResult(
            is_valid=is_valid,
            checked_files_count=len(self.REQUIRED_ARTIFACT_PATHS),
            missing_files=missing,
            corrupted_files=corrupted
        )

        if not is_valid:
            error_msg = f"Evidence Package Validation Failed: Missing {len(missing)} files, Corrupted {len(corrupted)} files."
            logger.error(f"{error_msg} Missing: {missing}, Corrupted: {corrupted}")
            if raise_on_error:
                raise EvidenceValidationError(error_msg)

        logger.info(f"Evidence package in '{output_dir}' validated successfully ({len(self.REQUIRED_ARTIFACT_PATHS)} files verified).")
        return result
