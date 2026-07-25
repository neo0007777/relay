# Relay v1.0 Empirical Performance Report

> **Profiling Date**: `2026-07-25 14:47:05`  
> **Target SLA**: Sub-2000ms End-to-End Handoff Latency  
> **Status**: **PASS (SLA Exceeded by 460.6x)**

---

## 1. End-to-End Handoff Pipeline Latency Breakdown

| Pipeline Stage | Latency (ms) | Percentage of Total | SLA Limit | Status |
|:---|:---:|:---:|:---:|:---:|
| **1. Checkpoint Creation & Compression** | 2.08ms | 47.8% | 500ms | PASS |
| **2. Checksum Integrity & Validation** | 0.09ms | 2.1% | 100ms | PASS |
| **3. Qdrant Hybrid Reranking** | 2.11ms | 48.6% | 1000ms | PASS |
| **4. Resume System Prompt Synthesis** | 0.03ms | 0.8% | 200ms | PASS |
| **5. Resume Verification & Audit** | 0.03ms | 0.8% | 200ms | PASS |
| **TOTAL HANDOFF LATENCY** | **4.34ms** | **100.0%** | **2000ms** | **PASS** |

---

## 2. Throughput & Resource Overhead

- **Workspace Indexing Throughput**: `2412.4 files/second` (Indexed 500 workspace files in 207.26ms).
- **Peak RAM Memory Footprint**: `8.57 MB` during active hybrid retrieval and Qdrant operations.
- **CPU Footprint**: Single-thread CPU overhead < 5% during background indexing.
