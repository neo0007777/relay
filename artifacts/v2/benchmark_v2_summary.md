# RelayBench Benchmark v2 — Live Agent Evaluation Report

> **Run Date**: `2026-07-26 00:14:17`  
> **Tasks Evaluated**: 32  
> **Iterations per Task**: 3  
> **Total Independent Runs**: 288  
> **Methodology**: Autonomous problem-solving agent loop (ZERO expected solution injection).

---

## Executive Summary & Statistical Findings

- **Relay (Full Knowledge Checkpoint)** achieved a **87.5% completion rate** (95% CI: ±0.0665).
- **Naive Truncation** achieved a **87.5% completion rate** (95% CI: ±0.0665).
- **No-Limit Baseline** achieved a **87.5% completion rate** (95% CI: ±0.0665).
- **Statistical Significance (Relay vs Naive Truncation)**: Welch's t-test $p$-value = `1.0` (Not Significant).
- **Dead-End Retry Reduction**: Relay reduced dead-end retries from `0.00` (Naive) to `0.00` (Relay) ($p$-value = `1.0`).

---

## Comparative Metrics Table

| Metric | Relay (Full) | Naive Truncation | No-Limit Baseline | Significance ($p$-value) |
|:---|:---:|:---:|:---:|:---:|
| **Completion Rate** | **0.8750** ± 0.0665 | 0.8750 ± 0.0665 | 0.8750 ± 0.0665 | $p = 1.0000$ |
| **Dead-End Retries** | **0.0000** | 0.0000 | 0.0000 | $p = 1.0000$ |
| **Repeated Work** | **0.3854** | 0.3750 | 0.3854 | — |
| **Retrieval Precision** | **0.0000** | 0.0000 | 0.0000 | — |
| **Retrieval Recall** | **0.0000** | 0.0000 | 0.0000 | — |
| **Handoff Latency (ms)** | **0.00 ms** | 0.00 ms | 0.00 ms | — |
| **Execution Duration (s)** | **3.628 s** | 3.828 s | 3.598 s | — |

---

## Key Experimental Redesigns in Benchmark v2

1. **Zero Solution Injection**: The agent dynamically parses failing pytest outputs and source code to construct fixes at runtime. No reference solution files are accessed or loaded.
2. **Realistic Naive Baseline**: Naive truncation resets context to the system prompt and goal, removing structured `WhyNotStore` memory and vector retrieval. The agent is forced to problem-solve without prior dead-end knowledge.
3. **Causal Isolation**: The ONLY difference between Relay Full and Naive Truncation is Relay's `KnowledgeCheckpoint` state injection (Why-NOT memory + vector retrieval context).

---

*Results produced autonomously by RelayBench Benchmark v2 Harness.*
