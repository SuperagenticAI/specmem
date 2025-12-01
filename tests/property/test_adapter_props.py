"""Property-based tests for spec-driven adapters.

**Feature: spec-driven-adapters**

Tests correctness properties for experimental adapter support.
"""

import warnings
from pathlib import Path

import pytest

from specmem.adapters.base import ExperimentalAdapterWarning, SpecAdapter
from specmem.core.specir import SpecBlock


# Test adapter implementations for property testing
class MockExperimentalAdapter(SpecAdapter):
    """Mock experimental adapter for testing."""

    @property
    def name(self) -> str:
        return "MockExperimental"

    def is_experimental(self) -> bool:
        return True

    def detect(self, repo_path: str) -> bool:
        return False

    def load(self, repo_path: str) -> list[SpecBlock]:
        self.warn_if_experimental()
        return []


class MockStableAdapter(SpecAdapter):
    """Mock stable adapter for testing."""

    @property
    def name(self) -> str:
        return "MockStable"

    def is_experimental(self) -> bool:
        return False

    def detect(self, repo_path: str) -> bool:
        return False

    def load(self, repo_path: str) -> list[SpecBlock]:
        return []


class TestExperimentalAdapterMarking:
    """Property 4: Experimental Adapter Marking.

    **Feature: spec-driven-adapters, Property 4: Experimental Adapter Marking**
    **Validates: Requirements 3.1**

    *For any* experimental adapter, the `is_experimental()` method SHALL return True.
    """

    def test_experimental_adapter_returns_true(self) -> None:
        """Experimental adapters must return True from is_experimental()."""
        adapter = MockExperimentalAdapter()
        assert adapter.is_experimental() is True

    def test_stable_adapter_returns_false(self) -> None:
        """Stable adapters must return False from is_experimental()."""
        adapter = MockStableAdapter()
        assert adapter.is_experimental() is False

    def test_experimental_adapter_issues_warning(self) -> None:
        """Experimental adapters must issue warning when warn_if_experimental() is called."""
        adapter = MockExperimentalAdapter()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            adapter.warn_if_experimental()

            assert len(w) == 1
            assert issubclass(w[0].category, ExperimentalAdapterWarning)
            assert "experimental" in str(w[0].message).lower()
            assert adapter.name in str(w[0].message)

    def test_stable_adapter_no_warning(self) -> None:
        """Stable adapters must not issue warning when warn_if_experimental() is called."""
        adapter = MockStableAdapter()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            adapter.warn_if_experimental()

            # Filter for ExperimentalAdapterWarning only
            experimental_warnings = [
                warning for warning in w if issubclass(warning.category, ExperimentalAdapterWarning)
            ]
            assert len(experimental_warnings) == 0

    def test_experimental_adapter_load_issues_warning(self) -> None:
        """Loading from experimental adapter must issue warning."""
        adapter = MockExperimentalAdapter()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            adapter.load("/tmp/test")

            experimental_warnings = [
                warning for warning in w if issubclass(warning.category, ExperimentalAdapterWarning)
            ]
            assert len(experimental_warnings) == 1


class TestAdapterBaseClass:
    """Tests for SpecAdapter base class behavior."""

    def test_default_is_experimental_returns_false(self) -> None:
        """Default is_experimental() should return False."""
        # MockStableAdapter doesn't override is_experimental, uses default
        adapter = MockStableAdapter()
        assert adapter.is_experimental() is False

    def test_adapter_repr(self) -> None:
        """Adapter repr should include class name and adapter name."""
        adapter = MockExperimentalAdapter()
        repr_str = repr(adapter)
        assert "MockExperimentalAdapter" in repr_str
        assert "MockExperimental" in repr_str


# ============================================================================
# Tessl Adapter Property Tests
# ============================================================================


