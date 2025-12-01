"""Memory Bank for SpecMem.

Handles chunking, ranking, scoring, and lifecycle management of SpecBlocks.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from specmem.core.specir import SpecBlock, SpecStatus
from specmem.vectordb.base import QueryResult, VectorStore


if TYPE_CHECKING:
    from specmem.core.config import SpecMemConfig
    from specmem.vectordb.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class MemoryStatistics:
    """Statistics about the memory bank contents."""

    total_blocks: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_status: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    pinned_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_blocks": self.total_blocks,
            "by_type": self.by_type,
            "by_status": self.by_status,
            "by_source": self.by_source,
            "pinned_count": self.pinned_count,
        }


class MemoryBank:
    """Central memory management for SpecMem.

    Coordinates between adapters, embeddings, and vector storage to provide
    a unified interface for storing and querying specifications.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        chunk_size: int = 1000,
    ) -> None:
        """Initialize the memory bank.

        Args:
            vector_store: Vector storage backend
            embedding_provider: Embedding generation provider
            chunk_size: Maximum characters per chunk for large documents
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.chunk_size = chunk_size
        self._blocks: list[SpecBlock] = []

    @classmethod
    def from_config(
        cls,
        config: SpecMemConfig,
        chunk_size: int = 1000,
    ) -> MemoryBank:
        """Create a MemoryBank from configuration.

        Args:
            config: SpecMem configuration
            chunk_size: Maximum characters per chunk

        Returns:
            Configured MemoryBank instance
        """
        from specmem.vectordb import LanceDBStore, get_embedding_provider

        # Create vector store based on config
        vector_store = LanceDBStore(db_path=config.vectordb.path)

        # Create embedding provider with API key from config or env
        embedding_provider = get_embedding_provider(
            provider=config.embedding.provider,
            model=config.embedding.model,
            api_key=config.embedding.get_api_key(),
        )

        return cls(
            vector_store=vector_store,
            embedding_provider=embedding_provider,
            chunk_size=chunk_size,
        )

    def initialize(self) -> None:
        """Initialize the memory bank and underlying storage."""
        self.vector_store.initialize()

    def add_blocks(self, blocks: list[SpecBlock]) -> int:
        """Add SpecBlocks to memory.

        Args:
            blocks: List of SpecBlocks to add

        Returns:
            Number of blocks added
        """
        if not blocks:
            return 0

        # Chunk large blocks if needed
        chunked_blocks = []
        for block in blocks:
            if len(block.text) > self.chunk_size:
                chunked_blocks.extend(self._chunk_block(block))
            else:
                chunked_blocks.append(block)

        # Generate embeddings
        texts = [block.text for block in chunked_blocks]
        embeddings = self.embedding_provider.embed(texts)

        # Store in vector database
        self.vector_store.store(chunked_blocks, embeddings)

        # Track locally
        self._blocks.extend(chunked_blocks)

        logger.info(f"Added {len(chunked_blocks)} blocks to memory")
        return len(chunked_blocks)

    def _chunk_block(self, block: SpecBlock) -> list[SpecBlock]:
        """Split a large block into smaller chunks.

        Args:
            block: SpecBlock to chunk

        Returns:
            List of chunked SpecBlocks
        """
        text = block.text
        chunks = []

        # Simple chunking by character count with overlap
        overlap = 100
        start = 0
        chunk_num = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Try to break at sentence boundary
            if end < len(text):
                for sep in [". ", ".\n", "\n\n", "\n"]:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start + self.chunk_size // 2:
                        end = last_sep + len(sep)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = f"{block.id}_chunk_{chunk_num}"
                chunks.append(
                    SpecBlock(
                        id=chunk_id,
                        type=block.type,
                        text=chunk_text,
                        source=block.source,
                        status=block.status,
                        tags=[*block.tags, f"chunk_{chunk_num}"],
                        links=[block.id],  # Link to parent
                        pinned=block.pinned,
                    )
                )
                chunk_num += 1

            start = end - overlap if end < len(text) else end

        return chunks if chunks else [block]

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        include_legacy: bool = False,
        include_pinned: bool = True,
    ) -> list[QueryResult]:
        """Query memory for relevant SpecBlocks.

        Args:
            query_text: Natural language query
            top_k: Maximum number of results
            include_legacy: Whether to include legacy blocks
            include_pinned: Whether to always include pinned blocks

        Returns:
            List of QueryResults ordered by relevance
        """
        # Generate query embedding
        query_embedding = self.embedding_provider.embed([query_text])[0]

        # Query vector store
        results = self.vector_store.query(
            query_embedding, top_k=top_k, include_legacy=include_legacy
        )

        # Add pinned blocks if requested
        if include_pinned:
            pinned = self.vector_store.get_pinned()
            pinned_ids = {r.block.id for r in results}

            for block in pinned:
                if block.id not in pinned_ids:
                    # Add pinned blocks with high score
                    results.append(QueryResult(block=block, score=1.0, distance=0.0))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:top_k]

    def get_statistics(self) -> MemoryStatistics:
        """Calculate memory statistics.

        Returns:
            MemoryStatistics with counts by type, status, source
        """
        stats = MemoryStatistics()

        # Get all blocks from store
        # For now, use locally tracked blocks
        blocks = self._blocks

        stats.total_blocks = len(blocks)

        # Count by type
        type_counter = Counter(b.type.value for b in blocks)
        stats.by_type = dict(type_counter)

        # Count by status
        status_counter = Counter(b.status.value for b in blocks)
        stats.by_status = dict(status_counter)

        # Count by source
        source_counter = Counter(b.source for b in blocks)
        stats.by_source = dict(source_counter)

        # Count pinned
        stats.pinned_count = sum(1 for b in blocks if b.pinned)

        return stats

    def update_status(self, block_id: str, status: SpecStatus) -> bool:
        """Update the status of a block.

        Args:
            block_id: ID of block to update
            status: New status

        Returns:
            True if update succeeded
        """
        success = self.vector_store.update_status(block_id, status.value)

        # Update local tracking
        if success:
            for block in self._blocks:
                if block.id == block_id:
                    block.status = status
                    break

        return success

    def clear(self) -> None:
        """Clear all memory."""
        self.vector_store.clear()
        self._blocks.clear()
        logger.info("Memory bank cleared")
