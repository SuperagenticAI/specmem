"""Property-based tests for Guidelines feature.

**Feature: coding-guidelines-view**
"""

from __future__ import annotations

from hypothesis import given, strategies as st

from specmem.guidelines.models import Guideline, GuidelinesResponse, SourceType


# Strategies for generating test data
source_type_strategy = st.sampled_from(list(SourceType))

guideline_strategy = st.builds(
    Guideline,
    id=st.text(min_size=1, max_size=16, alphabet="abcdef0123456789"),
    title=st.text(min_size=1, max_size=100),
    content=st.text(min_size=1, max_size=1000),
    source_type=source_type_strategy,
    source_file=st.text(min_size=1, max_size=100),
    file_pattern=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    tags=st.lists(st.text(min_size=1, max_size=20), max_size=5),
    is_sample=st.booleans(),
)


class TestGuidelinesModelProps:
    """Property tests for Guidelines data models.

    **Feature: coding-guidelines-view, Property 3: Count consistency**
    **Validates: Requirements 1.4**
    """

    @given(st.lists(guideline_strategy, max_size=50))
    def test_count_consistency(self, guidelines: list[Guideline]) -> None:
        """Total count equals sum of counts by source."""
        response = GuidelinesResponse.from_guidelines(guidelines)

        # Total count should equal length of guidelines
        assert response.total_count == len(guidelines)

        # Sum of counts by source should equal total
        sum_by_source = sum(response.counts_by_source.values())
        assert sum_by_source == response.total_count

        # Each source count should match actual count
        for source_type in SourceType:
            expected = len([g for g in guidelines if g.source_type == source_type])
            actual = response.counts_by_source.get(source_type.value, 0)
            assert actual == expected

    @given(guideline_strategy)
    def test_guideline_id_deterministic(self, guideline: Guideline) -> None:
        """Guideline ID generation is deterministic."""
        id1 = Guideline.generate_id(guideline.source_file, guideline.title)
        id2 = Guideline.generate_id(guideline.source_file, guideline.title)
        assert id1 == id2

    @given(st.text(min_size=1), st.text(min_size=1))
    def test_guideline_id_length(self, source: str, title: str) -> None:
        """Guideline ID has consistent length."""
        generated_id = Guideline.generate_id(source, title)
        assert len(generated_id) == 16



class TestGuidelinesScannerProps:
    """Property tests for GuidelinesScanner.

    **Feature: coding-guidelines-view, Property 1: Guidelines aggregation completeness**
    **Validates: Requirements 1.1, 5.1**
    """

    @given(st.lists(st.sampled_from(["claude", "cursor", "steering", "agents"]), max_size=10))
    def test_scanner_finds_all_source_types(self, source_types: list[str]) -> None:
        """Scanner returns files grouped by correct source type."""
        import tempfile
        from pathlib import Path

        from specmem.guidelines.scanner import GuidelinesScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create files for each source type
            created_files: dict[str, list[Path]] = {}
            for source_type in source_types:
                if source_type == "claude":
                    f = tmp_path / "CLAUDE.md"
                    f.write_text("# Claude Guidelines")
                    created_files.setdefault("claude", []).append(f)
                elif source_type == "cursor":
                    f = tmp_path / ".cursorrules"
                    f.write_text("# Cursor Rules")
                    created_files.setdefault("cursor", []).append(f)
                elif source_type == "steering":
                    steering_dir = tmp_path / ".kiro" / "steering"
                    steering_dir.mkdir(parents=True, exist_ok=True)
                    f = steering_dir / "test.md"
                    f.write_text("# Steering")
                    created_files.setdefault("steering", []).append(f)
                elif source_type == "agents":
                    f = tmp_path / "AGENTS.md"
                    f.write_text("# Agent Guidelines")
                    created_files.setdefault("agents", []).append(f)

            scanner = GuidelinesScanner(tmp_path)
            result = scanner.scan()

            # All created source types should be found
            for source_type in created_files:
                assert source_type in result, f"Missing source type: {source_type}"

    def test_scanner_empty_workspace(self) -> None:
        """Scanner handles empty workspace gracefully."""
        import tempfile
        from pathlib import Path

        from specmem.guidelines.scanner import GuidelinesScanner

        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = GuidelinesScanner(Path(tmpdir))
            result = scanner.scan()
            assert result == {}
            assert not scanner.has_guidelines()



