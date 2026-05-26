"""Guidelines parser for extracting coding guidelines from various file formats."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from specmem.guidelines.models import Guideline, SourceType


logger = logging.getLogger(__name__)

# Regex for YAML frontmatter
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class GuidelinesParser:
    """Parses guideline files into unified Guideline objects."""

    def parse_file(self, file_path: Path, source_type: str) -> list[Guideline]:
        """Parse a guideline file based on its source type.

        Args:
            file_path: Path to the guideline file
            source_type: Type of source (claude, cursor, steering, agents)

        Returns:
            List of parsed Guideline objects
        """
        if source_type == "claude":
            return self.parse_claude(file_path)
        elif source_type == "cursor":
            return self.parse_cursor(file_path)
        elif source_type == "steering":
            return self.parse_steering(file_path)
        elif source_type == "agents":
            return self.parse_agents(file_path)
        elif source_type == "codex_skill":
            return self.parse_skill(file_path, SourceType.CODEX_SKILL, ["codex", "skill"])
        elif source_type == "claude_skill":
            return self.parse_skill(file_path, SourceType.CLAUDE_SKILL, ["claude", "skill"])
        elif source_type == "copilot":
            return self.parse_markdown_file(
                file_path, SourceType.COPILOT, ["copilot", "instructions"]
            )
        elif source_type == "gemini":
            return self.parse_markdown_file(file_path, SourceType.GEMINI, ["gemini", "guidelines"])
        elif source_type == "opencode":
            return self.parse_markdown_file(
                file_path, SourceType.OPENCODE, ["opencode", "guidelines"]
            )
        elif source_type == "qwen":
            return self.parse_markdown_file(file_path, SourceType.QWEN, ["qwen", "guidelines"])
        else:
            logger.warning(f"Unknown source type: {source_type}")
            return []

    def parse_claude(self, file_path: Path) -> list[Guideline]:
        """Parse CLAUDE.md file into guidelines.

        Args:
            file_path: Path to CLAUDE.md file

        Returns:
            List of Guideline objects
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        return self._parse_markdown_sections(
            content, str(file_path), SourceType.CLAUDE, ["claude", "guidelines"]
        )

    def parse_cursor(self, file_path: Path) -> list[Guideline]:
        """Parse a Cursor rules file into guidelines.

        Handles both legacy ``.cursorrules`` files (plain markdown) and modern
        ``.cursor/rules/*.mdc`` files, which carry YAML frontmatter with
        ``description``, ``globs``, and ``alwaysApply`` keys.

        Args:
            file_path: Path to the Cursor rules file

        Returns:
            List of Guideline objects
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        frontmatter = self._parse_frontmatter(content)
        body = self._extract_body(content)

        guidelines = self._parse_markdown_sections(
            body, str(file_path), SourceType.CURSOR, ["cursor", "rules"]
        )

        always_apply = bool(frontmatter.get("alwaysApply"))
        file_pattern = self._normalize_patterns(frontmatter.get("globs"))
        for guideline in guidelines:
            # alwaysApply rules apply to every file, so leave file_pattern unset.
            if file_pattern and not always_apply:
                guideline.file_pattern = file_pattern
            if always_apply:
                guideline.tags.append("always-apply")
            if frontmatter.get("description"):
                guideline.tags.append("described")
        return guidelines

    def parse_steering(self, file_path: Path) -> list[Guideline]:
        """Parse Kiro steering file into guidelines.

        Args:
            file_path: Path to steering file

        Returns:
            List of Guideline objects
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        # Extract frontmatter
        frontmatter = self._parse_frontmatter(content)
        body = self._extract_body(content)

        # Get file pattern from frontmatter
        file_pattern = frontmatter.get("fileMatchPattern")
        inclusion = frontmatter.get("inclusion", "always")

        # Extract title from body
        title = self._extract_title(body, file_path)

        tags = ["steering", inclusion]
        if file_pattern:
            tags.append("file-specific")

        guideline = Guideline(
            id=Guideline.generate_id(str(file_path), title),
            title=title,
            content=body,
            source_type=SourceType.STEERING,
            source_file=str(file_path),
            file_pattern=file_pattern,
            tags=tags,
        )

        return [guideline]

    def parse_agents(self, file_path: Path) -> list[Guideline]:
        """Parse AGENTS.md file into guidelines.

        Args:
            file_path: Path to AGENTS.md file

        Returns:
            List of Guideline objects
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        return self._parse_markdown_sections(
            content, str(file_path), SourceType.AGENTS, ["agents", "guidelines"]
        )

    def parse_markdown_file(
        self,
        file_path: Path,
        source_type: SourceType,
        base_tags: list[str],
    ) -> list[Guideline]:
        """Parse a generic agent markdown instruction file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        body = self._extract_body(content)
        frontmatter = self._parse_frontmatter(content)
        file_pattern = self._normalize_patterns(
            frontmatter.get("applyTo") or frontmatter.get("globs")
        )

        guidelines = self._parse_markdown_sections(body, str(file_path), source_type, base_tags)
        for guideline in guidelines:
            if file_pattern:
                guideline.file_pattern = file_pattern
            if frontmatter.get("description"):
                guideline.tags.append("described")
        return guidelines

    def parse_skill(
        self,
        file_path: Path,
        source_type: SourceType,
        base_tags: list[str],
    ) -> list[Guideline]:
        """Parse an agent skill document as procedural memory."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

        frontmatter = self._parse_frontmatter(content)
        body = self._extract_body(content)
        title = str(
            frontmatter.get("name") or file_path.parent.name or self._extract_title(body, file_path)
        )
        description = frontmatter.get("description")
        text = body
        if description:
            text = f"{description}\n\n{text}".strip()

        tags = [*base_tags, file_path.parent.name]
        if frontmatter.get("license"):
            tags.append("licensed")

        return [
            Guideline(
                id=Guideline.generate_id(str(file_path), title),
                title=title,
                content=text,
                source_type=source_type,
                source_file=str(file_path),
                tags=tags,
            )
        ]

    def _parse_markdown_sections(
        self,
        content: str,
        source_file: str,
        source_type: SourceType,
        base_tags: list[str],
    ) -> list[Guideline]:
        """Parse markdown content into sections as guidelines.

        Args:
            content: Markdown content
            source_file: Path to source file
            source_type: Type of source
            base_tags: Base tags to apply to all guidelines

        Returns:
            List of Guideline objects
        """
        guidelines: list[Guideline] = []
        sections = self._extract_sections(content)

        if sections:
            for i, section in enumerate(sections):
                title = section.get("title", f"Section {i + 1}")
                section_content = section.get("content", "")

                if not section_content.strip():
                    continue

                tags = base_tags.copy()
                # Add tag from title
                tag = title.lower().replace(" ", "-")[:30]
                if tag and tag not in tags:
                    tags.append(tag)

                guideline = Guideline(
                    id=Guideline.generate_id(source_file, title),
                    title=title,
                    content=section_content,
                    source_type=source_type,
                    source_file=source_file,
                    tags=tags,
                )
                guidelines.append(guideline)
        else:
            # No sections found, create single guideline
            title = self._extract_title(content, Path(source_file))
            guideline = Guideline(
                id=Guideline.generate_id(source_file, title),
                title=title,
                content=content,
                source_type=source_type,
                source_file=source_file,
                tags=base_tags,
            )
            guidelines.append(guideline)

        return guidelines

    def _extract_sections(self, content: str) -> list[dict[str, str]]:
        """Extract sections from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of sections with title and content
        """
        sections: list[dict[str, str]] = []
        header_pattern = r"^(#{1,3})\s+(.+)$"
        lines = content.split("\n")

        current_section: dict[str, str] | None = None
        current_content: list[str] = []

        for line in lines:
            header_match = re.match(header_pattern, line)
            if header_match:
                # Save previous section
                if current_section is not None:
                    current_section["content"] = "\n".join(current_content).strip()
                    if current_section["content"]:
                        sections.append(current_section)

                # Start new section
                current_section = {
                    "title": header_match.group(2).strip(),
                    "content": "",
                }
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section is not None:
            current_section["content"] = "\n".join(current_content).strip()
            if current_section["content"]:
                sections.append(current_section)

        return sections

    @staticmethod
    def _normalize_patterns(value: Any) -> str | None:
        """Normalize a frontmatter glob value to a comma-separated pattern string.

        Accepts a YAML list (``["*.py", "*.ts"]``), a comma-separated string
        (``"*.py, *.ts"``), or a single pattern, and returns a single
        comma-separated string (or ``None`` if empty).
        """
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            parts = [str(v).strip() for v in value]
        else:
            parts = [p.strip() for p in str(value).split(",")]
        parts = [p for p in parts if p]
        return ",".join(parts) if parts else None

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from content.

        Args:
            content: Full file content

        Returns:
            Dictionary of frontmatter values
        """
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}

        try:
            frontmatter_text = match.group(1)
            parsed = yaml.safe_load(frontmatter_text)
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return {}

    def _extract_body(self, content: str) -> str:
        """Extract content without frontmatter.

        Args:
            content: Full file content

        Returns:
            Content without frontmatter
        """
        match = FRONTMATTER_PATTERN.match(content)
        if match:
            return content[match.end() :].strip()
        return content.strip()

    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from content.

        Args:
            content: Content to extract title from
            file_path: Path to file (used as fallback)

        Returns:
            Extracted title
        """
        # Look for first heading
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()

        # Fallback to filename
        return file_path.stem.replace("-", " ").replace("_", " ").title()