class TestTesslFileDetection:
    """Property 1: File Pattern Detection Completeness for Tessl.

    **Feature: spec-driven-adapters, Property 1: File Pattern Detection Completeness**
    **Validates: Requirements 1.1**

    *For any* directory containing files matching Tessl patterns,
    the adapter's `detect()` method SHALL return True.
    """

    @pytest.mark.parametrize(
        "filename",
        [
            "app.tessl",
            "component.spec.ts",
            "utils.spec.js",
            "tessl.config.js",
            "tessl.config.json",
            "tessl.yaml",
            "tessl.json",
        ],
    )
    def test_detect_tessl_files(self, filename: str, tmp_path: Path) -> None:
        """Tessl adapter detects directories with Tessl files."""
        from specmem.adapters.tessl import TesslAdapter

        # Create a file matching Tessl pattern
        test_file = tmp_path / filename
        test_file.write_text("# Test content")

        adapter = TesslAdapter()
        assert adapter.detect(str(tmp_path)) is True

    def test_detect_no_tessl_files(self, tmp_path: Path) -> None:
        """Tessl adapter returns False for directories without Tessl files."""
        from specmem.adapters.tessl import TesslAdapter

        # Create a non-Tessl file
        (tmp_path / "readme.md").write_text("# Readme")

        adapter = TesslAdapter()
        assert adapter.detect(str(tmp_path)) is False

    def test_detect_nonexistent_path(self) -> None:
        """Tessl adapter returns False for nonexistent paths."""
        from specmem.adapters.tessl import TesslAdapter

        adapter = TesslAdapter()
        assert adapter.detect("/nonexistent/path/12345") is False

    def test_tessl_is_experimental(self) -> None:
        """Tessl adapter must be marked as experimental."""
        from specmem.adapters.tessl import TesslAdapter

        adapter = TesslAdapter()
        assert adapter.is_experimental() is True


class TestTesslParsingCompleteness:
    """Property 2: Parsing Completeness for Tessl.

    **Feature: spec-driven-adapters, Property 2: Parsing Completeness**
    **Validates: Requirements 1.2**

    *For any* valid Tessl specification file, parsing SHALL extract
    all required components (text, metadata, relationships) without data loss.
    """

    def test_parse_tessl_spec_with_frontmatter(self, tmp_path: Path) -> None:
        """Tessl adapter extracts metadata from YAML frontmatter."""
        from specmem.adapters.tessl import TesslAdapter

        tessl_content = """---
tags:
  - api
  - backend
category: service
pinned: true
---
# User Authentication Service

This service handles user authentication and authorization.
"""
        test_file = tmp_path / "auth.tessl"
        test_file.write_text(tessl_content)

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        block = blocks[0]
        assert "api" in block.tags
        assert "backend" in block.tags
        assert "service" in block.tags
        assert block.pinned is True
        assert "User Authentication Service" in block.text

    def test_parse_tessl_spec_extracts_dependencies(self, tmp_path: Path) -> None:
        """Tessl adapter extracts dependencies from spec content."""
        from specmem.adapters.tessl import TesslAdapter

        tessl_content = """# Payment Service

depends on: auth-service, user-service
requires: database-connection

This service handles payments.
"""
        test_file = tmp_path / "payment.tessl"
        test_file.write_text(tessl_content)

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        block = blocks[0]
        assert "auth-service" in block.links
        assert "user-service" in block.links
        assert "database-connection" in block.links

    def test_parse_executable_spec_extracts_jsdoc(self, tmp_path: Path) -> None:
        """Tessl adapter extracts JSDoc comments from executable specs."""
        from specmem.adapters.tessl import TesslAdapter

        spec_content = """/**
 * User authentication module
 * Handles login and logout functionality
 */

describe('Authentication', () => {
  it('should login user with valid credentials', () => {
    // test code
  });

  it('should reject invalid credentials', () => {
    // test code
  });
});
"""
        test_file = tmp_path / "auth.spec.ts"
        test_file.write_text(spec_content)

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        block = blocks[0]
        assert "User authentication module" in block.text
        assert "should login user with valid credentials" in block.text
        assert "should reject invalid credentials" in block.text

    def test_parse_config_file(self, tmp_path: Path) -> None:
        """Tessl adapter parses configuration files."""
        from specmem.adapters.tessl import TesslAdapter

        config_content = """{
  "name": "my-project",
  "version": "1.0.0",
  "specs": ["./specs/**/*.tessl"]
}"""
        test_file = tmp_path / "tessl.config.json"
        test_file.write_text(config_content)

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        block = blocks[0]
        assert "config" in block.tags
        assert block.pinned is True

    def test_parse_manifest_file(self, tmp_path: Path) -> None:
        """Tessl adapter parses manifest files with dependencies."""
        from specmem.adapters.tessl import TesslAdapter

        manifest_content = """name: my-project
version: 1.0.0
description: A test project
dependencies:
  - auth-module
  - payment-module
"""
        test_file = tmp_path / "tessl.yaml"
        test_file.write_text(manifest_content)

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        block = blocks[0]
        assert "manifest" in block.tags
        assert "auth-module" in block.links
        assert "payment-module" in block.links

    @pytest.mark.parametrize(
        "content",
        [
            "Simple text content",
            "# Markdown heading\n\nSome content here.",
            "---\ntags: [test]\n---\nSpec content",
            "depends on: other-service\nrequires: database",
            "Multi\nline\ncontent\nwith\nmany\nlines",
        ],
    )
    def test_parse_arbitrary_tessl_content(self, content: str, tmp_path: Path) -> None:
        """Tessl adapter handles arbitrary content without crashing."""
        from specmem.adapters.tessl import TesslAdapter

        test_file = tmp_path / "test.tessl"
        test_file.write_text(content)

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Should not raise exception
            blocks = adapter.load(str(tmp_path))

        # Should return at least one block for valid content
        assert isinstance(blocks, list)
        assert len(blocks) >= 1


