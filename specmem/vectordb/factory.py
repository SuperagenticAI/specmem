"""Vector store factory for SpecMem.

Provides a unified interface for creating vector store instances
based on configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from specmem.core.exceptions import VectorStoreError


if TYPE_CHECKING:
    from specmem.vectordb.base import VectorStore


# Supported backend names
SUPPORTED_BACKENDS = {
    "lancedb",
    "chroma",
    "qdrant",
    "weaviate",
    "milvus",
    "agentvectordb",
}


def get_vector_store(
    backend: str = "lancedb",
    path: str | None = None,
    **kwargs,
) -> VectorStore:
    """Factory function to create a vector store instance.

    Args:
        backend: Backend name (lancedb, chroma, qdrant, weaviate, milvus, agentvectordb)
        path: Path for local storage (optional, uses default if not provided)
        **kwargs: Additional backend-specific arguments

    Returns:
        VectorStore instance

    Raises:
        VectorStoreError: If backend is not supported or initialization fails
    """
    if backend not in SUPPORTED_BACKENDS:
        raise VectorStoreError(
            f"Unsupported vector backend: {backend}",
            code="UNSUPPORTED_BACKEND",
            details={
                "backend": backend,
                "supported": list(SUPPORTED_BACKENDS),
            },
        )

    if backend == "lancedb":
        from specmem.vectordb.lancedb_store import LanceDBStore

        return LanceDBStore(db_path=path or ".specmem/vectordb", **kwargs)

    elif backend == "chroma":
        from specmem.vectordb.chroma_store import ChromaDBStore

        return ChromaDBStore(path=path or ".specmem/chroma", **kwargs)

    elif backend == "qdrant":
        from specmem.vectordb.qdrant_store import QdrantStore

        return QdrantStore(path=path or ".specmem/qdrant", **kwargs)

    elif backend == "weaviate":
        # Weaviate requires cloud connection typically
        raise VectorStoreError(
            "Weaviate backend not yet implemented. Use lancedb, chroma, or qdrant.",
            code="NOT_IMPLEMENTED",
            details={"backend": backend},
        )

    elif backend == "milvus":
        # Milvus requires additional setup
        raise VectorStoreError(
            "Milvus backend not yet implemented. Use lancedb, chroma, or qdrant.",
            code="NOT_IMPLEMENTED",
            details={"backend": backend},
        )

    elif backend == "agentvectordb":
        from specmem.vectordb.agentvectordb_store import AgentVectorDBStore

        return AgentVectorDBStore(db_path=path or ".specmem/agentvectordb", **kwargs)

    # Should not reach here due to earlier check
    raise VectorStoreError(f"Unknown backend: {backend}", code="UNKNOWN_BACKEND")


def list_backends() -> list[str]:
    """List all supported backend names.

    Returns:
        List of supported backend names
    """
    return sorted(SUPPORTED_BACKENDS)
