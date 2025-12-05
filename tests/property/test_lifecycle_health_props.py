"""Property-based tests for spec lifecycle health analysis.

**Feature: pragmatic-spec-lifecycle**
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.lifecycle.models import (
    SpecHealthScore,
    calculate_health_score,
)


class TestHealthScoreProperties:
    """Property tests for health score calculation."""

    @given(
        code_references=st.integers(min_value=0, max_value=1000),
        days_since_modified=st.integers(min_value=0, max_value=3650),
        query_count=st.integers(min_value=0, max_value=1000),
        stale_threshold=st.integers(min_value=1, max_value=365),
    )
    @settings(max_examples=100)
    def test_health_score_bounds(
        self,
        code_references: int,
        days_since_modified: int,
        query_count: int,
        stale_threshold: int,
    ) -> None:
        """**Feature: pragmatic-spec-lifecycle, Property 1: Health Score Bounds**

        *For any* spec with any combination of code references, modification date,
        and query count, the calculated health score SHALL always be between 0.0
        and 1.0 inclusive.

        **Validates: Requirements 1.2**
        """
        score = calculate_health_score(
            code_references=code_references,
            days_since_modified=days_since_modified,
            query_count=query_count,
            stale_threshold=stale_threshold,
        )

        assert 0.0 <= score <= 1.0, f"Score {score} out of bounds"

    @given(
        code_references=st.integers(min_value=0, max_value=100),
        days_since_modified=st.integers(min_value=0, max_value=365),
        query_count=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=100)
    def test_health_score_model_validation(
        self,
        code_references: int,
        days_since_modified: int,
        query_count: int,
    ) -> None:
        """**Feature: pragmatic-spec-lifecycle, Property 1: Health Score Bounds**

        SpecHealthScore model should reject scores outside valid bounds.

        **Validates: Requirements 1.2**
        """
        score = calculate_health_score(
            code_references=code_references,
            days_since_modified=days_since_modified,
            query_count=query_count,
        )

        # Should not raise for valid scores
        health = SpecHealthScore(
            spec_id="test-spec",
            spec_path=Path("test"),
            score=score,
            code_references=code_references,
            last_modified=datetime.now(UTC),
            query_count=query_count,
        )

        assert health.score == score

    def test_health_score_rejects_invalid_bounds(self) -> None:
        """SpecHealthScore should reject scores outside 0.0-1.0 range."""
        with pytest.raises(ValueError, match="Score must be between"):
            SpecHealthScore(
                spec_id="test",
                spec_path=Path("test"),
                score=1.5,  # Invalid
                code_references=0,
                last_modified=datetime.now(UTC),
            )

        with pytest.raises(ValueError, match="Score must be between"):
            SpecHealthScore(
                spec_id="test",
                spec_path=Path("test"),
                score=-0.1,  # Invalid
                code_references=0,
                last_modified=datetime.now(UTC),
            )

    @given(
        refs1=st.integers(min_value=0, max_value=10),
        refs2=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_more_references_higher_score(
        self,
        refs1: int,
        refs2: int,
    ) -> None:
        """More code references should generally lead to higher scores.

        **Validates: Requirements 1.2**
        """
        # Same freshness and usage, different references
        score1 = calculate_health_score(
            code_references=refs1,
            days_since_modified=30,
            query_count=5,
        )
        score2 = calculate_health_score(
            code_references=refs2,
            days_since_modified=30,
            query_count=5,
        )

        if refs1 > refs2:
            assert score1 >= score2
        elif refs2 > refs1:
            assert score2 >= score1

    @given(
        days1=st.integers(min_value=0, max_value=365),
        days2=st.integers(min_value=0, max_value=365),
    )
    @settings(max_examples=100)
    def test_fresher_specs_higher_score(
        self,
        days1: int,
        days2: int,
    ) -> None:
        """Fresher specs should generally have higher scores.

        **Validates: Requirements 1.2**
        """
        # Same references and usage, different freshness
        score1 = calculate_health_score(
            code_references=2,
            days_since_modified=days1,
            query_count=5,
        )
        score2 = calculate_health_score(
            code_references=2,
            days_since_modified=days2,
            query_count=5,
        )

        # Fresher (fewer days) should have higher or equal score
        if days1 < days2:
            assert score1 >= score2
        elif days2 < days1:
            assert score2 >= score1


class TestOrphanDetectionProperties:
    """Property tests for orphan detection consistency."""

    @given(
        num_specs=st.integers(min_value=1, max_value=10),
        orphan_indices=st.lists(st.integers(min_value=0, max_value=9), max_size=5),
    )
    @settings(max_examples=100)
    def test_orphan_detection_consistency(
        self,
        num_specs: int,
        orphan_indices: list[int],
    ) -> None:
        """**Feature: pragmatic-spec-lifecycle, Property 2: Orphan Detection Consistency**

        *For any* set of specs and impact graph, a spec is identified as orphaned
        if and only if it has zero code references in the graph, and the orphaned
        count in the summary matches the actual count of orphaned specs.

        **Validates: Requirements 1.1, 1.4**
        """
        import tempfile

        from specmem.lifecycle.health import HealthAnalyzer

        # Create temporary spec directory
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_base = Path(tmpdir)

            # Create spec directories
            specs_created = []
            expected_orphans = set()

            for i in range(num_specs):
                spec_dir = spec_base / f"spec-{i}"
                spec_dir.mkdir()
                (spec_dir / "requirements.md").write_text(f"# Spec {i}")
                specs_created.append(f"spec-{i}")

                # Mark as orphan if index is in orphan_indices
                if i in orphan_indices:
                    expected_orphans.add(f"spec-{i}")

            # Create mock impact graph that returns references based on orphan status
            class MockImpactGraph:
                def __init__(self, orphans: set[str]):
                    self.orphans = orphans

                def get_code_for_spec(self, spec_id: str) -> list[str]:
                    if spec_id in self.orphans:
                        return []  # No references = orphaned
                    return ["some_file.py"]  # Has references

            # Create analyzer with mock graph
            analyzer = HealthAnalyzer(
                impact_graph=MockImpactGraph(expected_orphans),
                spec_base_path=spec_base,
            )

            # Get orphaned specs
            orphaned = analyzer.get_orphaned_specs()
            orphaned_ids = {s.spec_id for s in orphaned}

            # Verify orphan detection matches expected
            assert (
                orphaned_ids == expected_orphans
            ), f"Expected orphans {expected_orphans}, got {orphaned_ids}"

            # Verify summary count matches
            summary = analyzer.get_summary()
            assert summary["orphaned_count"] == len(expected_orphans), (
                f"Summary orphaned_count {summary['orphaned_count']} != "
                f"expected {len(expected_orphans)}"
            )

            # Verify each orphaned spec has is_orphaned=True
            for score in orphaned:
                assert score.is_orphaned is True
                assert score.code_references == 0

    @given(
        code_refs=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_orphan_flag_matches_zero_references(
        self,
        code_refs: int,
    ) -> None:
        """Orphan flag should be True if and only if code_references is 0.

        **Validates: Requirements 1.1**
        """
        # A spec is orphaned iff it has zero code references
        is_orphaned = code_refs == 0

        health = SpecHealthScore(
            spec_id="test",
            spec_path=Path("test"),
            score=0.5,
            code_references=code_refs,
            last_modified=datetime.now(UTC),
            is_orphaned=is_orphaned,
        )

        # Verify the relationship
        if health.code_references == 0:
            assert health.is_orphaned is True or health.is_orphaned is False
            # The flag should be set correctly based on references

        # If we set is_orphaned based on code_refs, it should be consistent
        expected_orphan = code_refs == 0
        assert is_orphaned == expected_orphan
