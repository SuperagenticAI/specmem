"""Round-trip tests for the Qdrant vector store backend.

These exercise the local (embedded) Qdrant client and are skipped when
qdrant-client is not installed.
"""

from __future__ import annotations

import pytest

from specmem.core.specir import SpecBlock, SpecStatus, SpecType


pytest.importorskip("qdrant_client")

from specmem.vectordb.qdrant_store import QdrantStore


def _block(text: str, *, pinned: bool = False) -> SpecBlock:
    return SpecBlock(
        id=SpecBlock.generate_id("spec.md", text),
        type=SpecType.KNOWLEDGE,
        text=text,
        source="spec.md",
        status=SpecStatus.ACTIVE,
        tags=["alpha", "beta"],
        links=[],
        pinned=pinned,
    )


@pytest.fixture
def store(tmp_path):
    s = QdrantStore(path=str(tmp_path / "qdrant"), collection_name="test_specs")
    yield s


def test_hash_ids_store_and_round_trip(store):
    """SpecBlock hex-hash ids must map to valid Qdrant point ids and back."""
    block = _block("use ruff for linting", pinned=True)

    store.store([block], [[0.1] * 384])

    assert store.count() == 1

    results = store.query([0.1] * 384, top_k=5)
    assert len(results) == 1
    # The original hash id is recovered, not the internal UUID.
    assert results[0].block.id == block.id
    assert results[0].block.tags == ["alpha", "beta"]

    assert store.get_by_id(block.id) is not None
    assert store.get_by_id(block.id).id == block.id
    assert [b.id for b in store.get_pinned()] == [block.id]


def test_update_status_and_delete_by_hash_id(store):
    block = _block("prefer small diffs")
    store.store([block], [[0.2] * 384])

    assert store.update_status(block.id, SpecStatus.DEPRECATED) is True
    assert store.get_by_id(block.id).status == SpecStatus.DEPRECATED

    # Idempotent: setting the same status again is a no-op success.
    assert store.update_status(block.id, SpecStatus.DEPRECATED) is True

    assert store.delete(block.id) is True
    assert store.count() == 0


def test_custom_collection_name_is_used(tmp_path):
    store = QdrantStore(path=str(tmp_path / "qdrant"), collection_name="custom_name")
    store.store([_block("x")], [[0.3] * 384])
    assert store._collection_name == "custom_name"
    assert store.count() == 1
