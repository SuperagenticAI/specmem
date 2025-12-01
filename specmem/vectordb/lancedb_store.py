"""LanceDB vector store implementation for SpecMem.

LanceDB is the default vector store due to its:
- DiskANN-based search: Fast approximate nearest neighbor search
- Serverless architecture: No separate server process required
- Native Python integration: Direct integration without network overhead
- Columnar storage: Efficient storage and retrieval
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import lancedb
import pyarrow as pa

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


class LanceDBStore(VectorStore):
    """LanceDB implementation using DiskANN for fast vector search.

    Uses the latest LanceDB API (>=0.22.3) with proper table management.
    Supports full memory lifecycle with audit logging.
    """

    TABLE_NAME = "specblocks"
    AUDIT_TABLE_NAME = "audit_log"

    def __init__(self, db_path: str = ".specmem/vectordb") -> None:
        """Initialize LanceDB store.

        Args:
            db_path: Path to store the LanceDB database
        """
        self.db_path = db_path
        self.db: lancedb.DBConnection | None = None
        self.table: lancedb.table.Table | None = None
        self.audit_table: lancedb.table.Table | None = None
        self._initialized = False
        self._vector_dim: int | None = None

    def initialize(self) -> None:
        """Initialize LanceDB and open existing tables if present."""
        if self._initialized:
            return

        try:
            Path(self.db_path).mkdir(parents=True, exist_ok=True)
            self.db = lancedb.connect(self.db_path)

            if self.TABLE_NAME in self.db.table_names():
                self.table = self.db.open_table(self.TABLE_NAME)
                logger.info(f"Opened existing LanceDB table: {self.TABLE_NAME}")

            if self.AUDIT_TABLE_NAME in self.db.table_names():
                self.audit_table = self.db.open_table(self.AUDIT_TABLE_NAME)
                logger.info(f"Opened existing audit table: {self.AUDIT_TABLE_NAME}")

            self._initialized = True
            logger.info(f"LanceDB initialized at {self.db_path}")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize LanceDB: {e}",
                code="LANCEDB_INIT_ERROR",
                details={"path": self.db_path, "error": str(e)},
            ) from e

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    def _get_schema(self, vector_dim: int) -> pa.Schema:
        return pa.schema(
            [
                ("id", pa.string()),
                ("type", pa.string()),
                ("text", pa.string()),
                ("source", pa.string()),
                ("status", pa.string()),
                ("tags", pa.string()),
                ("links", pa.string()),
                ("pinned", pa.bool_()),
                ("vector", pa.list_(pa.float32(), vector_dim)),
                ("created_at", pa.float64()),
                ("updated_at", pa.float64()),
            ]
        )

    def _get_audit_schema(self, vector_dim: int) -> pa.Schema:
        return pa.schema(
            [
                ("id", pa.string()),
                ("block_id", pa.string()),
                ("type", pa.string()),
                ("text", pa.string()),
                ("source", pa.string()),
                ("previous_status", pa.string()),
                ("tags", pa.string()),
                ("links", pa.string()),
                ("pinned", pa.bool_()),
                ("vector", pa.list_(pa.float32(), vector_dim)),
                ("obsoleted_at", pa.float64()),
                ("reason", pa.string()),
                ("transition_history", pa.string()),
            ]
        )

    def store(self, blocks: list[SpecBlock], embeddings: list[list[float]]) -> None:
        self._ensure_initialized()

        if len(blocks) != len(embeddings):
            raise VectorStoreError(
                "Number of blocks and embeddings must match",
                code="MISMATCHED_LENGTHS",
                details={"blocks": len(blocks), "embeddings": len(embeddings)},
            )

        if not blocks:
            return

        try:
            vector_dim = len(embeddings[0])
            self._vector_dim = vector_dim
            now = datetime.now().timestamp()

            data = [
                {
                    "id": block.id,
                    "type": block.type.value,
                    "text": block.text,
                    "source": block.source,
                    "status": block.status.value,
                    "tags": ",".join(block.tags),
                    "links": ",".join(block.links),
                    "pinned": block.pinned,
                    "vector": embedding,
                    "created_at": now,
                    "updated_at": now,
                }
                for block, embedding in zip(blocks, embeddings, strict=False)
            ]

            schema = self._get_schema(vector_dim)
            self.table = self.db.create_table(
                name=self.TABLE_NAME,
                data=data,
                schema=schema,
                mode="overwrite",
            )

            logger.info(f"Stored {len(blocks)} blocks in LanceDB")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to store blocks: {e}",
                code="LANCEDB_STORE_ERROR",
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
        """Query with lifecycle filtering and governance rules."""
        self._ensure_initialized()

        if self.table is None:
            return []

        try:
            query_builder = self.table.search(embedding).limit(top_k * 2)

            # Build status filter - NEVER include obsolete
            status_conditions = ["status != 'obsolete'"]
            if not include_deprecated:
                status_conditions.append("status != 'deprecated'")
            if not include_legacy:
                status_conditions.append("status != 'legacy'")

            filter_expr = " AND ".join(status_conditions)

            # Apply governance rules
            if governance_rules:
                if governance_rules.max_age_days is not None:
                    cutoff = (
                        datetime.now() - timedelta(days=governance_rules.max_age_days)
                    ).timestamp()
                    filter_expr += f" AND created_at >= {cutoff}"

                if governance_rules.exclude_types:
                    type_list = ", ".join(f"'{t.value}'" for t in governance_rules.exclude_types)
                    filter_expr += f" AND type NOT IN ({type_list})"

                if governance_rules.exclude_sources:
                    for source in governance_rules.exclude_sources:
                        filter_expr += f" AND source != '{source}'"

            query_builder = query_builder.where(filter_expr)
            results = query_builder.to_list()

            query_results = []
            for row in results[:top_k]:
                block = self._row_to_specblock(row)
                distance = row.get("_distance", 0.0)
                score = 1.0 / (1.0 + distance)

                deprecation_warning = None
                if block.status == SpecStatus.DEPRECATED:
                    deprecation_warning = f"Block {block.id} is deprecated and may be removed"

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
                code="LANCEDB_QUERY_ERROR",
                details={"top_k": top_k, "error": str(e)},
            ) from e

    def get_pinned(self) -> list[SpecBlock]:
        self._ensure_initialized()

        if self.table is None:
            return []

        try:
            results = (
                self.table.search()
                .where("pinned = true AND status != 'obsolete'")
                .limit(1000)
                .to_list()
            )
            return [self._row_to_specblock(row) for row in results]

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get pinned blocks: {e}",
                code="LANCEDB_PINNED_ERROR",
                details={"error": str(e)},
            ) from e

    def update_status(
        self,
        block_id: str,
        status: SpecStatus,
        reason: str = "",
    ) -> bool:
        """Update status with transition validation and audit logging."""
        self._ensure_initialized()

        if self.table is None:
            return False

        try:
            # Get current block
            results = self.table.search().where(f"id = '{block_id}'").limit(1).to_list()
            if not results:
                return False

            row = results[0]
            current_status = SpecStatus(row["status"])

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

            # If transitioning to obsolete, move to audit log
            if status == SpecStatus.OBSOLETE:
                self._move_to_audit(row, current_status, reason)
                self.table.delete(f"id = '{block_id}'")
            else:
                self.table.update(
                    where=f"id = '{block_id}'",
                    values={"status": status.value, "updated_at": datetime.now().timestamp()},
                )

            return True

        except LifecycleError:
            raise
        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
            return False

    def _move_to_audit(self, row: dict, previous_status: SpecStatus, reason: str) -> None:
        """Move a block to the audit log."""
        try:
            vector_dim = len(row.get("vector", []))
            if vector_dim == 0:
                vector_dim = 384  # Default

            audit_data = [
                {
                    "id": f"audit_{row['id']}_{datetime.now().timestamp()}",
                    "block_id": row["id"],
                    "type": row["type"],
                    "text": row["text"],
                    "source": row["source"],
                    "previous_status": previous_status.value,
                    "tags": row.get("tags", ""),
                    "links": row.get("links", ""),
                    "pinned": row.get("pinned", False),
                    "vector": row.get("vector", [0.0] * vector_dim),
                    "obsoleted_at": datetime.now().timestamp(),
                    "reason": reason,
                    "transition_history": "[]",
                }
            ]

            if self.audit_table is None:
                schema = self._get_audit_schema(vector_dim)
                self.audit_table = self.db.create_table(
                    name=self.AUDIT_TABLE_NAME,
                    data=audit_data,
                    schema=schema,
                    mode="create",
                )
            else:
                self.audit_table.add(audit_data)

            logger.info(f"Moved block {row['id']} to audit log")

        except Exception as e:
            logger.error(f"Failed to move block to audit: {e}")

    def get_audit_log(self, limit: int = 100) -> list[AuditEntry]:
        """Retrieve obsolete blocks from audit log."""
        self._ensure_initialized()

        if self.audit_table is None:
            return []

        try:
            results = self.audit_table.search().limit(limit).to_list()

            entries = []
            for row in results:
                block = SpecBlock(
                    id=row["block_id"],
                    type=SpecType(row["type"]),
                    text=row["text"],
                    source=row["source"],
                    status=SpecStatus.OBSOLETE,
                    tags=row.get("tags", "").split(",") if row.get("tags") else [],
                    links=row.get("links", "").split(",") if row.get("links") else [],
                    pinned=row.get("pinned", False),
                )

                entries.append(
                    AuditEntry(
                        block=block,
                        obsoleted_at=datetime.fromtimestamp(row["obsoleted_at"]),
                        reason=row.get("reason", ""),
                        previous_status=SpecStatus(row["previous_status"]),
                        transition_history=[],
                    )
                )

            return entries

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get audit log: {e}",
                code="LANCEDB_AUDIT_ERROR",
                details={"error": str(e)},
            ) from e

    def get_by_id(self, block_id: str) -> SpecBlock | None:
        self._ensure_initialized()

        if self.table is None:
            return None

        try:
            results = self.table.search().where(f"id = '{block_id}'").limit(1).to_list()
            if not results:
                return None
            return self._row_to_specblock(results[0])

        except Exception as e:
            raise VectorStoreError(
                f"Failed to get block: {e}",
                code="LANCEDB_GET_ERROR",
                details={"block_id": block_id, "error": str(e)},
            ) from e

    def delete(self, block_id: str) -> bool:
        self._ensure_initialized()

        if self.table is None:
            return False

        try:
            results = self.table.search().where(f"id = '{block_id}'").limit(1).to_list()
            if not results:
                return False

            self.table.delete(f"id = '{block_id}'")
            return True

        except Exception as e:
            raise VectorStoreError(
                f"Failed to delete block: {e}",
                code="LANCEDB_DELETE_ERROR",
                details={"block_id": block_id, "error": str(e)},
            ) from e

    def count(self) -> int:
        self._ensure_initialized()

        if self.table is None:
            return 0

        try:
            return self.table.count_rows()
        except Exception:
            return 0

    def clear(self) -> None:
        self._ensure_initialized()

        if self.table is not None:
            try:
                self.db.drop_table(self.TABLE_NAME)
                self.table = None
                logger.info("Cleared LanceDB table")
            except Exception as e:
                raise VectorStoreError(
                    f"Failed to clear store: {e}",
                    code="LANCEDB_CLEAR_ERROR",
                    details={"error": str(e)},
                ) from e

        if self.audit_table is not None:
            try:
                self.db.drop_table(self.AUDIT_TABLE_NAME)
                self.audit_table = None
            except Exception:
                pass

    def _row_to_specblock(self, row: dict[str, Any]) -> SpecBlock:
        tags = row.get("tags", "")
        links = row.get("links", "")

        return SpecBlock(
            id=row["id"],
            type=SpecType(row["type"]),
            text=row["text"],
            source=row["source"],
            status=SpecStatus(row["status"]),
            tags=tags.split(",") if tags else [],
            links=links.split(",") if links else [],
            pinned=row.get("pinned", False),
        )
