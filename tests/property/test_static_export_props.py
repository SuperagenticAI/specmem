"""Property-based tests for static dashboard export.

**Feature: static-dashboard-deploy**
"""

from __future__ import annotations

import json
from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.export.models import (
    ExportBundle,
    ExportMetadata,
    FeatureCoverage,
    GuidelineData,
    HealthBreakdown,
    HistoryEntry,
    SpecData,
)


# Strategies for generating test data
@st.composite
def feature_coverage_strategy(draw: st.DrawFn) -> FeatureCoverage:
    """Generate random FeatureCoverage."""
    total = draw(st.integers(min_value=0, max_value=100))
    tested = draw(st.integers(min_value=0, max_value=total))
    coverage = (tested / total * 100) if total > 0 else 0.0
    return FeatureCoverage(
        feature_name=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N")))),
        coverage_percentage=coverage,
        tested_count=tested,
        total_count=total,
    )


@st.composite
def health_breakdown_strategy(draw: st.DrawFn) -> HealthBreakdown:
    """Generate random HealthBreakdown."""
    return HealthBreakdown(
        category=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L",)))),
        score=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        weight=draw(st.floats(min_value=0, max_value=1, allow_nan=False)),
    )


@st.composite
def spec_data_strategy(draw: st.DrawFn) -> SpecData:
    """Generate random SpecData."""
    total = draw(st.integers(min_value=0, max_value=50))
    completed = draw(st.integers(min_value=0, max_value=total))
    return SpecData(
        name=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "Pd")))),
        path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "Pd", "Pc")))),
        requirements=draw(st.text(min_size=1, max_size=500)),
        design=draw(st.one_of(st.none(), st.text(min_size=1, max_size=500))),
        tasks=draw(st.one_of(st.none(), st.text(min_size=1, max_size=500))),
        task_total=total,
        task_completed=completed,
    )


@st.composite
def guideline_data_strategy(draw: st.DrawFn) -> GuidelineData:
    """Generate random GuidelineData."""
    return GuidelineData(
        name=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N")))),
        path=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "Pd", "Pc")))),
        content=draw(st.text(min_size=1, max_size=500)),
        source_format=draw(st.sampled_from(["kiro", "claude", "cursor"])),
    )


@st.composite
def history_entry_strategy(draw: st.DrawFn) -> HistoryEntry:
    """Generate random HistoryEntry."""
    return HistoryEntry(
        timestamp=datetime.now(),
        coverage_percentage=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        health_score=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        validation_errors=draw(st.integers(min_value=0, max_value=100)),
    )


@st.composite
def export_metadata_strategy(draw: st.DrawFn) -> ExportMetadata:
    """Generate random ExportMetadata."""
    return ExportMetadata(
        generated_at=datetime.now(),
        commit_sha=draw(st.one_of(st.none(), st.text(min_size=7, max_size=12, alphabet="0123456789abcdef"))),
        branch=draw(st.one_of(st.none(), st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N", "Pd"))))),
        specmem_version=draw(st.text(min_size=1, max_size=20, alphabet="0123456789.")),
    )


@st.composite
def export_bundle_strategy(draw: st.DrawFn) -> ExportBundle:
    """Generate random ExportBundle."""
    return ExportBundle(
        metadata=draw(export_metadata_strategy()),
        coverage_percentage=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        features=draw(st.lists(feature_coverage_strategy(), min_size=0, max_size=10)),
        health_score=draw(st.floats(min_value=0, max_value=100, allow_nan=False)),
        health_grade=draw(st.sampled_from(["A", "B", "C", "D", "F", "N/A"])),
        health_breakdown=draw(st.lists(health_breakdown_strategy(), min_size=0, max_size=5)),
        validation_errors=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)),
        validation_warnings=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)),
        specs=draw(st.lists(spec_data_strategy(), min_size=0, max_size=5)),
        guidelines=draw(st.lists(guideline_data_strategy(), min_size=0, max_size=5)),
        history=draw(st.one_of(st.none(), st.lists(history_entry_strategy(), min_size=0, max_size=10))),
    )


