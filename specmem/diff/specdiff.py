"""SpecDiff - Main class for temporal spec intelligence.

Provides the core API for tracking spec evolution, detecting staleness,
analyzing drift, and managing deprecations.
"""

from __future__ import annotations

import difflib
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from specmem.diff.models import (
    ChangeReason,
    ChangeType,
    Contradiction,
    Deprecation,
    DriftItem,
    DriftReport,
    ModifiedSection,
    Severity,
    SpecChange,
    SpecVersion,
    StalenessWarning,
)
from specmem.diff.storage import VersionStore


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.impact import SpecImpactGraph

logger = logging.getLogger(__name__)


class SpecDiff:
    """Temporal spec intelligence system.

    Tracks specification evolution over time, enabling agents to understand
    what changed, why it changed, and what code is now invalid due to spec drift.
    """

    def __init__(
        self,
        storage_path: Path | str,
        impact_graph: SpecImpactGraph | None = None,
    ) -> None:
        """Initialize SpecDiff.

        Args:
            storage_path: Path to store version history database.
            impact_graph: Optional SpecImpactGraph for drift detection.
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._store = VersionStore(self.storage_path)
        self._impact_graph = impact_graph

        logger.debug(f"SpecDiff initialized at {self.storage_path}")

    def get_history(
        self,
        spec_id: str,
        limit: int | None = None,
    ) -> list[SpecVersion]:
        """Get version history for a spec, chronologically ordered.

        Args:
            spec_id: Spec identifier.
            limit: Maximum number of versions to return.

        Returns:
            List of versions ordered by timestamp (oldest first).
        """
        return self._store.get_history(spec_id, limit)

    def get_latest_version(self, spec_id: str) -> SpecVersion | None:
        """Get the latest version of a spec.

        Args:
            spec_id: Spec identifier.

        Returns:
            Latest SpecVersion if found, None otherwise.
        """
        return self._store.get_latest_version(spec_id)

    def track_version(
        self,
        spec: SpecBlock,
        commit_ref: str | None = None,
    ) -> SpecVersion:
        """Track a new version of a spec.

        Args:
            spec: The spec block to track.
            commit_ref: Optional git commit reference.

        Returns:
            Created SpecVersion.
        """
        # Get commit ref from git if not provided
        if commit_ref is None:
            commit_ref = self._get_current_commit()

        # Generate version ID
        version_id = commit_ref or datetime.now().strftime("%Y%m%d%H%M%S")

        # Check if this version already exists
        existing = self._store.get_version(spec.id, version_id)
        if existing:
            return existing

        # Create new version
        version = SpecVersion(
            spec_id=spec.id,
            version_id=version_id,
            timestamp=datetime.now(),
            content=spec.text,
            commit_ref=commit_ref,
            metadata={
                "source": spec.source,
                "type": spec.type.value,
                "tags": spec.tags,
            },
        )

        self._store.save_version(version)
        logger.info(f"Tracked version {version_id} for spec {spec.id}")
        return version

    def _get_current_commit(self) -> str | None:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()[:12]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def get_diff(
        self,
        spec_id: str,
        from_version: str | None = None,
        to_version: str | None = None,
    ) -> SpecChange | None:
        """Get diff between two versions.

        Args:
            spec_id: Spec identifier.
            from_version: Starting version (default: second-to-last).
            to_version: Ending version (default: latest).

        Returns:
            SpecChange describing the differences, or None if not enough versions.
        """
        history = self._store.get_history(spec_id)
        if len(history) < 2:
            return None

        # Get versions
        if from_version and to_version:
            old_ver = self._store.get_version(spec_id, from_version)
            new_ver = self._store.get_version(spec_id, to_version)
        else:
            old_ver = history[-2]
            new_ver = history[-1]

        if not old_ver or not new_ver:
            return None

        # Compute diff
        return self._compute_diff(old_ver, new_ver)

    def _compute_diff(
        self,
        old_version: SpecVersion,
        new_version: SpecVersion,
    ) -> SpecChange:
        """Compute diff between two versions."""
        old_lines = old_version.content.splitlines()
        new_lines = new_version.content.splitlines()

        differ = difflib.unified_diff(old_lines, new_lines, lineterm="")
        diff_lines = list(differ)

        added = []
        removed = []
        modified = []

        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                removed.append(line[1:])

        # Detect modified sections (lines that were both removed and added)
        for old_line in removed[:]:
            for new_line in added[:]:
                if self._is_similar(old_line, new_line):
                    modified.append(ModifiedSection(old_text=old_line, new_text=new_line))
                    removed.remove(old_line)
                    added.remove(new_line)
                    break

        # Classify change type
        change_type = self._classify_change(added, removed, modified)

        # Infer reason from commit message
        inferred_reason = self._infer_reason(new_version)

        return SpecChange(
            spec_id=old_version.spec_id,
            from_version=old_version.version_id,
            to_version=new_version.version_id,
            timestamp=new_version.timestamp,
            added=added,
            removed=removed,
            modified=modified,
            change_type=change_type,
            inferred_reason=inferred_reason,
        )

    def _is_similar(self, old_line: str, new_line: str, threshold: float = 0.6) -> bool:
        """Check if two lines are similar (modified rather than replaced)."""
        ratio = difflib.SequenceMatcher(None, old_line, new_line).ratio()
        return ratio >= threshold

    def _classify_change(
        self,
        added: list[str],
        removed: list[str],
        modified: list[ModifiedSection],
    ) -> ChangeType:
        """Classify the type of change."""
        if not added and not removed and not modified:
            return ChangeType.COSMETIC

        # Check for breaking change indicators
        breaking_keywords = ["remove", "delete", "deprecate", "breaking", "incompatible"]
        all_text = " ".join(added + removed).lower()
        if any(kw in all_text for kw in breaking_keywords):
            return ChangeType.BREAKING

        if removed and not added:
            return ChangeType.REMOVAL
        if added and not removed:
            return ChangeType.ADDITION

        return ChangeType.SEMANTIC

    def _infer_reason(self, version: SpecVersion) -> ChangeReason | None:
        """Infer reason for change from commit message."""
        if not version.commit_ref:
            return ChangeReason(
                reason="Unknown - no commit reference",
                confidence=0.0,
                source="none",
            )

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%s", version.commit_ref],
                capture_output=True,
                text=True,
                check=True,
            )
            commit_message = result.stdout.strip()

            if commit_message:
                return ChangeReason(
                    reason=commit_message,
                    confidence=0.8,
                    source="commit_message",
                )
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        return ChangeReason(
            reason="Unknown - could not retrieve commit message",
            confidence=0.0,
            source="none",
        )

    def check_staleness(
        self,
        spec_ids: list[str],
        cached_versions: dict[str, str] | None = None,
    ) -> list[StalenessWarning]:
        """Check if specs are stale.

        Args:
            spec_ids: List of spec identifiers to check.
            cached_versions: Map of spec_id to cached version_id.

        Returns:
            List of staleness warnings for stale specs.
        """
        warnings = []
        cached_versions = cached_versions or {}

        for spec_id in spec_ids:
            latest = self._store.get_latest_version(spec_id)
            if not latest:
                continue

            cached_version = cached_versions.get(spec_id)
            if not cached_version:
                continue

            # Check if cached version is older than latest
            if cached_version != latest.version_id:
                # Get changes since cached version
                changes = self._get_changes_since(spec_id, cached_version)

                # Determine severity
                severity = self._calculate_staleness_severity(changes)

                # Check if already acknowledged
                acknowledged = self._store.is_acknowledged(spec_id, cached_version)

                warnings.append(
                    StalenessWarning(
                        spec_id=spec_id,
                        cached_version=cached_version,
                        current_version=latest.version_id,
                        changes_since=changes,
                        severity=severity,
                        acknowledged=acknowledged,
                    )
                )

        return warnings

    def _get_changes_since(
        self,
        spec_id: str,
        from_version: str,
    ) -> list[SpecChange]:
        """Get all changes since a version."""
        history = self._store.get_history(spec_id)
        changes = []

        found_start = False
        prev_version = None

        for version in history:
            if version.version_id == from_version:
                found_start = True
                prev_version = version
                continue

            if found_start and prev_version:
                change = self._compute_diff(prev_version, version)
                changes.append(change)
                prev_version = version

        return changes

    def _calculate_staleness_severity(
        self,
        changes: list[SpecChange],
    ) -> Severity:
        """Calculate staleness severity based on changes."""
        if not changes:
            return Severity.LOW

        # Check for breaking changes
        if any(c.is_breaking() for c in changes):
            return Severity.CRITICAL

        # Check for removals
        if any(c.change_type == ChangeType.REMOVAL for c in changes):
            return Severity.HIGH

        # Check for semantic changes
        if any(c.change_type == ChangeType.SEMANTIC for c in changes):
            return Severity.MEDIUM

        return Severity.LOW

    def acknowledge_staleness(
        self,
        spec_id: str,
        version: str,
    ) -> bool:
        """Acknowledge a staleness warning.

        Args:
            spec_id: Spec identifier.
            version: Version being acknowledged.

        Returns:
            True if acknowledged successfully.
        """
        self._store.acknowledge_staleness(spec_id, version)
        logger.info(f"Acknowledged staleness for {spec_id} at version {version}")
        return True

    def get_drift_report(
        self,
        since: datetime | None = None,
    ) -> DriftReport:
        """Get report on code drift from specs.

        Args:
            since: Only include changes since this time.

        Returns:
            DriftReport with drifted code items.
        """
        if not self._impact_graph:
            return DriftReport()

        drifted_items = []
        total_severity = 0.0

        # Get all specs with recent changes
        # This is a simplified implementation - in production you'd
        # iterate through all tracked specs
        for spec_id in self._get_tracked_spec_ids():
            history = self._store.get_history(spec_id)
            if len(history) < 2:
                continue

            # Get recent change
            change = self._compute_diff(history[-2], history[-1])

            if since and change.timestamp < since:
                continue

            # Find code linked to this spec
            code_nodes = self._impact_graph.query_code_for_spec(spec_id)

            for code_node in code_nodes:
                severity = self._calculate_drift_severity(change)
                drifted_items.append(
                    DriftItem(
                        code_path=code_node.data.get("path", code_node.id),
                        spec_id=spec_id,
                        spec_change=change,
                        severity=severity,
                        suggested_action=self._suggest_action(change),
                    )
                )
                total_severity += severity

        return DriftReport(
            drifted_code=drifted_items,
            total_drift_score=total_severity / max(len(drifted_items), 1),
            generated_at=datetime.now(),
        )

    def _get_tracked_spec_ids(self) -> list[str]:
        """Get all tracked spec IDs."""
        conn = self._store._get_connection()
        rows = conn.execute("SELECT DISTINCT spec_id FROM spec_versions").fetchall()
        return [row["spec_id"] for row in rows]

    def _calculate_drift_severity(self, change: SpecChange) -> float:
        """Calculate drift severity from a change."""
        if change.is_breaking():
            return 1.0
        if change.change_type == ChangeType.REMOVAL:
            return 0.8
        if change.change_type == ChangeType.SEMANTIC:
            return 0.5
        return 0.2

    def _suggest_action(self, change: SpecChange) -> str:
        """Suggest action for a drift item."""
        if change.is_breaking():
            return "URGENT: Review and update code for breaking spec change"
        if change.change_type == ChangeType.REMOVAL:
            return "Remove or update code referencing removed spec content"
        if change.change_type == ChangeType.SEMANTIC:
            return "Review code to ensure it aligns with updated spec"
        return "Minor update may be needed"

    def get_contradictions(
        self,
        spec_id: str,
    ) -> list[Contradiction]:
        """Find contradictions in spec history.

        Args:
            spec_id: Spec identifier.

        Returns:
            List of contradictions found.
        """
        history = self._store.get_history(spec_id)
        if len(history) < 2:
            return []

        contradictions = []

        # Compare consecutive versions for contradictions
        for i in range(len(history) - 1):
            old_ver = history[i]
            new_ver = history[i + 1]

            # Look for contradictory patterns
            # This is a simplified heuristic - in production you'd use
            # more sophisticated semantic analysis
            old_lines = old_ver.content.lower().splitlines()
            new_lines = new_ver.content.lower().splitlines()

            for old_line in old_lines:
                for new_line in new_lines:
                    if self._is_contradictory(old_line, new_line):
                        contradictions.append(
                            Contradiction(
                                spec_id=spec_id,
                                old_text=old_line,
                                new_text=new_line,
                                conflict_type="semantic",
                                resolution_hint="Review both statements and clarify intent",
                            )
                        )

        return contradictions

    def _is_contradictory(self, old_line: str, new_line: str) -> bool:
        """Check if two lines are contradictory."""
        # Simple heuristic: look for negation patterns
        negation_pairs = [
            ("shall", "shall not"),
            ("must", "must not"),
            ("will", "will not"),
            ("can", "cannot"),
            ("should", "should not"),
        ]

        for positive, negative in negation_pairs:
            if positive in old_line and negative in new_line:
                # Check if they're about the same thing
                old_words = set(old_line.split())
                new_words = set(new_line.split())
                overlap = len(old_words & new_words) / max(len(old_words), 1)
                if overlap > 0.5:
                    return True

        return False

    def get_deprecations(
        self,
        include_expired: bool = False,
    ) -> list[Deprecation]:
        """Get deprecated specs sorted by urgency.

        Args:
            include_expired: Include deprecations past deadline.

        Returns:
            List of deprecations ordered by urgency descending.
        """
        return self._store.get_deprecations(include_expired)

    def deprecate_spec(
        self,
        spec_id: str,
        deadline: datetime | None = None,
        replacement_spec_id: str | None = None,
        urgency: float = 0.5,
    ) -> Deprecation:
        """Mark a spec as deprecated.

        Args:
            spec_id: Spec to deprecate.
            deadline: When migration must be complete.
            replacement_spec_id: What replaces this spec.
            urgency: Urgency score 0.0-1.0.

        Returns:
            Created Deprecation.
        """
        # Find affected code using impact graph
        affected_code = []
        if self._impact_graph:
            code_nodes = self._impact_graph.query_code_for_spec(spec_id)
            affected_code = [n.data.get("path", n.id) for n in code_nodes]

        deprecation = Deprecation(
            spec_id=spec_id,
            deprecated_at=datetime.now(),
            deadline=deadline,
            replacement_spec_id=replacement_spec_id,
            affected_code=affected_code,
            urgency=urgency,
        )

        self._store.save_deprecation(deprecation)
        logger.info(f"Deprecated spec {spec_id}")
        return deprecation

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
        return self._store.prune_history(older_than, keep_min)

    def close(self) -> None:
        """Close database connection."""
        self._store.close()
