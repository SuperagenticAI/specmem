from __future__ import annotations

from typing import TYPE_CHECKING

from specmem.core.specir import SpecType
from specmem.guidelines.aggregator import GuidelinesAggregator
from specmem.guidelines.models import SourceType
from specmem.guidelines.optimizer import OptimizedSkillStore
from specmem.guidelines.parser import GuidelinesParser
from specmem.guidelines.scanner import GuidelinesScanner


if TYPE_CHECKING:
    from pathlib import Path


def test_scanner_finds_modern_agent_guidance_files(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Agent Rules\n\nKeep changes scoped.")
    (tmp_path / "GEMINI.md").write_text("# Gemini\n\nUse project tests.")

    cursor_dir = tmp_path / ".cursor" / "rules"
    cursor_dir.mkdir(parents=True)
    (cursor_dir / "python.mdc").write_text(
        "---\ndescription: Python rules\n---\n# Python\n\nUse ruff."
    )

    codex_skill_dir = tmp_path / ".codex" / "skills" / "release-notes"
    codex_skill_dir.mkdir(parents=True)
    (codex_skill_dir / "SKILL.md").write_text(
        "---\nname: release-notes\ndescription: Draft release notes\n---\n# Steps\n\nSummarize commits."
    )

    copilot_dir = tmp_path / ".github"
    copilot_dir.mkdir()
    (copilot_dir / "copilot-instructions.md").write_text("# Copilot\n\nCheck specs first.")

    scanned = GuidelinesScanner(tmp_path).scan()

    assert "agents" in scanned
    assert "gemini" in scanned
    assert "cursor" in scanned
    assert "codex_skill" in scanned
    assert "copilot" in scanned


def test_parser_reads_skill_frontmatter_as_procedural_memory(tmp_path: Path) -> None:
    skill_file = tmp_path / ".codex" / "skills" / "qdrant-memory" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\n"
        "name: qdrant-memory\n"
        "description: Build a Qdrant-backed coding-agent memory layer\n"
        "---\n"
        "# Workflow\n\nUse hybrid retrieval and metadata filters."
    )

    guidelines = GuidelinesParser().parse_file(skill_file, "codex_skill")

    assert len(guidelines) == 1
    assert guidelines[0].source_type == SourceType.CODEX_SKILL
    assert guidelines[0].title == "qdrant-memory"
    assert "hybrid retrieval" in guidelines[0].content


def test_agent_guidance_converts_to_memory_blocks(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Architecture\n\nMemory updates must preserve intent.")
    skill_dir = tmp_path / ".claude" / "skills" / "review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: review\ndescription: Review code changes\n---\n# Checklist\n\nFind regressions."
    )

    blocks = GuidelinesAggregator(tmp_path).to_spec_blocks()

    assert len(blocks) == 2
    assert {block.type for block in blocks} == {SpecType.KNOWLEDGE}
    assert any(block.pinned for block in blocks)
    assert any("claude_skill" in block.tags and not block.pinned for block in blocks)


def test_cursor_mdc_frontmatter_scopes_by_globs(tmp_path: Path) -> None:
    rule = tmp_path / ".cursor" / "rules" / "python.mdc"
    rule.parent.mkdir(parents=True)
    rule.write_text(
        "---\n"
        "description: Python rules\n"
        'globs: ["**/*.py", "**/*.pyi"]\n'
        "---\n"
        "# Python\n\nUse ruff and type hints."
    )

    aggregator = GuidelinesAggregator(tmp_path)

    py_matches = aggregator.filter_by_file("src/app.py")
    md_matches = aggregator.filter_by_file("README.md")

    assert any(g.source_type == SourceType.CURSOR for g in py_matches)
    assert all(g.source_type != SourceType.CURSOR for g in md_matches)
    # Frontmatter must not leak into the body content.
    cursor = next(g for g in py_matches if g.source_type == SourceType.CURSOR)
    assert "globs:" not in cursor.content


def test_cursor_always_apply_rule_has_no_file_pattern(tmp_path: Path) -> None:
    rule = tmp_path / ".cursor" / "rules" / "global.mdc"
    rule.parent.mkdir(parents=True)
    rule.write_text(
        "---\nalwaysApply: true\nglobs: ['**/*.py']\n---\n# Global\n\nAlways prefer small diffs."
    )

    guidelines = GuidelinesParser().parse_file(rule, "cursor")

    assert guidelines
    assert all(g.file_pattern is None for g in guidelines)
    assert any("always-apply" in g.tags for g in guidelines)


def test_normalize_patterns_handles_list_and_csv() -> None:
    normalize = GuidelinesParser._normalize_patterns

    assert normalize(["**/*.py", "**/*.pyi"]) == "**/*.py,**/*.pyi"
    assert normalize("**/*.py, **/*.ts") == "**/*.py,**/*.ts"
    assert normalize("**/*.py") == "**/*.py"
    assert normalize(None) is None
    assert normalize([]) is None


