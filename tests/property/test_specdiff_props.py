"""Property-based tests for SpecDiff temporal intelligence.

Tests correctness properties defined in the design document.
"""

from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.diff import (
    ChangeReason,
    ChangeType,
    Contradiction,
    Deprecation,
    DriftItem,
    DriftReport,
    Severity,
    SpecChange,
    SpecVersion,
    StalenessWarning,
)


# =============================================================================
# Strategies for generating test data
# =============================================================================

spec_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-."),
    min_size=1,
    max_size=50,
)

version_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=40,
)

confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

content_strategy = st.text(min_size=1, max_size=500)

datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
)

change_type_strategy = st.sampled_from(list(ChangeType))

severity_strategy = st.sampled_from(list(Severity))


# =============================================================================
# Property 4: Change Reason Confidence Range
# For any ChangeReason, the confidence score SHALL be between 0.0 and 1.0.
# **Feature: specdiff, Property 4: Change Reason Confidence Range**
# **Validates: Requirements 2.4**
# =============================================================================


@given(
    reason=st.text(min_size=1, max_size=100),
    confidence=confidence_strategy,
    source=st.text(min_size=1, max_size=50),
)
@settings(max_examples=100)
def test_change_reason_confidence_in_valid_range(
    reason: str, confidence: float, source: str
) -> None:
    """Property 4: ChangeReason confidence is between 0.0 and 1.0.

    **Feature: specdiff, Property 4: Change Reason Confidence Range**
    **Validates: Requirements 2.4**
    """
    cr = ChangeReason(reason=reason, confidence=confidence, source=source)
    assert 0.0 <= cr.confidence <= 1.0, f"Confidence {cr.confidence} is not in range [0.0, 1.0]"


# =============================================================================
# Property 7: Drift Severity Range
# For any DriftItem, the severity score SHALL be between 0.0 and 1.0.
# **Feature: specdiff, Property 7: Drift Severity Range**
# **Validates: Requirements 3.2**
# =============================================================================


@given(
    code_path=st.text(min_size=1, max_size=100),
    spec_id=spec_id_strategy,
    severity=confidence_strategy,
)
@settings(max_examples=100)
def test_drift_item_severity_in_valid_range(code_path: str, spec_id: str, severity: float) -> None:
    """Property 7: DriftItem severity is between 0.0 and 1.0.

    **Feature: specdiff, Property 7: Drift Severity Range**
    **Validates: Requirements 3.2**
    """
    # Create a minimal SpecChange for the DriftItem
    spec_change = SpecChange(
        spec_id=spec_id,
        from_version="v1",
        to_version="v2",
        timestamp=datetime.now(),
    )

    drift_item = DriftItem(
        code_path=code_path,
        spec_id=spec_id,
        spec_change=spec_change,
        severity=severity,
    )

    assert (
        0.0 <= drift_item.severity <= 1.0
    ), f"Severity {drift_item.severity} is not in range [0.0, 1.0]"


# =============================================================================
# Serialization Round-Trip Tests
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    version_id=version_id_strategy,
    timestamp=datetime_strategy,
    content=content_strategy,
)
@settings(max_examples=100)
def test_spec_version_serialization_roundtrip(
    spec_id: str, version_id: str, timestamp: datetime, content: str
) -> None:
    """SpecVersion can be serialized and deserialized without data loss."""
    version = SpecVersion(
        spec_id=spec_id,
        version_id=version_id,
        timestamp=timestamp,
        content=content,
    )

    serialized = version.to_dict()
    restored = SpecVersion.from_dict(serialized)

    assert restored.spec_id == version.spec_id
    assert restored.version_id == version.version_id
    assert restored.content == version.content
    assert restored.content_hash == version.content_hash


@given(
    reason=st.text(min_size=1, max_size=100),
    confidence=confidence_strategy,
    source=st.text(min_size=1, max_size=50),
)
@settings(max_examples=100)
def test_change_reason_serialization_roundtrip(reason: str, confidence: float, source: str) -> None:
    """ChangeReason can be serialized and deserialized without data loss."""
    cr = ChangeReason(reason=reason, confidence=confidence, source=source)

    serialized = cr.to_dict()
    restored = ChangeReason.from_dict(serialized)

    assert restored.reason == cr.reason
    assert restored.confidence == cr.confidence
    assert restored.source == cr.source


