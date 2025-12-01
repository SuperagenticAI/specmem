"""Cursor adapter for SpecMem.

Cursor is an AI-powered code editor that uses rules files to customize
AI behavior. This adapter handles:
- .cursorrules files
- cursor.rules files
"""

import logging
import re
from pathlib import Path

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class CursorAdapter(SpecAdapter):
    """Experimental adapter for Cursor rules files.

    Detects and parses:
    - .cursorrules files
    - cursor.rules files
    """

    FILE_PATTERNS = [
        "**/.cursorrules",
        "**/cursor.rules",
    ]

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

        return any(list(path.glob(pattern)) for pattern in self.FILE_PATTERNS)

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all Cursor rules files."""
        self.warn_if_experimental()
        blocks: list[SpecBlock] = []
        path = Path(repo_path)

        if not path.exists():
            return blocks

        # Find all Cursor files
        cursor_files: list[Path] = []
        for pattern in self.FILE_PATTERNS:
            cursor_files.extend(path.glob(pattern))

        for file_path in cursor_files:
            try:
                file_blocks = self._parse_rules_file(file_path)
                blocks.extend(file_blocks)
            except Exception as e:
                logger.warning(f"Failed to parse Cursor file {file_path}: {e}")
                # Continue processing other files (graceful degradation)

        logger.info(f"Loaded {len(blocks)} SpecBlocks from Cursor rules")
        return blocks

    def _parse_rules_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse a Cursor rules file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract sections from the rules file
        sections = self._extract_sections(content)

        if sections:
            # Create a block for each section
            for i, section in enumerate(sections):
                block_id = SpecBlock.generate_id(source, f"cursor_section_{i}")
                tags = ["cursor", "rules"]
                if section.get("title"):
                    tags.append(section["title"].lower().replace(" ", "_")[:30])

                blocks.append(
                    SpecBlock(
                        id=block_id,
                        type=SpecType.KNOWLEDGE,
                        text=section["content"],
                        source=source,
                        status=SpecStatus.ACTIVE,
                        tags=tags,
                        links=[],
                        pinned=False,
                    )
                )
        else:
            # No sections found, create a single block for the entire content
            block_id = SpecBlock.generate_id(source, f"cursor_{file_path.stem}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.KNOWLEDGE,
                    text=content,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["cursor", "rules"],
                    links=[],
                    pinned=True,  # Rules files are important context
                )
            )

        return blocks

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
