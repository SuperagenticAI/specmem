"""Qdrant vector store implementation for SpecMem.

Qdrant is a high-performance vector similarity search engine.
Supports both local and cloud deployments.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

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


class QdrantStore(VectorStore):
    """Qdrant implementation for vector storage.

    Requires qdrant-client>=1.18.0.
    Install with: pip install specmem[qdrant]
    """

    COLLECTION_NAME = "specblocks"
    AUDIT_COLLECTION_NAME = "audit_log"

    @staticmethod
    def _point_id(block_id: str) -> str:
        """Map a SpecBlock id to a valid Qdrant point id.

        Qdrant requires point ids to be UUIDs or unsigned integers, but
        SpecBlock ids are short hex hashes. Map them deterministically to a
        UUID so the same block always resolves to the same point.
        """
        try:
            return str(UUID(block_id))
        except (ValueError, AttributeError, TypeError):
            return str(uuid5(NAMESPACE_URL, block_id))

    def __init__(
        self,
        path: str = ".specmem/qdrant",
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        audit_collection_name: str | None = None,
        vector_dim: int = 384,
    ) -> None:
        self._path = path
        self._url = url
        self._api_key = api_key
        self._collection_name = collection_name or self.COLLECTION_NAME
        self._audit_collection_name = audit_collection_name or self.AUDIT_COLLECTION_NAME
        self._client = None
        self._initialized = False
        self._vector_dim = vector_dim

    def initialize(self) -> None:
        if self._initialized:
            return

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            if self._url:
                self._client = QdrantClient(url=self._url, api_key=self._api_key)
            else:
                Path(self._path).mkdir(parents=True, exist_ok=True)
                self._client = QdrantClient(path=self._path)

            # Create collections if they don't exist
            collections = [c.name for c in self._client.get_collections().collections]

            if self._collection_name not in collections:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=VectorParams(size=self._vector_dim, distance=Distance.COSINE),
                )

            if self._audit_collection_name not in collections:
                self._client.create_collection(
                    collection_name=self._audit_collection_name,
                    vectors_config=VectorParams(size=self._vector_dim, distance=Distance.COSINE),
                )

            self._initialized = True
            logger.info("Qdrant initialized")

        except ImportError as e:
            raise VectorStoreError(
                "Qdrant not installed. Install with: pip install specmem[qdrant]",
                code="MISSING_DEPENDENCY",
            ) from e
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize Qdrant: {e}", code="QDRANT_INIT_ERROR"
            ) from e

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def store(self, blocks: list[SpecBlock], embeddings: list[list[float]]) -> None:
        if len(blocks) != len(embeddings):
            raise VectorStoreError("Mismatched lengths", code="MISMATCHED_LENGTHS")

        if not blocks:
            return

        self._vector_dim = len(embeddings[0])
        self._ensure_initialized()

        try:
            from qdrant_client.models import PointStruct

            now = datetime.now().timestamp()

            points = [
                PointStruct(
                    id=self._point_id(block.id),
                    vector=embedding,
                    payload={
                        "block_id": block.id,
                        "type": block.type.value,
                        "text": block.text,
                        "source": block.source,
                        "status": block.status.value,
                        "tags": ",".join(block.tags),
                        "links": ",".join(block.links),
                        "pinned": block.pinned,
                        "created_at": now,
                    },
                )
                for block, embedding in zip(blocks, embeddings, strict=False)
            ]

            self._client.upsert(collection_name=self._collection_name, points=points)
            logger.info(f"Stored {len(blocks)} blocks in Qdrant")

        except Exception as e:
            raise VectorStoreError(f"Failed to store: {e}", code="QDRANT_STORE_ERROR") from e

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
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Build filter conditions
            must_not = [FieldCondition(key="status", match=MatchValue(value="obsolete"))]

            if not include_deprecated:
                must_not.append(FieldCondition(key="status", match=MatchValue(value="deprecated")))
            if not include_legacy:
                must_not.append(FieldCondition(key="status", match=MatchValue(value="legacy")))

            if governance_rules and governance_rules.exclude_types:
                for t in governance_rules.exclude_types:
                    must_not.append(FieldCondition(key="type", match=MatchValue(value=t.value)))

            query_filter = Filter(must_not=must_not) if must_not else None

            response = self._client.query_points(
                collection_name=self._collection_name,
                query=embedding,
                limit=top_k,
                query_filter=query_filter,
            )

            return [
                QueryResult(
                    block=self._payload_to_specblock(
                        r.payload.get("block_id", str(r.id)), r.payload
                    ),
                    score=r.score,
                    distance=1.0 - r.score,
                    deprecation_warning=f"Block {r.payload.get('block_id', r.id)} is deprecated"
                    if r.payload.get("status") == "deprecated"
                    else None,
                )
                for r in response.points
            ]

        except Exception as e:
            raise VectorStoreError(f"Failed to query: {e}", code="QDRANT_QUERY_ERROR") from e

    def get_pinned(self) -> list[SpecBlock]:
        self._ensure_initialized()

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            results = self._client.scroll(
                collection_name=self._collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="pinned", match=MatchValue(value=True))],
                    must_not=[FieldCondition(key="status", match=MatchValue(value="obsolete"))],
                ),
                limit=1000,
            )[0]

            return [
                self._payload_to_specblock(r.payload.get("block_id", str(r.id)), r.payload)
                for r in results
            ]

        except Exception as e:
            raise VectorStoreError(f"Failed to get pinned: {e}", code="QDRANT_PINNED_ERROR") from e

    def update_status(self, block_id: str, status: SpecStatus | str, reason: str = "") -> bool:
        self._ensure_initialized()
        target_status = status if isinstance(status, SpecStatus) else SpecStatus(status)
        point_id = self._point_id(block_id)

        try:
            results = self._client.retrieve(collection_name=self._collection_name, ids=[point_id])
            if not results:
                return False

            payload = results[0].payload
            current_status = SpecStatus(payload["status"])
            if current_status == target_status:
                return True

            if not validate_transition(current_status, target_status):
                valid = [s.value for s in VALID_TRANSITIONS.get(current_status, set())]
                raise LifecycleError(
                    "Invalid transition",
                    from_status=current_status.value,
                    to_status=target_status.value,
                    block_id=block_id,
                    valid_transitions=valid,
                )

            if target_status == SpecStatus.OBSOLETE:
                self._move_to_audit(block_id, results[0], current_status, reason)
                self._client.delete(
                    collection_name=self._collection_name, points_selector=[point_id]
                )
            else:
                self._client.set_payload(
                    collection_name=self._collection_name,
                    payload={"status": target_status.value},
                    points=[point_id],
                )

            return True

        except LifecycleError:
            raise
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
            return False

    def _move_to_audit(
        self, block_id: str, point: Any, previous_status: SpecStatus, reason: str
    ) -> None:
        try:
            from qdrant_client.models import PointStruct

            audit_point = PointStruct(
                id=str(uuid4()),
                vector=point.vector,
                payload={
                    **point.payload,
                    "block_id": block_id,
                    "previous_status": previous_status.value,
                    "obsoleted_at": datetime.now().timestamp(),
                    "reason": reason,
                },
            )
            self._client.upsert(collection_name=self._audit_collection_name, points=[audit_point])
        except Exception as e:
            logger.error(f"Failed to move to audit: {e}")

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        self._ensure_initialized()

        try:
            results = self._client.scroll(collection_name=self._audit_collection_name, limit=limit)[
                0
            ]

            return [
                AuditEntry(
                    block=self._payload_to_specblock(
                        r.payload.get("block_id", str(r.id)), r.payload
                    ),
                    obsoleted_at=datetime.fromtimestamp(r.payload.get("obsoleted_at", 0)),
                    reason=r.payload.get("reason", ""),
                    previous_status=SpecStatus(r.payload.get("previous_status", "legacy")),
                )
                for r in results
            ]

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get audit log: {e}", code="QDRANT_AUDIT_ERROR"
            ) from e

    def get_by_id(self, block_id: str) -> SpecBlock | None:
        self._ensure_initialized()

        try:
            results = self._client.retrieve(
                collection_name=self._collection_name, ids=[self._point_id(block_id)]
            )
            if not results:
                return None
            return self._payload_to_specblock(block_id, results[0].payload)
        except Exception:
            return None

    def delete(self, block_id: str) -> bool:
        self._ensure_initialized()

        try:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=[self._point_id(block_id)],
            )
            return True
        except Exception:
            return False

    def count(self) -> int:
        self._ensure_initialized()
        try:
            return self._client.count(collection_name=self._collection_name).count
        except Exception:
            return 0

    def clear(self) -> None:
        self._ensure_initialized()
        try:
            self._client.delete_collection(self._collection_name)
            from qdrant_client.models import Distance, VectorParams

            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(size=self._vector_dim, distance=Distance.COSINE),
            )
        except Exception as e:
            raise VectorStoreError(f"Failed to clear: {e}", code="QDRANT_CLEAR_ERROR") from e

    def _payload_to_specblock(self, block_id: str, payload: dict) -> SpecBlock:
        return SpecBlock(
            id=block_id,
            type=SpecType(payload["type"]),
            text=payload["text"],
            source=payload["source"],
            status=SpecStatus(payload["status"]),
            tags=payload.get("tags", "").split(",") if payload.get("tags") else [],
            links=payload.get("links", "").split(",") if payload.get("links") else [],
            pinned=payload.get("pinned", False),
        )
