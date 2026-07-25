# Relay Developer & Benchmark Contributor Guide

> **Target Audience**: Core Developers, AI Researchers, Benchmark Contributors  
> **Document Version**: v1.1.0 (Sprint 6 Evidence & Evaluation Specification)

---

## 1. Quick Setup for Development

```bash
# 1. Clone repository
git clone https://github.com/relay-ai/relay.git
cd relay

# 2. Create virtual environment & install dev dependencies
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]

# 3. Verify installation with test suite (43 tests)
python3 -m pytest tests/ -v
```

---

## 2. Evidence & Evaluation Pipeline

Relay automatically generates a **15-file evidence package** on every benchmark execution. Artifacts are written to `artifacts/` without manual editing or synthetic placeholders.

```text
artifacts/
├── benchmark/
│   ├── summary.json          # Complete JSON payload of execution metrics
│   ├── summary.csv           # CSV metrics export for pandas / R analysis
│   └── summary.md            # Executive evaluation markdown summary
├── retrieval/
│   ├── retrieved_chunks.json # Context chunks with score breakdowns
│   ├── retrieval_scores.json # Signal score matrix (vector, graph, AST, recency)
│   └── retrieval_report.md   # Reranking explanation and selection rationale
├── checkpoints/
│   ├── checkpoint_metadata.json # Checkpoint metadata and component counts
│   ├── checkpoint_sizes.json    # Payload sizes (bytes) and compression ratios
│   └── checkpoint_report.md     # Checkpoint performance & payload metrics report
├── traces/
│   └── execution_trace.jsonl    # Deterministic step-by-step execution trace log
├── prompts/
│   └── resume_prompt.txt        # Exact synthesized resumed agent system prompt
└── dashboards/
    ├── benchmark_results.json   # Machine-readable evaluation dashboard results
    ├── benchmark_history.json   # Append-only historical run tracking
    ├── experiment_metadata.json # Git commit, Python, OS platform environment metadata
    └── regression_report.md     # Performance & precision regression detection report
```

---

## 3. Metric Definitions & Derivations

| Metric | Definition | Derivation Source |
|:---|:---|:---|
| **Task Completion Rate** | Percentage of benchmark tasks where all pytest assertions pass. | `tests_passed == tests_total` |
| **Continuity Score** | Preservation ratio of task goals, decisions, and Why-NOT memory in resumed prompt. | `ResumeVerifier` inspection |
| **Dead-End Retries** | Count of repeated failed tool actions previously logged in Why-NOT store. | `TraceReplayExecutor` step diff |
| **Hybrid Rerank Score** | Multi-signal score fusion: $0.40 \cdot S_{\text{vector}} + 0.30 \cdot S_{\text{graph}} + 0.20 \cdot S_{\text{recency}} + 0.10 \cdot S_{\text{ast}}$ | `HybridReranker` calculation |

---

## 4. Evidence Validation Rules & Regression Detection

Every evidence package is validated by `EvidenceValidator`:
1. **Completeness**: All 15 required artifact files must exist.
2. **Integrity**: Files cannot be empty (0 bytes) and JSON files must parse cleanly.
3. **Regression Detection**: `RegressionDetector` compares current run metrics against `benchmark_history.json`. It flags drops in completion rate >5% or increases in dead-end retries as warnings or critical alerts in `regression_report.md`.

To trigger full evidence package generation and validation:
```bash
relay benchmark --limit 2 --output artifacts/
```

---

## 5. Contributing a New Benchmark Task to RelayBench

Benchmark tasks reside in `relay/benchmark/datasets/`. To contribute a new task:

1. Create a task directory under `relay/benchmark/datasets/my_new_task/`.
2. Add `task.yaml`:
```yaml
task_id: "my-new-task"
title: "Fix Memory Leak in Connection Pool"
description: "Detailed problem specification..."
difficulty: "medium"
estimated_steps: 15
target_files:
  - "src/db/pool.py"
```
3. Add initial codebase files in `relay/benchmark/datasets/my_new_task/repository/`.
4. Add pytest test file in `relay/benchmark/datasets/my_new_task/tests/test_task.py`.
5. Verify task loading:
```bash
python3 -c "from relay.benchmark.dataset_loader import DatasetLoader; print(len(DatasetLoader().load_all_tasks()))"
```

---

## 6. Troubleshooting & FAQ

### Q: How do I verify evidence package completeness?
**A**: Run the python evidence validator:
```bash
python3 -c "from relay.benchmark.evidence_validator import EvidenceValidator; EvidenceValidator().validate_package('artifacts/')"
```

### Q: Why is Qdrant running in-memory by default?
**A**: Relay uses `:memory:` Qdrant Client by default for zero-dependency execution in CI and local benchmarking. To connect to a remote Qdrant cluster, set `RELAY_QDRANT_IN_MEMORY=false` and configure `RELAY_QDRANT_HOST`.
