<div align="center">

# ⚡ Relay v1.0

**Context-Handoff Protocol & Infrastructure Middleware for Long-Running AI Coding Agents**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector--Store-red.svg)](https://qdrant.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests: 50/50 Passing](https://img.shields.io/badge/Tests-50%2F50%20Passing-brightgreen.svg)](tests/)
[![Author](https://img.shields.io/badge/Author-neo0007777-purple.svg)](https://github.com/neo0007777)

<br/>

[Quick Start](#-quick-start-under-2-minutes) •
[Architecture](#%EF%B8%8F-system-architecture--data-flow) •
[Features](#-core-capabilities--technical-innovations) •
[Benchmark v2](#-relaybench-evaluation-results-benchmark-v2) •
[CLI & API Reference](#-cli--api-reference) •
[Docker Deployment](#-docker-deployment)

</div>

---

## 📌 Executive Summary

Long-running autonomous AI coding agents (Claude Code, OpenHands, Codex CLI, Aider, Devin-style systems) hit a fundamental physical limit: **context window exhaustion**. As an agent reads multi-file repositories, runs tests, inspects tracebacks, and executes tool calls, its context window fills rapidly.

Existing systems resort to two crude recovery strategies when context limit is approached:
1. **Truncation**: Blindly dropping early chat messages, destroying architectural decisions, variable definitions, and file context.
2. **Unstructured Paragraph Summarization**: Prompting an LLM to "summarize history", which loses precise line numbers, AST symbol signatures, exact git diffs, and failing tracebacks.

Both methods lead to severe failure modes — most notably **Dead-End Loops**, where a fresh agent instance forgets previously rejected hypotheses and endlessly retries the exact same broken patches.

### The Relay Solution

**Relay** is open-source infrastructure middleware that replaces conversational summarization with **Structured Knowledge Checkpointing**, **Why-NOT Memory**, and **Multi-Signal Hybrid Retrieval**.

When context usage reaches a configurable threshold (e.g., 85%), Relay interceptors checkpoint the active session into an immutable `KnowledgeCheckpoint` containing:
- **Narrative Progress**: Structured task goal and step summary.
- **Decision Log**: Key architectural choices made and their rationales.
- **Why-NOT Store**: Explicit memory of *failed hypotheses, rejected patches, and runtime tracebacks*.
- **AST Symbol Deltas**: Class/function definitions modified or created.
- **JIT Context Retrieval**: Hybrid vector (Qdrant) + graph (AST proximity) retrieval of relevant workspace chunks.

Fresh agent instances resume from a synthesized, highly token-efficient system prompt — allowing tasks to continue seamlessly across context boundaries without repeating work or retrying dead ends.

---

## 🚀 Quick Start (Under 2 Minutes)

```bash
# 1. Clone repository & enter directory
git clone https://github.com/neo0007777/relay.git
cd relay

# 2. Install package in editable mode
pip install -e .

# 3. Run complete unit & integration test suite (50/50 passing)
python3 -m pytest tests/ -v

# 4. Run quickstart handoff demo script
python3 scripts/demo_1_context_handoff.py

# 5. Run RelayBench Benchmark v2 suite
python3 scripts/run_benchmark_v2.py --iterations 3
```

---

## 🏗️ System Architecture & Data Flow

```
                                  ┌───────────────────────────┐
                                  │    Active Agent Session   │
                                  └─────────────┬─────────────┘
                                                │
                                       (Token Usage ≥ 85%)
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │   Context Monitor Interceptor   │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │   Knowledge Checkpoint Engine   │
                               ├─────────────────────────────────┤
                               │  • Task Goal & Narrative       │
                               │  • Architectural Decision Tree  │
                               │  • "Why-NOT" Dead-End Memory    │
                               │  • Git Diffs & AST Deltas       │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │  Hybrid Graph & Vector Reranker │
                               ├─────────────────────────────────┤
                               │  • Qdrant Dense Vector Store    │
                               │  • AST Topological Proximity    │
                               │  • Edit Recency Scoring         │
                               └────────────────┬────────────────┘
                                                │
                                                ▼
                               ┌─────────────────────────────────┐
                               │  LangGraph Handoff Orchestrator │
                               ├─────────────────────────────────┤
                               │  Synthesizes System Prompt &    │
                               │  Resumes Fresh Agent Session    │
                               └─────────────────────────────────┘
```

---

## 💡 Core Capabilities & Technical Innovations

### 1. Multi-Signal Intelligent Triggers
`ContextMonitor` continuously evaluates 5 distinct signals to trigger handoffs before catastrophic context overflow:
- **Token Ratio**: Usage vs maximum provider token limit.
- **Edit Velocity**: High frequency of rapid file modifications.
- **Repeated Tool Failures**: Consecutive command exit-code failures.
- **Reasoning Loop Detection**: Long chains of reasoning without state progress.
- **Explicit Trigger**: Programmatic or manual checkpoint boundary.

$$\text{NORMAL} \longrightarrow \text{WARNING} \longrightarrow \text{CHECKPOINT\_REQUIRED} \longrightarrow \text{HANDOFF\_IN\_PROGRESS} \longrightarrow \text{RESUMED}$$

### 2. Structured Knowledge Checkpointing
Relay serializes task state into an atomic, SHA-256 verified `KnowledgeCheckpoint` JSON schema:

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
One of Relay's primary design ideas is the **"Why-NOT" store**, which explicitly records rejected approaches, failed hypotheses, and runtime tracebacks. When a fresh agent resumes execution after handoff, the prompt builder injects negative constraints so the agent avoids repeating known dead ends:

> ❌ **DO NOT RETRY PREVIOUSLY FAILED APPROACHES:**
> - `Mutex lock around refresh queue`: Failed due to `DeadlockError: lock timeout after 5.0s`.

### 4. Multi-Signal Hybrid Reranker
Retrieves relevant code context for the resumed session by scoring chunks across 4 orthogonal dimensions:

$$\text{Score} = 0.40 \cdot S_{\text{vector}} + 0.30 \cdot S_{\text{graph}} + 0.20 \cdot S_{\text{recency}} + 0.10 \cdot S_{\text{ast}}$$

---

## 📊 RelayBench Evaluation Results (Benchmark v2)

RelayBench v2 is an autonomous, live agent evaluation suite spanning **288 independent runs** across 32 tasks and 3 experimental conditions with **zero expected solution injection**:

| Strategy / Scenario | Completion Rate | 95% Confidence Interval | Dead-End Retries (mean) | Handoff Latency (ms) | Welch's $p$-value |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Relay (Full Knowledge Checkpoint)** | **100.0%** | $\pm 0.0000$ | **0.00** | **2.60 ms** | Baseline |
| **Naive Truncation (Baseline)** | 92.7% | $\pm 0.0521$ | 0.28 | 0.00 ms | **$p = 0.0042$** (Significant) |
| **Unlimited Context (Upper Bound)** | 100.0% | $\pm 0.0000$ | 0.00 | 0.00 ms | $p = 1.0000$ |

> **Operational Definition — Dead-End Retry**: A tool step where the agent attempts a patch or code edit matching an approach previously listed in the `WhyNotStore` without introducing new information.
>
> **Statistical Significance**: Computed via Welch's two-sample $t$-test across 288 runs. Raw trace datasets are exported to `artifacts/v2/benchmark_v2_results.csv`.

---

## 🚧 Current Limitations

- **Task Scope**: Currently evaluated on Python repository tasks; multi-language tasks (TypeScript, Go) remain in development.
- **Agent Coverage**: Claude Code CLI adapter currently has the highest test coverage.
- **Context Horizon**: Evaluated up to 128k context budgets; ultra-long horizon sessions (>200k tokens) remain future work.

---

## 🔮 Future Work

- [ ] **SWE-bench Integration**: Evaluate Relay on real SWE-bench Lite repository issues.
- [ ] **OpenHands & Aider Adapter Expansion**: Deepen integration hooks with OpenHands and Aider agent runners.
- [ ] **Multi-Agent Cross-Session Memory**: Persist knowledge checkpoints across distinct agent team roles.
- [ ] **Distributed Checkpoint Storage**: S3/Postgres backends for enterprise cluster agent handoffs.

---

## 🛠️ CLI & API Reference

### CLI Commands

```bash
# Run an agent task through Relay middleware
relay run claude --project . --goal "Refactor database connection pool"

# Execute Benchmark v2 evaluation suite
python3 scripts/run_benchmark_v2.py --iterations 3

# List persisted checkpoints
relay checkpoint list

# Replay an execution trace in sandbox environment
relay replay .relay/traces/trace_sample.jsonl
```

### FastAPI Endpoints

Relay exposes REST APIs for remote agent orchestration:

```bash
# Health Check
curl http://localhost:8000/health

# Trigger Manual Checkpoint
curl -X POST http://localhost:8000/api/v1/checkpoint \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess-123", "task_goal": "Optimize query"}'

# Execute Handoff
curl -X POST http://localhost:8000/api/v1/handoff \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess-123"}'
```

---

## 🐳 Docker Deployment

```bash
# Start Relay API server & Qdrant vector database
docker-compose up --build -d

# Check service container status
docker-compose ps
```

---

## 💻 Frontend Dashboard (Next.js)

Relay includes a modern Next.js + Tailwind visualization web app:

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000 to view handoff timeline & Qdrant retrieval visualizer
```

---

## 📜 Documentation & Verification Reports

- 📘 [Claim Verification Matrix](docs/CLAIM_VERIFICATION_MATRIX.md)
- 🏗️ [Architecture & Security Audit](docs/ARCHITECTURE.md)
- 💻 [Developer & Contributor Guide](docs/DEVELOPER_GUIDE.md)
- ⚡ [Empirical Performance Report](docs/PERFORMANCE_REPORT.md)
- 📈 [Scalability Report](docs/SCALABILITY_REPORT.md)
- 🛡️ [Fault Injection Resilience Report](docs/RESILIENCE_REPORT.md)
- 📋 [v1.0.0 Release Notes](RELEASE_NOTES_v1.0.0.md)
- 📑 [Open Source Final Guide](FINAL_RECOMMENDATION.md)

---

## 👤 Author & Contributor

- **GitHub**: [@neo0007777](https://github.com/neo0007777)
- **Repository**: [https://github.com/neo0007777/relay](https://github.com/neo0007777/relay)

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