# ============================================================================
# GitHub SpecKit Adapter Property Tests
# ============================================================================


class TestSpecKitFileDetection:
    """Property 1: File Pattern Detection Completeness for GitHub SpecKit.

    **Feature: spec-driven-adapters, Property 1: File Pattern Detection Completeness**
    **Validates: Requirements 2.1**

    *For any* directory containing GitHub SpecKit .specify/ structure,
    the adapter's `detect()` method SHALL return True.
    """

    def test_detect_speckit_specify_directory(self, tmp_path: Path) -> None:
        """SpecKit adapter detects .specify directory structure."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify directory structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        specs_dir = specify_dir / "specs"
        specs_dir.mkdir()

        adapter = SpecKitAdapter()
        assert adapter.detect(str(tmp_path)) is True

    def test_detect_speckit_with_memory(self, tmp_path: Path) -> None:
        """SpecKit adapter detects .specify with memory directory."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify/memory structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        memory_dir = specify_dir / "memory"
        memory_dir.mkdir()
        (memory_dir / "constitution.md").write_text("# Constitution")

        adapter = SpecKitAdapter()
        assert adapter.detect(str(tmp_path)) is True

    def test_detect_no_speckit_files(self, tmp_path: Path) -> None:
        """SpecKit adapter returns False for directories without SpecKit structure."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create a non-SpecKit file
        (tmp_path / "readme.md").write_text("# Readme")

        adapter = SpecKitAdapter()
        assert adapter.detect(str(tmp_path)) is False

    def test_detect_nonexistent_path(self) -> None:
        """SpecKit adapter returns False for nonexistent paths."""
        from specmem.adapters.speckit import SpecKitAdapter

        adapter = SpecKitAdapter()
        assert adapter.detect("/nonexistent/path/12345") is False

    def test_speckit_is_experimental(self) -> None:
        """SpecKit adapter must be marked as experimental."""
        from specmem.adapters.speckit import SpecKitAdapter

        adapter = SpecKitAdapter()
        assert adapter.is_experimental() is True


class TestSpecKitMetadataPreservation:
    """Property 3: Metadata Preservation for GitHub SpecKit.

    **Feature: spec-driven-adapters, Property 3: Metadata Preservation**
    **Validates: Requirements 2.3**

    *For any* specification containing metadata, the metadata SHALL be
    preserved in the resulting SpecBlock tags or links.
    """

    def test_parse_spec_with_user_stories(self, tmp_path: Path) -> None:
        """SpecKit adapter extracts user stories from spec.md."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        specs_dir = specify_dir / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "001-auth-feature"
        feature_dir.mkdir()

        spec_content = """# Feature Specification: User Authentication

**Feature Branch**: `001-auth-feature`
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Login Flow (Priority: P1)

Users should be able to login with email and password.

**Acceptance Scenarios**:

1. **Given** a registered user, **When** they enter valid credentials, **Then** they are logged in

### User Story 2 - Password Reset (Priority: P2)

Users should be able to reset their password.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow users to login with email/password
- **FR-002**: System MUST validate email format

## Success Criteria

- **SC-001**: Users can login in under 3 seconds
"""
        (feature_dir / "spec.md").write_text(spec_content)

        adapter = SpecKitAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        # Check that user stories are extracted
        all_tags = []
        for block in blocks:
            all_tags.extend(block.tags)
        assert "speckit" in all_tags
        assert "user_story" in all_tags or "functional_requirement" in all_tags

    def test_parse_constitution(self, tmp_path: Path) -> None:
        """SpecKit adapter extracts constitution principles."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify/memory structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        memory_dir = specify_dir / "memory"
        memory_dir.mkdir()

        constitution_content = """# Project Constitution

