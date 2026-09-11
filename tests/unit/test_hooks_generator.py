"""Unit tests for KiroHooksGenerator cue-anchored delivery hooks."""

from __future__ import annotations

import json
from pathlib import Path

from specmem.hooks.generator import KiroHook, KiroHooksGenerator


def test_generate_hooks_includes_session_start_event_cue(tmp_path: Path) -> None:
    generator = KiroHooksGenerator(tmp_path)
    hooks = generator.generate_hooks()

    session = next(h for h in hooks if h.name == "specmem-session-context")
    assert session.trigger == "session_start"
    assert session.action == "specmem guidelines context"
    assert "query" not in session.action.lower()
    assert session.file_pattern is None


def test_generate_hooks_includes_path_cue_file_save(tmp_path: Path) -> None:
    generator = KiroHooksGenerator(tmp_path)
    hooks = generator.generate_hooks()

    path_hook = next(h for h in hooks if h.name == "specmem-path-context")
    assert path_hook.trigger == "file_save"
    assert path_hook.file_pattern is not None
    assert "${file}" in path_hook.action
    assert "guidelines context" in path_hook.action
    assert "--file" in path_hook.action


def test_generate_hooks_keeps_validate_and_coverage(tmp_path: Path) -> None:
    generator = KiroHooksGenerator(tmp_path)
    by_name = {h.name: h for h in generator.generate_hooks()}

    assert "specmem-validate-on-save" in by_name
    assert by_name["specmem-validate-on-save"].trigger == "file_save"
    assert "validate" in by_name["specmem-validate-on-save"].action

    assert "specmem-coverage-on-test-save" in by_name
    assert by_name["specmem-coverage-on-test-save"].file_pattern == "tests/**/*.py"
    assert "cov" in by_name["specmem-coverage-on-test-save"].action


def test_write_hooks_does_not_overwrite_existing(tmp_path: Path) -> None:
    generator = KiroHooksGenerator(tmp_path)
    hooks_dir = tmp_path / ".kiro" / "hooks"
    hooks_dir.mkdir(parents=True)
    existing = hooks_dir / "specmem-session-context.json"
    existing.write_text(
        json.dumps(
            {
                "name": "specmem-session-context",
                "description": "user customized",
                "trigger": "session_start",
                "action": "echo custom",
                "enabled": True,
            }
        )
    )

    written = generator.write_hooks()
    assert written >= 1
    data = json.loads(existing.read_text())
    assert data["action"] == "echo custom"
    assert data["description"] == "user customized"


def test_write_hooks_creates_session_and_path_json(tmp_path: Path) -> None:
    generator = KiroHooksGenerator(tmp_path)
    count = generator.write_hooks()
    assert count == len(generator.generate_hooks())

    session_file = tmp_path / ".kiro" / "hooks" / "specmem-session-context.json"
    path_file = tmp_path / ".kiro" / "hooks" / "specmem-path-context.json"
    assert session_file.exists()
    assert path_file.exists()

    session = json.loads(session_file.read_text())
    path = json.loads(path_file.read_text())
    assert session["trigger"] == "session_start"
    assert session["action"] == "specmem guidelines context"
    assert path["trigger"] == "file_save"
    assert "guidelines context --file ${file}" in path["action"]


def test_kiro_hook_to_dict_omits_null_file_pattern() -> None:
    hook = KiroHook(
        name="demo",
        description="d",
        trigger="session_start",
        action="specmem guidelines context",
    )
    data = hook.to_dict()
    assert "filePattern" not in data
    assert data["action"] == "specmem guidelines context"
