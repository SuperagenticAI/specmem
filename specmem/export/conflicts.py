"""Conflict detection for GitHub Pages deployment.

This module detects potential conflicts with existing GitHub Pages deployments.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# Patterns that indicate existing GitHub Pages content
CONFLICT_PATTERNS = [
    "index.html",
    "_config.yml",  # Jekyll
    "mkdocs.yml",  # MkDocs
    "docusaurus.config.js",  # Docusaurus
    "docusaurus.config.ts",
    "book.toml",  # mdBook
    "conf.py",  # Sphinx
    "_sidebar.md",  # Docsify
    "CNAME",  # Custom domain
]


@dataclass
class ConflictWarning:
    """Warning about a potential conflict."""

    file_path: str
    message: str


@dataclass
class ConflictResult:
    """Result of conflict detection."""

    has_conflicts: bool
    warnings: list[ConflictWarning]
    existing_files: list[str]


class ConflictDetector:
    """Detects conflicts with existing GitHub Pages deployments."""

    def __init__(self, target_dir: Path):
        """Initialize the conflict detector.

        Args:
            target_dir: The target directory for deployment
        """
        self.target_dir = Path(target_dir)

    def detect(self) -> ConflictResult:
        """Detect potential conflicts.

        Returns:
            ConflictResult with warnings and existing files
        """
        warnings: list[ConflictWarning] = []
        existing_files: list[str] = []

        if not self.target_dir.exists():
            return ConflictResult(
                has_conflicts=False,
                warnings=[],
                existing_files=[],
            )

        # Check for conflict patterns
        for pattern in CONFLICT_PATTERNS:
            pattern_path = self.target_dir / pattern
            if pattern_path.exists():
                existing_files.append(pattern)
                warnings.append(
                    ConflictWarning(
                        file_path=pattern,
                        message=self._get_warning_message(pattern),
                    )
                )

        # Check for any existing content
        if self.target_dir.exists() and any(self.target_dir.iterdir()):
            has_content = True
        else:
            has_content = False

        return ConflictResult(
            has_conflicts=len(warnings) > 0 or has_content,
            warnings=warnings,
            existing_files=existing_files,
        )

    def _get_warning_message(self, pattern: str) -> str:
        """Get a descriptive warning message for a conflict pattern.

        Args:
            pattern: The conflict pattern file name

        Returns:
            Human-readable warning message
        """
        messages = {
            "index.html": "Existing index.html will be overwritten",
            "_config.yml": "Jekyll configuration detected - this may conflict with SpecMem dashboard",
            "mkdocs.yml": "MkDocs configuration detected - consider using a subdirectory",
            "docusaurus.config.js": "Docusaurus configuration detected - consider using a subdirectory",
            "docusaurus.config.ts": "Docusaurus configuration detected - consider using a subdirectory",
            "book.toml": "mdBook configuration detected - consider using a subdirectory",
            "conf.py": "Sphinx configuration detected - consider using a subdirectory",
            "_sidebar.md": "Docsify configuration detected - consider using a subdirectory",
            "CNAME": "Custom domain configuration detected",
        }
        return messages.get(pattern, f"Existing file {pattern} may be overwritten")

    def check_overwrite_safe(self, force: bool = False) -> tuple[bool, str | None]:
        """Check if it's safe to proceed with deployment.

        Args:
            force: If True, allow overwriting existing content

        Returns:
            Tuple of (is_safe, error_message)
        """
        result = self.detect()

        if not result.has_conflicts:
            return True, None

        if force:
            return True, None

        if result.warnings:
            warning_msgs = [w.message for w in result.warnings]
            return False, (
                "Existing GitHub Pages content detected:\n"
                + "\n".join(f"  - {msg}" for msg in warning_msgs)
                + "\n\nUse --force to overwrite, or configure a different deploy_path."
            )

        return False, (
            "Target directory contains existing files. "
            "Use --force to overwrite, or configure a different deploy_path."
        )


def detect_conflicts(target_dir: Path) -> ConflictResult:
    """Convenience function to detect conflicts.

    Args:
        target_dir: The target directory for deployment

    Returns:
        ConflictResult with warnings and existing files
    """
    detector = ConflictDetector(target_dir)
    return detector.detect()


def has_documentation_conflict(target_dir: Path) -> bool:
    """Check if target directory has documentation framework files.

    Args:
        target_dir: The target directory to check

    Returns:
        True if documentation framework files are detected
    """
    result = detect_conflicts(target_dir)
    return len(result.existing_files) > 0