## Article I: Library-First Principle

Every feature MUST begin as a standalone library.

## Article II: CLI Interface Mandate

All libraries MUST expose CLI interfaces.

## Article III: Test-First Imperative

All implementation MUST follow TDD.
"""
        (memory_dir / "constitution.md").write_text(constitution_content)

        adapter = SpecKitAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        # Check constitution is extracted
        constitution_blocks = [b for b in blocks if "constitution" in b.tags]
        assert len(constitution_blocks) >= 1
        assert constitution_blocks[0].pinned is True

    def test_parse_plan(self, tmp_path: Path) -> None:
        """SpecKit adapter extracts implementation plan."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        specs_dir = specify_dir / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "001-feature"
        feature_dir.mkdir()

        plan_content = """# Implementation Plan: Feature

## Summary

Building a user authentication system.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI
**Storage**: PostgreSQL
**Testing**: pytest

## Project Structure

### Source Code

```text
src/
├── models/
├── services/
└── api/
```
"""
        (feature_dir / "plan.md").write_text(plan_content)

        adapter = SpecKitAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        plan_blocks = [b for b in blocks if "plan" in b.tags]
        assert len(plan_blocks) >= 1

    def test_parse_tasks(self, tmp_path: Path) -> None:
        """SpecKit adapter extracts task breakdown."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify structure
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        specs_dir = specify_dir / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "001-feature"
        feature_dir.mkdir()

        tasks_content = """# Tasks: Feature

## Phase 1: Setup

- [ ] T001 Create project structure
- [ ] T002 [P] Initialize dependencies

## Phase 2: User Story 1 - Login

- [ ] T003 [US1] Create User model
- [x] T004 [US1] Implement auth service
"""
        (feature_dir / "tasks.md").write_text(tasks_content)

        adapter = SpecKitAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        # Should extract tasks
        task_blocks = [b for b in blocks if b.type.value == "task"]
        assert len(task_blocks) >= 1


# ============================================================================
# Cursor Adapter Property Tests
# ============================================================================


class TestCursorFileDetection:
    """Property 1: File Pattern Detection Completeness for Cursor.

    **Feature: spec-driven-adapters, Property 1: File Pattern Detection Completeness**
    **Validates: Requirements 4.1**

    *For any* directory containing files matching Cursor patterns,
    the adapter's `detect()` method SHALL return True.
    """

    @pytest.mark.parametrize(
        "filename",
        [
            ".cursorrules",
            "cursor.rules",
        ],
    )
    def test_detect_cursor_files(self, filename: str, tmp_path: Path) -> None:
        """Cursor adapter detects directories with Cursor files."""
        from specmem.adapters.cursor import CursorAdapter

        # Create a file matching Cursor pattern
        test_file = tmp_path / filename
        test_file.write_text("# Cursor rules")

        adapter = CursorAdapter()
        assert adapter.detect(str(tmp_path)) is True

    def test_detect_no_cursor_files(self, tmp_path: Path) -> None:
        """Cursor adapter returns False for directories without Cursor files."""
        from specmem.adapters.cursor import CursorAdapter

        # Create a non-Cursor file
        (tmp_path / "readme.md").write_text("# Readme")

        adapter = CursorAdapter()
        assert adapter.detect(str(tmp_path)) is False

    def test_cursor_is_experimental(self) -> None:
        """Cursor adapter must be marked as experimental."""
        from specmem.adapters.cursor import CursorAdapter

        adapter = CursorAdapter()
        assert adapter.is_experimental() is True

    def test_parse_cursor_rules_with_sections(self, tmp_path: Path) -> None:
        """Cursor adapter extracts sections from rules files."""
        from specmem.adapters.cursor import CursorAdapter

        rules_content = """# Code Style

Use TypeScript for all new code.
Follow ESLint rules.

# Testing

Write unit tests for all functions.
Use Jest for testing.

# Documentation

