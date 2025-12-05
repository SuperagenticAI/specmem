"""Property-based tests for Impact Graph Visualization.

**Feature: project-polish**
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from specmem.graph.models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    ImpactGraphData,
    NodeType,
)


# Strategies for generating graph data
node_type_strategy = st.sampled_from(list(NodeType))
edge_type_strategy = st.sampled_from(list(EdgeType))


def node_strategy(node_type: NodeType | None = None):
    """Strategy for generating graph nodes."""
    return st.builds(
        GraphNode,
        id=st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-:"
            ),
        ),
        type=st.just(node_type) if node_type else node_type_strategy,
        label=st.text(min_size=1, max_size=50),
        metadata=st.just({}),
    )


class TestGraphFilterConsistency:
    """Property tests for graph filtering.

    **Feature: project-polish, Property 6: Graph Filter Consistency**
    **Validates: Requirements 2.5**
    """

    @given(
        num_nodes=st.integers(min_value=1, max_value=20),
        filter_types=st.lists(node_type_strategy, min_size=1, max_size=4, unique=True),
    )
    @settings(max_examples=100)
    def test_filter_preserves_matching_nodes(self, num_nodes: int, filter_types: list[NodeType]):
        """Filtered graph should contain exactly nodes matching filter."""
        # Create nodes with various types
        nodes = []
        for i in range(num_nodes):
            node_type = list(NodeType)[i % len(NodeType)]
            nodes.append(
                GraphNode(
                    id=f"node_{i}",
                    type=node_type,
                    label=f"Node {i}",
                )
            )

        graph = ImpactGraphData(nodes=nodes, edges=[])
        filtered = graph.filter_by_type(filter_types)

        # All filtered nodes should have matching type
        for node in filtered.nodes:
            assert (
                node.type in filter_types
            ), f"Node {node.id} has type {node.type} not in {filter_types}"

        # Count should match expected
        expected_count = sum(1 for n in nodes if n.type in filter_types)
        assert len(filtered.nodes) == expected_count

    @given(
        num_nodes=st.integers(min_value=2, max_value=10),
        filter_types=st.lists(node_type_strategy, min_size=1, max_size=2, unique=True),
    )
    @settings(max_examples=100)
    def test_filter_preserves_edges_between_visible_nodes(
        self, num_nodes: int, filter_types: list[NodeType]
    ):
        """Edges between visible nodes should be preserved after filtering."""
        # Create nodes
        nodes = []
        for i in range(num_nodes):
            node_type = list(NodeType)[i % len(NodeType)]
            nodes.append(
                GraphNode(
                    id=f"node_{i}",
                    type=node_type,
                    label=f"Node {i}",
                )
            )

        # Create edges between consecutive nodes
        edges = []
        for i in range(num_nodes - 1):
            edges.append(
                GraphEdge(
                    source=f"node_{i}",
                    target=f"node_{i + 1}",
                    relationship=EdgeType.IMPLEMENTS,
                )
            )

        graph = ImpactGraphData(nodes=nodes, edges=edges)
        filtered = graph.filter_by_type(filter_types)

        # Get IDs of filtered nodes
        filtered_ids = {n.id for n in filtered.nodes}

        # All edges in filtered graph should connect filtered nodes
        for edge in filtered.edges:
            assert edge.source in filtered_ids, f"Edge source {edge.source} not in filtered nodes"
            assert edge.target in filtered_ids, f"Edge target {edge.target} not in filtered nodes"

    @given(
        num_nodes=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_filter_with_all_types_preserves_all(self, num_nodes: int):
        """Filtering with all types should preserve all nodes."""
        nodes = []
        for i in range(num_nodes):
            node_type = list(NodeType)[i % len(NodeType)]
            nodes.append(
                GraphNode(
                    id=f"node_{i}",
                    type=node_type,
                    label=f"Node {i}",
                )
            )

        graph = ImpactGraphData(nodes=nodes, edges=[])
        filtered = graph.filter_by_type(list(NodeType))

        assert len(filtered.nodes) == len(graph.nodes)


class TestGraphConnectedNodes:
    """Property tests for finding connected nodes."""

    @given(
        num_nodes=st.integers(min_value=2, max_value=10),
        target_idx=st.integers(min_value=0, max_value=9),
    )
    @settings(max_examples=100)
    def test_connected_nodes_are_bidirectional(self, num_nodes: int, target_idx: int):
        """Connected nodes should include both incoming and outgoing edges."""
        assume(target_idx < num_nodes)

        # Create nodes
        nodes = [
            GraphNode(id=f"node_{i}", type=NodeType.SPEC, label=f"Node {i}")
            for i in range(num_nodes)
        ]

        # Create edges: each node connects to the next
        edges = []
        for i in range(num_nodes - 1):
            edges.append(
                GraphEdge(
                    source=f"node_{i}",
                    target=f"node_{i + 1}",
                    relationship=EdgeType.IMPLEMENTS,
                )
            )

        graph = ImpactGraphData(nodes=nodes, edges=edges)
        connected = graph.get_connected_nodes(f"node_{target_idx}")

        # Check expected connections
        expected = set()
        if target_idx > 0:
            expected.add(f"node_{target_idx - 1}")  # Incoming
        if target_idx < num_nodes - 1:
            expected.add(f"node_{target_idx + 1}")  # Outgoing

        assert connected == expected


class TestGraphSerialization:
    """Property tests for graph serialization."""

    @given(
        num_nodes=st.integers(min_value=0, max_value=10),
        num_edges=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=100)
    def test_to_dict_preserves_counts(self, num_nodes: int, num_edges: int):
        """to_dict should preserve node and edge counts."""
        nodes = [
            GraphNode(
                id=f"node_{i}",
                type=list(NodeType)[i % len(NodeType)],
                label=f"Node {i}",
            )
            for i in range(num_nodes)
        ]

        # Create valid edges (only if we have enough nodes)
        edges = []
        if num_nodes >= 2:
            for i in range(min(num_edges, num_nodes - 1)):
                edges.append(
                    GraphEdge(
                        source=f"node_{i}",
                        target=f"node_{i + 1}",
                        relationship=EdgeType.IMPLEMENTS,
                    )
                )

        graph = ImpactGraphData(nodes=nodes, edges=edges)
        data = graph.to_dict()

        assert data["stats"]["total_nodes"] == len(nodes)
        assert data["stats"]["total_edges"] == len(edges)
        assert len(data["nodes"]) == len(nodes)
        assert len(data["edges"]) == len(edges)
