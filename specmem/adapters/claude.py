"""Claude adapter for SpecMem.

Claude is an AI assistant that can use project files to understand context.
This adapter handles:
- claude_project.xml files
- .claude/**/*.xml files
- project.claude files
"""

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class ClaudeAdapter(SpecAdapter):
    """Experimental adapter for Claude project files.

    Detects and parses:
    - claude_project.xml files
    - .claude/**/*.xml files
    - project.claude files
    """

    FILE_PATTERNS = [
        "**/claude_project.xml",
        "**/.claude/**/*.xml",
        "**/project.claude",
        "**/CLAUDE.md",
    ]

    @property
    def name(self) -> str:
        return "Claude"

    def is_experimental(self) -> bool:
        """Claude adapter is experimental."""
        return True

    def detect(self, repo_path: str) -> bool:
        """Check if Claude project files exist in the repository."""
        path = Path(repo_path)
        if not path.exists():
            return False

        return any(list(path.glob(pattern)) for pattern in self.FILE_PATTERNS)

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all Claude project files."""
        self.warn_if_experimental()
        blocks: list[SpecBlock] = []
        path = Path(repo_path)

        if not path.exists():
            return blocks

        # Find all Claude files
        claude_files: list[Path] = []
        for pattern in self.FILE_PATTERNS:
            claude_files.extend(path.glob(pattern))

        for file_path in claude_files:
            try:
                file_blocks = self._parse_file(file_path)
                blocks.extend(file_blocks)
            except Exception as e:
                logger.warning(f"Failed to parse Claude file {file_path}: {e}")
                # Continue processing other files (graceful degradation)

        logger.info(f"Loaded {len(blocks)} SpecBlocks from Claude project files")
        return blocks

    def _parse_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse a Claude file based on its type."""
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()

        if suffix == ".xml":
            return self._parse_xml_project(file_path)
        elif suffix == ".claude" or name == "claude.md":
            return self._parse_claude_file(file_path)
        else:
            logger.debug(f"Unknown Claude file type: {file_path}")
            return []

    def _parse_xml_project(self, file_path: Path) -> list[SpecBlock]:
        """Parse XML project file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
            root = ET.fromstring(content)

            # Extract project context
            context = self._extract_xml_context(root)

            # Create main project block
            block_id = SpecBlock.generate_id(source, f"claude_project_{file_path.stem}")
            tags = ["claude", "project"]

            # Add tags from XML attributes
            if root.attrib:
                for key, value in root.attrib.items():
                    if key in ("type", "category", "domain"):
                        tags.append(value.lower())

            text = self._format_context_as_text(context)

            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.KNOWLEDGE,
                    text=text,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=tags,
                    links=context.get("references", []),
                    pinned=True,  # Project files are important context
                )
            )

            # Extract individual sections as separate blocks
            section_blocks = self._extract_xml_sections(root, source, file_path.stem)
            blocks.extend(section_blocks)

        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML {file_path}: {e}")
            # Try to parse as plain text
            blocks.extend(self._parse_claude_file(file_path))
        except Exception as e:
            logger.warning(f"Failed to process Claude XML {file_path}: {e}")

        return blocks

    def _parse_claude_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse plain text Claude file (project.claude or CLAUDE.md)."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract sections from markdown-like content
        sections = self._extract_markdown_sections(content)

        if sections:
            for i, section in enumerate(sections):
                block_id = SpecBlock.generate_id(source, f"claude_section_{i}")
                tags = ["claude", "context"]
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
            # No sections, create single block
            block_id = SpecBlock.generate_id(source, f"claude_{file_path.stem}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.KNOWLEDGE,
                    text=content,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["claude", "context"],
                    links=[],
                    pinned=True,
                )
            )

        return blocks

    def _extract_xml_context(self, root: ET.Element) -> dict[str, Any]:
        """Extract context information from XML element."""
        context: dict[str, Any] = {
            "name": root.attrib.get("name", root.tag),
            "description": "",
            "requirements": [],
            "references": [],
        }

        # Extract text content from common elements
        for elem in root:
            tag = elem.tag.lower()
            text = elem.text.strip() if elem.text else ""

            if tag in ("description", "summary", "overview"):
                context["description"] = text
            elif tag in ("requirements", "specs", "specifications"):
                # Extract child requirements
                for child in elem:
                    if child.text:
                        context["requirements"].append(child.text.strip())
            elif tag in ("references", "links", "dependencies"):
                for child in elem:
                    if child.text:
                        context["references"].append(child.text.strip())
                    elif child.attrib.get("href"):
                        context["references"].append(child.attrib["href"])
            elif text:
                # Store other elements as additional context
                if "additional" not in context:
                    context["additional"] = {}
                context["additional"][tag] = text

        return context

    def _extract_xml_sections(
        self, root: ET.Element, source: str, file_stem: str
    ) -> list[SpecBlock]:
        """Extract individual sections from XML as separate blocks."""
        blocks: list[SpecBlock] = []

        for i, elem in enumerate(root):
            tag = elem.tag.lower()
            text = self._element_to_text(elem)

            if not text.strip():
                continue

            # Skip elements already processed in main context
            if tag in ("description", "summary", "overview"):
                continue

            block_id = SpecBlock.generate_id(source, f"claude_{file_stem}_{tag}_{i}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.KNOWLEDGE,
                    text=f"[{tag.title()}]\n{text}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["claude", tag],
                    links=[],
                    pinned=False,
                )
            )

        return blocks

    def _element_to_text(self, elem: ET.Element) -> str:
        """Convert XML element to readable text."""
        parts: list[str] = []

        if elem.text:
            parts.append(elem.text.strip())

        for child in elem:
            child_text = self._element_to_text(child)
            if child_text:
                parts.append(f"- {child_text}")

        return "\n".join(parts)

    def _extract_markdown_sections(self, content: str) -> list[dict[str, str]]:
        """Extract sections from markdown content."""
        sections: list[dict[str, str]] = []

        # Split by markdown headers
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

    def _format_context_as_text(self, context: dict[str, Any]) -> str:
        """Format context dictionary as readable text."""
        lines: list[str] = []

        if context.get("name"):
            lines.append(f"# {context['name']}")

        if context.get("description"):
            lines.append(f"\n{context['description']}")

        if context.get("requirements"):
            lines.append("\n## Requirements")
            for req in context["requirements"]:
                lines.append(f"- {req}")

        if context.get("references"):
            lines.append("\n## References")
            for ref in context["references"]:
                lines.append(f"- {ref}")

        if context.get("additional"):
            for key, value in context["additional"].items():
                lines.append(f"\n## {key.title()}")
                lines.append(value)

        return "\n".join(lines)
