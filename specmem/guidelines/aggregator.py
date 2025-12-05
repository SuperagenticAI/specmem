"""Guidelines aggregator for combining and filtering guidelines from all sources."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

from specmem.guidelines.models import Guideline, GuidelinesResponse, SourceType
from specmem.guidelines.parser import GuidelinesParser
from specmem.guidelines.scanner import GuidelinesScanner


logger = logging.getLogger(__name__)


class GuidelinesAggregator:
    """Aggregates and filters guidelines from all sources."""

    def __init__(self, workspace_path: Path | None = None):
        """Initialize the aggregator.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = workspace_path or Path.cwd()
        self.scanner = GuidelinesScanner(self.workspace_path)
        self.parser = GuidelinesParser()
        self._guidelines: list[Guideline] | None = None

    def get_all(self, include_samples: bool = True) -> GuidelinesResponse:
        """Get all guidelines from all sources.

        Args:
            include_samples: Whether to include sample guidelines if no real ones exist

        Returns:
            GuidelinesResponse with all guidelines
        """
        if self._guidelines is None:
            self._load_guidelines()

        guidelines = self._guidelines or []

        # Include samples if no real guidelines and samples requested
        if not guidelines and include_samples:
            from specmem.guidelines.samples import SampleGuidelinesProvider

            provider = SampleGuidelinesProvider()
            guidelines = provider.get_all_samples()

        return GuidelinesResponse.from_guidelines(guidelines)

    def filter_by_source(self, source_type: str | SourceType) -> list[Guideline]:
        """Filter guidelines by source type.

        Args:
            source_type: Source type to filter by

        Returns:
            List of guidelines matching the source type
        """
        if self._guidelines is None:
            self._load_guidelines()

        if isinstance(source_type, str):
            try:
                source_type = SourceType(source_type)
            except ValueError:
                return []

        return [g for g in (self._guidelines or []) if g.source_type == source_type]

    def filter_by_file(self, file_path: str) -> list[Guideline]:
        """Get guidelines that apply to a specific file.

        Args:
            file_path: Path to the file to check

        Returns:
            List of guidelines that apply to the file
        """
        if self._guidelines is None:
            self._load_guidelines()

        matching: list[Guideline] = []
        for guideline in self._guidelines or []:
            if guideline.file_pattern is None:
                # Guidelines without patterns apply to all files
                matching.append(guideline)
            elif self._matches_pattern(file_path, guideline.file_pattern):
                matching.append(guideline)

        return matching

    def search(self, query: str) -> list[Guideline]:
        """Search guidelines by title and content.

        Args:
            query: Search query

        Returns:
            List of matching guidelines
        """
        if self._guidelines is None:
            self._load_guidelines()

        query_lower = query.lower()
        matching: list[Guideline] = []

        for guideline in self._guidelines or []:
            if (
                query_lower in guideline.title.lower()
                or query_lower in guideline.content.lower()
            ):
                matching.append(guideline)

        return matching

    def _load_guidelines(self) -> None:
        """Load all guidelines from scanned files."""
        self._guidelines = []
        scanned = self.scanner.scan()

        for source_type, files in scanned.items():
            for file_path in files:
                try:
                    guidelines = self.parser.parse_file(file_path, source_type)
                    self._guidelines.extend(guidelines)
                except Exception as e:
                    logger.warning(f"Failed to parse {file_path}: {e}")

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if a file path matches a glob pattern.

        Args:
            file_path: Path to check
            pattern: Glob pattern

        Returns:
            True if the path matches the pattern
        """
        # Normalize path separators
        file_path = file_path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")

        return fnmatch.fnmatch(file_path, pattern)

    def reload(self) -> None:
        """Reload guidelines from disk."""
        self._guidelines = None
