# Changelog

All notable changes to the **Relay** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-07-24 - Sprint 3 Real Agent Integration

### Added
- **Abstract Agent Adapter Framework (`relay/adapters/base.py`)**: Implemented `BaseAgentAdapter` interface providing provider-agnostic token monitoring, tool call interception, dead-end logging, handoff orchestration, and trace exporting.
- **Claude Code Adapter (`relay/adapters/claude_code.py`)**: Added `ClaudeCodeAdapter` supporting Claude Code tools (`View`, `Edit`, `Replace`, `Bash`).
- **OpenAI Codex CLI Adapter (`relay/adapters/codex.py`)**: Added `CodexCLIAdapter` supporting Codex tools (`read`, `patch`, `exec`).
- **OpenHands Adapter (`relay/adapters/openhands.py`)**: Added `OpenHandsAdapter` supporting OpenHands event stream actions (`CmdRunAction`, `FileEditAction`, `FileReadAction`).
- **Trace Recorder Engine (`relay/adapters/trace_recorder.py`)**: Added `TraceRecorder` for real-time append-only JSONL recording of agent execution steps.
- **Relay CLI Executable (`relay/cli.py`)**: Added unified `relay` CLI executable (`relay run`, `relay benchmark`, `relay replay`, `relay checkpoint list`, `relay checkpoint resume`). Registered `[project.scripts] relay` entry point in `pyproject.toml`.
- **Integration Documentation (`INTEGRATION_GUIDE.md`)**: Created comprehensive integration guide detailing Adapter API, JSONL Trace Specification, CLI Reference, and System Architecture Diagram.

## [0.1.1] - 2026-07-24

### Added
- **Atomic File Persistence**: Added POSIX atomic writing via `tempfile.NamedTemporaryFile` and `os.replace` in `CheckpointManager.save_checkpoint` to prevent corrupt files during process interrupts.
- **Corrupt Checkpoint Handling**: Added graceful `json.JSONDecodeError` exception handling and logging in `CheckpointManager.load_checkpoint`.
- **Unit Test Coverage**: Added `test_corrupt_checkpoint_file` in `tests/test_checkpointing.py`.

## [0.1.0] - 2026-07-24

### Added
- Initial core release of Relay AI Agent Context Handoff Infrastructure.
- Pydantic v2 Knowledge Checkpoint schemas and Why-NOT store.
- Python AST diff parser and module import dependency graph extractor.
- Qdrant vector database integration and hybrid multi-signal reranker.
- LangGraph state machine agent handoff runner.
- FastAPI REST API backend (`POST /api/v1/checkpoint`, `POST /api/v1/resume`).
- Next.js technical dashboard and standalone static demo website.
