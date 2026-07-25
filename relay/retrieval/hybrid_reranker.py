"""
Multi-Signal Hybrid Reranker for Relay Context Handoff.
Combines Vector Similarity, AST Dependency Proximity, Git Edit Recency, and AST Symbol Changes.
"""

from typing import List, Dict, Any, Optional
from relay.core.config import settings
from relay.core.logger import get_logger
from relay.schemas.checkpoint import KnowledgeCheckpoint, RetrievedChunk
from relay.retrieval.vector_store import QdrantVectorStore
from relay.retrieval.graph_retriever import GraphContextRetriever

logger = get_logger("relay.retrieval.hybrid_reranker")


class HybridReranker:
    """
    Reranks candidate context chunks by blending semantic, structural graph, and edit-recency signals.
    """

    def __init__(
        self,
        vector_store: Optional[QdrantVectorStore] = None,
        graph_retriever: Optional[GraphContextRetriever] = None,
        w_vector: float = 0.40,
        w_graph: float = 0.30,
        w_recency: float = 0.20,
        w_ast: float = 0.10,
    ):
        self.vector_store = vector_store or QdrantVectorStore()
        self.graph_retriever = graph_retriever or GraphContextRetriever()

        # Signal Weights (sum = 1.0)
        self.w_vector = w_vector
        self.w_graph = w_graph
        self.w_recency = w_recency
        self.w_ast = w_ast

    def retrieve_hybrid_context(
        self,
        query: str,
        checkpoint: KnowledgeCheckpoint,
        top_k: int = settings.TOP_K_RETRIEVAL,
        candidate_chunks: Optional[List[RetrievedChunk]] = None,
    ) -> List[RetrievedChunk]:
        """
        Executes hybrid retrieval and multi-signal reranking for agent handoff.

        Returns:
            Top-K reranked RetrievedChunk objects.
        """
        # 1. Fetch vector candidates if not provided
        if candidate_chunks is None:
            candidate_chunks = self.vector_store.search_similar(query=query, top_k=top_k * 3)

        if not candidate_chunks:
            logger.info("No candidate chunks available for hybrid reranking.")
            return []

        # 2. Compute AST Graph distances from modified files
        active_files = [diff.file_path for diff in checkpoint.file_diffs]
        graph_distances = self.graph_retriever.compute_file_distances(
            dependency_graph=checkpoint.dependency_graph,
            active_files=active_files
        )

        # 3. Identify modified AST symbols
        modified_ast_files = {change.file_path for change in checkpoint.ast_changes}

        reranked: List[RetrievedChunk] = []

        for chunk in candidate_chunks:
            # Signal 1: Vector score (normalized [0, 1])
            s_vec = max(0.0, min(1.0, chunk.score))

            # Signal 2: Graph proximity score
            s_graph = self.graph_retriever.score_graph_relevance(chunk.file_path, graph_distances)

            # Signal 3: Git edit recency score (1.0 if modified in diffs, 0.0 otherwise)
            s_recency = 1.0 if chunk.file_path in active_files else 0.2

            # Signal 4: AST node modification score (1.0 if AST changed, 0.0 otherwise)
            s_ast = 1.0 if chunk.file_path in modified_ast_files else 0.0

            # Blended final score
            final_score = (
                self.w_vector * s_vec +
                self.w_graph * s_graph +
                self.w_recency * s_recency +
                self.w_ast * s_ast
            )

            reranked.append(RetrievedChunk(
                chunk_id=chunk.chunk_id,
                file_path=chunk.file_path,
                content=chunk.content,
                score=round(final_score, 4),
                retrieval_source="hybrid_blended",
                metadata={
                    "vector_score": round(s_vec, 3),
                    "graph_score": round(s_graph, 3),
                    "recency_score": round(s_recency, 3),
                    "ast_score": round(s_ast, 3),
                }
            ))

        # Sort descending by final score
        reranked.sort(key=lambda c: c.score, reverse=True)
        result = reranked[:top_k]

        logger.info(
            f"Hybrid reranking retrieved top {len(result)} chunks. "
            f"Top chunk: '{result[0].file_path}' (score={result[0].score})"
        )

        return result