class TestExportCompleteness:
    """Property tests for export data completeness.

    **Feature: static-dashboard-deploy, Property 1: Export data completeness**
    **Validates: Requirements 1.1, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
    """

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_export_contains_all_required_keys(self, bundle: ExportBundle) -> None:
        """For any valid export bundle, the JSON output contains all required keys."""
        data = bundle.to_dict()

        required_keys = {"metadata", "coverage", "health", "validation", "specs", "guidelines"}
        assert required_keys.issubset(data.keys()), f"Missing keys: {required_keys - data.keys()}"

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_metadata_contains_required_fields(self, bundle: ExportBundle) -> None:
        """For any export, metadata contains all required fields."""
        data = bundle.to_dict()
        metadata = data["metadata"]

        required_fields = {"generated_at", "commit_sha", "branch", "specmem_version"}
        assert required_fields.issubset(metadata.keys())

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_coverage_contains_required_fields(self, bundle: ExportBundle) -> None:
        """For any export, coverage contains required fields."""
        data = bundle.to_dict()
        coverage = data["coverage"]

        assert "coverage_percentage" in coverage
        assert "features" in coverage
        assert isinstance(coverage["features"], list)

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_health_contains_required_fields(self, bundle: ExportBundle) -> None:
        """For any export, health contains required fields."""
        data = bundle.to_dict()
        health = data["health"]

        assert "overall_score" in health
        assert "letter_grade" in health
        assert "breakdown" in health

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_validation_contains_required_fields(self, bundle: ExportBundle) -> None:
        """For any export, validation contains required fields."""
        data = bundle.to_dict()
        validation = data["validation"]

        assert "errors" in validation
        assert "warnings" in validation


class TestExportRoundTrip:
    """Property tests for export round-trip consistency.

    **Feature: static-dashboard-deploy, Property 2: Export round-trip consistency**
    **Validates: Requirements 1.1**
    """

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_json_round_trip(self, bundle: ExportBundle) -> None:
        """For any export bundle, JSON serialization round-trip preserves data."""
        data = bundle.to_dict()

        # Serialize to JSON string
        json_str = json.dumps(data)

        # Deserialize back
        restored = json.loads(json_str)

        # Verify structure is preserved
        assert restored.keys() == data.keys()
        assert restored["metadata"] == data["metadata"]
        assert restored["coverage"] == data["coverage"]
        assert restored["health"] == data["health"]
        assert restored["validation"] == data["validation"]
        assert len(restored["specs"]) == len(data["specs"])
        assert len(restored["guidelines"]) == len(data["guidelines"])

    @given(entry=history_entry_strategy())
    @settings(max_examples=100)
    def test_history_entry_round_trip(self, entry: HistoryEntry) -> None:
        """For any history entry, to_dict/from_dict round-trip preserves data."""
        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)

        assert restored.coverage_percentage == entry.coverage_percentage
        assert restored.health_score == entry.health_score
        assert restored.validation_errors == entry.validation_errors


import tempfile
from pathlib import Path

from specmem.export.history import HistoryManager


class TestHistoryAppend:
    """Property tests for history append consistency.

    **Feature: static-dashboard-deploy, Property 8: History append consistency**
    **Validates: Requirements 7.1**
    """

    @given(
        initial_count=st.integers(min_value=0, max_value=20),
        bundle=export_bundle_strategy(),
    )
    @settings(max_examples=100)
    def test_append_increases_count_by_one(
        self, initial_count: int, bundle: ExportBundle
    ) -> None:
        """For any history with N entries, appending results in N+1 entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            manager = HistoryManager(history_file, limit=100)  # High limit to avoid truncation

            # Create initial history
            initial_entries = [
                HistoryEntry(
                    timestamp=datetime.now(),
                    coverage_percentage=50.0,
                    health_score=75.0,
                    validation_errors=0,
                )
                for _ in range(initial_count)
            ]
            if initial_entries:
                manager.save(initial_entries)

            # Append new entry
            result = manager.append(bundle)

            # Verify count increased by 1
            assert len(result) == initial_count + 1

    @given(bundle=export_bundle_strategy())
    @settings(max_examples=100)
    def test_append_preserves_existing_entries(self, bundle: ExportBundle) -> None:
        """Appending preserves existing history entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            manager = HistoryManager(history_file, limit=100)

            # Create initial history with known values
            initial_entries = [
                HistoryEntry(
                    timestamp=datetime.now(),
                    coverage_percentage=42.0,
                    health_score=88.0,
                    validation_errors=3,
                )
            ]
            manager.save(initial_entries)

            # Append new entry
            result = manager.append(bundle)

            # Verify original entry is preserved
            assert result[0].coverage_percentage == 42.0
            assert result[0].health_score == 88.0
            assert result[0].validation_errors == 3


class TestHistoryTruncation:
    """Property tests for history truncation.

    **Feature: static-dashboard-deploy, Property 9: History truncation**
    **Validates: Requirements 7.3**
    """

    @given(
        entry_count=st.integers(min_value=0, max_value=100),
        limit=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100)
    def test_truncation_respects_limit(self, entry_count: int, limit: int) -> None:
        """For any history, truncation results in at most limit entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            manager = HistoryManager(history_file, limit=limit)

            entries = [
                HistoryEntry(
                    timestamp=datetime.now(),
                    coverage_percentage=float(i),
                    health_score=float(i),
                    validation_errors=i,
                )
                for i in range(entry_count)
            ]

            result = manager.truncate(entries)

            assert len(result) <= limit

    @given(
        entry_count=st.integers(min_value=35, max_value=100),
    )
    @settings(max_examples=100)
    def test_truncation_keeps_most_recent(self, entry_count: int) -> None:
        """Truncation keeps the most recent entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            history_file = Path(tmpdir) / "history.json"
            limit = 30
            manager = HistoryManager(history_file, limit=limit)

            # Create entries with sequential coverage values
            entries = [
                HistoryEntry(
                    timestamp=datetime.now(),
                    coverage_percentage=float(i),
                    health_score=float(i),
                    validation_errors=i,
                )
                for i in range(entry_count)
            ]

            result = manager.truncate(entries)

            # Most recent entries should be kept (highest indices)
            assert len(result) == limit
            # Last entry should have the highest coverage value
            assert result[-1].coverage_percentage == float(entry_count - 1)


