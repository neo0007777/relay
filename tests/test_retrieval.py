"""
Unit tests for Relay Hybrid Retrieval Engine (Phase 2).
"""

import pytest
from relay.schemas.checkpoint import KnowledgeCheckpoint, FileDiffSummary, ASTNodeChange, RetrievedChunk
from relay.retrieval.vector_store import QdrantVectorStore, FeatureHashEmbedder
from relay.retrieval.graph_retriever import GraphContextRetriever
from relay.retrieval.hybrid_reranker import HybridReranker


def test_feature_hash_embedder():
    embedder = FeatureHashEmbedder(dimension=64)
    vec1 = embedder.embed_text("authentication login jwt token")
    vec2 = embedder.embed_text("authentication login jwt token")
    vec3 = embedder.embed_text("database sql postgres query")

    assert len(vec1) == 64
    assert vec1 == vec2  # Deterministic
    assert vec1 != vec3  # Different tokens


def test_qdrant_vector_store():
    store = QdrantVectorStore(in_memory=True, dimension=384)

    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            file_path="src/auth.py",
            content="def authenticate_user(username, password): return True",
            score=1.0,
            retrieval_source="raw"
        ),
        RetrievedChunk(
            chunk_id="c2",
            file_path="src/db.py",
            content="class DatabaseConnection: def connect(self): pass",
            score=1.0,
            retrieval_source="raw"
        ),
    ]

    count = store.upsert_chunks(chunks)
    assert count == 2

    # Search for auth
    results = store.search_similar("authenticate user username", top_k=2)
    assert len(results) > 0
    assert results[0].file_path == "src/auth.py"


def test_graph_context_retriever():
    retriever = GraphContextRetriever()

    dep_graph = {
        "src/main.py": ["src/auth.py", "src/db.py"],
        "src/auth.py": ["src/tokens.py"],
        "src/db.py": ["src/models.py"],
    }

    distances = retriever.compute_file_distances(dep_graph, active_files=["src/main.py"])

    assert distances["src/main.py"] == 0
    assert distances["src/auth.py"] == 1
    assert distances["src/db.py"] == 1
    assert distances["src/tokens.py"] == 2

    assert retriever.score_graph_relevance("src/main.py", distances) == 1.0
    assert retriever.score_graph_relevance("src/auth.py", distances) == 0.75
    assert retriever.score_graph_relevance("src/tokens.py", distances) == 0.40
    assert retriever.score_graph_relevance("src/unrelated.py", distances) == 0.0


def test_hybrid_reranker():
    store = QdrantVectorStore(in_memory=True, dimension=64)
    retriever = GraphContextRetriever()
    reranker = HybridReranker(vector_store=store, graph_retriever=retriever)

    # Index sample chunks
    chunks = [
        RetrievedChunk(chunk_id="ch-auth", file_path="src/auth.py", content="JWT token validation logic", score=0.9, retrieval_source="vec"),
        RetrievedChunk(chunk_id="ch-db", file_path="src/db.py", content="Postgres pool connector", score=0.8, retrieval_source="vec"),
        RetrievedChunk(chunk_id="ch-util", file_path="src/utils.py", content="String helper functions", score=0.4, retrieval_source="vec"),
    ]
    store.upsert_chunks(chunks)

    # Checkpoint with active edit on src/auth.py
    checkpoint = KnowledgeCheckpoint(
        checkpoint_id="chk-test",
        session_id="sess-test",
        task_goal="Fix JWT authentication bug",
        narrative_progress="Editing auth.py",
        file_diffs=[FileDiffSummary(file_path="src/auth.py", status="modified", additions=10, deletions=2, patch_summary="diff")],
        ast_changes=[ASTNodeChange(file_path="src/auth.py", symbol_name="verify_jwt", symbol_type="function", change_type="modified")],
        dependency_graph={"src/auth.py": ["src/tokens.py"]}
    )

    reranked = reranker.retrieve_hybrid_context(
        query="JWT authentication verify_jwt token",
        checkpoint=checkpoint,
        top_k=3,
        candidate_chunks=chunks
    )

    assert len(reranked) == 3
    # src/auth.py must rank #1 due to combined vector + recency + AST score
    assert reranked[0].file_path == "src/auth.py"
    assert reranked[0].score > reranked[1].score
    assert "vector_score" in reranked[0].metadata


def test_custom_embedder_injection():
    from relay.retrieval.vector_store import BaseEmbedder, QdrantVectorStore

    class MockConstantEmbedder(BaseEmbedder):
        def embed_text(self, text: str):
            return [0.5] * 64

    custom_embedder = MockConstantEmbedder()
    store = QdrantVectorStore(in_memory=True, dimension=64, embedder=custom_embedder)
    assert store.embedder is custom_embedder
    vec = store.embedder.embed_text("sample")
    assert vec == [0.5] * 64
