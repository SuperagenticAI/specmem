"""Property-based tests for SpecBlock model.

These tests use Hypothesis to verify universal properties that should hold
across all valid inputs.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from specmem.core.specir import SpecBlock, SpecStatus, SpecType


# Strategies for generating valid SpecBlock data
spec_type_strategy = st.sampled_from(list(SpecType))
spec_status_strategy = st.sampled_from(list(SpecStatus))

# Non-empty text that isn't just whitespace
valid_text_strategy = st.text(min_size=1).filter(lambda x: x.strip())

# Source paths
source_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())

# Tags and links
tags_strategy = st.lists(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()), max_size=10)
links_strategy = st.lists(
    st.text(min_size=16, max_size=16, alphabet="0123456789abcdef"), max_size=5
)


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
        tags=draw(tags_strategy),
        links=draw(links_strategy),
        pinned=draw(st.booleans()),
    )


# Feature: specmem-mvp, Property 1: SpecBlock Serialization Round-Trip
# Validates: Requirements 2.6, 2.7
@given(block=valid_specblock_strategy())
@settings(max_examples=100)
def test_specblock_serialization_roundtrip(block: SpecBlock) -> None:
    """For any valid SpecBlock, serializing to JSON and deserializing back
    SHALL produce an equivalent SpecBlock with identical field values.
    """
    # Serialize to JSON
    json_str = block.to_json()

    # Deserialize back
    restored = SpecBlock.from_json(json_str)

    # Verify all fields are identical
    assert restored.id == block.id
    assert restored.type == block.type
    assert restored.text == block.text
    assert restored.source == block.source
    assert restored.status == block.status
    assert restored.tags == block.tags
    assert restored.links == block.links
    assert restored.pinned == block.pinned

    # Also verify model equality
    assert restored == block


# Feature: specmem-mvp, Property 2: SpecBlock ID Determinism
# Validates: Requirements 2.2
@given(source=source_strategy, text=valid_text_strategy)
@settings(max_examples=100)
def test_specblock_id_determinism(source: str, text: str) -> None:
    """For any source path and text content, generating a SpecBlock ID
    multiple times SHALL always produce the same ID value.
    """
    id1 = SpecBlock.generate_id(source, text)
    id2 = SpecBlock.generate_id(source, text)
    id3 = SpecBlock.generate_id(source, text)

    assert id1 == id2
    assert id2 == id3

    # ID should be 16 characters hex
    assert len(id1) == 16
    assert all(c in "0123456789abcdef" for c in id1)


# Feature: specmem-mvp, Property 3: Empty Text Rejection
# Validates: Requirements 2.5
@given(whitespace=st.text(alphabet=" \t\n\r", min_size=0, max_size=100))
@settings(max_examples=100)
def test_empty_text_rejection(whitespace: str) -> None:
    """For any string composed entirely of whitespace characters,
    creating a SpecBlock with that text SHALL raise a validation error.
    """
    with pytest.raises(ValidationError):
        SpecBlock(
            id="test123456789abc",
            type=SpecType.REQUIREMENT,
            text=whitespace,
            source="test.md",
        )


# Additional property: Different inputs produce different IDs
@given(
    source1=source_strategy,
    text1=valid_text_strategy,
    source2=source_strategy,
    text2=valid_text_strategy,
)
@settings(max_examples=100)
def test_different_inputs_different_ids(source1: str, text1: str, source2: str, text2: str) -> None:
    """Different source/text combinations should produce different IDs
    (with very high probability due to hash collision resistance).
    """
    # Skip if inputs are identical
    if source1 == source2 and text1 == text2:
        return

    id1 = SpecBlock.generate_id(source1, text1)
    id2 = SpecBlock.generate_id(source2, text2)

    # Different inputs should produce different IDs
    assert id1 != id2
