"""Vector storage backends for SpecMem.

The local embedding backend (LanceDB + sentence-transformers) requires
the 'local' extra: pip install specmem[local]
"""

from specmem.vectordb.base import (
    VALID_TRANSITIONS,
    AuditEntry,
    GovernanceRules,
    QueryResult,
    VectorStore,
    validate_transition,
)


# Lazy imports for optional dependencies
_lancedb_store = None
_embedding_provider = None


def get_lancedb_store():
    """Get LanceDBStore class (requires specmem[local])."""
    global _lancedb_store
    if _lancedb_store is None:
        try:
            from specmem.vectordb.lancedb_store import LanceDBStore

            _lancedb_store = LanceDBStore
        except ImportError as e:
            raise ImportError(
                "LanceDB is not installed. Install with: pip install specmem[local]"
            ) from e
    return _lancedb_store


def get_embedding_provider():
    """Get embedding provider (requires specmem[local])."""
    global _embedding_provider
    if _embedding_provider is None:
        try:
            from specmem.vectordb.embeddings import get_embedding_provider as _get_provider

            _embedding_provider = _get_provider
        except ImportError as e:
            raise ImportError("Embedding providers require: pip install specmem[local]") from e
    return _embedding_provider()


# Try to import for backwards compatibility, but don't fail
try:
    from specmem.vectordb.embeddings import (
        EmbeddingProvider,
        LocalEmbeddingProvider,
        get_embedding_provider,
    )
    from specmem.vectordb.factory import SUPPORTED_BACKENDS, get_vector_store, list_backends
    from specmem.vectordb.lancedb_store import LanceDBStore

    _HAS_LOCAL = True
except ImportError:
    _HAS_LOCAL = False
    LanceDBStore = None  # type: ignore
    EmbeddingProvider = None  # type: ignore
    LocalEmbeddingProvider = None  # type: ignore
    SUPPORTED_BACKENDS = {}
    get_vector_store = None  # type: ignore
    list_backends = None  # type: ignore


__all__ = [
    "SUPPORTED_BACKENDS",
    "VALID_TRANSITIONS",
    "AuditEntry",
    "EmbeddingProvider",
    "GovernanceRules",
    "LanceDBStore",
    "LocalEmbeddingProvider",
    "QueryResult",
    "VectorStore",
    "get_embedding_provider",
    "get_lancedb_store",
    "get_vector_store",
    "list_backends",
    "validate_transition",
]
