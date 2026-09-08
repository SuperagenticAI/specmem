"""Unit tests for OpenSpecAdapter.

Covers detection and load for openspec/specs, openspec/changes, nested
layouts, empty repos, config.yaml, and graceful skip of malformed files.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from specmem.adapters.openspec import OpenSpecAdapter
from specmem.core.specir import SpecStatus, SpecType


@pytest.fixture
def adapter() -> OpenSpecAdapter:
    """Create an OpenSpecAdapter instance."""
    return OpenSpecAdapter()


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestOpenSpecAdapterDetection:
    """Tests for OpenSpecAdapter.detect()"""

    def test_detect_specs_only(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should detect openspec/specs with a domain spec.md."""
        _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            "# Auth\n\n### Requirement: Login\nUsers can log in.\n",
        )

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_changes_only(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should detect openspec/changes with a change folder."""
        _write(
            tmp_path / "openspec" / "changes" / "add-dark-mode" / "proposal.md",
            "# Proposal\n\nAdd dark mode.\n",
        )

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_config_only(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should detect openspec/config.yaml alone."""
        _write(tmp_path / "openspec" / "config.yaml", "schema: spec-driven\n")

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_empty_specs_dir(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Empty openspec/specs/ still signals an OpenSpec project."""
        (tmp_path / "openspec" / "specs").mkdir(parents=True)

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_empty_repo(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should not false-positive on an empty repository."""
        assert adapter.detect(str(tmp_path)) is False

    def test_detect_openspec_dir_without_content(
        self, adapter: OpenSpecAdapter, tmp_path: Path
    ) -> None:
        """Bare openspec/ with neither specs, changes, nor config is False."""
        (tmp_path / "openspec").mkdir()

        assert adapter.detect(str(tmp_path)) is False

    def test_detect_unrelated_markdown(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should not detect README.md at the repo root."""
        (tmp_path / "README.md").write_text("# Readme\n")

        assert adapter.detect(str(tmp_path)) is False

    def test_detect_missing_repo(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should return False when the repository path does not exist."""
        assert adapter.detect(str(tmp_path / "does-not-exist")) is False


class TestOpenSpecAdapterLoadSpecs:
    """Tests for loading openspec/specs/**."""

    def test_load_specs_only(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should load domain specs as REQUIREMENT blocks."""
        _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            """# Auth

## Requirement: Login

Users MUST authenticate with email.

## Requirement: Logout

Users MUST be able to end a session.
""",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 2
        assert all(b.type == SpecType.REQUIREMENT for b in blocks)
        assert all(b.status == SpecStatus.ACTIVE for b in blocks)
        assert all("openspec" in b.tags for b in blocks)
        assert all("auth" in b.tags for b in blocks)
        assert all("specs" in b.tags for b in blocks)
        texts = [b.text for b in blocks]
        assert any("authenticate with email" in t for t in texts)
        assert any("end a session" in t for t in texts)

    def test_load_nested_domain_specs(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should load nested domain folders under specs/."""
        _write(
            tmp_path / "openspec" / "specs" / "payments" / "checkout" / "spec.md",
            "# Checkout\n\nCharge cards securely.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        assert all(b.type == SpecType.REQUIREMENT for b in blocks)
        assert any("payments" in b.tags for b in blocks)
        assert any("checkout" in b.tags for b in blocks)


class TestOpenSpecAdapterLoadChanges:
    """Tests for loading openspec/changes/**."""

    def test_load_changes_only(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should map proposal/design/tasks/delta specs to sensible types."""
        change = tmp_path / "openspec" / "changes" / "add-dark-mode"
        _write(change / "proposal.md", "# Proposal\n\nAdd a theme toggle.\n")
        _write(change / "design.md", "# Design\n\nUse CSS variables.\n")
        _write(
            change / "tasks.md",
            "# Tasks\n\n## Infra\n\n- [ ] Create ThemeContext\n",
        )
        _write(
            change / "specs" / "ui" / "spec.md",
            "# Delta for UI\n\n## ADDED Requirements\n\nTheme selection MUST work.\n",
        )

        blocks = adapter.load(str(tmp_path))

        by_type = {b.type for b in blocks}
        assert SpecType.KNOWLEDGE in by_type  # proposal
        assert SpecType.DESIGN in by_type
        assert SpecType.TASK in by_type
        assert SpecType.REQUIREMENT in by_type  # delta spec

        assert all("openspec" in b.tags for b in blocks)
        assert all("add_dark_mode" in b.tags or "changes" in b.tags for b in blocks)

        proposals = [b for b in blocks if "proposal" in b.tags]
        assert proposals
        assert any("theme toggle" in b.text for b in proposals)

    def test_load_archived_change_as_legacy(
        self, adapter: OpenSpecAdapter, tmp_path: Path
    ) -> None:
        """Archived changes should be LEGACY status and tagged archive."""
        _write(
            tmp_path
            / "openspec"
            / "changes"
            / "archive"
            / "2025-01-24-add-dark-mode"
            / "proposal.md",
            "# Archived\n\nCompleted dark mode.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        assert all(b.status == SpecStatus.LEGACY for b in blocks)
        assert all("archive" in b.tags for b in blocks)


class TestOpenSpecAdapterLoadMixed:
    """Combined layouts and edge cases."""

    def test_load_specs_and_changes(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should load both specs/ and changes/ in one pass."""
        _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            "# Auth\n\nLogin works.\n",
        )
        _write(
            tmp_path / "openspec" / "changes" / "add-2fa" / "proposal.md",
            "# Proposal\n\nAdd two-factor auth.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 2
        sources = " ".join(b.source for b in blocks)
        assert "specs" in sources
        assert "add-2fa" in sources

    def test_load_config_yaml_as_knowledge(
        self, adapter: OpenSpecAdapter, tmp_path: Path
    ) -> None:
        """Should index context and rules from config.yaml as knowledge."""
        _write(
            tmp_path / "openspec" / "config.yaml",
            """schema: spec-driven
context: |
  Tech stack: TypeScript, React
  Testing: Vitest
rules:
  proposal:
    - Include rollback plan
  design:
    - Include sequence diagrams
""",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 2
        assert all(b.type == SpecType.KNOWLEDGE for b in blocks)
        assert all("openspec" in b.tags and "config" in b.tags for b in blocks)

        texts = [b.text for b in blocks]
        assert any("TypeScript" in t for t in texts)
        assert any("rollback" in t.lower() for t in texts)

        context_blocks = [b for b in blocks if "context" in b.tags]
        assert context_blocks
        assert context_blocks[0].pinned is True

    def test_load_empty_repo(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should return [] for a repo with no openspec/."""
        assert adapter.load(str(tmp_path)) == []

    def test_load_empty_openspec_dirs(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Empty specs/ and changes/ should yield no blocks."""
        (tmp_path / "openspec" / "specs").mkdir(parents=True)
        (tmp_path / "openspec" / "changes").mkdir(parents=True)

        assert adapter.load(str(tmp_path)) == []

    def test_load_skips_empty_file(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should skip empty markdown files."""
        _write(tmp_path / "openspec" / "specs" / "auth" / "spec.md", "")

        assert adapter.load(str(tmp_path)) == []

    def test_load_skips_heading_only(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should skip headings with no body content."""
        _write(tmp_path / "openspec" / "specs" / "auth" / "spec.md", "# Title\n\n# Another\n")

        assert adapter.load(str(tmp_path)) == []

    def test_load_skips_junk_dirs(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should not load markdown from node_modules under openspec/."""
        _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            "# Auth\n\nKeep this.\n",
        )
        _write(
            tmp_path / "openspec" / "changes" / "node_modules" / "pkg" / "readme.md",
            "# Vendor\n\nIgnore me.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Keep this." in blocks[0].text
        assert all("Ignore me." not in b.text for b in blocks)

    def test_load_skips_schemas_dir(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should not walk openspec/schemas/ custom workflow files."""
        _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            "# Auth\n\nReal spec.\n",
        )
        _write(
            tmp_path / "openspec" / "schemas" / "custom" / "README.md",
            "# Schema docs\n\nNot a product spec.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Real spec." in blocks[0].text

    def test_load_malformed_file_does_not_crash(
        self, adapter: OpenSpecAdapter, tmp_path: Path
    ) -> None:
        """Should warn and continue when parse fails on one file."""
        _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            "# Auth\n\nValid content.\n",
        )
        _write(
            tmp_path / "openspec" / "specs" / "bad" / "spec.md",
            "# Bad\n\nWill raise.\n",
        )

        original = OpenSpecAdapter._parse_markdown_file

        def flaky(
            self: OpenSpecAdapter, file_path: Path, openspec_root: Path
        ) -> list:
            if file_path.parent.name == "bad":
                raise ValueError("malformed")
            return original(self, file_path, openspec_root)

        with patch.object(OpenSpecAdapter, "_parse_markdown_file", flaky):
            blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Valid content." in blocks[0].text

    def test_load_unreadable_file(self, adapter: OpenSpecAdapter, tmp_path: Path) -> None:
        """Should skip files that cannot be read."""
        target = _write(
            tmp_path / "openspec" / "specs" / "auth" / "spec.md",
            "# Auth\n\nSecret.\n",
        )
        original = Path.read_text

        def boom(self: Path, *args: object, **kwargs: object) -> str:
            if self == target:
                raise OSError("permission denied")
            return original(self, *args, **kwargs)

        with patch.object(Path, "read_text", boom):
            blocks = adapter.load(str(tmp_path))

        assert blocks == []

    def test_load_whole_file_without_headings(
        self, adapter: OpenSpecAdapter, tmp_path: Path
    ) -> None:
        """File with no headings becomes one pinned block."""
        content = "Plain requirement text without headings.\n"
        _write(tmp_path / "openspec" / "specs" / "auth" / "spec.md", content)

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert blocks[0].pinned is True
        assert blocks[0].text == content
        assert blocks[0].type == SpecType.REQUIREMENT

    def test_load_malformed_config_falls_back(
        self, adapter: OpenSpecAdapter, tmp_path: Path
    ) -> None:
        """Broken YAML in config.yaml should fall back to raw knowledge."""
        _write(
            tmp_path / "openspec" / "config.yaml",
            "context: |\n  unbroken start\n rules: [unterminated\n",
        )

        blocks = adapter.load(str(tmp_path))

        # Either raw fallback or empty; must not crash
        assert isinstance(blocks, list)
        if blocks:
            assert all(b.type == SpecType.KNOWLEDGE for b in blocks)
            assert all("config" in b.tags for b in blocks)


class TestOpenSpecAdapterProperties:
    """Tests for adapter properties."""

    def test_adapter_name(self, adapter: OpenSpecAdapter) -> None:
        assert adapter.name == "OpenSpec"

    def test_is_not_experimental(self, adapter: OpenSpecAdapter) -> None:
        """Documented OpenSpec layout is a stable adapter."""
        assert adapter.is_experimental() is False

    def test_adapter_repr(self, adapter: OpenSpecAdapter) -> None:
        repr_str = repr(adapter)
        assert "OpenSpecAdapter" in repr_str
        assert "OpenSpec" in repr_str

    def test_registry_discovers_openspec(self) -> None:
        """Auto-discovery should register OpenSpec."""
        from specmem.adapters import get_adapter

        found = get_adapter("openspec")
        assert found is not None
        assert found.name == "OpenSpec"
        assert found.is_experimental() is False
