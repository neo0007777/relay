"""
Observability and Telemetry Engine for Relay Autonomous Handoff.
Captures lifecycle stage events, timestamps, stage durations, and human-readable execution timelines.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from relay.core.logger import get_logger

logger = get_logger("relay.core.telemetry")


class TelemetryEvent(BaseModel):
    """Single telemetry event record in handoff execution timeline."""

    stage_name: str = Field(description="Stage name (e.g. Session Started, Warning Threshold, Checkpoint Created)")
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_ms: float = Field(default=0.0, description="Duration in milliseconds taken by this stage")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific metrics and data")


class HandoffTelemetry:
    """Manages telemetry event streams and formats structured execution timelines."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.events: List[TelemetryEvent] = []
        self._stage_timers: Dict[str, float] = {}

    def start_stage(self, stage_name: str) -> None:
        """Marks the start timestamp for a handoff stage."""
        self._stage_timers[stage_name] = time.perf_counter()

    def record_stage(self, stage_name: str, payload: Optional[Dict[str, Any]] = None) -> TelemetryEvent:
        """
        Records a completed stage event with elapsed duration (ms).
        """
        start_time = self._stage_timers.pop(stage_name, time.perf_counter())
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        event = TelemetryEvent(
            stage_name=stage_name,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            payload=payload or {}
        )
        self.events.append(event)
        logger.info(f"Telemetry Timeline [{stage_name}]: {duration_ms:.2f}ms | Payload: {payload or {}}")
        return event

    def format_timeline(self) -> str:
        """
        Formats human-readable execution timeline for CLI and diagnostic inspection.
        """
        lines = [
            f"=================== RELAY TELEMETRY TIMELINE ===================",
            f"Session ID: {self.session_id}",
            f"Total Events: {len(self.events)}",
            "-" * 64,
        ]

        total_duration = sum(e.duration_ms for e in self.events)

        for idx, event in enumerate(self.events, 1):
            ts_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
            lines.append(f" [{idx}] {ts_str} | {event.stage_name:<30} ({event.duration_ms:.1f}ms)")
            if event.payload:
                for k, v in event.payload.items():
                    lines.append(f"      • {k}: {v}")

        lines.append("-" * 64)
        lines.append(f"Total Handoff Latency: {total_duration:.2f}ms")
        lines.append("==================================================================")
        return "\n".join(lines)
