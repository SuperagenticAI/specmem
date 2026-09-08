"""Cursor adapter for SpecMem.

Cursor is an AI-powered code editor that uses rules files to customize
AI behavior. This adapter handles:
- Legacy .cursorrules and cursor.rules files
- Modern .cursor/rules/*.mdc project rules (YAML frontmatter + markdown body)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)

# YAML frontmatter at the start of .mdc files
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

# Truncate long glob lists when embedding them in SpecBlock text/tags
_MAX_GLOBS_IN_TAG = 80
_MAX_GLOBS_IN_TEXT = 200


class CursorAdapter(SpecAdapter):
    """Experimental adapter for Cursor rules files.

    Detects and parses:
    - .cursorrules files (legacy)
    - cursor.rules files (legacy)
    - .cursor/rules/*.mdc files (current Cursor project rules)
    """

    FILE_PATTERNS = [
        "**/.cursorrules",
        "**/cursor.rules",
        "**/.cursor/rules/*.mdc",
    ]

    SKIP_DIRS = frozenset(
        {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".tox",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".specmem",
            "dist",
            "build",
        }
    )

    @property
    def name(self) -> str:
        return "Cursor"

    def is_experimental(self) -> bool:
        """Cursor adapter is experimental."""
        return True

    def detect(self, repo_path: str) -> bool:
        """Check if Cursor rules exist in the repository."""
        path = Path(repo_path)
        if not path.exists():
            return False
        return bool(self._find_files(path))

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all Cursor rules files."""
        self.warn_if_experimental()
        blocks: list[SpecBlock] = []
        path = Path(repo_path)

        if not path.exists():
            return blocks

        for file_path in self._find_files(path):
            try:
                file_blocks = self._parse_rules_file(file_path)
                blocks.extend(file_blocks)
            except Exception as e:
                logger.warning(f"Failed to parse Cursor file {file_path}: {e}")
                # Continue processing other files (graceful degradation)

        logger.info(f"Loaded {len(blocks)} SpecBlocks from Cursor rules")
        return blocks

    def _find_files(self, repo_path: Path) -> list[Path]:
        """Find Cursor rules files, skipping junk directories and duplicates."""
        seen: set[Path] = set()
        found: list[Path] = []

        for pattern in self.FILE_PATTERNS:
            try:
                matches = list(repo_path.glob(pattern))
            except OSError as e:
                logger.warning(f"Failed to glob {pattern} under {repo_path}: {e}")
                continue

            for match in matches:
                try:
                    if not match.is_file():
                        continue
                    if self._is_under_skip_dir(repo_path, match):
                        continue
                    key = match.resolve()
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(match)
                except OSError as e:
                    logger.warning(f"Failed to inspect {match}: {e}")

        return found

    def _is_under_skip_dir(self, repo_path: Path, file_path: Path) -> bool:
        """Return True if file_path sits under a junk directory relative to repo_path."""
        try:
            relative = file_path.relative_to(repo_path)
        except ValueError:
            return False
        return any(part in self.SKIP_DIRS for part in relative.parts)

    def _parse_rules_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse a Cursor rules file (legacy or .mdc)."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        if not content.strip():
            return blocks

        is_mdc = file_path.suffix.lower() == ".mdc"
        frontmatter: dict[str, Any] = {}
        body = content

        if is_mdc:
            frontmatter = self._parse_frontmatter(content)
            body = self._extract_body(content)
            if not body.strip():
                return blocks

        meta_tags, text_prefix = self._frontmatter_meta(frontmatter) if is_mdc else ([], "")

        # Extract sections from the rules body
        sections = self._extract_sections(body)

        if sections:
            for i, section in enumerate(sections):
                block_id = SpecBlock.generate_id(source, f"cursor_section_{i}")
                tags = ["cursor", "rules"]
                if is_mdc:
                    tags.append("mdc")
                tags.extend(meta_tags)
                if section.get("title"):
                    tags.append(section["title"].lower().replace(" ", "_")[:30])

                text = section["content"]
                if text_prefix:
                    text = f"{text_prefix}\n\n{text}".strip()

                blocks.append(
                    SpecBlock(
                        id=block_id,
                        type=SpecType.KNOWLEDGE,
                        text=text,
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=tags,
                        links=[],
                        pinned=False,
                    )
                )
        else:
            # No sections found, create a single block for the entire body
            text = body
            if text_prefix:
                text = f"{text_prefix}\n\n{text}".strip()
            if not text.strip():
                return blocks

            block_id = SpecBlock.generate_id(source, f"cursor_{file_path.stem}")
            tags = ["cursor", "rules"]
            if is_mdc:
                tags.append("mdc")
            tags.extend(meta_tags)

            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.KNOWLEDGE,
                    text=text,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=tags,
                    links=[],
                    pinned=True,  # Rules files are important context
                )
            )

        return blocks

    def _frontmatter_meta(self, frontmatter: dict[str, Any]) -> tuple[list[str], str]:
        """Map .mdc frontmatter into tags and an optional text prefix.

        SpecIR has no dedicated fields for description/globs/alwaysApply, so
        useful values are preserved via tags and a short text prefix.
        """
        tags: list[str] = []
        prefix_parts: list[str] = []

        if frontmatter.get("alwaysApply") is True:
            tags.append("always-apply")

        description = frontmatter.get("description")
        if description:
            desc = str(description).strip()
            if desc:
                tags.append("described")
                prefix_parts.append(desc)

        globs = self._normalize_globs(frontmatter.get("globs"))
        if globs:
            # Keep a truncated glob string in tags for filtering/search.
            tag_globs = globs if len(globs) <= _MAX_GLOBS_IN_TAG else globs[: _MAX_GLOBS_IN_TAG - 3] + "..."
            tags.append(f"globs:{tag_globs}")
            text_globs = (
                globs if len(globs) <= _MAX_GLOBS_IN_TEXT else globs[: _MAX_GLOBS_IN_TEXT - 3] + "..."
            )
            prefix_parts.append(f"Globs: {text_globs}")

        return tags, "\n".join(prefix_parts).strip()

    @staticmethod
    def _normalize_globs(value: Any) -> str | None:
        """Normalize frontmatter globs to a comma-separated string."""
        if value is None:
            return None
        if isinstance(value, (list, tuple)):
            parts = [str(v).strip() for v in value]
        else:
            parts = [p.strip() for p in str(value).split(",")]
        parts = [p for p in parts if p]
        return ",".join(parts) if parts else None

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """Extract YAML frontmatter from .mdc content."""
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}
        try:
            parsed = yaml.safe_load(match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse Cursor .mdc frontmatter: {e}")
            return {}

    def _extract_body(self, content: str) -> str:
        """Return markdown body with YAML frontmatter stripped."""
        match = FRONTMATTER_PATTERN.match(content)
        if match:
            return content[match.end() :].strip()
        return content.strip()

    def _extract_sections(self, content: str) -> list[dict[str, str]]:
        """Extract sections from rules content.

        Sections are identified by:
        - Markdown headers (# or ##)
        - Lines ending with colon followed by content
        - Numbered sections
        """
        sections: list[dict[str, str]] = []

        # Try to split by markdown headers
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

        # If no markdown headers found, try other patterns
        if not sections:
            sections = self._extract_rule_blocks(content)

        return sections

    def _extract_rule_blocks(self, content: str) -> list[dict[str, str]]:
        """Extract rule blocks from non-markdown content."""
        sections: list[dict[str, str]] = []

        # Try to split by blank lines into logical blocks
        blocks = re.split(r"\n\s*\n", content)

        for i, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue

            # Try to extract a title from the first line
            lines = block.split("\n", 1)
            first_line = lines[0].strip()

            # Check if first line looks like a title (ends with colon, is short, etc.)
            if first_line.endswith(":") or (
                len(first_line) < 50 and not first_line.startswith("-")
            ):
                title = first_line.rstrip(":")
                content_text = lines[1].strip() if len(lines) > 1 else ""
            else:
                title = f"Rule {i + 1}"
                content_text = block

            if content_text:
                sections.append({"title": title, "content": content_text})

        return sections
