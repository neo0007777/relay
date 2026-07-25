#!/usr/bin/env python3
"""
Demo 3: Reproducible Hybrid Retrieval Execution.
Demonstrates: Repository Indexing → Dense Vector Search → AST Graph Search → Hybrid Reranking → Resumed Prompt Synthesis.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from relay.schemas.checkpoint import RetrievedChunk, KnowledgeCheckpoint, WhyNotItem, FileDiffSummary
from relay.retrieval.vector_store import QdrantVectorStore
from relay.retrieval.graph_retriever import GraphContextRetriever
from relay.retrieval.hybrid_reranker import HybridReranker

def run_demo_3():
    print("=" * 70)
    print("⚡ RELAY DEMO 3: Stage-by-Stage Hybrid Retrieval & Reranking")
    print("=" * 70)

    # Step 1: Repository Indexing
    print("\n[Stage 1] Repository Workspace Scanning & Indexing")
    chunks = [
        RetrievedChunk(
            chunk_id="chk-1",
            file_path="src/auth/jwt_verifier.py",
            content="def verify_jwt_rs256(token: str, public_key: str):\n    # RS256 token validation logic\n    pass\n",
            score=1.0,
            retrieval_source="indexed_file"
        ),
        RetrievedChunk(
            chunk_id="chk-2",
            file_path="src/auth/tokens.py",
            content="class TokenService:\n    def refresh_access_token(self, refresh_token: str):\n        pass\n",
            score=1.0,
            retrieval_source="indexed_file"
        ),
        RetrievedChunk(
            chunk_id="chk-3",
            file_path="src/config/settings.py",
            content="class RelaySettings(BaseSettings):\n    jwt_secret: str = 'default'\n",
            score=1.0,
            retrieval_source="indexed_file"
        )
    ]
    print(f"      Indexed {len(chunks)} code chunks across repository.")

    # Step 2: Dense Vector Store Embeddings
    print("\n[Stage 2] Dense Vector Search (Qdrant Client)")
    vstore = QdrantVectorStore()
    vstore.upsert_chunks(chunks)
    vector_results = vstore.search_similar("verify jwt token", top_k=3)
    for r in vector_results:
        print(f"      Vector Match: '{r.file_path}' (Score: {r.score:.3f})")

    # Step 3: AST Dependency Graph Topological Proximity
    print("\n[Stage 3] AST Topological Dependency Graph Distance")
    graph_retriever = GraphContextRetriever()
    dep_graph = {
        "src/auth/tokens.py": ["src/auth/jwt_verifier.py"],
        "src/auth/jwt_verifier.py": ["src/config/settings.py"]
    }
    distances = graph_retriever.compute_file_distances(dep_graph, active_files=["src/auth/tokens.py"])
    print(f"      Graph distances from 'tokens.py': {distances}")

    # Step 4: Multi-Signal Hybrid Reranker
    print("\n[Stage 4] Multi-Signal Hybrid Score Fusion")
    reranker = HybridReranker(vector_store=vstore, graph_retriever=graph_retriever)
    checkpoint = KnowledgeCheckpoint(
        checkpoint_id="chk-hybrid-demo",
        session_id="sess-demo-3",
        task_goal="Refactor JWT verification",
        narrative_progress="Initial verification logic drafted",
        file_diffs=[FileDiffSummary(file_path="src/auth/jwt_verifier.py", status="modified", additions=5, deletions=2, patch_summary="signature update")],
        dependency_graph=dep_graph,
        why_not_store=[
            WhyNotItem(
                approach_id="wn-1",
                attempted_idea="Symmetric HMAC secret key",
                rationale_rejected="Security violation"
            )
        ]
    )

    reranked_chunks = reranker.retrieve_hybrid_context(
        query="verify jwt token",
        checkpoint=checkpoint,
        top_k=3,
        candidate_chunks=chunks
    )

    print("\n      Hybrid Reranked Context Results:")
    for rank, chunk in enumerate(reranked_chunks, 1):
        print(f"      [{rank}] File: '{chunk.file_path}' | Hybrid Score: {chunk.score:.4f} | Source: {chunk.retrieval_source}")

    # Step 5: Prompt Synthesis
    print("\n[Stage 5] Resumed Agent System Prompt Synthesis")
    top_context = [f"// File: {c.file_path}\n{c.content}" for c in reranked_chunks[:2]]
    print(f"      Synthesized {len(top_context)} context chunks into resumed agent prompt.")

    print("\n✅ DEMO 3 SUCCESS: Stage-by-stage hybrid retrieval complete!")

if __name__ == "__main__":
    run_demo_3()
