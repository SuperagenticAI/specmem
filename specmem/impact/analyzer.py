"""SpecImpact - Dependency analyzer for SpecMem.

Maps code files to related specifications and detects which specs
are affected by code changes.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from specmem.core.specir import SpecBlock


logger = logging.getLogger(__name__)


@dataclass
class ImpactResult:
    """Result of impact analysis."""

    changed_files: list[str] = field(default_factory=list)
    affected_specs: list[SpecBlock] = field(default_factory=list)
    uncovered_files: list[str] = field(default_factory=list)


class SpecImpactAnalyzer:
    """Analyzes impact of code changes on specifications.

    Maps code files to related SpecIR blocks and identifies which
    specifications need attention when code changes.
    """

    def __init__(self, repo_path: str = ".") -> None:
        """Initialize the analyzer.

        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self._file_to_specs: dict[str, list[SpecBlock]] = {}

    def build_mapping(self, blocks: list[SpecBlock]) -> None:
        """Build mapping from files to specifications.

        Args:
            blocks: List of SpecBlocks to map
        """
        self._file_to_specs.clear()

        for block in blocks:
            # Extract file references from block text
            files = self._extract_file_references(block.text)

            # Also map by source file
            source_dir = Path(block.source).parent
            if source_dir.name == "specs":
                # This is a spec file, try to find related code
                pass

            for file_ref in files:
                if file_ref not in self._file_to_specs:
                    self._file_to_specs[file_ref] = []
                self._file_to_specs[file_ref].append(block)

    def _extract_file_references(self, text: str) -> list[str]:
        """Extract file path references from text.

        Args:
            text: Text to search for file references

        Returns:
            List of file paths found
        """
        import re

        files = []

        # Match common file patterns
        patterns = [
            r"`([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)`",  # `path/to/file.ext`
            r"'([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)'",  # 'path/to/file.ext'
            r'"([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)"',  # "path/to/file.ext"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            files.extend(matches)

        return list(set(files))

    def get_changed_files(self, base_ref: str = "HEAD~1") -> list[str]:
        """Get list of changed files using git.

        Args:
            base_ref: Git reference to compare against

        Returns:
            List of changed file paths
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base_ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            return files
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to get git diff: {e}")
            return []
        except FileNotFoundError:
            logger.warning("Git not found")
            return []

    def analyze(self, blocks: list[SpecBlock], base_ref: str = "HEAD~1") -> ImpactResult:
        """Analyze impact of code changes on specifications.

        Args:
            blocks: List of SpecBlocks to analyze
            base_ref: Git reference to compare against

        Returns:
            ImpactResult with affected specs and uncovered files
        """
        # Build mapping
        self.build_mapping(blocks)

        # Get changed files
        changed_files = self.get_changed_files(base_ref)

        # Find affected specs
        affected_specs: list[SpecBlock] = []
        affected_ids: set[str] = set()
        uncovered_files: list[str] = []

        for file_path in changed_files:
            specs = self._file_to_specs.get(file_path, [])
            if specs:
                for spec in specs:
                    if spec.id not in affected_ids:
                        affected_specs.append(spec)
                        affected_ids.add(spec.id)
            else:
                uncovered_files.append(file_path)

        return ImpactResult(
            changed_files=changed_files,
            affected_specs=affected_specs,
            uncovered_files=uncovered_files,
        )

    def get_specs_for_file(self, file_path: str) -> list[SpecBlock]:
        """Get specifications related to a file.

        Args:
            file_path: Path to the file

        Returns:
            List of related SpecBlocks
        """
        return self._file_to_specs.get(file_path, [])
