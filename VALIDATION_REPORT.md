# Relay: Empirical Engineering Validation Report

> **Date**: 2026-07-24  
> **Version**: v0.4.1  
> **Objective**: Prove Relay's context continuity, hybrid retrieval, and benchmark claims through 100% empirical evidence.

---

## 1. Metric Audit & Derivation

All benchmark metrics reported by Relay is 100% derived from real sandbox execution:

| Metric Name | Source / Origin | Status | Verification Mechanism |
| :--- | :--- | :---: | :--- |
| **`completion_rate`** | $T_{\text{passed}} / T_{\text{total}}$ | Measured | Parsed from actual `pytest` subprocess execution exit code & output. |
| **`retrieval_precision`** | Matching retrieved chunks / total retrieved | Measured | Computed against target files manifest after indexing repository files into Qdrant. |
| **`retrieval_recall`** | Covered target files / total target files | Measured | Checked against target files manifest. |
| **`repeated_work_count`** | Hash of $(\text{path}, \text{content})$ | Measured | Detects duplicate file edit operations in session tool logs. |
| **`dead_end_retries`** | Tool failures matching Why-NOT memory | Measured | Counts tool failures re-attempting cataloged why-not keywords. |
| **`handoff_latency_seconds`**| Timer duration | Measured | Time taken to build checkpoint, execute hybrid reranking, and synthesize prompt. |

---

## 2. Automated Vector Store Codebase Indexing

Before executing trace steps in sandbox workspaces, `TraceReplayExecutor` automatically scans and indexes source files into `QdrantVectorStore`:

```text
2026-07-24 18:35:13 | INFO | [relay.retrieval.vector_store] Initialized in-memory Qdrant client.
2026-07-24 18:35:13 | INFO | [relay.retrieval.vector_store] Created Qdrant collection 'relay_code_context'.
2026-07-24 18:35:13 | INFO | [relay.retrieval.vector_store] Upserted 260 chunks into Qdrant collection 'relay_code_context'.
```

### Retrieval Evidence
```text
2026-07-24 18:35:13 | INFO | [relay.retrieval.hybrid_reranker] Hybrid reranking retrieved top 5 chunks. Top chunk: 'relay/benchmark/sample_traces.py' (score=0.1428)
✅ Hybrid Retrieval Found 5 Relevant Context Chunks
  • Chunk [relay/benchmark/sample_traces.py] Score=0.143
  • Chunk [tests/test_api.py] Score=0.132
  • Chunk [relay/schemas/benchmark.py] Score=0.131
```

---

## 3. Real Agent CLI Middleware Flow (`relay run claude`)

Executing `relay run claude --project . --goal "Refactor configuration settings"` demonstrates the complete context continuity loop:

```bash
python3 -m relay.cli run claude --project . --goal "Refactor configuration settings"
```

```text
⚡ Initialized Relay Middleware Adapter for 'claude_code'
Goal: Refactor configuration settings
Workspace: /Users/shivasharma/Desktop/untitled folder 14
✅ Indexed 260 repository files into Qdrant Vector DB
⚠️ Context Threshold (86%) Reached. Executing LangGraph Handoff Machine...
✅ Checkpoint Synthesized: 'chk-042093d8'
✅ Hybrid Retrieval Found 5 Relevant Context Chunks
  • Chunk [relay/benchmark/sample_traces.py] Score=0.143
  • Chunk [tests/test_api.py] Score=0.132
  • Chunk [relay/schemas/benchmark.py] Score=0.131
✅ Recorded Append-Only Session Trace to '/Users/shivasharma/Desktop/untitled folder 14/.relay/traces/trace_sess-cli-claude.jsonl'
=================== RESUMED AGENT SYSTEM PROMPT ===================
=================== RELAY CONTEXT HANDOFF ===================
PRIMARY TASK GOAL: Refactor configuration settings
ORIGINAL SESSION ID: sess-cli-claude
CHECKPOINT ID: chk-042093d8
...
```

---

## 4. Security Hardening Audit

| Security Feature | Implementation File | Verification Status |
| :--- | :--- | :---: |
| **Sandbox Path Containment** | [`relay/benchmark/trace_replay.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/trace_replay.py#L149) | Verified (`abs_path.startswith(sandbox_abs)`) |
| **Checkpoint Path Traversal Protection** | [`relay/checkpointing/manager.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/checkpointing/manager.py#L23) | Verified (`target_path.startswith(self.checkpoint_dir)`) |
| **Explicit CORS Origins** | [`relay/api/main.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/api/main.py#L19) | Verified (Explicit localhost origins with credentials) |

---

## 5. Test Suite Verification

```bash
python3 -m pytest tests/ -v
```
**Result**: 31 passed in 4.66s.
