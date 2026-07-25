#!/usr/bin/env python3
"""
Relay QuickStart Example.
Demonstrates: Agent Execution Interception -> Context Monitoring -> Autonomous Handoff -> Checkpoint Validation -> Resume Verification.
"""

import os
import sys

# Ensure relay is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from relay.schemas.agent_state import AgentSessionState
from relay.handoff.hooks import AgentExecutionHook
from relay.handoff.orchestrator import HandoffOrchestrator


def main():
    print("=" * 70)
    print("⚡ RELAY QUICKSTART EXAMPLE: Autonomous Context Handoff Engine")
    print("=" * 70)

    # Step 1: Initialize Agent Session State
    session = AgentSessionState(
        session_id="quickstart-session-001",
        agent_type="claude_code",
        task_goal="Implement Rate Limiting Middleware in src/api/limiter.py",
        tokens_consumed=110000,
        token_limit=128000,
        active_files=["src/api/limiter.py"]
    )
    print(f"\n[1] Initialized Agent Session State:")
    print(f"    • Session ID: {session.session_id}")
    print(f"    • Task Goal: {session.task_goal}")
    print(f"    • Token Consumption: {session.tokens_consumed}/{session.token_limit} ({session.context_usage_ratio:.1%})")

    # Step 2: Intercept Tool Actions & Log Why-NOT / Decisions
    hook = AgentExecutionHook(session_state=session)
    hook.record_decision(
        choice_made="Token Bucket Algorithm",
        justification="Provides smooth rate limiting with low memory footprint",
        files_affected=["src/api/limiter.py"]
    )
    hook.record_why_not(
        attempted_idea="Fixed Window Counter",
        rationale_rejected="Allows double burst traffic at window boundaries",
        files_involved=["src/api/limiter.py"]
    )
    print(f"\n[2] Logged Intercepted Agent State:")
    print(f"    • Decision: 'Token Bucket Algorithm'")
    print(f"    • Dead End (Why-NOT): 'Fixed Window Counter'")

    # Simulate tool action step
    hook.record_tool_step(
        tool_name="edit_file",
        input_params={"path": "src/api/limiter.py"},
        output="Updated rate limiter implementation"
    )

    # Step 3: Trigger Autonomous Handoff Orchestrator
    print(f"\n[3] Triggering HandoffOrchestrator Engine...")
    orchestrator = HandoffOrchestrator()
    result = orchestrator.execute_autonomous_handoff(
        session_state=session,
        hook=hook,
        workspace_dir="."
    )

    # Step 4: Display Resumed Prompt & Results
    print(f"\n[4] Handoff Pipeline Completed Successfully:")
    print(f"    • Status: {result['status']}")
    print(f"    • Monitor State: {result['monitor_state']}")
    print(f"    • Checkpoint ID: {result['checkpoint_id']}")
    print(f"    • Checksum Valid: {result['validation_result'].is_valid}")
    print(f"    • Context Preserved: {result['verification_report'].is_fully_preserved}")

    print("\n=================== RESUMED SYSTEM PROMPT SAMPLE ===================")
    print(result['resumed_prompt'][:350] + "\n... [Truncated] ...")
    print("====================================================================")
    print("\n✅ QUICKSTART COMPLETE: Relay handoff engine executed cleanly!")


if __name__ == "__main__":
    main()
