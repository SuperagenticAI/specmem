"""History tracking for static dashboard export.

This module manages historical data points for trend visualization.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from specmem.export.models import ExportBundle, HistoryEntry


class HistoryManager:
    """Manages historical data for trend tracking."""

    DEFAULT_LIMIT = 30

    def __init__(self, history_file: Path, limit: int = DEFAULT_LIMIT):
        """Initialize the history manager.

        Args:
            history_file: Path to the history JSON file
            limit: Maximum number of history entries to keep
        """
        self.history_file = Path(history_file)
        self.limit = limit

    def load(self) -> list[HistoryEntry]:
        """Load history from file.

        Returns:
            List of history entries, empty if file doesn't exist
        """
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)
                return [HistoryEntry.from_dict(entry) for entry in data]
        except (json.JSONDecodeError, KeyError, ValueError):
            # Corrupted file, start fresh
            return []

    def save(self, entries: list[HistoryEntry]) -> None:
        """Save history to file.

        Args:
            entries: List of history entries to save
        """
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump([entry.to_dict() for entry in entries], f, indent=2)

    def append(self, bundle: ExportBundle) -> list[HistoryEntry]:
        """Append current metrics to history.

        Args:
            bundle: The export bundle with current metrics

        Returns:
            Updated list of history entries (truncated to limit)
        """
        entries = self.load()

        new_entry = HistoryEntry(
            timestamp=bundle.metadata.generated_at,
            coverage_percentage=bundle.coverage_percentage,
            health_score=bundle.health_score,
            validation_errors=len(bundle.validation_errors),
        )

        entries.append(new_entry)

        # Truncate to limit (keep most recent)
        if len(entries) > self.limit:
            entries = entries[-self.limit:]

        self.save(entries)
        return entries

    def truncate(self, entries: list[HistoryEntry]) -> list[HistoryEntry]:
        """Truncate history to configured limit.

        Args:
            entries: List of history entries

        Returns:
            Truncated list (most recent entries)
        """
        if len(entries) <= self.limit:
            return entries
        return entries[-self.limit:]

    def get_history_for_bundle(self, bundle: ExportBundle) -> list[HistoryEntry]:
        """Get history entries to include in export bundle.

        This loads existing history and optionally appends current metrics.

        Args:
            bundle: The export bundle

        Returns:
            List of history entries for the bundle
        """
        entries = self.load()
        return self.truncate(entries)
