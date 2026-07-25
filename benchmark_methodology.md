# RelayBench: Research Methodology & Benchmark Specification (Sprint 2)

## Abstract

This document presents the complete research architecture, dataset taxonomy, sandbox trace replay engine, mathematical metric formulations, statistical confidence framework, and ablation matrix of **RelayBench** (v0.3.0). RelayBench is a production-grade benchmark framework executing real software engineering tasks across **32 standardized task packages** in 10 categories.

---

## 1. Task Taxonomy & Dataset Architecture (32 Tasks)

RelayBench tasks are organized under `relay/benchmark/datasets/` into 10 categories. Each task package contains:
- `task.yaml`: Metadata, difficulty, target files manifest, test script path.
- `problem.md`: Detailed engineering problem specification.
- `repository/`: Initial runnable codebase directory.
- `tests/`: Executable `pytest` unit & integration test files.
- `expected_outputs/`: Reference solution patch/code.
- `metadata.json`: Machine-readable metadata.

### Dataset Category Taxonomy

| Category | Task ID | Task Title | Difficulty | Target Files Manifest |
| :--- | :--- | :--- | :---: | :--- |
| **Authentication** | `auth-jwt-refresh` | JWT Token Refresh Bug | Medium | `src/auth/jwt.py` |
| **Authentication** | `auth-oauth-callback` | OAuth Callback Validation | Medium | `src/auth/oauth.py` |
| **Authentication** | `auth-password-hash` | Argon2 Password Migration | Medium | `src/auth/crypto.py` |
| **Authentication** | `auth-mfa-totp` | MFA TOTP Verification | Hard | `src/auth/mfa.py` |
| **Backend** | `backend-fastapi-bug` | FastAPI Router Path Parameter Fix | Easy | `src/backend/router.py` |
| **Backend** | `backend-flask-endpoint` | Flask CORS Response Header Fix | Easy | `src/backend/flask_app.py` |
| **Backend** | `backend-rest-refactor` | REST Payload Validation Refactor | Medium | `src/backend/validator.py` |
| **Backend** | `backend-gunicorn-worker` | Gunicorn Worker Timeout Fix | Easy | `src/backend/gunicorn_conf.py` |
| **Database** | `database-sqlite-migration` | Async SQLite Migration Script | Medium | `src/db/migrations.py` |
| **Database** | `database-postgres-pool` | Postgres Pool Connection Leak Fix | Hard | `src/db/pool.py` |
| **Database** | `database-orm-query` | SQLAlchemy N+1 Query Fix | Hard | `src/db/queries.py` |
| **Frontend** | `frontend-react-state` | React State Synchronization Bug | Medium | `src/frontend/state.js` |
| **Frontend** | `frontend-next-hydration` | Next.js SSR Hydration Error | Hard | `src/frontend/hydration.js` |
| **Frontend** | `frontend-css-regression` | CSS Grid Layout Alignment Fix | Easy | `src/frontend/styles.css` |
| **Testing** | `testing-broken-fixture` | Pytest Fixture Teardown Fix | Easy | `tests/fixtures.py` |
| **Testing** | `testing-missing-integration` | Stripe Webhook Integration Test | Medium | `src/payments/stripe.py` |
| **Testing** | `testing-mocking-failure` | Unmocked HTTP Client Call Fix | Easy | `src/client/http.py` |
| **Debugging** | `debugging-memory-leak` | Background Queue Memory Leak | Hard | `src/debug/worker.py` |
| **Debugging** | `debugging-infinite-loop` | Graph Traversal Cycle Fix | Hard | `src/debug/graph.py` |
| **Debugging** | `debugging-race-condition` | Lock Manager Race Condition | Hard | `src/debug/lock.py` |
| **Refactoring** | `refactoring-class-extract` | Extract NotificationService | Medium | `src/refactor/user.py` |
| **Refactoring** | `refactoring-dependency-inversion` | Apply Dependency Inversion | Medium | `src/refactor/repo.py` |
| **Refactoring** | `refactoring-type-hints` | PEP 484 Type Annotations | Easy | `src/refactor/types.py` |
| **API** | `api-graphql-resolver` | GraphQL Resolver Field Fix | Medium | `src/api/graphql.py` |
| **API** | `api-rate-limiter` | Sliding Window Rate Limiter | Hard | `src/api/limiter.py` |
| **API** | `api-webhook-verifier` | HMAC SHA-256 Webhook Verifier | Medium | `src/api/webhook.py` |
| **Concurrency** | `concurrency-asyncio-deadlock` | Asyncio Lock Timeout Fix | Hard | `src/concurrency/async_queue.py` |
| **Concurrency** | `concurrency-threadpool-leak` | ThreadPoolExecutor Shutdown Leak | Hard | `src/concurrency/pool.py` |
| **Concurrency** | `concurrency-atomic-cas` | Atomic CAS Counter Fix | Medium | `src/concurrency/atomic.py` |
| **Memory** | `memory-unclosed-fd` | Unclosed File Descriptor Leak | Medium | `src/memory/reader.py` |
| **Memory** | `memory-streaming-payload` | Streaming Chunked Reader Fix | Hard | `src/memory/stream.py` |
| **Memory** | `memory-gc-retention` | Circular Reference GC Fix | Hard | `src/memory/tree.py` |