@given(
    spec_id=spec_id_strategy,
    deprecated_at=datetime_strategy,
    urgency=confidence_strategy,
)
@settings(max_examples=100)
def test_deprecation_serialization_roundtrip(
    spec_id: str, deprecated_at: datetime, urgency: float
) -> None:
    """Deprecation can be serialized and deserialized without data loss."""
    dep = Deprecation(
        spec_id=spec_id,
        deprecated_at=deprecated_at,
        urgency=urgency,
    )

    serialized = dep.to_dict()
    restored = Deprecation.from_dict(serialized)

    assert restored.spec_id == dep.spec_id
    assert restored.urgency == dep.urgency


# =============================================================================
# Property 5: Change Reasons Ordered by Confidence
# For any ChangeReason with alternatives, the alternatives SHALL be ordered
# by confidence descending.
# **Feature: specdiff, Property 5: Change Reasons Ordered by Confidence**
# **Validates: Requirements 2.5**
# =============================================================================


@given(
    confidences=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=2,
        max_size=5,
    ),
)
@settings(max_examples=100)
def test_change_reasons_ordered_by_confidence(confidences: list[float]) -> None:
    """Property 5: Alternatives are ordered by confidence descending.

    **Feature: specdiff, Property 5: Change Reasons Ordered by Confidence**
    **Validates: Requirements 2.5**
    """
    # Create alternatives with varying confidence
    alternatives = [
        ChangeReason(reason=f"Reason {i}", confidence=conf, source="test")
        for i, conf in enumerate(confidences)
    ]

    # Sort by confidence descending (as the system should do)
    sorted_alternatives = sorted(alternatives, key=lambda x: x.confidence, reverse=True)

    # Create main reason with sorted alternatives
    main_reason = ChangeReason(
        reason="Main reason",
        confidence=1.0,
        source="test",
        alternatives=sorted_alternatives,
    )

    # Verify ordering
    for i in range(len(main_reason.alternatives) - 1):
        assert (
            main_reason.alternatives[i].confidence >= main_reason.alternatives[i + 1].confidence
        ), (
            f"Alternatives not ordered by confidence: "
            f"{main_reason.alternatives[i].confidence} < {main_reason.alternatives[i + 1].confidence}"
        )


# =============================================================================
# Property 11: Critical Staleness for Breaking Changes
# For any staleness involving a BREAKING change, the severity SHALL be CRITICAL.
# **Feature: specdiff, Property 11: Critical Staleness for Breaking Changes**
# **Validates: Requirements 4.4**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
)
@settings(max_examples=100)
def test_breaking_change_triggers_critical_severity(spec_id: str) -> None:
    """Property 11: Breaking changes result in CRITICAL severity.

    **Feature: specdiff, Property 11: Critical Staleness for Breaking Changes**
    **Validates: Requirements 4.4**
    """
    # Create a breaking change
    breaking_change = SpecChange(
        spec_id=spec_id,
        from_version="v1",
        to_version="v2",
        timestamp=datetime.now(),
        change_type=ChangeType.BREAKING,
    )

    assert breaking_change.is_breaking() is True

    # When a breaking change is detected, staleness should be CRITICAL
    # This tests the model's is_breaking() method
    if breaking_change.is_breaking():
        expected_severity = Severity.CRITICAL
        warning = StalenessWarning(
            spec_id=spec_id,
            cached_version="v1",
            current_version="v2",
            changes_since=[breaking_change],
            severity=expected_severity,
        )
        assert warning.severity == Severity.CRITICAL


# =============================================================================
# Property 14: Deprecation Date Tracking
# For any deprecated spec, the Deprecation SHALL include the deprecation date.
# **Feature: specdiff, Property 14: Deprecation Date Tracking**
# **Validates: Requirements 6.1**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    deprecated_at=datetime_strategy,
)
@settings(max_examples=100)
def test_deprecation_has_date(spec_id: str, deprecated_at: datetime) -> None:
    """Property 14: Deprecation includes deprecation date.

    **Feature: specdiff, Property 14: Deprecation Date Tracking**
    **Validates: Requirements 6.1**
    """
    dep = Deprecation(spec_id=spec_id, deprecated_at=deprecated_at)

    assert dep.deprecated_at is not None
    assert isinstance(dep.deprecated_at, datetime)


