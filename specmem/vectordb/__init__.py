"""Vector storage backends for SpecMem."""

from specmem.vectordb.base import (
    VALID_TRANSITIONS,
    AuditEntry,
    GovernanceRules,
    QueryResult,
    VectorStore,
    validate_transition,
)
from specmem.vectordb.embeddings import (
    EmbeddingProvider,
    LocalEmbeddingProvider,
    get_embedding_provider,
)
from specmem.vectordb.factory import SUPPORTED_BACKENDS, get_vector_store, list_backends
from specmem.vectordb.lancedb_store import LanceDBStore


__all__ = [
    "SUPPORTED_BACKENDS",
    "VALID_TRANSITIONS",
    "AuditEntry",
    # Embeddings
    "EmbeddingProvider",
    "GovernanceRules",
    # Default store
    "LanceDBStore",
    "LocalEmbeddingProvider",
    "QueryResult",
    # Base classes and types
    "VectorStore",
    "get_embedding_provider",
    # Factory
    "get_vector_store",
    "list_backends",
    "validate_transition",
]
