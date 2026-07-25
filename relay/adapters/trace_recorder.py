"""
Standardized JSONL Trace Recorder for Relay Agent Sessions.
Captures append-only execution events including tool calls, token counts, and checkpoint metadata.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger

logger = get_logger("relay.adapters.trace_recorder")


class TraceRecordEntry(BaseModel):
    """Single JSONL record line in an agent trace log."""

    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    session_id: str = Field(description="Agent session ID")
    step_index: int = Field(description="Sequential step index")
    tool_name: str = Field(description="Tool or action name")
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_summary: str = Field(default="")
    exit_code: int = Field(default=0)
    is_failure: bool = Field(default=False)
    tokens_consumed: int = Field(default=0)
    checkpoint_id: Optional[str] = Field(default=None)


class TraceRecorder:
    """Manages append-only JSONL trace recording for active agent sessions."""

    def __init__(self, session_id: str, trace_dir: str = ".relay/traces"):
        self.session_id = session_id
        self.trace_dir = os.path.abspath(trace_dir)
        os.makedirs(self.trace_dir, exist_ok=True)
        self.filepath = os.path.join(self.trace_dir, f"trace_{session_id}.jsonl")
        self.entries: List[TraceRecordEntry] = []

    def record_step(
        self,
        step_index: int,
        tool_name: str,
        input_params: Dict[str, Any],
        output_summary: str,
        exit_code: int = 0,
        is_failure: bool = False,
        tokens_consumed: int = 0,
        checkpoint_id: Optional[str] = None
    ) -> TraceRecordEntry:
        """
        Records a step entry and appends it to the JSONL trace file.
        """
        entry = TraceRecordEntry(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            step_index=step_index,
            tool_name=tool_name,
            input_params=input_params,
            output_summary=output_summary[:500],
            exit_code=exit_code,
            is_failure=is_failure,
            tokens_consumed=tokens_consumed,
            checkpoint_id=checkpoint_id
        )
        self.entries.append(entry)

        try:
            with open(self.filepath, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
            logger.debug(f"Recorded trace step #{step_index} to {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to append to trace file '{self.filepath}': {e}")

        return entry

    def export_full_trace(self, target_filepath: str) -> str:
        """
        Exports all entries in memory to a target JSONL file.
        """
        target_abs = os.path.abspath(target_filepath)
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)

        with open(target_abs, "w", encoding="utf-8") as f:
            for entry in self.entries:
                f.write(entry.model_dump_json() + "\n")

        logger.info(f"Exported full trace ({len(self.entries)} steps) to {target_abs}")
        return target_abs
