"""
Qdrant Vector Storage Integration for Relay.
Indexes code chunks, tool logs, and documentation with dense semantic vector embeddings.
"""

import math
import hashlib
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from relay.core.config import settings
from relay.core.logger import get_logger
from relay.schemas.checkpoint import RetrievedChunk

logger = get_logger("relay.retrieval.vector_store")


class BaseEmbedder(ABC):
    """Abstract Base Class for text embedding models in Relay."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Converts input text string into a dense vector embedding."""
        pass


class FeatureHashEmbedder(BaseEmbedder):
    """
    Deterministic feature-hashing embedder producing L2-normalized dense vectors of specified dimension.
    Provides fast, standalone vector embeddings without requiring external API calls.
    """

    def __init__(self, dimension: int = settings.EMBEDDING_DIMENSION):
        self.dimension = dimension

    def _tokenize(self, text: str) -> List[str]:
        # Replace non-alphanumeric with spaces
        raw = re.sub(r'[^a-zA-Z0-9_]', ' ', text.lower())
        tokens: List[str] = []
        for word in raw.split():
            tokens.append(word)
            # Split snake_case
            if '_' in word:
                parts = [p for p in word.split('_') if p]
                tokens.extend(parts)
            # Split camelCase
            camel_parts = re.findall(r'[a-z]+|[A-Z][a-z]*|[0-9]+', word)
            if len(camel_parts) > 1:
                tokens.extend([p.lower() for p in camel_parts])
        return list(set(tokens))

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        tokens = self._tokenize(text)

        # Add unigrams and bigrams
        features = list(tokens)
        for i in range(len(tokens) - 1):
            features.append(f"{tokens[i]}_{tokens[i+1]}")

        for feat in features:
            hash_val = int(hashlib.sha256(feat.encode("utf-8")).hexdigest(), 16)
            idx = hash_val % self.dimension
            vector[idx] += 1.0

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector


class QdrantVectorStore:
    """Manages Qdrant vector collection setup, indexing, and retrieval."""

    def __init__(
        self,
        collection_name: str = settings.QDRANT_COLLECTION_NAME,
        in_memory: bool = settings.QDRANT_IN_MEMORY,
        dimension: int = settings.EMBEDDING_DIMENSION,
        embedder: Optional[BaseEmbedder] = None,
    ):
        self.collection_name = collection_name
        self.dimension = dimension
        self.embedder = embedder or FeatureHashEmbedder(dimension=dimension)

        if in_memory:
            self.client = QdrantClient(":memory:")
            logger.info("Initialized in-memory Qdrant client.")
        else:
            self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            logger.info(f"Connected to remote Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Creates Qdrant collection if it does not already exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.dimension,
                        distance=qmodels.Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection '{self.collection_name}'.")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")

    def upsert_chunks(self, chunks: List[RetrievedChunk]) -> int:
        """
        Indexes a list of RetrievedChunk objects into Qdrant.

        Returns:
            Number of points successfully upserted.
        """
        if not chunks:
            return 0

        points: List[qmodels.PointStruct] = []
        for idx, chunk in enumerate(chunks):
            vector = self.embedder.embed_text(chunk.content)
            # Use deterministic integer hash of chunk_id as Qdrant ID
            point_id = int(hashlib.md5(chunk.chunk_id.encode("utf-8")).hexdigest()[:8], 16)

            payload = {
                "chunk_id": chunk.chunk_id,
                "file_path": chunk.file_path,
                "content": chunk.content,
                "retrieval_source": chunk.retrieval_source,
                "metadata": chunk.metadata,
            }

            points.append(qmodels.PointStruct(id=point_id, vector=vector, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Upserted {len(points)} chunks into Qdrant collection '{self.collection_name}'.")
        return len(points)

    def search_similar(self, query: str, top_k: int = settings.TOP_K_RETRIEVAL) -> List[RetrievedChunk]:
        """
        Performs cosine vector similarity search in Qdrant.
        """
        query_vector = self.embedder.embed_text(query)
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )

        retrieved: List[RetrievedChunk] = []
        for hit in results:
            payload = hit.payload or {}
            retrieved.append(RetrievedChunk(
                chunk_id=str(payload.get("chunk_id", str(hit.id))),
                file_path=str(payload.get("file_path", "")),
                content=str(payload.get("content", "")),
                score=float(hit.score),
                retrieval_source="vector_semantic",
                metadata=payload.get("metadata", {})
            ))

        return retrieved
