"""
FastAPI Routes for Relay Checkpoint Management and Agent Handoff.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from relay.schemas.agent_state import AgentSessionState
from relay.schemas.checkpoint import KnowledgeCheckpoint, WhyNotItem, DecisionItem
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.handoff.runner import LangGraphHandoffRunner, AgentHandoffState

from relay.api.dependencies import (
    get_checkpoint_manager,
    get_knowledge_compressor,
    get_handoff_runner,
)

router = APIRouter(prefix="/api/v1", tags=["Checkpoints & Handoff"])


class CheckpointCreateRequest(BaseModel):
    session_state: AgentSessionState
    why_not_store: List[WhyNotItem] = Field(default_factory=list)
    decision_log: List[DecisionItem] = Field(default_factory=list)


class ResumeHandoffRequest(BaseModel):
    checkpoint_id: str
    query_override: Optional[str] = None


class ResumeHandoffResponse(BaseModel):
    checkpoint_id: str
    session_id: str
    task_goal: str
    resumed_prompt: str
    retrieved_chunk_count: int


@router.post("/checkpoint", response_model=KnowledgeCheckpoint)
def create_checkpoint(
    req: CheckpointCreateRequest,
    compressor: KnowledgeCompressor = Depends(get_knowledge_compressor),
    manager: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Synthesizes and persists a KnowledgeCheckpoint from active agent session state."""
    try:
        chk = compressor.compress_session(
            session_state=req.session_state,
            why_not_store=req.why_not_store,
            decision_log=req.decision_log,
        )
        manager.save_checkpoint(chk)
        return chk
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkpoint: {str(e)}")


@router.post("/resume", response_model=ResumeHandoffResponse)
def execute_resume_handoff(
    req: ResumeHandoffRequest,
    manager: CheckpointManager = Depends(get_checkpoint_manager),
    runner: LangGraphHandoffRunner = Depends(get_handoff_runner),
):
    """Performs hybrid context retrieval and returns the system prompt for agent handoff."""
    chk = manager.load_checkpoint(req.checkpoint_id)
    if not chk:
        raise HTTPException(status_code=404, detail=f"Checkpoint '{req.checkpoint_id}' not found.")

    final_state = runner.resume_from_checkpoint(chk)

    return ResumeHandoffResponse(
        checkpoint_id=chk.checkpoint_id,
        session_id=chk.session_id,
        task_goal=chk.task_goal,
        resumed_prompt=final_state["resumed_prompt"],
        retrieved_chunk_count=len(final_state["retrieved_context"]),
    )


@router.get("/checkpoints", response_model=List[KnowledgeCheckpoint])
def list_checkpoints(
    session_id: Optional[str] = None,
    manager: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Lists saved KnowledgeCheckpoints."""
    return manager.list_checkpoints(session_id=session_id)


@router.get("/checkpoints/{checkpoint_id}", response_model=KnowledgeCheckpoint)
def get_checkpoint(
    checkpoint_id: str,
    manager: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Retrieves a single KnowledgeCheckpoint by ID."""
    chk = manager.load_checkpoint(checkpoint_id)
    if not chk:
        raise HTTPException(status_code=404, detail=f"Checkpoint '{checkpoint_id}' not found.")
    return chk


@router.delete("/checkpoints/{checkpoint_id}")
def delete_checkpoint(
    checkpoint_id: str,
    manager: CheckpointManager = Depends(get_checkpoint_manager),
):
    """Deletes a single KnowledgeCheckpoint by ID."""
    deleted = manager.delete_checkpoint(checkpoint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Checkpoint '{checkpoint_id}' not found or could not be deleted.")
    return {"status": "deleted", "checkpoint_id": checkpoint_id}
