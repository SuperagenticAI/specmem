"""Guidelines converter for transforming between different formats."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from specmem.guidelines.models import ConversionResult, Guideline, SourceType


class GuidelinesConverter:
    """Converts guidelines between different formats."""

    def to_steering(self, guideline: Guideline) -> ConversionResult:
        """Convert a guideline to Kiro steering format.

        Args:
            guideline: Guideline to convert

        Returns:
            ConversionResult with steering file content
        """
        # Generate filename from title
        filename = self._generate_filename(guideline.title) + ".md"

        # Determine frontmatter
        inclusion_mode = self.suggest_inclusion_mode(guideline)
        file_pattern = self.suggest_file_pattern(guideline)

        frontmatter: dict[str, Any] = {"inclusion": inclusion_mode}
        if file_pattern:
            frontmatter["fileMatchPattern"] = file_pattern

        # Build content
        yaml_content = yaml.dump(frontmatter, default_flow_style=False).strip()
        content = f"---\n{yaml_content}\n---\n\n# {guideline.title}\n\n{guideline.content}"

        return ConversionResult(
            filename=filename,
            content=content,
            frontmatter=frontmatter,
            source_guideline=guideline,
        )

    def to_claude(self, guidelines: list[Guideline]) -> str:
        """Convert guidelines to CLAUDE.md format.

        Args:
            guidelines: List of guidelines to convert

        Returns:
            CLAUDE.md content
        """
        sections: list[str] = ["# Project Guidelines\n"]

        for guideline in guidelines:
            sections.append(f"## {guideline.title}\n")
            sections.append(guideline.content)
            sections.append("")

        return "\n".join(sections)

    def to_cursor(self, guidelines: list[Guideline]) -> str:
        """Convert guidelines to .cursorrules format.

        Args:
            guidelines: List of guidelines to convert

        Returns:
            .cursorrules content
        """
        sections: list[str] = []

        for guideline in guidelines:
            sections.append(f"# {guideline.title}\n")
            sections.append(guideline.content)
            sections.append("")

        return "\n".join(sections)

    def suggest_inclusion_mode(self, guideline: Guideline) -> str:
        """Suggest appropriate inclusion mode based on content.

        Args:
            guideline: Guideline to analyze

        Returns:
            Suggested inclusion mode (always, fileMatch, manual)
        """
        content_lower = guideline.content.lower()
        title_lower = guideline.title.lower()

        # Check for file-specific patterns
        file_patterns = [
            r"\.py\b",
            r"\.ts\b",
            r"\.js\b",
            r"\.tsx\b",
            r"\.jsx\b",
            r"python",
            r"typescript",
            r"javascript",
            r"test",
            r"spec",
        ]

        for pattern in file_patterns:
            if re.search(pattern, content_lower) or re.search(pattern, title_lower):
                return "fileMatch"

        # Check for manual triggers
        manual_keywords = ["optional", "advanced", "experimental", "deprecated"]
        for keyword in manual_keywords:
            if keyword in content_lower or keyword in title_lower:
                return "manual"

        return "always"

    def suggest_file_pattern(self, guideline: Guideline) -> str | None:
        """Suggest file pattern based on guideline content.

        Args:
            guideline: Guideline to analyze

        Returns:
            Suggested file pattern or None
        """
        content_lower = guideline.content.lower()
        title_lower = guideline.title.lower()

        # Map keywords to patterns
        pattern_map = {
            "python": "**/*.py",
            ".py": "**/*.py",
            "typescript": "**/*.ts",
            ".ts": "**/*.ts",
            "javascript": "**/*.js",
            ".js": "**/*.js",
            "react": "**/*.tsx",
            ".tsx": "**/*.tsx",
            "test": "tests/**/*.py",
            "spec": "tests/**/*.py",
        }

        for keyword, pattern in pattern_map.items():
            if keyword in content_lower or keyword in title_lower:
                return pattern

        return None

    def bulk_convert_to_steering(
        self, guidelines: list[Guideline]
    ) -> list[ConversionResult]:
        """Convert multiple guidelines to steering files.

        Args:
            guidelines: List of guidelines to convert

        Returns:
            List of ConversionResults
        """
        results: list[ConversionResult] = []
        seen_filenames: set[str] = set()

        for guideline in guidelines:
            result = self.to_steering(guideline)

            # Handle duplicate filenames
            base_filename = result.filename
            counter = 1
            while result.filename in seen_filenames:
                name, ext = base_filename.rsplit(".", 1)
                result.filename = f"{name}-{counter}.{ext}"
                counter += 1

            seen_filenames.add(result.filename)
            results.append(result)

        return results

    def write_steering_files(
        self, results: list[ConversionResult], output_dir: Path
    ) -> list[Path]:
        """Write conversion results to steering files.

        Args:
            results: List of ConversionResults
            output_dir: Directory to write files to

        Returns:
            List of written file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []

        for result in results:
            file_path = output_dir / result.filename
            file_path.write_text(result.content, encoding="utf-8")
            written.append(file_path)

        return written

    def _generate_filename(self, title: str) -> str:
        """Generate a filename from a title.

        Args:
            title: Title to convert

        Returns:
            Kebab-case filename
        """
        # Convert to lowercase and replace spaces/special chars with hyphens
        filename = title.lower()
        filename = re.sub(r"[^a-z0-9]+", "-", filename)
        filename = filename.strip("-")
        return filename[:50] if filename else "guideline"
