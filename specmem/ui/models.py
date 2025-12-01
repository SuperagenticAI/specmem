"""API response models for SpecMem Web UI."""

from pydantic import BaseModel, Field

from specmem.core.specir import SpecBlock


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text to max_length characters with ellipsis.

    Args:
        text: The text to truncate
        max_length: Maximum length before truncation (default 200)

    Returns:
        Truncated text with ellipsis if longer than max_length,
        otherwise the original text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


class BlockSummary(BaseModel):
    """Summary view of a SpecBlock for list display."""

    id: str
    type: str
    text_preview: str = Field(description="Truncated to 200 chars")
    source: str
    status: str
    pinned: bool

    @classmethod
    def from_spec_block(cls, block: SpecBlock) -> "BlockSummary":
        """Create a BlockSummary from a SpecBlock."""
        return cls(
            id=block.id,
            type=block.type.value,
            text_preview=truncate_text(block.text),
            source=block.source,
            status=block.status.value,
            pinned=block.pinned,
        )


class BlockDetail(BaseModel):
    """Full detail view of a SpecBlock."""

    id: str
    type: str
    text: str
    source: str
    status: str
    pinned: bool
    tags: list[str]
    links: list[str]

    @classmethod
    def from_spec_block(cls, block: SpecBlock) -> "BlockDetail":
        """Create a BlockDetail from a SpecBlock."""
        return cls(
            id=block.id,
            type=block.type.value,
            text=block.text,
            source=block.source,
            status=block.status.value,
            pinned=block.pinned,
            tags=block.tags,
            links=block.links,
        )


class BlockListResponse(BaseModel):
    """Response for listing blocks."""

    blocks: list[BlockSummary]
    total: int
    active_count: int
    legacy_count: int
    pinned_count: int


class StatsResponse(BaseModel):
    """Response for memory statistics."""

    total_blocks: int
    active_count: int
    legacy_count: int
    pinned_count: int
    by_type: dict[str, int]
    by_source: dict[str, int]
    memory_size_bytes: int


class SearchResult(BaseModel):
    """A single search result with relevance score."""

    block: BlockSummary
    score: float = Field(ge=0.0, description="Relevance score (higher is better)")


class SearchResponse(BaseModel):
    """Response for semantic search."""

    results: list[SearchResult]
    query: str


class ExportResponse(BaseModel):
    """Response for export operation."""

    success: bool
    output_path: str
    message: str


class PinnedBlockResponse(BaseModel):
    """Response for pinned blocks with reason."""

    block: BlockSummary
    reason: str = Field(default="Contains critical specification keyword")


class PinnedListResponse(BaseModel):
    """Response for listing pinned blocks."""

    blocks: list[PinnedBlockResponse]
    total: int


class WebSocketMessage(BaseModel):
    """WebSocket message for live updates."""

    type: str = Field(description="Message type: 'refresh', 'error', 'connected'")
    data: dict | None = None
    message: str | None = None
