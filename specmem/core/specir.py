"""SpecIR - Canonical Spec Intermediate Representation.

This module defines the core data models for SpecMem's unified specification
representation. All specs from different frameworks are normalized into
SpecBlock structures.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import TYPE_CHECKING, Any, Self

from pydantic import BaseModel, Field, field_validator


if TYPE_CHECKING:
    from specmem.core.mappings import CodeRef, TestMapping


class SpecType(str, Enum):
    """Classification of specification block types."""

    REQUIREMENT = "requirement"
    DESIGN = "design"
    TASK = "task"
    DECISION = "decision"
    KNOWLEDGE = "knowledge"
    MD = "md"


class SpecStatus(str, Enum):
    """Lifecycle status of a specification block.

    States:
        ACTIVE: Currently valid and included in queries
        DEPRECATED: Still valid but marked for future removal
        LEGACY: Excluded from standard queries, available with flag
        OBSOLETE: Excluded from all queries
    """

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    LEGACY = "legacy"
    OBSOLETE = "obsolete"


class SpecBlock(BaseModel):
    """Canonical representation of a specification unit.

    SpecBlock is the universal format that all spec frameworks are normalized
    into. It enables uniform retrieval and guaranteed compatibility across
    different coding agents.

    Attributes:
        id: Unique deterministic ID based on source and content hash
        type: Classification of the spec block (requirement, design, etc.)
        text: Content of the specification
        source: Source file path where this spec originated
        status: Lifecycle status (active, deprecated, legacy, obsolete)
        tags: List of tags for categorization
        links: List of related SpecBlock IDs
        pinned: Whether this block is in deterministic memory (guaranteed recall)
        test_mappings: List of tests that validate this spec
        code_refs: List of code references implementing this spec
        confidence: Overall confidence score for this spec (0.0-1.0)
    """

    id: str = Field(..., description="Unique deterministic ID")
    type: SpecType = Field(..., description="Classification of the spec block")
    text: str = Field(..., min_length=1, description="Content of the specification")
    source: str = Field(..., description="Source file path")
    status: SpecStatus = Field(default=SpecStatus.ACTIVE)
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list, description="Related SpecBlock IDs")
    pinned: bool = Field(default=False, description="Deterministic memory flag")
    test_mappings: list[dict[str, Any]] = Field(
        default_factory=list, description="Tests validating this spec"
    )
    code_refs: list[dict[str, Any]] = Field(
        default_factory=list, description="Code implementing this spec"
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """Validate that text is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("text cannot be empty or whitespace only")
        return v

    @classmethod
    def generate_id(cls, source: str, text: str) -> str:
        """Generate deterministic ID from source and content.

        The ID is a 16-character hex string derived from SHA-256 hash
        of the source path and text content combined.

        Args:
            source: Source file path
            text: Content text

        Returns:
            16-character deterministic ID
        """
        content = f"{source}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation of the SpecBlock
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Deserialize from JSON string.

        Args:
            json_str: JSON string to parse

        Returns:
            SpecBlock instance
        """
        return cls.model_validate_json(json_str)

    def __str__(self) -> str:
        """Human-readable string representation."""
        status_marker = "" if self.status == SpecStatus.ACTIVE else f" [{self.status.value}]"
        pinned_marker = " 📌" if self.pinned else ""
        return f"[{self.type.value}]{status_marker}{pinned_marker} {self.text[:50]}..."

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"SpecBlock(id={self.id!r}, type={self.type.value!r}, "
            f"source={self.source!r}, status={self.status.value!r})"
        )

    def get_test_mappings(self) -> list[TestMapping]:
        """Get test mappings as TestMapping objects.

        Returns:
            List of TestMapping objects
        """
        from specmem.core.mappings import TestMapping

        return [TestMapping.from_dict(m) for m in self.test_mappings]

    def set_test_mappings(self, mappings: list[TestMapping]) -> None:
        """Set test mappings from TestMapping objects.

        Args:
            mappings: List of TestMapping objects
        """
        self.test_mappings = [m.to_dict() for m in mappings]

    def add_test_mapping(self, mapping: TestMapping) -> None:
        """Add a test mapping.

        Args:
            mapping: TestMapping to add
        """
        self.test_mappings.append(mapping.to_dict())

    def get_code_refs(self) -> list[CodeRef]:
        """Get code references as CodeRef objects.

        Returns:
            List of CodeRef objects
        """
        from specmem.core.mappings import CodeRef

        return [CodeRef.from_dict(r) for r in self.code_refs]

    def set_code_refs(self, refs: list[CodeRef]) -> None:
        """Set code references from CodeRef objects.

        Args:
            refs: List of CodeRef objects
        """
        self.code_refs = [r.to_dict() for r in refs]

    def add_code_ref(self, ref: CodeRef) -> None:
        """Add a code reference.

        Args:
            ref: CodeRef to add
        """
        self.code_refs.append(ref.to_dict())