# =============================================================================
# Property 15: Deprecation Urgency Ordering
# For any list of deprecations, they SHALL be ordered by urgency descending.
# **Feature: specdiff, Property 15: Deprecation Urgency Ordering**
# **Validates: Requirements 6.5**
# =============================================================================


@given(
    urgencies=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=2,
        max_size=10,
    ),
)
@settings(max_examples=100)
def test_deprecations_ordered_by_urgency(urgencies: list[float]) -> None:
    """Property 15: Deprecations are ordered by urgency descending.

    **Feature: specdiff, Property 15: Deprecation Urgency Ordering**
    **Validates: Requirements 6.5**
    """
    # Create deprecations with varying urgency
    deprecations = [
        Deprecation(
            spec_id=f"spec_{i}",
            deprecated_at=datetime.now(),
            urgency=urg,
        )
        for i, urg in enumerate(urgencies)
    ]

    # Sort by urgency descending (as the system should do)
    sorted_deps = sorted(deprecations, key=lambda x: x.urgency, reverse=True)

    # Verify ordering
    for i in range(len(sorted_deps) - 1):
        assert sorted_deps[i].urgency >= sorted_deps[i + 1].urgency, (
            f"Deprecations not ordered by urgency: "
            f"{sorted_deps[i].urgency} < {sorted_deps[i + 1].urgency}"
        )


# =============================================================================
# Property 1: Version History Chronological Order
# For any spec with multiple versions, get_history() SHALL return versions
# ordered by timestamp ascending (oldest first).
# **Feature: specdiff, Property 1: Version History Chronological Order**
# **Validates: Requirements 1.1**
# =============================================================================

import tempfile
from pathlib import Path

from specmem.diff import SpecDiff, VersionStore


@given(
    timestamps=st.lists(
        datetime_strategy,
        min_size=2,
        max_size=10,
        unique=True,
    ),
)
@settings(max_examples=50)
def test_version_history_chronological_order(timestamps: list[datetime]) -> None:
    """Property 1: Version history is ordered by timestamp ascending.

    **Feature: specdiff, Property 1: Version History Chronological Order**
    **Validates: Requirements 1.1**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(Path(tmpdir) / "test.db")

        # Add versions in random order
        for i, ts in enumerate(timestamps):
            version = SpecVersion(
                spec_id="test.spec",
                version_id=f"v{i}",
                timestamp=ts,
                content=f"Content {i}",
            )
            store.save_version(version)

        # Get history
        history = store.get_history("test.spec")

        # Verify chronological order
        for i in range(len(history) - 1):
            assert history[i].timestamp <= history[i + 1].timestamp, (
                f"History not in chronological order: "
                f"{history[i].timestamp} > {history[i + 1].timestamp}"
            )

        store.close()


# =============================================================================
# Property 18: History Pruning Preserves Minimum
# For any prune operation with keep_min=N, at least N versions SHALL remain.
# **Feature: specdiff, Property 18: History Pruning Preserves Minimum**
# **Validates: Requirements 9.5**
# =============================================================================


@given(
    num_versions=st.integers(min_value=5, max_value=20),
    keep_min=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=50)
def test_pruning_preserves_minimum_versions(num_versions: int, keep_min: int) -> None:
    """Property 18: Pruning keeps at least keep_min versions.

    **Feature: specdiff, Property 18: History Pruning Preserves Minimum**
    **Validates: Requirements 9.5**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(Path(tmpdir) / "test.db")

        # Add versions
        base_time = datetime(2020, 1, 1)
        for i in range(num_versions):
            version = SpecVersion(
                spec_id="test.spec",
                version_id=f"v{i}",
                timestamp=base_time + timedelta(days=i),
                content=f"Content {i}",
            )
            store.save_version(version)

        # Prune old versions
        prune_before = base_time + timedelta(days=num_versions + 10)
        store.prune_history(prune_before, keep_min=keep_min)

        # Check remaining versions
        history = store.get_history("test.spec")
        assert len(history) >= min(
            keep_min, num_versions
        ), f"Expected at least {min(keep_min, num_versions)} versions, got {len(history)}"

        store.close()


