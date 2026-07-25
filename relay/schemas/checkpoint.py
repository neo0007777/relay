"""
Pydantic Data Contracts for Relay Knowledge Checkpoints and Handoff State.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WhyNotItem(BaseModel):
    """
    Catalog record of a rejected approach, failed hypothesis, or dead end.
    Prevents resumed agents from retrying failed code edits or invalid paths.
    """

    approach_id: str = Field(description="Unique identifier for the rejected approach")
    attempted_idea: str = Field(description="High-level description of what approach was attempted")
    rationale_rejected: str = Field(description="Why this approach failed or was rejected")
    error_traceback: Optional[str] = Field(default=None, description="Exact error output or failure message if applicable")
    files_involved: List[str] = Field(default_factory=list, description="Files modified or tested in this failed attempt")
    timestamp: datetime = Field(default_factory=datetime.now)


class DecisionItem(BaseModel):
    """Structured rationale for an architectural or code decision made by the agent."""

    decision_id: str = Field(description="Unique decision ID")
    choice_made: str = Field(description="What specific architectural/code choice was selected")
    alternatives_considered: List[str] = Field(default_factory=list, description="Other options considered")
    justification: str = Field(description="Why this choice was selected over alternatives")
    files_affected: List[str] = Field(default_factory=list)


class ASTNodeChange(BaseModel):
    """Structural change in code AST between session start and checkpoint."""

    file_path: str = Field(description="File containing AST change")
    symbol_name: str = Field(description="Class, function, or method name modified")
    symbol_type: str = Field(description="function, class, async_function, method")
    change_type: str = Field(description="added, modified, removed")
    signature: Optional[str] = Field(default=None, description="Function/method signature string")


class FileDiffSummary(BaseModel):
    """Git diff patch and change metrics for a modified file."""

    file_path: str = Field(description="Relative path of file")
    status: str = Field(description="modified, added, deleted, renamed")
    additions: int = Field(default=0, description="Lines added")
    deletions: int = Field(default=0, description="Lines deleted")
    patch_summary: str = Field(description="Truncated git diff patch snippet")


class RetrievedChunk(BaseModel):
    """Context chunk retrieved via hybrid (vector + graph + recency) search."""

    chunk_id: str = Field(description="Unique chunk identifier")
    file_path: str = Field(description="Source file path")
    content: str = Field(description="Code or documentation chunk text")
    score: float = Field(description="Combined relevance score [0.0, 1.0]")
    retrieval_source: str = Field(description="Source signal: vector, graph_dependency, git_recency, ast_coupling")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeCheckpoint(BaseModel):
    """
    Complete Relay Knowledge Checkpoint schema.
    Encapsulates knowledge, reasoning state, dead ends, AST deltas, and retrieved context.
    """

    checkpoint_id: str = Field(description="Unique checkpoint UUID")
    session_id: str = Field(description="Original agent session ID")
    task_goal: str = Field(description="Primary user task goal")
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Progress & State
    narrative_progress: str = Field(description="High-level summary of work accomplished so far")
    pending_todos: List[str] = Field(default_factory=list, description="Remaining tasks or steps")
    
    # Reasoning & Dead-End Memory
    decision_log: List[DecisionItem] = Field(default_factory=list, description="Log of choices made")
    why_not_store: List[WhyNotItem] = Field(default_factory=list, description="Catalog of rejected approaches and dead ends")
    
    # Structural Code State
    file_diffs: List[FileDiffSummary] = Field(default_factory=list, description="Git diff summaries")
    ast_changes: List[ASTNodeChange] = Field(default_factory=list, description="AST symbol level changes")
    dependency_graph: Dict[str, List[str]] = Field(default_factory=dict, description="Touched file dependency graph mapping")
    
    # Execution & Retrieved Context
    important_tool_outputs: List[str] = Field(default_factory=list, description="Key tool outputs/logs retained")
    retrieved_context: List[RetrievedChunk] = Field(default_factory=list, description="Chunks populated during handoff")
    
    # Usage Stats
    tokens_at_checkpoint: int = Field(default=0)
    context_limit: int = Field(default=128000)
