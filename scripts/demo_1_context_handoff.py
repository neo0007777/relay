#!/usr/bin/env python3
"""
Demo 1: Reproducible Context Handoff Execution.
Demonstrates: Repository Scanning → Context Budget Interception → Checkpoint Creation → LangGraph Handoff → Resumed Agent Session.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from relay.adapters.claude_code import ClaudeCodeAdapter
from relay.schemas.checkpoint import KnowledgeCheckpoint, DecisionItem, WhyNotItem, ASTNodeChange
from relay.checkpointing.manager import CheckpointManager
from relay.handoff.runner import LangGraphHandoffRunner

def run_demo_1():
    print("=" * 70)
    print("⚡ RELAY DEMO 1: Reproducible Context Handoff Execution")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Step 1: Initialize Agent Session & Workspace
        session_id = "sess-demo-1"
        task_goal = "Refactor Authentication Service into TokenService"
        print(f"\n[1/5] Initializing agent session '{session_id}' in workspace: {tmp_dir}")
        adapter = ClaudeCodeAdapter(session_id=session_id, task_goal=task_goal)

        # Create sample workspace source file
        sample_file = os.path.join(tmp_dir, "auth_service.py")
        with open(sample_file, "w") as f:
            f.write("def verify_token(token: str):\n    return True\n")
        print(f"      Created sample source file: {sample_file}")

        # Step 2: Record Tool Actions until Context Budget Threshold (86%)
        print("\n[2/5] Simulating agent tool execution steps...")
        adapter.session_state.tokens_consumed = 50000
        adapter.intercept_tool_call("View", {"file_path": "auth_service.py"}, "File content inspected")
        adapter.session_state.tokens_consumed = 110100
        adapter.record_decision("Atomic Redis key swap", "Prevents async thread deadlocks under concurrent load")
        adapter.record_why_not("Mutex lock around refresh queue", "Caused deadlock in async execution loop")
        print(f"      Token budget usage: {adapter.session_state.tokens_consumed} / 128,000 tokens (86.0%)")

        # Step 3: Trigger Checkpoint Interceptor & Save Checkpoint
        print("\n[3/5] Context monitor threshold (85%) reached. Executing adapter handoff...")
        chk_mgr = CheckpointManager(checkpoint_dir=tmp_dir)
        runner = LangGraphHandoffRunner(manager=chk_mgr)
        adapter.runner = runner

        handoff_state = adapter.trigger_handoff()
        checkpoint = handoff_state.get("checkpoint")
        resumed_prompt = handoff_state.get("resumed_prompt", "")

        print(f"      ✅ KnowledgeCheckpoint created ID: '{checkpoint.checkpoint_id if checkpoint else 'None'}'")
        print(f"      Handoff status: {handoff_state.get('status')}")

        # Step 4: Verify System Prompt & Continuation
        print("\n[4/5] Resumed Agent System Prompt Synthesized:")
        print("-" * 50)
        prompt_lines = resumed_prompt.split("\n")
        for line in prompt_lines[:25]:
            print(f"      {line}")
        print("      ... [Prompt output complete] ...")
        print("-" * 50)

        assert "RELAY CONTEXT HANDOFF" in resumed_prompt
        assert "Atomic Redis key swap" in resumed_prompt
        assert "Mutex lock around refresh queue" in resumed_prompt
        print("\n✅ DEMO 1 SUCCESS: Context handoff executed cleanly and verified reproducibly!")

if __name__ == "__main__":
    run_demo_1()