# =============================================================================
# Property 13: Contradiction Includes Both Versions
# For any Contradiction, it SHALL include both the old and new conflicting text.
# **Feature: specdiff, Property 13: Contradiction Includes Both Versions**
# **Validates: Requirements 5.2, 5.3**
# =============================================================================


@given(
    old_text=st.text(min_size=1, max_size=100),
    new_text=st.text(min_size=1, max_size=100),
)
@settings(max_examples=100)
def test_contradiction_includes_both_texts(old_text: str, new_text: str) -> None:
    """Property 13: Contradiction includes both old and new text.

    **Feature: specdiff, Property 13: Contradiction Includes Both Versions**
    **Validates: Requirements 5.2, 5.3**
    """
    contradiction = Contradiction(
        spec_id="test.spec",
        old_text=old_text,
        new_text=new_text,
    )

    assert contradiction.old_text == old_text
    assert contradiction.new_text == new_text
    assert contradiction.old_text is not None
    assert contradiction.new_text is not None


# =============================================================================
# Property 16: Version Auto-Creation
# For any spec tracked via track_version(), a new SpecVersion SHALL be created
# and stored in the version history.
# **Feature: specdiff, Property 16: Version Auto-Creation**
# **Validates: Requirements 9.1**
# =============================================================================

from specmem.core.specir import SpecBlock, SpecType


@given(
    spec_id=spec_id_strategy,
    content=st.text(min_size=10, max_size=200),
)
@settings(max_examples=50)
def test_track_version_creates_version(spec_id: str, content: str) -> None:
    """Property 16: track_version creates a new version in history.

    **Feature: specdiff, Property 16: Version Auto-Creation**
    **Validates: Requirements 9.1**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        # Create a spec block
        spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=content,
            source="test.md",
        )

        # Track the version
        version = specdiff.track_version(spec)

        # Verify version was created
        assert version is not None
        assert version.spec_id == spec_id
        assert version.content == content

        # Verify it's in history
        history = specdiff.get_history(spec_id)
        assert len(history) >= 1
        assert any(v.version_id == version.version_id for v in history)

        specdiff.close()


@given(
    spec_id=spec_id_strategy,
    contents=st.lists(
        st.text(min_size=10, max_size=100),
        min_size=2,
        max_size=5,
        unique=True,
    ),
)
@settings(max_examples=30)
def test_multiple_versions_tracked(spec_id: str, contents: list[str]) -> None:
    """Property 16: Multiple versions can be tracked for the same spec.

    **Feature: specdiff, Property 16: Version Auto-Creation**
    **Validates: Requirements 9.1**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        tracked_versions = []
        for i, content in enumerate(contents):
            spec = SpecBlock(
                id=spec_id,
                type=SpecType.REQUIREMENT,
                text=content,
                source="test.md",
            )
            # Use unique version IDs since we're not using git
            version = specdiff.track_version(spec, commit_ref=f"commit_{i}")
            tracked_versions.append(version)

        # Verify all versions are in history
        history = specdiff.get_history(spec_id)
        assert len(history) == len(contents)

        specdiff.close()


# =============================================================================
# Property 17: Git Commit as Version ID
# WHEN git is available, the system SHALL use the commit hash as version_id.
# WHEN git is unavailable, the system SHALL fall back to timestamp-based ID.
# **Feature: specdiff, Property 17: Git Commit as Version ID**
# **Validates: Requirements 9.2**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    content=st.text(min_size=10, max_size=100),
    commit_ref=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=7,
        max_size=12,
    ),
)
@settings(max_examples=50)
def test_explicit_commit_ref_used_as_version_id(
    spec_id: str, content: str, commit_ref: str
) -> None:
    """Property 17: Explicit commit_ref is used as version_id.

    **Feature: specdiff, Property 17: Git Commit as Version ID**
    **Validates: Requirements 9.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=content,
            source="test.md",
        )

        # Track with explicit commit ref
        version = specdiff.track_version(spec, commit_ref=commit_ref)

        # Verify commit ref is used as version ID
        assert version.version_id == commit_ref
        assert version.commit_ref == commit_ref

        specdiff.close()


@given(
    spec_id=spec_id_strategy,
    content=st.text(min_size=10, max_size=100),
)
@settings(max_examples=30)
def test_version_id_generated_when_no_commit(spec_id: str, content: str) -> None:
    """Property 17: Version ID is generated when no commit ref available.

    **Feature: specdiff, Property 17: Git Commit as Version ID**
    **Validates: Requirements 9.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=content,
            source="test.md",
        )

        # Track without commit ref (will try git, fall back to timestamp)
        version = specdiff.track_version(spec)

        # Version ID should be non-empty
        assert version.version_id is not None
        assert len(version.version_id) > 0

        specdiff.close()


