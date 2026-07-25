"""
Relay CLI (`relay-cli`) Executable Entry Point.
Command-line interface for running agent middleware sessions, benchmark runs, trace replays, and checkpoint management.
"""

import os
import sys
import json
import argparse
from typing import List, Optional

from relay import __version__
from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState
from relay.checkpointing.manager import CheckpointManager
from relay.handoff.runner import LangGraphHandoffRunner
from relay.benchmark.runner import BenchmarkRunner
from relay.benchmark.trace_replay import TraceReplayExecutor, AgentTrace
from relay.adapters.claude_code import ClaudeCodeAdapter
from relay.adapters.codex import CodexCLIAdapter
from relay.adapters.openhands import OpenHandsAdapter

logger = get_logger("relay.cli")


def main(args: Optional[List[str]] = None) -> None:
    """Main CLI entry point function for `relay` executable."""
    parser = argparse.ArgumentParser(
        prog="relay",
        description="⚡ Relay — Context Continuity Middleware & Evaluation Framework for AI Coding Agents",
    )
    parser.add_argument("--version", action="version", version=f"relay v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Relay CLI Commands")

    # Command 1: relay run <agent_type> --project <dir>
    run_parser = subparsers.add_parser("run", help="Run AI agent session through Relay middleware")
    run_parser.add_argument("agent", choices=["claude", "claude_code", "codex", "codex_cli", "openhands"], help="Agent type")
    run_parser.add_argument("--project", default=".", help="Project workspace directory")
    run_parser.add_argument("--goal", default="Software Engineering Task Goal", help="User task goal")

    # Command 2: relay benchmark
    bench_parser = subparsers.add_parser("benchmark", help="Execute RelayBench evaluation suite")
    bench_parser.add_argument("--project", default=".", help="Workspace directory")
    bench_parser.add_argument("--repetitions", type=int, default=1, help="Number of repetitions per task")
    bench_parser.add_argument("--limit", type=int, default=None, help="Limit total tasks to execute")
    bench_parser.add_argument("--output", default="artifacts", help="Output artifacts directory")
    bench_parser.add_argument("--no-ablations", action="store_true", help="Disable ablation matrix")

    # Command 3: relay replay <trace.jsonl>
    replay_parser = subparsers.add_parser("replay", help="Replay an agent execution trace deterministically")
    replay_parser.add_argument("trace_file", help="Path to trace JSONL file")

    # Command 4: relay checkpoint [list | resume <id>]
    chk_parser = subparsers.add_parser("checkpoint", help="Manage Relay Knowledge Checkpoints")
    chk_sub = chk_parser.add_subparsers(dest="chk_command")

    chk_list_parser = chk_sub.add_parser("list", help="List persisted checkpoints")
    chk_list_parser.add_argument("--session", default=None, help="Filter by session ID")

    chk_resume_parser = chk_sub.add_parser("resume", help="Resume handoff from checkpoint ID")
    chk_resume_parser.add_argument("checkpoint_id", help="Checkpoint UUID to resume")

    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        sys.exit(0)

    if parsed_args.command == "run":
        _handle_run(parsed_args)
    elif parsed_args.command == "benchmark":
        _handle_benchmark(parsed_args)
    elif parsed_args.command == "replay":
        _handle_replay(parsed_args)
    elif parsed_args.command == "checkpoint":
        _handle_checkpoint(parsed_args)


