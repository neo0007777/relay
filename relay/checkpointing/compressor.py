"""
Hybrid Knowledge Compressor for Relay.
Structures runtime context into narrative summary, decision trees, Why-Not dead ends, and structural AST state.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from relay.core.logger import get_logger
from relay.schemas.agent_state import AgentSessionState, ToolExecutionLog
from relay.schemas.checkpoint import (
    KnowledgeCheckpoint,
    WhyNotItem,
    DecisionItem,
    FileDiffSummary,
    ASTNodeChange,
)
from relay.checkpointing.git_ast_analyzer import GitASTAnalyzer

logger = get_logger("relay.checkpointing.compressor")


class KnowledgeCompressor:
    """
    Compresses active agent session logs into a rich KnowledgeCheckpoint.
    Combines narrative state, Why-Not store, AST deltas, and tool output history.
    """

    def __init__(self, ast_analyzer: Optional[GitASTAnalyzer] = None):
        self.ast_analyzer = ast_analyzer or GitASTAnalyzer()

    def compress_session(
        self,
        session_state: AgentSessionState,
        why_not_store: Optional[List[WhyNotItem]] = None,
        decision_log: Optional[List[DecisionItem]] = None,
        file_diff_map: Optional[Dict[str, tuple[str, str]]] = None,
        workspace_dir: Optional[str] = None,
    ) -> KnowledgeCheckpoint:
        """
        Synthesizes a KnowledgeCheckpoint object from session state and code diffs.
        """
        why_not = why_not_store or []
        decisions = decision_log or []
        diff_map = file_diff_map or {}

        # Synthesize narrative summary from tool execution logs
        narrative = self._build_narrative_summary(session_state)

        # Extract file diff summaries and AST symbol changes
        file_diffs = self.ast_analyzer.summarize_file_diffs(diff_map)
        ast_changes: List[ASTNodeChange] = []
        for path, (old_code, new_code) in diff_map.items():
            ast_changes.extend(self.ast_analyzer.diff_ast_symbols(path, old_code, new_code))

        # Build dependency graph for active files
        dep_graph = self.ast_analyzer.build_file_dependency_graph(session_state.active_files)

        # Extract key tool outputs (errors or test runs)
        important_outputs = [
            f"[{log.tool_name}] (exit={log.exit_code}): {log.output_summary}"
            for log in session_state.tool_logs
            if log.is_failure or log.exit_code != 0 or "test" in log.tool_name.lower()
        ]

        checkpoint = KnowledgeCheckpoint(
            checkpoint_id=f"chk-{uuid.uuid4().hex[:8]}",
            session_id=session_state.session_id,
            task_goal=session_state.task_goal,
            created_at=datetime.now(),
            narrative_progress=narrative,
            pending_todos=self._extract_pending_todos(session_state),
            decision_log=decisions,
            why_not_store=why_not,
            file_diffs=file_diffs,
            ast_changes=ast_changes,
            dependency_graph=dep_graph,
            important_tool_outputs=important_outputs,
            tokens_at_checkpoint=session_state.tokens_consumed,
            context_limit=session_state.token_limit,
        )

        logger.info(
            f"Synthesized KnowledgeCheckpoint '{checkpoint.checkpoint_id}' "
            f"with {len(why_not)} why-not items, {len(decisions)} decisions, "
            f"and {len(ast_changes)} AST deltas."
        )

        return checkpoint

    def _build_narrative_summary(self, session: AgentSessionState) -> str:
        """Constructs narrative text summary of current progress."""
        if not session.tool_logs:
            active_str = f" Active files: {', '.join(session.active_files)}." if session.active_files else ""
            return f"Session started for task: {session.task_goal}.{active_str} No tools executed yet."

        summary_lines = [
            f"Goal: {session.task_goal}",
            f"Active Files: {', '.join(session.active_files) if session.active_files else 'None'}",
            f"Executed {len(session.tool_logs)} actions across {len(session.active_files)} active files.",
            "Recent key actions:"
        ]
        for log in session.tool_logs[-5:]:
            status = "FAILED" if log.is_failure else "SUCCESS"
            summary_lines.append(f"  - {log.tool_name} [{status}]: {log.output_summary[:80]}")

        return "\n".join(summary_lines)

    def _extract_pending_todos(self, session: AgentSessionState) -> List[str]:
        """Extracts pending TODO items from session metadata or tool logs."""
        todos = session.metadata.get("pending_todos", [])
        if isinstance(todos, list) and todos:
            return [str(t) for t in todos]
        return ["Continue task implementation and resolve remaining failing tests."]
