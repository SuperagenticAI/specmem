"""Context optimization for token budget compliance.

Handles fitting SpecBlocks within token budgets while preserving
relevance ordering and sentence boundaries.
"""

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from specmem.context.estimator import FormatType, TokenEstimator


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock

logger = logging.getLogger(__name__)


@dataclass
class ContextChunk:
    """A chunk of context optimized for agent consumption."""

    block_id: str
    block_type: str
    source: str
    text: str
    tokens: int
    relevance: float
    pinned: bool
    truncated: bool = False
    original_tokens: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.block_id,
            "type": self.block_type,
            "source": self.source,
            "text": self.text,
            "tokens": self.tokens,
            "relevance_score": self.relevance,
            "pinned": self.pinned,
            "truncated": self.truncated,
        }

    @classmethod
    def from_block(
        cls,
        block: "SpecBlock",
        relevance: float,
        token_estimator: TokenEstimator,
    ) -> "ContextChunk":
        """Create a ContextChunk from a SpecBlock.

        Args:
            block: Source SpecBlock
            relevance: Relevance score (0.0 to 1.0)
            token_estimator: Token estimator for counting

        Returns:
            New ContextChunk instance
        """
        tokens = token_estimator.count_tokens(block.text)
        return cls(
            block_id=block.id,
            block_type=block.type.value,
            source=block.source,
            text=block.text,
            tokens=tokens,
            relevance=relevance,
            pinned=block.pinned,
            truncated=False,
            original_tokens=tokens,
        )


class ContextOptimizer:
    """Optimizes context to fit within token budgets.

    Prioritizes content by:
    1. Pinned blocks (always included if budget allows)
    2. Higher relevance scores
    3. Complete content over truncated
    """

    # Sentence ending patterns
    SENTENCE_END_PATTERN = re.compile(r"[.!?](?:\s|$)")

    def __init__(
        self,
        token_estimator: TokenEstimator | None = None,
        default_budget: int = 4000,
    ) -> None:
        """Initialize the context optimizer.

        Args:
            token_estimator: Token estimator (creates default if None)
            default_budget: Default token budget
        """
        self.token_estimator = token_estimator or TokenEstimator()
        self.default_budget = default_budget

    def optimize(
        self,
        blocks: list["SpecBlock"],
        scores: list[float],
        token_budget: int | None = None,
        format: FormatType = "json",
    ) -> list[ContextChunk]:
        """Optimize blocks to fit within token budget.

        Args:
            blocks: List of SpecBlocks to optimize
            scores: Relevance scores for each block (same order)
            token_budget: Maximum tokens (uses default if None)
            format: Output format for overhead calculation

        Returns:
            List of ContextChunks fitting within budget
        """
        if not blocks:
            return []

        budget = token_budget or self.default_budget

        # Create chunks with relevance scores
        chunks = [
            ContextChunk.from_block(block, score, self.token_estimator)
            for block, score in zip(blocks, scores, strict=False)
        ]

        # Sort: pinned first, then by relevance descending
        chunks.sort(key=lambda c: (not c.pinned, -c.relevance))

        # Calculate format overhead
        overhead = self.token_estimator.estimate_overhead(format, len(chunks))
        available_budget = budget - overhead

        if available_budget <= 0:
            logger.warning(f"Token budget {budget} too small for format overhead {overhead}")
            return []

        # Fit chunks within budget
        return self._fit_to_budget(chunks, available_budget)

    def _fit_to_budget(
        self,
        chunks: list[ContextChunk],
        budget: int,
    ) -> list[ContextChunk]:
        """Fit chunks within budget, truncating if necessary.

        Args:
            chunks: Sorted chunks (pinned first, then by relevance)
            budget: Available token budget

        Returns:
            Chunks fitting within budget
        """
        result: list[ContextChunk] = []
        remaining_budget = budget

        for chunk in chunks:
            if chunk.tokens <= remaining_budget:
                # Fits completely
                result.append(chunk)
                remaining_budget -= chunk.tokens
            elif remaining_budget > 50:  # Minimum useful chunk size
                # Try to truncate
                truncated = self._truncate_chunk(chunk, remaining_budget)
                if truncated and truncated.tokens > 0:
                    result.append(truncated)
                    remaining_budget -= truncated.tokens
            # else: skip this chunk

        return result

    def _truncate_chunk(
        self,
        chunk: ContextChunk,
        max_tokens: int,
    ) -> ContextChunk | None:
        """Truncate a chunk to fit within token limit.

        Preserves sentence boundaries when possible.

        Args:
            chunk: Chunk to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated chunk or None if too small
        """
        if max_tokens < 20:  # Too small to be useful
            return None

        text = chunk.text

        # Binary search for the right length
        # Start with estimated character count
        estimated_chars = max_tokens * 4  # Conservative estimate

        if estimated_chars >= len(text):
            return chunk  # No truncation needed

        # Find sentence boundary before estimated position
        truncated_text = self._truncate_at_sentence(text, estimated_chars)

        # Verify token count and adjust if needed
        actual_tokens = self.token_estimator.count_tokens(truncated_text)

        # If still too long, reduce further
        while actual_tokens > max_tokens and len(truncated_text) > 50:
            estimated_chars = int(estimated_chars * 0.8)
            truncated_text = self._truncate_at_sentence(text, estimated_chars)
            actual_tokens = self.token_estimator.count_tokens(truncated_text)

        if actual_tokens == 0 or len(truncated_text) < 20:
            return None

        return ContextChunk(
            block_id=chunk.block_id,
            block_type=chunk.block_type,
            source=chunk.source,
            text=truncated_text,
            tokens=actual_tokens,
            relevance=chunk.relevance,
            pinned=chunk.pinned,
            truncated=True,
            original_tokens=chunk.original_tokens,
        )

    def _truncate_at_sentence(self, text: str, max_chars: int) -> str:
        """Truncate text at a sentence boundary.

        Args:
            text: Text to truncate
            max_chars: Maximum characters

        Returns:
            Truncated text ending at sentence boundary
        """
        if len(text) <= max_chars:
            return text

        # Look for sentence endings before max_chars
        search_text = text[:max_chars]

        # Find all sentence endings
        matches = list(self.SENTENCE_END_PATTERN.finditer(search_text))

        if matches:
            # Use the last sentence ending
            last_match = matches[-1]
            return text[: last_match.end()].strip()

        # No sentence boundary found, try to break at word boundary
        last_space = search_text.rfind(" ")
        if last_space > max_chars // 2:
            return text[:last_space].strip() + "..."

        # Fall back to hard truncation
        return text[:max_chars].strip() + "..."

    def truncate_to_budget(
        self,
        chunks: list[ContextChunk],
        budget: int,
    ) -> list[ContextChunk]:
        """Truncate chunks to fit budget, preserving sentence boundaries.

        Lower-relevance chunks are truncated first.

        Args:
            chunks: Chunks to truncate (already sorted by priority)
            budget: Token budget

        Returns:
            Truncated chunks fitting within budget
        """
        return self._fit_to_budget(chunks, budget)

    def estimate_total_tokens(self, chunks: list[ContextChunk]) -> int:
        """Calculate total tokens for a list of chunks.

        Args:
            chunks: List of chunks

        Returns:
            Total token count
        """
        return sum(c.tokens for c in chunks)