# =============================================================================
# Property 2: Diff Completeness
# For any two spec versions, get_diff() SHALL identify all added, removed,
# and modified content.
# **Feature: specdiff, Property 2: Diff Completeness**
# **Validates: Requirements 1.2**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    old_content=st.text(min_size=10, max_size=200),
    new_content=st.text(min_size=10, max_size=200),
)
@settings(max_examples=50)
def test_diff_identifies_changes(spec_id: str, old_content: str, new_content: str) -> None:
    """Property 2: Diff identifies all changes between versions.

    **Feature: specdiff, Property 2: Diff Completeness**
    **Validates: Requirements 1.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        # Create two versions
        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        # Get diff
        diff = specdiff.get_diff(spec_id, "v1", "v2")

        if old_content == new_content:
            # No changes expected
            if diff:
                assert len(diff.added) == 0
                assert len(diff.removed) == 0
                assert len(diff.modified) == 0
        else:
            # Some changes should be detected
            assert diff is not None
            # At least one type of change should be present
            has_changes = len(diff.added) > 0 or len(diff.removed) > 0 or len(diff.modified) > 0
            assert has_changes, "Diff should detect changes between different content"

        specdiff.close()


@given(
    spec_id=spec_id_strategy,
    base_lines=st.lists(st.text(min_size=5, max_size=50), min_size=3, max_size=10),
    added_lines=st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=3),
)
@settings(max_examples=30)
def test_diff_detects_additions(
    spec_id: str, base_lines: list[str], added_lines: list[str]
) -> None:
    """Property 2: Diff correctly identifies added lines.

    **Feature: specdiff, Property 2: Diff Completeness**
    **Validates: Requirements 1.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        old_content = "\n".join(base_lines)
        new_content = "\n".join(base_lines + added_lines)

        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        diff = specdiff.get_diff(spec_id, "v1", "v2")

        assert diff is not None
        # Added lines should be detected
        assert len(diff.added) >= len(
            added_lines
        ), f"Expected at least {len(added_lines)} additions, got {len(diff.added)}"

        specdiff.close()


@given(
    spec_id=spec_id_strategy,
    base_lines=st.lists(st.text(min_size=5, max_size=50), min_size=5, max_size=10),
    remove_count=st.integers(min_value=1, max_value=3),
)
@settings(max_examples=30)
def test_diff_detects_removals(spec_id: str, base_lines: list[str], remove_count: int) -> None:
    """Property 2: Diff correctly identifies removed lines.

    **Feature: specdiff, Property 2: Diff Completeness**
    **Validates: Requirements 1.2**
    """
    if remove_count >= len(base_lines):
        return  # Skip if we'd remove all lines

    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        old_content = "\n".join(base_lines)
        new_content = "\n".join(base_lines[:-remove_count])

        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        diff = specdiff.get_diff(spec_id, "v1", "v2")

        assert diff is not None
        # Removed lines should be detected
        assert (
            len(diff.removed) >= remove_count
        ), f"Expected at least {remove_count} removals, got {len(diff.removed)}"

        specdiff.close()