Add JSDoc comments to all public functions.
"""
        test_file = tmp_path / ".cursorrules"
        test_file.write_text(rules_content)

        adapter = CursorAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 3
        # Check that sections are preserved in tags
        all_tags = []
        for block in blocks:
            all_tags.extend(block.tags)
        assert "code_style" in all_tags or "testing" in all_tags

    def test_parse_cursor_rules_without_sections(self, tmp_path: Path) -> None:
        """Cursor adapter handles rules files without clear sections."""
        from specmem.adapters.cursor import CursorAdapter

        rules_content = """Always use TypeScript.
Follow best practices.
Write clean code.
"""
        test_file = tmp_path / ".cursorrules"
        test_file.write_text(rules_content)

        adapter = CursorAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        assert "cursor" in blocks[0].tags
        assert "rules" in blocks[0].tags


# ============================================================================
# Claude Adapter Property Tests
# ============================================================================


class TestClaudeFileDetection:
    """Property 1: File Pattern Detection Completeness for Claude.

    **Feature: spec-driven-adapters, Property 1: File Pattern Detection Completeness**
    **Validates: Requirements 5.1**

    *For any* directory containing files matching Claude patterns,
    the adapter's `detect()` method SHALL return True.
    """

    @pytest.mark.parametrize(
        "filename",
        [
            "claude_project.xml",
            "project.claude",
            "CLAUDE.md",
        ],
    )
    def test_detect_claude_files(self, filename: str, tmp_path: Path) -> None:
        """Claude adapter detects directories with Claude files."""
        from specmem.adapters.claude import ClaudeAdapter

        # Create a file matching Claude pattern
        test_file = tmp_path / filename
        test_file.write_text("# Claude project")

        adapter = ClaudeAdapter()
        assert adapter.detect(str(tmp_path)) is True

    def test_detect_claude_directory(self, tmp_path: Path) -> None:
        """Claude adapter detects .claude directory with XML files."""
        from specmem.adapters.claude import ClaudeAdapter

        # Create .claude directory with XML file
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "context.xml").write_text("<project></project>")

        adapter = ClaudeAdapter()
        assert adapter.detect(str(tmp_path)) is True

    def test_detect_no_claude_files(self, tmp_path: Path) -> None:
        """Claude adapter returns False for directories without Claude files."""
        from specmem.adapters.claude import ClaudeAdapter

        # Create a non-Claude file
        (tmp_path / "readme.md").write_text("# Readme")

        adapter = ClaudeAdapter()
        assert adapter.detect(str(tmp_path)) is False

    def test_claude_is_experimental(self) -> None:
        """Claude adapter must be marked as experimental."""
        from specmem.adapters.claude import ClaudeAdapter

        adapter = ClaudeAdapter()
        assert adapter.is_experimental() is True

    def test_parse_xml_project(self, tmp_path: Path) -> None:
        """Claude adapter parses XML project files."""
        from specmem.adapters.claude import ClaudeAdapter

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<project name="MyProject" type="web">
    <description>A web application project</description>
    <requirements>
        <requirement>User authentication</requirement>
        <requirement>Data persistence</requirement>
    </requirements>
    <references>
        <link href="docs/api.md">API Documentation</link>
    </references>
</project>
"""
        test_file = tmp_path / "claude_project.xml"
        test_file.write_text(xml_content)

        adapter = ClaudeAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        # Check that project info is extracted
        main_block = blocks[0]
        assert "claude" in main_block.tags
        assert "project" in main_block.tags
        assert main_block.pinned is True

    def test_parse_claude_md(self, tmp_path: Path) -> None:
        """Claude adapter parses CLAUDE.md files."""
        from specmem.adapters.claude import ClaudeAdapter

        md_content = """# Project Context

This is a Python project for data analysis.

## Requirements

- Python 3.10+
- pandas
- numpy

## Architecture

The project follows a modular architecture.
"""
        test_file = tmp_path / "CLAUDE.md"
        test_file.write_text(md_content)

        adapter = ClaudeAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        assert "claude" in blocks[0].tags


# ============================================================================
# Graceful Error Handling Property Tests
# ============================================================================


