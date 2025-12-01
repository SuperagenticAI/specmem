"""AgentVectorDB vector store implementation for SpecMem.

AgentVectorDB is an agent-optimized memory system from Superagentic AI.
Provides advanced features like importance scoring and memory decay.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from specmem.core.exceptions import LifecycleError, VectorStoreError
from specmem.core.specir import SpecBlock, SpecStatus, SpecType
from specmem.vectordb.base import (
    VALID_TRANSITIONS,
    AuditEntry,
    GovernanceRules,
    QueryResult,
    VectorStore,
    validate_transition,
)


logger = logging.getLogger(__name__)


class AgentVectorDBStore(VectorStore):
    """AgentVectorDB implementation with advanced memory features.

    Requires agentvectordb>=0.0.3.
    Install with: pip install specmem[agentvectordb]

    Features:
        - Namespace isolation for project separation
        - Importance scoring for memory prioritization
        - Memory decay for time-based relevance
        - Smart pruning for memory management
    """

    COLLECTION_NAME = "specmem_memories"
    AUDIT_COLLECTION_NAME = "specmem_audit"

    def __init__(
        self,
        db_path: str = ".specmem/agentvectordb",
        namespace: str = "default",
        enable_importance_scoring: bool = True,
        enable_memory_decay: bool = True,
        decay_rate: float = 0.1,
    ) -> None:
        self._db_path = db_path
        self._namespace = namespace
        self._importance_scoring = enable_importance_scoring
        self._memory_decay = enable_memory_decay
        self._decay_rate = decay_rate
        self._store = None
        self._collection = None
        self._audit_collection = None
        self._embedding_function = None
        self._initialized = False
        self._vector_dim = 384

    def initialize(self) -> None:
        if self._initialized:
            return

        try:
            from agentvectordb import AgentVectorDBStore as AVDBStore
            from agentvectordb.embeddings import DefaultTextEmbeddingFunction

            Path(self._db_path).mkdir(parents=True, exist_ok=True)

            self._store = AVDBStore(db_path=self._db_path)
            self._embedding_function = DefaultTextEmbeddingFunction(dimension=self._vector_dim)

            # Create main collection with namespace prefix
            collection_name = f"{self._namespace}_{self.COLLECTION_NAME}"
            self._collection = self._store.get_or_create_collection(
                name=collection_name,
                embedding_function=self._embedding_function,
                vector_dimension=self._vector_dim,
                update_last_accessed_on_query=True,
            )

            # Create audit collection
            audit_name = f"{self._namespace}_{self.AUDIT_COLLECTION_NAME}"
            self._audit_collection = self._store.get_or_create_collection(
                name=audit_name,
                embedding_function=self._embedding_function,
                vector_dimension=self._vector_dim,
            )

            self._initialized = True
            logger.info(
                f"AgentVectorDB initialized at {self._db_path} (namespace: {self._namespace})"
            )

        except ImportError as e:
            raise VectorStoreError(
                "AgentVectorDB not installed. Install with: pip install specmem[agentvectordb]",
                code="MISSING_DEPENDENCY",
                details={"package": "agentvectordb"},
            ) from e
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize AgentVectorDB: {e}",
                code="AGENTVECTORDB_INIT_ERROR",
                details={"path": self._db_path, "error": str(e)},
            ) from e

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def _calculate_importance(self, block: SpecBlock) -> float:
        """Calculate importance score for a block."""
        if not self._importance_scoring:
            return 0.5

        score = 0.5  # Base score

        # Pinned blocks are most important
        if block.pinned:
            score = 1.0
        # Requirements and designs are more important
        elif block.type in (SpecType.REQUIREMENT, SpecType.DESIGN):
            score = 0.8
        elif block.type == SpecType.DECISION:
            score = 0.7
        elif block.type == SpecType.TASK:
            score = 0.6

        # Deprecated blocks are less important
        if block.status == SpecStatus.DEPRECATED:
            score *= 0.5

        return min(1.0, max(0.0, score))

    def store(self, blocks: list[SpecBlock], embeddings: list[list[float]]) -> None:
        self._ensure_initialized()

        if len(blocks) != len(embeddings):
            raise VectorStoreError("Mismatched lengths", code="MISMATCHED_LENGTHS")

        if not blocks:
            return

        try:
            self._vector_dim = len(embeddings[0])

            entries = []
            for block, embedding in zip(blocks, embeddings, strict=False):
                importance = self._calculate_importance(block)

                entries.append(
                    {
                        "id": block.id,
                        "content": block.text,
                        "vector": embedding,
                        "type": block.type.value,
                        "importance_score": importance,
                        "source": block.source,
                        "tags": block.tags,
                        "extra": {
                            "status": block.status.value,
                            "links": ",".join(block.links),
                            "pinned": block.pinned,
                        },
                    }
                )

            self._collection.add_batch(entries)
            logger.info(f"Stored {len(blocks)} blocks in AgentVectorDB")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to store blocks: {e}",
                code="AGENTVECTORDB_STORE_ERROR",
                details={"num_blocks": len(blocks), "error": str(e)},
            ) from e

    def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        include_deprecated: bool = False,
        include_legacy: bool = False,
        governance_rules: GovernanceRules | None = None,
    ) -> list[QueryResult]:
        self._ensure_initialized()

        try:
            # Build filter SQL for AgentVectorDB

            # Never include obsolete (stored in extra.status)
            # Note: AgentVectorDB uses SQL-like filtering

            results = self._collection.query(
                query_vector=embedding,
                k=top_k * 2,  # Get more to filter
            )

            query_results = []
            for row in results:
                # Extract status from metadata
                extra = row.get("metadata", {}).get("extra", "{}")
                if isinstance(extra, str):
                    import json

                    try:
                        extra = json.loads(extra)
                    except Exception:
                        extra = {}

                status_str = extra.get("status", "active")
                status = SpecStatus(status_str)

                # Apply lifecycle filters
                if status == SpecStatus.OBSOLETE:
                    continue
                if status == SpecStatus.DEPRECATED and not include_deprecated:
                    continue
                if status == SpecStatus.LEGACY and not include_legacy:
                    continue

                # Apply governance rules
                if governance_rules:
                    block_type = SpecType(row.get("type", "requirement"))
                    if (
                        governance_rules.exclude_types
                        and block_type in governance_rules.exclude_types
                    ):
                        continue

                    source = row.get("metadata", {}).get("source", "")
                    if (
                        governance_rules.exclude_sources
                        and source in governance_rules.exclude_sources
                    ):
                        continue

                    importance = row.get("importance_score", 0.5)
                    if (
                        governance_rules.min_importance
                        and importance < governance_rules.min_importance
                    ):
                        continue

                block = self._row_to_specblock(row)
                distance = row.get("_distance", 0.0)
                score = 1.0 / (1.0 + distance)

                deprecation_warning = None
                if status == SpecStatus.DEPRECATED:
                    deprecation_warning = f"Block {block.id} is deprecated"

                query_results.append(
                    QueryResult(
                        block=block,
                        score=score,
                        distance=distance,
                        deprecation_warning=deprecation_warning,
                        importance_score=row.get("importance_score"),
                    )
                )

                if len(query_results) >= top_k:
                    break

            return query_results

        except Exception as e:
            raise VectorStoreError(
                f"Failed to query: {e}",
                code="AGENTVECTORDB_QUERY_ERROR",
                details={"error": str(e)},
            ) from e

    def get_pinned(self) -> list[SpecBlock]:
        self._ensure_initialized()

        try:
            # Query with high importance (pinned blocks have importance=1.0)
            results = self._collection.query(
                query_text="",
                filter_sql="importance_score >= 0.9",
                k=1000,
            )

            blocks = []
            for row in results:
                block = self._row_to_specblock(row)
                if block.pinned and block.status != SpecStatus.OBSOLETE:
                    blocks.append(block)

            return blocks

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get pinned: {e}", code="AGENTVECTORDB_PINNED_ERROR"
            ) from e

    def update_status(self, block_id: str, status: SpecStatus, reason: str = "") -> bool:
        self._ensure_initialized()

        try:
            result = self._collection.get_by_id(block_id)
            if not result:
                return False

            extra = result.get("metadata", {}).get("extra", "{}")
            if isinstance(extra, str):
                import json

                try:
                    extra = json.loads(extra)
                except Exception:
                    extra = {}

            current_status = SpecStatus(extra.get("status", "active"))

            if not validate_transition(current_status, status):
                valid = [s.value for s in VALID_TRANSITIONS.get(current_status, set())]
                raise LifecycleError(
                    "Invalid transition",
                    from_status=current_status.value,
                    to_status=status.value,
                    block_id=block_id,
                    valid_transitions=valid,
                )

            if status == SpecStatus.OBSOLETE:
                self._move_to_audit(block_id, result, current_status, reason)
                self._collection.delete(entry_id=block_id)
            else:
                # Update status in extra metadata
                extra["status"] = status.value
                # AgentVectorDB doesn't have direct update, so delete and re-add
                self._collection.delete(entry_id=block_id)
                result["metadata"]["extra"] = extra
                self._collection.add(**result)

            return True

        except LifecycleError:
            raise
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
            return False

    def _move_to_audit(
        self, block_id: str, row: dict, previous_status: SpecStatus, reason: str
    ) -> None:
        try:
            self._audit_collection.add(
                id=f"audit_{block_id}_{datetime.now().timestamp()}",
                content=row.get("content", ""),
                type="audit",
                importance_score=0.0,
                source=row.get("metadata", {}).get("source", ""),
                tags=["audit", "obsolete"],
                extra={
                    "block_id": block_id,
                    "previous_status": previous_status.value,
                    "obsoleted_at": datetime.now().timestamp(),
                    "reason": reason,
                    "original_type": row.get("type", ""),
                },
            )
        except Exception as e:
            logger.error(f"Failed to move to audit: {e}")

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        self._ensure_initialized()

        try:
            results = self._audit_collection.query(query_text="", k=limit)

            entries = []
            for row in results:
                extra = row.get("metadata", {}).get("extra", {})
                if isinstance(extra, str):
                    import json

                    try:
                        extra = json.loads(extra)
                    except Exception:
                        extra = {}

                block = SpecBlock(
                    id=extra.get("block_id", row.get("id", "")),
                    type=SpecType(extra.get("original_type", "requirement")),
                    text=row.get("content", ""),
                    source=row.get("metadata", {}).get("source", ""),
                    status=SpecStatus.OBSOLETE,
                    tags=row.get("metadata", {}).get("tags", []),
                    links=[],
                    pinned=False,
                )

                entries.append(
                    AuditEntry(
                        block=block,
                        obsoleted_at=datetime.fromtimestamp(extra.get("obsoleted_at", 0)),
                        reason=extra.get("reason", ""),
                        previous_status=SpecStatus(extra.get("previous_status", "legacy")),
                    )
                )

            return entries

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get audit log: {e}", code="AGENTVECTORDB_AUDIT_ERROR"
            ) from e

    def prune_memories(
        self,
        max_age_seconds: int | None = None,
        min_importance: float | None = None,
    ) -> int:
        """Prune old or unimportant memories.

        Args:
            max_age_seconds: Remove memories older than this
            min_importance: Remove memories with importance below this

        Returns:
            Number of memories pruned
        """
        self._ensure_initialized()

        try:
            return self._collection.prune_memories(
                max_age_seconds=max_age_seconds,
                min_importance_score=min_importance,
            )
        except Exception as e:
            logger.warning(f"Failed to prune memories: {e}")
            return 0

    def get_by_id(self, block_id: str) -> SpecBlock | None:
        self._ensure_initialized()

        try:
            result = self._collection.get_by_id(block_id)
            if not result:
                return None
            return self._row_to_specblock(result)
        except Exception:
            return None

    def delete(self, block_id: str) -> bool:
        self._ensure_initialized()

        try:
            self._collection.delete(entry_id=block_id)
            return True
        except Exception:
            return False

    def count(self) -> int:
        self._ensure_initialized()
        return self._collection.count()

    def clear(self) -> None:
        self._ensure_initialized()
        # AgentVectorDB doesn't have a clear method, recreate collection
        try:
            collection_name = f"{self._namespace}_{self.COLLECTION_NAME}"
            self._collection = self._store.get_or_create_collection(
                name=collection_name,
                embedding_function=self._embedding_function,
                vector_dimension=self._vector_dim,
                recreate=True,
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to clear: {e}", code="AGENTVECTORDB_CLEAR_ERROR") from e

    def _row_to_specblock(self, row: dict) -> SpecBlock:
        metadata = row.get("metadata", {})
        extra = metadata.get("extra", {})

        if isinstance(extra, str):
            import json

            try:
                extra = json.loads(extra)
            except Exception:
                extra = {}

        return SpecBlock(
            id=row.get("id", ""),
            type=SpecType(row.get("type", "requirement")),
            text=row.get("content", ""),
            source=metadata.get("source", ""),
            status=SpecStatus(extra.get("status", "active")),
            tags=metadata.get("tags", []),
            links=extra.get("links", "").split(",") if extra.get("links") else [],
            pinned=extra.get("pinned", False),
        )
