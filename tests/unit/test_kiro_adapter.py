"""Unit tests for KiroAdapter.

Tests detection, parsing, and error handling for Kiro spec files.
"""

import tempfile
from pathlib import Path

import pytest

from specmem.adapters.kiro import KiroAdapter
from specmem.core.specir import SpecStatus, SpecType


@pytest.fixture
def adapter() -> KiroAdapter:
    """Create a KiroAdapter instance."""
    return KiroAdapter()


@pytest.fixture
def temp_repo():
    """Create a temporary repository directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestKiroAdapterDetection:
    """Tests for KiroAdapter.detect()"""

    def test_detect_with_valid_kiro_directory(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should detect when .kiro/specs exists with spec files."""
        # Create valid Kiro structure
        spec_dir = temp_repo / ".kiro" / "specs" / "my-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "requirements.md").write_text("# Requirements")

        assert adapter.detect(str(temp_repo)) is True

    def test_detect_with_missing_kiro_directory(
        self, adapter: KiroAdapter, temp_repo: Path
    ) -> None:
        """Should not detect when .kiro directory is missing."""
        assert adapter.detect(str(temp_repo)) is False

    def test_detect_with_empty_specs_directory(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should not detect when specs directory is empty."""
        specs_dir = temp_repo / ".kiro" / "specs"
        specs_dir.mkdir(parents=True)

        assert adapter.detect(str(temp_repo)) is False

    def test_detect_with_design_file_only(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should detect when only design.md exists."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "design.md").write_text("# Design")

        assert adapter.detect(str(temp_repo)) is True

    def test_detect_with_tasks_file_only(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should detect when only tasks.md exists."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "tasks.md").write_text("# Tasks")

        assert adapter.detect(str(temp_repo)) is True


class TestKiroAdapterRequirementsParsing:
    """Tests for parsing requirements.md files."""

    def test_parse_requirements_with_user_story(
        self, adapter: KiroAdapter, temp_repo: Path
    ) -> None:
        """Should extract user stories from requirements."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        requirements_content = """# Requirements

### Requirement 1: User Authentication

**User Story:** As a user, I want to log in securely, so that my data is protected.

#### Acceptance Criteria

1. WHEN a user enters valid credentials THEN the system SHALL authenticate them
2. WHEN a user enters invalid credentials THEN the system SHALL reject the login
"""
        (spec_dir / "requirements.md").write_text(requirements_content)

        blocks = adapter.load(str(temp_repo))

        # Should have user story and acceptance criteria
        assert len(blocks) >= 1

        # Check for requirement blocks
        req_blocks = [b for b in blocks if b.type == SpecType.REQUIREMENT]
        assert len(req_blocks) >= 1

    def test_parse_requirements_with_shall_keyword_pins_block(
        self, adapter: KiroAdapter, temp_repo: Path
    ) -> None:
        """Blocks with SHALL keyword should be pinned."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        requirements_content = """# Requirements

### Requirement 1

**User Story:** Test story

#### Acceptance Criteria

1. WHEN something happens THEN the system SHALL do something
"""
        (spec_dir / "requirements.md").write_text(requirements_content)

        blocks = adapter.load(str(temp_repo))

        # Find blocks with SHALL
        shall_blocks = [b for b in blocks if "SHALL" in b.text.upper()]
        assert len(shall_blocks) >= 1
        assert all(b.pinned for b in shall_blocks)


class TestKiroAdapterDesignParsing:
    """Tests for parsing design.md files."""

    def test_parse_design_sections(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should extract design sections."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        design_content = """# Design Document

## Overview

This is the overview section with important design information.

## Architecture

The system uses a layered architecture with clear separation of concerns.

## Components

Various components work together to provide functionality.
"""
        (spec_dir / "design.md").write_text(design_content)

        blocks = adapter.load(str(temp_repo))

        # Should have design blocks
        design_blocks = [b for b in blocks if b.type == SpecType.DESIGN]
        assert len(design_blocks) >= 2

        # Check tags
        for block in design_blocks:
            assert "design" in block.tags


class TestKiroAdapterTasksParsing:
    """Tests for parsing tasks.md files."""

    def test_parse_tasks_with_checkboxes(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should extract tasks from checkbox lists."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        tasks_content = """# Implementation Plan

- [ ] 1. Set up project structure
- [ ] 2. Implement core models
- [x] 3. Write tests
- [ ] 4. Documentation
"""
        (spec_dir / "tasks.md").write_text(tasks_content)

        blocks = adapter.load(str(temp_repo))

        # Should have task blocks
        task_blocks = [b for b in blocks if b.type == SpecType.TASK]
        assert len(task_blocks) >= 3

    def test_completed_tasks_marked_as_legacy(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Completed tasks (checked) should be marked as legacy."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        tasks_content = """# Tasks

- [x] 1. Completed task
- [ ] 2. Pending task
"""
        (spec_dir / "tasks.md").write_text(tasks_content)

        blocks = adapter.load(str(temp_repo))
        task_blocks = [b for b in blocks if b.type == SpecType.TASK]

        # Find completed and pending tasks
        completed = [b for b in task_blocks if "Completed" in b.text]
        pending = [b for b in task_blocks if "Pending" in b.text]

        if completed:
            assert completed[0].status == SpecStatus.LEGACY
        if pending:
            assert pending[0].status == SpecStatus.ACTIVE


class TestKiroAdapterErrorHandling:
    """Tests for error handling."""

    def test_handles_malformed_content_gracefully(
        self, adapter: KiroAdapter, temp_repo: Path
    ) -> None:
        """Should handle malformed content without crashing."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        # Write malformed content
        (spec_dir / "requirements.md").write_text("This is not valid markdown structure")

        # Should not raise, should return empty or partial results
        blocks = adapter.load(str(temp_repo))
        assert isinstance(blocks, list)

    def test_handles_empty_files(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should handle empty files gracefully."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        (spec_dir / "requirements.md").write_text("")
        (spec_dir / "design.md").write_text("")
        (spec_dir / "tasks.md").write_text("")

        blocks = adapter.load(str(temp_repo))
        assert isinstance(blocks, list)

    def test_handles_missing_files(self, adapter: KiroAdapter, temp_repo: Path) -> None:
        """Should handle missing files gracefully."""
        spec_dir = temp_repo / ".kiro" / "specs" / "feature"
        spec_dir.mkdir(parents=True)

        # Only create one file
        (spec_dir / "requirements.md").write_text("# Requirements")

        blocks = adapter.load(str(temp_repo))
        assert isinstance(blocks, list)


class TestKiroAdapterProperties:
    """Tests for adapter properties."""

    def test_adapter_name(self, adapter: KiroAdapter) -> None:
        """Adapter should have correct name."""
        assert adapter.name == "Kiro"

    def test_adapter_repr(self, adapter: KiroAdapter) -> None:
        """Adapter repr should be informative."""
        repr_str = repr(adapter)
        assert "KiroAdapter" in repr_str
        assert "Kiro" in repr_str
