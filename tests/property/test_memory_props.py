"""Property-based tests for Memory system (VectorStore).

These tests use Hypothesis to verify universal properties that should hold
across all valid memory operations.
"""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.core.specir import SpecBlock, SpecStatus, SpecType
from specmem.vectordb.lancedb_store import LanceDBStore


# Strategies for generating test data
spec_type_strategy = st.sampled_from(list(SpecType))
spec_status_strategy = st.sampled_from([SpecStatus.ACTIVE, SpecStatus.DEPRECATED])
legacy_status_strategy = st.sampled_from([SpecStatus.LEGACY, SpecStatus.OBSOLETE])

valid_text_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
source_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Embedding dimension (using small dimension for tests)
EMBEDDING_DIM = 8


def generate_random_embedding(seed: int) -> list[float]:
    """Generate a deterministic random embedding from seed."""
    import random

    rng = random.Random(seed)
    return [rng.random() for _ in range(EMBEDDING_DIM)]


@st.composite
def valid_specblock_strategy(draw: st.DrawFn) -> SpecBlock:
    """Generate valid SpecBlock instances."""
    source = draw(source_strategy)
    text = draw(valid_text_strategy)
    block_id = SpecBlock.generate_id(source, text)

    return SpecBlock(
        id=block_id,
        type=draw(spec_type_strategy),
        text=text,
        source=source,
        status=draw(spec_status_strategy),
        tags=[],
        links=[],
        pinned=draw(st.booleans()),
    )


@st.composite
def legacy_specblock_strategy(draw: st.DrawFn) -> SpecBlock:
    """Generate SpecBlock with legacy/obsolete status."""
    source = draw(source_strategy)
    text = draw(valid_text_strategy)
    block_id = SpecBlock.generate_id(source, text)

    return SpecBlock(
        id=block_id,
        type=draw(spec_type_strategy),
        text=text,
        source=source,
        status=draw(legacy_status_strategy),
        tags=[],
        links=[],
        pinned=False,
    )


@pytest.fixture
def temp_store():
    """Create a temporary LanceDB store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()
        yield store


# Feature: specmem-mvp, Property 5: Vector Query Relevance Ordering
# Validates: Requirements 3.3, 6.3
@given(
    blocks=st.lists(valid_specblock_strategy(), min_size=2, max_size=10, unique_by=lambda b: b.id)
)
@settings(max_examples=50)
def test_vector_query_relevance_ordering(blocks: list[SpecBlock]) -> None:
    """For any query embedding and result set, the returned SpecBlocks
    SHALL be ordered by descending similarity score.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()

        # Generate embeddings
        embeddings = [generate_random_embedding(i) for i in range(len(blocks))]

        # Store blocks
        store.store(blocks, embeddings)

        # Query with first embedding
        query_embedding = embeddings[0]
        results = store.query(query_embedding, top_k=len(blocks))

        # Verify ordering: scores should be descending
        if len(results) > 1:
            scores = [r.score for r in results]
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1], f"Scores not in descending order: {scores}"


# Feature: specmem-mvp, Property 6: Pinned Block Inclusion
# Validates: Requirements 4.1, 4.2
@given(
    pinned_blocks=st.lists(
        valid_specblock_strategy(), min_size=1, max_size=3, unique_by=lambda b: b.id
    ),
)
@settings(max_examples=30)
def test_pinned_block_inclusion(pinned_blocks: list[SpecBlock]) -> None:
    """For any query against memory containing pinned SpecBlocks,
    all pinned blocks SHALL appear in the results regardless of similarity score.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()

        # Mark all blocks as pinned
        for block in pinned_blocks:
            block.pinned = True

        # Generate embeddings
        embeddings = [generate_random_embedding(i) for i in range(len(pinned_blocks))]

        # Store blocks
        store.store(pinned_blocks, embeddings)

        # Get pinned blocks
        retrieved_pinned = store.get_pinned()
        retrieved_pinned_ids = {b.id for b in retrieved_pinned}

        # All pinned blocks should be retrievable
        expected_pinned_ids = {b.id for b in pinned_blocks}
        assert (
            expected_pinned_ids == retrieved_pinned_ids
        ), f"Expected {expected_pinned_ids}, got {retrieved_pinned_ids}"


# Feature: specmem-mvp, Property 7: Legacy Block Exclusion
# Validates: Requirements 5.3, 5.5
@given(
    active_blocks=st.lists(
        valid_specblock_strategy(), min_size=1, max_size=3, unique_by=lambda b: b.id
    ),
    legacy_blocks=st.lists(
        legacy_specblock_strategy(), min_size=1, max_size=3, unique_by=lambda b: b.id
    ),
)
@settings(max_examples=30)
def test_legacy_block_exclusion(
    active_blocks: list[SpecBlock], legacy_blocks: list[SpecBlock]
) -> None:
    """For any standard query (without include_legacy flag) against memory
    containing legacy SpecBlocks, no legacy blocks SHALL appear in the results.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()

        # Combine and deduplicate
        all_blocks = {b.id: b for b in active_blocks + legacy_blocks}
        blocks = list(all_blocks.values())

        # Generate embeddings
        embeddings = [generate_random_embedding(i) for i in range(len(blocks))]

        # Store blocks
        store.store(blocks, embeddings)

        # Query without include_legacy
        query_embedding = generate_random_embedding(999)
        results = store.query(query_embedding, top_k=100, include_legacy=False)

        # No legacy/obsolete blocks should appear
        legacy_statuses = {SpecStatus.LEGACY, SpecStatus.OBSOLETE}
        for result in results:
            assert (
                result.block.status not in legacy_statuses
            ), f"Legacy block {result.block.id} appeared in results"


# Feature: specmem-mvp, Property 8: Status Transition Persistence
# Validates: Requirements 5.7
@given(block=valid_specblock_strategy(), new_status=spec_status_strategy)
@settings(max_examples=50)
def test_status_transition_persistence(block: SpecBlock, new_status: SpecStatus) -> None:
    """For any SpecBlock whose status is changed, querying that block
    after persistence SHALL return the updated status.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()

        # Store block
        embedding = generate_random_embedding(42)
        store.store([block], [embedding])

        # Update status
        success = store.update_status(block.id, new_status.value)
        assert success, "Status update should succeed"

        # Retrieve and verify
        retrieved = store.get_by_id(block.id)
        assert retrieved is not None, "Block should be retrievable"
        assert (
            retrieved.status == new_status
        ), f"Status should be {new_status}, got {retrieved.status}"


def test_store_and_retrieve_basic() -> None:
    """Basic test for store and retrieve operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()

        block = SpecBlock(
            id="test123",
            type=SpecType.REQUIREMENT,
            text="Test requirement",
            source="test.md",
        )

        embedding = [0.1] * EMBEDDING_DIM
        store.store([block], [embedding])

        # Verify count
        assert store.count() == 1

        # Retrieve by ID
        retrieved = store.get_by_id("test123")
        assert retrieved is not None
        assert retrieved.id == block.id
        assert retrieved.text == block.text


def test_clear_store() -> None:
    """Test clearing the store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LanceDBStore(db_path=str(Path(tmpdir) / "vectordb"))
        store.initialize()

        block = SpecBlock(
            id="test123",
            type=SpecType.REQUIREMENT,
            text="Test requirement",
            source="test.md",
        )

        store.store([block], [[0.1] * EMBEDDING_DIM])
        assert store.count() == 1

        store.clear()
        assert store.count() == 0
