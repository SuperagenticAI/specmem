"""Tests for vector DB config validation and CLI kwargs wiring."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from specmem.cli.main import _vector_store_kwargs
from specmem.core.config import SpecMemConfig, VectorDBConfig


def test_qdrant_collection_is_threaded_into_kwargs() -> None:
    config = SpecMemConfig()
    config.vectordb = VectorDBConfig(
        backend="qdrant",
        qdrant_url="http://localhost:6333",
        qdrant_api_key="secret",
        qdrant_collection="my_specs",
    )

    kwargs = _vector_store_kwargs(config)

    assert kwargs == {
        "url": "http://localhost:6333",
        "api_key": "secret",
        "collection_name": "my_specs",
    }


def test_non_qdrant_backend_passes_no_kwargs() -> None:
    config = SpecMemConfig()
    config.vectordb = VectorDBConfig(backend="lancedb", qdrant_collection="ignored")

    assert _vector_store_kwargs(config) == {}


def test_unsupported_backend_rejected() -> None:
    with pytest.raises(ValidationError):
        VectorDBConfig(backend="sqlite-vec")
