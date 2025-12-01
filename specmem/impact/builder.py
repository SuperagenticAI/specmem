"""GraphBuilder - Builds SpecImpact graph from specs and code analysis.

Analyzes code files to discover relationships with specs and tests,
building a complete impact graph.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from specmem.impact.graph import SpecImpactGraph
from specmem.impact.graph_models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
)


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.testing.engine import TestMappingEngine

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds SpecImpact graph from specs and code analysis."""

    def __init__(
        self,
        workspace_path: Path | str,
        confidence_threshold: float = 0.5,
    ) -> None:
        """Initialize the builder.

        Args:
            workspace_path: Path to the workspace root.
            confidence_threshold: Minimum confidence for non-suggested links.
        """
        self.workspace_path = Path(workspace_path)
        self.confidence_threshold = confidence_threshold

    def build(
        self,
        specs: list[SpecBlock],
        test_engine: TestMappingEngine | None = None,
        storage_path: Path | str | None = None,
    ) -> SpecImpactGraph:
        """Build complete graph from specs and code.

        Args:
            specs: List of SpecBlocks to include.
            test_engine: Optional test mapping engine for test links.
            storage_path: Optional path to persist the graph.

        Returns:
            Built SpecImpactGraph.
        """
        graph = SpecImpactGraph(storage_path)

        # Add spec nodes
        for spec in specs:
            node = GraphNode(
                id=f"spec:{spec.id}",
                type=NodeType.SPEC,
                data={
                    "title": spec.title,
                    "source": spec.source,
                    "tags": spec.tags,
                },
            )
            graph.add_node(node)
            logger.debug(f"Added spec node: {node.id}")

        # Analyze code files for spec links
        self._analyze_code_files(graph, specs)

        # Link tests if engine provided
        if test_engine:
            self._link_tests(graph, specs, test_engine)

        # Save if storage path provided
        if storage_path:
            graph.save()

        logger.info(f"Built graph with {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph

    def _analyze_code_files(
        self,
        graph: SpecImpactGraph,
        specs: list[SpecBlock],
    ) -> None:
        """Analyze code files for spec links.

        Args:
            graph: Graph to add nodes/edges to.
            specs: Specs to link against.
        """
        # Build spec name index for matching
        spec_names: dict[str, str] = {}  # name -> spec_id
        for spec in specs:
            # Index by ID parts
            parts = spec.id.split(".")
            for part in parts:
                if part.lower() not in spec_names:
                    spec_names[part.lower()] = spec.id

            # Index by title words
            if spec.title:
                for word in spec.title.lower().split():
                    if len(word) > 3 and word not in spec_names:
                        spec_names[word] = spec.id

        # Find code files
        code_extensions = {".py", ".js", ".ts", ".tsx", ".jsx"}
        for ext in code_extensions:
            for code_file in self.workspace_path.rglob(f"*{ext}"):
                # Skip test files, node_modules, venv
                rel_path = code_file.relative_to(self.workspace_path)
                path_str = str(rel_path)

                if any(
                    skip in path_str
                    for skip in [
                        "node_modules",
                        ".venv",
                        "venv",
                        "__pycache__",
                        ".git",
                        "dist",
                        "build",
                    ]
                ):
                    continue

                # Analyze file for spec references
                edges = self.analyze_code_links(code_file, specs, spec_names)

                if edges:
                    # Add code node
                    code_node = GraphNode(
                        id=f"code:{path_str}",
                        type=NodeType.CODE,
                        data={"path": path_str},
                    )
                    graph.add_node(code_node)

                    # Add edges
                    for edge in edges:
                        graph.add_edge(edge)

    def analyze_code_links(
        self,
        code_file: Path,
        specs: list[SpecBlock],
        spec_names: dict[str, str] | None = None,
    ) -> list[GraphEdge]:
        """Analyze a code file for spec links.

        Args:
            code_file: Path to the code file.
            specs: Specs to match against.
            spec_names: Optional pre-built name index.

        Returns:
            List of edges linking code to specs.
        """
        edges: list[GraphEdge] = []

        try:
            content = code_file.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to read {code_file}: {e}")
            return edges

        rel_path = str(code_file.relative_to(self.workspace_path))
        code_id = f"code:{rel_path}"

        # Build spec name index if not provided
        if spec_names is None:
            spec_names = {}
            for spec in specs:
                parts = spec.id.split(".")
                for part in parts:
                    if part.lower() not in spec_names:
                        spec_names[part.lower()] = spec.id

        # Check for explicit spec references in comments
        spec_refs = self._find_spec_references(content)
        for spec_id, confidence in spec_refs:
            full_spec_id = f"spec:{spec_id}"
            edges.append(
                GraphEdge(
                    source_id=code_id,
                    target_id=full_spec_id,
                    relationship=EdgeType.IMPLEMENTS,
                    confidence=confidence,
                    metadata={"method": "explicit_reference"},
                    manual=False,
                )
            )

        # Check for naming convention matches
        file_name = code_file.stem.lower()
        for name, spec_id in spec_names.items():
            if name in file_name:
                confidence = self._calculate_name_confidence(name, file_name)
                if confidence >= 0.3:  # Minimum threshold
                    full_spec_id = f"spec:{spec_id}"
                    # Don't duplicate if already found
                    if not any(e.target_id == full_spec_id for e in edges):
                        edges.append(
                            GraphEdge(
                                source_id=code_id,
                                target_id=full_spec_id,
                                relationship=EdgeType.IMPLEMENTS,
                                confidence=confidence,
                                metadata={"method": "naming_convention"},
                                manual=False,
                            )
                        )

        return edges

    def _find_spec_references(self, content: str) -> list[tuple[str, float]]:
        """Find explicit spec references in code comments.

        Args:
            content: File content to search.

        Returns:
            List of (spec_id, confidence) tuples.
        """
        refs: list[tuple[str, float]] = []

        # Pattern: @spec spec_id or Spec: spec_id or implements: spec_id
        patterns = [
            (r"@spec\s+([a-zA-Z0-9_.]+)", 0.95),
            (r"Spec:\s*([a-zA-Z0-9_.]+)", 0.9),
            (r"implements:\s*([a-zA-Z0-9_.]+)", 0.9),
            (r"Requirement:\s*([a-zA-Z0-9_.]+)", 0.85),
        ]

        for pattern, confidence in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                refs.append((match, confidence))

        return refs

    def _calculate_name_confidence(self, spec_name: str, file_name: str) -> float:
        """Calculate confidence based on naming similarity.

        Args:
            spec_name: Spec name/part to match.
            file_name: Code file name.

        Returns:
            Confidence score 0.0-1.0.
        """
        # Exact match in file name
        if spec_name == file_name:
            return 0.8

        # Spec name is significant part of file name
        if len(spec_name) >= 4 and spec_name in file_name:
            ratio = len(spec_name) / len(file_name)
            return min(0.7, 0.4 + ratio * 0.3)

        return 0.3

    def _link_tests(
        self,
        graph: SpecImpactGraph,
        specs: list[SpecBlock],
        test_engine: TestMappingEngine,
    ) -> None:
        """Link tests to specs using test mappings.

        Args:
            graph: Graph to add nodes/edges to.
            specs: Specs to link.
            test_engine: Test mapping engine.
        """
        for spec in specs:
            spec_id = f"spec:{spec.id}"

            # Get test mappings for this spec
            if hasattr(spec, "test_mappings") and spec.test_mappings:
                for mapping in spec.test_mappings:
                    test_id = f"test:{mapping.path}"

                    # Add test node if not exists
                    if test_id not in graph.nodes:
                        test_node = GraphNode(
                            id=test_id,
                            type=NodeType.TEST,
                            data={
                                "framework": mapping.framework,
                                "path": mapping.path,
                                "selector": mapping.selector,
                            },
                        )
                        graph.add_node(test_node)

                    # Add edge
                    graph.add_edge(
                        GraphEdge(
                            source_id=test_id,
                            target_id=spec_id,
                            relationship=EdgeType.TESTS,
                            confidence=mapping.confidence,
                            metadata={"selector": mapping.selector},
                        )
                    )