def test_copilot_applyto_list_scopes_guideline(tmp_path: Path) -> None:
    instr = tmp_path / ".github" / "instructions" / "py.instructions.md"
    instr.parent.mkdir(parents=True)
    instr.write_text(
        "---\napplyTo: ['**/*.py']\n---\n# Style\n\nKeep functions short."
    )

    aggregator = GuidelinesAggregator(tmp_path)

    assert any(g.source_type == SourceType.COPILOT for g in aggregator.filter_by_file("a.py"))
    assert all(g.source_type != SourceType.COPILOT for g in aggregator.filter_by_file("a.md"))


def test_build_context_layers_always_file_scoped_and_task_skills(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("# Architecture\n\nPreserve repository intent.")

    instr = tmp_path / ".github" / "instructions" / "python.instructions.md"
    instr.parent.mkdir(parents=True)
    instr.write_text("---\napplyTo: ['**/*.py']\n---\n# Python\n\nUse type hints.")

    skill = tmp_path / ".codex" / "skills" / "qdrant-memory" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\n"
        "name: qdrant-memory\n"
        "description: Design Qdrant memory retrieval for coding agents\n"
        "---\n"
        "# Workflow\n\nUse payload filters."
    )

    context = GuidelinesAggregator(tmp_path).build_context(
        files=["src/app.py"],
        task="improve qdrant memory retrieval",
    )

    assert [g.source_type for g in context["always_on"]] == [SourceType.AGENTS]
    assert [g.source_type for g in context["file_scoped"]] == [SourceType.COPILOT]
    assert [g.source_type for g in context["skills"]] == [SourceType.CODEX_SKILL]


def test_optimized_skill_artifact_is_used_only_when_enabled(tmp_path: Path) -> None:
    skill = tmp_path / ".codex" / "skills" / "qdrant-memory" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "---\n"
        "name: qdrant-memory\n"
        "description: Design Qdrant memory retrieval\n"
        "---\n"
        "# Workflow\n\nUse payload filters."
    )
    candidate = tmp_path / "candidate.md"
    candidate.write_text(
        "# Workflow\n\n"
        "Use payload filters.\n\n"
        "## Verification\n\n"
        "Before indexing retrieval skills, verify that task intent, collection name, "
        "and metadata filters are all represented in the final memory text."
    )

    result = OptimizedSkillStore(tmp_path).promote_candidate(
        skill,
        candidate,
        score_before=0.4,
        score_after=0.8,
        evaluator="unit",
    )

    assert result.accepted

    default_blocks = GuidelinesAggregator(tmp_path).to_spec_blocks()
    optimized_blocks = GuidelinesAggregator(tmp_path).to_spec_blocks(optimize_skills=True)

    assert "Verify that task intent" not in default_blocks[0].text
    assert "verify that task intent" in optimized_blocks[0].text.lower()
    assert "optimized-skill" in optimized_blocks[0].tags
    assert "skillopt:validated" in optimized_blocks[0].tags


def test_stale_optimized_skill_artifact_is_ignored(tmp_path: Path) -> None:
    skill = tmp_path / ".claude" / "skills" / "review" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# Review\n\nFind regressions.")
    candidate = tmp_path / "candidate.md"
    candidate.write_text(
        "# Review\n\n"
        "Find regressions.\n\n"
        "## Evidence\n\n"
        "Check failing tests, changed call sites, and backwards compatibility notes."
    )

    result = OptimizedSkillStore(tmp_path).promote_candidate(
        skill,
        candidate,
        score_before=0.2,
        score_after=0.9,
        evaluator="unit",
    )
    assert result.accepted

    skill.write_text("# Review\n\nFind regressions and security issues.")

    blocks = GuidelinesAggregator(tmp_path).to_spec_blocks(optimize_skills=True)

    assert "backwards compatibility notes" not in blocks[0].text
    assert "security issues" in blocks[0].text
    assert "optimized-skill" not in blocks[0].tags


def test_instruction_generated_candidate_accepts_static_non_regression(tmp_path: Path) -> None:
    skill = tmp_path / ".codex" / "skills" / "review" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(
        "# Review\n\n"
        "Check regressions, compatibility, tests, and project-specific constraints."
    )
    candidate = tmp_path / "candidate.md"
    candidate.write_text(
        "# Review\n\n"
        "Check regressions, compatibility, tests, and project-specific constraints.\n\n"
        "## Retrieval Notes\n\n"
        "Keep review keywords explicit so this skill is easier to select for code review tasks."
    )

    result = OptimizedSkillStore(tmp_path).promote_candidate(
        skill,
        candidate,
        evaluator="openai:test",
        allow_static_non_regression=True,
    )

    assert result.accepted
    assert result.score_after > result.score_before

    blocks = GuidelinesAggregator(tmp_path).to_spec_blocks(optimize_skills=True)

    assert "Retrieval Notes" in blocks[0].text
    assert any(tag.startswith("skillopt:score:") for tag in blocks[0].tags)
