"""Property-based tests for Agent Experience Pack Builder.

These tests verify that the pack builder correctly includes all active blocks.
"""

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.agentx.pack_builder import PackBuilder
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


# Strategies for generating test data
spec_type_strategy = st.sampled_from(list(SpecType))
active_status_strategy = st.just(SpecStatus.ACTIVE)
legacy_status_strategy = st.sampled_from([SpecStatus.LEGACY, SpecStatus.OBSOLETE])

valid_text_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
source_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())


@st.composite
def active_specblock_strategy(draw: st.DrawFn) -> SpecBlock:
    """Generate active SpecBlock instances."""
    source = draw(source_strategy)
    text = draw(valid_text_strategy)
    block_id = SpecBlock.generate_id(source, text)

    return SpecBlock(
        id=block_id,
        type=draw(spec_type_strategy),
        text=text,
        source=source,
        status=SpecStatus.ACTIVE,
        tags=[],
        links=[],
        pinned=draw(st.booleans()),
    )


@st.composite
def legacy_specblock_strategy(draw: st.DrawFn) -> SpecBlock:
    """Generate legacy SpecBlock instances."""
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


# Feature: specmem-mvp, Property 10: Agent Pack Completeness
# Validates: Requirements 7.2
@given(
    active_blocks=st.lists(
        active_specblock_strategy(), min_size=1, max_size=10, unique_by=lambda b: b.id
    ),
)
@settings(max_examples=50)
def test_agent_pack_completeness(active_blocks: list[SpecBlock]) -> None:
    """For any set of active SpecBlocks, the generated Agent Experience Pack
    SHALL contain all active blocks in agent_memory.json.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / ".specmem"
        builder = PackBuilder(output_dir=str(output_dir))

        # Build pack with active blocks only
        builder.build(active_blocks)

        # Read agent_memory.json
        memory_path = output_dir / "agent_memory.json"
        assert memory_path.exists(), "agent_memory.json should be created"

        with open(memory_path) as f:
            memory_data = json.load(f)

        # Extract block IDs from memory
        memory_block_ids = {b["id"] for b in memory_data["blocks"]}

        # All active blocks should be in memory
        active_block_ids = {b.id for b in active_blocks}
        assert (
            active_block_ids == memory_block_ids
        ), f"Expected {active_block_ids}, got {memory_block_ids}"


@given(
    blocks=st.lists(active_specblock_strategy(), min_size=1, max_size=5, unique_by=lambda b: b.id)
)
@settings(max_examples=30)
def test_knowledge_index_contains_all_blocks(blocks: list[SpecBlock]) -> None:
    """Knowledge index should reference all active blocks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / ".specmem"
        builder = PackBuilder(output_dir=str(output_dir))

        builder.build(blocks)

        # Read knowledge_index.json
        index_path = output_dir / "knowledge_index.json"
        assert index_path.exists(), "knowledge_index.json should be created"

        with open(index_path) as f:
            index_data = json.load(f)

        # All blocks should be in type_index
        all_indexed_ids = set()
        for ids in index_data["type_index"].values():
            all_indexed_ids.update(ids)

        block_ids = {b.id for b in blocks}
        assert (
            block_ids == all_indexed_ids
        ), f"Expected {block_ids} in type_index, got {all_indexed_ids}"


def test_pack_creates_all_files() -> None:
    """Pack builder should create all required files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / ".specmem"
        builder = PackBuilder(output_dir=str(output_dir))

        block = SpecBlock(
            id="test123",
            type=SpecType.REQUIREMENT,
            text="Test requirement for pack builder",
            source="test.md",
        )

        builder.build([block])

        # Check all files exist
        assert (output_dir / "agent_memory.json").exists()
        assert (output_dir / "knowledge_index.json").exists()
        assert (output_dir / "agent_context.md").exists()


def test_pack_preserves_user_content() -> None:
    """Pack builder should preserve user modifications to agent_context.md."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / ".specmem"
        output_dir.mkdir(parents=True)

        # Create existing agent_context.md with user content
        context_path = output_dir / "agent_context.md"
        context_path.write_text(
            "# Old Content\n\n"
            "<!-- USER -->\n"
            "My custom notes that should be preserved.\n"
            "<!-- /USER -->\n"
        )

        builder = PackBuilder(output_dir=str(output_dir))

        block = SpecBlock(
            id="test123",
            type=SpecType.REQUIREMENT,
            text="Test requirement",
            source="test.md",
        )

        builder.build([block], preserve_context=True)

        # Check user content is preserved
        new_content = context_path.read_text()
        assert "My custom notes that should be preserved." in new_content
        assert "<!-- USER -->" in new_content
        assert "<!-- /USER -->" in new_content
