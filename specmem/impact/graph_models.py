"""Graph data models for SpecImpact Graph.

Defines the core data structures for the bidirectional relationship graph
that connects specifications, code files, and tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Types of nodes in the SpecImpact graph."""

    SPEC = "spec"
    CODE = "code"
    TEST = "test"


class EdgeType(str, Enum):
    """Types of relationships between nodes in the graph."""

    IMPLEMENTS = "implements"  # Code implements spec
    TESTS = "tests"  # Test validates spec
    DEPENDS_ON = "depends_on"  # Code depends on code
    REFERENCES = "references"  # Spec references spec


@dataclass
class GraphNode:
    """Node in the SpecImpact graph.

    Represents a spec, code file, or test in the relationship graph.
    """

    id: str
    type: NodeType
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    suggested: bool = False

    def __post_init__(self) -> None:
        """Validate node data after initialization."""
        if not self.id:
            raise ValueError("Node id cannot be empty")
        if not isinstance(self.type, NodeType):
            self.type = NodeType(self.type)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize node to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "confidence": self.confidence,
            "suggested": self.suggested,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        """Deserialize node from dictionary."""
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            data=data.get("data", {}),
            confidence=data.get("confidence", 1.0),
            suggested=data.get("suggested", False),
        )


@dataclass
class GraphEdge:
    """Edge connecting two nodes in the SpecImpact graph.

    Represents a relationship between specs, code, and tests.
    """

    source_id: str
    target_id: str
    relationship: EdgeType
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    manual: bool = False

    def __post_init__(self) -> None:
        """Validate edge data after initialization."""
        if not self.source_id:
            raise ValueError("Edge source_id cannot be empty")
        if not self.target_id:
            raise ValueError("Edge target_id cannot be empty")
        if not isinstance(self.relationship, EdgeType):
            self.relationship = EdgeType(self.relationship)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize edge to dictionary."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship.value,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "manual": self.manual,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        """Deserialize edge from dictionary."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship=EdgeType(data["relationship"]),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            manual=data.get("manual", False),
        )


@dataclass
class ImpactSet:
    """Complete impact set for a change.

    Contains all specs, code, and tests affected by a set of file changes.
    """

    specs: list[GraphNode] = field(default_factory=list)
    code: list[GraphNode] = field(default_factory=list)
    tests: list[GraphNode] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    depth: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize impact set to dictionary."""
        return {
            "specs": [n.to_dict() for n in self.specs],
            "code": [n.to_dict() for n in self.code],
            "tests": [n.to_dict() for n in self.tests],
            "changed_files": self.changed_files,
            "depth": self.depth,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImpactSet:
        """Deserialize impact set from dictionary."""
        return cls(
            specs=[GraphNode.from_dict(n) for n in data.get("specs", [])],
            code=[GraphNode.from_dict(n) for n in data.get("code", [])],
            tests=[GraphNode.from_dict(n) for n in data.get("tests", [])],
            changed_files=data.get("changed_files", []),
            depth=data.get("depth", 0),
            message=data.get("message", ""),
        )

    def get_test_commands(self) -> dict[str, list[str]]:
        """Get test commands grouped by framework.

        Returns:
            Dictionary mapping framework names to lists of test file paths.
        """
        commands: dict[str, list[str]] = {}
        for test_node in self.tests:
            framework = test_node.data.get("framework", "unknown")
            path = test_node.data.get("path", test_node.id)
            if framework not in commands:
                commands[framework] = []
            commands[framework].append(path)
        return commands

    def is_empty(self) -> bool:
        """Check if the impact set is empty."""
        return not self.specs and not self.code and not self.tests
