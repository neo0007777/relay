"""
Centralized Configuration Settings for Relay using Pydantic Settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class RelaySettings(BaseSettings):
    """Configuration options for Relay core middleware, vector store, and API."""

    # Project Information
    ENV: str = Field(default="development", description="Execution environment (development, staging, production)")
    DEBUG: bool = Field(default=True, description="Enable debug logging")

    # Context & Checkpoint Monitor Thresholds
    CONTEXT_LIMIT_TOKENS: int = Field(default=128000, description="Default max context token limit (e.g. 128k)")
    CHECKPOINT_THRESHOLD_RATIO: float = Field(default=0.85, description="Token capacity ratio that triggers checkpoint (85%)")

    # Storage Paths
    CHECKPOINT_DIR: str = Field(default=".relay/checkpoints", description="Directory to persist local knowledge checkpoints")
    BENCHMARK_RESULTS_DIR: str = Field(default=".relay/benchmark_results", description="Directory to store evaluation results")

    # Vector Storage (Qdrant)
    QDRANT_HOST: str = Field(default="localhost", description="Qdrant service host")
    QDRANT_PORT: int = Field(default=6333, description="Qdrant service port")
    QDRANT_IN_MEMORY: bool = Field(default=True, description="Use in-memory Qdrant client for local dev/testing")
    QDRANT_COLLECTION_NAME: str = Field(default="relay_code_context", description="Qdrant collection name")

    # Embedding / Retrieval Settings
    EMBEDDING_DIMENSION: int = Field(default=384, description="Vector dimension for embeddings")
    TOP_K_RETRIEVAL: int = Field(default=5, description="Number of context chunks to retrieve during handoff")

    model_config = SettingsConfigDict(
        env_prefix="RELAY_",
        case_sensitive=False,
    )


# Global settings singleton instance
settings = RelaySettings()
