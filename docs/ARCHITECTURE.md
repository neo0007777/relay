# Relay Architecture & System Specification

> **Target Audience**: Systems Engineers, AI Researchers, External Open-Source Contributors  
> **Document Version**: v1.0.0

---

## 1. Overview & Problem Statement

Context-window exhaustion is the primary bottleneck preventing autonomous AI coding agents from completing complex, multi-file software engineering tasks. When agent sessions exceed token boundaries (e.g. 128k tokens), traditional systems either **naively truncate chat history** or generate an **unstructured LLM summary**. Both approaches fail because:
1. **Loss of AST & Code State**: Exact variable signatures, AST symbol changes, and line diffs disappear.
2. **Repeated Dead Ends**: Fresh agent instances lack memory of *failed attempts*, causing them to repeatedly retry identical broken patches.

**Relay** solves this by providing **Structured Knowledge Checkpointing**, **Why-NOT Dead-End Memory**, and **Multi-Signal Hybrid Retrieval**.

---

## 2. End-to-End Execution Flow

```
[ Active Agent Session ]
           │
  (Token Usage ≥ 85%)
           │
           ▼
┌─────────────────────────────────┐
│   Context Monitor Interceptor   │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│   Knowledge Checkpoint Engine   │
├─────────────────────────────────┤
│  • Narrative Progress           │
│  • Decision Tree & Rationale    │
│  • "Why-NOT" Dead-End Store     │
│  • Git Diff & AST Symbol Deltas │
│  • Touched Dependency Graph     │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│   Hybrid Graph & Vector Store   │
├─────────────────────────────────┤
│  Qdrant Dense Embeddings        │
│  + AST Topological Proximity    │
│  + Edit Recency Reranker        │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│   LangGraph Handoff Machine     │
├─────────────────────────────────┤
│  Synthesizes System Prompt &    │
│  Resumes Fresh Agent Instance   │
└─────────────────────────────────┘
```

---

## 3. Core Component Responsibilities

### 3.1 Context Monitor Interceptor (`relay/checkpointing/monitor.py`)
- Tracks cumulative token consumption step-by-step.
- Triggers boundary condition when `tokens / limit >= 0.85` (configurable).

### 3.2 Knowledge Compressor & Checkpoint Manager (`relay/checkpointing/`)
- `KnowledgeCompressor`: Serializes active reasoning state into a structured `KnowledgeCheckpoint` schema.
- `CheckpointManager`: Atomic JSON file persistence with path traversal containment protection.

### 3.3 Hybrid Vector & Graph Retriever (`relay/retrieval/`)
- `QdrantVectorStore`: Dense vector embeddings (FeatureHash / OpenAI embeddings) in Qdrant collections.
- `GraphContextRetriever`: BFS topological distance computation across module import graphs.
- `HybridReranker`: Score fusion combining vector, graph, edit recency, and AST node modification signals:
  $$\text{Score} = w_v \cdot S_{\text{vector}} + w_g \cdot S_{\text{graph}} + w_r \cdot S_{\text{recency}} + w_a \cdot S_{\text{ast}}$$

### 3.4 LangGraph Handoff Machine (`relay/handoff/`)
- Orchestrates state machine nodes: `evaluate_boundary` → `create_checkpoint` → `retrieve_context` → `resume_agent`.
- Synthesizes formatted system prompts tailored for `ClaudeCodeAdapter`, `CodexCLIAdapter`, or `OpenHandsAdapter`.

---

## 4. Threat Model & Security Architecture

| Security Domain | Mitigation Mechanism | Implementation Source File | Verification |
|:---|:---|:---|:---:|
| **Path Traversal Protection** | Ensures checkpoint file access is strictly contained within designated `.relay/checkpoints` directory. | [`relay/checkpointing/manager.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/checkpointing/manager.py#L23) | Verified |
| **Sandbox Path Containment** | Prevents trace replay from executing tool actions outside sandbox directory root. | [`relay/benchmark/trace_replay.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/trace_replay.py#L149) | Verified |
| **Explicit CORS Restricting** | Restricts FastAPI REST API origins strictly to local dashboard hosts. | [`relay/api/main.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/api/main.py#L19) | Verified |
