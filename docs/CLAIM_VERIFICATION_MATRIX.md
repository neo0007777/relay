# Relay: Claim Verification Matrix

> **Document Version**: v1.0.0  
> **Target Audience**: Technical Reviewers, OpenAI / Anthropic / Cursor Engineers  
> **Objective**: Map every architectural claim and benchmark metric in Relay to its exact source implementation, test suite, and reproduction command.

---

## 1. System Architecture Claims

| # | System Claim | Implementation Module | Test Suite File | Verification Mechanism | Reproduction Command |
|:-:|:---|:---|:---|:---|:---|
| **1** | **Context Threshold Interceptor**<br>Fires checkpointing when token budget reaches 85%. | [`relay/checkpointing/monitor.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/checkpointing/monitor.py)<br>[`relay/handoff/agent_hooks.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/handoff/agent_hooks.py) | [`tests/test_checkpointing.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_checkpointing.py)<br>[`tests/test_handoff.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_handoff.py) | Mock token consumption; verify threshold triggers exact ratio calculations. | `python3 -m pytest tests/test_checkpointing.py -k test_context_monitor_threshold -v` |
| **2** | **Structured Knowledge Checkpointing**<br>Preserves narrative state, decision tree, Why-NOT memory, and AST changes. | [`relay/schemas/checkpoint.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/schemas/checkpoint.py)<br>[`relay/checkpointing/manager.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/checkpointing/manager.py)<br>[`relay/checkpointing/compressor.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/checkpointing/compressor.py) | [`tests/test_checkpointing.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_checkpointing.py) | Assert atomic JSON serialization, schema validation, and lossy compression rules. | `python3 -m pytest tests/test_checkpointing.py -k test_checkpoint_manager_persistence -v` |
| **3** | **"Why-NOT" Memory Store**<br>Eliminates dead-end retry loops by indexing rejected approaches. | [`relay/schemas/checkpoint.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/schemas/checkpoint.py)<br>[`relay/retrieval/hybrid_reranker.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/retrieval/hybrid_reranker.py)<br>[`relay/handoff/prompt_builder.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/handoff/prompt_builder.py) | [`tests/test_retrieval.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_retrieval.py)<br>[`tests/test_adapters.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_adapters.py) | Verify keyword match boost and system prompt injection of `❌ DO NOT RETRY`. | `python3 -m pytest tests/test_retrieval.py -k test_why_not_memory_boost -v` |
| **4** | **AST & Dependency Graph Analyzer**<br>Extracts structural symbol changes and module proximity graph. | [`relay/checkpointing/git_ast_analyzer.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/checkpointing/git_ast_analyzer.py)<br>[`relay/retrieval/ast_graph.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/retrieval/ast_graph.py) | [`tests/test_checkpointing.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_checkpointing.py)<br>[`tests/test_retrieval.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_retrieval.py) | Parse AST diffs from python files; build topological import graphs. | `python3 -m pytest tests/test_checkpointing.py -k test_git_ast_analyzer_diff -v` |
| **5** | **Multi-Signal Hybrid Reranker**<br>Score = $w_v S_{\text{vector}} + w_g S_{\text{graph}} + w_r S_{\text{recency}} + w_a S_{\text{ast}}$. | [`relay/retrieval/hybrid_reranker.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/retrieval/hybrid_reranker.py) | [`tests/test_retrieval.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_retrieval.py) | Verify scoring formula components across vector, graph distance, recency, and AST. | `python3 -m pytest tests/test_retrieval.py -k test_hybrid_reranker_scoring -v` |
| **6** | **LangGraph Agent Handoff Machine**<br>State machine orchestrating boundary evaluation, checkpointing, and resume prompt. | [`relay/handoff/langgraph_runner.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/handoff/langgraph_runner.py)<br>[`relay/handoff/runner.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/handoff/runner.py) | [`tests/test_handoff.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_handoff.py) | Trace graph state transitions: `evaluate_boundary` → `create_checkpoint` → `resume_agent`. | `python3 -m pytest tests/test_handoff.py -k test_langgraph_handoff_machine_workflow -v` |
| **7** | **Multi-Agent CLI Adapters**<br>Seamless adapters for Claude Code, Codex, and OpenHands agents. | [`relay/adapters/claude_code.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/adapters/claude_code.py)<br>[`relay/adapters/codex.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/adapters/codex.py)<br>[`relay/adapters/openhands.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/adapters/openhands.py) | [`tests/test_adapters.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_adapters.py) | Assert formatted handoff system prompts match agent-specific prompt structure. | `python3 -m pytest tests/test_adapters.py -v` |
| **8** | **FastAPI REST Service**<br>RESTful API for remote agent orchestration and benchmark execution. | [`relay/api/main.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/api/main.py)<br>[`relay/api/routes/checkpoint.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/api/routes/checkpoint.py) | [`tests/test_api.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/tests/test_api.py) | Test `/health`, `/api/v1/checkpoint`, `/api/v1/resume`, and `/api/v1/metrics`. | `python3 -m pytest tests/test_api.py -v` |

---

## 2. RelayBench Metric Derivation & Verification

| Metric Name | Mathematical Definition | Empirical Data Source | Code Location | Reproduction Command |
|:---|:---|:---|:---|:---|
| **`completion_rate`** | $T_{\text{passed}} / T_{\text{total}}$ | Executed pytest exit code in replay sandbox | [`relay/benchmark/metrics.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/metrics.py#L40) | `python3 -m pytest tests/test_benchmark.py -k test_objective_metrics_calculator -v` |
| **`retrieval_precision`** | $\frac{\|C_{\text{retrieved}} \cap C_{\text{target}}\|}{\|C_{\text{retrieved}}\|}$ | Target file manifest comparison | [`relay/benchmark/metrics.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/metrics.py#L65) | `python3 -m pytest tests/test_benchmark.py -k test_objective_metrics_calculator -v` |
| **`retrieval_recall`** | $\frac{\|C_{\text{retrieved}} \cap C_{\text{target}}\|}{\|C_{\text{target}}\|}$ | Target file manifest comparison | [`relay/benchmark/metrics.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/metrics.py#L75) | `python3 -m pytest tests/test_benchmark.py -k test_objective_metrics_calculator -v` |
| **`repeated_work_count`** | Count of duplicate $\text{hash}(\text{file\_path}, \text{action})$ | Tool invocation trace log parser | [`relay/benchmark/metrics.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/metrics.py#L90) | `python3 -m pytest tests/test_benchmark.py -k test_objective_metrics_calculator -v` |
| **`dead_end_retries`** | Count of tool calls matching Why-NOT keywords | Session trace log analyzer | [`relay/benchmark/metrics.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/benchmark/metrics.py#L110) | `python3 -m pytest tests/test_benchmark.py -k test_objective_metrics_calculator -v` |
| **`handoff_latency_seconds`** | $t_{\text{resume}} - t_{\text{checkpoint\_trigger}}$ | Precision nanosecond timer | [`relay/handoff/runner.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/handoff/runner.py#L85) | `python3 -m pytest tests/test_handoff.py -k test_langgraph_handoff_runner -v` |

---

## 3. Independent Verification Execution Commands

To independently reproduce the entire test suite and CLI execution flow:

```bash
# 1. Run all unit & integration tests
python3 -m pytest tests/ -v

# 2. Run CLI execution smoke test
python3 -m relay.cli run claude --project . --goal "Refactor configuration settings"

# 3. List persisted checkpoints
python3 -m relay.cli checkpoint list
```
