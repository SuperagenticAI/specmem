"""Property-based tests for vector store backends.

Tests correctness properties defined in the pluggable-vectordb design document.
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.core.specir import SpecBlock, SpecStatus, SpecType
from specmem.vectordb.base import GovernanceRules
from specmem.vectordb.lancedb_store import LanceDBStore


# Strategies for generating test data
spec_type_strategy = st.sampled_from(list(SpecType))
spec_status_strategy = st.sampled_from(
    [SpecStatus.ACTIVE, SpecStatus.DEPRECATED, SpecStatus.LEGACY]
)


def create_test_block(
    block_id: str = "test-1",
    status: SpecStatus = SpecStatus.ACTIVE,
    spec_type: SpecType = SpecType.REQUIREMENT,
    text: str = "Test specification content",
) -> SpecBlock:
    """Create a test SpecBlock."""
    return SpecBlock(
        id=block_id,
        type=spec_type,
        text=text,
        source="test.md",
        status=status,
        tags=["test"],
        links=[],
        pinned=False,
    )


def create_test_embedding(dim: int = 384) -> list[float]:
    """Create a test embedding vector."""
    return [0.1] * dim


class TestDeprecatedBlockExclusion:
    """**Feature: pluggable-vectordb, Property 4: Deprecated blocks excluded by default**"""

    def test_deprecated_excluded_by_default(self, tmp_path: Path):
        """Deprecated blocks are excluded when include_deprecated=False.

        **Validates: Requirements 4.3**
        """
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        # Create blocks with different statuses
        blocks = [
            create_test_block("active-1", SpecStatus.ACTIVE, text="Active block"),
            create_test_block("deprecated-1", SpecStatus.DEPRECATED, text="Deprecated block"),
        ]
        embeddings = [create_test_embedding(), create_test_embedding()]

        store.store(blocks, embeddings)

        # Query without include_deprecated
        results = store.query(create_test_embedding(), top_k=10, include_deprecated=False)

        # Should only return active block
        result_ids = [r.block.id for r in results]
        assert "active-1" in result_ids
        assert "deprecated-1" not in result_ids

    def test_deprecated_included_when_flag_set(self, tmp_path: Path):
        """Deprecated blocks are included when include_deprecated=True."""
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [
            create_test_block("active-1", SpecStatus.ACTIVE, text="Active block"),
            create_test_block("deprecated-1", SpecStatus.DEPRECATED, text="Deprecated block"),
        ]
        embeddings = [create_test_embedding(), create_test_embedding()]

        store.store(blocks, embeddings)

        # Query with include_deprecated=True
        results = store.query(create_test_embedding(), top_k=10, include_deprecated=True)

        result_ids = [r.block.id for r in results]
        assert "active-1" in result_ids
        assert "deprecated-1" in result_ids

    def test_deprecated_blocks_have_warning(self, tmp_path: Path):
        """Deprecated blocks include deprecation warning in results."""
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [create_test_block("deprecated-1", SpecStatus.DEPRECATED)]
        embeddings = [create_test_embedding()]

        store.store(blocks, embeddings)

        results = store.query(create_test_embedding(), top_k=10, include_deprecated=True)

        assert len(results) == 1
        assert results[0].deprecation_warning is not None
        assert "deprecated" in results[0].deprecation_warning.lower()


class TestLegacyBlockExclusion:
    """**Feature: pluggable-vectordb, Property 5: Legacy blocks excluded by default**"""

    def test_legacy_excluded_by_default(self, tmp_path: Path):
        """Legacy blocks are excluded when include_legacy=False.

        **Validates: Requirements 5.1**
        """
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [
            create_test_block("active-1", SpecStatus.ACTIVE, text="Active block"),
            create_test_block("legacy-1", SpecStatus.LEGACY, text="Legacy block"),
        ]
        embeddings = [create_test_embedding(), create_test_embedding()]

        store.store(blocks, embeddings)

        results = store.query(create_test_embedding(), top_k=10, include_legacy=False)

        result_ids = [r.block.id for r in results]
        assert "active-1" in result_ids
        assert "legacy-1" not in result_ids

    def test_legacy_included_when_flag_set(self, tmp_path: Path):
        """Legacy blocks are included when include_legacy=True."""
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [
            create_test_block("active-1", SpecStatus.ACTIVE, text="Active block"),
            create_test_block("legacy-1", SpecStatus.LEGACY, text="Legacy block"),
        ]
        embeddings = [create_test_embedding(), create_test_embedding()]

        store.store(blocks, embeddings)

        results = store.query(create_test_embedding(), top_k=10, include_legacy=True)

        result_ids = [r.block.id for r in results]
        assert "active-1" in result_ids
        assert "legacy-1" in result_ids


class TestObsoleteBlockNeverReturned:
    """**Feature: pluggable-vectordb, Property 6: Obsolete blocks never returned**"""

    def test_obsolete_never_returned(self, tmp_path: Path):
        """Obsolete blocks are never returned regardless of flags.

        **Validates: Requirements 6.2**
        """
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        # Create active block first
        blocks = [
            create_test_block("active-1", SpecStatus.ACTIVE, text="Active block"),
            create_test_block("legacy-1", SpecStatus.LEGACY, text="Legacy block"),
        ]
        embeddings = [create_test_embedding(), create_test_embedding()]

        store.store(blocks, embeddings)

        # Transition legacy to obsolete
        store.update_status("legacy-1", SpecStatus.OBSOLETE, reason="Test obsolescence")

        # Query with all flags enabled
        results = store.query(
            create_test_embedding(),
            top_k=10,
            include_deprecated=True,
            include_legacy=True,
        )

        result_ids = [r.block.id for r in results]
        assert "active-1" in result_ids
        assert "legacy-1" not in result_ids  # Obsolete, should not be returned


class TestAuditLog:
    """**Feature: pluggable-vectordb, Property 9: Audit log contains obsolete blocks**"""

    def test_obsolete_blocks_in_audit_log(self, tmp_path: Path):
        """Blocks transitioned to obsolete appear in audit log.

        **Validates: Requirements 6.1, 6.3**
        """
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [create_test_block("legacy-1", SpecStatus.LEGACY, text="Legacy block")]
        embeddings = [create_test_embedding()]

        store.store(blocks, embeddings)

        # Transition to obsolete
        store.update_status("legacy-1", SpecStatus.OBSOLETE, reason="No longer needed")

        # Check audit log
        audit_entries = store.get_audit_log()

        assert len(audit_entries) == 1
        assert audit_entries[0].block.id == "legacy-1"
        assert audit_entries[0].reason == "No longer needed"
        assert audit_entries[0].previous_status == SpecStatus.LEGACY

    def test_audit_log_preserves_block_data(self, tmp_path: Path):
        """Audit log preserves complete block data."""
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        original_block = SpecBlock(
            id="test-block",
            type=SpecType.DESIGN,
            text="Important design decision",
            source="design.md",
            status=SpecStatus.LEGACY,
            tags=["architecture", "important"],
            links=["req-1", "req-2"],
            pinned=True,
        )

        store.store([original_block], [create_test_embedding()])
        store.update_status("test-block", SpecStatus.OBSOLETE, reason="Superseded")

        audit_entries = store.get_audit_log()

        assert len(audit_entries) == 1
        archived = audit_entries[0].block
        assert archived.id == original_block.id
        assert archived.type == original_block.type
        assert archived.text == original_block.text
        assert archived.source == original_block.source


class TestGovernanceRules:
    """**Feature: pluggable-vectordb, Property 10: Governance rules filter results**"""

    def test_exclude_types_filter(self, tmp_path: Path):
        """Governance rules exclude specified types.

        **Validates: Requirements 9.2**
        """
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [
            create_test_block("req-1", spec_type=SpecType.REQUIREMENT, text="Requirement"),
            create_test_block("design-1", spec_type=SpecType.DESIGN, text="Design"),
            create_test_block("task-1", spec_type=SpecType.TASK, text="Task"),
        ]
        embeddings = [create_test_embedding() for _ in blocks]

        store.store(blocks, embeddings)

        # Exclude TASK type
        rules = GovernanceRules(exclude_types=[SpecType.TASK])
        results = store.query(create_test_embedding(), top_k=10, governance_rules=rules)

        result_types = [r.block.type for r in results]
        assert SpecType.TASK not in result_types
        assert SpecType.REQUIREMENT in result_types
        assert SpecType.DESIGN in result_types

    def test_exclude_sources_filter(self, tmp_path: Path):
        """Governance rules exclude specified sources.

        **Validates: Requirements 9.3**
        """
        store = LanceDBStore(db_path=str(tmp_path / "test_db"))
        store.initialize()

        blocks = [
            SpecBlock(
                id="b1",
                type=SpecType.REQUIREMENT,
                text="Block 1",
                source="keep.md",
                status=SpecStatus.ACTIVE,
            ),
            SpecBlock(
                id="b2",
                type=SpecType.REQUIREMENT,
                text="Block 2",
                source="exclude.md",
                status=SpecStatus.ACTIVE,
            ),
        ]
        embeddings = [create_test_embedding() for _ in blocks]

        store.store(blocks, embeddings)

        rules = GovernanceRules(exclude_sources=["exclude.md"])
        results = store.query(create_test_embedding(), top_k=10, governance_rules=rules)

        result_sources = [r.block.source for r in results]
        assert "keep.md" in result_sources
        assert "exclude.md" not in result_sources


class TestVectorStoreFactory:
    """**Feature: pluggable-vectordb, Property 1: Factory returns correct backend type**"""

    def test_factory_returns_lancedb(self, tmp_path: Path):
        """Factory returns LanceDBStore for 'lancedb' backend.

        **Validates: Requirements 1.1**
        """
        from specmem.vectordb import get_vector_store
        from specmem.vectordb.lancedb_store import LanceDBStore

        store = get_vector_store(backend="lancedb", path=str(tmp_path / "lance"))
        assert isinstance(store, LanceDBStore)

    def test_factory_returns_chroma(self, tmp_path: Path):
        """Factory returns ChromaDBStore for 'chroma' backend.

        **Validates: Requirements 1.2**
        """
        pytest.importorskip("chromadb")
        from specmem.vectordb import get_vector_store
        from specmem.vectordb.chroma_store import ChromaDBStore

        store = get_vector_store(backend="chroma", path=str(tmp_path / "chroma"))
        assert isinstance(store, ChromaDBStore)

    def test_factory_returns_qdrant(self, tmp_path: Path):
        """Factory returns QdrantStore for 'qdrant' backend.

        **Validates: Requirements 1.3**
        """
        pytest.importorskip("qdrant_client")
        from specmem.vectordb import get_vector_store
        from specmem.vectordb.qdrant_store import QdrantStore

        store = get_vector_store(backend="qdrant", path=str(tmp_path / "qdrant"))
        assert isinstance(store, QdrantStore)


class TestUnknownBackendError:
    """**Feature: pluggable-vectordb, Property 2: Unknown backend raises error**"""

    @given(
        backend_name=st.text(min_size=1, max_size=20).filter(
            lambda x: x
            not in {"lancedb", "chroma", "qdrant", "weaviate", "milvus", "agentvectordb"}
        )
    )
    @settings(max_examples=50)
    def test_unknown_backend_raises_error(self, backend_name: str):
        """Unknown backend names raise VectorStoreError.

        **Validates: Requirements 2.3**
        """
        from specmem.core.exceptions import VectorStoreError
        from specmem.vectordb import get_vector_store

        with pytest.raises(VectorStoreError) as exc_info:
            get_vector_store(backend=backend_name)

        assert exc_info.value.code == "UNSUPPORTED_BACKEND"
        assert exc_info.value.details["backend"] == backend_name
        assert "supported" in exc_info.value.details
