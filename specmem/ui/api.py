"""REST API endpoints for SpecMem Web UI."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from specmem.core.specir import SpecBlock
from specmem.ui.filters import (
    calculate_counts,
    count_by_source,
    count_by_type,
    filter_blocks,
    get_pinned_blocks,
)
from specmem.ui.models import (
    BlockDetail,
    BlockListResponse,
    BlockSummary,
    ExportResponse,
    PinnedBlockResponse,
    PinnedListResponse,
    SearchResponse,
    SearchResult,
    StatsResponse,
)


router = APIRouter(prefix="/api", tags=["api"])

# These will be set by the server when it starts
_blocks: list[SpecBlock] = []
_vector_store = None
_pack_builder = None
_workspace_path: Path = Path()


def set_context(
    blocks: list[SpecBlock],
    vector_store=None,
    pack_builder=None,
    workspace_path: Path = Path(),
):
    """Set the context for API endpoints."""
    global _blocks, _vector_store, _pack_builder, _workspace_path
    _blocks = blocks
    _vector_store = vector_store
    _pack_builder = pack_builder
    _workspace_path = workspace_path


def get_blocks() -> list[SpecBlock]:
    """Get current blocks."""
    return _blocks


@router.get("/blocks", response_model=BlockListResponse)
async def list_blocks(
    status: str | None = Query(None, description="Filter by status: active, legacy, or all"),
    type: str | None = Query(None, description="Filter by type: requirement, design, task, etc."),
) -> BlockListResponse:
    """List all blocks with optional filters."""
    filtered = filter_blocks(_blocks, status=status, block_type=type)
    total, active_count, legacy_count, pinned_count = calculate_counts(filtered)

    return BlockListResponse(
        blocks=[BlockSummary.from_spec_block(b) for b in filtered],
        total=total,
        active_count=active_count,
        legacy_count=legacy_count,
        pinned_count=pinned_count,
    )


@router.get("/blocks/{block_id}", response_model=BlockDetail)
async def get_block(block_id: str) -> BlockDetail:
    """Get a single block by ID."""
    for block in _blocks:
        if block.id == block_id:
            return BlockDetail.from_spec_block(block)
    raise HTTPException(status_code=404, detail=f"Block not found: {block_id}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Get memory statistics."""
    total, active_count, legacy_count, pinned_count = calculate_counts(_blocks)
    by_type = count_by_type(_blocks)
    by_source = count_by_source(_blocks)

    # Estimate memory size (rough approximation)
    memory_size = sum(len(b.text.encode("utf-8")) for b in _blocks)

    return StatsResponse(
        total_blocks=total,
        active_count=active_count,
        legacy_count=legacy_count,
        pinned_count=pinned_count,
        by_type=by_type,
        by_source=by_source,
        memory_size_bytes=memory_size,
    )


@router.get("/search", response_model=SearchResponse)
async def search_blocks(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results"),
) -> SearchResponse:
    """Semantic search for blocks."""
    if not _vector_store:
        # Fallback to simple text search if no vector store
        results = []
        query_lower = q.lower()
        for block in _blocks:
            if query_lower in block.text.lower():
                # Simple relevance: position-based score
                pos = block.text.lower().find(query_lower)
                score = 1.0 - (pos / len(block.text)) if pos >= 0 else 0.0
                results.append(
                    SearchResult(
                        block=BlockSummary.from_spec_block(block),
                        score=score,
                    )
                )
        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return SearchResponse(results=results[:limit], query=q)

    # Use vector store for semantic search
    try:
        query_results = _vector_store.query(q, top_k=limit)
        results = []
        for block, score in query_results:
            results.append(
                SearchResult(
                    block=BlockSummary.from_spec_block(block),
                    score=score,
                )
            )
        # Results should already be sorted by score from vector store
        return SearchResponse(results=results, query=q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {e!s}")


@router.get("/pinned", response_model=PinnedListResponse)
async def get_pinned() -> PinnedListResponse:
    """Get all pinned blocks."""
    pinned = get_pinned_blocks(_blocks)

    responses = []
    for block in pinned:
        reason = "Contains critical specification keyword (SHALL)"
        if "requirement" in block.type.value.lower():
            reason = "Core requirement specification"
        elif "design" in block.type.value.lower():
            reason = "Architecture decision"

        responses.append(
            PinnedBlockResponse(
                block=BlockSummary.from_spec_block(block),
                reason=reason,
            )
        )

    return PinnedListResponse(blocks=responses, total=len(responses))


@router.post("/export", response_model=ExportResponse)
async def export_pack() -> ExportResponse:
    """Export Agent Experience Pack."""
    if not _pack_builder:
        return ExportResponse(
            success=False,
            output_path="",
            message="Pack builder not initialized. Run 'specmem build' first.",
        )

    try:
        output_path = _workspace_path / ".specmem"
        _pack_builder.build(_blocks, output_path)
        return ExportResponse(
            success=True,
            output_path=str(output_path),
            message=f"Agent Experience Pack exported to {output_path}",
        )
    except Exception as e:
        return ExportResponse(
            success=False,
            output_path="",
            message=f"Export failed: {e!s}",
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "blocks_loaded": len(_blocks)}
