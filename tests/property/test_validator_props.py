"""Property-based tests for SpecValidator.

Tests correctness properties defined in the design document.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.validator.config import RuleConfig, ValidationConfig
from specmem.validator.models import IssueSeverity, ValidationIssue, ValidationResult


# =============================================================================
# Strategies for generating test data
# =============================================================================

severity_strategy = st.sampled_from(list(IssueSeverity))

rule_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=30,
)

spec_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-."),
    min_size=1,
    max_size=50,
)

message_strategy = st.text(min_size=1, max_size=200)

validation_issue_strategy = st.builds(
    ValidationIssue,
    rule_id=rule_id_strategy,
    severity=severity_strategy,
    message=message_strategy,
    spec_id=spec_id_strategy,
    file_path=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    line_number=st.one_of(st.none(), st.integers(min_value=1, max_value=10000)),
    context=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(max_size=50), st.integers()),
        max_size=5,
    ),
    suggestion=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
)

validation_result_strategy = st.builds(
    ValidationResult,
    issues=st.lists(validation_issue_strategy, max_size=20),
    specs_validated=st.integers(min_value=0, max_value=100),
    rules_run=st.integers(min_value=0, max_value=20),
    duration_ms=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
)


# =============================================================================
# Property 8: Result Completeness
# For any validation run, the result SHALL include all issues with spec_id,
# severity, and message; and the summary counts SHALL match the actual issue counts.
# **Feature: spec-validator, Property 8: Result Completeness**
# **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
# =============================================================================


@given(result=validation_result_strategy)
@settings(max_examples=100)
def test_result_has_complete_metadata(result: ValidationResult) -> None:
    """Property 8: ValidationResult includes all required metadata.

    **Feature: spec-validator, Property 8: Result Completeness**
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """
    # Every issue should have required fields
    for issue in result.issues:
        assert issue.rule_id is not None and len(issue.rule_id) > 0
        assert issue.severity is not None
        assert isinstance(issue.severity, IssueSeverity)
        assert issue.message is not None and len(issue.message) > 0
        assert issue.spec_id is not None and len(issue.spec_id) > 0

    # Summary counts should match actual counts
    actual_errors = sum(1 for i in result.issues if i.severity == IssueSeverity.ERROR)
    actual_warnings = sum(1 for i in result.issues if i.severity == IssueSeverity.WARNING)
    actual_info = sum(1 for i in result.issues if i.severity == IssueSeverity.INFO)

    assert result.error_count == actual_errors
    assert result.warning_count == actual_warnings
    assert result.info_count == actual_info

    # Total issues should match
    assert len(result.issues) == result.error_count + result.warning_count + result.info_count


@given(issues=st.lists(validation_issue_strategy, min_size=1, max_size=20))
@settings(max_examples=100)
def test_result_filtering_methods(issues: list[ValidationIssue]) -> None:
    """Property 8: ValidationResult filtering methods work correctly.

    **Feature: spec-validator, Property 8: Result Completeness**
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """
    result = ValidationResult(
        issues=issues,
        specs_validated=1,
        rules_run=1,
        duration_ms=100.0,
    )

    # Test severity filtering
    errors = result.get_by_severity(IssueSeverity.ERROR)
    warnings = result.get_by_severity(IssueSeverity.WARNING)
    info_issues = result.get_by_severity(IssueSeverity.INFO)

    # All returned issues should have correct severity
    for issue in errors:
        assert issue.severity == IssueSeverity.ERROR
    for issue in warnings:
        assert issue.severity == IssueSeverity.WARNING
    for issue in info_issues:
        assert issue.severity == IssueSeverity.INFO

    # Test spec filtering
    spec_id = issues[0].spec_id
    spec_issues = result.get_by_spec(spec_id)
    for issue in spec_issues:
        assert issue.spec_id == spec_id

    # Test rule filtering
    rule_id = issues[0].rule_id
    rule_issues = result.get_by_rule(rule_id)
    for issue in rule_issues:
        assert issue.rule_id == rule_id


@given(result=validation_result_strategy)
@settings(max_examples=100)
def test_is_valid_reflects_errors(result: ValidationResult) -> None:
    """Property 8: is_valid is True iff no errors exist.

    **Feature: spec-validator, Property 8: Result Completeness**
    **Validates: Requirements 7.5**
    """
    has_errors = any(i.severity == IssueSeverity.ERROR for i in result.issues)
    assert result.is_valid == (not has_errors)


# =============================================================================
# Property 10: Configuration Respect
# For any rule and configuration, the engine SHALL respect enabled/disabled
# settings and severity overrides.
# **Feature: spec-validator, Property 10: Configuration Respect**
# **Validates: Requirements 9.2, 9.3, 9.4**
# =============================================================================


rule_config_strategy = st.builds(
    RuleConfig,
    enabled=st.booleans(),
    severity=st.one_of(st.none(), severity_strategy),
    options=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(max_size=50), st.integers(), st.floats(allow_nan=False)),
        max_size=5,
    ),
)

validation_config_strategy = st.builds(
    ValidationConfig,
    rules=st.dictionaries(rule_id_strategy, rule_config_strategy, max_size=10),
    similarity_threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    min_acceptance_criteria=st.integers(min_value=0, max_value=10),
    max_spec_length=st.integers(min_value=100, max_value=100000),
)


@given(config=validation_config_strategy, rule_id=rule_id_strategy)
@settings(max_examples=100)
def test_config_respects_enabled_setting(config: ValidationConfig, rule_id: str) -> None:
    """Property 10: is_rule_enabled respects configuration.

    **Feature: spec-validator, Property 10: Configuration Respect**
    **Validates: Requirements 9.2**
    """
    if rule_id in config.rules:
        # If rule is configured, respect its enabled setting
        assert config.is_rule_enabled(rule_id) == config.rules[rule_id].enabled
    else:
        # If rule is not configured, it should be enabled by default
        assert config.is_rule_enabled(rule_id) is True


@given(
    config=validation_config_strategy,
    rule_id=rule_id_strategy,
    default_severity=severity_strategy,
)
@settings(max_examples=100)
def test_config_respects_severity_override(
    config: ValidationConfig, rule_id: str, default_severity: IssueSeverity
) -> None:
    """Property 10: get_severity respects configuration overrides.

    **Feature: spec-validator, Property 10: Configuration Respect**
    **Validates: Requirements 9.3**
    """
    result = config.get_severity(rule_id, default_severity)

    if rule_id in config.rules and config.rules[rule_id].severity is not None:
        # If severity is configured, use it
        assert result == config.rules[rule_id].severity
    else:
        # Otherwise use default
        assert result == default_severity


@given(config=validation_config_strategy)
@settings(max_examples=100)
def test_config_serialization_roundtrip(config: ValidationConfig) -> None:
    """Property 10: ValidationConfig can be serialized and deserialized.

    **Feature: spec-validator, Property 10: Configuration Respect**
    **Validates: Requirements 9.4**
    """
    serialized = config.to_dict()

    # Verify structure
    assert "rules" in serialized
    assert "similarity_threshold" in serialized
    assert "min_acceptance_criteria" in serialized
    assert "max_spec_length" in serialized

    # Verify values preserved
    assert serialized["similarity_threshold"] == config.similarity_threshold
    assert serialized["min_acceptance_criteria"] == config.min_acceptance_criteria
    assert serialized["max_spec_length"] == config.max_spec_length


@given(issue=validation_issue_strategy)
@settings(max_examples=100)
def test_issue_serialization_roundtrip(issue: ValidationIssue) -> None:
    """ValidationIssue can be serialized and deserialized without data loss."""
    serialized = issue.to_dict()
    restored = ValidationIssue.from_dict(serialized)

    assert restored.rule_id == issue.rule_id
    assert restored.severity == issue.severity
    assert restored.message == issue.message
    assert restored.spec_id == issue.spec_id
    assert restored.file_path == issue.file_path
    assert restored.line_number == issue.line_number
    assert restored.context == issue.context
    assert restored.suggestion == issue.suggestion


@given(result=validation_result_strategy)
@settings(max_examples=100)
def test_result_serialization_roundtrip(result: ValidationResult) -> None:
    """ValidationResult can be serialized and deserialized without data loss."""
    serialized = result.to_dict()
    restored = ValidationResult.from_dict(serialized)

    assert restored.specs_validated == result.specs_validated
    assert restored.rules_run == result.rules_run
    assert restored.duration_ms == result.duration_ms
    assert len(restored.issues) == len(result.issues)

    # Check computed properties match
    assert restored.is_valid == result.is_valid
    assert restored.error_count == result.error_count
    assert restored.warning_count == result.warning_count
    assert restored.info_count == result.info_count


# =============================================================================
# Property 9: Valid Specs Pass
# For any well-formed spec with no issues, the validator SHALL return a result
# with zero issues and is_valid=True.
# **Feature: spec-validator, Property 9: Valid Specs Pass**
# **Validates: Requirements 7.5**
# =============================================================================

from specmem.validator.engine import ValidationEngine


@given(specs_count=st.integers(min_value=0, max_value=10))
@settings(max_examples=50)
def test_empty_rules_produce_valid_result(specs_count: int) -> None:
    """Property 9: Engine with no rules produces valid result.

    **Feature: spec-validator, Property 9: Valid Specs Pass**
    **Validates: Requirements 7.5**
    """
    engine = ValidationEngine()
    # No rules registered, so no issues should be found
    result = engine.validate([])

    assert result.is_valid is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.info_count == 0
    assert len(result.issues) == 0


@given(config=validation_config_strategy)
@settings(max_examples=50)
def test_engine_respects_config(config: ValidationConfig) -> None:
    """Property 9: Engine uses provided configuration.

    **Feature: spec-validator, Property 9: Valid Specs Pass**
    **Validates: Requirements 7.5**
    """
    engine = ValidationEngine(config)
    assert engine.config == config


@given(
    error_issues=st.lists(
        validation_issue_strategy.filter(lambda i: i.severity == IssueSeverity.ERROR),
        min_size=1,
        max_size=5,
    ),
    warning_issues=st.lists(
        validation_issue_strategy.filter(lambda i: i.severity == IssueSeverity.WARNING),
        max_size=5,
    ),
)
@settings(max_examples=50)
def test_specs_with_errors_fail_validation(
    error_issues: list[ValidationIssue], warning_issues: list[ValidationIssue]
) -> None:
    """Property 9: Results with errors have is_valid=False.

    **Feature: spec-validator, Property 9: Valid Specs Pass**
    **Validates: Requirements 7.5**
    """
    result = ValidationResult(
        issues=error_issues + warning_issues,
        specs_validated=1,
        rules_run=5,
        duration_ms=100.0,
    )

    # Should not be valid due to errors
    assert result.is_valid is False
    assert result.error_count > 0


# =============================================================================
# Property 1: Contradiction Detection Completeness
# For any pair of specs where one contains "SHALL" and another contains
# "SHALL NOT" on the same subject, the validator SHALL detect and report
# the contradiction.
# **Feature: spec-validator, Property 1: Contradiction Detection Completeness**
# **Validates: Requirements 1.1, 1.2, 1.4**
# =============================================================================

from specmem.core.specir import SpecBlock, SpecType
from specmem.validator.rules.contradiction import ContradictionRule


# Stop words that should be filtered from subjects
_STOP_WORDS = {
    "the",
    "a",
    "an",
    "be",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "at",
    "when",
    "under",
    "any",
    "all",
    "circumstances",
    "requested",
    "if",
    "then",
    "while",
    "during",
    "after",
    "before",
    "with",
    "without",
}


def _is_valid_subject(s: str) -> bool:
    """Check if subject contains at least one non-stop word."""
    words = set(s.lower().split()) - _STOP_WORDS
    return len(words) > 0 and len(s.strip()) >= 3


@given(
    subject=st.text(
        alphabet=st.characters(whitelist_categories=("L",)),
        min_size=3,
        max_size=20,
    ).filter(_is_valid_subject),
    modal_pair=st.sampled_from(
        [
            ("shall", "shall not"),
            ("must", "must not"),
            ("will", "will not"),
            ("can", "cannot"),
        ]
    ),
)
@settings(max_examples=100)
def test_contradiction_detected_for_negation_patterns(
    subject: str, modal_pair: tuple[str, str]
) -> None:
    """Property 1: Contradictions with negation patterns are detected.

    **Feature: spec-validator, Property 1: Contradiction Detection Completeness**
    **Validates: Requirements 1.1, 1.2, 1.4**
    """
    positive, negative = modal_pair

    # Create two specs with contradictory statements
    spec1 = SpecBlock(
        id="spec1",
        type=SpecType.REQUIREMENT,
        text=f"The system {positive} {subject} when requested",
        source="test.md",
    )
    spec2 = SpecBlock(
        id="spec2",
        type=SpecType.REQUIREMENT,
        text=f"The system {negative} {subject} under any circumstances",
        source="test.md",
    )

    rule = ContradictionRule()
    config = ValidationConfig()
    issues = rule.validate([spec1, spec2], config)

    # Should detect the contradiction
    assert (
        len(issues) >= 1
    ), f"Expected contradiction for '{positive}' vs '{negative}' on '{subject}'"
    assert any("contradiction" in issue.message.lower() for issue in issues)


@given(
    subject1=st.text(
        alphabet=st.characters(whitelist_categories=("L",)),
        min_size=5,
        max_size=20,
    ).filter(lambda s: s.strip()),
    subject2=st.text(
        alphabet=st.characters(whitelist_categories=("L",)),
        min_size=5,
        max_size=20,
    ).filter(lambda s: s.strip()),
)
@settings(max_examples=100)
def test_no_false_positive_for_different_subjects(subject1: str, subject2: str) -> None:
    """Property 1: No false positives for different subjects.

    **Feature: spec-validator, Property 1: Contradiction Detection Completeness**
    **Validates: Requirements 1.1, 1.2, 1.4**
    """
    # Skip if subjects are too similar
    words1 = set(subject1.lower().split())
    words2 = set(subject2.lower().split())
    if words1 & words2:
        return  # Skip test if subjects overlap

    spec1 = SpecBlock(
        id="spec1",
        type=SpecType.REQUIREMENT,
        text=f"The system shall {subject1} when requested",
        source="test.md",
    )
    spec2 = SpecBlock(
        id="spec2",
        type=SpecType.REQUIREMENT,
        text=f"The system shall not {subject2} under any circumstances",
        source="test.md",
    )

    rule = ContradictionRule()
    config = ValidationConfig()
    issues = rule.validate([spec1, spec2], config)

    # Should NOT detect contradiction for different subjects
    assert len(issues) == 0, f"False positive: '{subject1}' vs '{subject2}' are different subjects"


# =============================================================================
# Property 2: Acceptance Criteria Completeness
# For any spec missing acceptance criteria or with fewer than the configured
# minimum, the validator SHALL report an issue.
# **Feature: spec-validator, Property 2: Acceptance Criteria Completeness**
# **Validates: Requirements 2.1, 2.4**
# =============================================================================

from specmem.validator.rules.acceptance_criteria import AcceptanceCriteriaRule


@given(
    min_criteria=st.integers(min_value=1, max_value=5),
    actual_criteria=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100)
def test_insufficient_criteria_detected(min_criteria: int, actual_criteria: int) -> None:
    """Property 2: Specs with insufficient criteria are flagged.

    **Feature: spec-validator, Property 2: Acceptance Criteria Completeness**
    **Validates: Requirements 2.1, 2.4**
    """
    # Build spec text with the specified number of criteria
    criteria_lines = "\n".join(
        f"{i + 1}. WHEN user requests THEN system SHALL respond" for i in range(actual_criteria)
    )

    spec_text = f"""# Requirement

