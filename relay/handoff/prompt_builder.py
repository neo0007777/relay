"""
PromptBuilder Abstraction for Relay Resumed Agent Instances.
Separates system prompt construction, state formatting, and Why-NOT dead-end rendering from state machine orchestration.
"""

from typing import Optional, Any
from relay.schemas.checkpoint import KnowledgeCheckpoint


class PromptBuilder:
    """Constructs structured, contextual system prompts for resumed agent instances."""

    def build(self, checkpoint: KnowledgeCheckpoint, retrieved_context: Optional[Any] = None, agent_type: Optional[str] = None) -> str:
        """Alias for build_resume_prompt."""
        return self.build_resume_prompt(checkpoint)

    def build_resume_prompt(self, checkpoint: KnowledgeCheckpoint) -> str:
        """
        Synthesizes a structured system prompt from a KnowledgeCheckpoint.

        Args:
            checkpoint: KnowledgeCheckpoint object containing narrative progress, Why-NOT dead ends, and retrieved context.

        Returns:
            Formatted prompt string ready for initial agent context injection.
        """
        prompt_lines = [
            "=================== RELAY CONTEXT HANDOFF ===================",
            f"PRIMARY TASK GOAL: {checkpoint.task_goal}",
            f"ORIGINAL SESSION ID: {checkpoint.session_id}",
            f"CHECKPOINT ID: {checkpoint.checkpoint_id}",
            "\n--- NARRATIVE PROGRESS ---",
            checkpoint.narrative_progress,
            "\n--- RECENT DECISIONS MADE ---"
        ]

        if not checkpoint.decision_log:
            prompt_lines.append("None recorded.")
        else:
            for dec in checkpoint.decision_log:
                prompt_lines.append(f"• Decision [{dec.decision_id}]: {dec.choice_made} (Why: {dec.justification})")

        prompt_lines.append("\n--- WHY-NOT STORE (REJECTED APPROACHES & DEAD ENDS - DO NOT RETRY) ---")
        if not checkpoint.why_not_store:
            prompt_lines.append("None recorded.")
        else:
            for wn in checkpoint.why_not_store:
                prompt_lines.append(f"❌ DEAD END [{wn.approach_id}]: Tried '{wn.attempted_idea}' -> Failed because: {wn.rationale_rejected}")
                if wn.error_traceback:
                    prompt_lines.append(f"   Error Traceback: {wn.error_traceback[:150]}")

        prompt_lines.append("\n--- FILE DIFFS & AST CHANGES ---")
        if not checkpoint.file_diffs and not checkpoint.ast_changes:
            prompt_lines.append("No file modifications recorded.")
        else:
            for diff in checkpoint.file_diffs:
                prompt_lines.append(f"• Modified file: {diff.file_path} (+{diff.additions}/-{diff.deletions})")
            for ast in checkpoint.ast_changes:
                prompt_lines.append(f"• AST symbol change in {ast.file_path}: {ast.symbol_name} ({ast.change_type})")

        prompt_lines.append("\n--- RETRIEVED HYBRID CONTEXT ---")
        if not checkpoint.retrieved_context:
            prompt_lines.append("No context chunks retrieved.")
        else:
            for chunk in checkpoint.retrieved_context:
                prompt_lines.append(f"\nFile: {chunk.file_path} (Score: {chunk.score:.2f}, Source: {chunk.retrieval_source})")
                prompt_lines.append(f"```\n{chunk.content[:400]}\n```")

        prompt_lines.append("\n--- PENDING TODO ITEMS ---")
        if not checkpoint.pending_todos:
            prompt_lines.append("• Continue task implementation and verify tests.")
        else:
            for todo in checkpoint.pending_todos:
                prompt_lines.append(f"• {todo}")

        prompt_lines.append("\n=============================================================")
        prompt_lines.append("Instruction: Resume execution from where the previous agent stopped. Do NOT retry any dead ends listed in the Why-NOT store.")

        return "\n".join(prompt_lines)