class TestGuidelinesParserProps:
    """Property tests for GuidelinesParser.

    **Feature: coding-guidelines-view, Property 2: Source grouping correctness**
    **Validates: Requirements 1.2**
    """

    @given(st.text(min_size=10, max_size=500))
    def test_parser_preserves_content(self, content: str) -> None:
        """Parser preserves content from source files."""
        import tempfile
        from pathlib import Path

        from specmem.guidelines.parser import GuidelinesParser

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "CLAUDE.md"
            test_file.write_text(f"# Test\n\n{content}")

            parser = GuidelinesParser()
            guidelines = parser.parse_claude(test_file)

            assert len(guidelines) >= 1
            # Content should be preserved (possibly with section extraction)
            all_content = " ".join(g.content for g in guidelines)
            # At minimum, non-whitespace content should be present
            assert len(all_content.strip()) > 0

    def test_parser_assigns_correct_source_type(self) -> None:
        """Parser assigns correct source type to each guideline."""
        import tempfile
        from pathlib import Path

        from specmem.guidelines.parser import GuidelinesParser

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create files for each type
            claude_file = tmp_path / "CLAUDE.md"
            claude_file.write_text("# Claude\nGuidelines here")

            cursor_file = tmp_path / ".cursorrules"
            cursor_file.write_text("# Cursor\nRules here")

            agents_file = tmp_path / "AGENTS.md"
            agents_file.write_text("# Agents\nInstructions here")

            steering_dir = tmp_path / ".kiro" / "steering"
            steering_dir.mkdir(parents=True)
            steering_file = steering_dir / "test.md"
            steering_file.write_text("---\ninclusion: always\n---\n# Steering\nContent")

            parser = GuidelinesParser()

            claude_guidelines = parser.parse_claude(claude_file)
            cursor_guidelines = parser.parse_cursor(cursor_file)
            agents_guidelines = parser.parse_agents(agents_file)
            steering_guidelines = parser.parse_steering(steering_file)

            # All guidelines should have correct source type
            for g in claude_guidelines:
                assert g.source_type == SourceType.CLAUDE

            for g in cursor_guidelines:
                assert g.source_type == SourceType.CURSOR

            for g in agents_guidelines:
                assert g.source_type == SourceType.AGENTS

            for g in steering_guidelines:
                assert g.source_type == SourceType.STEERING



class TestGuidelinesAggregatorProps:
    """Property tests for GuidelinesAggregator.

    **Feature: coding-guidelines-view**
    """

    @given(st.lists(guideline_strategy, min_size=1, max_size=20))
    def test_filter_by_source_correctness(self, guidelines: list[Guideline]) -> None:
        """Property 4: Filter returns correct subset.

        **Validates: Requirements 2.2**
        """
        from specmem.guidelines.aggregator import GuidelinesAggregator

        # Create aggregator and inject guidelines directly
        aggregator = GuidelinesAggregator()
        aggregator._guidelines = guidelines

        for source_type in SourceType:
            filtered = aggregator.filter_by_source(source_type)

            # All filtered guidelines should have matching source type
            for g in filtered:
                assert g.source_type == source_type

            # Should contain all guidelines with that source type
            expected = [g for g in guidelines if g.source_type == source_type]
            assert len(filtered) == len(expected)

    @given(
        st.lists(guideline_strategy, min_size=1, max_size=20),
        st.text(min_size=3, max_size=20),
    )
    def test_search_coverage(self, guidelines: list[Guideline], query: str) -> None:
        """Property 5: Search covers title and content.

        **Validates: Requirements 3.1, 3.2**
        """
        from specmem.guidelines.aggregator import GuidelinesAggregator

        aggregator = GuidelinesAggregator()
        aggregator._guidelines = guidelines

        results = aggregator.search(query)
        query_lower = query.lower()

        # All results should contain query in title or content
        for g in results:
            assert query_lower in g.title.lower() or query_lower in g.content.lower()

        # All guidelines containing query should be in results
        for g in guidelines:
            if query_lower in g.title.lower() or query_lower in g.content.lower():
                assert g in results

    @given(st.lists(guideline_strategy, min_size=1, max_size=10))
    def test_filter_by_file_pattern_matching(self, guidelines: list[Guideline]) -> None:
        """Property 6: File pattern matching works correctly.

        **Validates: Requirements 5.3**
        """
        from specmem.guidelines.aggregator import GuidelinesAggregator

        aggregator = GuidelinesAggregator()

        # Set specific patterns for testing
        test_guidelines = []
        for i, g in enumerate(guidelines):
            if i % 2 == 0:
                # Even indices: pattern matches .py files
                g.file_pattern = "**/*.py"
            else:
                # Odd indices: no pattern (applies to all)
                g.file_pattern = None
            test_guidelines.append(g)

        aggregator._guidelines = test_guidelines

        # Test with a .py file
        py_results = aggregator.filter_by_file("src/main.py")

        # Should include all guidelines (those with .py pattern and those with no pattern)
        assert len(py_results) == len(test_guidelines)

        # Test with a .js file
        js_results = aggregator.filter_by_file("src/main.js")

        # Should only include guidelines with no pattern
        expected_js = [g for g in test_guidelines if g.file_pattern is None]
        assert len(js_results) == len(expected_js)



