"""
Ablation Study Matrix and Configuration Engine for RelayBench.
Enables controlled comparative evaluations with specific Relay components disabled.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from relay.retrieval.hybrid_reranker import HybridReranker
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.handoff.runner import LangGraphHandoffRunner


class AblationConfig(BaseModel):
    """Configuration flags for a specific Relay ablation experiment."""

    name: str = Field(description="Ablation identifier (e.g. relay_full, no_why_not, no_ast, no_graph, vector_only)")
    description: str = Field(description="Human-readable description of what component is disabled")
    enable_why_not: bool = Field(default=True, description="Whether Why-NOT dead-end memory is enabled")
    enable_ast: bool = Field(default=True, description="Whether AST symbol change analysis is enabled")
    enable_graph: bool = Field(default=True, description="Whether AST dependency graph retrieval is enabled")
    enable_hybrid_rerank: bool = Field(default=True, description="Whether multi-signal hybrid reranking is enabled")


# Standardized Ablation Matrix
ABLATION_MATRIX: Dict[str, AblationConfig] = {
    "relay_full": AblationConfig(
        name="relay_full",
        description="Full Relay pipeline with Why-NOT memory, AST analysis, graph retrieval, and hybrid reranking.",
        enable_why_not=True,
        enable_ast=True,
        enable_graph=True,
        enable_hybrid_rerank=True,
    ),
    "no_why_not": AblationConfig(
        name="no_why_not",
        description="Relay with Why-NOT dead-end memory disabled (no cataloging of rejected approaches).",
        enable_why_not=False,
        enable_ast=True,
        enable_graph=True,
        enable_hybrid_rerank=True,
    ),
    "no_ast": AblationConfig(
        name="no_ast",
        description="Relay with Python AST symbol modification analysis disabled.",
        enable_why_not=True,
        enable_ast=False,
        enable_graph=True,
        enable_hybrid_rerank=True,
    ),
    "no_graph": AblationConfig(
        name="no_graph",
        description="Relay with AST dependency graph topological retrieval disabled.",
        enable_why_not=True,
        enable_ast=True,
        enable_graph=False,
        enable_hybrid_rerank=True,
    ),
    "vector_only": AblationConfig(
        name="vector_only",
        description="Relay using dense Qdrant vector retrieval only (graph, recency, and AST signals disabled).",
        enable_why_not=True,
        enable_ast=False,
        enable_graph=False,
        enable_hybrid_rerank=False,
    ),
}


def build_ablation_runner(config: AblationConfig, manager: Optional[CheckpointManager] = None) -> LangGraphHandoffRunner:
    """
    Constructs a LangGraphHandoffRunner configured according to AblationConfig settings.
    """
    # Configure reranker weights based on ablation flags
    w_vec = 1.0 if not config.enable_hybrid_rerank else 0.40
    w_graph = 0.30 if (config.enable_hybrid_rerank and config.enable_graph) else 0.0
    w_recency = 0.20 if config.enable_hybrid_rerank else 0.0
    w_ast = 0.10 if (config.enable_hybrid_rerank and config.enable_ast) else 0.0

    # Normalize weights so they sum to 1.0
    total_w = w_vec + w_graph + w_recency + w_ast
    if total_w > 0:
        w_vec /= total_w
        w_graph /= total_w
        w_recency /= total_w
        w_ast /= total_w

    reranker = HybridReranker(
        w_vector=w_vec,
        w_graph=w_graph,
        w_recency=w_recency,
        w_ast=w_ast
    )

    compressor = KnowledgeCompressor()
    return LangGraphHandoffRunner(compressor=compressor, manager=manager, reranker=reranker)
