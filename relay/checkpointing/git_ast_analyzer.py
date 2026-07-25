"""
Git Diff and Python AST Analyzer for Relay Knowledge Checkpoints.
Parses structural AST symbol modifications, git diff patches, and dependency graphs.
"""

import ast
import os
from typing import List, Dict, Set, Tuple, Optional
from relay.core.logger import get_logger
from relay.schemas.checkpoint import FileDiffSummary, ASTNodeChange

logger = get_logger("relay.checkpointing.git_ast")


class GitASTAnalyzer:
    """Analyzes codebase changes via Python AST and Git diff parsing."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = os.path.abspath(repo_root)

    def _extract_symbols_from_tree(self, tree: Optional[ast.AST]) -> Dict[str, Tuple[str, str]]:
        """
        Traverses an AST tree and returns a mapping of symbol_name -> (symbol_type, signature).
        """
        symbols: Dict[str, Tuple[str, str]] = {}
        if not tree:
            return symbols

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                sig = f"def {node.name}({', '.join(arg.arg for arg in node.args.args)})"
                symbols[node.name] = ("function", sig)
            elif isinstance(node, ast.AsyncFunctionDef):
                sig = f"async def {node.name}({', '.join(arg.arg for arg in node.args.args)})"
                symbols[node.name] = ("async_function", sig)
            elif isinstance(node, ast.ClassDef):
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                sig = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
                symbols[node.name] = ("class", sig)

        return symbols

    def extract_ast_symbols(self, file_path: str) -> List[Tuple[str, str, str]]:
        """
        Parses a Python file and extracts (symbol_name, symbol_type, signature).
        """
        full_path = os.path.join(self.repo_root, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(full_path) or not full_path.endswith(".py"):
            return []

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                code = f.read()

            tree = ast.parse(code, filename=full_path)
            symbol_map = self._extract_symbols_from_tree(tree)
            return [(name, stype, sig) for name, (stype, sig) in symbol_map.items()]
        except Exception as e:
            logger.warning(f"Failed to parse AST for file {file_path}: {e}")
            return []

    def diff_ast_symbols(self, file_path: str, old_code: str, new_code: str) -> List[ASTNodeChange]:
        """
        Compares AST nodes between old_code and new_code for a specific file.
        """
        changes: List[ASTNodeChange] = []
        try:
            old_tree = ast.parse(old_code) if old_code else None
            new_tree = ast.parse(new_code) if new_code else None
        except Exception as e:
            logger.warning(f"AST diff parse error in {file_path}: {e}")
            return changes

        old_symbols = self._extract_symbols_from_tree(old_tree)
        new_symbols = self._extract_symbols_from_tree(new_tree)

        # Added or modified
        for name, (stype, sig) in new_symbols.items():
            if name not in old_symbols:
                changes.append(ASTNodeChange(
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=stype,
                    change_type="added",
                    signature=sig
                ))
            elif old_symbols[name] != (stype, sig):
                changes.append(ASTNodeChange(
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=stype,
                    change_type="modified",
                    signature=sig
                ))

        # Removed
        for name, (stype, sig) in old_symbols.items():
            if name not in new_symbols:
                changes.append(ASTNodeChange(
                    file_path=file_path,
                    symbol_name=name,
                    symbol_type=stype,
                    change_type="removed",
                    signature=sig
                ))

        return changes

    def build_file_dependency_graph(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Extracts import dependency relationships across given files.

        Returns:
            Dict[file_path, List[imported_module_or_file_paths]]
        """
        graph: Dict[str, List[str]] = {}

        for rel_path in file_paths:
            full_path = os.path.join(self.repo_root, rel_path) if not os.path.isabs(rel_path) else rel_path
            if not os.path.exists(full_path) or not rel_path.endswith(".py"):
                graph[rel_path] = []
                continue

            dependencies: Set[str] = set()
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=full_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            dependencies.add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            dependencies.add(node.module)

                graph[rel_path] = sorted(list(dependencies))
            except Exception as e:
                logger.warning(f"Error extracting dependencies for {rel_path}: {e}")
                graph[rel_path] = []

        return graph

    def summarize_file_diffs(self, file_diff_map: Dict[str, Tuple[str, str]]) -> List[FileDiffSummary]:
        """
        Converts old/new file content pairs into structured FileDiffSummary objects.
        """
        summaries: List[FileDiffSummary] = []

        import difflib

        for rel_path, (old_text, new_text) in file_diff_map.items():
            old_lines = old_text.splitlines(keepends=True) if old_text else []
            new_lines = new_text.splitlines(keepends=True) if new_text else []

            diff_lines = list(difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                n=1
            ))

            additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
            deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

            status = "added" if not old_text else ("deleted" if not new_text else "modified")
            patch_snippet = "".join(diff_lines[:15]) if diff_lines else f"Diff status: {status} (+{additions}, -{deletions})"

            summaries.append(FileDiffSummary(
                file_path=rel_path,
                status=status,
                additions=additions,
                deletions=deletions,
                patch_summary=patch_snippet
            ))

        return summaries
