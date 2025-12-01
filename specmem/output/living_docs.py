"""Living Documentation Generator for SpecMem.

Generates Markdown documentation from specifications that stays
up-to-date with the codebase.
"""

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from specmem.core.specir import SpecBlock


logger = logging.getLogger(__name__)


class LivingDocsGenerator:
    """Generates living documentation from SpecBlocks.

    Creates Markdown summaries organized by specification type,
    with links to source files and relationships.
    """

    def __init__(self, output_dir: str = "docs/specs") -> None:
        """Initialize the generator.

        Args:
            output_dir: Directory to output documentation
        """
        self.output_dir = Path(output_dir)

    def generate(self, blocks: list[SpecBlock]) -> Path:
        """Generate living documentation from SpecBlocks.

        Args:
            blocks: List of SpecBlocks to document

        Returns:
            Path to the output directory
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate index
        self._generate_index(blocks)

        # Generate per-type documentation
        by_type = self._group_by_type(blocks)
        for spec_type, type_blocks in by_type.items():
            self._generate_type_doc(spec_type, type_blocks)

        # Generate per-source documentation
        by_source = self._group_by_source(blocks)
        self._generate_source_index(by_source)

        logger.info(f"Generated living documentation at {self.output_dir}")
        return self.output_dir

    def _generate_index(self, blocks: list[SpecBlock]) -> None:
        """Generate the main index file."""
        lines = [
            "# Specification Documentation",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "This documentation is automatically generated from project specifications.",
            "",
            "## Overview",
            "",
            f"- **Total Specifications**: {len(blocks)}",
            f"- **Pinned (Critical)**: {sum(1 for b in blocks if b.pinned)}",
            "",
            "## By Type",
            "",
        ]

        # Count by type
        by_type = self._group_by_type(blocks)
        for spec_type in ["requirement", "design", "task", "decision", "knowledge", "md"]:
            count = len(by_type.get(spec_type, []))
            if count > 0:
                lines.append(f"- [{spec_type.title()}s](./{spec_type}s.md) ({count})")

        lines.extend(
            [
                "",
                "## By Source",
                "",
                "See [Source Index](./sources.md) for specifications organized by source file.",
            ]
        )

        output_path = self.output_dir / "index.md"
        output_path.write_text("\n".join(lines))

    def _generate_type_doc(self, spec_type: str, blocks: list[SpecBlock]) -> None:
        """Generate documentation for a specific type."""
        lines = [
            f"# {spec_type.title()}s",
            "",
            f"*{len(blocks)} specifications*",
            "",
            "[← Back to Index](./index.md)",
            "",
        ]

        # Group by source
        by_source: dict[str, list[SpecBlock]] = defaultdict(list)
        for block in blocks:
            by_source[block.source].append(block)

        for source, source_blocks in sorted(by_source.items()):
            lines.append(f"## From `{source}`")
            lines.append("")

            for block in source_blocks:
                pinned = "📌 " if block.pinned else ""
                status = f" [{block.status.value}]" if block.status.value != "active" else ""

                lines.append(f"### {pinned}{block.id[:8]}{status}")
                lines.append("")
                lines.append(block.text)
                lines.append("")

                if block.tags:
                    lines.append(f"**Tags**: {', '.join(block.tags)}")
                    lines.append("")

                if block.links:
                    lines.append(f"**Related**: {', '.join(block.links)}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        output_path = self.output_dir / f"{spec_type}s.md"
        output_path.write_text("\n".join(lines))

    def _generate_source_index(self, by_source: dict[str, list[SpecBlock]]) -> None:
        """Generate source file index."""
        lines = [
            "# Specifications by Source",
            "",
            "[← Back to Index](./index.md)",
            "",
        ]

        for source, blocks in sorted(by_source.items()):
            lines.append(f"## `{source}`")
            lines.append("")
            lines.append(f"*{len(blocks)} specifications*")
            lines.append("")

            for block in blocks:
                pinned = "📌 " if block.pinned else ""
                lines.append(f"- {pinned}[{block.type.value}] {block.text[:80]}...")

            lines.append("")

        output_path = self.output_dir / "sources.md"
        output_path.write_text("\n".join(lines))

    def _group_by_type(self, blocks: list[SpecBlock]) -> dict[str, list[SpecBlock]]:
        """Group blocks by type."""
        by_type: dict[str, list[SpecBlock]] = defaultdict(list)
        for block in blocks:
            by_type[block.type.value].append(block)
        return dict(by_type)

    def _group_by_source(self, blocks: list[SpecBlock]) -> dict[str, list[SpecBlock]]:
        """Group blocks by source file."""
        by_source: dict[str, list[SpecBlock]] = defaultdict(list)
        for block in blocks:
            by_source[block.source].append(block)
        return dict(by_source)