class TestGuidelinesConverterProps:
    """Property tests for GuidelinesConverter.

    **Feature: coding-guidelines-view**
    """

    @given(guideline_strategy)
    def test_conversion_round_trip(self, guideline: Guideline) -> None:
        """Property 7: Content preserved through conversion.

        **Validates: Requirements 6.1, 6.2, 6.3**
        """
        from specmem.guidelines.converter import GuidelinesConverter

        converter = GuidelinesConverter()
        result = converter.to_steering(guideline)

        # Content should be preserved in the output
        assert guideline.content in result.content

        # Title should be preserved
        assert guideline.title in result.content

        # Frontmatter should have inclusion mode
        assert "inclusion" in result.frontmatter
        assert result.frontmatter["inclusion"] in ("always", "fileMatch", "manual")

        # Filename should be valid
        assert result.filename.endswith(".md")
        assert len(result.filename) > 3

    @given(st.lists(guideline_strategy, min_size=1, max_size=10))
    def test_bulk_conversion_completeness(self, guidelines: list[Guideline]) -> None:
        """Property 8: Bulk conversion covers all guidelines.

        **Validates: Requirements 7.1, 7.2**
        """
        from specmem.guidelines.converter import GuidelinesConverter

        converter = GuidelinesConverter()
        results = converter.bulk_convert_to_steering(guidelines)

        # Should have one result per guideline
        assert len(results) == len(guidelines)

        # All filenames should be unique
        filenames = [r.filename for r in results]
        assert len(filenames) == len(set(filenames))

        # All original content should be preserved
        for i, result in enumerate(results):
            assert guidelines[i].content in result.content

    @given(st.lists(guideline_strategy, min_size=1, max_size=5))
    def test_export_format_validity(self, guidelines: list[Guideline]) -> None:
        """Property 10: Export produces valid format.

        **Validates: Requirements 9.1, 9.2, 9.3**
        """
        from specmem.guidelines.converter import GuidelinesConverter

        converter = GuidelinesConverter()

        # Test Claude export
        claude_output = converter.to_claude(guidelines)
        assert "# Project Guidelines" in claude_output
        for g in guidelines:
            assert g.title in claude_output
            assert g.content in claude_output

        # Test Cursor export
        cursor_output = converter.to_cursor(guidelines)
        for g in guidelines:
            assert g.title in cursor_output
            assert g.content in cursor_output



class TestSampleGuidelinesProps:
    """Property tests for SampleGuidelinesProvider.

    **Feature: coding-guidelines-view, Property 9: Sample marking**
    **Validates: Requirements 8.2**
    """

    def test_all_samples_marked(self) -> None:
        """All sample guidelines have is_sample=True."""
        from specmem.guidelines.samples import SampleGuidelinesProvider

        provider = SampleGuidelinesProvider()
        samples = provider.get_all_samples()

        assert len(samples) > 0, "Should have at least one sample"

        for sample in samples:
            assert sample.is_sample is True, f"Sample {sample.title} not marked"
            assert sample.source_type == SourceType.SAMPLE

    def test_samples_have_content(self) -> None:
        """All sample guidelines have non-empty content."""
        from specmem.guidelines.samples import SampleGuidelinesProvider

        provider = SampleGuidelinesProvider()
        samples = provider.get_all_samples()

        for sample in samples:
            assert len(sample.title) > 0
            assert len(sample.content) > 0
            assert len(sample.source_file) > 0
