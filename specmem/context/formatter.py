"""Context formatting for different output types.

Supports JSON, Markdown, and plain text output formats.
"""

import json
from collections import defaultdict
from typing import Literal

from specmem.context.optimizer import ContextChunk


FormatType = Literal["json", "markdown", "text"]


class ContextFormatter:
    """Formats context chunks for agent consumption.

    Supports three output formats:
    - json: Structured JSON with full metadata
    - markdown: Human-readable with headers and bullets
    - text: Plain text with separators
    """

    TEXT_SEPARATOR = "\n---\n"

    def format(self, chunks: list[ContextChunk], format: FormatType = "json") -> str:
        """Format chunks in specified format.

        Args:
            chunks: List of context chunks
            format: Output format (json, markdown, text)

        Returns:
            Formatted string
        """
        if format == "json":
            return self.format_json(chunks)
        elif format == "markdown":
            return self.format_markdown(chunks)
        elif format == "text":
            return self.format_text(chunks)
        else:
            # Default to JSON for unknown formats
            return self.format_json(chunks)

    def format_json(self, chunks: list[ContextChunk]) -> str:
        """Format as JSON with metadata.

        Includes id, type, source, relevance_score for each chunk.

        Args:
            chunks: List of context chunks

        Returns:
            JSON string
        """
        data = [chunk.to_dict() for chunk in chunks]
        return json.dumps(data, indent=2)

    def format_markdown(self, chunks: list[ContextChunk]) -> str:
        """Format as structured Markdown.

        Groups chunks by type with headers and bullet points.

        Args:
            chunks: List of context chunks

        Returns:
            Markdown string
        """
        if not chunks:
            return "# Context\n\nNo relevant specifications found."

        lines = ["# Specification Context", ""]

        # Group by type
        by_type: dict[str, list[ContextChunk]] = defaultdict(list)
        for chunk in chunks:
            by_type[chunk.block_type].append(chunk)

        # Type display order
        type_order = ["requirement", "design", "task", "decision", "knowledge"]
        sorted_types = sorted(
            by_type.keys(), key=lambda t: type_order.index(t) if t in type_order else 999
        )

        for block_type in sorted_types:
            type_chunks = by_type[block_type]

            # Type header
            lines.append(f"## {block_type.title()}s")
            lines.append("")

            for chunk in type_chunks:
                # Pinned indicator
                pinned = "📌 " if chunk.pinned else ""
                truncated = " *(truncated)*" if chunk.truncated else ""

                # Source as subheading
                lines.append(f"### {pinned}{chunk.source}{truncated}")
                lines.append("")

                # Content as bullet points or paragraphs
                text_lines = chunk.text.strip().split("\n")
                for line in text_lines:
                    if line.strip():
                        # Preserve existing bullets, add bullets to plain lines
                        if line.strip().startswith(("-", "*", "•", "1.", "2.")):
                            lines.append(line)
                        else:
                            lines.append(f"- {line.strip()}")

                lines.append("")

                # Relevance score
                lines.append(f"*Relevance: {chunk.relevance:.2f}*")
                lines.append("")

        return "\n".join(lines)

    def format_text(self, chunks: list[ContextChunk]) -> str:
        """Format as plain text with separators.

        Args:
            chunks: List of context chunks

        Returns:
            Plain text string
        """
        if not chunks:
            return "No relevant specifications found."

        sections = []

        for chunk in chunks:
            pinned = "[PINNED] " if chunk.pinned else ""
            truncated = " [TRUNCATED]" if chunk.truncated else ""

            section = f"""{pinned}[{chunk.block_type.upper()}]{truncated}
Source: {chunk.source}
Relevance: {chunk.relevance:.2f}

{chunk.text}"""
            sections.append(section)

        return self.TEXT_SEPARATOR.join(sections)
