"""Base interface for vector storage backends.

All vector stores must implement the VectorStore interface to be used
by SpecMem for storing and querying SpecBlocks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from specmem.core.specir import SpecStatus, SpecType


if TYPE_CHECKING:
    from datetime import datetime

    from specmem.core.specir import SpecBlock


# Valid lifecycle state transitions
VALID_TRANSITIONS: dict[SpecStatus, set[SpecStatus]] = {
    SpecStatus.ACTIVE: {SpecStatus.DEPRECATED, SpecStatus.LEGACY},
    SpecStatus.DEPRECATED: {SpecStatus.LEGACY, SpecStatus.ACTIVE},  # Can reactivate
    SpecStatus.LEGACY: {SpecStatus.OBSOLETE, SpecStatus.DEPRECATED},  # Can undeprecate
    SpecStatus.OBSOLETE: set(),  # Terminal state
}


@dataclass
class GovernanceRules:
    """Rules for controlling memory retrieval.

    Attributes:
        max_age_days: Exclude blocks older than this many days
        exclude_types: List of SpecTypes to exclude from results
        exclude_sources: List of source file patterns to exclude
        min_importance: Minimum importance score (AgentVectorDB only)
    """

    max_age_days: int | None = None
    exclude_types: list[SpecType] = field(default_factory=list)
    exclude_sources: list[str] = field(default_factory=list)
    min_importance: float | None = None

    def __post_init__(self) -> None:
        """Validate rule values."""
        if self.max_age_days is not None and self.max_age_days < 0:
            raise ValueError("max_age_days must be non-negative")
        if self.min_importance is not None and not (0.0 <= self.min_importance <= 1.0):
            raise ValueError("min_importance must be between 0.0 and 1.0")


@dataclass
class AuditEntry:
    """Record of an obsolete block for audit purposes.

    Attributes:
        block: The complete SpecBlock data
        obsoleted_at: Timestamp when block became obsolete
        reason: Reason for obsolescence
        previous_status: Status before becoming obsolete
        transition_history: List of all status transitions
    """

    block: SpecBlock
    obsoleted_at: datetime
    reason: str = ""
    previous_status: SpecStatus = SpecStatus.LEGACY
    transition_history: list[dict] = field(default_factory=list)


@dataclass
class QueryResult:
    """Result from a vector query.

    Attributes:
        block: The matching SpecBlock
        score: Similarity score (higher is more similar)
        distance: Distance metric (lower is more similar)
        deprecation_warning: Warning message if block is deprecated
        importance_score: Importance score from AgentVectorDB
    """

    block: SpecBlock
    score: float
    distance: float = 0.0
    deprecation_warning: str | None = None
    importance_score: float | None = None


def validate_transition(from_status: SpecStatus, to_status: SpecStatus) -> bool:
    """Validate if a lifecycle transition is allowed.

    Args:
        from_status: Current status
        to_status: Target status

    Returns:
        True if transition is valid
    """
    return to_status in VALID_TRANSITIONS.get(from_status, set())


class VectorStore(ABC):
    """Abstract interface for vector database backends.

    Implementations:
        - LanceDBStore: Default, uses DiskANN for fast search
        - AgentVectorDBStore: Advanced agent-optimized memory
        - ChromaDBStore: ChromaDB backend
        - QdrantStore: Qdrant backend
        - WeaviateStore: Weaviate backend
        - MilvusStore: Milvus backend
    """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the vector store and create schema if needed.

        This method should be called before any other operations.
        It should be idempotent (safe to call multiple times).
        """
        pass

    @abstractmethod
    def store(self, blocks: list[SpecBlock], embeddings: list[list[float]]) -> None:
        """Store SpecBlocks with their embeddings.

        Args:
            blocks: List of SpecBlock instances to store
            embeddings: Corresponding embedding vectors (same length as blocks)

        Raises:
            VectorStoreError: If storage fails
        """
        pass

    @abstractmethod
    def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        include_deprecated: bool = False,
        include_legacy: bool = False,
        governance_rules: GovernanceRules | None = None,
    ) -> list[QueryResult]:
        """Query for similar SpecBlocks by embedding vector.

        Args:
            embedding: Query embedding vector
            top_k: Maximum number of results to return
            include_deprecated: Whether to include deprecated blocks
            include_legacy: Whether to include legacy blocks
            governance_rules: Additional filtering rules

        Returns:
            List of QueryResult ordered by descending similarity score.
            Obsolete blocks are NEVER returned regardless of flags.
        """
        pass

    @abstractmethod
    def get_pinned(self) -> list[SpecBlock]:
        """Retrieve all pinned (deterministic) SpecBlocks.

        Pinned blocks are always included in query results regardless
        of similarity score.

        Returns:
            List of all pinned SpecBlocks
        """
        pass

    @abstractmethod
    def update_status(
        self,
        block_id: str,
        status: SpecStatus,
        reason: str = "",
    ) -> bool:
        """Update the lifecycle status of a SpecBlock.

        Validates that the transition is allowed before updating.
        If transitioning to OBSOLETE, moves block to audit log.

        Args:
            block_id: ID of the block to update
            status: New status value
            reason: Reason for the status change

        Returns:
            True if update succeeded, False if block not found

        Raises:
            LifecycleError: If the transition is not allowed
        """
        pass

    @abstractmethod
    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        """Retrieve obsolete blocks from the audit log.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of AuditEntry records, most recent first
        """
        pass

    @abstractmethod
    def get_by_id(self, block_id: str) -> SpecBlock | None:
        """Retrieve a SpecBlock by its ID.

        Args:
            block_id: ID of the block to retrieve

        Returns:
            SpecBlock if found, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, block_id: str) -> bool:
        """Delete a SpecBlock by its ID.

        Args:
            block_id: ID of the block to delete

        Returns:
            True if deletion succeeded, False if block not found
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Get the total number of stored SpecBlocks.

        Returns:
            Total count of blocks in the store
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Remove all SpecBlocks from the store.

        Use with caution - this is destructive.
        """
        pass