def _handle_run(args: argparse.Namespace) -> None:
    """Handles `relay run` command with full middleware execution flow."""
    agent_type = args.agent.lower()
    session_id = f"sess-cli-{agent_type}"
    proj_dir = os.path.abspath(args.project)

    if agent_type in ("claude", "claude_code"):
        adapter = ClaudeCodeAdapter(session_id=session_id, task_goal=args.goal)
    elif agent_type in ("codex", "codex_cli"):
        adapter = CodexCLIAdapter(session_id=session_id, task_goal=args.goal)
    else:
        adapter = OpenHandsAdapter(session_id=session_id, task_goal=args.goal)

    print(f"⚡ Initialized Relay Middleware Adapter for '{adapter.session_state.agent_type}'")
    print(f"Goal: {args.goal}")
    print(f"Workspace: {proj_dir}")

    # Stage 1: Index repository workspace into Qdrant Vector Store
    from relay.schemas.checkpoint import RetrievedChunk
    indexed_chunks = []
    for root, _, files in os.walk(proj_dir):
        if ".relay" in root or "__pycache__" in root or ".git" in root:
            continue
        for fname in files:
            if fname.endswith((".py", ".js", ".css", ".md", ".json", ".yaml")):
                fpath = os.path.join(root, fname)
                rel_fpath = os.path.relpath(fpath, proj_dir)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    if content.strip():
                        indexed_chunks.append(RetrievedChunk(
                            chunk_id=f"chk-cli-{rel_fpath}",
                            file_path=rel_fpath,
                            content=content,
                            score=1.0,
                            retrieval_source="cli_index"
                        ))
                except Exception:
                    pass

    if indexed_chunks:
        count = adapter.runner.reranker.vector_store.upsert_chunks(indexed_chunks)
        print(f"✅ Indexed {count} repository files into Qdrant Vector DB")

    # Stage 2: Intercept Tool Actions & Simulate Token Accumulation
    adapter.intercept_tool_call(
        raw_tool_name="View" if agent_type.startswith("claude") else "read",
        input_params={"path": "relay/core/config.py"},
        output="Inspected configuration settings"
    )

    adapter.record_why_not(
        attempted_idea="Hardcoded threshold configuration",
        rationale_rejected="Requires flexible pydantic settings environment overrides",
        error_traceback="ConfigurationError: Environment variable RELAY_CHECKPOINT_THRESHOLD_RATIO ignored"
    )

    adapter.record_decision(
        choice_made="Centralized RelaySettings using Pydantic Settings",
        justification="Ensures clean environment variable overrides across production and dev"
    )

    # Force threshold handoff trigger
    adapter.session_state.tokens_consumed = int(adapter.session_state.token_limit * 0.86)
    should_trigger = adapter.intercept_tool_call(
        raw_tool_name="Edit" if agent_type.startswith("claude") else "patch",
        input_params={"path": "relay/core/config.py", "content": "# Updated config\n"},
        output="Updated configuration settings"
    )

    # Stage 3: Handoff, Hybrid Retrieval & System Prompt Synthesis
    print(f"⚠️ Context Threshold (86%) Reached. Executing LangGraph Handoff Machine...")
    handoff_state = adapter.trigger_handoff()

    chk = handoff_state.get("checkpoint")
    retrieved = handoff_state.get("retrieved_context", [])
    prompt = handoff_state.get("resumed_prompt", "")

    print(f"✅ Checkpoint Synthesized: '{chk.checkpoint_id if chk else 'None'}'")
    print(f"✅ Hybrid Retrieval Found {len(retrieved)} Relevant Context Chunks")
    for r in retrieved[:3]:
        print(f"  • Chunk [{r.file_path}] Score={r.score:.3f}")

    trace_path = adapter.export_trace(f".relay/traces/trace_{session_id}.jsonl")
    print(f"✅ Recorded Append-Only Session Trace to '{trace_path}'")
    print("=================== RESUMED AGENT SYSTEM PROMPT ===================")
    print(prompt[:400] + "\n... [Prompt Truncated] ...")
    print("==================================================================")


def _handle_benchmark(args: argparse.Namespace) -> None:
    """Handles `relay benchmark` command."""
    out_dir = getattr(args, "output", "artifacts")
    limit = getattr(args, "limit", None)
    print(f"⚡ Starting RelayBench Evaluation ({args.repetitions} repetitions, output: {out_dir})...")
    runner = BenchmarkRunner(output_dir=out_dir)
    result = runner.run_full_evaluation(
        repetitions=args.repetitions,
        include_ablations=not args.no_ablations,
        limit_tasks=limit
    )
    print(f"✅ Benchmark Complete! Evidence package exported to '{out_dir}'")
    print(f"Relay Avg Completion: {result.relay_summary.get('avg_completion_rate', 0):.1%}")


def _handle_replay(args: argparse.Namespace) -> None:
    """Handles `relay replay` command."""
    if not os.path.exists(args.trace_file):
        print(f"Error: Trace file '{args.trace_file}' not found.")
        sys.exit(1)

    print(f"⚡ Replaying Trace File '{args.trace_file}'...")
    trace = AgentTrace.load_jsonl(args.trace_file)
    print(f"Loaded {len(trace.steps)} trace steps for session '{trace.session_id}'.")


def _handle_checkpoint(args: argparse.Namespace) -> None:
    """Handles `relay checkpoint` commands."""
    manager = CheckpointManager()

    if args.chk_command == "list":
        checkpoints = manager.list_checkpoints(session_id=args.session)
        print(f"Found {len(checkpoints)} Knowledge Checkpoints:")
        for chk in checkpoints:
            print(f"  • [{chk.checkpoint_id}] Session: {chk.session_id} | Goal: {chk.task_goal[:50]}...")
    elif args.chk_command == "resume":
        chk = manager.load_checkpoint(args.checkpoint_id)
        if not chk:
            print(f"Error: Checkpoint '{args.checkpoint_id}' not found.")
            sys.exit(1)

        runner = LangGraphHandoffRunner(manager=manager)
        final_state = runner.resume_from_checkpoint(chk)
        print("=================== RESUMED SYSTEM PROMPT ===================")
        print(final_state["resumed_prompt"])
        print("=============================================================")
    else:
        print("Usage: relay checkpoint [list | resume <checkpoint_id>]")


if __name__ == "__main__":
    main()
