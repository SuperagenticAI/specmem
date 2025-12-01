"""Property-based tests for memory lifecycle state machine.

Tests correctness properties defined in the pluggable-vectordb design document.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.core.exceptions import LifecycleError
from specmem.core.specir import SpecStatus
from specmem.vectordb.base import VALID_TRANSITIONS, validate_transition


# Generate all valid transitions as tuples
VALID_TRANSITION_PAIRS = [
    (from_status, to_status)
    for from_status, valid_targets in VALID_TRANSITIONS.items()
    for to_status in valid_targets
]

# Generate all invalid transitions
ALL_STATUS_PAIRS = [
    (from_status, to_status) for from_status in SpecStatus for to_status in SpecStatus
]
INVALID_TRANSITION_PAIRS = [pair for pair in ALL_STATUS_PAIRS if pair not in VALID_TRANSITION_PAIRS]


class TestValidLifecycleTransitions:
    """**Feature: pluggable-vectordb, Property 7: Valid lifecycle transitions succeed**"""

    @given(transition=st.sampled_from(VALID_TRANSITION_PAIRS))
    @settings(max_examples=100)
    def test_valid_transitions_succeed(self, transition: tuple[SpecStatus, SpecStatus]):
        """For any valid transition, validate_transition returns True.

        **Validates: Requirements 7.1, 7.2, 7.3, 7.5**
        """
        from_status, to_status = transition
        assert validate_transition(from_status, to_status) is True

    def test_active_to_deprecated_allowed(self):
        """Active blocks can be deprecated."""
        assert validate_transition(SpecStatus.ACTIVE, SpecStatus.DEPRECATED) is True

    def test_active_to_legacy_allowed(self):
        """Active blocks can be marked legacy directly."""
        assert validate_transition(SpecStatus.ACTIVE, SpecStatus.LEGACY) is True

    def test_deprecated_to_legacy_allowed(self):
        """Deprecated blocks can become legacy."""
        assert validate_transition(SpecStatus.DEPRECATED, SpecStatus.LEGACY) is True

    def test_deprecated_to_active_allowed(self):
        """Deprecated blocks can be reactivated."""
        assert validate_transition(SpecStatus.DEPRECATED, SpecStatus.ACTIVE) is True

    def test_legacy_to_obsolete_allowed(self):
        """Legacy blocks can become obsolete."""
        assert validate_transition(SpecStatus.LEGACY, SpecStatus.OBSOLETE) is True

    def test_legacy_to_deprecated_allowed(self):
        """Legacy blocks can be un-deprecated."""
        assert validate_transition(SpecStatus.LEGACY, SpecStatus.DEPRECATED) is True


class TestInvalidLifecycleTransitions:
    """**Feature: pluggable-vectordb, Property 8: Invalid lifecycle transitions fail**"""

    @given(transition=st.sampled_from(INVALID_TRANSITION_PAIRS))
    @settings(max_examples=100)
    def test_invalid_transitions_fail(self, transition: tuple[SpecStatus, SpecStatus]):
        """For any invalid transition, validate_transition returns False.

        **Validates: Requirements 7.4**
        """
        from_status, to_status = transition
        assert validate_transition(from_status, to_status) is False

    def test_obsolete_is_terminal(self):
        """Obsolete blocks cannot transition to any other state."""
        for status in SpecStatus:
            assert validate_transition(SpecStatus.OBSOLETE, status) is False

    def test_active_to_obsolete_not_allowed(self):
        """Active blocks cannot become obsolete directly."""
        assert validate_transition(SpecStatus.ACTIVE, SpecStatus.OBSOLETE) is False

    def test_deprecated_to_obsolete_not_allowed(self):
        """Deprecated blocks cannot become obsolete directly."""
        assert validate_transition(SpecStatus.DEPRECATED, SpecStatus.OBSOLETE) is False

    def test_same_status_not_allowed(self):
        """Transitioning to the same status is not allowed."""
        for status in SpecStatus:
            assert validate_transition(status, status) is False


class TestLifecycleError:
    """Tests for LifecycleError exception."""

    def test_lifecycle_error_contains_details(self):
        """LifecycleError contains all transition details."""
        error = LifecycleError(
            message="Invalid transition",
            from_status="active",
            to_status="obsolete",
            block_id="test-123",
            valid_transitions=["deprecated", "legacy"],
        )

        assert error.code == "LIFECYCLE_ERROR"
        assert error.from_status == "active"
        assert error.to_status == "obsolete"
        assert error.block_id == "test-123"
        assert error.details["valid_transitions"] == ["deprecated", "legacy"]

    def test_lifecycle_error_message(self):
        """LifecycleError has proper string representation."""
        error = LifecycleError(
            message="Cannot transition from active to obsolete",
            from_status="active",
            to_status="obsolete",
            block_id="test-123",
        )

        assert "LIFECYCLE_ERROR" in str(error)
        assert "Cannot transition" in str(error)
