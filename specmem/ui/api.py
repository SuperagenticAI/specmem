"""REST API endpoints for SpecMem Web UI."""

import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

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


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])

# These will be set by the server when it starts
_blocks: list[SpecBlock] = []
_vector_store = None
_pack_builder = None
_workspace_path: Path = Path()

# Simple in-memory cache with TTL
_cache: dict[str, tuple[float, Any]] = {}
_cache_ttl: float = 300.0  # 5 minutes default TTL


def _get_cached(key: str) -> Any | None:
    """Get cached value if not expired."""
    if key in _cache:
        timestamp, value = _cache[key]
        if time.time() - timestamp < _cache_ttl:
            return value
        del _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    """Set cached value with current timestamp."""
    _cache[key] = (time.time(), value)


def clear_cache() -> None:
    """Clear all cached data."""
    global _cache
    _cache = {}


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
        from specmem.vectordb.embeddings import LocalEmbeddingProvider

        # Generate embedding for query text
        embedding_provider = LocalEmbeddingProvider()
        query_embedding = embedding_provider.embed([q])[0]

        # Query with embedding vector
        query_results = _vector_store.query(query_embedding, top_k=limit)
        results = []
        for result in query_results:
            results.append(
                SearchResult(
                    block=BlockSummary.from_spec_block(result.block),
                    score=result.score,
                )
            )
        # Results should already be sorted by score from vector store
        return SearchResponse(results=results, query=q)
    except Exception as e:
        logger.error(f"Search error: {e}")
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


@router.get("/healthz")
async def health_check():
    """Health check endpoint for liveness probes."""
    return {"status": "ok", "blocks_loaded": len(_blocks)}


@router.post("/cache/clear")
async def clear_api_cache():
    """Clear all cached data to force fresh computation."""
    clear_cache()
    return {"status": "ok", "message": "Cache cleared"}


# =============================================================================
# Spec File Content API Endpoint
# =============================================================================


class SpecFileResponse(BaseModel):
    """Response model for spec file content."""

    feature_name: str
    file_type: str
    file_path: str
    content: str
    exists: bool


@router.get("/specs/{feature_name}/{file_type}", response_model=SpecFileResponse)
async def get_spec_file(feature_name: str, file_type: str) -> SpecFileResponse:
    """Get the full content of a spec file.

    Args:
        feature_name: Name of the feature folder (e.g., 'streaming-context-api')
        file_type: Type of spec file ('requirements', 'design', or 'tasks')

    Returns:
        Full content of the spec file
    """
    if file_type not in ("requirements", "design", "tasks"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file_type: {file_type}. Must be 'requirements', 'design', or 'tasks'",
        )

    file_path = _workspace_path / ".kiro" / "specs" / feature_name / f"{file_type}.md"

    if not file_path.exists():
        return SpecFileResponse(
            feature_name=feature_name,
            file_type=file_type,
            file_path=str(file_path),
            content="",
            exists=False,
        )

    try:
        content = file_path.read_text()
        return SpecFileResponse(
            feature_name=feature_name,
            file_type=file_type,
            file_path=str(file_path),
            content=content,
            exists=True,
        )
    except Exception as e:
        logger.error(f"Failed to read spec file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e!s}")


# =============================================================================
# Coverage API Endpoints
# =============================================================================


class CriterionResponse(BaseModel):
    """Response model for a single criterion."""

    id: str
    number: str
    text: str
    feature_name: str
    is_covered: bool
    confidence: float
    test_name: str | None = None
    test_file: str | None = None


class FeatureCoverageResponse(BaseModel):
    """Response model for feature coverage."""

    feature_name: str
    total_count: int
    tested_count: int
    coverage_percentage: float
    criteria: list[CriterionResponse]


class CoverageResponse(BaseModel):
    """Response model for overall coverage."""

    total_criteria: int
    covered_criteria: int
    coverage_percentage: float
    features: list[FeatureCoverageResponse]
    badge_url: str


class TestSuggestionResponse(BaseModel):
    """Response model for test suggestions."""

    criterion_id: str
    criterion_text: str
    feature_name: str
    suggested_file: str
    suggested_name: str
    verification_points: list[str]


@router.get("/coverage", response_model=CoverageResponse)
async def get_coverage() -> CoverageResponse:
    """Get spec coverage analysis (cached for 5 minutes)."""
    # Check cache first
    cached = _get_cached("coverage")
    if cached is not None:
        return cached

    try:
        from specmem.coverage.engine import CoverageEngine

        engine = CoverageEngine(_workspace_path)
        result = engine.analyze_coverage()

        features = []
        for feature in result.features:
            criteria = []
            for match in feature.criteria:
                criteria.append(
                    CriterionResponse(
                        id=match.criterion.id,
                        number=match.criterion.number,
                        text=match.criterion.text,
                        feature_name=match.criterion.feature_name,
                        is_covered=match.is_covered,
                        confidence=match.confidence,
                        test_name=match.test.name if match.test else None,
                        test_file=match.test.file_path if match.test else None,
                    )
                )
            features.append(
                FeatureCoverageResponse(
                    feature_name=feature.feature_name,
                    total_count=feature.total_count,
                    tested_count=feature.tested_count,
                    coverage_percentage=feature.coverage_percentage,
                    criteria=criteria,
                )
            )

        # Generate badge URL
        percentage = int(result.coverage_percentage)
        color = "red" if percentage < 50 else "yellow" if percentage <= 80 else "green"
        badge_url = f"https://img.shields.io/badge/Spec_Coverage-{percentage}%25-{color}"

        response = CoverageResponse(
            total_criteria=result.total_criteria,
            covered_criteria=result.covered_criteria,
            coverage_percentage=result.coverage_percentage,
            features=features,
            badge_url=badge_url,
        )
        _set_cached("coverage", response)
        return response
    except Exception as e:
        logger.error(f"Coverage analysis failed: {e}")
        return CoverageResponse(
            total_criteria=0,
            covered_criteria=0,
            coverage_percentage=100.0,
            features=[],
            badge_url="https://img.shields.io/badge/Spec_Coverage-N%2FA-lightgrey",
        )