from specmem.export.conflicts import ConflictDetector, CONFLICT_PATTERNS


class TestConflictDetection:
    """Property tests for conflict detection accuracy.

    **Feature: static-dashboard-deploy, Property 3: Conflict detection accuracy**
    **Validates: Requirements 3.1**
    """

    @given(pattern=st.sampled_from(CONFLICT_PATTERNS))
    @settings(max_examples=100)
    def test_detects_known_conflict_patterns(self, pattern: str) -> None:
        """For any known conflict pattern, detector returns a warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            
            # Create the conflict file
            conflict_file = target_dir / pattern
            conflict_file.parent.mkdir(parents=True, exist_ok=True)
            conflict_file.write_text("test content")

            detector = ConflictDetector(target_dir)
            result = detector.detect()

            assert result.has_conflicts
            assert pattern in result.existing_files
            assert len(result.warnings) > 0

    @given(
        patterns=st.lists(
            st.sampled_from(CONFLICT_PATTERNS),
            min_size=1,
            max_size=5,
            unique=True,
        )
    )
    @settings(max_examples=50)
    def test_detects_multiple_conflicts(self, patterns: list[str]) -> None:
        """For multiple conflict patterns, all are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create all conflict files
            for pattern in patterns:
                conflict_file = target_dir / pattern
                conflict_file.write_text("test content")

            detector = ConflictDetector(target_dir)
            result = detector.detect()

            assert result.has_conflicts
            for pattern in patterns:
                assert pattern in result.existing_files

    def test_no_conflicts_in_empty_dir(self) -> None:
        """Empty directory has no conflicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            # Create empty subdirectory
            empty_dir = target_dir / "empty"
            empty_dir.mkdir()

            detector = ConflictDetector(empty_dir)
            result = detector.detect()

            assert len(result.existing_files) == 0
            assert len(result.warnings) == 0


class TestOverwriteProtection:
    """Property tests for overwrite protection.

    **Feature: static-dashboard-deploy, Property 5: Overwrite protection**
    **Validates: Requirements 3.4**
    """

    @given(pattern=st.sampled_from(CONFLICT_PATTERNS))
    @settings(max_examples=50)
    def test_blocks_overwrite_without_force(self, pattern: str) -> None:
        """Deployment fails without force when conflicts exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            
            # Create conflict file
            conflict_file = target_dir / pattern
            conflict_file.write_text("test content")

            detector = ConflictDetector(target_dir)
            is_safe, error = detector.check_overwrite_safe(force=False)

            assert not is_safe
            assert error is not None

    @given(pattern=st.sampled_from(CONFLICT_PATTERNS))
    @settings(max_examples=50)
    def test_allows_overwrite_with_force(self, pattern: str) -> None:
        """Deployment succeeds with force even when conflicts exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            
            # Create conflict file
            conflict_file = target_dir / pattern
            conflict_file.write_text("test content")

            detector = ConflictDetector(target_dir)
            is_safe, error = detector.check_overwrite_safe(force=True)

            assert is_safe
            assert error is None

    def test_allows_deployment_to_empty_dir(self) -> None:
        """Deployment to empty directory is always safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir) / "new_dir"
            # Don't create the directory

            detector = ConflictDetector(target_dir)
            is_safe, error = detector.check_overwrite_safe(force=False)

            assert is_safe
            assert error is None


from specmem.export.filters import (
    FilterCriteria,
    filter_specs,
    search_specs,
    filter_by_status,
    get_spec_status,
    matches_all_criteria,
)


