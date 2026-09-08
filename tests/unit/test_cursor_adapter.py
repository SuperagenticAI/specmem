"""Unit tests for CursorAdapter.

Tests detection and load for legacy .cursorrules / cursor.rules and modern
.cursor/rules/*.mdc files, including YAML frontmatter handling.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from specmem.adapters.cursor import CursorAdapter
from specmem.core.specir import SpecStatus, SpecType


@pytest.fixture
def adapter() -> CursorAdapter:
    """Create a CursorAdapter instance."""
    return CursorAdapter()


def _write_mdc(path: Path, frontmatter: str, body: str) -> Path:
    """Write an .mdc file with YAML frontmatter and markdown body."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}")
    return path


class TestCursorAdapterDetection:
    """Tests for CursorAdapter.detect()"""

    def test_detect_mdc_only(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should detect a repo that only has .cursor/rules/*.mdc."""
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "style.mdc",
            "description: Style rules\nalwaysApply: true\n",
            "# Style\n\nUse typed Python.\n",
        )

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_legacy_cursorrules(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should detect legacy .cursorrules files."""
        (tmp_path / ".cursorrules").write_text("# Rules\n\nUse TypeScript.")

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_legacy_cursor_rules(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should detect legacy cursor.rules files."""
        (tmp_path / "cursor.rules").write_text("# Rules\n\nPrefer const.")

        assert adapter.detect(str(tmp_path)) is True

    def test_detect_empty_repo(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should not false-positive on an empty repository."""
        assert adapter.detect(str(tmp_path)) is False

    def test_detect_unrelated_markdown(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should not detect README.md or plain .md under .cursor/rules."""
        rules = tmp_path / ".cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "notes.md").write_text("# Not a rule\n")
        (tmp_path / "README.md").write_text("# Readme\n")

        assert adapter.detect(str(tmp_path)) is False

    def test_detect_missing_repo(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should return False when the repository path does not exist."""
        assert adapter.detect(str(tmp_path / "does-not-exist")) is False

    def test_detect_ignores_junk_dirs(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should ignore Cursor files inside node_modules, .git, and .venv."""
        for junk in ("node_modules", ".git", ".venv"):
            junk_dir = tmp_path / junk / "pkg" / ".cursor" / "rules"
            junk_dir.mkdir(parents=True)
            (junk_dir / "vendor.mdc").write_text(
                "---\nalwaysApply: true\n---\n\n# Vendor\n\nIgnore me.\n"
            )
            (tmp_path / junk / ".cursorrules").write_text("# Junk\n")

        assert adapter.detect(str(tmp_path)) is False


class TestCursorAdapterLoadMdc:
    """Tests for loading .cursor/rules/*.mdc files."""

    def test_load_mdc_with_frontmatter(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should strip frontmatter, keep body, and preserve useful metadata."""
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "frontend.mdc",
            (
                'description: "Frontend component standards"\n'
                "globs: src/components/**/*.tsx,src/**/*.ts\n"
                "alwaysApply: false\n"
            ),
            "# Components\n\nUse the design system.\n\n## Validation\n\nValidate API inputs.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 2
        assert all(b.type == SpecType.KNOWLEDGE for b in blocks)
        assert all(b.status == SpecStatus.ACTIVE for b in blocks)
        assert all("cursor" in b.tags and "rules" in b.tags and "mdc" in b.tags for b in blocks)
        assert all("described" in b.tags for b in blocks)
        assert all(any(t.startswith("globs:") for t in b.tags) for b in blocks)
        assert all("always-apply" not in b.tags for b in blocks)

        texts = [b.text for b in blocks]
        assert any("Use the design system." in text for text in texts)
        assert any("Validate API inputs." in text for text in texts)
        assert all("Frontend component standards" in text for text in texts)
        assert all("Globs: src/components/**/*.tsx,src/**/*.ts" in text for text in texts)
        # Frontmatter keys must not leak as raw YAML into the body
        assert all("alwaysApply:" not in text for text in texts)
        assert all("---" not in text.split("\n")[0] for text in texts)

    def test_load_mdc_always_apply(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should tag alwaysApply: true as always-apply."""
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "always.mdc",
            "alwaysApply: true\ndescription: Universal rules\n",
            "Always run tests before committing.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        assert all("always-apply" in b.tags for b in blocks)
        assert all("mdc" in b.tags for b in blocks)
        assert any("Universal rules" in b.text for b in blocks)
        assert any("Always run tests before committing." in b.text for b in blocks)

    def test_load_mdc_globs_list(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should normalize YAML list globs into a comma-separated string."""
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "api.mdc",
            "globs:\n  - \"**/*.py\"\n  - \"**/api/**\"\nalwaysApply: false\n",
            "# API\n\nUse typed request models.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        glob_tags = [t for t in blocks[0].tags if t.startswith("globs:")]
        assert glob_tags
        assert "**/*.py" in glob_tags[0]
        assert "**/api/**" in glob_tags[0]
        assert "Globs: **/*.py,**/api/**" in blocks[0].text

    def test_load_mdc_without_frontmatter(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should still load .mdc files that lack YAML frontmatter."""
        rules = tmp_path / ".cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "plain.mdc").write_text("# Plain\n\nKeep diffs small.\n")

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Keep diffs small." in blocks[0].text
        assert "mdc" in blocks[0].tags
        assert "always-apply" not in blocks[0].tags

    def test_load_mdc_bad_frontmatter_does_not_crash(
        self, adapter: CursorAdapter, tmp_path: Path
    ) -> None:
        """Should strip a malformed frontmatter fence and still load the body."""
        rules = tmp_path / ".cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "broken.mdc").write_text(
            "---\nalwaysApply: [unterminated\n---\n\n# Still valid\n\nBody survives.\n"
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Body survives." in blocks[0].text
        assert "mdc" in blocks[0].tags

    def test_load_mdc_frontmatter_only_skips(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should skip .mdc files that have frontmatter but no body content."""
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "empty-body.mdc",
            "alwaysApply: true\ndescription: Empty\n",
            "\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert blocks == []


class TestCursorAdapterLoadLegacy:
    """Tests for legacy .cursorrules / cursor.rules loading."""

    def test_load_legacy_cursorrules_with_headings(
        self, adapter: CursorAdapter, tmp_path: Path
    ) -> None:
        """Legacy .cursorrules should still split on markdown headings."""
        (tmp_path / ".cursorrules").write_text(
            """# Code Style

Use TypeScript.

## Testing

Write unit tests.
"""
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 2
        assert all(b.type == SpecType.KNOWLEDGE for b in blocks)
        assert all("cursor" in b.tags and "rules" in b.tags for b in blocks)
        assert all("mdc" not in b.tags for b in blocks)
        texts = [b.text for b in blocks]
        assert any("Use TypeScript." in text for text in texts)
        assert any("Write unit tests." in text for text in texts)

    def test_load_legacy_without_headings(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Legacy files without headings still produce SpecBlocks."""
        content = "Always use TypeScript.\nFollow best practices.\n"
        (tmp_path / ".cursorrules").write_text(content)

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) >= 1
        assert all("cursor" in b.tags for b in blocks)
        # First line may become a title tag; body retains remaining lines.
        assert any("best practices" in b.text.lower() for b in blocks)

    def test_load_legacy_and_mdc_together(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should load both legacy and .mdc rules from the same repo."""
        (tmp_path / ".cursorrules").write_text("# Legacy\n\nLegacy rule body.\n")
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "modern.mdc",
            "alwaysApply: true\n",
            "# Modern\n\nModern rule body.\n",
        )

        blocks = adapter.load(str(tmp_path))

        texts = "\n".join(b.text for b in blocks)
        assert "Legacy rule body." in texts
        assert "Modern rule body." in texts
        assert any("mdc" in b.tags for b in blocks)
        assert any("mdc" not in b.tags for b in blocks)


class TestCursorAdapterLoadEdgeCases:
    """Error handling and junk-dir skipping."""

    def test_load_skips_missing_repo(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should return an empty list when the repository is missing."""
        assert adapter.load(str(tmp_path / "missing")) == []

    def test_load_skips_empty_file(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should skip empty legacy files."""
        (tmp_path / ".cursorrules").write_text("")

        assert adapter.load(str(tmp_path)) == []

    def test_load_skips_junk_dirs(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should not load Cursor files from ignored directories."""
        junk = tmp_path / "node_modules" / "lib" / ".cursor" / "rules"
        junk.mkdir(parents=True)
        (junk / "vendor.mdc").write_text("---\nalwaysApply: true\n---\n\n# Vendor\n\nIgnore.\n")
        _write_mdc(
            tmp_path / ".cursor" / "rules" / "keep.mdc",
            "alwaysApply: true\n",
            "# Keep\n\nKeep this.\n",
        )

        blocks = adapter.load(str(tmp_path))

        assert len(blocks) == 1
        assert "Keep this." in blocks[0].text
        assert "Ignore." not in blocks[0].text

    def test_load_skips_unreadable_file(self, adapter: CursorAdapter, tmp_path: Path) -> None:
        """Should warn and continue when a file cannot be read."""
        (tmp_path / ".cursorrules").write_text("# Rules\n\nImportant context.")
        original = Path.read_text

        def boom(self: Path, *args: object, **kwargs: object) -> str:
            if self.name in {".cursorrules", "cursor.rules"} or self.suffix == ".mdc":
                raise OSError("permission denied")
            return original(self, *args, **kwargs)

        with patch.object(Path, "read_text", boom):
            blocks = adapter.load(str(tmp_path))

        assert blocks == []

    def test_load_malformed_file_does_not_crash(
        self, adapter: CursorAdapter, tmp_path: Path
    ) -> None:
        """Should handle unexpected parse errors without crashing."""
        (tmp_path / ".cursorrules").write_text("# Valid\n\nKeep going.")

        with patch.object(adapter, "_extract_sections", side_effect=ValueError("bad markdown")):
            blocks = adapter.load(str(tmp_path))

        assert blocks == []


class TestCursorAdapterProperties:
    """Tests for adapter properties."""

    def test_adapter_name(self, adapter: CursorAdapter) -> None:
        """Adapter name should be Cursor."""
        assert adapter.name == "Cursor"

    def test_is_experimental(self, adapter: CursorAdapter) -> None:
        """Cursor adapter remains experimental."""
        assert adapter.is_experimental() is True

    def test_file_patterns_include_mdc(self, adapter: CursorAdapter) -> None:
        """FILE_PATTERNS should include modern .mdc and legacy patterns."""
        assert "**/.cursor/rules/*.mdc" in adapter.FILE_PATTERNS
        assert "**/.cursorrules" in adapter.FILE_PATTERNS
        assert "**/cursor.rules" in adapter.FILE_PATTERNS

    def test_adapter_repr(self, adapter: CursorAdapter) -> None:
        """Adapter repr should be informative."""
        repr_str = repr(adapter)
        assert "CursorAdapter" in repr_str
        assert "Cursor" in repr_str
