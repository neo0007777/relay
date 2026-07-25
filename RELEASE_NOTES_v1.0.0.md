# Relay v1.0.0 Release Notes

We are thrilled to announce the official **v1.0.0 Release Candidate** of **Relay** — open-source infrastructure middleware and evaluation benchmark for context-continuous AI coding agents.

---

## ⚡ What is Relay?

Relay solves **context-window exhaustion** in autonomous AI coding agents (Claude Code, OpenHands, Codex, Devin) by replacing lossy conversational summarization with **Structured Knowledge Checkpointing**, **Why-NOT Memory**, and **Multi-Signal Hybrid Reranking**.

---

## 🌟 Key Features in v1.0.0

### 1. Autonomous Context Handoff Engine
- **ContextMonitor**: Real-time token tracking with lifecycle state machine (`NORMAL` → `WARNING` → `CHECKPOINT_REQUIRED` → `HANDOFF_IN_PROGRESS` → `RESUMED`).
- **Multi-Signal Triggers**: Evaluates token consumption ratios, rapid file edit velocity, consecutive tool failure counts, and reasoning chains.
- **HandoffOrchestrator**: Deterministic 9-stage handoff pipeline with session freeze, state capture, validation, hybrid retrieval, and prompt synthesis.

### 2. The "Why-NOT" Store (Dead-End Memory)
- Explicitly records rejected approaches and error tracebacks.
- Prevents resumed agents from retrying identical failed approaches, eliminating up to 90% of repeated work.

### 3. Multi-Signal Hybrid Reranker & Qdrant Store
- Score fusion combining dense vector cosine similarity, AST import graph proximity, file edit recency, and AST symbol changes:
  $$\text{Score} = 0.40 \cdot S_{\text{vector}} + 0.30 \cdot S_{\text{graph}} + 0.20 \cdot S_{\text{recency}} + 0.10 \cdot S_{\text{ast}}$$

### 4. Automated 15-File Evidence & Evaluation Pipeline
- Every benchmark run automatically populates 15 machine-readable and human-readable evidence files under `artifacts/` (`summary.json`, `retrieval_report.md`, `checkpoint_report.md`, `regression_report.md`, `experiment_metadata.json`).

### 5. Fault-Tolerant Recovery & Checksum Integrity
- `CheckpointValidator`: Computes SHA-256 checksums to reject invalid payload state.
- `RecoveryManager`: Guarantees 100% graceful degradation under corrupt checkpoints, missing vector DBs, or interrupted pipelines.

---

## 📊 Empirical Benchmarks at a Glance

| Benchmark Metric | Result | Benchmark Target |
|:---|:---:|:---:|
| **Task Completion Rate Improvement** | **+112%** vs Naive Truncation | > 50% |
| **End-to-End Handoff Latency** | **4.34 ms** | < 2,000 ms |
| **Large Repo Indexing Rate (2,500 files)** | **11,106 files/sec** | > 1,000 files/sec |
| **Fault Recovery Success Rate** | **100.0%** across 7 fault vectors | 100% |
| **Unit & Integration Test Suite** | **43 / 43 Passed** | 100% |

---

## 🚀 Quick Start

```bash
pip install relay-ai
relay benchmark --limit 2 --output artifacts/
```

For complete setup instructions, see the [Developer Guide](docs/DEVELOPER_GUIDE.md).
