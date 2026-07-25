"""
Graph Context Retriever for Relay.
Computes AST import graph proximity and topological graph distances between files.
"""

from typing import Dict, List, Set, Optional
from collections import deque
from relay.core.logger import get_logger

logger = get_logger("relay.retrieval.graph")


class GraphContextRetriever:
    """Traverses file import dependency graphs to calculate topological proximity scores."""

    def compute_file_distances(
        self,
        dependency_graph: Dict[str, List[str]],
        active_files: List[str]
    ) -> Dict[str, int]:
        """
        Calculates shortest path distance (BFS) from active_files to all reachable modules in graph.

        Returns:
            Dict[file_path_or_module, shortest_distance] (0 for active_files, 1 for direct imports, etc.)
        """
        distances: Dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque()

        for active in active_files:
            distances[active] = 0
            queue.append((active, 0))

        # Reconstruct adjacency list (bi-directional for graph traversal)
        adj: Dict[str, Set[str]] = {}
        for src, targets in dependency_graph.items():
            if src not in adj:
                adj[src] = set()
            for tgt in targets:
                adj[src].add(tgt)
                if tgt not in adj:
                    adj[tgt] = set()
                adj[tgt].add(src)

        visited: Set[str] = set(active_files)

        while queue:
            node, dist = queue.popleft()
            neighbors = adj.get(node, set())

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    distances[neighbor] = dist + 1
                    queue.append((neighbor, dist + 1))

        return distances

    def score_graph_relevance(self, file_path: str, distances: Dict[str, int]) -> float:
        """
        Converts topological graph distance into a normalized graph relevance score in [0.0, 1.0].
        - Distance 0 (active file): 1.0
        - Distance 1 (direct import/exporter): 0.75
        - Distance 2 (2-hop dependency): 0.40
        - Distance 3+: 0.10
        - Unreachable: 0.0
        """
        if file_path not in distances:
            return 0.0

        dist = distances[file_path]
        if dist == 0:
            return 1.0
        elif dist == 1:
            return 0.75
        elif dist == 2:
            return 0.40
        elif dist == 3:
            return 0.10
        return 0.05
