"""Unit tests for AgentsAdapter.

Tests detection, heading split, aliases, and error handling for AGENTS.md.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from specmem.adapters.agents import AgentsAdapter
from specmem.core.specir import SpecStatus, SpecType


@pytest.fixture
def adapter() -> AgentsAdapter:
    """Create an AgentsAdapter instance."""
    return AgentsAdapter()


class TestAgentsAdapterDetection:
    """Tests for AgentsAdapter.detect()"""

    def test_detect_root_file(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should detect AGENTS.md at the repository root."""
        (tmp_path / "AGENTS.md").write_text("# Agent rules\n\nKeep changes scoped.")

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_nested_file(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should detect nested AGENTS.md files."""
        nested = tmp_path / "packages" / "api"
        nested.mkdir(parents=True)
        (nested / "AGENTS.md").write_text("# Package rules\n\nUse typed APIs.")

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_agent_md_alias(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should detect AGENT.md alias used by the guidelines scanner."""
        (tmp_path / "AGENT.md").write_text("# Alias\n\nFollow these rules.")

        assert adapter.detect(str(tmp_path)) is True

    @pytest.mark.parametrize("filename", ["Agents.md", "Agent.md"])
    def test_detect_case_aliases(
        self, adapter: AgentsAdapter, tmp_path: Path, filename: str
    ) -> None:
        """Should detect Agents.md and Agent.md aliases."""
        (tmp_path / filename).write_text("# Alias\n\nFollow these rules.")

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_empty_repo(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should not false-positive on an empty repository."""
        assert adapter.detect(str(tmp_path)) is False

    def test_detect_unrelated_markdown(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should not detect README.md or other markdown files."""
        (tmp_path / "README.md").write_text("# Readme\n\nHello.")

        assert adapter.detect(str(tmp_path)) is False

    def test_detect_missing_repo(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should return False when the repository path does not exist."""
        assert adapter.detect(str(tmp_path / "does-not-exist")) is False

    def test_detect_ignores_junk_dirs(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should ignore AGENTS.md inside node_modules, .git, and .venv."""
        for junk in ("node_modules", ".git", ".venv"):
            junk_dir = tmp_path / junk / "pkg"
            junk_dir.mkdir(parents=True)
            (junk_dir / "AGENTS.md").write_text("# Junk\n\nShould be ignored.")

        assert adapter.detect(str(tmp_path)) is False


class TestAgentsAdapterLoad:
    """Tests for AgentsAdapter.load()"""

    def test_load_sections_from_headings(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should split AGENTS.md on markdown headings into SpecBlocks."""
        (tmp_path / "AGENTS.md").write_text(
            """# Project Rules

Keep pull requests focused.

## Testing

Run unit tests before opening a PR.

### Style

Prefer typed Python.
"""
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 3
        assert all(b.type == SpecType.KNOWLEDGE for b in blocks)
        assert all(b.status == SpecStatus.ACTIVE for b in blocks)
        assert all(b.pinned is False for b in blocks)
        assert all("agents" in b.tags and "agents.md" in b.tags for b in blocks)

        texts = [b.text for b in blocks]
        assert any("Keep pull requests focused." in text for text in texts)
        assert any("Run unit tests before opening a PR." in text for text in texts)
        assert any("Prefer typed Python." in text for text in texts)

        all_tags = [tag for b in blocks for tag in b.tags]
        assert "project_rules" in all_tags
        assert "testing" in all_tags
        assert "style" in all_tags

    def test_load_whole_file_without_headings(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should create one pinned SpecBlock when the file has no headings."""
        content = "Always use typed Python.\nKeep diffs small.\n"
        (tmp_path / "AGENTS.md").write_text(content)

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        block = blocks[0]
        assert block.type == SpecType.KNOWLEDGE
        assert block.status == SpecStatus.ACTIVE
        assert block.pinned is True
        assert block.text == content
        assert block.tags == ["agents", "agents.md"]
        assert "AGENTS.md" in block.source

    def test_load_nested_file(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should load nested AGENTS.md files."""
        nested = tmp_path / "apps" / "web"
        nested.mkdir(parents=True)
        (nested / "AGENTS.md").write_text("# Frontend\n\nUse the design system.")

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Use the design system." in blocks[0].text
        assert str(nested / "AGENTS.md") == blocks[0].source

    def test_load_agent_md_alias(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should parse AGENT.md the same way as AGENTS.md."""
        (tmp_path / "AGENT.md").write_text("# Alias\n\nTreat this as agent guidance.")

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert blocks[0].type == SpecType.KNOWLEDGE
        assert "Treat this as agent guidance." in blocks[0].text
        assert "agents" in blocks[0].tags

    def test_load_deduplicates_paths(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should not emit duplicate blocks for the same file."""
        (tmp_path / "AGENTS.md").write_text("# Rules\n\nOne file only.")

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1

    def test_load_skips_missing_repo(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should return an empty list when the repository is missing."""
        blocks = adapter.load(str(tmp_path / "missing"))
        assert blocks == []

    def test_load_skips_empty_file(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should skip empty files without creating SpecBlocks."""
        (tmp_path / "AGENTS.md").write_text("")

        blocks = adapter.load(str(tmp_path))

        assert blocks == []

    def test_load_skips_whitespace_only_file(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should skip whitespace-only files."""
        (tmp_path / "AGENTS.md").write_text("   \n\n  \n")

        blocks = adapter.load(str(tmp_path))

        assert blocks == []

    def test_load_skips_heading_only_sections(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should skip headings that have no body content."""
        (tmp_path / "AGENTS.md").write_text("# Title\n\n# Another\n")

        blocks = adapter.load(str(tmp_path))

        assert blocks == []

    def test_load_skips_unreadable_file(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should warn and continue when a file cannot be read."""
        (tmp_path / "AGENTS.md").write_text("# Rules\n\nImportant context.")
        original = Path.read_text

        def boom(self: Path, *args: object, **kwargs: object) -> str:
            if self.name in AgentsAdapter.FILENAMES:
                raise OSError("permission denied")
            return original(self, *args, **kwargs)

        with patch.object(Path, "read_text", boom):
            blocks = adapter.load(str(tmp_path))

        assert blocks == []

    def test_load_skips_junk_dirs(self, adapter: AgentsAdapter, tmp_path: Path) -> None:
        """Should not load AGENTS.md from ignored directories."""
        junk = tmp_path / "node_modules" / "lib"
        junk.mkdir(parents=True)
        (junk / "AGENTS.md").write_text("# Vendor\n\nIgnore me.")
        (tmp_path / "AGENTS.md").write_text("# Root\n\nKeep this.")

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Keep this." in blocks[0].text
        assert "Ignore me." not in blocks[0].text

    def test_load_malformed_file_does_not_crash(
        self, adapter: AgentsAdapter, tmp_path: Path
    ) -> None:
        """Should handle unexpected parse errors without crashing."""
        (tmp_path / "AGENTS.md").write_text("# Valid\n\nKeep going.")

        with patch.object(adapter, "_extract_sections", side_effect=ValueError("bad markdown")):
            blocks = adapter.load(str(tmp_path))

        assert blocks == []


class TestAgentsAdapterProperties:
    """Tests for adapter properties."""

    def test_adapter_name(self, adapter: AgentsAdapter) -> None:
        """Adapter name should be AGENTS.md so scan output is obvious."""
        assert adapter.name == "AGENTS.md"

    def test_is_not_experimental(self, adapter: AgentsAdapter) -> None:
        """AGENTS.md is a stable standard adapter."""
        assert adapter.is_experimental() is False

    def test_adapter_repr(self, adapter: AgentsAdapter) -> None:
        """Adapter repr should be informative."""
        repr_str = repr(adapter)
        assert "AgentsAdapter" in repr_str
        assert "AGENTS.md" in repr_str