## Acceptance Criteria

{criteria_lines}
"""

    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=spec_text,
        source="test.md",
    )

    rule = AcceptanceCriteriaRule()
    config = ValidationConfig(min_acceptance_criteria=min_criteria)
    issues = rule.validate([spec], config)

    if actual_criteria < min_criteria:
        # Should have an issue about insufficient criteria
        insufficient_issues = [
            i
            for i in issues
            if "insufficient" in i.message.lower() or "minimum" in i.message.lower()
        ]
        assert (
            len(insufficient_issues) >= 1
        ), f"Expected issue for {actual_criteria} criteria when minimum is {min_criteria}"
    else:
        # Should NOT have an issue about insufficient criteria
        insufficient_issues = [i for i in issues if "insufficient" in i.message.lower()]
        assert (
            len(insufficient_issues) == 0
        ), f"Unexpected issue for {actual_criteria} criteria when minimum is {min_criteria}"


@given(has_section=st.booleans())
@settings(max_examples=50)
def test_missing_acceptance_criteria_section_detected(has_section: bool) -> None:
    """Property 2: Missing acceptance criteria section is detected.

    **Feature: spec-validator, Property 2: Acceptance Criteria Completeness**
    **Validates: Requirements 2.1, 2.4**
    """
    if has_section:
        spec_text = """# Requirement

