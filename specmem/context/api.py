"""Streaming Context API for real-time agent queries.

Provides both synchronous and async streaming interfaces for
querying specification memory with token budget optimization.
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from specmem.context.estimator import FormatType, TokenEstimator
from specmem.context.formatter import ContextFormatter
from specmem.context.optimizer import ContextChunk, ContextOptimizer
from specmem.context.profiles import ProfileManager


if TYPE_CHECKING:
    from specmem.core.memory_bank import MemoryBank

logger = logging.getLogger(__name__)


@dataclass
class ContextResponse:
    """Response from context query."""

    chunks: list[ContextChunk] = field(default_factory=list)
    total_tokens: int = 0
    token_budget: int = 4000
    truncated_count: int = 0
    query: str = ""
    format: str = "json"
    formatted_content: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "total_tokens": self.total_tokens,
            "token_budget": self.token_budget,
            "truncated_count": self.truncated_count,
            "query": self.query,
            "format": self.format,
        }


@dataclass
class StreamCompletion:
    """Completion signal for streaming."""

    total_chunks: int
    total_tokens: int
    token_budget: int
    truncated_count: int
    elapsed_ms: float
    timed_out: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "type": "complete",
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "token_budget": self.token_budget,
            "truncated_count": self.truncated_count,
            "elapsed_ms": self.elapsed_ms,
        }
        if self.timed_out:
            result["timed_out"] = True
        return result


class StreamingContextAPI:
    """API for streaming context to AI agents.

    Provides both synchronous and async interfaces for querying
    specification memory with automatic token budget optimization.
    """

    DEFAULT_BUDGET = 4000
    DEFAULT_TOP_K = 20

    def __init__(
        self,
        memory_bank: "MemoryBank",
        token_estimator: TokenEstimator | None = None,
        profile_manager: ProfileManager | None = None,
        default_budget: int = DEFAULT_BUDGET,
    ) -> None:
        """Initialize the streaming API.

        Args:
            memory_bank: Memory bank for querying specs
            token_estimator: Token estimator (creates default if None)
            profile_manager: Profile manager (creates default if None)
            default_budget: Default token budget
        """
        self.memory_bank = memory_bank
        self.token_estimator = token_estimator or TokenEstimator()
        self.profile_manager = profile_manager or ProfileManager()
        self.default_budget = default_budget

        self.optimizer = ContextOptimizer(self.token_estimator, default_budget)
        self.formatter = ContextFormatter()

    def get_context(
        self,
        query: str,
        token_budget: int | None = None,
        format: FormatType = "json",
        type_filters: list[str] | None = None,
        profile: str | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> ContextResponse:
        """Get context synchronously (non-streaming).

        Args:
            query: Natural language query
            token_budget: Maximum tokens (uses profile/default if None)
            format: Output format (json, markdown, text)
            type_filters: Filter by spec types
            profile: Agent profile name
            top_k: Maximum results to consider

        Returns:
            ContextResponse with optimized chunks
        """
        # Apply profile settings
        if profile:
            agent_profile = self.profile_manager.get(profile)
            if token_budget is None:
                token_budget = agent_profile.token_budget
            if format == "json" and agent_profile.preferred_format != "json":
                format = agent_profile.preferred_format  # type: ignore
            if not type_filters and agent_profile.type_filters:
                type_filters = agent_profile.type_filters

        budget = token_budget or self.default_budget

        # Query memory bank
        results = self.memory_bank.query(
            query_text=query,
            top_k=top_k,
            include_legacy=False,
            include_pinned=True,
        )

        # Filter by type if specified
        if type_filters:
            valid_types = {t.lower() for t in type_filters}
            results = [r for r in results if r.block.type.value.lower() in valid_types]

        # Extract blocks and scores
        blocks = [r.block for r in results]
        scores = [r.score for r in results]

        # Optimize to fit budget
        chunks = self.optimizer.optimize(blocks, scores, budget, format)

        # Calculate stats
        total_tokens = sum(c.tokens for c in chunks)
        truncated_count = sum(1 for c in chunks if c.truncated)

        # Format content
        formatted = self.formatter.format(chunks, format)

        return ContextResponse(
            chunks=chunks,
            total_tokens=total_tokens,
            token_budget=budget,
            truncated_count=truncated_count,
            query=query,
            format=format,
            formatted_content=formatted,
        )

    async def stream_query(
        self,
        query: str,
        token_budget: int | None = None,
        format: FormatType = "json",
        type_filters: list[str] | None = None,
        profile: str | None = None,
        top_k: int = DEFAULT_TOP_K,
        timeout_ms: int | None = None,
    ) -> AsyncGenerator[ContextChunk | StreamCompletion, None]:
        """Stream relevant context chunks for a query.

        Yields chunks one at a time, ordered by priority:
        1. Pinned blocks first
        2. Then by relevance score descending

        Args:
            query: Natural language query
            token_budget: Maximum tokens
            format: Output format
            type_filters: Filter by spec types
            profile: Agent profile name
            top_k: Maximum results
            timeout_ms: Optional timeout in milliseconds

        Yields:
            ContextChunk objects, then StreamCompletion at end
        """
        start_time = time.time()
        timed_out = False

        try:
            # Get context with optional timeout
            if timeout_ms:
                timeout_sec = timeout_ms / 1000
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.get_context,
                        query=query,
                        token_budget=token_budget,
                        format=format,
                        type_filters=type_filters,
                        profile=profile,
                        top_k=top_k,
                    ),
                    timeout=timeout_sec,
                )
            else:
                response = self.get_context(
                    query=query,
                    token_budget=token_budget,
                    format=format,
                    type_filters=type_filters,
                    profile=profile,
                    top_k=top_k,
                )
        except TimeoutError:
            timed_out = True
            # Return empty response on timeout
            response = ContextResponse(
                query=query,
                format=format,
                token_budget=token_budget or self.default_budget,
            )
            logger.warning(f"Context query timed out after {timeout_ms}ms")

        # Stream chunks
        for chunk in response.chunks:
            yield chunk
            # Allow other tasks to run
            await asyncio.sleep(0)

        # Send completion signal
        elapsed_ms = (time.time() - start_time) * 1000
        completion = StreamCompletion(
            total_chunks=len(response.chunks),
            total_tokens=response.total_tokens,
            token_budget=response.token_budget,
            truncated_count=response.truncated_count,
            elapsed_ms=elapsed_ms,
        )

        # Add timeout indicator if applicable
        if timed_out:
            completion.timed_out = True  # type: ignore

        yield completion

    def filter_by_types(
        self,
        chunks: list[ContextChunk],
        type_filters: list[str],
    ) -> list[ContextChunk]:
        """Filter chunks by specification types.

        Args:
            chunks: Chunks to filter
            type_filters: Types to include (OR logic)

        Returns:
            Filtered chunks
        """
        if not type_filters:
            return chunks

        valid_types = {t.lower() for t in type_filters}
        return [c for c in chunks if c.block_type.lower() in valid_types]