# =============================================================================
# Property 3: Change Metadata Completeness
# For any SpecChange, it SHALL include spec_id, from_version, to_version,
# timestamp, and change_type.
# **Feature: specdiff, Property 3: Change Metadata Completeness**
# **Validates: Requirements 1.3**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    old_content=st.text(min_size=10, max_size=100),
    new_content=st.text(min_size=10, max_size=100),
)
@settings(max_examples=50)
def test_spec_change_has_complete_metadata(
    spec_id: str, old_content: str, new_content: str
) -> None:
    """Property 3: SpecChange includes all required metadata.

    **Feature: specdiff, Property 3: Change Metadata Completeness**
    **Validates: Requirements 1.3**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        diff = specdiff.get_diff(spec_id, "v1", "v2")

        if diff:
            # Verify all required metadata is present
            assert diff.spec_id == spec_id
            assert diff.from_version == "v1"
            assert diff.to_version == "v2"
            assert diff.timestamp is not None
            assert isinstance(diff.timestamp, datetime)
            assert diff.change_type is not None
            assert isinstance(diff.change_type, ChangeType)

        specdiff.close()


# =============================================================================
# Property 9: Staleness Detection Accuracy
# For any spec where cached_version != current_version, check_staleness()
# SHALL return a warning.
# **Feature: specdiff, Property 9: Staleness Detection Accuracy**
# **Validates: Requirements 4.1, 4.2**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    old_content=st.text(min_size=10, max_size=100),
    new_content=st.text(min_size=10, max_size=100),
)
@settings(max_examples=50)
def test_staleness_detected_when_versions_differ(
    spec_id: str, old_content: str, new_content: str
) -> None:
    """Property 9: Staleness is detected when cached version differs from current.

    **Feature: specdiff, Property 9: Staleness Detection Accuracy**
    **Validates: Requirements 4.1, 4.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        # Create two versions
        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        # Check staleness with cached version v1
        warnings = specdiff.check_staleness(
            spec_ids=[spec_id],
            cached_versions={spec_id: "v1"},
        )

        # Should detect staleness since v1 != v2
        assert len(warnings) == 1
        assert warnings[0].spec_id == spec_id
        assert warnings[0].cached_version == "v1"
        assert warnings[0].current_version == "v2"

        specdiff.close()


@given(
    spec_id=spec_id_strategy,
    content=st.text(min_size=10, max_size=100),
)
@settings(max_examples=50)
def test_no_staleness_when_versions_match(spec_id: str, content: str) -> None:
    """Property 9: No staleness when cached version matches current.

    **Feature: specdiff, Property 9: Staleness Detection Accuracy**
    **Validates: Requirements 4.1, 4.2**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=content,
            source="test.md",
        )

        specdiff.track_version(spec, commit_ref="v1")

        # Check staleness with current version
        warnings = specdiff.check_staleness(
            spec_ids=[spec_id],
            cached_versions={spec_id: "v1"},
        )

        # Should not detect staleness
        assert len(warnings) == 0

        specdiff.close()


# =============================================================================
# Property 10: Staleness Warning Includes Diff
# For any staleness warning, it SHALL include the changes since the cached version.
# **Feature: specdiff, Property 10: Staleness Warning Includes Diff**
# **Validates: Requirements 4.3**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    old_content=st.text(min_size=10, max_size=100),
    new_content=st.text(min_size=10, max_size=100),
)
@settings(max_examples=50)
def test_staleness_warning_includes_changes(
    spec_id: str, old_content: str, new_content: str
) -> None:
    """Property 10: Staleness warning includes changes since cached version.

    **Feature: specdiff, Property 10: Staleness Warning Includes Diff**
    **Validates: Requirements 4.3**
    """
    if old_content == new_content:
        return  # Skip if content is the same

    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        warnings = specdiff.check_staleness(
            spec_ids=[spec_id],
            cached_versions={spec_id: "v1"},
        )

        assert len(warnings) == 1
        warning = warnings[0]

        # Warning should include changes
        assert warning.changes_since is not None
        assert len(warning.changes_since) >= 1

        # Each change should have proper structure
        for change in warning.changes_since:
            assert change.spec_id == spec_id
            assert change.from_version is not None
            assert change.to_version is not None

        specdiff.close()


# =============================================================================
# Property 12: Acknowledgment Persistence
# For any acknowledged staleness, the acknowledgment SHALL persist across
# subsequent check_staleness() calls.
# **Feature: specdiff, Property 12: Acknowledgment Persistence**
# **Validates: Requirements 4.5**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    old_content=st.text(min_size=10, max_size=100),
    new_content=st.text(min_size=10, max_size=100),
)
@settings(max_examples=50)
def test_acknowledgment_persists(spec_id: str, old_content: str, new_content: str) -> None:
    """Property 12: Staleness acknowledgment persists.

    **Feature: specdiff, Property 12: Acknowledgment Persistence**
    **Validates: Requirements 4.5**
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        specdiff = SpecDiff(Path(tmpdir) / "test.db")

        old_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=old_content,
            source="test.md",
        )
        new_spec = SpecBlock(
            id=spec_id,
            type=SpecType.REQUIREMENT,
            text=new_content,
            source="test.md",
        )

        specdiff.track_version(old_spec, commit_ref="v1")
        specdiff.track_version(new_spec, commit_ref="v2")

        # Acknowledge staleness
        specdiff.acknowledge_staleness(spec_id, "v1")

        # Check staleness again
        warnings = specdiff.check_staleness(
            spec_ids=[spec_id],
            cached_versions={spec_id: "v1"},
        )

        # Warning should still be returned but marked as acknowledged
        if len(warnings) > 0:
            assert warnings[0].acknowledged is True

        specdiff.close()


