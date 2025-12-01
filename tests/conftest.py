"""Pytest configuration and shared fixtures for SpecMem tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_kiro_project(temp_dir: Path) -> Path:
    """Create a sample Kiro project structure."""
    # Create .kiro/specs directory
    specs_dir = temp_dir / ".kiro" / "specs" / "test-feature"
    specs_dir.mkdir(parents=True)

    # Create requirements.md
    requirements = specs_dir / "requirements.md"
    requirements.write_text("""# Requirements Document

## Introduction

Test feature requirements.

## Requirements

### Requirement 1: User Authentication

**User Story:** As a user, I want to log in securely.

#### Acceptance Criteria

1. WHEN a user provides valid credentials THEN the System SHALL authenticate the user
2. WHEN a user provides invalid credentials THEN the System SHALL reject the login attempt
""")

    # Create design.md
    design = specs_dir / "design.md"
    design.write_text("""# Design Document

## Overview

Authentication system design.

## Architecture

The system uses JWT tokens for authentication.
""")

    # Create tasks.md
    tasks = specs_dir / "tasks.md"
    tasks.write_text("""# Implementation Plan

- [ ] 1. Implement login endpoint
- [ ] 2. Add JWT token generation
- [x] 3. Create user model
""")

    return temp_dir


@pytest.fixture
def sample_spec_block():
    """Create a sample SpecBlock for testing."""
    from specmem.core.specir import SpecBlock, SpecType

    return SpecBlock(
        id="test_block_1",
        type=SpecType.REQUIREMENT,
        text="WHEN a user logs in THEN the system SHALL authenticate them",
        source="test/requirements.md",
        tags=["auth", "login"],
    )


@pytest.fixture
def sample_spec_blocks():
    """Create multiple sample SpecBlocks for testing."""
    from specmem.core.specir import SpecBlock, SpecStatus, SpecType

    return [
        SpecBlock(
            id="req_1",
            type=SpecType.REQUIREMENT,
            text="User authentication requirement",
            source="requirements.md",
            tags=["auth"],
            pinned=True,
        ),
        SpecBlock(
            id="design_1",
            type=SpecType.DESIGN,
            text="JWT-based authentication design",
            source="design.md",
            tags=["auth", "jwt"],
        ),
        SpecBlock(
            id="task_1",
            type=SpecType.TASK,
            text="Implement login endpoint",
            source="tasks.md",
            status=SpecStatus.ACTIVE,
        ),
        SpecBlock(
            id="legacy_1",
            type=SpecType.REQUIREMENT,
            text="Old authentication method",
            source="requirements.md",
            status=SpecStatus.LEGACY,
        ),
    ]