class TestClientSideSearchFiltering:
    """Property tests for client-side search filtering.

    **Feature: static-dashboard-deploy, Property 6: Client-side search filtering**
    **Validates: Requirements 6.1, 6.2**
    """

    @given(
        specs=st.lists(spec_data_strategy(), min_size=1, max_size=10),
        query=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    @settings(max_examples=100)
    def test_search_results_contain_query(
        self, specs: list[SpecData], query: str
    ) -> None:
        """For any search query, all results contain the query in name or content."""
        results = search_specs(specs, query)
        query_lower = query.lower()

        for spec in results:
            found = any([
                query_lower in spec.name.lower(),
                query_lower in spec.path.lower(),
                query_lower in spec.requirements.lower(),
                spec.design and query_lower in spec.design.lower(),
                spec.tasks and query_lower in spec.tasks.lower(),
            ])
            assert found, f"Query '{query}' not found in spec '{spec.name}'"

    @given(specs=st.lists(spec_data_strategy(), min_size=0, max_size=10))
    @settings(max_examples=100)
    def test_empty_query_returns_all(self, specs: list[SpecData]) -> None:
        """Empty query returns all specs."""
        results = search_specs(specs, "")
        assert len(results) == len(specs)

        results = search_specs(specs, "   ")
        assert len(results) == len(specs)

    @given(
        specs=st.lists(spec_data_strategy(), min_size=1, max_size=10),
        query=st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_search_is_case_insensitive(
        self, specs: list[SpecData], query: str
    ) -> None:
        """Search is case-insensitive."""
        results_lower = search_specs(specs, query.lower())
        results_upper = search_specs(specs, query.upper())

        assert len(results_lower) == len(results_upper)


class TestMultiCriteriaFiltering:
    """Property tests for multi-criteria filtering.

    **Feature: static-dashboard-deploy, Property 7: Multi-criteria filtering**
    **Validates: Requirements 6.3**
    """

    @given(
        specs=st.lists(spec_data_strategy(), min_size=1, max_size=10),
        status=st.sampled_from(["complete", "in_progress", "not_started"]),
    )
    @settings(max_examples=100)
    def test_status_filter_matches_criteria(
        self, specs: list[SpecData], status: str
    ) -> None:
        """For any status filter, all results have matching status."""
        results = filter_by_status(specs, status)

        for spec in results:
            assert get_spec_status(spec) == status

    @given(
        specs=st.lists(spec_data_strategy(), min_size=1, max_size=10),
        query=st.one_of(st.none(), st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",)))),
        status=st.one_of(st.none(), st.sampled_from(["complete", "in_progress", "not_started"])),
    )
    @settings(max_examples=100)
    def test_multi_criteria_all_match(
        self, specs: list[SpecData], query: str | None, status: str | None
    ) -> None:
        """For any filter combination, all results match ALL criteria."""
        criteria = FilterCriteria(query=query, status=status)
        results = filter_specs(specs, criteria)

        for spec in results:
            assert matches_all_criteria(spec, criteria)

    @given(specs=st.lists(spec_data_strategy(), min_size=0, max_size=10))
    @settings(max_examples=100)
    def test_empty_criteria_returns_all(self, specs: list[SpecData]) -> None:
        """Empty criteria returns all specs."""
        criteria = FilterCriteria()
        results = filter_specs(specs, criteria)
        assert len(results) == len(specs)


class TestDeployPathConfiguration:
    """Property tests for deploy path configuration.

    **Feature: static-dashboard-deploy, Property 4: Deploy path configuration**
    **Validates: Requirements 3.3**
    """

    @given(
        path=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N", "Pd")),
        )
    )
    @settings(max_examples=100)
    def test_base_path_in_generated_html(self, path: str) -> None:
        """For any valid path, the generated HTML uses that base path."""
        from specmem.cli.export import _generate_static_html

        data = {
            "metadata": {
                "generated_at": "2024-01-01T00:00:00",
                "commit_sha": "abc123",
                "branch": "main",
                "specmem_version": "0.1.0",
            },
            "coverage": {"coverage_percentage": 75.0, "features": []},
            "health": {"overall_score": 80, "letter_grade": "B", "breakdown": []},
            "validation": {"errors": [], "warnings": []},
            "specs": [],
            "guidelines": [],
        }

        base_path = f"/{path}/"
        html = _generate_static_html(data, base_path)

        # Verify base path is in the HTML
        assert f'<base href="{base_path}">' in html

    @given(
        path=st.sampled_from([
            "specmem-dashboard",
            "specs",
            "dashboard",
            "my-project-specs",
            "docs/specs",
        ])
    )
    @settings(max_examples=50)
    def test_common_paths_work(self, path: str) -> None:
        """Common deploy paths generate valid HTML."""
        from specmem.cli.export import _generate_static_html

        data = {
            "metadata": {
                "generated_at": "2024-01-01T00:00:00",
                "commit_sha": None,
                "branch": None,
                "specmem_version": "0.1.0",
            },
            "coverage": {"coverage_percentage": 0, "features": []},
            "health": {"overall_score": 0, "letter_grade": "N/A", "breakdown": []},
            "validation": {"errors": [], "warnings": []},
            "specs": [],
            "guidelines": [],
        }

        base_path = f"/{path}/"
        html = _generate_static_html(data, base_path)

        # Verify it's valid HTML
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert f'<base href="{base_path}">' in html