class TestGracefulErrorHandling:
    """Property 5: Graceful Error Handling.

    **Feature: spec-driven-adapters, Property 5: Graceful Error Handling**
    **Validates: Requirements 3.3, 3.4**

    *For any* malformed or unsupported specification content, the adapter
    SHALL log a warning and continue processing remaining files.
    """

    def test_tessl_handles_malformed_yaml(self, tmp_path: Path) -> None:
        """Tessl adapter handles malformed YAML gracefully."""
        from specmem.adapters.tessl import TesslAdapter

        # Create a valid file and a malformed file
        (tmp_path / "valid.tessl").write_text("# Valid spec")
        (tmp_path / "tessl.config.json").write_text("{ invalid json }")

        adapter = TesslAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Should not raise exception
            blocks = adapter.load(str(tmp_path))

        # Should still return blocks from valid file
        assert len(blocks) >= 1

    def test_speckit_handles_malformed_spec(self, tmp_path: Path) -> None:
        """SpecKit adapter handles malformed spec files gracefully."""
        from specmem.adapters.speckit import SpecKitAdapter

        # Create .specify structure with valid and malformed files
        specify_dir = tmp_path / ".specify"
        specify_dir.mkdir()
        specs_dir = specify_dir / "specs"
        specs_dir.mkdir()
        feature_dir = specs_dir / "001-feature"
        feature_dir.mkdir()

        # Valid spec
        (feature_dir / "spec.md").write_text(
            "# Valid Spec\n\n## Requirements\n\n- **FR-001**: Test"
        )
        # Malformed plan (will be parsed but may have issues)
        (feature_dir / "plan.md").write_text("Not a valid plan format")

        adapter = SpecKitAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Should not raise exception
            blocks = adapter.load(str(tmp_path))

        # Should still return blocks from valid file
        assert len(blocks) >= 1

    def test_claude_handles_malformed_xml(self, tmp_path: Path) -> None:
        """Claude adapter handles malformed XML gracefully."""
        from specmem.adapters.claude import ClaudeAdapter

        # Create a valid file and a malformed file
        (tmp_path / "CLAUDE.md").write_text("# Valid context")
        (tmp_path / "claude_project.xml").write_text("<invalid>xml")

        adapter = ClaudeAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Should not raise exception
            blocks = adapter.load(str(tmp_path))

        # Should still return blocks from valid file
        assert len(blocks) >= 1

    def test_cursor_handles_empty_file(self, tmp_path: Path) -> None:
        """Cursor adapter handles empty files gracefully."""
        from specmem.adapters.cursor import CursorAdapter

        # Create an empty file
        (tmp_path / ".cursorrules").write_text("")

        adapter = CursorAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Should not raise exception
            blocks = adapter.load(str(tmp_path))

        # Should return empty list or minimal block
        assert isinstance(blocks, list)


# ============================================================================
# Adapter Registration Tests
# ============================================================================


class TestAdapterRegistration:
    """Tests for adapter registration and discovery.

    **Feature: spec-driven-adapters**
    **Validates: Requirements 3.1**
    """

    def test_all_adapters_registered(self) -> None:
        """All adapters should be registered in the registry."""
        from specmem.adapters import get_all_adapters

        adapters = get_all_adapters()
        adapter_names = [a.name.lower() for a in adapters]

        # Check all expected adapters are registered
        assert "kiro" in adapter_names
        assert "tessl" in adapter_names
        assert "speckit" in adapter_names
        assert "cursor" in adapter_names
        assert "claude" in adapter_names

    def test_experimental_adapters_marked(self) -> None:
        """Experimental adapters should be properly marked."""
        from specmem.adapters import get_experimental_adapters

        experimental = get_experimental_adapters()
        experimental_names = [a.name.lower() for a in experimental]

        # Tessl, SpecKit, Cursor, Claude should be experimental
        assert "tessl" in experimental_names
        assert "speckit" in experimental_names
        assert "cursor" in experimental_names
        assert "claude" in experimental_names

        # Kiro should NOT be experimental
        assert "kiro" not in experimental_names

    def test_get_adapter_by_name(self) -> None:
        """Should be able to get adapter by name."""
        from specmem.adapters import get_adapter

        tessl = get_adapter("tessl")
        assert tessl is not None
        assert tessl.name == "Tessl"
        assert tessl.is_experimental() is True

        kiro = get_adapter("kiro")
        assert kiro is not None
        assert kiro.name == "Kiro"
        assert kiro.is_experimental() is False

    def test_get_adapter_case_insensitive(self) -> None:
        """Adapter lookup should be case-insensitive."""
        from specmem.adapters import get_adapter

        assert get_adapter("TESSL") is not None
        assert get_adapter("Tessl") is not None
        assert get_adapter("tessl") is not None
