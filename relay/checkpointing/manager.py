"""
Checkpoint Persistence Manager for Relay.
Saves, loads, validates, and lists KnowledgeCheckpoints.
"""

import os
import json
from typing import List, Optional
from relay.core.config import settings
from relay.core.logger import get_logger
from relay.schemas.checkpoint import KnowledgeCheckpoint

logger = get_logger("relay.checkpointing.manager")


class CheckpointManager:
    """Manages disk persistence and retrieval of KnowledgeCheckpoint objects."""

    def __init__(self, checkpoint_dir: str = settings.CHECKPOINT_DIR):
        self.checkpoint_dir = os.path.abspath(checkpoint_dir)
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def _get_filepath(self, checkpoint_id: str) -> str:
        safe_id = os.path.basename(checkpoint_id.replace("/", "_").replace("\\", "_"))
        target_path = os.path.abspath(os.path.join(self.checkpoint_dir, f"{safe_id}.json"))
        if not target_path.startswith(self.checkpoint_dir):
            raise ValueError(f"Invalid checkpoint ID path traversal attempt: '{checkpoint_id}'")
        return target_path

    def save_checkpoint(self, checkpoint: KnowledgeCheckpoint) -> str:
        """
        Serializes and atomically writes a KnowledgeCheckpoint to JSON storage.
        Uses a temporary file and atomic os.replace to prevent file corruption.

        Returns:
            Absolute file path of persisted checkpoint.
        """
        filepath = self._get_filepath(checkpoint.checkpoint_id)
        data = checkpoint.model_dump(mode="json")

        import tempfile
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.checkpoint_dir,
                delete=False,
                encoding="utf-8",
                suffix=".tmp"
            ) as tf:
                temp_file_path = tf.name
                json.dump(data, tf, indent=2, ensure_ascii=False)

            # Atomic swap
            os.replace(temp_file_path, filepath)
            logger.info(f"Saved checkpoint '{checkpoint.checkpoint_id}' atomically to {filepath}")
            return filepath
        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass
            logger.error(f"Failed atomic save for checkpoint '{checkpoint.checkpoint_id}': {e}")
            raise IOError(f"Could not save checkpoint atomically: {e}") from e

    def load_checkpoint(self, checkpoint_id: str) -> Optional[KnowledgeCheckpoint]:
        """
        Loads and parses a KnowledgeCheckpoint from JSON storage.
        """
        filepath = self._get_filepath(checkpoint_id)
        if not os.path.exists(filepath):
            logger.warning(f"Checkpoint '{checkpoint_id}' not found at {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            checkpoint = KnowledgeCheckpoint.model_validate(data)
            logger.info(f"Successfully loaded checkpoint '{checkpoint_id}'")
            return checkpoint
        except json.JSONDecodeError as e:
            logger.error(f"Corrupt JSON format in checkpoint file '{filepath}': {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load/parse checkpoint '{checkpoint_id}': {e}")
            return None

    def list_checkpoints(self, session_id: Optional[str] = None) -> List[KnowledgeCheckpoint]:
        """
        Lists all available checkpoints on disk, optionally filtered by session_id.
        """
        checkpoints: List[KnowledgeCheckpoint] = []
        if not os.path.exists(self.checkpoint_dir):
            return checkpoints

        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith(".json"):
                cid = filename[:-5]
                chk = self.load_checkpoint(cid)
                if chk:
                    if session_id is None or chk.session_id == session_id:
                        checkpoints.append(chk)

        checkpoints.sort(key=lambda c: c.created_at, reverse=True)
        return checkpoints

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Deletes a KnowledgeCheckpoint file from disk.

        Returns:
            True if file existed and was removed, False otherwise.
        """
        filepath = self._get_filepath(checkpoint_id)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.info(f"Deleted checkpoint file '{filepath}'")
                return True
            except OSError as e:
                logger.error(f"Failed to delete checkpoint file '{filepath}': {e}")
                return False
        return False