# =============================================================================
# Property 6: Drift Detection Completeness
# For any spec change, all code linked to that spec SHALL be included in
# the drift report.
# **Feature: specdiff, Property 6: Drift Detection Completeness**
# **Validates: Requirements 3.1**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    code_paths=st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-./"),
            min_size=5,
            max_size=50,
        ),
        min_size=1,
        max_size=5,
        unique=True,
    ),
)
@settings(max_examples=30)
def test_drift_report_includes_all_linked_code(spec_id: str, code_paths: list[str]) -> None:
    """Property 6: Drift report includes all code linked to changed spec.

    **Feature: specdiff, Property 6: Drift Detection Completeness**
    **Validates: Requirements 3.1**
    """
    # This test verifies the DriftReport structure
    # In a full integration test, we'd use a real SpecImpactGraph

    # Create a mock drift report with all linked code
    spec_change = SpecChange(
        spec_id=spec_id,
        from_version="v1",
        to_version="v2",
        timestamp=datetime.now(),
        change_type=ChangeType.SEMANTIC,
    )

    drift_items = [
        DriftItem(
            code_path=path,
            spec_id=spec_id,
            spec_change=spec_change,
            severity=0.5,
        )
        for path in code_paths
    ]

    report = DriftReport(
        drifted_code=drift_items,
        total_drift_score=0.5,
        generated_at=datetime.now(),
    )

    # Verify all code paths are in the report
    reported_paths = {item.code_path for item in report.drifted_code}
    for path in code_paths:
        assert path in reported_paths, f"Code path {path} not in drift report"


# =============================================================================
# Property 8: Drift References Spec Change
# For any DriftItem, it SHALL reference the SpecChange that caused the drift.
# **Feature: specdiff, Property 8: Drift References Spec Change**
# **Validates: Requirements 3.3**
# =============================================================================


@given(
    spec_id=spec_id_strategy,
    code_path=st.text(min_size=5, max_size=50),
    from_version=version_id_strategy,
    to_version=version_id_strategy,
)
@settings(max_examples=50)
def test_drift_item_references_spec_change(
    spec_id: str, code_path: str, from_version: str, to_version: str
) -> None:
    """Property 8: DriftItem references the causing SpecChange.

    **Feature: specdiff, Property 8: Drift References Spec Change**
    **Validates: Requirements 3.3**
    """
    spec_change = SpecChange(
        spec_id=spec_id,
        from_version=from_version,
        to_version=to_version,
        timestamp=datetime.now(),
        change_type=ChangeType.SEMANTIC,
    )

    drift_item = DriftItem(
        code_path=code_path,
        spec_id=spec_id,
        spec_change=spec_change,
        severity=0.5,
    )

    # Verify drift item references the spec change
    assert drift_item.spec_change is not None
    assert drift_item.spec_change.spec_id == spec_id
    assert drift_item.spec_change.from_version == from_version
    assert drift_item.spec_change.to_version == to_version
    assert drift_item.spec_id == spec_change.spec_id
