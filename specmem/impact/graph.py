"""SpecImpact Graph - Bidirectional relationship graph for spec impact analysis.

Connects specifications, code files, and tests to enable selective testing
and context-aware development.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from specmem.impact.graph_models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    ImpactSet,
    NodeType,
)


logger = logging.getLogger(__name__)


class SpecImpactGraph:
    """Bidirectional relationship graph for spec impact analysis.

    Enables querying:
    - Which specs are affected by code changes
    - Which tests should run for changes
    - Which code implements a spec
    """

    def __init__(self, storage_path: Path | str | None = None) -> None:
        """Initialize the graph.

        Args:
            storage_path: Path to store graph data (JSON file).
                         If None, graph is in-memory only.
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []

        # Index structures for fast lookups
        self._outgoing: dict[str, list[GraphEdge]] = defaultdict(list)
        self._incoming: dict[str, list[GraphEdge]] = defaultdict(list)

        # Load existing graph if storage exists
        if self.storage_path and self.storage_path.exists():
            self.load()

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph.

        Args:
            node: The node to add. If a node with the same ID exists,
                  it will be replaced.
        """
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID.

        Args:
            node_id: The node ID to look up.

        Returns:
            The node if found, None otherwise.
        """
        return self._nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all its edges.

        Args:
            node_id: The node ID to remove.

        Returns:
            True if node was removed, False if not found.
        """
        if node_id not in self._nodes:
            return False

        del self._nodes[node_id]

        # Remove edges involving this node
        self._edges = [e for e in self._edges if node_id not in (e.source_id, e.target_id)]

        # Update indexes
        self._rebuild_indexes()
        return True

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph.

        Args:
            edge: The edge to add.
        """
        # Check if edge already exists
        for i, existing in enumerate(self._edges):
            if (
                existing.source_id == edge.source_id
                and existing.target_id == edge.target_id
                and existing.relationship == edge.relationship
            ):
                # Replace existing edge
                self._edges[i] = edge
                self._rebuild_indexes()
                return

        self._edges.append(edge)
        self._outgoing[edge.source_id].append(edge)
        self._incoming[edge.target_id].append(edge)

    def remove_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: EdgeType | None = None,
    ) -> bool:
        """Remove an edge from the graph.

        Args:
            source_id: Source node ID.
            target_id: Target node ID.
            relationship: Optional relationship type to match.

        Returns:
            True if edge was removed, False if not found.
        """
        removed = False
        new_edges = []
        for edge in self._edges:
            if (
                edge.source_id == source_id
                and edge.target_id == target_id
                and (relationship is None or edge.relationship == relationship)
            ):
                removed = True
            else:
                new_edges.append(edge)

        if removed:
            self._edges = new_edges
            self._rebuild_indexes()

        return removed

    def _rebuild_indexes(self) -> None:
        """Rebuild edge indexes after modifications."""
        self._outgoing = defaultdict(list)
        self._incoming = defaultdict(list)
        for edge in self._edges:
            self._outgoing[edge.source_id].append(edge)
            self._incoming[edge.target_id].append(edge)

    def get_edges_from(self, node_id: str) -> list[GraphEdge]:
        """Get all outgoing edges from a node."""
        return self._outgoing.get(node_id, [])

    def get_edges_to(self, node_id: str) -> list[GraphEdge]:
        """Get all incoming edges to a node."""
        return self._incoming.get(node_id, [])

    @property
    def nodes(self) -> dict[str, GraphNode]:
        """Get all nodes in the graph."""
        return self._nodes

    @property
    def edges(self) -> list[GraphEdge]:
        """Get all edges in the graph."""
        return self._edges

    def save(self) -> None:
        """Save graph to storage."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }

        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Saved graph to {self.storage_path}")

    def load(self) -> None:
        """Load graph from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        with open(self.storage_path) as f:
            data = json.load(f)

        self._nodes = {n["id"]: GraphNode.from_dict(n) for n in data.get("nodes", [])}
        self._edges = [GraphEdge.from_dict(e) for e in data.get("edges", [])]
        self._rebuild_indexes()

        logger.debug(f"Loaded graph from {self.storage_path}")

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Dictionary with node counts, edge counts, etc.
        """
        node_counts = defaultdict(int)
        for node in self._nodes.values():
            node_counts[node.type.value] += 1

        edge_counts = defaultdict(int)
        for edge in self._edges:
            edge_counts[edge.relationship.value] += 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": dict(node_counts),
            "edges_by_type": dict(edge_counts),
        }

    def query_specs_for_code(
        self,
        file_path: str,
        include_transitive: bool = True,
        max_depth: int = 2,
    ) -> list[GraphNode]:
        """Get specs linked to a code file.

        Args:
            file_path: Path to the code file.
            include_transitive: Include indirectly linked specs.
            max_depth: Maximum traversal depth for transitive links.

        Returns:
            List of spec nodes linked to the code file.
        """
        # Find the code node
        code_node_id = f"code:{file_path}"
        if code_node_id not in self._nodes:
            # Try without prefix
            code_node_id = file_path
            if code_node_id not in self._nodes:
                return []

        # BFS to find connected specs
        visited: set[str] = set()
        specs: list[GraphNode] = []
        queue: list[tuple[str, int]] = [(code_node_id, 0)]

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            current_node = self._nodes.get(current_id)
            if current_node and current_node.type == NodeType.SPEC:
                specs.append(current_node)

            if not include_transitive and depth > 0:
                continue
            if depth >= max_depth:
                continue

            # Follow outgoing edges
            for edge in self._outgoing.get(current_id, []):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))

            # Follow incoming edges (bidirectional)
            for edge in self._incoming.get(current_id, []):
                if edge.source_id not in visited:
                    queue.append((edge.source_id, depth + 1))

        # Sort by confidence descending
        specs.sort(key=lambda n: n.confidence, reverse=True)
        return specs

    def query_code_for_spec(self, spec_id: str) -> list[GraphNode]:
        """Get code files implementing a spec.

        Args:
            spec_id: The spec ID to look up.

        Returns:
            List of code nodes linked to the spec.
        """
        # Find the spec node
        if spec_id not in self._nodes:
            spec_id = f"spec:{spec_id}"
            if spec_id not in self._nodes:
                return []

        code_nodes: list[GraphNode] = []

        # Find incoming IMPLEMENTS edges
        for edge in self._incoming.get(spec_id, []):
            if edge.relationship == EdgeType.IMPLEMENTS:
                node = self._nodes.get(edge.source_id)
                if node and node.type == NodeType.CODE:
                    code_nodes.append(node)

        # Also check outgoing edges (bidirectional)
        for edge in self._outgoing.get(spec_id, []):
            if edge.relationship == EdgeType.IMPLEMENTS:
                node = self._nodes.get(edge.target_id)
                if node and node.type == NodeType.CODE:
                    code_nodes.append(node)

        # Sort by confidence descending
        code_nodes.sort(key=lambda n: n.confidence, reverse=True)
        return code_nodes

    def query_tests_for_change(
        self,
        changed_files: list[str],
    ) -> list[GraphNode]:
        """Get tests to run for changed files.

        Traverses code→spec→test path to find relevant tests.

        Args:
            changed_files: List of changed file paths.

        Returns:
            List of test nodes ordered by confidence descending.
        """
        test_nodes: dict[str, GraphNode] = {}

        for file_path in changed_files:
            # Get specs for this code file
            specs = self.query_specs_for_code(file_path)

            for spec in specs:
                # Find tests for this spec
                for edge in self._incoming.get(spec.id, []):
                    if edge.relationship == EdgeType.TESTS:
                        node = self._nodes.get(edge.source_id)
                        if node and node.type == NodeType.TEST:
                            test_nodes[node.id] = node

                for edge in self._outgoing.get(spec.id, []):
                    if edge.relationship == EdgeType.TESTS:
                        node = self._nodes.get(edge.target_id)
                        if node and node.type == NodeType.TEST:
                            test_nodes[node.id] = node

        # Sort by confidence descending
        result = list(test_nodes.values())
        result.sort(key=lambda n: n.confidence, reverse=True)
        return result

    def query_impact(
        self,
        changed_files: list[str],
        depth: int = 2,
        include_suggested: bool = False,
        limit: int | None = None,
    ) -> ImpactSet:
        """Get full impact set for changed files.

        Args:
            changed_files: List of changed file paths.
            depth: Maximum traversal depth for transitive relationships.
            include_suggested: Include suggested (low-confidence) links.
            limit: Maximum number of results per category.

        Returns:
            ImpactSet containing affected specs, code, and tests.
        """
        if not changed_files:
            return ImpactSet(
                changed_files=[],
                depth=depth,
                message="No files provided",
            )

        specs: dict[str, GraphNode] = {}
        code: dict[str, GraphNode] = {}
        tests: dict[str, GraphNode] = {}

        # BFS from each changed file
        for file_path in changed_files:
            visited: set[str] = set()
            queue: list[tuple[str, int]] = []

            # Find starting node
            code_node_id = f"code:{file_path}"
            if code_node_id in self._nodes:
                queue.append((code_node_id, 0))
            elif file_path in self._nodes:
                queue.append((file_path, 0))

            while queue:
                current_id, current_depth = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)

                node = self._nodes.get(current_id)
                if not node:
                    continue

                # Skip suggested links if not included
                if not include_suggested and node.suggested:
                    continue

                # Categorize node
                if node.type == NodeType.SPEC:
                    specs[node.id] = node
                elif node.type == NodeType.CODE:
                    code[node.id] = node
                elif node.type == NodeType.TEST:
                    tests[node.id] = node

                # Continue traversal if within depth
                if current_depth < depth:
                    for edge in self._outgoing.get(current_id, []):
                        if edge.target_id not in visited:
                            queue.append((edge.target_id, current_depth + 1))
                    for edge in self._incoming.get(current_id, []):
                        if edge.source_id not in visited:
                            queue.append((edge.source_id, current_depth + 1))

        # Convert to sorted lists
        spec_list = sorted(specs.values(), key=lambda n: n.confidence, reverse=True)
        code_list = sorted(code.values(), key=lambda n: n.confidence, reverse=True)
        test_list = sorted(tests.values(), key=lambda n: n.confidence, reverse=True)

        # Apply limits
        if limit:
            spec_list = spec_list[:limit]
            code_list = code_list[:limit]
            test_list = test_list[:limit]

        # Generate message
        if not spec_list and not code_list and not test_list:
            message = "No tracked impact found for the changed files"
        else:
            message = (
                f"Found {len(spec_list)} specs, {len(code_list)} code files, {len(test_list)} tests"
            )

        return ImpactSet(
            specs=spec_list,
            code=code_list,
            tests=test_list,
            changed_files=changed_files,
            depth=depth,
            message=message,
        )

    def update_incremental(
        self,
        changed_specs: list[str] | None = None,
        changed_code: list[str] | None = None,
    ) -> None:
        """Update graph incrementally for changes.

        Only updates nodes and edges related to changed files,
        preserving unaffected relationships.

        Args:
            changed_specs: List of changed spec file paths.
            changed_code: List of changed code file paths.
        """
        changed_specs = changed_specs or []
        changed_code = changed_code or []

        # Track which nodes need edge updates
        nodes_to_update: set[str] = set()

        # Update spec nodes
        for spec_path in changed_specs:
            node_id = f"spec:{spec_path}"
            if node_id in self._nodes:
                nodes_to_update.add(node_id)
                logger.debug(f"Marking spec node for update: {node_id}")

        # Update code nodes
        for code_path in changed_code:
            node_id = f"code:{code_path}"
            if node_id in self._nodes:
                nodes_to_update.add(node_id)
                logger.debug(f"Marking code node for update: {node_id}")

        # Remove edges from updated nodes (they'll be re-added by builder)
        if nodes_to_update:
            self._edges = [e for e in self._edges if e.source_id not in nodes_to_update]
            self._rebuild_indexes()
            logger.info(f"Incremental update: cleared edges for {len(nodes_to_update)} nodes")

    def export(
        self,
        format: str = "json",
        filter_type: NodeType | None = None,
        focal_node: str | None = None,
        max_depth: int | None = None,
    ) -> str:
        """Export graph in specified format.

        Args:
            format: Output format ('json', 'dot', 'mermaid').
            filter_type: Only include nodes of this type.
            focal_node: Extract subgraph around this node.
            max_depth: Maximum depth for subgraph extraction.

        Returns:
            Graph data in the specified format.
        """
        # Get nodes and edges to export
        if focal_node and max_depth:
            nodes, edges = self._extract_subgraph(focal_node, max_depth)
        else:
            nodes = list(self._nodes.values())
            edges = self._edges

        # Apply type filter
        if filter_type:
            nodes = [n for n in nodes if n.type == filter_type]
            node_ids = {n.id for n in nodes}
            edges = [e for e in edges if e.source_id in node_ids and e.target_id in node_ids]

        if format == "json":
            return self._export_json(nodes, edges)
        elif format == "dot":
            return self._export_dot(nodes, edges)
        elif format == "mermaid":
            return self._export_mermaid(nodes, edges)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _extract_subgraph(
        self,
        focal_node: str,
        max_depth: int,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Extract subgraph around a focal node."""
        if focal_node not in self._nodes:
            return [], []

        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(focal_node, 0)]
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            node = self._nodes.get(current_id)
            if node:
                nodes.append(node)

            if depth < max_depth:
                for edge in self._outgoing.get(current_id, []):
                    edges.append(edge)
                    if edge.target_id not in visited:
                        queue.append((edge.target_id, depth + 1))
                for edge in self._incoming.get(current_id, []):
                    edges.append(edge)
                    if edge.source_id not in visited:
                        queue.append((edge.source_id, depth + 1))

        return nodes, edges

    def _export_json(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> str:
        """Export as JSON."""
        data = {
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
        }
        return json.dumps(data, indent=2)

    def _export_dot(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> str:
        """Export as Graphviz DOT format."""
        lines = ["digraph SpecImpactGraph {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box];")
        lines.append("")

        # Node styles by type
        type_styles = {
            NodeType.SPEC: 'style=filled,fillcolor="#e1f5fe"',
            NodeType.CODE: 'style=filled,fillcolor="#fff3e0"',
            NodeType.TEST: 'style=filled,fillcolor="#e8f5e9"',
        }

        for node in nodes:
            style = type_styles.get(node.type, "")
            label = node.id.replace('"', '\\"')
            lines.append(f'  "{node.id}" [label="{label}",{style}];')

        lines.append("")

        for edge in edges:
            label = edge.relationship.value
            lines.append(f'  "{edge.source_id}" -> "{edge.target_id}" [label="{label}"];')

        lines.append("}")
        return "\n".join(lines)

    def _export_mermaid(
        self,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> str:
        """Export as Mermaid diagram."""
        lines = ["graph LR"]

        # Node definitions with styles
        for node in nodes:
            node_id = node.id.replace(":", "_").replace(".", "_").replace("/", "_")
            label = node.id
            if node.type == NodeType.SPEC:
                lines.append(f"  {node_id}[{label}]")
            elif node.type == NodeType.CODE:
                lines.append(f"  {node_id}({label})")
            elif node.type == NodeType.TEST:
                lines.append(f"  {node_id}{{{label}}}")

        # Edges
        for edge in edges:
            src = edge.source_id.replace(":", "_").replace(".", "_").replace("/", "_")
            tgt = edge.target_id.replace(":", "_").replace(".", "_").replace("/", "_")
            label = edge.relationship.value
            lines.append(f"  {src} -->|{label}| {tgt}")

        return "\n".join(lines)
