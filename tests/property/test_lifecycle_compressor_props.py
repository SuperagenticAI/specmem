"""Property-based tests for spec lifecycle compressor.

**Feature: pragmatic-spec-lifecycle**
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.lifecycle.compressor import CompressorEngine


def create_spec_file(dir_path: Path, name: str, content: str) -> Path:
    """Create a spec file with given content."""
    spec_dir = dir_path / name
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "requirements.md").write_text(content)
    return spec_dir


class TestCompressionPreservesCriteriaProperties:
    """Property tests for compression preserving criteria."""

    @given(
        criteria=st.lists(
            st.from_regex(r"WHEN [a-z]+ THEN [a-z]+", fullmatch=True),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_compression_preserves_all_criteria(
        self,
        criteria: list[str],
    ) -> None:
        """**Feature: pragmatic-spec-lifecycle, Property 8: Compression Preserves Criteria**

        *For any* compressed spec, all acceptance criteria from the original spec
        SHALL be present in the compressed version, and the compressed size SHALL
        be less than or equal to the original size.

        **Validates: Requirements 4.1, 4.2**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)

            # Create verbose spec with criteria
            criteria_text = "\n".join([f"{i + 1}. {c}" for i, c in enumerate(criteria)])
            content = f"""# Test Spec

## Introduction

This is a very verbose introduction that goes on and on about various things
that are not really necessary for the agent to understand. It contains lots
of filler text that could be compressed without losing important information.
The purpose of this text is to make the spec verbose enough to trigger
compression. We need to add more and more text here to ensure the spec
exceeds the verbose threshold.

## Glossary

- **Term1**: A definition that is quite long and verbose
- **Term2**: Another definition with lots of unnecessary detail

## Requirements

### Requirement 1

**User Story:** As a user, I want something verbose.

#### Acceptance Criteria

{criteria_text}

## Additional Verbose Section

More verbose content that can be safely removed during compression.
This section adds bulk but not value to the spec.
"""
            spec_path = create_spec_file(spec_dir, "test-spec", content)

            # Compress
            compressor = CompressorEngine(
                preserve_acceptance_criteria=True,
                verbose_threshold_chars=100,  # Low threshold for testing
            )

            compressed = compressor.compress_spec("test-spec", spec_path)

            # Verify all criteria are preserved
            for criterion in criteria:
                # The criterion text should appear in compressed content
                assert (
                    criterion in compressed.compressed_content
                ), f"Criterion '{criterion}' not found in compressed content"

            # Verify preserved_criteria list contains all criteria
            assert len(compressed.preserved_criteria) >= len(criteria)

    @given(
        original_size=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=30)
    def test_compressed_size_not_larger_than_original(
        self,
        original_size: int,
    ) -> None:
        """Compressed size should not exceed original size.

        **Validates: Requirements 4.1**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)

            # Create content of specified size
            filler = "x" * (original_size - 100)
            content = f"""# Test Spec

## Introduction

{filler}

## Requirements

### Requirement 1

#### Acceptance Criteria

1. WHEN user acts THEN system responds
"""
            spec_path = create_spec_file(spec_dir, "test-spec", content)

            compressor = CompressorEngine(verbose_threshold_chars=50)
            compressed = compressor.compress_spec("test-spec", spec_path)

            # Compressed should not be larger than original
            assert compressed.compressed_size <= compressed.original_size


class TestCompressionStorageProperties:
    """Property tests for compression storage."""

    @given(
        spec_name=st.from_regex(r"[a-z][a-z0-9-]{0,19}", fullmatch=True),
    )
    @settings(max_examples=30)
    def test_both_versions_retrievable(
        self,
        spec_name: str,
    ) -> None:
        """**Feature: pragmatic-spec-lifecycle, Property 9: Compression Storage**

        *For any* spec that has been compressed, both the original and compressed
        versions SHALL be retrievable.

        **Validates: Requirements 4.3**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)

            original_content = f"""# {spec_name} Spec

## Introduction

Original verbose content for {spec_name}.

## Requirements

### Requirement 1

#### Acceptance Criteria

1. WHEN user does something THEN system responds
"""
            spec_path = create_spec_file(spec_dir, spec_name, original_content)

            compressor = CompressorEngine(
                verbose_threshold_chars=50,
                compression_storage_dir=Path(tmpdir) / "compressed",
            )

            # Compress
            compressed = compressor.compress_spec(spec_name, spec_path)

            # Verify compressed version is retrievable
            cached = compressor.get_compressed(spec_name)
            assert cached is not None
            assert cached.compressed_content == compressed.compressed_content

            # Verify original is retrievable
            original = compressor.get_original(spec_name)
            assert original is not None
            assert spec_name in original  # Original content should contain spec name


class TestVerboseFlaggingProperties:
    """Property tests for verbose flagging consistency."""

    @given(
        content_size=st.integers(min_value=100, max_value=20000),
        threshold=st.integers(min_value=1000, max_value=10000),
    )
    @settings(max_examples=50)
    def test_verbose_flagging_consistent_with_threshold(
        self,
        content_size: int,
        threshold: int,
    ) -> None:
        """**Feature: pragmatic-spec-lifecycle, Property 10: Verbose Flagging Consistency**

        *For any* spec with compression ratio exceeding the configured threshold,
        the spec SHALL be flagged as verbose in health reports.

        **Validates: Requirements 4.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)

            # Create content of specified size
            filler = "x" * max(0, content_size - 50)
            content = f"# Test\n\n{filler}"
            spec_path = create_spec_file(spec_dir, "test-spec", content)

            compressor = CompressorEngine(verbose_threshold_chars=threshold)

            # Check if flagged as verbose
            is_verbose = compressor.is_verbose("test-spec", spec_path)

            # Should be verbose if content exceeds threshold
            expected_verbose = content_size > threshold
            assert is_verbose == expected_verbose, (
                f"Content size {content_size}, threshold {threshold}: "
                f"expected verbose={expected_verbose}, got {is_verbose}"
            )

    @given(
        num_specs=st.integers(min_value=1, max_value=5),
        verbose_indices=st.lists(st.integers(min_value=0, max_value=4), max_size=3),
    )
    @settings(max_examples=30)
    def test_get_verbose_specs_returns_correct_list(
        self,
        num_specs: int,
        verbose_indices: list[int],
    ) -> None:
        """get_verbose_specs should return exactly the specs exceeding threshold.

        **Validates: Requirements 4.5**
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            spec_dir = Path(tmpdir)
            threshold = 500

            # Create specs, some verbose some not
            specs: list[tuple[str, Path]] = []
            expected_verbose: set[str] = set()

            for i in range(num_specs):
                spec_name = f"spec-{i}"

                # Make verbose if index is in verbose_indices
                if i in verbose_indices:
                    content = "# Verbose\n\n" + "x" * (threshold + 100)
                    expected_verbose.add(spec_name)
                else:
                    content = "# Short\n\nBrief content."

                spec_path = create_spec_file(spec_dir, spec_name, content)
                specs.append((spec_name, spec_path))

            compressor = CompressorEngine(verbose_threshold_chars=threshold)
            verbose_list = compressor.get_verbose_specs(specs)

            assert set(verbose_list) == expected_verbose
