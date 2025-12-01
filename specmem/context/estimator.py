"""Token estimation for context window optimization.

Provides accurate token counting using tiktoken when available,
with fallback to character-based estimation.
"""

import logging
from typing import Literal


logger = logging.getLogger(__name__)

# Try to import tiktoken, fall back to estimation if not available
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.debug("tiktoken not available, using character-based estimation")


FormatType = Literal["json", "markdown", "text"]


class TokenEstimator:
    """Estimates token counts for text content.

    Uses tiktoken for accurate counting when available, with fallback
    to character-based estimation (4 chars per token average).
    """

    DEFAULT_CHARS_PER_TOKEN = 4  # Conservative estimate for fallback

    # Format overhead estimates (tokens per block)
    FORMAT_OVERHEAD = {
        "json": 25,  # {"id": "...", "type": "...", ...}
        "markdown": 10,  # ## Header\n- bullet
        "text": 5,  # --- separator
    }

    def __init__(self, tokenizer: str = "cl100k_base") -> None:
        """Initialize the token estimator.

        Args:
            tokenizer: Name of tiktoken encoding to use.
                       Common options: cl100k_base (GPT-4), p50k_base (GPT-3)
        """
        self._tokenizer_name = tokenizer
        self._encoding = None

        if TIKTOKEN_AVAILABLE:
            try:
                self._encoding = tiktoken.get_encoding(tokenizer)
                logger.debug(f"Using tiktoken encoding: {tokenizer}")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoding '{tokenizer}': {e}")

    @property
    def is_tiktoken_available(self) -> bool:
        """Check if tiktoken is available and loaded."""
        return self._encoding is not None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens in the text
        """
        if not text:
            return 0

        if self._encoding is not None:
            return len(self._encoding.encode(text))

        # Fallback: estimate based on character count
        return max(1, len(text) // self.DEFAULT_CHARS_PER_TOKEN)

    def count_with_format(self, text: str, format: FormatType) -> int:
        """Count tokens including format overhead.

        Args:
            text: Text content
            format: Output format (json, markdown, text)

        Returns:
            Token count including formatting overhead
        """
        base_tokens = self.count_tokens(text)
        overhead = self.FORMAT_OVERHEAD.get(format, 0)
        return base_tokens + overhead

    def estimate_overhead(self, format: FormatType, num_blocks: int) -> int:
        """Estimate total formatting overhead for multiple blocks.

        Args:
            format: Output format
            num_blocks: Number of blocks to format

        Returns:
            Estimated overhead tokens
        """
        per_block = self.FORMAT_OVERHEAD.get(format, 0)

        # Add container overhead for JSON (array brackets, commas)
        if format == "json":
            container_overhead = 2 + (num_blocks - 1) if num_blocks > 0 else 0
            return (per_block * num_blocks) + container_overhead

        # Add header overhead for Markdown (type headers)
        if format == "markdown":
            # Assume ~5 type headers
            header_overhead = 15
            return (per_block * num_blocks) + header_overhead

        return per_block * num_blocks

    def estimate_total(
        self,
        texts: list[str],
        format: FormatType = "json",
    ) -> int:
        """Estimate total tokens for a list of texts with formatting.

        Args:
            texts: List of text contents
            format: Output format

        Returns:
            Total estimated tokens
        """
        content_tokens = sum(self.count_tokens(t) for t in texts)
        overhead = self.estimate_overhead(format, len(texts))
        return content_tokens + overhead

    def fits_budget(
        self,
        texts: list[str],
        budget: int,
        format: FormatType = "json",
    ) -> bool:
        """Check if texts fit within token budget.

        Args:
            texts: List of text contents
            budget: Token budget
            format: Output format

        Returns:
            True if total tokens <= budget
        """
        return self.estimate_total(texts, format) <= budget

    def set_tokenizer(self, tokenizer: str) -> bool:
        """Change the tokenizer.

        Args:
            tokenizer: Name of tiktoken encoding

        Returns:
            True if tokenizer was successfully loaded
        """
        if not TIKTOKEN_AVAILABLE:
            logger.warning("tiktoken not available, cannot change tokenizer")
            return False

        try:
            self._encoding = tiktoken.get_encoding(tokenizer)
            self._tokenizer_name = tokenizer
            logger.debug(f"Switched to tiktoken encoding: {tokenizer}")
            return True
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding '{tokenizer}': {e}")
            return False