---

## 2. Sandbox Execution & Trace Replay Engine

Benchmark tasks are executed in isolated temporary OS directories (`tempfile.TemporaryDirectory`).

```
 [ BenchmarkRunner ] ──► [ DatasetLoader ] ──► Loads 32 Task Packages
         │
         ▼ (for each task & repetition N)
 ┌──────────────────────────────────────────────┐
 │ Temporary OS Sandbox (tempfile.TempDirectory) │
 ├──────────────────────────────────────────────┤
 │ 1. Materialize initial codebase & tests      │
 │ 2. Replay trace steps & file modifications   │
 │ 3. Intercept context limits & run LangGraph  │
 │ 4. Execute `pytest` via subprocess           │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
 ┌──────────────────────────────────────────────┐
 │ Derive Objective Derived Metrics              │
 ├──────────────────────────────────────────────┤
 │ Completion Rate, Precision, Recall,          │
 │ Repeated Work, Dead Ends, Latency, Duration  │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
 Exports: .relay/benchmark_results.json & benchmark_results.csv
```

---

## 3. 100% Derived Objective Metrics

RelayBench contains **zero hardcoded values**. All reported metrics are derived mathematically from actual execution:

1. **Task Completion Rate ($CR$)**:
   $$CR = \frac{T_{\text{passed}}}{T_{\text{total}}}$$
2. **Ground-Truth Retrieval Precision ($P$) & Recall ($R$)**:
   $$P = \frac{|\{c \in C_{\text{retrieved}} \mid c.\text{file\_path} \in F_{\text{target}}\}|}{|C_{\text{retrieved}}|}, \quad R = \frac{|\{c.\text{file\_path} \in F_{\text{target}} \mid c \in C_{\text{retrieved}}\}|}{|F_{\text{target}}|}$$
3. **Repeated Edits Count ($W_{\text{dup}}$)**: Exact matching of $(\text{path}, \text{hash}(\text{content}))$ pairs across file edits.
4. **Dead-End Retries ($D_{\text{retry}}$)**: Tool steps re-attempting keywords or file paths cataloged in `why_not_store`.
5. **Composite Continuity Score ($S_{\text{cont}}$)**:
   $$S_{\text{cont}} = \text{clamp}\Big(0.50 \cdot CR + 0.50 \cdot P - 0.20 \cdot \min(1.0, W_{\text{dup}} \cdot 0.08) - 0.25 \cdot \min(1.0, D_{\text{retry}} \cdot 0.12), 0.0, 1.0\Big)$$

---

## 4. Statistical Confidence Framework

Every evaluation runs for $N$ repetitions (default $N=3$). For every metric distribution $X = \{x_1, \dots, x_N\}$:
- **Sample Mean ($\mu$)**: $\mu = \frac{1}{N} \sum_{i=1}^N x_i$
- **Median**: Middle value of sorted observations.
- **Sample Standard Deviation ($s$)**: $s = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (x_i - \mu)^2}$
- **95% Confidence Interval ($CI_{95}$)**: $CI_{95} = 1.96 \cdot \frac{s}{\sqrt{N}}$

---

## 5. Ablation Study Matrix

| Ablation Name | Why-NOT Memory | AST Analysis | Graph Retrieval | Hybrid Reranker |
| :--- | :---: | :---: | :---: | :---: |
| `relay_full` | ✅ Enabled | ✅ Enabled | ✅ Enabled | ✅ Blended (0.40/0.30/0.20/0.10) |
| `no_why_not` | ❌ Disabled | ✅ Enabled | ✅ Enabled | ✅ Blended |
| `no_ast` | ✅ Enabled | ❌ Disabled | ✅ Enabled | ✅ Blended |
| `no_graph` | ✅ Enabled | ✅ Enabled | ❌ Disabled | ✅ Blended |
| `vector_only` | ✅ Enabled | ❌ Disabled | ❌ Disabled | ❌ Dense Vector Only (1.0) |

---

## 6. Reproducibility Guide

Run full benchmark evaluation across 32 tasks and export reports:

```bash
python3 -c "from relay.benchmark.runner import BenchmarkRunner; runner = BenchmarkRunner(); result = runner.run_full_evaluation(repetitions=3); print(result.relay_summary)"
```

Report files generated:
- `.relay/benchmark_results.json`
- `.relay/benchmark_results.csv`
