"""Property-based tests for Test Mapping Engine.

Tests correctness properties defined in the test-mapping-engine design document.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.core import CodeRef, SpecBlock, SpecType, TestMapping


# Strategies for generating test data
framework_strategy = st.sampled_from(["pytest", "jest", "vitest", "playwright", "mocha"])

path_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/_-."),
    min_size=3,
    max_size=100,
).filter(lambda x: len(x.strip()) > 0)

selector_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_::."),
    min_size=1,
    max_size=100,
).filter(lambda x: len(x.strip()) > 0)

confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

language_strategy = st.sampled_from(["python", "javascript", "typescript", "java", "go"])

symbols_strategy = st.lists(
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_"),
        min_size=1,
        max_size=50,
    ).filter(lambda x: len(x.strip()) > 0),
    max_size=10,
)


class TestTestMappingCompleteness:
    """**Feature: test-mapping-engine, Property 1: TestMapping Completeness**

    *For any* TestMapping object, it SHALL contain non-empty framework, path,
    and selector fields.

    **Validates: Requirements 1.2**
    """

    @given(
        framework=framework_strategy,
        path=path_strategy,
        selector=selector_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=100)
    def test_test_mapping_has_required_fields(
        self,
        framework: str,
        path: str,
        selector: str,
        confidence: float,
    ):
        """For any valid TestMapping, all required fields are non-empty."""
        tm = TestMapping(
            framework=framework,
            path=path,
            selector=selector,
            confidence=confidence,
        )

        assert tm.framework and len(tm.framework) > 0
        assert tm.path and len(tm.path) > 0
        assert tm.selector and len(tm.selector) > 0
        assert 0.0 <= tm.confidence <= 1.0

    def test_empty_framework_rejected(self):
        """Empty framework is rejected."""
        with pytest.raises(ValueError, match="framework cannot be empty"):
            TestMapping(framework="", path="test.py", selector="test")

    def test_empty_path_rejected(self):
        """Empty path is rejected."""
        with pytest.raises(ValueError, match="path cannot be empty"):
            TestMapping(framework="pytest", path="", selector="test")

    def test_empty_selector_rejected(self):
        """Empty selector is rejected."""
        with pytest.raises(ValueError, match="selector cannot be empty"):
            TestMapping(framework="pytest", path="test.py", selector="")


class TestSpecBlockTestMappingRoundTrip:
    """**Feature: test-mapping-engine, Property 3: SpecBlock Test Mapping Round-Trip**

    *For any* SpecBlock with test_mappings, serializing then deserializing
    SHALL produce an equivalent SpecBlock with identical test_mappings.

    **Validates: Requirements 2.3, 2.4**
    """

    @given(
        framework=framework_strategy,
        path=path_strategy,
        selector=selector_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=100)
    def test_test_mapping_round_trip(
        self,
        framework: str,
        path: str,
        selector: str,
        confidence: float,
    ):
        """For any TestMapping, to_dict/from_dict produces equivalent object."""
        original = TestMapping(
            framework=framework,
            path=path,
            selector=selector,
            confidence=confidence,
        )

        # Round-trip through dict
        restored = TestMapping.from_dict(original.to_dict())

        assert restored.framework == original.framework
        assert restored.path == original.path
        assert restored.selector == original.selector
        assert restored.confidence == original.confidence

    @given(
        framework=framework_strategy,
        path=path_strategy,
        selector=selector_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=50)
    def test_specblock_test_mappings_round_trip(
        self,
        framework: str,
        path: str,
        selector: str,
        confidence: float,
    ):
        """For any SpecBlock with test_mappings, JSON round-trip preserves mappings."""
        tm = TestMapping(
            framework=framework,
            path=path,
            selector=selector,
            confidence=confidence,
        )

        block = SpecBlock(
            id="test123",
            type=SpecType.REQUIREMENT,
            text="Test requirement",
            source="test.md",
        )
        block.add_test_mapping(tm)

        # Round-trip through JSON
        json_str = block.to_json()
        restored = SpecBlock.from_json(json_str)

        assert len(restored.test_mappings) == 1
        restored_tm = restored.get_test_mappings()[0]
        assert restored_tm.framework == tm.framework
        assert restored_tm.path == tm.path
        assert restored_tm.selector == tm.selector
        assert restored_tm.confidence == tm.confidence


class TestSpecBlockCodeRefRoundTrip:
    """**Feature: test-mapping-engine, Property 4: SpecBlock CodeRef Round-Trip**

    *For any* SpecBlock with code_refs, serializing then deserializing
    SHALL produce an equivalent SpecBlock with identical code_refs.

    **Validates: Requirements 3.4, 3.5**
    """

    @given(
        language=language_strategy,
        file_path=path_strategy,
        symbols=symbols_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=100)
    def test_code_ref_round_trip(
        self,
        language: str,
        file_path: str,
        symbols: list[str],
        confidence: float,
    ):
        """For any CodeRef, to_dict/from_dict produces equivalent object."""
        original = CodeRef(
            language=language,
            file_path=file_path,
            symbols=symbols,
            confidence=confidence,
        )

        # Round-trip through dict
        restored = CodeRef.from_dict(original.to_dict())

        assert restored.language == original.language
        assert restored.file_path == original.file_path
        assert restored.symbols == original.symbols
        assert restored.confidence == original.confidence

    @given(
        language=language_strategy,
        file_path=path_strategy,
        symbols=symbols_strategy,
        confidence=confidence_strategy,
        start_line=st.integers(min_value=0, max_value=1000),
        line_count=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=50)
    def test_code_ref_with_line_range_round_trip(
        self,
        language: str,
        file_path: str,
        symbols: list[str],
        confidence: float,
        start_line: int,
        line_count: int,
    ):
        """For any CodeRef with line_range, round-trip preserves line_range."""
        end_line = start_line + line_count

        original = CodeRef(
            language=language,
            file_path=file_path,
            symbols=symbols,
            line_range=(start_line, end_line),
            confidence=confidence,
        )

        # Round-trip through dict
        restored = CodeRef.from_dict(original.to_dict())

        assert restored.line_range == original.line_range

    @given(
        language=language_strategy,
        file_path=path_strategy,
        symbols=symbols_strategy,
        confidence=confidence_strategy,
    )
    @settings(max_examples=50)
    def test_specblock_code_refs_round_trip(
        self,
        language: str,
        file_path: str,
        symbols: list[str],
        confidence: float,
    ):
        """For any SpecBlock with code_refs, JSON round-trip preserves refs."""
        cr = CodeRef(
            language=language,
            file_path=file_path,
            symbols=symbols,
            confidence=confidence,
        )

        block = SpecBlock(
            id="test123",
            type=SpecType.REQUIREMENT,
            text="Test requirement",
            source="test.md",
        )
        block.add_code_ref(cr)

        # Round-trip through JSON
        json_str = block.to_json()
        restored = SpecBlock.from_json(json_str)

        assert len(restored.code_refs) == 1
        restored_cr = restored.get_code_refs()[0]
        assert restored_cr.language == cr.language
        assert restored_cr.file_path == cr.file_path
        assert restored_cr.symbols == cr.symbols
        assert restored_cr.confidence == cr.confidence


class TestConfidenceRangeValidation:
    """**Feature: test-mapping-engine, Property 5: Confidence Range Validation**

    *For any* confidence value, the system SHALL reject values outside
    the range [0.0, 1.0].

    **Validates: Requirements 4.2**
    """

    @given(confidence=st.floats(min_value=1.01, max_value=100.0, allow_nan=False))
    @settings(max_examples=50)
    def test_confidence_above_1_rejected_for_test_mapping(self, confidence: float):
        """Confidence > 1.0 is rejected for TestMapping."""
        with pytest.raises(ValueError, match="confidence must be between"):
            TestMapping(
                framework="pytest",
                path="test.py",
                selector="test",
                confidence=confidence,
            )

    @given(confidence=st.floats(min_value=-100.0, max_value=-0.01, allow_nan=False))
    @settings(max_examples=50)
    def test_confidence_below_0_rejected_for_test_mapping(self, confidence: float):
        """Confidence < 0.0 is rejected for TestMapping."""
        with pytest.raises(ValueError, match="confidence must be between"):
            TestMapping(
                framework="pytest",
                path="test.py",
                selector="test",
                confidence=confidence,
            )

    @given(confidence=st.floats(min_value=1.01, max_value=100.0, allow_nan=False))
    @settings(max_examples=50)
    def test_confidence_above_1_rejected_for_code_ref(self, confidence: float):
        """Confidence > 1.0 is rejected for CodeRef."""
        with pytest.raises(ValueError, match="confidence must be between"):
            CodeRef(
                language="python",
                file_path="test.py",
                confidence=confidence,
            )

    @given(confidence=st.floats(min_value=-100.0, max_value=-0.01, allow_nan=False))
    @settings(max_examples=50)
    def test_confidence_below_0_rejected_for_code_ref(self, confidence: float):
        """Confidence < 0.0 is rejected for CodeRef."""
        with pytest.raises(ValueError, match="confidence must be between"):
            CodeRef(
                language="python",
                file_path="test.py",
                confidence=confidence,
            )

    @given(confidence=confidence_strategy)
    @settings(max_examples=100)
    def test_valid_confidence_accepted(self, confidence: float):
        """Valid confidence values [0.0, 1.0] are accepted."""
        tm = TestMapping(
            framework="pytest",
            path="test.py",
            selector="test",
            confidence=confidence,
        )
        assert tm.confidence == confidence

        cr = CodeRef(
            language="python",
            file_path="test.py",
            confidence=confidence,
        )
        assert cr.confidence == confidence

    def test_specblock_confidence_default(self):
        """SpecBlock confidence defaults to 1.0."""
        block = SpecBlock(
            id="test",
            type=SpecType.REQUIREMENT,
            text="Test",
            source="test.md",
        )
        assert block.confidence == 1.0
