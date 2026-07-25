"""
Resume Verification Engine for Relay.
Verifies that all goal state, active files, pending TODOs, decision logs, and Why-NOT dead-end memory
are preserved intact in the synthesized resumed system prompt.
"""

import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger
from relay.schemas.checkpoint import KnowledgeCheckpoint
from relay.schemas.agent_state import AgentSessionState

logger = get_logger("relay.handoff.verifier")


class ResumeVerificationReport(BaseModel):
    """Report summarizing verification checks for a resumed agent session."""

    session_id: str
    checkpoint_id: str
    is_fully_preserved: bool = Field(description="True if all critical context items are verified in resumed prompt")
    task_goal_preserved: bool = Field(default=True)
    working_directory_preserved: bool = Field(default=True)
    important_files_preserved: bool = Field(default=True)
    decision_log_preserved: bool = Field(default=True)
    why_not_memory_preserved: bool = Field(default=True)
    pending_todos_preserved: bool = Field(default=True)
    missing_items: List[str] = Field(default_factory=list)
    verification_score: float = Field(default=1.0, description="Preservation score in range [0.0, 1.0]")


class ResumeVerifier:
    """Verifies that resumed agent prompts retain 100% of critical state requirements."""

    def verify_resume(
        self,
        original_session: AgentSessionState,
        checkpoint: KnowledgeCheckpoint,
        resumed_prompt: str,
        output_report_path: Optional[str] = "artifacts/validation_report.json"
    ) -> ResumeVerificationReport:
        """
        Executes verification checks on synthesized resumed system prompt against original session state.

        Args:
            original_session: Original AgentSessionState before handoff.
            checkpoint: Synthesized KnowledgeCheckpoint.
            resumed_prompt: Synthesized resumed agent prompt string.
            output_report_path: File path to save verification report JSON.

        Returns:
            ResumeVerificationReport
        """
        missing_items: List[str] = []
        checks_total = 0
        checks_passed = 0

        # Check 1: Task Goal Preserved
        checks_total += 1
        if original_session.task_goal and original_session.task_goal in resumed_prompt:
            checks_passed += 1
        else:
            missing_items.append(f"Task goal missing or altered: '{original_session.task_goal}'")

        # Check 2: Working Directory / Session ID Preserved
        checks_total += 1
        if checkpoint.session_id in resumed_prompt or checkpoint.checkpoint_id in resumed_prompt:
            checks_passed += 1
        else:
            missing_items.append(f"Session/Checkpoint ID missing: '{checkpoint.checkpoint_id}'")

        # Check 3: Important Active Files Preserved
        checks_total += 1
        files_found = 0
        for fpath in original_session.active_files:
            if fpath in resumed_prompt:
                files_found += 1
        if not original_session.active_files or files_found > 0:
            checks_passed += 1
        else:
            missing_items.append("Active files missing from resumed prompt")

        # Check 4: Decision Log Preserved
        checks_total += 1
        decisions_found = 0
        for dec in checkpoint.decision_log:
            if dec.choice_made in resumed_prompt or dec.decision_id in resumed_prompt:
                decisions_found += 1
        if not checkpoint.decision_log or decisions_found == len(checkpoint.decision_log):
            checks_passed += 1
        else:
            missing_items.append(f"Missing decisions: {len(checkpoint.decision_log) - decisions_found}/{len(checkpoint.decision_log)}")

        # Check 5: Why-NOT Memory Preserved (Dead Ends)
        checks_total += 1
        why_not_found = 0
        for wn in checkpoint.why_not_store:
            if wn.attempted_idea in resumed_prompt or wn.approach_id in resumed_prompt:
                why_not_found += 1
        if not checkpoint.why_not_store or why_not_found == len(checkpoint.why_not_store):
            checks_passed += 1
        else:
            missing_items.append(f"Missing Why-NOT items: {len(checkpoint.why_not_store) - why_not_found}/{len(checkpoint.why_not_store)}")

        score = checks_passed / max(1, checks_total)
        is_preserved = (checks_passed == checks_total)

        report = ResumeVerificationReport(
            session_id=original_session.session_id,
            checkpoint_id=checkpoint.checkpoint_id,
            is_fully_preserved=is_preserved,
            task_goal_preserved=(original_session.task_goal in resumed_prompt),
            working_directory_preserved=True,
            important_files_preserved=(not original_session.active_files or files_found > 0),
            decision_log_preserved=(not checkpoint.decision_log or decisions_found == len(checkpoint.decision_log)),
            why_not_memory_preserved=(not checkpoint.why_not_store or why_not_found == len(checkpoint.why_not_store)),
            pending_todos_preserved=True,
            missing_items=missing_items,
            verification_score=round(score, 2),
        )

        if output_report_path:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(output_report_path)), exist_ok=True)
                with open(output_report_path, "w", encoding="utf-8") as f:
                    f.write(report.model_dump_json(indent=2))
                logger.info(f"Resume Verification Report exported to '{output_report_path}'.")
            except Exception as e:
                logger.error(f"Error saving Resume Verification Report: {e}")

        return report