@router.get("/coverage/suggestions", response_model=list[TestSuggestionResponse])
async def get_coverage_suggestions(
    feature: str | None = Query(None, description="Filter by feature name"),
) -> list[TestSuggestionResponse]:
    """Get test suggestions for uncovered criteria."""
    try:
        from specmem.coverage.engine import CoverageEngine

        engine = CoverageEngine(_workspace_path)
        suggestions = engine.get_suggestions(feature_name=feature)

        return [
            TestSuggestionResponse(
                criterion_id=s.criterion.id,
                criterion_text=s.criterion.text,
                feature_name=s.criterion.feature_name,
                suggested_file=s.suggested_file,
                suggested_name=s.suggested_name,
                verification_points=s.verification_points,
            )
            for s in suggestions
        ]
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        return []


# =============================================================================
# Sessions API Endpoints
# =============================================================================


class SessionMessageResponse(BaseModel):
    """Response model for a session message."""

    role: str
    content: str
    timestamp_ms: int | None = None


class SessionResponse(BaseModel):
    """Response model for a session."""

    session_id: str
    title: str
    workspace_directory: str
    date_created_ms: int
    message_count: int
    messages: list[SessionMessageResponse] | None = None


class SessionSearchResultResponse(BaseModel):
    """Response model for session search result."""

    session: SessionResponse
    score: float
    matched_message_indices: list[int]


class SessionListResponse(BaseModel):
    """Response model for session list."""

    sessions: list[SessionResponse]
    total: int


class SessionSearchResponse(BaseModel):
    """Response model for session search."""

    results: list[SessionSearchResultResponse]
    query: str


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100, description="Maximum sessions to return"),
    workspace_only: bool = Query(False, description="Only show sessions for current workspace"),
) -> SessionListResponse:
    """List recent sessions."""
    try:
        from specmem.sessions.discovery import SessionDiscovery
        from specmem.sessions.indexer import SessionIndexer
        from specmem.sessions.storage import SessionStorage

        discovery = SessionDiscovery()
        sessions_path = discovery.find_sessions_path()

        if not sessions_path:
            return SessionListResponse(sessions=[], total=0)

        storage = SessionStorage(sessions_path)
        indexer = SessionIndexer(storage)
        indexer.index_sessions()

        workspace = str(_workspace_path) if workspace_only else None
        sessions = storage.list_sessions(workspace=workspace, limit=limit)

        return SessionListResponse(
            sessions=[
                SessionResponse(
                    session_id=s.session_id,
                    title=s.title,
                    workspace_directory=s.workspace_directory,
                    date_created_ms=s.date_created_ms,
                    message_count=s.message_count,
                )
                for s in sessions
            ],
            total=len(sessions),
        )
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return SessionListResponse(sessions=[], total=0)


