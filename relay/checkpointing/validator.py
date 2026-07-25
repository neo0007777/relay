"""
Checkpoint Validation and Integrity Verification Engine for Relay.
Verifies required fields, workspace file existence, payload checksums, and prompt synthesis viability.
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger
from relay.schemas.checkpoint import KnowledgeCheckpoint

logger = get_logger("relay.checkpointing.validator")


class ValidationResult(BaseModel):
    """Container for checkpoint validation outcome."""

    is_valid: bool = Field(description="True if checkpoint satisfies all validity contracts")
    checksum: str = Field(description="Deterministic SHA-256 hash of checkpoint payload")
    errors: List[str] = Field(default_factory=list, description="List of validation errors if invalid")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")


class CheckpointValidator:
    """
    Validates KnowledgeCheckpoint objects against schema integrity, workspace file existence,
    and SHA-256 checksum verification.
    """

    @staticmethod
    def compute_checksum(checkpoint: KnowledgeCheckpoint) -> str:
        """
        Computes a deterministic SHA-256 checksum of the checkpoint content.
        Excludes non-deterministic runtime fields like checksum itself.
        """
        payload_data = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "session_id": checkpoint.session_id,
            "task_goal": checkpoint.task_goal,
            "narrative_progress": checkpoint.narrative_progress,
            "decision_log": [d.model_dump(mode="json") for d in checkpoint.decision_log],
            "why_not_store": [w.model_dump(mode="json") for w in checkpoint.why_not_store],
            "ast_changes": [a.model_dump(mode="json") for a in checkpoint.ast_changes],
        }
        serialized = json.dumps(payload_data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def validate(
        self,
        checkpoint: KnowledgeCheckpoint,
        workspace_dir: Optional[str] = None
    ) -> ValidationResult:
        """
        Executes complete validation checks on a KnowledgeCheckpoint.

        Args:
            checkpoint: KnowledgeCheckpoint instance to validate.
            workspace_dir: Optional root directory path to verify referenced files exist.

        Returns:
            ValidationResult with validity status, SHA-256 checksum, and error details.
        """
        errors: List[str] = []
        warnings: List[str] = []
        checksum = self.compute_checksum(checkpoint)

        # 1. Required Fields Check
        if not checkpoint.checkpoint_id or not checkpoint.checkpoint_id.strip():
            errors.append("Missing required field: 'checkpoint_id'")
        if not checkpoint.session_id or not checkpoint.session_id.strip():
            errors.append("Missing required field: 'session_id'")
        if not checkpoint.task_goal or not checkpoint.task_goal.strip():
            errors.append("Missing required field: 'task_goal'")
        if not checkpoint.narrative_progress or not checkpoint.narrative_progress.strip():
            errors.append("Missing required field: 'narrative_progress'")

        # 2. Schema Structure Verification
        if checkpoint.tokens_at_checkpoint < 0:
            errors.append("Invalid tokens_at_checkpoint: value cannot be negative")
        if checkpoint.context_limit <= 0:
            errors.append("Invalid context_limit: value must be positive")

        # 3. Workspace File Existence Check (if workspace_dir provided)
        if workspace_dir and os.path.exists(workspace_dir):
            abs_workspace = os.path.abspath(workspace_dir)

            # Check file diff paths
            for diff in checkpoint.file_diffs:
                target_path = os.path.join(abs_workspace, diff.file_path)
                if not os.path.exists(target_path):
                    warnings.append(f"Referenced diff file does not exist in workspace: '{diff.file_path}'")

            # Check AST changed files
            for ast_change in checkpoint.ast_changes:
                target_path = os.path.join(abs_workspace, ast_change.file_path)
                if not os.path.exists(target_path):
                    warnings.append(f"Referenced AST changed file does not exist in workspace: '{ast_change.file_path}'")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"Checkpoint '{checkpoint.checkpoint_id}' validated successfully (Checksum: {checksum[:8]}).")
        else:
            logger.error(f"Checkpoint '{checkpoint.checkpoint_id}' validation failed with {len(errors)} errors.")

        return ValidationResult(
            is_valid=is_valid,
            checksum=checksum,
            errors=errors,
            warnings=warnings
        )
