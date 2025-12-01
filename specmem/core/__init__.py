"""Core domain models and logic for SpecMem."""

from specmem.core.config import EmbeddingConfig, SpecMemConfig, VectorDBConfig
from specmem.core.exceptions import (
    AdapterError,
    ConfigurationError,
    EmbeddingError,
    SpecMemError,
    VectorStoreError,
)
from specmem.core.mappings import CodeRef, TestMapping
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


__all__ = [
    "AdapterError",
    "CodeRef",
    "ConfigurationError",
    "EmbeddingConfig",
    "EmbeddingError",
    "SpecBlock",
    "SpecMemConfig",
    "SpecMemError",
    "SpecStatus",
    "SpecType",
    "TestMapping",
    "VectorDBConfig",
    "VectorStoreError",
]
