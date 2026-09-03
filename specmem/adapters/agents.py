"""AGENTS.md adapter for SpecMem.

AGENTS.md is the AAIF / Linux Foundation standard for agent instructions:
plain Markdown at the repo root or nested, with closest-file-wins. Codex,
Cursor, Factory, Warp, OpenCode, Amp, Aider, and others consume it.

This adapter handles the official filename plus the aliases already used
by the guidelines scanner:
- AGENTS.md / Agents.md
- AGENT.md / Agent.md
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class AgentsAdapter(SpecAdapter):
    """Stable adapter for AGENTS.md agent-instruction files.

    Detects and parses:
    - AGENTS.md / Agents.md (official AAIF filename)
    - AGENT.md / Agent.md (guidelines-scanner aliases)
    """

    FILENAMES = frozenset({"AGENTS.md", "Agents.md", "AGENT.md", "Agent.md"})
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
        return "AGENTS.md"

    def is_experimental(self) -> bool:
        """AGENTS.md is a stable standard, not an experimental adapter."""
        return False

    def detect(self, repo_path: str) -> bool:
        """Return True if any AGENTS.md (or alias) exists in the repository."""
        path = Path(repo_path)
        if not path.exists():
            return False
        return bool(self._find_files(path))

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all AGENTS.md files into SpecBlocks."""
        blocks: list[SpecBlock] = []
        path = Path(repo_path)

        if not path.exists():
            return blocks

        for file_path in self._find_files(path):
            try:
                file_blocks = self._parse_file(file_path)
                blocks.extend(file_blocks)
            except Exception as e:
                logger.warning(f"Failed to parse AGENTS.md file {file_path}: {e}")

        logger.info(f"Loaded {len(blocks)} SpecBlocks from AGENTS.md files")
        return blocks

    def _find_files(self, repo_path: Path) -> list[Path]:
        """Find AGENTS.md files, skipping junk directories and duplicates."""
        seen: set[Path] = set()
        found: list[Path] = []
        self._walk(repo_path, repo_path, seen, found)
        return found

    def _walk(
        self,
        root: Path,
        directory: Path,
        seen: set[Path],
        found: list[Path],
    ) -> None:
        try:
            entries = list(directory.iterdir())
        except OSError as e:
            logger.warning(f"Failed to read directory {directory}: {e}")
            return

        for entry in entries:
            try:
                if entry.is_dir():
                    if entry.name in self.SKIP_DIRS:
                        continue
                    self._walk(root, entry, seen, found)
                elif entry.is_file() and entry.name in self.FILENAMES:
                    key = entry.resolve()
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(entry)
            except OSError as e:
                logger.warning(f"Failed to inspect {entry}: {e}")

    def _parse_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse a single AGENTS.md file into SpecBlocks."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        if not content.strip():
            return blocks

        sections = self._extract_sections(content)

        if sections:
            for section in sections:
                tags = ["agents", "agents.md"]
                if section["title"]:
                    tags.append(self._slug(section["title"]))

                blocks.append(
                    SpecBlock(
                        id=SpecBlock.generate_id(source, section["content"]),
                        type=SpecType.KNOWLEDGE,
                        text=section["content"],
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=tags,
                        links=[],
                        pinned=False,
                    )
                )
        elif re.search(r"^#{1,3}\s+.+", content, re.MULTILINE):
            # Headings exist but no usable body text — skip empty-ish file
            return blocks
        else:
            blocks.append(
                SpecBlock(
                    id=SpecBlock.generate_id(source, content),
                    type=SpecType.KNOWLEDGE,
                    text=content,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["agents", "agents.md"],
                    links=[],
                    pinned=True,  # Whole-file agent context is important
                )
            )

        return blocks

    def _extract_sections(self, content: str) -> list[dict[str, str]]:
        """Split content on markdown # / ## / ### headings.

        Returns an empty list when no headings are present so the caller
        can emit a single whole-file SpecBlock.
        """
        sections: list[dict[str, str]] = []
        header_pattern = r"^(#{1,3})\s+(.+)$"

        current_section: dict[str, str] | None = None
        current_content: list[str] = []

        for line in content.split("\n"):
            header_match = re.match(header_pattern, line)
            if header_match:
                if current_section is not None:
                    current_section["content"] = "\n".join(current_content).strip()
                    if current_section["content"]:
                        sections.append(current_section)

                current_section = {
                    "title": header_match.group(2).strip(),
                    "content": "",
                }
                current_content = []
            else:
                current_content.append(line)

        if current_section is not None:
            current_section["content"] = "\n".join(current_content).strip()
            if current_section["content"]:
                sections.append(current_section)

        return sections

    @staticmethod
    def _slug(title: str) -> str:
        """Turn a heading into a short tag slug."""
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        return slug[:30]
