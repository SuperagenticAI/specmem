"""ChromaDB vector store implementation for SpecMem.

ChromaDB is a popular open-source embedding database that provides:
- Simple API for vector storage and retrieval
- Built-in embedding functions
- Persistent storage
- Metadata filtering
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

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


if TYPE_CHECKING:
    import chromadb

logger = logging.getLogger(__name__)


class ChromaDBStore(VectorStore):
    """ChromaDB implementation for vector storage.

    Requires chromadb>=1.3.5 to be installed.
    Install with: pip install specmem[chroma]
    """

    COLLECTION_NAME = "specblocks"
    AUDIT_COLLECTION_NAME = "audit_log"

    def __init__(
        self,
        path: str = ".specmem/chroma",
        collection_name: str = COLLECTION_NAME,
    ) -> None:
        """Initialize ChromaDB store.

        Args:
            path: Path to store the ChromaDB database
            collection_name: Name of the collection to use
        """
        self._path = path
        self._collection_name = collection_name
        self._client: chromadb.PersistentClient | None = None
        self._collection = None
        self._audit_collection = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        if self._initialized:
            return

        try:
            import chromadb

            Path(self._path).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self._path)

            # Get or create main collection
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            # Get or create audit collection
            self._audit_collection = self._client.get_or_create_collection(
                name=self.AUDIT_COLLECTION_NAME,
            )

            self._initialized = True
            logger.info(f"ChromaDB initialized at {self._path}")

        except ImportError as e:
            raise VectorStoreError(
                "ChromaDB not installed. Install with: pip install specmem[chroma]",
                code="MISSING_DEPENDENCY",
                details={"package": "chromadb"},
            ) from e
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize ChromaDB: {e}",
                code="CHROMA_INIT_ERROR",
                details={"path": self._path, "error": str(e)},
            ) from e

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def store(self, blocks: list[SpecBlock], embeddings: list[list[float]]) -> None:
        """Store blocks with embeddings in ChromaDB."""
        self._ensure_initialized()

        if len(blocks) != len(embeddings):
            raise VectorStoreError(
                "Number of blocks and embeddings must match",
                code="MISMATCHED_LENGTHS",
            )

        if not blocks:
            return

        try:
            now = datetime.now().timestamp()

            ids = [block.id for block in blocks]
            documents = [block.text for block in blocks]
            metadatas = [
                {
                    "type": block.type.value,
                    "source": block.source,
                    "status": block.status.value,
                    "tags": ",".join(block.tags),
                    "links": ",".join(block.links),
                    "pinned": block.pinned,
                    "created_at": now,
                    "updated_at": now,
                }
                for block in blocks
            ]

            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            logger.info(f"Stored {len(blocks)} blocks in ChromaDB")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to store blocks: {e}",
                code="CHROMA_STORE_ERROR",
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
        """Query ChromaDB with lifecycle filtering."""
        self._ensure_initialized()

        try:
            # Build where filter - ChromaDB uses $and, $or, $ne operators
            where_conditions = []

            # Never include obsolete
            where_conditions.append({"status": {"$ne": "obsolete"}})

            if not include_deprecated:
                where_conditions.append({"status": {"$ne": "deprecated"}})

            if not include_legacy:
                where_conditions.append({"status": {"$ne": "legacy"}})

            # Apply governance rules
            if governance_rules:
                if governance_rules.exclude_types:
                    for t in governance_rules.exclude_types:
                        where_conditions.append({"type": {"$ne": t.value}})

                if governance_rules.exclude_sources:
                    for s in governance_rules.exclude_sources:
                        where_conditions.append({"source": {"$ne": s}})

            where_filter = (
                {"$and": where_conditions} if len(where_conditions) > 1 else where_conditions[0]
            )

            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            query_results = []
            if results["ids"] and results["ids"][0]:
                for i, block_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    distance = results["distances"][0][i] if results["distances"] else 0.0

                    block = self._metadata_to_specblock(block_id, document, metadata)
                    score = 1.0 / (1.0 + distance)

                    deprecation_warning = None
                    if block.status == SpecStatus.DEPRECATED:
                        deprecation_warning = f"Block {block.id} is deprecated"

                    query_results.append(
                        QueryResult(
                            block=block,
                            score=score,
                            distance=distance,
                            deprecation_warning=deprecation_warning,
                        )
                    )

            return query_results

        except Exception as e:
            raise VectorStoreError(
                f"Failed to query: {e}",
                code="CHROMA_QUERY_ERROR",
                details={"error": str(e)},
            ) from e

    def get_pinned(self) -> list[SpecBlock]:
        """Get all pinned blocks."""
        self._ensure_initialized()

        try:
            results = self._collection.get(
                where={"$and": [{"pinned": True}, {"status": {"$ne": "obsolete"}}]},
                include=["documents", "metadatas"],
            )

            blocks = []
            if results["ids"]:
                for i, block_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i]
                    document = results["documents"][i]
                    blocks.append(self._metadata_to_specblock(block_id, document, metadata))

            return blocks

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get pinned blocks: {e}",
                code="CHROMA_PINNED_ERROR",
            ) from e

    def update_status(
        self,
        block_id: str,
        status: SpecStatus,
        reason: str = "",
    ) -> bool:
        """Update block status with validation."""
        self._ensure_initialized()

        try:
            # Get current block
            results = self._collection.get(ids=[block_id], include=["documents", "metadatas"])

            if not results["ids"]:
                return False

            metadata = results["metadatas"][0]
            current_status = SpecStatus(metadata["status"])

            # Validate transition
            if not validate_transition(current_status, status):
                valid = [s.value for s in VALID_TRANSITIONS.get(current_status, set())]
                raise LifecycleError(
                    f"Cannot transition from {current_status.value} to {status.value}",
                    from_status=current_status.value,
                    to_status=status.value,
                    block_id=block_id,
                    valid_transitions=valid,
                )

            # Move to audit if obsolete
            if status == SpecStatus.OBSOLETE:
                self._move_to_audit(block_id, results, current_status, reason)
                self._collection.delete(ids=[block_id])
            else:
                metadata["status"] = status.value
                metadata["updated_at"] = datetime.now().timestamp()
                self._collection.update(ids=[block_id], metadatas=[metadata])

            return True

        except LifecycleError:
            raise
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
            return False

    def _move_to_audit(
        self, block_id: str, results: dict, previous_status: SpecStatus, reason: str
    ) -> None:
        """Move block to audit collection."""
        try:
            metadata = results["metadatas"][0]
            document = results["documents"][0]

            audit_id = f"audit_{block_id}_{datetime.now().timestamp()}"
            audit_metadata = {
                "block_id": block_id,
                "type": metadata["type"],
                "source": metadata["source"],
                "previous_status": previous_status.value,
                "tags": metadata.get("tags", ""),
                "links": metadata.get("links", ""),
                "pinned": metadata.get("pinned", False),
                "obsoleted_at": datetime.now().timestamp(),
                "reason": reason,
            }

            self._audit_collection.add(
                ids=[audit_id],
                documents=[document],
                metadatas=[audit_metadata],
            )

        except Exception as e:
            logger.error(f"Failed to move to audit: {e}")

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        """Get audit log entries."""
        self._ensure_initialized()

        try:
            results = self._audit_collection.get(
                limit=limit,
                include=["documents", "metadatas"],
            )

            entries = []
            if results["ids"]:
                for i, _ in enumerate(results["ids"]):
                    metadata = results["metadatas"][i]
                    document = results["documents"][i]

                    block = SpecBlock(
                        id=metadata["block_id"],
                        type=SpecType(metadata["type"]),
                        text=document,
                        source=metadata["source"],
                        status=SpecStatus.OBSOLETE,
                        tags=metadata.get("tags", "").split(",") if metadata.get("tags") else [],
                        links=metadata.get("links", "").split(",") if metadata.get("links") else [],
                        pinned=metadata.get("pinned", False),
                    )

                    entries.append(
                        AuditEntry(
                            block=block,
                            obsoleted_at=datetime.fromtimestamp(metadata["obsoleted_at"]),
                            reason=metadata.get("reason", ""),
                            previous_status=SpecStatus(metadata["previous_status"]),
                        )
                    )

            return entries

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get audit log: {e}",
                code="CHROMA_AUDIT_ERROR",
            ) from e

    def get_by_id(self, block_id: str) -> SpecBlock | None:
        """Get block by ID."""
        self._ensure_initialized()

        try:
            results = self._collection.get(ids=[block_id], include=["documents", "metadatas"])

            if not results["ids"]:
                return None

            return self._metadata_to_specblock(
                block_id, results["documents"][0], results["metadatas"][0]
            )

        except Exception as e:
            raise VectorStoreError(f"Failed to get block: {e}", code="CHROMA_GET_ERROR") from e

    def delete(self, block_id: str) -> bool:
        """Delete block by ID."""
        self._ensure_initialized()

        try:
            results = self._collection.get(ids=[block_id])
            if not results["ids"]:
                return False

            self._collection.delete(ids=[block_id])
            return True

        except Exception as e:
            raise VectorStoreError(f"Failed to delete: {e}", code="CHROMA_DELETE_ERROR") from e

    def count(self) -> int:
        """Get total block count."""
        self._ensure_initialized()
        return self._collection.count()

    def clear(self) -> None:
        """Clear all blocks."""
        self._ensure_initialized()

        try:
            self._client.delete_collection(self._collection_name)
            self._collection = self._client.create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to clear: {e}", code="CHROMA_CLEAR_ERROR") from e

    def _metadata_to_specblock(self, block_id: str, document: str, metadata: dict) -> SpecBlock:
        """Convert ChromaDB metadata to SpecBlock."""
        return SpecBlock(
            id=block_id,
            type=SpecType(metadata["type"]),
            text=document,
            source=metadata["source"],
            status=SpecStatus(metadata["status"]),
            tags=metadata.get("tags", "").split(",") if metadata.get("tags") else [],
            links=metadata.get("links", "").split(",") if metadata.get("links") else [],
            pinned=metadata.get("pinned", False),
        )
