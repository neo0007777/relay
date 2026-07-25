"""
FastAPI Dependency Injection Factories for Relay API Endpoints.
Prevents import-time side effects and allows request-scoped or test-overridden instances.
"""

from fastapi import Depends
from relay.checkpointing.compressor import KnowledgeCompressor
from relay.checkpointing.manager import CheckpointManager
from relay.handoff.runner import LangGraphHandoffRunner
from relay.benchmark.harness import RelayBenchmarkHarness


def get_checkpoint_manager() -> CheckpointManager:
    """Dependency factory for CheckpointManager instance."""
    return CheckpointManager()


def get_knowledge_compressor() -> KnowledgeCompressor:
    """Dependency factory for KnowledgeCompressor instance."""
    return KnowledgeCompressor()


def get_handoff_runner(
    compressor: KnowledgeCompressor = Depends(get_knowledge_compressor),
    manager: CheckpointManager = Depends(get_checkpoint_manager),
) -> LangGraphHandoffRunner:
    """Dependency factory for LangGraphHandoffRunner instance."""
    return LangGraphHandoffRunner(compressor=compressor, manager=manager)


def get_benchmark_harness() -> RelayBenchmarkHarness:
    """Dependency factory for RelayBenchmarkHarness instance."""
    return RelayBenchmarkHarness()