@router.get("/sessions/search", response_model=SessionSearchResponse)
async def search_sessions(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
) -> SessionSearchResponse:
    """Search sessions by query."""
    try:
        from specmem.sessions.discovery import SessionDiscovery
        from specmem.sessions.indexer import SessionIndexer
        from specmem.sessions.models import SearchFilters
        from specmem.sessions.search import SessionSearchEngine
        from specmem.sessions.storage import SessionStorage

        discovery = SessionDiscovery()
        sessions_path = discovery.find_sessions_path()

        if not sessions_path:
            return SessionSearchResponse(results=[], query=q)

        storage = SessionStorage(sessions_path)
        indexer = SessionIndexer(storage)
        indexer.index_sessions()

        search_engine = SessionSearchEngine(storage)
        filters = SearchFilters(limit=limit)
        results = search_engine.search(q, filters)

        return SessionSearchResponse(
            results=[
                SessionSearchResultResponse(
                    session=SessionResponse(
                        session_id=r.session.session_id,
                        title=r.session.title,
                        workspace_directory=r.session.workspace_directory,
                        date_created_ms=r.session.date_created_ms,
                        message_count=r.session.message_count,
                    ),
                    score=r.score,
                    matched_message_indices=r.matched_message_indices,
                )
                for r in results
            ],
            query=q,
        )
    except Exception as e:
        logger.error(f"Session search failed: {e}")
        return SessionSearchResponse(results=[], query=q)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get a specific session with messages."""
    try:
        from specmem.sessions.discovery import SessionDiscovery
        from specmem.sessions.indexer import SessionIndexer
        from specmem.sessions.storage import SessionStorage

        discovery = SessionDiscovery()
        sessions_path = discovery.find_sessions_path()

        if not sessions_path:
            raise HTTPException(status_code=404, detail="Sessions not configured")

        storage = SessionStorage(sessions_path)
        indexer = SessionIndexer(storage)
        indexer.index_sessions()

        session = storage.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        return SessionResponse(
            session_id=session.session_id,
            title=session.title,
            workspace_directory=session.workspace_directory,
            date_created_ms=session.date_created_ms,
            message_count=session.message_count,
            messages=[
                SessionMessageResponse(
                    role=m.role.value,
                    content=m.content[:500] + "..." if len(m.content) > 500 else m.content,
                    timestamp_ms=m.timestamp_ms,
                )
                for m in session.messages[:50]  # Limit messages
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Powers API Endpoints
# =============================================================================


class PowerToolResponse(BaseModel):
    """Response model for a Power tool."""

    name: str
    description: str


class PowerResponse(BaseModel):
    """Response model for a Power."""

    name: str
    description: str
    version: str | None = None
    keywords: list[str]
    tools: list[PowerToolResponse]
    steering_files: list[str]


class PowerListResponse(BaseModel):
    """Response model for Power list."""

    powers: list[PowerResponse]
    total: int


@router.get("/powers", response_model=PowerListResponse)
async def list_powers() -> PowerListResponse:
    """List installed Kiro Powers."""
    try:
        powers_dir = _workspace_path / ".kiro" / "powers"
        if not powers_dir.exists():
            return PowerListResponse(powers=[], total=0)

        from specmem.adapters.power import PowerAdapter

        adapter = PowerAdapter()
        powers = []

        for power_dir in powers_dir.iterdir():
            if not power_dir.is_dir():
                continue

            power_info = adapter._load_power_info(power_dir)
            if power_info:
                powers.append(
                    PowerResponse(
                        name=power_info.name,
                        description=power_info.description,
                        version=power_info.version,
                        keywords=power_info.keywords,
                        tools=[
                            PowerToolResponse(name=t.name, description=t.description)
                            for t in power_info.tools
                        ],
                        steering_files=[str(f.name) for f in power_info.steering_files],
                    )
                )

        return PowerListResponse(powers=powers, total=len(powers))
    except Exception as e:
        logger.error(f"Failed to list powers: {e}")
        return PowerListResponse(powers=[], total=0)


@router.get("/powers/{power_name}")
async def get_power(power_name: str) -> PowerResponse:
    """Get details for a specific Power."""
    powers_dir = _workspace_path / ".kiro" / "powers" / power_name
    if not powers_dir.exists():
        raise HTTPException(status_code=404, detail=f"Power not found: {power_name}")

    try:
        from specmem.adapters.power import PowerAdapter

        adapter = PowerAdapter()
        power_info = adapter._load_power_info(powers_dir)

        if not power_info:
            raise HTTPException(status_code=404, detail=f"Power not found: {power_name}")

        return PowerResponse(
            name=power_info.name,
            description=power_info.description,
            version=power_info.version,
            keywords=power_info.keywords,
            tools=[
                PowerToolResponse(name=t.name, description=t.description) for t in power_info.tools
            ],
            steering_files=[str(f.name) for f in power_info.steering_files],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get power: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Score API Endpoints
# =============================================================================


class ScoreBreakdownResponse(BaseModel):
    """Response model for score breakdown."""

    category: str
    score: float
    weight: float
    weighted_score: float
    details: str


class HealthScoreResponse(BaseModel):
    """Response model for health score."""

    overall_score: float
    letter_grade: str
    grade_color: str
    breakdown: list[ScoreBreakdownResponse]
    suggestions: list[str]
    spec_count: int
    feature_count: int


@router.get("/health", response_model=HealthScoreResponse)
async def get_health_score() -> HealthScoreResponse:
    """Get project health score (cached for 5 minutes)."""
    # Check cache first
    cached = _get_cached("health")
    if cached is not None:
        return cached

    try:
        from specmem.health.engine import HealthScoreEngine

        engine = HealthScoreEngine(_workspace_path)
        score = engine.calculate()

        response = HealthScoreResponse(
            overall_score=round(score.overall_score, 1),
            letter_grade=score.letter_grade,
            grade_color=score.grade_to_color(score.letter_grade),
            breakdown=[
                ScoreBreakdownResponse(
                    category=item.category.value,
                    score=round(item.score, 1),
                    weight=item.weight,
                    weighted_score=round(item.weighted_score(), 1),
                    details=item.details,
                )
                for item in score.breakdown
            ],
            suggestions=score.suggestions,
            spec_count=score.spec_count,
            feature_count=score.feature_count,
        )
        _set_cached("health", response)
        return response
    except Exception as e:
        logger.error(f"Health score calculation failed: {e}")
        return HealthScoreResponse(
            overall_score=0.0,
            letter_grade="F",
            grade_color="#ef4444",
            breakdown=[],
            suggestions=["Unable to calculate health score"],
            spec_count=0,
            feature_count=0,
        )


# =============================================================================
# Impact Graph API Endpoints
# =============================================================================


class GraphNodeResponse(BaseModel):
    """Response model for a graph node."""

    id: str
    type: str
    label: str
    metadata: dict
    x: float | None = None
    y: float | None = None


class GraphEdgeResponse(BaseModel):
    """Response model for a graph edge."""

    source: str
    target: str
    relationship: str
    weight: float = 1.0


class ImpactGraphResponse(BaseModel):
    """Response model for impact graph."""

    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    stats: dict


@router.get("/graph", response_model=ImpactGraphResponse)
async def get_impact_graph(
    types: str | None = Query(None, description="Comma-separated node types to include"),
) -> ImpactGraphResponse:
    """Get impact graph data for visualization (cached for 5 minutes)."""
    # Check cache first (only for unfiltered requests)
    cache_key = f"graph:{types or 'all'}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        from specmem.graph.builder import ImpactGraphBuilder
        from specmem.graph.models import NodeType

        builder = ImpactGraphBuilder(_workspace_path)
        graph = builder.build()

        # Apply type filter if specified
        if types:
            type_list = [NodeType(t.strip()) for t in types.split(",")]
            graph = graph.filter_by_type(type_list)

        data = graph.to_dict()

        response = ImpactGraphResponse(
            nodes=[
                GraphNodeResponse(
                    id=n["id"],
                    type=n["type"],
                    label=n["label"],
                    metadata=n["metadata"],
                    x=n.get("x"),
                    y=n.get("y"),
                )
                for n in data["nodes"]
            ],
            edges=[
                GraphEdgeResponse(
                    source=e["source"],
                    target=e["target"],
                    relationship=e["relationship"],
                    weight=e.get("weight", 1.0),
                )
                for e in data["edges"]
            ],
            stats=data["stats"],
        )
        _set_cached(cache_key, response)
        return response
    except Exception as e:
        logger.error(f"Failed to build impact graph: {e}")
        return ImpactGraphResponse(
            nodes=[],
            edges=[],
            stats={"total_nodes": 0, "total_edges": 0, "nodes_by_type": {}},
        )


# =============================================================================
# Quick Actions API Endpoints
# =============================================================================


class ActionResultResponse(BaseModel):
    """Response model for quick action results."""

    success: bool
    action: str
    message: str
    data: dict | None = None
    error: str | None = None


@router.post("/actions/scan", response_model=ActionResultResponse)
async def action_scan() -> ActionResultResponse:
    """Execute scan action."""
    # Clear cache to force fresh data after scan
    clear_cache()

    try:
        from specmem.adapters import detect_adapters

        adapters = detect_adapters(_workspace_path)
        total_blocks = 0
        adapter_results = {}

        for adapter in adapters:
            blocks = adapter.load(_workspace_path)
            adapter_results[adapter.__class__.__name__] = len(blocks)
            total_blocks += len(blocks)

        return ActionResultResponse(
            success=True,
            action="scan",
            message=f"Found {total_blocks} specifications",
            data={
                "total_blocks": total_blocks,
                "adapters": adapter_results,
            },
        )
    except Exception as e:
        logger.error(f"Scan action failed: {e}")
        return ActionResultResponse(
            success=False,
            action="scan",
            message="Scan failed",
            error=str(e),
        )


@router.post("/actions/build", response_model=ActionResultResponse)
async def action_build() -> ActionResultResponse:
    """Execute build action."""
    try:
        from specmem.adapters.kiro import KiroAdapter
        from specmem.agentx.pack_builder import PackBuilder

        adapter = KiroAdapter()
        if not adapter.detect(_workspace_path):
            return ActionResultResponse(
                success=False,
                action="build",
                message="No specifications found",
                error="No Kiro specs detected in workspace",
            )

        blocks = adapter.load(_workspace_path)
        builder = PackBuilder()
        output_path = _workspace_path / ".specmem"
        builder.build(blocks, output_path)

        return ActionResultResponse(
            success=True,
            action="build",
            message=f"Built Agent Experience Pack with {len(blocks)} specs",
            data={
                "blocks_count": len(blocks),
                "output_path": str(output_path),
            },
        )
    except Exception as e:
        logger.error(f"Build action failed: {e}")
        return ActionResultResponse(
            success=False,
            action="build",
            message="Build failed",
            error=str(e),
        )


@router.post("/actions/validate", response_model=ActionResultResponse)
async def action_validate() -> ActionResultResponse:
    """Execute validate action."""
    try:
        from specmem.validator.engine import SpecValidator

        validator = SpecValidator(_workspace_path)
        results = validator.validate_all()

        total_issues = sum(len(r.issues) for r in results)
        errors = sum(1 for r in results for i in r.issues if i.severity == "error")
        warnings = sum(1 for r in results for i in r.issues if i.severity == "warning")

        if errors > 0:
            message = f"Found {errors} errors and {warnings} warnings"
            success = False
        elif warnings > 0:
            message = f"Found {warnings} warnings"
            success = True
        else:
            message = "All specifications are valid"
            success = True

        return ActionResultResponse(
            success=success,
            action="validate",
            message=message,
            data={
                "total_issues": total_issues,
                "errors": errors,
                "warnings": warnings,
                "files_checked": len(results),
            },
        )
    except Exception as e:
        logger.error(f"Validate action failed: {e}")
        return ActionResultResponse(
            success=False,
            action="validate",
            message="Validation failed",
            error=str(e),
        )


@router.post("/actions/coverage", response_model=ActionResultResponse)
async def action_coverage() -> ActionResultResponse:
    """Execute coverage action."""
    try:
        from specmem.coverage.engine import CoverageEngine

        engine = CoverageEngine(_workspace_path)
        result = engine.analyze_coverage()

        return ActionResultResponse(
            success=True,
            action="coverage",
            message=f"Coverage: {result.coverage_percentage:.1f}%",
            data={
                "coverage_percentage": round(result.coverage_percentage, 1),
                "total_criteria": result.total_criteria,
                "covered_criteria": result.covered_criteria,
                "uncovered_criteria": result.total_criteria - result.covered_criteria,
            },
        )
    except Exception as e:
        logger.error(f"Coverage action failed: {e}")
        return ActionResultResponse(
            success=False,
            action="coverage",
            message="Coverage analysis failed",
            error=str(e),
        )


@router.post("/actions/query", response_model=ActionResultResponse)
async def action_query(
    q: str = Query(..., description="Query string"),
) -> ActionResultResponse:
    """Execute query action."""
    try:
        # Use the existing search functionality
        search_response = await search_blocks(q=q, limit=5)

        return ActionResultResponse(
            success=True,
            action="query",
            message=f"Found {len(search_response.results)} results",
            data={
                "query": q,
                "results_count": len(search_response.results),
                "results": [
                    {
                        "type": r.block.type,
                        "preview": r.block.text_preview[:100],
                        "score": round(r.score, 2),
                    }
                    for r in search_response.results
                ],
            },
        )
    except Exception as e:
        logger.error(f"Query action failed: {e}")
        return ActionResultResponse(
            success=False,
            action="query",
            message="Query failed",
            error=str(e),
        )


# =============================================================================
# Lifecycle API Endpoints - Spec Health, Pruning, Generation, Compression
# =============================================================================


class SpecHealthScoreResponse(BaseModel):
    """Response model for spec health score."""

    spec_id: str
    spec_path: str
    score: float
    code_references: int
    last_modified: str
    query_count: int
    is_orphaned: bool
    is_stale: bool
    compression_ratio: float | None = None
    recommendations: list[str]


class LifecycleHealthResponse(BaseModel):
    """Response model for lifecycle health analysis."""

    total_specs: int
    orphaned_count: int
    stale_count: int
    average_score: float
    scores: list[SpecHealthScoreResponse]


class PruneResultResponse(BaseModel):
    """Response model for prune result."""

    spec_id: str
    spec_path: str
    action: str
    archive_path: str | None = None
    reason: str


class PruneRequest(BaseModel):
    """Request model for prune operation."""

    spec_names: list[str] | None = None
    mode: str = "archive"
    dry_run: bool = True
    force: bool = False
    orphaned: bool = False
    stale: bool = False
    stale_days: int = 90


class PruneResponse(BaseModel):
    """Response model for prune operation."""

    success: bool
    message: str
    dry_run: bool
    results: list[PruneResultResponse]


class GenerateRequest(BaseModel):
    """Request model for generate operation."""

    files: list[str]
    format: str = "kiro"
    group_by: str = "directory"
    write: bool = False


class GeneratedSpecResponse(BaseModel):
    """Response model for generated spec."""

    spec_name: str
    spec_path: str
    source_files: list[str]
    adapter_format: str
    content_preview: str
    content_size: int


class GenerateResponse(BaseModel):
    """Response model for generate operation."""

    success: bool
    message: str
    specs: list[GeneratedSpecResponse]


class CompressRequest(BaseModel):
    """Request model for compress operation."""

    spec_names: list[str] | None = None
    threshold: int = 5000
    all_verbose: bool = False
    save: bool = False


class CompressedSpecResponse(BaseModel):
    """Response model for compressed spec."""

    spec_id: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    preserved_criteria_count: int


class CompressResponse(BaseModel):
    """Response model for compress operation."""

    success: bool
    message: str
    results: list[CompressedSpecResponse]
    verbose_specs: list[str] | None = None


@router.get("/lifecycle/health", response_model=LifecycleHealthResponse)
async def get_lifecycle_health(
    stale_days: int = Query(90, description="Days threshold for stale detection"),
) -> LifecycleHealthResponse:
    """Get spec health scores for all specifications."""
    try:
        from specmem.lifecycle import HealthAnalyzer

        spec_base = _workspace_path / ".kiro" / "specs"

        if not spec_base.exists():
            return LifecycleHealthResponse(
                total_specs=0,
                orphaned_count=0,
                stale_count=0,
                average_score=0.0,
                scores=[],
            )

        analyzer = HealthAnalyzer(
            spec_base_path=spec_base,
            stale_threshold_days=stale_days,
        )

        scores = analyzer.analyze_all()
        summary = analyzer.get_summary()

        return LifecycleHealthResponse(
            total_specs=summary["total_specs"],
            orphaned_count=summary["orphaned_count"],
            stale_count=summary["stale_count"],
            average_score=summary["average_score"],
            scores=[
                SpecHealthScoreResponse(
                    spec_id=s.spec_id,
                    spec_path=str(s.spec_path),
                    score=s.score,
                    code_references=s.code_references,
                    last_modified=s.last_modified.isoformat(),
                    query_count=s.query_count,
                    is_orphaned=s.is_orphaned,
                    is_stale=s.is_stale,
                    compression_ratio=s.compression_ratio,
                    recommendations=s.recommendations,
                )
                for s in scores
            ],
        )
    except Exception as e:
        logger.error(f"Lifecycle health analysis failed: {e}")
        return LifecycleHealthResponse(
            total_specs=0,
            orphaned_count=0,
            stale_count=0,
            average_score=0.0,
            scores=[],
        )


@router.get("/lifecycle/health/{spec_name}", response_model=SpecHealthScoreResponse)
async def get_spec_health(
    spec_name: str,
    stale_days: int = Query(90, description="Days threshold for stale detection"),
) -> SpecHealthScoreResponse:
    """Get health score for a specific spec."""
    from fastapi import HTTPException

    try:
        from specmem.lifecycle import HealthAnalyzer

        spec_base = _workspace_path / ".kiro" / "specs"
        spec_path = spec_base / spec_name

        if not spec_path.exists():
            raise HTTPException(status_code=404, detail=f"Spec not found: {spec_name}")

        analyzer = HealthAnalyzer(
            spec_base_path=spec_base,
            stale_threshold_days=stale_days,
        )

        score = analyzer.analyze_spec(spec_name, spec_path)

        return SpecHealthScoreResponse(
            spec_id=score.spec_id,
            spec_path=str(score.spec_path),
            score=score.score,
            code_references=score.code_references,
            last_modified=score.last_modified.isoformat(),
            query_count=score.query_count,
            is_orphaned=score.is_orphaned,
            is_stale=score.is_stale,
            compression_ratio=score.compression_ratio,
            recommendations=score.recommendations,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Spec health analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lifecycle/prune", response_model=PruneResponse)
async def prune_specs(request: PruneRequest) -> PruneResponse:
    """Prune orphaned or stale specifications."""
    try:
        from specmem.lifecycle import HealthAnalyzer, PrunerEngine

        spec_base = _workspace_path / ".kiro" / "specs"
        archive_dir = _workspace_path / ".specmem" / "archive"

        if not spec_base.exists():
            return PruneResponse(
                success=False,
                message="No specs found at .kiro/specs/",
                dry_run=request.dry_run,
                results=[],
            )

        if request.mode not in ("archive", "delete"):
            return PruneResponse(
                success=False,
                message=f"Invalid mode: {request.mode}. Use 'archive' or 'delete'.",
                dry_run=request.dry_run,
                results=[],
            )

        analyzer = HealthAnalyzer(
            spec_base_path=spec_base,
            stale_threshold_days=request.stale_days,
        )
        pruner = PrunerEngine(
            health_analyzer=analyzer,
            archive_dir=archive_dir,
        )

        results = []

        if request.spec_names:
            results = pruner.prune_by_name(
                spec_names=request.spec_names,
                mode=request.mode,  # type: ignore
                dry_run=request.dry_run,
                force=request.force,
            )
        elif request.orphaned:
            results = pruner.prune_orphaned(
                mode=request.mode,  # type: ignore
                dry_run=request.dry_run,
                force=request.force,
            )
        elif request.stale:
            results = pruner.prune_stale(
                threshold_days=request.stale_days,
                mode=request.mode,  # type: ignore
                dry_run=request.dry_run,
            )
        else:
            # Return analysis only
            scores = pruner.analyze()
            return PruneResponse(
                success=True,
                message=f"Found {len(scores)} specs. Use orphaned=true or stale=true to prune.",
                dry_run=True,
                results=[],
            )

        action_word = "would be" if request.dry_run else "were"
        return PruneResponse(
            success=True,
            message=f"{len(results)} spec(s) {action_word} processed",
            dry_run=request.dry_run,
            results=[
                PruneResultResponse(
                    spec_id=r.spec_id,
                    spec_path=str(r.spec_path),
                    action=r.action,
                    archive_path=str(r.archive_path) if r.archive_path else None,
                    reason=r.reason,
                )
                for r in results
            ],
        )
    except Exception as e:
        logger.error(f"Prune operation failed: {e}")
        return PruneResponse(
            success=False,
            message=f"Prune failed: {e!s}",
            dry_run=request.dry_run,
            results=[],
        )


@router.post("/lifecycle/generate", response_model=GenerateResponse)
async def generate_specs(request: GenerateRequest) -> GenerateResponse:
    """Generate specifications from code files."""
    try:
        from specmem.lifecycle import GeneratorEngine

        output_dir = _workspace_path / ".kiro" / "specs"

        generator = GeneratorEngine(
            default_format=request.format,
            output_dir=output_dir,
        )

        all_specs = []

        for file_arg in request.files:
            file_path = Path(file_arg)
            if not file_path.is_absolute():
                file_path = _workspace_path / file_path

            if not file_path.exists():
                continue

            if file_path.is_file():
                spec = generator.generate_from_file(file_path)
                all_specs.append(spec)
            else:
                specs = generator.generate_from_directory(
                    file_path,
                    group_by=request.group_by,  # type: ignore
                    output_format=request.format,
                )
                all_specs.extend(specs)

        if request.write:
            for spec in all_specs:
                generator.write_spec(spec)

        return GenerateResponse(
            success=True,
            message=f"Generated {len(all_specs)} spec(s)"
            + (" and saved to disk" if request.write else ""),
            specs=[
                GeneratedSpecResponse(
                    spec_name=s.spec_name,
                    spec_path=str(s.spec_path),
                    source_files=[str(f) for f in s.source_files],
                    adapter_format=s.adapter_format,
                    content_preview=s.content[:500] + "..." if len(s.content) > 500 else s.content,
                    content_size=len(s.content),
                )
                for s in all_specs
            ],
        )
    except Exception as e:
        logger.error(f"Generate operation failed: {e}")
        return GenerateResponse(
            success=False,
            message=f"Generation failed: {e!s}",
            specs=[],
        )


@router.post("/lifecycle/compress", response_model=CompressResponse)
async def compress_specs(request: CompressRequest) -> CompressResponse:
    """Compress verbose specifications."""
    try:
        from specmem.lifecycle import CompressorEngine

        spec_base = _workspace_path / ".kiro" / "specs"
        compressed_dir = _workspace_path / ".specmem" / "compressed"

        if not spec_base.exists():
            return CompressResponse(
                success=False,
                message="No specs found at .kiro/specs/",
                results=[],
            )

        compressor = CompressorEngine(
            verbose_threshold_chars=request.threshold,
            compression_storage_dir=compressed_dir,
        )

        # Discover specs
        specs: list[tuple[str, Path]] = []
        for item in spec_base.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                specs.append((item.name, item))

        if not specs:
            return CompressResponse(
                success=False,
                message="No specs found.",
                results=[],
            )

        results = []

        if request.spec_names:
            for name in request.spec_names:
                spec_path = spec_base / name
                if spec_path.exists():
                    compressed = compressor.compress_spec(name, spec_path)
                    results.append(compressed)
        elif request.all_verbose:
            results = compressor.compress_all(specs)
        else:
            # Return list of verbose specs
            verbose = compressor.get_verbose_specs(specs, request.threshold)
            return CompressResponse(
                success=True,
                message=f"Found {len(verbose)} verbose spec(s) exceeding {request.threshold} chars",
                results=[],
                verbose_specs=verbose,
            )

        if request.save:
            for result in results:
                compressor.save_compressed(result)

        return CompressResponse(
            success=True,
            message=f"Compressed {len(results)} spec(s)" + (" and saved" if request.save else ""),
            results=[
                CompressedSpecResponse(
                    spec_id=r.spec_id,
                    original_size=r.original_size,
                    compressed_size=r.compressed_size,
                    compression_ratio=r.compression_ratio,
                    preserved_criteria_count=len(r.preserved_criteria),
                )
                for r in results
            ],
        )
    except Exception as e:
        logger.error(f"Compress operation failed: {e}")
        return CompressResponse(
            success=False,
            message=f"Compression failed: {e!s}",
            results=[],
        )


# Quick action for lifecycle health
@router.post("/actions/lifecycle-health", response_model=ActionResultResponse)
async def action_lifecycle_health() -> ActionResultResponse:
    """Execute lifecycle health action."""
    try:
        health_response = await get_lifecycle_health()

        return ActionResultResponse(
            success=True,
            action="lifecycle-health",
            message=f"Analyzed {health_response.total_specs} specs (avg score: {health_response.average_score:.2f})",
            data={
                "total_specs": health_response.total_specs,
                "orphaned_count": health_response.orphaned_count,
                "stale_count": health_response.stale_count,
                "average_score": round(health_response.average_score, 2),
            },
        )
    except Exception as e:
        logger.error(f"Lifecycle health action failed: {e}")
        return ActionResultResponse(
            success=False,
            action="lifecycle-health",
            message="Health analysis failed",
            error=str(e),
        )


# =============================================================================
# Kiro Configuration API Endpoints
# =============================================================================


class SteeringFileResponse(BaseModel):
    """Response model for a steering file."""

    name: str
    title: str
    inclusion: str
    file_match_pattern: str | None = None
    body_preview: str


class MCPServerResponse(BaseModel):
    """Response model for an MCP server."""

    name: str
    command: str
    args: list[str]
    disabled: bool
    auto_approve: list[str]


class HookResponse(BaseModel):
    """Response model for a hook."""

    name: str
    description: str
    trigger: str
    file_pattern: str | None = None
    enabled: bool
    action: str | None = None


class KiroConfigResponse(BaseModel):
    """Response model for Kiro configuration."""

    steering_files: list[SteeringFileResponse]
    mcp_servers: list[MCPServerResponse]
    hooks: list[HookResponse]
    total_tools: int
    enabled_servers: int
    active_hooks: int


@router.get("/kiro-config", response_model=KiroConfigResponse)
async def get_kiro_config() -> KiroConfigResponse:
    """Get Kiro configuration summary."""
    try:
        from specmem.kiro.indexer import KiroConfigIndexer

        indexer = KiroConfigIndexer(_workspace_path)
        indexer.index_all()
        summary = indexer.get_summary()

        return KiroConfigResponse(
            steering_files=[
                SteeringFileResponse(
                    name=s.path.name,
                    title=s.title,
                    inclusion=s.inclusion,
                    file_match_pattern=s.file_match_pattern,
                    body_preview=s.body[:200] + "..." if len(s.body) > 200 else s.body,
                )
                for s in summary.steering_files
            ],
            mcp_servers=[
                MCPServerResponse(
                    name=m.name,
                    command=m.command,
                    args=m.args,
                    disabled=m.disabled,
                    auto_approve=m.auto_approve,
                )
                for m in summary.mcp_servers
            ],
            hooks=[
                HookResponse(
                    name=h.name,
                    description=h.description,
                    trigger=h.trigger,
                    file_pattern=h.file_pattern,
                    enabled=h.enabled,
                    action=h.action,
                )
                for h in summary.hooks
            ],
            total_tools=summary.total_tools,
            enabled_servers=summary.enabled_servers,
            active_hooks=summary.active_hooks,
        )
    except Exception as e:
        logger.error(f"Failed to get Kiro config: {e}")
        return KiroConfigResponse(
            steering_files=[],
            mcp_servers=[],
            hooks=[],
            total_tools=0,
            enabled_servers=0,
            active_hooks=0,
        )


# =============================================================================
# Coding Guidelines API Endpoints
# =============================================================================


class GuidelineResponse(BaseModel):
    """Response model for a single guideline."""

    id: str
    title: str
    content: str
    source_type: str
    source_file: str
    file_pattern: str | None = None
    tags: list[str]
    is_sample: bool = False


class GuidelinesListResponse(BaseModel):
    """Response model for guidelines list."""

    guidelines: list[GuidelineResponse]
    total_count: int
    counts_by_source: dict[str, int]


class ConversionResultResponse(BaseModel):
    """Response model for conversion result."""

    filename: str
    content: str
    frontmatter: dict
    source_id: str


class ExportResultResponse(BaseModel):
    """Response model for export result."""

    format: str
    content: str
    filename: str


@router.get("/guidelines", response_model=GuidelinesListResponse)
async def get_guidelines(
    source: str | None = Query(None, description="Filter by source type"),
    file: str | None = Query(None, description="Filter by file path"),
    q: str | None = Query(None, description="Search query"),
) -> GuidelinesListResponse:
    """Get all coding guidelines with optional filtering."""
    try:
        from specmem.guidelines.aggregator import GuidelinesAggregator

        aggregator = GuidelinesAggregator(_workspace_path)

        if source:
            guidelines = aggregator.filter_by_source(source)
            from specmem.guidelines.models import GuidelinesResponse

            response = GuidelinesResponse.from_guidelines(guidelines)
        elif file:
            guidelines = aggregator.filter_by_file(file)
            from specmem.guidelines.models import GuidelinesResponse

            response = GuidelinesResponse.from_guidelines(guidelines)
        elif q:
            guidelines = aggregator.search(q)
            from specmem.guidelines.models import GuidelinesResponse

            response = GuidelinesResponse.from_guidelines(guidelines)
        else:
            response = aggregator.get_all(include_samples=True)

        return GuidelinesListResponse(
            guidelines=[
                GuidelineResponse(
                    id=g.id,
                    title=g.title,
                    content=g.content,
                    source_type=g.source_type.value,
                    source_file=g.source_file,
                    file_pattern=g.file_pattern,
                    tags=g.tags,
                    is_sample=g.is_sample,
                )
                for g in response.guidelines
            ],
            total_count=response.total_count,
            counts_by_source=response.counts_by_source,
        )
    except Exception as e:
        logger.error(f"Failed to get guidelines: {e}")
        return GuidelinesListResponse(
            guidelines=[],
            total_count=0,
            counts_by_source={},
        )


class ConvertRequest(BaseModel):
    """Request model for conversion."""

    guideline_id: str
    format: str = "steering"  # steering, claude, or cursor
    preview: bool = True


@router.post("/guidelines/convert", response_model=ConversionResultResponse)
async def convert_guideline(request: ConvertRequest) -> ConversionResultResponse:
    """Convert a guideline to any format (steering, claude, cursor)."""
    try:
        from specmem.guidelines.aggregator import GuidelinesAggregator
        from specmem.guidelines.converter import GuidelinesConverter

        if request.format not in ("steering", "claude", "cursor"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {request.format}. Valid formats: steering, claude, cursor",
            )

        aggregator = GuidelinesAggregator(_workspace_path)
        response = aggregator.get_all(include_samples=True)

        # Find the guideline by ID
        guideline = None
        for g in response.guidelines:
            if g.id == request.guideline_id:
                guideline = g
                break

        if not guideline:
            raise HTTPException(status_code=404, detail="Guideline not found")

        converter = GuidelinesConverter()

        if request.format == "steering":
            result = converter.to_steering(guideline)
            filename = result.filename
            content = result.content
            frontmatter = result.frontmatter

            # Write file if not preview
            if not request.preview:
                steering_dir = _workspace_path / ".kiro" / "steering"
                converter.write_steering_files([result], steering_dir)
        elif request.format == "claude":
            content = converter.to_claude([guideline])
            filename = "CLAUDE.md"
            frontmatter = {}

            if not request.preview:
                (_workspace_path / filename).write_text(content, encoding="utf-8")
        else:  # cursor
            content = converter.to_cursor([guideline])
            filename = ".cursorrules"
            frontmatter = {}

            if not request.preview:
                (_workspace_path / filename).write_text(content, encoding="utf-8")

        return ConversionResultResponse(
            filename=filename,
            content=content,
            frontmatter=frontmatter,
            source_id=guideline.id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to convert guideline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExportRequest(BaseModel):
    """Request model for export."""

    format: str  # "claude" or "cursor"


@router.post("/guidelines/export", response_model=ExportResultResponse)
async def export_guidelines(request: ExportRequest) -> ExportResultResponse:
    """Export all guidelines to Claude or Cursor format."""
    try:
        from specmem.guidelines.aggregator import GuidelinesAggregator
        from specmem.guidelines.converter import GuidelinesConverter

        aggregator = GuidelinesAggregator(_workspace_path)
        response = aggregator.get_all(include_samples=False)

        if not response.guidelines:
            raise HTTPException(status_code=404, detail="No guidelines to export")

        converter = GuidelinesConverter()

        if request.format == "claude":
            content = converter.to_claude(response.guidelines)
            filename = "CLAUDE.md"
        elif request.format == "cursor":
            content = converter.to_cursor(response.guidelines)
            filename = ".cursorrules"
        else:
            raise HTTPException(
                status_code=400, detail=f"Invalid format: {request.format}"
            )

        return ExportResultResponse(
            format=request.format,
            content=content,
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export guidelines: {e}")
        raise HTTPException(status_code=500, detail=str(e))
