"""Guidelines aggregator for combining and filtering guidelines from all sources."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

from specmem.core.specir import SpecBlock, SpecStatus, SpecType
from specmem.guidelines.models import Guideline, GuidelinesResponse, SourceType
from specmem.guidelines.optimizer import OptimizedSkillStore
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
            if query_lower in guideline.title.lower() or query_lower in guideline.content.lower():
                matching.append(guideline)

        return matching

    def build_context(
        self,
        files: list[str] | None = None,
        task: str | None = None,
    ) -> dict[str, list[Guideline]]:
        """Build a layered agent-memory context from local guidance files.

        The result mirrors how coding agents should consume project memory:
        always-on guidance first, file-scoped guidance for changed files next,
        and procedural skills only when their title, tags, or description match
        the task intent.
        """
        if self._guidelines is None:
            self._load_guidelines()

        files = files or []
        always_on: list[Guideline] = []
        file_scoped: list[Guideline] = []
        skills: list[Guideline] = []

        for guideline in self._guidelines or []:
            if self._is_skill(guideline):
                if task and self._matches_task(guideline, task):
                    skills.append(guideline)
                continue

            if guideline.file_pattern:
                if any(self._matches_pattern(file_path, guideline.file_pattern) for file_path in files):
                    file_scoped.append(guideline)
            else:
                always_on.append(guideline)

        return {
            "always_on": self._dedupe_guidelines(always_on),
            "file_scoped": self._dedupe_guidelines(file_scoped),
            "skills": self._dedupe_guidelines(skills),
        }

    def to_spec_blocks(
        self,
        include_samples: bool = False,
        optimize_skills: bool = False,
    ) -> list[SpecBlock]:
        """Convert discovered guidelines to SpecBlocks for memory indexing."""
        response = self.get_all(include_samples=include_samples)
        optimized_store = OptimizedSkillStore(self.workspace_path) if optimize_skills else None
        blocks: list[SpecBlock] = []

        for guideline in response.guidelines:
            tags = ["agent-guidance", guideline.source_type.value, *guideline.tags]
            if guideline.file_pattern:
                tags.append("file-scoped")

            text = guideline.content.strip()
            if optimized_store and self._is_skill(guideline):
                optimized = optimized_store.resolve(Path(guideline.source_file))
                if optimized:
                    text = optimized.content.strip()
                    tags.extend(optimized.tags)
            if not text:
                continue

            blocks.append(
                SpecBlock(
                    id=SpecBlock.generate_id(guideline.source_file, text),
                    type=SpecType.KNOWLEDGE,
                    text=f"# {guideline.title}\n\n{text}",
                    source=guideline.source_file,
                    status=SpecStatus.ACTIVE,
                    tags=list(dict.fromkeys(tags)),
                    links=[],
                    pinned=guideline.source_type
                    not in {SourceType.CODEX_SKILL, SourceType.CLAUDE_SKILL},
                )
            )

        return blocks

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

        The pattern may be a single glob or a comma-separated list of globs
        (as produced for Cursor ``globs`` or Copilot ``applyTo``); the path
        matches if it matches any of them.

        Args:
            file_path: Path to check
            pattern: Glob pattern, or comma-separated globs

        Returns:
            True if the path matches the pattern
        """
        # Normalize path separators
        file_path = file_path.replace("\\", "/")

        for single in pattern.split(","):
            single = single.strip().replace("\\", "/")
            if not single:
                continue
            if fnmatch.fnmatch(file_path, single):
                return True
            # fnmatch has no recursive "**"; let a leading "**/" also match
            # files at the repository root (e.g. "**/*.py" matching "a.py").
            if single.startswith("**/") and fnmatch.fnmatch(file_path, single[3:]):
                return True
        return False

    def _is_skill(self, guideline: Guideline) -> bool:
        return guideline.source_type in {SourceType.CODEX_SKILL, SourceType.CLAUDE_SKILL}

    def _matches_task(self, guideline: Guideline, task: str) -> bool:
        tokens = {
            token
            for token in re_split_words(task)
            if len(token) >= 3
        }
        if not tokens:
            return False

        haystack = " ".join(
            [guideline.title, guideline.content, guideline.source_file, " ".join(guideline.tags)]
        ).lower()
        return any(token in haystack for token in tokens)

    def _dedupe_guidelines(self, guidelines: list[Guideline]) -> list[Guideline]:
        seen: set[str] = set()
        unique: list[Guideline] = []
        for guideline in guidelines:
            if guideline.id in seen:
                continue
            seen.add(guideline.id)
            unique.append(guideline)
        return unique

    def reload(self) -> None:
        """Reload guidelines from disk."""
        self._guidelines = None


def re_split_words(text: str) -> list[str]:
    """Split task text into lowercase search terms without pulling in regex state."""
    import re

    return re.findall(r"[a-z0-9_+-]+", text.lower())
