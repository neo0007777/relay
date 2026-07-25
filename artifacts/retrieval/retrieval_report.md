# Relay Hybrid Retrieval Explanation Report

> **Total Chunks Reranked**: `2`

---

## Retrieved Chunk Explanation Breakdown

| Rank | File Path | Vector Score | Graph Score | AST Score | Recency Score | Final Score | Selection Rationale |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | `src/auth/jwt_verifier.py` | 0.50 | 0.75 | 0.00 | 1.00 | **0.9000** | Selected for handoff context via dense vector cosine similarity (0.50), active file modification recency, topological import graph proximity. |
| **2** | `src/config/settings.py` | 0.50 | 0.20 | 0.00 | 0.20 | **0.6600** | Selected for handoff context via dense vector cosine similarity (0.50). |

---

## Scoring Formula & Weights
$$\text{Score} = 0.40 \cdot S_{\text{vector}} + 0.30 \cdot S_{\text{graph}} + 0.20 \cdot S_{\text{recency}} + 0.10 \cdot S_{\text{ast}}$$