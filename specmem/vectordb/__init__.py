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

# Embedding providers. The factory and provider classes import lightly; the
# heavy local dependency (sentence-transformers) is imported lazily inside
# LocalEmbeddingProvider only when a local provider is actually instantiated.
# This means get_embedding_provider() works for cloud providers and alternative
# vector stores (Qdrant, Chroma) without requiring the 'local' extra.
from specmem.vectordb.embeddings import (
    EmbeddingProvider,
    LocalEmbeddingProvider,
    get_embedding_provider,
)


# Lazy import for the optional LanceDB store class (requires specmem[local]).
_lancedb_store = None


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


# Vector store factory (optional backends fail gracefully).
try:
    from specmem.vectordb.factory import SUPPORTED_BACKENDS, get_vector_store, list_backends
except ImportError:
    SUPPORTED_BACKENDS = {}
    get_vector_store = None  # type: ignore
    list_backends = None  # type: ignore

# LanceDB store class (optional, requires specmem[local]).
try:
    from specmem.vectordb.lancedb_store import LanceDBStore

    _HAS_LOCAL = True
except ImportError:
    _HAS_LOCAL = False
    LanceDBStore = None  # type: ignore


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
