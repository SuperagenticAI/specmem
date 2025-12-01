"""Agent Experience Pack Builder for SpecMem.

Generates the .specmem/ output directory containing:
- agent_memory.json: All active SpecBlocks with metadata
- agent_context.md: Human-readable summary
- knowledge_index.json: Searchable keyword index
"""

import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from specmem.core.specir import SpecBlock, SpecStatus


logger = logging.getLogger(__name__)


class AgentMemory(BaseModel):
    """Structure for agent_memory.json output."""

    version: str = "1.0"
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    blocks: list[dict] = Field(default_factory=list)
    pinned_ids: list[str] = Field(default_factory=list)
    statistics: dict = Field(default_factory=dict)


class KnowledgeIndex(BaseModel):
    """Structure for knowledge_index.json output."""

    version: str = "1.0"
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    keywords: dict[str, list[str]] = Field(default_factory=dict)
    type_index: dict[str, list[str]] = Field(default_factory=dict)
    source_index: dict[str, list[str]] = Field(default_factory=dict)


class PackBuilder:
    """Builds Agent Experience Packs from SpecBlocks.

    The pack is output to .specmem/ directory and contains everything
    a coding agent needs to understand the project's specifications.
    """

    def __init__(self, output_dir: str = ".specmem") -> None:
        """Initialize the pack builder.

        Args:
            output_dir: Directory to output the pack
        """
        self.output_dir = Path(output_dir)

    def build(
        self,
        blocks: list[SpecBlock],
        preserve_context: bool = True,
    ) -> Path:
        """Build the Agent Experience Pack.

        Args:
            blocks: List of SpecBlocks to include
            preserve_context: Whether to preserve user modifications to agent_context.md

        Returns:
            Path to the output directory
        """
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Filter to active blocks only
        active_blocks = [b for b in blocks if b.status == SpecStatus.ACTIVE]

        # Generate each component
        self._generate_agent_memory(active_blocks)
        self._generate_knowledge_index(active_blocks)
        self._generate_agent_context(active_blocks, preserve_context)

        logger.info(f"Built Agent Experience Pack at {self.output_dir}")
        return self.output_dir

    def _generate_agent_memory(self, blocks: list[SpecBlock]) -> None:
        """Generate agent_memory.json."""
        memory = AgentMemory(
            blocks=[b.model_dump() for b in blocks],
            pinned_ids=[b.id for b in blocks if b.pinned],
            statistics={
                "total": len(blocks),
                "by_type": self._count_by_field(blocks, "type"),
                "pinned": sum(1 for b in blocks if b.pinned),
            },
        )

        output_path = self.output_dir / "agent_memory.json"
        output_path.write_text(memory.model_dump_json(indent=2))
        logger.debug(f"Generated {output_path}")

    def _generate_knowledge_index(self, blocks: list[SpecBlock]) -> None:
        """Generate knowledge_index.json."""
        keywords: dict[str, list[str]] = defaultdict(list)
        type_index: dict[str, list[str]] = defaultdict(list)
        source_index: dict[str, list[str]] = defaultdict(list)

        for block in blocks:
            # Extract keywords from text
            block_keywords = self._extract_keywords(block.text)
            for keyword in block_keywords:
                if block.id not in keywords[keyword]:
                    keywords[keyword].append(block.id)

            # Index by type
            type_index[block.type.value].append(block.id)

            # Index by source
            source_index[block.source].append(block.id)

        index = KnowledgeIndex(
            keywords=dict(keywords),
            type_index=dict(type_index),
            source_index=dict(source_index),
        )

        output_path = self.output_dir / "knowledge_index.json"
        output_path.write_text(index.model_dump_json(indent=2))
        logger.debug(f"Generated {output_path}")

    def _generate_agent_context(self, blocks: list[SpecBlock], preserve_context: bool) -> None:
        """Generate agent_context.md."""
        output_path = self.output_dir / "agent_context.md"

        # Check for existing user modifications
        existing_content = ""
        user_section = ""
        if preserve_context and output_path.exists():
            existing_content = output_path.read_text()
            # Extract user-added sections (marked with <!-- USER -->)
            user_match = re.search(
                r"<!-- USER -->(.*?)<!-- /USER -->",
                existing_content,
                re.DOTALL,
            )
            if user_match:
                user_section = user_match.group(0)

        # Generate new content
        content = self._build_context_markdown(blocks)

        # Append user section if exists
        if user_section:
            content += f"\n\n{user_section}"

        output_path.write_text(content)
        logger.debug(f"Generated {output_path}")

    def _build_context_markdown(self, blocks: list[SpecBlock]) -> str:
        """Build the markdown content for agent_context.md."""
        lines = [
            "# Agent Context",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "This file provides a human-readable summary of the project's specifications.",
            "It is automatically generated by SpecMem.",
            "",
            "## Summary",
            "",
            f"- **Total Specifications**: {len(blocks)}",
            f"- **Pinned (Critical)**: {sum(1 for b in blocks if b.pinned)}",
            "",
        ]

        # Group by type
        by_type: dict[str, list[SpecBlock]] = defaultdict(list)
        for block in blocks:
            by_type[block.type.value].append(block)

        # Add sections for each type
        type_order = ["requirement", "design", "task", "decision", "knowledge", "md"]
        for spec_type in type_order:
            type_blocks = by_type.get(spec_type, [])
            if not type_blocks:
                continue

            lines.append(f"## {spec_type.title()}s ({len(type_blocks)})")
            lines.append("")

            for block in type_blocks[:10]:  # Limit to 10 per type
                pinned = "📌 " if block.pinned else ""
                text_preview = block.text[:100].replace("\n", " ")
                if len(block.text) > 100:
                    text_preview += "..."
                lines.append(f"- {pinned}**{block.id[:8]}**: {text_preview}")

            if len(type_blocks) > 10:
                lines.append(f"- *...and {len(type_blocks) - 10} more*")

            lines.append("")

        # Add placeholder for user content
        lines.extend(
            [
                "## Custom Notes",
                "",
                "<!-- USER -->",
                "Add your custom notes here. This section will be preserved on regeneration.",
                "<!-- /USER -->",
            ]
        )

        return "\n".join(lines)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text."""
        # Simple keyword extraction: words longer than 4 chars
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

        # Filter common words
        stopwords = {
            "that",
            "this",
            "with",
            "from",
            "have",
            "will",
            "when",
            "then",
            "shall",
            "should",
            "would",
            "could",
            "must",
            "been",
            "being",
            "were",
            "what",
            "which",
            "where",
            "there",
            "their",
            "they",
            "about",
            "after",
            "before",
            "between",
            "through",
            "during",
        }

        keywords = [w for w in words if w not in stopwords]

        # Return unique keywords
        return list(set(keywords))

    def _count_by_field(self, blocks: list[SpecBlock], field: str) -> dict[str, int]:
        """Count blocks by a field value."""
        counts: dict[str, int] = defaultdict(int)
        for block in blocks:
            value = getattr(block, field)
            if hasattr(value, "value"):
                value = value.value
            counts[str(value)] += 1
        return dict(counts)
