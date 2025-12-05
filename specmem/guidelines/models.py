"""Data models for coding guidelines."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    """Source type for coding guidelines."""

    CLAUDE = "claude"
    CURSOR = "cursor"
    STEERING = "steering"
    AGENTS = "agents"
    SAMPLE = "sample"


@dataclass
class Guideline:
    """A single coding guideline.

    Attributes:
        id: Unique identifier for the guideline
        title: Title or heading of the guideline
        content: Full content of the guideline
        source_type: Type of source (claude, cursor, steering, agents, sample)
        source_file: Path to the source file
        file_pattern: Glob pattern for files this guideline applies to
        tags: List of tags for categorization
        is_sample: Whether this is a sample guideline for demonstration
    """

    id: str
    title: str
    content: str
    source_type: SourceType
    source_file: str
    file_pattern: str | None = None
    tags: list[str] = field(default_factory=list)
    is_sample: bool = False

    @staticmethod
    def generate_id(source_file: str, title: str) -> str:
        """Generate a unique ID for a guideline.

        Args:
            source_file: Path to the source file
            title: Title of the guideline

        Returns:
            A unique hash-based ID
        """
        content = f"{source_file}:{title}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ConversionResult:
    """Result of converting a guideline to another format.

    Attributes:
        filename: Suggested filename for the converted content
        content: The converted content
        frontmatter: YAML frontmatter for steering files
        source_guideline: The original guideline that was converted
    """

    filename: str
    content: str
    frontmatter: dict[str, Any]
    source_guideline: Guideline


@dataclass
class GuidelinesResponse:
    """Response containing aggregated guidelines.

    Attributes:
        guidelines: List of all guidelines
        total_count: Total number of guidelines
        counts_by_source: Count of guidelines per source type
    """

    guidelines: list[Guideline]
    total_count: int
    counts_by_source: dict[str, int]

    @classmethod
    def from_guidelines(cls, guidelines: list[Guideline]) -> GuidelinesResponse:
        """Create a response from a list of guidelines.

        Args:
            guidelines: List of guidelines to aggregate

        Returns:
            GuidelinesResponse with computed counts
        """
        counts: dict[str, int] = {}
        for g in guidelines:
            source = g.source_type.value
            counts[source] = counts.get(source, 0) + 1

        return cls(
            guidelines=guidelines,
            total_count=len(guidelines),
            counts_by_source=counts,
        )
