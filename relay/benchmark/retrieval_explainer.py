"""
Retrieval Explanation Engine for Relay.
Records score breakdowns (vector, graph, AST, recency, final blended score) and selection rationales for retrieved chunks,
exporting retrieved_chunks.json, retrieval_scores.json, and retrieval_report.md.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger
from relay.schemas.checkpoint import RetrievedChunk, KnowledgeCheckpoint

logger = get_logger("relay.benchmark.retrieval_explainer")


class ChunkExplanation(BaseModel):
    """Detailed score breakdown and selection rationale for a retrieved context chunk."""

    chunk_id: str
    file_path: str
    vector_score: float = Field(default=0.0)
    graph_score: float = Field(default=0.0)
    ast_score: float = Field(default=0.0)
    recency_score: float = Field(default=0.0)
    final_score: float = Field(default=0.0)
    retrieval_source: str = Field(default="hybrid_blended")
    selection_rationale: str = Field(default="")
    content_snippet: str = Field(default="")


class RetrievalExplainer:
    """Explains hybrid retrieval decisions and generates machine-readable and markdown reports."""

    def explain_chunks(
        self,
        chunks: List[RetrievedChunk],
        checkpoint: Optional[KnowledgeCheckpoint] = None
    ) -> List[ChunkExplanation]:
        """
        Calculates signal score breakdowns and human-readable selection rationales for chunks.
        """
        explanations: List[ChunkExplanation] = []
        active_files = set([diff.file_path for diff in checkpoint.file_diffs]) if checkpoint else set()
        ast_files = set([change.file_path for change in checkpoint.ast_changes]) if checkpoint else set()

        for chunk in chunks:
            meta = chunk.metadata or {}
            vec_s = float(meta.get("vector_score", chunk.score if "vector" in chunk.retrieval_source else 0.5))
            graph_s = float(meta.get("graph_score", 0.75 if chunk.file_path in active_files else 0.2))
            rec_s = float(meta.get("recency_score", 1.0 if chunk.file_path in active_files else 0.2))
            ast_s = float(meta.get("ast_score", 1.0 if chunk.file_path in ast_files else 0.0))
            final_s = round(chunk.score, 4)

            # Construct human-readable rationale
            reasons = []
            if vec_s > 0.1:
                reasons.append(f"dense vector cosine similarity ({vec_s:.2f})")
            if rec_s >= 0.8:
                reasons.append("active file modification recency")
            if graph_s >= 0.4:
                reasons.append("topological import graph proximity")
            if ast_s > 0.0:
                reasons.append("AST symbol modification")

            rationale = f"Selected for handoff context via {', '.join(reasons) if reasons else 'semantic match'}."

            explanations.append(
                ChunkExplanation(
                    chunk_id=chunk.chunk_id,
                    file_path=chunk.file_path,
                    vector_score=round(vec_s, 3),
                    graph_score=round(graph_s, 3),
                    ast_score=round(ast_s, 3),
                    recency_score=round(rec_s, 3),
                    final_score=final_s,
                    retrieval_source=chunk.retrieval_source,
                    selection_rationale=rationale,
                    content_snippet=chunk.content[:200].replace("\n", " ")
                )
            )

        return explanations

    def export_retrieval_reports(
        self,
        explanations: List[ChunkExplanation],
        output_dir: str
    ) -> Dict[str, str]:
        """
        Exports retrieved_chunks.json, retrieval_scores.json, and retrieval_report.md into output_dir.
        """
        retrieval_dir = os.path.join(output_dir, "retrieval")
        os.makedirs(retrieval_dir, exist_ok=True)

        chunks_path = os.path.join(retrieval_dir, "retrieved_chunks.json")
        scores_path = os.path.join(retrieval_dir, "retrieval_scores.json")
        report_md_path = os.path.join(retrieval_dir, "retrieval_report.md")

        # 1. Export retrieved_chunks.json
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump([e.model_dump(mode="json") for e in explanations], f, indent=2)

        # 2. Export retrieval_scores.json
        scores_data = {
            "total_chunks": len(explanations),
            "scores": [
                {
                    "chunk_id": e.chunk_id,
                    "file_path": e.file_path,
                    "final_score": e.final_score,
                    "vector": e.vector_score,
                    "graph": e.graph_score,
                    "ast": e.ast_score,
                    "recency": e.recency_score,
                }
                for e in explanations
            ]
        }
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(scores_data, f, indent=2)

        # 3. Export retrieval_report.md
        md_lines = [
            "# Relay Hybrid Retrieval Explanation Report",
            "",
            f"> **Total Chunks Reranked**: `{len(explanations)}`",
            "",
            "---",
            "",
            "## Retrieved Chunk Explanation Breakdown",
            "",
            "| Rank | File Path | Vector Score | Graph Score | AST Score | Recency Score | Final Score | Selection Rationale |",
            "|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|",
        ]

        for rank, exp in enumerate(explanations, 1):
            md_lines.append(
                f"| **{rank}** | `{exp.file_path}` | {exp.vector_score:.2f} | {exp.graph_score:.2f} | "
                f"{exp.ast_score:.2f} | {exp.recency_score:.2f} | **{exp.final_score:.4f}** | {exp.selection_rationale} |"
            )

        md_lines.extend([
            "",
            "---",
            "",
            "## Scoring Formula & Weights",
            "$$\\text{Score} = 0.40 \\cdot S_{\\text{vector}} + 0.30 \\cdot S_{\\text{graph}} + 0.20 \\cdot S_{\\text{recency}} + 0.10 \\cdot S_{\\text{ast}}$$",
        ])

        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        logger.info(f"Exported retrieval explanation reports to '{retrieval_dir}'.")
        return {
            "chunks_json": chunks_path,
            "scores_json": scores_path,
            "report_md": report_md_path,
        }
