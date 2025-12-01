"""REST API endpoints for Streaming Context API.

Provides HTTP endpoints for context queries, streaming, and profile management.
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from specmem.context.api import StreamingContextAPI
from specmem.context.optimizer import ContextChunk
from specmem.context.profiles import AgentProfile, ProfileManager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["context"])

# Module-level state (set by server)
_context_api: StreamingContextAPI | None = None
_profile_manager: ProfileManager | None = None


def set_context_api(api: StreamingContextAPI) -> None:
    """Set the context API instance."""
    global _context_api
    _context_api = api


def set_profile_manager(manager: ProfileManager) -> None:
    """Set the profile manager instance."""
    global _profile_manager
    _profile_manager = manager


def get_context_api() -> StreamingContextAPI:
    """Get the context API instance."""
    if _context_api is None:
        raise HTTPException(
            status_code=503,
            detail="Context API not initialized. Run 'specmem build' first.",
        )
    return _context_api


def get_profile_manager() -> ProfileManager:
    """Get the profile manager instance."""
    if _profile_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Profile manager not initialized.",
        )
    return _profile_manager


# Request/Response Models


class ContextQueryRequest(BaseModel):
    """Request body for context query."""

    query: str = Field(..., description="Natural language query")
    token_budget: int | None = Field(None, ge=100, le=100000, description="Token budget")
    format: str = Field("json", description="Output format: json, markdown, text")
    type_filters: list[str] | None = Field(None, description="Filter by spec types")
    profile: str | None = Field(None, description="Agent profile name")
    top_k: int = Field(20, ge=1, le=100, description="Maximum results")


class ContextChunkResponse(BaseModel):
    """Response model for a context chunk."""

    id: str
    type: str
    source: str
    text: str
    tokens: int
    relevance_score: float
    pinned: bool
    truncated: bool


class ContextQueryResponse(BaseModel):
    """Response model for context query."""

    chunks: list[ContextChunkResponse]
    total_tokens: int
    token_budget: int
    truncated_count: int
    query: str
    format: str
    formatted_content: str


class ProfileResponse(BaseModel):
    """Response model for agent profile."""

    name: str
    context_window: int
    token_budget: int
    preferred_format: str
    type_filters: list[str]


class ProfileCreateRequest(BaseModel):
    """Request body for creating a profile."""

    name: str = Field(..., min_length=1, max_length=50)
    context_window: int = Field(8000, ge=1000, le=1000000)
    token_budget: int = Field(4000, ge=100, le=100000)
    preferred_format: str = Field("json")
    type_filters: list[str] = Field(default_factory=list)


# Endpoints


@router.post("/query", response_model=ContextQueryResponse)
async def query_context(request: ContextQueryRequest) -> ContextQueryResponse:
    """Query context with token budget optimization.

    Returns relevant specifications optimized to fit within the token budget.
    """
    api = get_context_api()

    response = api.get_context(
        query=request.query,
        token_budget=request.token_budget,
        format=request.format,  # type: ignore
        type_filters=request.type_filters,
        profile=request.profile,
        top_k=request.top_k,
    )

    return ContextQueryResponse(
        chunks=[
            ContextChunkResponse(
                id=c.block_id,
                type=c.block_type,
                source=c.source,
                text=c.text,
                tokens=c.tokens,
                relevance_score=c.relevance,
                pinned=c.pinned,
                truncated=c.truncated,
            )
            for c in response.chunks
        ],
        total_tokens=response.total_tokens,
        token_budget=response.token_budget,
        truncated_count=response.truncated_count,
        query=response.query,
        format=response.format,
        formatted_content=response.formatted_content,
    )


@router.get("/stream")
async def stream_context(
    query: str = Query(..., description="Natural language query"),
    token_budget: int | None = Query(None, ge=100, le=100000),
    format: str = Query("json", description="Output format"),
    type_filters: str | None = Query(None, description="Comma-separated type filters"),
    profile: str | None = Query(None, description="Agent profile name"),
    top_k: int = Query(20, ge=1, le=100),
) -> StreamingResponse:
    """Stream context as Server-Sent Events.

    Streams chunks one at a time, followed by a completion event.
    """
    api = get_context_api()

    # Parse type filters
    filters = type_filters.split(",") if type_filters else None

    async def generate_events():
        async for item in api.stream_query(
            query=query,
            token_budget=token_budget,
            format=format,  # type: ignore
            type_filters=filters,
            profile=profile,
            top_k=top_k,
        ):
            if isinstance(item, ContextChunk):
                data = json.dumps(
                    {
                        "type": "chunk",
                        "data": item.to_dict(),
                    }
                )
            else:  # StreamCompletion
                data = json.dumps(item.to_dict())

            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# Profile Management Endpoints


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles() -> list[ProfileResponse]:
    """List all agent profiles."""
    manager = get_profile_manager()
    profiles = manager.list_all()

    return [
        ProfileResponse(
            name=p.name,
            context_window=p.context_window,
            token_budget=p.token_budget,
            preferred_format=p.preferred_format,
            type_filters=p.type_filters,
        )
        for p in profiles
    ]


@router.post("/profiles", response_model=ProfileResponse)
async def create_profile(request: ProfileCreateRequest) -> ProfileResponse:
    """Create or update an agent profile."""
    manager = get_profile_manager()

    profile = AgentProfile(
        name=request.name,
        context_window=request.context_window,
        token_budget=request.token_budget,
        preferred_format=request.preferred_format,
        type_filters=request.type_filters,
    )

    manager.set(profile)

    return ProfileResponse(
        name=profile.name,
        context_window=profile.context_window,
        token_budget=profile.token_budget,
        preferred_format=profile.preferred_format,
        type_filters=profile.type_filters,
    )


@router.get("/profiles/{name}", response_model=ProfileResponse)
async def get_profile(name: str) -> ProfileResponse:
    """Get a specific agent profile."""
    manager = get_profile_manager()
    profile = manager.get(name)

    return ProfileResponse(
        name=profile.name,
        context_window=profile.context_window,
        token_budget=profile.token_budget,
        preferred_format=profile.preferred_format,
        type_filters=profile.type_filters,
    )


@router.delete("/profiles/{name}")
async def delete_profile(name: str) -> dict:
    """Delete a custom agent profile."""
    manager = get_profile_manager()

    if manager.delete(name):
        return {"message": f"Profile '{name}' deleted"}
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete profile '{name}' (not found or is default)",
        )
