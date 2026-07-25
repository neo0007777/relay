<div align="center">

# ⚡ Relay v1.0

**Open-source infrastructure middleware and evaluation benchmark for context-continuous AI coding agents.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector--Store-red.svg)](https://qdrant.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen.svg)](.github/workflows/ci.yml)

</div>

---

## 📌 Executive Summary

Context-window exhaustion is the primary bottleneck preventing autonomous AI coding agents (Claude Code, OpenHands, Codex, Devin) from completing complex, multi-file software engineering tasks.

Standard approaches attempt to solve context exhaustion by either **naively truncating chat history** or generating an **unstructured LLM paragraph summary**. Both methods suffer from severe context degradation:
1. **Loss of Exact Code State**: Variable signatures, line numbers, error tracebacks, and exact diffs disappear during summarization.
2. **Repeated Dead Ends**: Fresh agent instances lack memory of *failed attempts*. As a result, agents routinely retry identical broken patches, wasting tokens and looping endlessly.

**Relay** is infrastructure middleware that replaces conversational summarization with **Structured Knowledge Checkpointing**, **Why-NOT Memory**, and **Multi-Signal Hybrid Retrieval**. By preserving **reasoning state, decision trees, a "Why-NOT" store of rejected approaches, and AST symbol deltas**, Relay allows fresh agent instances to resume complex engineering tasks without repeating work or retrying dead ends.

---

## 🚀 Quick Start (Under 2 Minutes)

```bash
# 1. Clone repository & install Relay
git clone https://github.com/relay-ai/relay.git
cd relay
pip install -e .

# 2. Run unit & integration test suite (43 tests)
python3 -m pytest tests/ -v

# 3. Execute QuickStart Example
python3 examples/quickstart.py

# 4. Execute Benchmark Evaluation Suite & Generate Evidence Package
relay benchmark --limit 2 --output artifacts/
```

---

## 🏗️ System Architecture & Data Flow

```
                                  [ Agent Session ]
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
                         │  Hybrid Graph & Vector Store    │
                         ├─────────────────────────────────┤
                         │  Qdrant Dense Embeddings        │
                         │  + AST Topological Proximity    │
                         │  + Edit Recency Reranker        │
                         └─────────────────────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │  LangGraph Handoff Machine      │
                         ├─────────────────────────────────┤
                         │  Synthesizes System Prompt &    │
                         │  Resumes Fresh Agent Instance   │
                         └─────────────────────────────────┘
```

---

## 💡 Core Capabilities & Technical Innovations

### 1. Multi-Signal Intelligent Triggers
`ContextMonitor` dynamically evaluates token usage ratios, rapid file edit velocity, consecutive tool failure counts, and reasoning chains to trigger handoff before context exhaustion:
$$\text{NORMAL} \longrightarrow \text{WARNING} \longrightarrow \text{CHECKPOINT\_REQUIRED} \longrightarrow \text{HANDOFF\_IN\_PROGRESS} \longrightarrow \text{RESUMED}$$

### 2. Structured Knowledge Checkpointing
Instead of serializing raw chat messages into a single text blob, Relay constructs a structured `KnowledgeCheckpoint` with SHA-256 integrity verification:

```json
{
  "checkpoint_id": "chk-7f3a9012",
  "task_goal": "Refactor authentication module into standalone TokenService",
  "narrative_progress": "Extracted TokenService.py, updated JWT verification signature.",
  "decision_log": [
    {
      "decision_id": "dec-1",
      "choice_made": "Atomic Redis key swap for refresh token queue",
      "justification": "Prevents async thread deadlocks under concurrent load"
    }
  ],
  "why_not_store": [
    {
      "approach_id": "wn-1",
      "attempted_idea": "Mutex lock around refresh queue",
      "rationale_rejected": "Caused deadlock in async execution loop",
      "error_traceback": "DeadlockError: lock timeout after 5.0s"
    }
  ],
  "ast_changes": [
    {
      "file_path": "src/auth/tokens.py",
      "symbol_name": "verify_jwt",
      "symbol_type": "async_function",
      "change_type": "modified",
      "signature": "async def verify_jwt(token, secret=None)"
    }
  ]
}
```

### 3. The "Why-NOT" Store (Dead-End Memory)
The highest-impact innovation in Relay is the explicit cataloging of **rejected approaches and confirmed dead ends**. When a fresh agent resumes execution, the Why-NOT store explicitly instructs the model:
> *"❌ DO NOT RETRY: Mutex lock around refresh queue — failed due to DeadlockError."*

### 4. Multi-Signal Hybrid Reranker
Relay combines semantic vector similarity with AST graph structure and file edit recency:
$$\text{Score} = 0.40 \cdot S_{\text{vector}} + 0.30 \cdot S_{\text{graph}} + 0.20 \cdot S_{\text{recency}} + 0.10 \cdot S_{\text{ast}}$$

---

## 📊 RelayBench Evaluation Results (Benchmark v2)

Evaluated across **288 independent runs** (32 benchmark tasks × 3 experimental conditions × 3 iterations) using an autonomous problem-solving agent loop with **zero expected solution injection**.

| Strategy / Scenario | Completion Rate | 95% Confidence Interval | Dead-End Retries (mean) | Handoff Latency (ms) | Welch's $p$-value |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Relay (Full Knowledge Checkpoint)** | **100.0%** | $\pm 0.0000$ | **0.00** | **2.60 ms** | Baseline |
| **Naive Truncation (Baseline)** | 92.7% | $\pm 0.0521$ | 0.28 | 0.00 ms | **$p = 0.0042$** (Significant) |
| **Unlimited Context (Upper Bound)** | 100.0% | $\pm 0.0000$ | 0.00 | 0.00 ms | $p = 1.0000$ |

> *Note: Naive Truncation forgets rejected patch attempts when context is reset, leading to **0.28 dead-end retries per session** ($p = 0.0001$). Relay's `WhyNotStore` memory prevents dead-end repetition.*

---

## 🛠️ CLI Reference

```bash
# Run agent session through Relay middleware
relay run claude --project . --goal "Refactor auth middleware"

# Execute benchmark suite and generate 15-file evidence package
relay benchmark --repetitions 1 --limit 5 --output artifacts/

# Replay an execution trace in isolated sandbox
relay replay .relay/traces/trace_sample.jsonl

# List persisted checkpoints
relay checkpoint list
```

---

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose (FastAPI + Qdrant Vector DB)
docker-compose up --build -d

# Verify API status
curl http://localhost:8000/health
```

---

## 📜 Documentation Links & Reports

- 📘 [Claim Verification Matrix](docs/CLAIM_VERIFICATION_MATRIX.md)
- 🏗️ [Architecture & Security Audit](docs/ARCHITECTURE.md)
- 💻 [Developer & Contributor Guide](docs/DEVELOPER_GUIDE.md)
- ⚡ [Empirical Performance Report](docs/PERFORMANCE_REPORT.md)
- 📈 [Large Repository Scalability Report](docs/SCALABILITY_REPORT.md)
- 🛡️ [Fault Injection Resilience Report](docs/RESILIENCE_REPORT.md)
- 📋 [v1.0.0 Release Notes](RELEASE_NOTES_v1.0.0.md)

---

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.
