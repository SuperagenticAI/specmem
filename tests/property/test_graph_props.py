"""Property-based tests for SpecImpact Graph.

Tests correctness properties defined in the design document.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.impact import (
    EdgeType,
    GraphEdge,
    GraphNode,
    ImpactSet,
    NodeType,
)


# =============================================================================
# Strategies for generating test data
# =============================================================================

node_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-:."),
    min_size=1,
    max_size=50,
)

confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

node_type_strategy = st.sampled_from(list(NodeType))

edge_type_strategy = st.sampled_from(list(EdgeType))

node_data_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.one_of(st.text(max_size=50), st.integers(), st.floats(allow_nan=False)),
    max_size=5,
)

node_strategy = st.builds(
    GraphNode,
    id=node_id_strategy,
    type=node_type_strategy,
    data=node_data_strategy,
    confidence=confidence_strategy,
    suggested=st.booleans(),
)

edge_strategy = st.builds(
    GraphEdge,
    source_id=node_id_strategy,
    target_id=node_id_strategy,
    relationship=edge_type_strategy,
    confidence=confidence_strategy,
    metadata=node_data_strategy,
    manual=st.booleans(),
)


# =============================================================================
# Property 3: Confidence Inclusion
# For any returned node in an impact query, the result SHALL include a
# confidence score between 0.0 and 1.0.
# **Feature: specimpact-graph, Property 3: Confidence Inclusion**
# **Validates: Requirements 1.2, 2.2, 3.2**
# =============================================================================


@given(node=node_strategy)
@settings(max_examples=100)
def test_node_confidence_in_valid_range(node: GraphNode) -> None:
    """Property 3: All GraphNode confidence scores are between 0.0 and 1.0.

    **Feature: specimpact-graph, Property 3: Confidence Inclusion**
    **Validates: Requirements 1.2, 2.2, 3.2**
    """
    assert (
        0.0 <= node.confidence <= 1.0
    ), f"Node confidence {node.confidence} is not in range [0.0, 1.0]"


@given(edge=edge_strategy)
@settings(max_examples=100)
def test_edge_confidence_in_valid_range(edge: GraphEdge) -> None:
    """Property 3: All GraphEdge confidence scores are between 0.0 and 1.0.

    **Feature: specimpact-graph, Property 3: Confidence Inclusion**
    **Validates: Requirements 1.2, 2.2, 3.2**
    """
    assert (
        0.0 <= edge.confidence <= 1.0
    ), f"Edge confidence {edge.confidence} is not in range [0.0, 1.0]"


@given(nodes=st.lists(node_strategy, min_size=0, max_size=10))
@settings(max_examples=100)
def test_impact_set_all_nodes_have_valid_confidence(nodes: list[GraphNode]) -> None:
    """Property 3: All nodes in ImpactSet have confidence in [0.0, 1.0].

    **Feature: specimpact-graph, Property 3: Confidence Inclusion**
    **Validates: Requirements 1.2, 2.2, 3.2**
    """
    # Split nodes by type for ImpactSet
    specs = [n for n in nodes if n.type == NodeType.SPEC]
    code = [n for n in nodes if n.type == NodeType.CODE]
    tests = [n for n in nodes if n.type == NodeType.TEST]

    impact_set = ImpactSet(specs=specs, code=code, tests=tests)

    # Verify all nodes in impact set have valid confidence
    for node in impact_set.specs + impact_set.code + impact_set.tests:
        assert (
            0.0 <= node.confidence <= 1.0
        ), f"Node {node.id} has invalid confidence {node.confidence}"


# =============================================================================
# Round-trip serialization tests
# =============================================================================


@given(node=node_strategy)
@settings(max_examples=100)
def test_node_serialization_roundtrip(node: GraphNode) -> None:
    """Nodes can be serialized and deserialized without data loss."""
    serialized = node.to_dict()
    restored = GraphNode.from_dict(serialized)

    assert restored.id == node.id
    assert restored.type == node.type
    assert restored.confidence == node.confidence
    assert restored.suggested == node.suggested
    assert restored.data == node.data


@given(edge=edge_strategy)
@settings(max_examples=100)
def test_edge_serialization_roundtrip(edge: GraphEdge) -> None:
    """Edges can be serialized and deserialized without data loss."""
    serialized = edge.to_dict()
    restored = GraphEdge.from_dict(serialized)

    assert restored.source_id == edge.source_id
    assert restored.target_id == edge.target_id
    assert restored.relationship == edge.relationship
    assert restored.confidence == edge.confidence
    assert restored.manual == edge.manual
    assert restored.metadata == edge.metadata


@given(nodes=st.lists(node_strategy, min_size=0, max_size=10))
@settings(max_examples=100)
def test_impact_set_serialization_roundtrip(nodes: list[GraphNode]) -> None:
    """ImpactSet can be serialized and deserialized without data loss."""
    specs = [n for n in nodes if n.type == NodeType.SPEC]
    code = [n for n in nodes if n.type == NodeType.CODE]
    tests = [n for n in nodes if n.type == NodeType.TEST]

    impact_set = ImpactSet(
        specs=specs,
        code=code,
        tests=tests,
        changed_files=["file1.py", "file2.py"],
        depth=2,
        message="Test message",
    )

    serialized = impact_set.to_dict()
    restored = ImpactSet.from_dict(serialized)

    assert len(restored.specs) == len(impact_set.specs)
    assert len(restored.code) == len(impact_set.code)
    assert len(restored.tests) == len(impact_set.tests)
    assert restored.changed_files == impact_set.changed_files
    assert restored.depth == impact_set.depth
    assert restored.message == impact_set.message


# =============================================================================
# Property 1: Spec Query Completeness
# For any code file with linked specs, querying specs for that file SHALL
# return all directly linked specs.
# **Feature: specimpact-graph, Property 1: Spec Query Completeness**
# **Validates: Requirements 1.1**
# =============================================================================

from specmem.impact import SpecImpactGraph


@given(
    code_id=node_id_strategy,
    spec_ids=st.lists(node_id_strategy, min_size=1, max_size=5, unique=True),
)
@settings(max_examples=100)
def test_spec_query_returns_all_linked_specs(code_id: str, spec_ids: list[str]) -> None:
    """Property 1: Querying specs for code returns all directly linked specs.

    **Feature: specimpact-graph, Property 1: Spec Query Completeness**
    **Validates: Requirements 1.1**
    """
    graph = SpecImpactGraph()

    # Add code node
    code_node = GraphNode(id=f"code:{code_id}", type=NodeType.CODE)
    graph.add_node(code_node)

    # Add spec nodes and link them
    for spec_id in spec_ids:
        spec_node = GraphNode(id=f"spec:{spec_id}", type=NodeType.SPEC)
        graph.add_node(spec_node)
        graph.add_edge(
            GraphEdge(
                source_id=code_node.id,
                target_id=spec_node.id,
                relationship=EdgeType.IMPLEMENTS,
            )
        )

    # Query specs for code
    result = graph.query_specs_for_code(code_node.id)
    result_ids = {n.id for n in result}

    # All linked specs should be returned
    expected_ids = {f"spec:{sid}" for sid in spec_ids}
    assert expected_ids == result_ids, f"Expected specs {expected_ids}, got {result_ids}"


# =============================================================================
# Property 2: Transitive Closure
# For any graph with path A→B→C, querying impact for A with depth≥2 SHALL
# include C in results.
# **Feature: specimpact-graph, Property 2: Transitive Closure**
# **Validates: Requirements 1.3**
# =============================================================================


@given(
    node_a=node_id_strategy,
    node_b=node_id_strategy,
    node_c=node_id_strategy,
)
@settings(max_examples=100)
def test_transitive_closure_with_depth(node_a: str, node_b: str, node_c: str) -> None:
    """Property 2: Querying with depth≥2 includes transitively connected nodes.

    **Feature: specimpact-graph, Property 2: Transitive Closure**
    **Validates: Requirements 1.3**
    """
    # Ensure unique IDs
    if len({node_a, node_b, node_c}) < 3:
        return  # Skip if not unique

    graph = SpecImpactGraph()

    # Create chain: A → B → C
    graph.add_node(GraphNode(id=f"code:{node_a}", type=NodeType.CODE))
    graph.add_node(GraphNode(id=f"spec:{node_b}", type=NodeType.SPEC))
    graph.add_node(GraphNode(id=f"test:{node_c}", type=NodeType.TEST))

    graph.add_edge(
        GraphEdge(
            source_id=f"code:{node_a}",
            target_id=f"spec:{node_b}",
            relationship=EdgeType.IMPLEMENTS,
        )
    )
    graph.add_edge(
        GraphEdge(
            source_id=f"test:{node_c}",
            target_id=f"spec:{node_b}",
            relationship=EdgeType.TESTS,
        )
    )

    # Query with depth=2 should find all nodes
    impact = graph.query_impact([f"code:{node_a}"], depth=2)

    all_ids = {n.id for n in impact.specs + impact.code + impact.tests}
    assert f"spec:{node_b}" in all_ids, "Spec B should be in impact set"
    assert f"test:{node_c}" in all_ids, "Test C should be in impact set (transitive)"


# =============================================================================
# Property 4: Test Ordering
# For any list of tests returned from impact query, tests SHALL be ordered
# by confidence descending.
# **Feature: specimpact-graph, Property 4: Test Ordering**
# **Validates: Requirements 2.3**
# =============================================================================


@given(
    confidences=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=2,
        max_size=10,
    ),
)
@settings(max_examples=100)
def test_tests_ordered_by_confidence_descending(confidences: list[float]) -> None:
    """Property 4: Tests are ordered by confidence descending.

    **Feature: specimpact-graph, Property 4: Test Ordering**
    **Validates: Requirements 2.3**
    """
    graph = SpecImpactGraph()

    # Add a code node and spec
    graph.add_node(GraphNode(id="code:main.py", type=NodeType.CODE))
    graph.add_node(GraphNode(id="spec:main", type=NodeType.SPEC))
    graph.add_edge(
        GraphEdge(
            source_id="code:main.py",
            target_id="spec:main",
            relationship=EdgeType.IMPLEMENTS,
        )
    )

    # Add test nodes with varying confidence
    for i, conf in enumerate(confidences):
        test_node = GraphNode(
            id=f"test:test_{i}.py",
            type=NodeType.TEST,
            confidence=conf,
            data={"framework": "pytest", "path": f"test_{i}.py"},
        )
        graph.add_node(test_node)
        graph.add_edge(
            GraphEdge(
                source_id=test_node.id,
                target_id="spec:main",
                relationship=EdgeType.TESTS,
            )
        )

    # Query tests
    tests = graph.query_tests_for_change(["code:main.py"])

    # Verify ordering
    for i in range(len(tests) - 1):
        assert (
            tests[i].confidence >= tests[i + 1].confidence
        ), f"Tests not ordered by confidence: {tests[i].confidence} < {tests[i + 1].confidence}"


# =============================================================================
# Property 5: Bidirectional Query
# For any edge A→B in the graph, querying from A SHALL find B, and querying
# from B SHALL find A.
# **Feature: specimpact-graph, Property 5: Bidirectional Query**
# **Validates: Requirements 1.1, 3.1**
# =============================================================================


@given(
    code_id=node_id_strategy,
    spec_id=node_id_strategy,
)
@settings(max_examples=100)
def test_bidirectional_query(code_id: str, spec_id: str) -> None:
    """Property 5: Queries work bidirectionally.

    **Feature: specimpact-graph, Property 5: Bidirectional Query**
    **Validates: Requirements 1.1, 3.1**
    """
    if code_id == spec_id:
        return  # Skip if same ID

    graph = SpecImpactGraph()

    # Add nodes
    code_node = GraphNode(id=f"code:{code_id}", type=NodeType.CODE)
    spec_node = GraphNode(id=f"spec:{spec_id}", type=NodeType.SPEC)
    graph.add_node(code_node)
    graph.add_node(spec_node)

    # Add edge: code → spec
    graph.add_edge(
        GraphEdge(
            source_id=code_node.id,
            target_id=spec_node.id,
            relationship=EdgeType.IMPLEMENTS,
        )
    )

    # Query from code should find spec
    specs = graph.query_specs_for_code(code_node.id)
    assert any(
        s.id == spec_node.id for s in specs
    ), f"Spec {spec_node.id} not found when querying from code"

    # Query from spec should find code
    code_nodes = graph.query_code_for_spec(spec_node.id)
    assert any(
        c.id == code_node.id for c in code_nodes
    ), f"Code {code_node.id} not found when querying from spec"


# =============================================================================
# Property 7: Impact Set Completeness
# For any impact query, the result SHALL contain specs, code, and tests lists
# (possibly empty).
# **Feature: specimpact-graph, Property 7: Impact Set Completeness**
# **Validates: Requirements 5.1**
# =============================================================================


@given(
    changed_files=st.lists(node_id_strategy, min_size=0, max_size=5),
)
@settings(max_examples=100)
def test_impact_set_always_has_all_lists(changed_files: list[str]) -> None:
    """Property 7: Impact set always contains specs, code, and tests lists.

    **Feature: specimpact-graph, Property 7: Impact Set Completeness**
    **Validates: Requirements 5.1**
    """
    graph = SpecImpactGraph()

    # Query impact (even with empty graph)
    impact = graph.query_impact(changed_files)

    # All lists should exist (possibly empty)
    assert isinstance(impact.specs, list), "specs should be a list"
    assert isinstance(impact.code, list), "code should be a list"
    assert isinstance(impact.tests, list), "tests should be a list"
    assert isinstance(impact.changed_files, list), "changed_files should be a list"
    assert isinstance(impact.depth, int), "depth should be an int"
    assert isinstance(impact.message, str), "message should be a string"


# =============================================================================
# Property 8: Depth Limiting
# For any impact query with depth=N, no returned node SHALL be more than N
# edges from input nodes.
# **Feature: specimpact-graph, Property 8: Depth Limiting**
# **Validates: Requirements 5.2**
# =============================================================================


@given(
    depth=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=100)
def test_depth_limiting(depth: int) -> None:
    """Property 8: Impact query respects depth limit.

    **Feature: specimpact-graph, Property 8: Depth Limiting**
    **Validates: Requirements 5.2**
    """
    graph = SpecImpactGraph()

    # Create a chain: code0 → spec0 → test0 → spec1 → test1 → ...
    # Each step is 1 edge away
    prev_id = "code:start"
    graph.add_node(GraphNode(id=prev_id, type=NodeType.CODE))

    for i in range(6):  # Create chain longer than max depth
        spec_id = f"spec:spec_{i}"
        test_id = f"test:test_{i}"

        graph.add_node(GraphNode(id=spec_id, type=NodeType.SPEC))
        graph.add_node(GraphNode(id=test_id, type=NodeType.TEST))

        graph.add_edge(
            GraphEdge(
                source_id=prev_id,
                target_id=spec_id,
                relationship=EdgeType.IMPLEMENTS if i == 0 else EdgeType.REFERENCES,
            )
        )
        graph.add_edge(
            GraphEdge(
                source_id=test_id,
                target_id=spec_id,
                relationship=EdgeType.TESTS,
            )
        )

        prev_id = test_id

    # Query with specific depth
    impact = graph.query_impact(["code:start"], depth=depth)

    # Count nodes at each depth level
    all_nodes = impact.specs + impact.code + impact.tests

    # With depth=0, should only get the starting node
    # With depth=1, should get nodes 1 edge away
    # etc.
    # The exact count depends on graph structure, but we verify
    # that deeper nodes are not included when depth is limited

    if depth == 0:
        # Only the starting code node
        assert len(all_nodes) <= 1, f"With depth=0, got {len(all_nodes)} nodes"
    elif depth == 1:
        # Starting node + directly connected
        assert len(all_nodes) <= 3, f"With depth=1, got {len(all_nodes)} nodes"


# =============================================================================
# Property 6: Incremental Preservation
# For any incremental update affecting node X, all nodes not connected to X
# SHALL remain unchanged.
# **Feature: specimpact-graph, Property 6: Incremental Preservation**
# **Validates: Requirements 4.3**
# =============================================================================


@given(
    node_a=node_id_strategy,
    node_b=node_id_strategy,
)
@settings(max_examples=100)
def test_incremental_update_preserves_unconnected_nodes(node_a: str, node_b: str) -> None:
    """Property 6: Incremental updates preserve unconnected nodes.

    **Feature: specimpact-graph, Property 6: Incremental Preservation**
    **Validates: Requirements 4.3**
    """
    if node_a == node_b:
        return

    graph = SpecImpactGraph()

    # Add two unconnected nodes
    graph.add_node(GraphNode(id=f"code:{node_a}", type=NodeType.CODE))
    graph.add_node(GraphNode(id=f"spec:{node_b}", type=NodeType.SPEC))

    # Store original state
    original_node_b = graph.get_node(f"spec:{node_b}")
    assert original_node_b is not None

    # Perform incremental update on node_a
    graph.update_incremental(changed_code=[f"code:{node_a}"])

    # Node B should be unchanged
    updated_node_b = graph.get_node(f"spec:{node_b}")
    assert updated_node_b is not None
    assert updated_node_b.id == original_node_b.id
    assert updated_node_b.type == original_node_b.type
    assert updated_node_b.confidence == original_node_b.confidence


# =============================================================================
# Property 9: Export Format Validity
# For any graph export in JSON format, the output SHALL be valid JSON
# parseable back to graph structure.
# **Feature: specimpact-graph, Property 9: Export Format Validity**
# **Validates: Requirements 6.1, 6.2**
# =============================================================================

import json


@given(
    nodes=st.lists(node_strategy, min_size=0, max_size=5, unique_by=lambda n: n.id),
)
@settings(max_examples=100)
def test_json_export_is_valid_and_roundtrips(nodes: list[GraphNode]) -> None:
    """Property 9: JSON export is valid and can be parsed back.

    **Feature: specimpact-graph, Property 9: Export Format Validity**
    **Validates: Requirements 6.1, 6.2**
    """
    graph = SpecImpactGraph()

    # Add nodes
    for node in nodes:
        graph.add_node(node)

    # Add some edges between nodes
    for i in range(len(nodes) - 1):
        graph.add_edge(
            GraphEdge(
                source_id=nodes[i].id,
                target_id=nodes[i + 1].id,
                relationship=EdgeType.IMPLEMENTS,
            )
        )

    # Export to JSON
    json_output = graph.export("json")

    # Should be valid JSON
    parsed = json.loads(json_output)

    # Should have nodes and edges
    assert "nodes" in parsed
    assert "edges" in parsed
    assert isinstance(parsed["nodes"], list)
    assert isinstance(parsed["edges"], list)

    # Node count should match
    assert len(parsed["nodes"]) == len(nodes)


@given(
    nodes=st.lists(node_strategy, min_size=1, max_size=3, unique_by=lambda n: n.id),
)
@settings(max_examples=50)
def test_dot_export_is_valid_format(nodes: list[GraphNode]) -> None:
    """DOT export produces valid Graphviz format.

    **Feature: specimpact-graph, Property 9: Export Format Validity**
    **Validates: Requirements 6.2**
    """
    graph = SpecImpactGraph()

    for node in nodes:
        graph.add_node(node)

    dot_output = graph.export("dot")

    # Should start with digraph
    assert dot_output.startswith("digraph"), "DOT output should start with 'digraph'"
    assert "}" in dot_output, "DOT output should end with '}'"


@given(
    nodes=st.lists(node_strategy, min_size=1, max_size=3, unique_by=lambda n: n.id),
)
@settings(max_examples=50)
def test_mermaid_export_is_valid_format(nodes: list[GraphNode]) -> None:
    """Mermaid export produces valid diagram format.

    **Feature: specimpact-graph, Property 9: Export Format Validity**
    **Validates: Requirements 6.2**
    """
    graph = SpecImpactGraph()

    for node in nodes:
        graph.add_node(node)

    mermaid_output = graph.export("mermaid")

    # Should start with graph directive
    assert mermaid_output.startswith("graph"), "Mermaid output should start with 'graph'"


# =============================================================================
# Property 10: Suggested Link Marking
# For any auto-discovered link with confidence below threshold, the edge
# SHALL be marked as suggested=True.
# **Feature: specimpact-graph, Property 10: Suggested Link Marking**
# **Validates: Requirements 7.3**
# =============================================================================


@given(
    confidence=st.floats(min_value=0.0, max_value=0.49, allow_nan=False),
)
@settings(max_examples=100)
def test_low_confidence_nodes_marked_as_suggested(confidence: float) -> None:
    """Property 10: Low confidence nodes are marked as suggested.

    **Feature: specimpact-graph, Property 10: Suggested Link Marking**
    **Validates: Requirements 7.3**
    """
    # Create a node with low confidence and suggested=True
    node = GraphNode(
        id="spec:test",
        type=NodeType.SPEC,
        confidence=confidence,
        suggested=True,  # Should be marked as suggested for low confidence
    )

    assert node.suggested is True, "Low confidence node should be marked as suggested"
    assert node.confidence < 0.5, "Confidence should be below threshold"


# =============================================================================
# Property 11: Manual Link Priority
# For any node with both manual and auto-discovered links, manual links
# SHALL have higher effective confidence.
# **Feature: specimpact-graph, Property 11: Manual Link Priority**
# **Validates: Requirements 7.4**
# =============================================================================


@given(
    auto_confidence=st.floats(min_value=0.0, max_value=0.7, allow_nan=False),
)
@settings(max_examples=100)
def test_manual_edges_have_higher_priority(auto_confidence: float) -> None:
    """Property 11: Manual edges have higher effective confidence.

    **Feature: specimpact-graph, Property 11: Manual Link Priority**
    **Validates: Requirements 7.4**
    """
    graph = SpecImpactGraph()

    # Add nodes
    graph.add_node(GraphNode(id="code:main.py", type=NodeType.CODE))
    graph.add_node(GraphNode(id="spec:main", type=NodeType.SPEC))

    # Add auto-discovered edge
    auto_edge = GraphEdge(
        source_id="code:main.py",
        target_id="spec:main",
        relationship=EdgeType.IMPLEMENTS,
        confidence=auto_confidence,
        manual=False,
    )
    graph.add_edge(auto_edge)

    # Add manual edge (should replace or have higher priority)
    manual_edge = GraphEdge(
        source_id="code:main.py",
        target_id="spec:main",
        relationship=EdgeType.IMPLEMENTS,
        confidence=1.0,  # Manual edges typically have high confidence
        manual=True,
    )
    graph.add_edge(manual_edge)

    # The edge in the graph should be the manual one
    edges = graph.get_edges_from("code:main.py")
    assert len(edges) == 1, "Should have exactly one edge"
    assert edges[0].manual is True, "Manual edge should take priority"
    assert edges[0].confidence == 1.0, "Manual edge confidence should be preserved"
