"""
Fault-Tolerant Recovery Engine for Relay Autonomous Handoff.
Provides graceful degradation and fallback handlers for corrupted checkpoints, missing workspace files,
Qdrant/vector store outages, and partial resume failures.
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.schemas.checkpoint import KnowledgeCheckpoint, RetrievedChunk, FileDiffSummary

logger = get_logger("relay.handoff.recovery")


class RecoveryManager:
    """Provides fallback mechanisms to guarantee handoff continuity even under catastrophic errors."""

    def recover_corrupted_checkpoint(
        self,
        raw_data: Optional[str],
        session_state: AgentSessionState
    ) -> KnowledgeCheckpoint:
        """
        Recovers from corrupted checkpoint JSON or deserialization failure by constructing
        a minimal valid KnowledgeCheckpoint from session_state.
        """
        logger.warning(f"Executing Recovery: Corrupted checkpoint detected for session '{session_state.session_id}'.")
        
        recovered_id = f"chk-recovered-{uuid.uuid4().hex[:8]}"
        return KnowledgeCheckpoint(
            checkpoint_id=recovered_id,
            session_id=session_state.session_id,
            task_goal=session_state.task_goal or "Recovered Software Engineering Task Goal",
            created_at=datetime.now(),
            narrative_progress=f"Recovered checkpoint fallback for session '{session_state.session_id}'.",
            file_diffs=[
                FileDiffSummary(
                    file_path=fpath,
                    status="modified",
                    additions=1,
                    deletions=0,
                    patch_summary="Recovered active file"
                )
                for fpath in session_state.active_files
            ],
            tokens_at_checkpoint=session_state.tokens_consumed,
            context_limit=session_state.token_limit or 128000,
        )

    def recover_missing_files(
        self,
        checkpoint: KnowledgeCheckpoint,
        workspace_dir: str
    ) -> KnowledgeCheckpoint:
        """
        Filters out missing or deleted workspace files from checkpoint file_diffs and ast_changes.
        """
        if not workspace_dir or not os.path.exists(workspace_dir):
            return checkpoint

        abs_dir = os.path.abspath(workspace_dir)
        valid_diffs = []
        for diff in checkpoint.file_diffs:
            if os.path.exists(os.path.join(abs_dir, diff.file_path)):
                valid_diffs.append(diff)
            else:
                logger.warning(f"Recovery: Excluded non-existent diff file '{diff.file_path}' from checkpoint.")

        valid_ast = []
        for change in checkpoint.ast_changes:
            if os.path.exists(os.path.join(abs_dir, change.file_path)):
                valid_ast.append(change)
            else:
                logger.warning(f"Recovery: Excluded non-existent AST file '{change.file_path}' from checkpoint.")

        checkpoint.file_diffs = valid_diffs
        checkpoint.ast_changes = valid_ast
        return checkpoint

    def recover_retrieval_failure(
        self,
        checkpoint: KnowledgeCheckpoint,
        workspace_dir: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """
        Provides fallback context chunks when Qdrant, embeddings, or vector stores fail.
        Constructs context directly from active file diffs and workspace files.
        """
        logger.warning(f"Executing Recovery: Vector retrieval unavailable for checkpoint '{checkpoint.checkpoint_id}'. Building fallback context.")
        fallback_chunks: List[RetrievedChunk] = []

        for idx, diff in enumerate(checkpoint.file_diffs):
            fallback_chunks.append(
                RetrievedChunk(
                    chunk_id=f"chk-fallback-{idx}",
                    file_path=diff.file_path,
                    content=f"// [RECOVERED FALLBACK CONTEXT]\n// File: {diff.file_path}\n{diff.patch_summary}",
                    score=0.5,
                    retrieval_source="recovery_fallback_diff",
                    metadata={"recovered": True}
                )
            )

        if not fallback_chunks and workspace_dir and os.path.exists(workspace_dir):
            # Attempt to read first available python file in workspace
            for root, _, files in os.walk(workspace_dir):
                for fname in files:
                    if fname.endswith(".py"):
                        rel_path = os.path.relpath(os.path.join(root, fname), workspace_dir)
                        try:
                            with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                                content = f.read(1000)
                            fallback_chunks.append(
                                RetrievedChunk(
                                    chunk_id="chk-fallback-workspace",
                                    file_path=rel_path,
                                    content=content,
                                    score=0.4,
                                    retrieval_source="recovery_fallback_workspace",
                                    metadata={"recovered": True}
                                )
                            )
                            break
                        except Exception:
                            pass
                if fallback_chunks:
                    break

        return fallback_chunks

    def recover_partial_resume(
        self,
        session_state: AgentSessionState,
        exception: Exception
    ) -> str:
        """
        Constructs a minimal safe resumed agent system prompt when handoff pipeline fails partially.
        """
        logger.error(f"Executing Recovery: Partial resume failure for session '{session_state.session_id}': {exception}")
        return (
            f"=================== RELAY CONTEXT HANDOFF (EMERGENCY RECOVERY) ===================\n"
            f"PRIMARY TASK GOAL: {session_state.task_goal}\n"
            f"ORIGINAL SESSION ID: {session_state.session_id}\n\n"
            f"--- EMERGENCY RECOVERY NOTICE ---\n"
            f"Handoff engine encountered an exception: {str(exception)}\n"
            f"Active Files: {', '.join(session_state.active_files) if session_state.active_files else 'None'}\n\n"
            f"Instruction: Resume execution carefully. Re-inspect workspace files before proceeding.\n"
            f"=================================================================================="
        )
