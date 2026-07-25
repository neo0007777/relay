# Relay: Real Agent Integration Guide & CLI Reference

## 1. Overview & Adapter Architecture

Relay operates as a universal, provider-agnostic middleware layer between AI coding agents (**Claude Code**, **OpenAI Codex CLI**, **OpenHands**) and target software repositories.

```
┌─────────────────────────────────────────────────────────┐
│               Real AI Coding Agent                      │
│     (Claude Code / OpenAI Codex CLI / OpenHands)        │
└──────────────────────────┬──────────────────────────────┘
                           │ Raw Tool Action Streams
                           ▼
┌─────────────────────────────────────────────────────────┐
│              Relay Agent Adapter Sub-system             │
│   (BaseAgentAdapter -> ClaudeCode / Codex / OpenHands)  │
├─────────────────────────────────────────────────────────┤
│  • Token Usage Interceptor & Context Monitor            │
│  • Tool Action Translation & AST Diff Tracker           │
│  • Why-NOT Dead-End Store & Decision Logger             │
│  • Append-Only JSONL Trace Recorder                     │
└──────────────────────────┬──────────────────────────────┘
                           │ Usage ≥ 85% Threshold
                           ▼
┌─────────────────────────────────────────────────────────┐
│          LangGraph Orchestration Machine                │
│    (Knowledge Checkpoint + Hybrid Rerank + Prompt)       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
              Fresh Agent Instance Resumed
```

---

## 2. Agent Adapter API Reference

Every agent adapter inherits from `BaseAgentAdapter` ([`relay/adapters/base.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/adapters/base.py)) and exposes standard lifecycle methods:

```python
from relay.adapters.claude_code import ClaudeCodeAdapter

adapter = ClaudeCodeAdapter(
    session_id="sess-001",
    task_goal="Refactor TokenService in FastAPI",
    token_limit=128000
)

# 1. Intercept tool execution step
should_trigger_checkpoint = adapter.intercept_tool_call(
    raw_tool_name="Edit",
    input_params={"path": "src/auth/manager.py", "content": "updated code"},
    output="File modified successfully"
)

# 2. Record dead end or rejected approach
adapter.record_why_not(
    attempted_idea="Inline refresh token queue",
    rationale_rejected="Caused circular import and async thread deadlock",
    error_traceback="ImportError: cannot import TokenService"
)

# 3. Record explicit design decision
adapter.record_decision(
    choice_made="Extract standalone TokenService class",
    justification="Decouples token lifecycle management"
)

# 4. Trigger context handoff when threshold is met
if should_trigger_checkpoint:
    final_state = adapter.trigger_handoff()
    resumed_prompt = final_state["resumed_prompt"]
```

---

## 3. Standardized JSONL Trace Format

Every agent execution session is recorded to `.relay/traces/trace_<session_id>.jsonl` using the `TraceRecorder` engine ([`relay/adapters/trace_recorder.py`](file:///Users/shivasharma/Desktop/untitled%20folder%2014/relay/adapters/trace_recorder.py)):

```json
{
  "timestamp": "2026-07-24T18:10:00.123456",
  "session_id": "sess-001",
  "step_index": 1,
  "tool_name": "edit_file",
  "input_params": {"path": "src/auth/manager.py", "content": "..."},
  "output_summary": "File modified successfully",
  "exit_code": 0,
  "is_failure": false,
  "tokens_consumed": 105000,
  "checkpoint_id": "chk-7f3a9012"
}
```

---

## 4. Relay CLI Reference (`relay-cli`)

Relay installs a unified CLI executable `relay`:

### Run Agent Session

```bash
relay run claude --project ./repo --goal "Refactor auth manager"
relay run codex --project ./repo --goal "Implement OAuth PKCE"
relay run openhands --project ./repo --goal "Fix queue memory leak"
```

### Run Benchmark Suite

```bash
relay benchmark --repetitions 3
```

### Replay Execution Trace

```bash
relay replay .relay/traces/trace_sess-001.jsonl
```

### Manage Checkpoints

```bash
# List persisted checkpoints
relay checkpoint list

# Resume handoff prompt for a checkpoint
relay checkpoint resume chk-7f3a9012
```
