"""Impact Graph Builder implementation."""

import logging
from pathlib import Path

from specmem.graph.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    ImpactGraphData,
    NodeType,
)


logger = logging.getLogger(__name__)


class ImpactGraphBuilder:
    """Builds impact graph data for visualization.

    Creates a graph showing relationships between specs, code files, and tests.
    """

    def __init__(self, workspace_path: Path):
        """Initialize the graph builder.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = workspace_path

    def build(self) -> ImpactGraphData:
        """Build the complete impact graph.

        Returns:
            ImpactGraphData with all nodes and edges
        """
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # Add feature nodes
        feature_nodes = self._build_feature_nodes()
        nodes.extend(feature_nodes)

        # Add spec nodes
        spec_nodes = self._build_spec_nodes()
        nodes.extend(spec_nodes)

        # Add code nodes (from impact graph if available)
        code_nodes = self._build_code_nodes()
        nodes.extend(code_nodes)

        # Add test nodes
        test_nodes = self._build_test_nodes()
        nodes.extend(test_nodes)

        # Build edges
        edges.extend(self._build_feature_spec_edges(feature_nodes, spec_nodes))
        edges.extend(self._build_spec_code_edges(spec_nodes, code_nodes))
        edges.extend(self._build_code_test_edges(code_nodes, test_nodes))

        return ImpactGraphData(nodes=nodes, edges=edges)

    def _build_feature_nodes(self) -> list[GraphNode]:
        """Build nodes for features (spec directories)."""
        nodes = []
        specs_dir = self.workspace_path / ".kiro" / "specs"

        if not specs_dir.exists():
            return nodes

        for feature_dir in specs_dir.iterdir():
            if not feature_dir.is_dir():
                continue

            node = GraphNode(
                id=f"feature:{feature_dir.name}",
                type=NodeType.FEATURE,
                label=feature_dir.name.replace("-", " ").title(),
                metadata={
                    "path": str(feature_dir.relative_to(self.workspace_path)),
                    "has_requirements": (feature_dir / "requirements.md").exists(),
                    "has_design": (feature_dir / "design.md").exists(),
                    "has_tasks": (feature_dir / "tasks.md").exists(),
                },
            )
            nodes.append(node)

        return nodes

    def _build_spec_nodes(self) -> list[GraphNode]:
        """Build nodes for individual spec files."""
        nodes = []
        specs_dir = self.workspace_path / ".kiro" / "specs"

        if not specs_dir.exists():
            return nodes

        for spec_file in specs_dir.rglob("*.md"):
            # Get spec type from filename
            spec_type = spec_file.stem  # requirements, design, tasks
            feature_name = spec_file.parent.name

            node = GraphNode(
                id=f"spec:{feature_name}/{spec_type}",
                type=NodeType.SPEC,
                label=f"{feature_name}: {spec_type}",
                metadata={
                    "path": str(spec_file.relative_to(self.workspace_path)),
                    "feature": feature_name,
                    "spec_type": spec_type,
                },
            )
            nodes.append(node)

        return nodes

    def _build_code_nodes(self) -> list[GraphNode]:
        """Build nodes for code files from impact graph or by scanning workspace."""
        nodes = []
        code_files: set[str] = set()

        # Try to load from impact graph first
        try:
            from specmem.impact.graph import SpecImpactGraph
            from specmem.impact.graph_models import NodeType as ImpactNodeType

            graph_path = self.workspace_path / ".specmem" / "impact_graph.json"
            if graph_path.exists():
                graph = SpecImpactGraph(graph_path)
                graph.load()

                # Get code nodes from the graph
                for node_id, node in graph.nodes.items():
                    if node.type == ImpactNodeType.CODE:
                        # Extract path from node id (format: "code:path/to/file.py")
                        if node_id.startswith("code:"):
                            code_files.add(node_id[5:])
                        else:
                            code_files.add(node_id)

        except Exception as e:
            logger.debug(f"Could not load impact graph: {e}")

        # If no code files from graph, scan for Python files in specmem/
        if not code_files:
            src_dir = self.workspace_path / "specmem"
            if src_dir.exists():
                for py_file in src_dir.rglob("*.py"):
                    if "__pycache__" not in str(py_file):
                        rel_path = str(py_file.relative_to(self.workspace_path))
                        code_files.add(rel_path)

        # Create nodes for code files
        for code_path in code_files:
            path = Path(code_path)
            node = GraphNode(
                id=f"code:{code_path}",
                type=NodeType.CODE,
                label=path.name,
                metadata={
                    "path": code_path,
                    "extension": path.suffix,
                },
            )
            nodes.append(node)

        return nodes

    def _build_test_nodes(self) -> list[GraphNode]:
        """Build nodes for test files."""
        nodes = []
        tests_dir = self.workspace_path / "tests"

        if not tests_dir.exists():
            return nodes

        for test_file in tests_dir.rglob("test_*.py"):
            rel_path = str(test_file.relative_to(self.workspace_path))
            node = GraphNode(
                id=f"test:{rel_path}",
                type=NodeType.TEST,
                label=test_file.stem,
                metadata={
                    "path": rel_path,
                },
            )
            nodes.append(node)

        return nodes

    def _build_feature_spec_edges(
        self, features: list[GraphNode], specs: list[GraphNode]
    ) -> list[GraphEdge]:
        """Build edges from features to their specs."""
        edges = []

        for spec in specs:
            feature_name = spec.metadata.get("feature")
            if feature_name:
                feature_id = f"feature:{feature_name}"
                # Check if feature exists
                if any(f.id == feature_id for f in features):
                    edge = GraphEdge(
                        source=feature_id,
                        target=spec.id,
                        relationship=EdgeType.CONTAINS,
                    )
                    edges.append(edge)

        return edges

    def _build_spec_code_edges(
        self, specs: list[GraphNode], code_nodes: list[GraphNode]
    ) -> list[GraphEdge]:
        """Build edges from specs to code files using heuristics."""
        edges = []
        code_node_ids = {c.id for c in code_nodes}

        # Build edges using name matching heuristics
        for spec in specs:
            feature_name = spec.metadata.get("feature", "")
            if not feature_name:
                continue

            # Convert feature name to possible module names
            # e.g., "streaming-context-api" -> ["streaming_context_api", "context", "streaming"]
            feature_parts = feature_name.replace("-", "_").split("_")

            for code in code_nodes:
                code_path = code.metadata.get("path", "")
                code_name = Path(code_path).stem

                # Check if any feature part matches the code file name
                for part in feature_parts:
                    if len(part) > 3 and part in code_name.lower():
                        edge = GraphEdge(
                            source=spec.id,
                            target=code.id,
                            relationship=EdgeType.IMPLEMENTS,
                        )
                        edges.append(edge)
                        break

        return edges

    def _build_code_test_edges(
        self, code_nodes: list[GraphNode], test_nodes: list[GraphNode]
    ) -> list[GraphEdge]:
        """Build edges from code files to test files."""
        edges = []

        # Simple heuristic: match test files to code files by name
        for code in code_nodes:
            code_name = Path(code.metadata.get("path", "")).stem

            for test in test_nodes:
                test_name = test.metadata.get("path", "")
                # Check if test name contains code name
                if code_name in test_name:
                    edge = GraphEdge(
                        source=code.id,
                        target=test.id,
                        relationship=EdgeType.TESTED_BY,
                    )
                    edges.append(edge)

        return edges