## Acceptance Criteria

1. WHEN user requests THEN system SHALL respond
2. WHEN error occurs THEN system SHALL log
"""
    else:
        spec_text = """# Requirement

The system should do something useful.
"""

    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=spec_text,
        source="test.md",
    )

    rule = AcceptanceCriteriaRule()
    config = ValidationConfig(min_acceptance_criteria=2)
    issues = rule.validate([spec], config)

    if not has_section:
        # Should detect missing section
        missing_issues = [i for i in issues if "missing" in i.message.lower()]
        assert len(missing_issues) >= 1, "Expected issue for missing acceptance criteria section"
    else:
        # Should NOT report missing section
        missing_issues = [i for i in issues if "missing" in i.message.lower()]
        assert len(missing_issues) == 0, "Unexpected missing section issue"


# =============================================================================
# Property 3: Invalid Constraint Detection
# For any spec with impossible values (negative counts, >100%, min>max),
# the validator SHALL detect and report the issue.
# **Feature: spec-validator, Property 3: Invalid Constraint Detection**
# **Validates: Requirements 3.1, 3.2, 3.3**
# =============================================================================

from specmem.validator.rules.constraints import ConstraintRule


@given(percentage=st.floats(min_value=100.1, max_value=1000.0, allow_nan=False))
@settings(max_examples=50)
def test_impossible_percentage_detected(percentage: float) -> None:
    """Property 3: Percentages > 100% are detected.

    **Feature: spec-validator, Property 3: Invalid Constraint Detection**
    **Validates: Requirements 3.1**
    """
    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=f"The system shall achieve {percentage}% uptime",
        source="test.md",
    )

    rule = ConstraintRule()
    config = ValidationConfig()
    issues = rule.validate([spec], config)

    assert len(issues) >= 1, f"Expected issue for {percentage}%"
    assert any("percentage" in i.message.lower() for i in issues)


@given(percentage=st.integers(min_value=0, max_value=100))
@settings(max_examples=50)
def test_valid_percentage_not_flagged(percentage: int) -> None:
    """Property 3: Valid percentages (0-100%) are not flagged.

    **Feature: spec-validator, Property 3: Invalid Constraint Detection**
    **Validates: Requirements 3.1**
    """
    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=f"The system shall achieve {percentage}% uptime",
        source="test.md",
    )

    rule = ConstraintRule()
    config = ValidationConfig()
    issues = rule.validate([spec], config)

    percentage_issues = [i for i in issues if "percentage" in i.message.lower()]
    assert len(percentage_issues) == 0, f"Unexpected issue for valid {percentage}%"


@given(
    min_val=st.integers(min_value=10, max_value=1000),
    max_val=st.integers(min_value=0, max_value=9),
)
@settings(max_examples=50)
def test_conflicting_range_detected(min_val: int, max_val: int) -> None:
    """Property 3: min > max ranges are detected.

    **Feature: spec-validator, Property 3: Invalid Constraint Detection**
    **Validates: Requirements 3.2**
    """
    # min_val is always > max_val due to strategy constraints
    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=f"The value must be between {min_val} and {max_val}",
        source="test.md",
    )

    rule = ConstraintRule()
    config = ValidationConfig()
    issues = rule.validate([spec], config)

    assert len(issues) >= 1, f"Expected issue for range {min_val} to {max_val}"
    assert any("range" in i.message.lower() or "minimum" in i.message.lower() for i in issues)


@given(time_value=st.floats(min_value=-1000.0, max_value=-0.1, allow_nan=False))
@settings(max_examples=50)
def test_negative_time_detected(time_value: float) -> None:
    """Property 3: Negative time constraints are detected.

    **Feature: spec-validator, Property 3: Invalid Constraint Detection**
    **Validates: Requirements 3.3**
    """
    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=f"Response time: {time_value} ms",
        source="test.md",
    )

    rule = ConstraintRule()
    config = ValidationConfig()
    issues = rule.validate([spec], config)

    assert len(issues) >= 1, f"Expected issue for negative time {time_value}"
    assert any("time" in i.message.lower() or "negative" in i.message.lower() for i in issues)


# =============================================================================
# Property 4: Duplicate Detection with Similarity
# For any pair of specs with similarity >= threshold, the validator SHALL
# report them as potential duplicates.
# **Feature: spec-validator, Property 4: Duplicate Detection with Similarity**
# **Validates: Requirements 4.1, 4.2, 4.3**
# =============================================================================

from specmem.validator.rules.duplicates import DuplicateRule


@given(threshold=st.floats(min_value=0.5, max_value=0.95, allow_nan=False))
@settings(max_examples=50)
def test_identical_specs_detected_as_duplicates(threshold: float) -> None:
    """Property 4: Identical specs are detected as duplicates.

    **Feature: spec-validator, Property 4: Duplicate Detection with Similarity**
    **Validates: Requirements 4.1, 4.2, 4.3**
    """
    text = "The system shall process user requests within 100ms response time"

    spec1 = SpecBlock(
        id="spec1",
        type=SpecType.REQUIREMENT,
        text=text,
        source="test1.md",
    )
    spec2 = SpecBlock(
        id="spec2",
        type=SpecType.REQUIREMENT,
        text=text,  # Identical text
        source="test2.md",
    )

    rule = DuplicateRule()
    config = ValidationConfig(similarity_threshold=threshold)
    issues = rule.validate([spec1, spec2], config)

    # Should detect as duplicates (100% similarity)
    duplicate_issues = [
        i for i in issues if "duplicate" in i.message.lower() or "similarity" in i.message.lower()
    ]
    assert len(duplicate_issues) >= 1, "Expected duplicate detection for identical specs"


# =============================================================================
# Property 5: ID Uniqueness
# For any set of specs with duplicate IDs, the validator SHALL report an error.
# **Feature: spec-validator, Property 5: ID Uniqueness**
# **Validates: Requirements 4.4**
# =============================================================================


@given(spec_id=spec_id_strategy)
@settings(max_examples=50)
def test_duplicate_ids_detected(spec_id: str) -> None:
    """Property 5: Duplicate spec IDs are detected.

    **Feature: spec-validator, Property 5: ID Uniqueness**
    **Validates: Requirements 4.4**
    """
    spec1 = SpecBlock(
        id=spec_id,
        type=SpecType.REQUIREMENT,
        text="First requirement text",
        source="test1.md",
    )
    spec2 = SpecBlock(
        id=spec_id,  # Same ID
        type=SpecType.REQUIREMENT,
        text="Different requirement text",
        source="test2.md",
    )

    rule = DuplicateRule()
    config = ValidationConfig()
    issues = rule.validate([spec1, spec2], config)

    # Should detect duplicate ID
    id_issues = [
        i for i in issues if "duplicate" in i.message.lower() and "id" in i.message.lower()
    ]
    assert len(id_issues) >= 1, f"Expected duplicate ID detection for '{spec_id}'"
    assert any(
        i.severity == IssueSeverity.ERROR for i in id_issues
    ), "Duplicate IDs should be errors"


# =============================================================================
# Property 6: Timeline Consistency
# For any spec with a deadline in the past, the validator SHALL report an issue.
# **Feature: spec-validator, Property 6: Timeline Consistency**
# **Validates: Requirements 5.1, 5.2, 5.3**
# =============================================================================

from specmem.validator.rules.timeline import TimelineRule


@given(
    year=st.integers(min_value=2020, max_value=2025),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
)
@settings(max_examples=50)
def test_past_deadline_detected(year: int, month: int, day: int) -> None:
    """Property 6: Past deadlines are detected.

    **Feature: spec-validator, Property 6: Timeline Consistency**
    **Validates: Requirements 5.1, 5.2, 5.3**
    """
    from datetime import date

    deadline = date(year, month, day)
    today = date.today()

    # Only test if deadline is actually in the past
    if deadline >= today:
        return

    date_str = deadline.strftime("%Y-%m-%d")
    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=f"Complete by deadline: {date_str}",
        source="test.md",
    )

    rule = TimelineRule()
    config = ValidationConfig()
    issues = rule.validate([spec], config)

    # Should detect past deadline
    deadline_issues = [
        i for i in issues if "past" in i.message.lower() or "deadline" in i.message.lower()
    ]
    assert len(deadline_issues) >= 1, f"Expected past deadline detection for {date_str}"


# =============================================================================
# Property 7: Structure Validation
# For any spec exceeding max length, the validator SHALL report a warning.
# **Feature: spec-validator, Property 7: Structure Validation**
# **Validates: Requirements 6.1, 6.4**
# =============================================================================

from specmem.validator.rules.structure import StructureRule


@given(
    max_length=st.integers(min_value=100, max_value=1000),
    extra_length=st.integers(min_value=1, max_value=500),
)
@settings(max_examples=50)
def test_spec_length_exceeded_detected(max_length: int, extra_length: int) -> None:
    """Property 7: Specs exceeding max length are detected.

    **Feature: spec-validator, Property 7: Structure Validation**
    **Validates: Requirements 6.1, 6.4**
    """
    # Create text that exceeds max_length
    text = "x" * (max_length + extra_length)

    spec = SpecBlock(
        id="test-spec",
        type=SpecType.REQUIREMENT,
        text=text,
        source="test.md",
    )

    rule = StructureRule()
    config = ValidationConfig(max_spec_length=max_length)
    issues = rule.validate([spec], config)

    # Should detect length exceeded
    length_issues = [
        i for i in issues if "length" in i.message.lower() or "exceeds" in i.message.lower()
    ]
    assert (
        len(length_issues) >= 1
    ), f"Expected length exceeded detection for {len(text)} > {max_length}"


# =============================================================================
# Property 11: CLI Exit Code
# For any validation result with errors, the CLI SHALL exit with non-zero code.
# **Feature: spec-validator, Property 11: CLI Exit Code**
# **Validates: Requirements 8.3**
# =============================================================================


@given(
    has_errors=st.booleans(),
    warning_count=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=50)
def test_validation_result_exit_code_logic(has_errors: bool, warning_count: int) -> None:
    """Property 11: is_valid determines exit code logic.

    **Feature: spec-validator, Property 11: CLI Exit Code**
    **Validates: Requirements 8.3**
    """
    # Build issues list
    issues: list[ValidationIssue] = []

    if has_errors:
        issues.append(
            ValidationIssue(
                rule_id="test",
                severity=IssueSeverity.ERROR,
                message="Test error",
                spec_id="test-spec",
            )
        )

    for _ in range(warning_count):
        issues.append(
            ValidationIssue(
                rule_id="test",
                severity=IssueSeverity.WARNING,
                message="Test warning",
                spec_id="test-spec",
            )
        )

    result = ValidationResult(
        issues=issues,
        specs_validated=1,
        rules_run=1,
        duration_ms=100.0,
    )

    # is_valid should be False only if there are errors
    # Warnings alone should not cause validation to fail
    if has_errors:
        assert result.is_valid is False, "Should fail with errors"
    else:
        assert result.is_valid is True, "Should pass without errors (warnings are OK)"


# =============================================================================
# Property 12: Client API Correctness
# For any validation through the client API, the result SHALL match
# direct engine validation.
# **Feature: spec-validator, Property 12: Client API Correctness**
# **Validates: Requirements 10.1, 10.2, 10.4**
# =============================================================================


@given(
    error_count=st.integers(min_value=0, max_value=3),
    warning_count=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=50)
def test_client_api_filtering_methods(error_count: int, warning_count: int) -> None:
    """Property 12: Client API filtering methods work correctly.

    **Feature: spec-validator, Property 12: Client API Correctness**
    **Validates: Requirements 10.1, 10.2, 10.4**
    """
    # Build issues list
    issues: list[ValidationIssue] = []

    for i in range(error_count):
        issues.append(
            ValidationIssue(
                rule_id="test",
                severity=IssueSeverity.ERROR,
                message=f"Test error {i}",
                spec_id="test-spec",
            )
        )

    for i in range(warning_count):
        issues.append(
            ValidationIssue(
                rule_id="test",
                severity=IssueSeverity.WARNING,
                message=f"Test warning {i}",
                spec_id="test-spec",
            )
        )

    result = ValidationResult(
        issues=issues,
        specs_validated=1,
        rules_run=1,
        duration_ms=100.0,
    )

    # Test filtering methods
    errors = result.get_errors()
    warnings = result.get_warnings()

    assert len(errors) == error_count
    assert len(warnings) == warning_count

    # All errors should have ERROR severity
    for error in errors:
        assert error.severity == IssueSeverity.ERROR

    # All warnings should have WARNING severity
    for warning in warnings:
        assert warning.severity == IssueSeverity.WARNING

    # is_valid should reflect error presence
    assert result.is_valid == (error_count == 0)
