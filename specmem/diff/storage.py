"""Storage layer for SpecDiff version history.

Uses SQLite for persistent storage of spec versions, staleness acknowledgments,
and deprecations.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from specmem.diff.models import Deprecation, SpecVersion


logger = logging.getLogger(__name__)


class VersionStore:
    """SQLite-based storage for spec version history."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS spec_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spec_id TEXT NOT NULL,
        version_id TEXT NOT NULL,
        timestamp DATETIME NOT NULL,
        commit_ref TEXT,
        content_hash TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT,
        UNIQUE(spec_id, version_id)
    );

    CREATE TABLE IF NOT EXISTS staleness_acks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spec_id TEXT NOT NULL,
        version_id TEXT NOT NULL,
        acknowledged_at DATETIME NOT NULL,
        UNIQUE(spec_id, version_id)
    );

    CREATE TABLE IF NOT EXISTS deprecations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spec_id TEXT NOT NULL UNIQUE,
        deprecated_at DATETIME NOT NULL,
        deadline DATETIME,
        replacement_spec_id TEXT,
        affected_code TEXT,
        urgency REAL DEFAULT 0.5,
        metadata TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_versions_spec ON spec_versions(spec_id);
    CREATE INDEX IF NOT EXISTS idx_versions_timestamp ON spec_versions(timestamp);
    CREATE INDEX IF NOT EXISTS idx_deprecations_urgency ON deprecations(urgency DESC);
    """

    def __init__(self, db_path: Path | str) -> None:
        """Initialize the version store.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _initialize_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.executescript(self.SCHEMA)
        conn.commit()
        logger.debug(f"Initialized VersionStore at {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # =========================================================================
    # Version CRUD Operations
    # =========================================================================

    def save_version(self, version: SpecVersion) -> None:
        """Save a spec version.

        Args:
            version: The version to save.
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO spec_versions
            (spec_id, version_id, timestamp, commit_ref, content_hash, content, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                version.spec_id,
                version.version_id,
                version.timestamp.isoformat(),
                version.commit_ref,
                version.content_hash,
                version.content,
                json.dumps(version.metadata),
            ),
        )
        conn.commit()
        logger.debug(f"Saved version {version.version_id} for spec {version.spec_id}")

    def get_version(self, spec_id: str, version_id: str) -> SpecVersion | None:
        """Get a specific version.

        Args:
            spec_id: Spec identifier.
            version_id: Version identifier.

        Returns:
            SpecVersion if found, None otherwise.
        """
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT * FROM spec_versions
            WHERE spec_id = ? AND version_id = ?
            """,
            (spec_id, version_id),
        ).fetchone()

        if row:
            return self._row_to_version(row)
        return None

    def get_history(
        self,
        spec_id: str,
        limit: int | None = None,
    ) -> list[SpecVersion]:
        """Get version history for a spec, ordered by timestamp ascending.

        Args:
            spec_id: Spec identifier.
            limit: Maximum number of versions to return.

        Returns:
            List of versions ordered by timestamp (oldest first).
        """
        conn = self._get_connection()
        query = """
            SELECT * FROM spec_versions
            WHERE spec_id = ?
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"

        rows = conn.execute(query, (spec_id,)).fetchall()
        return [self._row_to_version(row) for row in rows]

    def get_latest_version(self, spec_id: str) -> SpecVersion | None:
        """Get the latest version of a spec.

        Args:
            spec_id: Spec identifier.

        Returns:
            Latest SpecVersion if found, None otherwise.
        """
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT * FROM spec_versions
            WHERE spec_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (spec_id,),
        ).fetchone()

        if row:
            return self._row_to_version(row)
        return None

    def delete_version(self, spec_id: str, version_id: str) -> bool:
        """Delete a specific version.

        Args:
            spec_id: Spec identifier.
            version_id: Version identifier.

        Returns:
            True if deleted, False if not found.
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            DELETE FROM spec_versions
            WHERE spec_id = ? AND version_id = ?
            """,
            (spec_id, version_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def prune_history(
        self,
        older_than: datetime,
        keep_min: int = 10,
    ) -> int:
        """Prune old versions, keeping at least keep_min per spec.

        Args:
            older_than: Delete versions older than this.
            keep_min: Minimum versions to keep per spec.

        Returns:
            Number of versions deleted.
        """
        conn = self._get_connection()

        # Get specs with more than keep_min versions
        specs = conn.execute(
            """
            SELECT spec_id, COUNT(*) as count
            FROM spec_versions
            GROUP BY spec_id
            HAVING count > ?
            """,
            (keep_min,),
        ).fetchall()

        total_deleted = 0
        for row in specs:
            spec_id = row["spec_id"]
            count = row["count"]

            # Calculate how many we can delete
            can_delete = count - keep_min

            # Delete oldest versions that are older than threshold
            cursor = conn.execute(
                """
                DELETE FROM spec_versions
                WHERE spec_id = ? AND timestamp < ?
                AND id IN (
                    SELECT id FROM spec_versions
                    WHERE spec_id = ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                )
                """,
                (spec_id, older_than.isoformat(), spec_id, can_delete),
            )
            total_deleted += cursor.rowcount

        conn.commit()
        logger.info(f"Pruned {total_deleted} old versions")
        return total_deleted

    def _row_to_version(self, row: sqlite3.Row) -> SpecVersion:
        """Convert database row to SpecVersion."""
        return SpecVersion(
            spec_id=row["spec_id"],
            version_id=row["version_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            commit_ref=row["commit_ref"],
            content_hash=row["content_hash"],
            content=row["content"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # =========================================================================
    # Staleness Acknowledgment Operations
    # =========================================================================

    def acknowledge_staleness(
        self,
        spec_id: str,
        version_id: str,
    ) -> None:
        """Record staleness acknowledgment.

        Args:
            spec_id: Spec identifier.
            version_id: Version that was acknowledged.
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO staleness_acks
            (spec_id, version_id, acknowledged_at)
            VALUES (?, ?, ?)
            """,
            (spec_id, version_id, datetime.now().isoformat()),
        )
        conn.commit()

    def is_acknowledged(self, spec_id: str, version_id: str) -> bool:
        """Check if staleness was acknowledged.

        Args:
            spec_id: Spec identifier.
            version_id: Version to check.

        Returns:
            True if acknowledged, False otherwise.
        """
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT 1 FROM staleness_acks
            WHERE spec_id = ? AND version_id = ?
            """,
            (spec_id, version_id),
        ).fetchone()
        return row is not None

    # =========================================================================
    # Deprecation Operations
    # =========================================================================

    def save_deprecation(self, deprecation: Deprecation) -> None:
        """Save a deprecation record.

        Args:
            deprecation: The deprecation to save.
        """
        conn = self._get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO deprecations
            (spec_id, deprecated_at, deadline, replacement_spec_id, affected_code, urgency)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                deprecation.spec_id,
                deprecation.deprecated_at.isoformat(),
                deprecation.deadline.isoformat() if deprecation.deadline else None,
                deprecation.replacement_spec_id,
                json.dumps(deprecation.affected_code),
                deprecation.urgency,
            ),
        )
        conn.commit()

    def get_deprecation(self, spec_id: str) -> Deprecation | None:
        """Get deprecation for a spec.

        Args:
            spec_id: Spec identifier.

        Returns:
            Deprecation if found, None otherwise.
        """
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT * FROM deprecations WHERE spec_id = ?
            """,
            (spec_id,),
        ).fetchone()

        if row:
            return self._row_to_deprecation(row)
        return None

    def get_deprecations(
        self,
        include_expired: bool = False,
    ) -> list[Deprecation]:
        """Get all deprecations sorted by urgency.

        Args:
            include_expired: Include deprecations past deadline.

        Returns:
            List of deprecations ordered by urgency descending.
        """
        conn = self._get_connection()

        if include_expired:
            query = """
                SELECT * FROM deprecations
                ORDER BY urgency DESC
            """
            rows = conn.execute(query).fetchall()
        else:
            query = """
                SELECT * FROM deprecations
                WHERE deadline IS NULL OR deadline > ?
                ORDER BY urgency DESC
            """
            rows = conn.execute(query, (datetime.now().isoformat(),)).fetchall()

        return [self._row_to_deprecation(row) for row in rows]

    def delete_deprecation(self, spec_id: str) -> bool:
        """Delete a deprecation record.

        Args:
            spec_id: Spec identifier.

        Returns:
            True if deleted, False if not found.
        """
        conn = self._get_connection()
        cursor = conn.execute(
            """
            DELETE FROM deprecations WHERE spec_id = ?
            """,
            (spec_id,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def _row_to_deprecation(self, row: sqlite3.Row) -> Deprecation:
        """Convert database row to Deprecation."""
        return Deprecation(
            spec_id=row["spec_id"],
            deprecated_at=datetime.fromisoformat(row["deprecated_at"]),
            deadline=datetime.fromisoformat(row["deadline"]) if row["deadline"] else None,
            replacement_spec_id=row["replacement_spec_id"],
            affected_code=json.loads(row["affected_code"]) if row["affected_code"] else [],
            urgency=row["urgency"],
        )
