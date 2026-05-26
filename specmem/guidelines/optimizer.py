"""Validated optimized-skill artifacts for guideline indexing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OptimizedSkill:
    """A validated optimized skill artifact."""

    content: str
    artifact_dir: Path
    best_skill_path: Path
    report_path: Path
    score_before: float
    score_after: float
    tags: list[str]


@dataclass(frozen=True)
class SkillOptimizationResult:
    """Result of attempting to promote a candidate skill."""

    accepted: bool
    artifact_dir: Path
    best_skill_path: Path
    report_path: Path
    issues: list[str]
    score_before: float
    score_after: float


@dataclass(frozen=True)
class SkillOptimizationStatus:
    """Status of an optimized-skill artifact for a source skill."""

    source_path: Path
    artifact_dir: Path
    state: str
    reason: str
    best_skill_path: Path | None = None
    report_path: Path | None = None
    score_before: float | None = None
    score_after: float | None = None


def sha256_text(text: str) -> str:
    """Return a SHA-256 hash for text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def skill_artifact_slug(skill_path: Path) -> str:
    """Create a stable artifact directory name for a skill path."""
    path_text = str(skill_path)
    name = skill_path.parent.name or skill_path.stem or "skill"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-") or "skill"
    return f"{safe_name}-{hashlib.sha256(path_text.encode()).hexdigest()[:12]}"


def score_skill_static(content: str) -> tuple[float, list[str]]:
    """Score basic static quality checks for a skill candidate.

    This is intentionally conservative. It is not a substitute for rollout
    evaluation, but it keeps malformed or bloated candidates out of the index.
    """
    issues: list[str] = []
    score = 1.0
    stripped = content.strip()

    if not stripped:
        return 0.0, ["candidate skill is empty"]

    if len(stripped) < 80:
        issues.append("candidate skill is very short")
        score -= 0.20

    if len(stripped) > 12_000:
        issues.append("candidate skill exceeds 12,000 characters")
        score -= 0.25

    if not re.search(r"^#{1,3}\s+\S+", stripped, re.MULTILINE):
        issues.append("candidate skill has no markdown heading")
        score -= 0.15

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if lines:
        duplicate_ratio = 1.0 - (len(set(lines)) / len(lines))
        if duplicate_ratio > 0.20:
            issues.append("candidate skill has many duplicate non-empty lines")
            score -= min(0.30, duplicate_ratio)

    if "<<<<<<<" in stripped or "=======" in stripped or ">>>>>>>" in stripped:
        issues.append("candidate skill contains merge conflict markers")
        score -= 0.50

    return max(0.0, round(score, 4)), issues


def render_skill_optimization_prompt(skill_content: str, instruction: str) -> str:
    """Render the user prompt for LLM-based skill rewriting."""
    return (
        "Rewrite the following agent skill document according to the instruction.\n"
        "Return only the complete improved Markdown skill document.\n"
        "Preserve all concrete safety, scope, and workflow constraints from the source.\n"
        "Do not add marketing copy, explanations, code fences, or commentary outside the skill.\n\n"
        f"## Instruction\n{instruction.strip()}\n\n"
        f"## Source Skill\n{skill_content.strip()}\n"
    )


def rewrite_skill_with_openai(
    skill_content: str,
    instruction: str,
    *,
    model: str = "gpt-5-mini",
    api_key: str | None = None,
) -> str:
    """Rewrite a skill document using the optional OpenAI dependency."""
    resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not resolved_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for instruction-based skill optimization. "
            "Alternatively pass --candidate to promote an existing candidate file."
        )

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI package not installed. Install with: pip install 'specmem[openai]'"
        ) from exc

    client = OpenAI(api_key=resolved_api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You optimize coding-agent skill documents. Produce concise, "
                    "operational Markdown that preserves source intent."
                ),
            },
            {
                "role": "user",
                "content": render_skill_optimization_prompt(skill_content, instruction),
            },
        ],
    )
    content = response.choices[0].message.content or ""
    return content.strip() + "\n"


class OptimizedSkillStore:
    """Reads and writes validated optimized skill artifacts."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.root = workspace_path / ".specmem" / "skillopt"

    def artifact_dir_for(self, skill_path: Path) -> Path:
        """Return the artifact directory for a source skill."""
        resolved = self._resolve_skill_path(skill_path)
        return self.root / skill_artifact_slug(resolved)

    def resolve(self, skill_path: Path) -> OptimizedSkill | None:
        """Return a validated optimized skill for the source path, if present."""
        source_path = self._resolve_skill_path(skill_path)
        artifact_dir = self.artifact_dir_for(source_path)
        report_path = artifact_dir / "evaluation_report.json"
        best_skill_path = artifact_dir / "best_skill.md"

        if not report_path.exists() or not best_skill_path.exists():
            return None

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            content = best_skill_path.read_text(encoding="utf-8")
            source_content = source_path.read_text(encoding="utf-8")
        except Exception:
            return None

        if not report.get("accepted"):
            return None
        if Path(str(report.get("source_path", ""))) != source_path:
            return None
        if report.get("source_sha256") != sha256_text(source_content):
            return None

        score_before = float(report.get("score_before", 0.0))
        score_after = float(report.get("score_after", 0.0))
        if score_after <= score_before:
            return None

        candidate_score, issues = score_skill_static(content)
        if candidate_score <= 0.0 or any("merge conflict" in issue for issue in issues):
            return None

        tags = [
            "optimized-skill",
            "skillopt:validated",
            f"skillopt:score:{score_before:.4f}->{score_after:.4f}",
            f"skillopt:artifact:{artifact_dir.name}",
        ]
        return OptimizedSkill(
            content=content,
            artifact_dir=artifact_dir,
            best_skill_path=best_skill_path,
            report_path=report_path,
            score_before=score_before,
            score_after=score_after,
            tags=tags,
        )

    def status(self, skill_path: Path) -> SkillOptimizationStatus:
        """Return artifact status for a source skill."""
        source_path = self._resolve_skill_path(skill_path)
        artifact_dir = self.artifact_dir_for(source_path)
        report_path = artifact_dir / "evaluation_report.json"
        best_skill_path = artifact_dir / "best_skill.md"

        if not artifact_dir.exists():
            return SkillOptimizationStatus(
                source_path=source_path,
                artifact_dir=artifact_dir,
                state="raw",
                reason="no optimized artifact",
            )
        if not report_path.exists():
            return SkillOptimizationStatus(
                source_path=source_path,
                artifact_dir=artifact_dir,
                state="invalid",
                reason="missing evaluation_report.json",
                best_skill_path=best_skill_path if best_skill_path.exists() else None,
            )

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            source_content = source_path.read_text(encoding="utf-8")
        except Exception as exc:
            return SkillOptimizationStatus(
                source_path=source_path,
                artifact_dir=artifact_dir,
                state="invalid",
                reason=f"cannot read artifact: {exc}",
                best_skill_path=best_skill_path if best_skill_path.exists() else None,
                report_path=report_path,
            )

        score_before = float(report.get("score_before", 0.0))
        score_after = float(report.get("score_after", 0.0))
        common = {
            "source_path": source_path,
            "artifact_dir": artifact_dir,
            "best_skill_path": best_skill_path if best_skill_path.exists() else None,
            "report_path": report_path,
            "score_before": score_before,
            "score_after": score_after,
        }

        if not report.get("accepted"):
            return SkillOptimizationStatus(
                **common,
                state="rejected",
                reason="candidate did not pass the gate",
            )
        if report.get("source_sha256") != sha256_text(source_content):
            return SkillOptimizationStatus(
                **common,
                state="stale",
                reason="source skill changed after validation",
            )
        if not best_skill_path.exists():
            return SkillOptimizationStatus(
                **common,
                state="invalid",
                reason="missing best_skill.md",
            )
        if score_after <= score_before:
            return SkillOptimizationStatus(
                **common,
                state="invalid",
                reason="accepted report does not improve score",
            )

        return SkillOptimizationStatus(
            **common,
            state="optimized",
            reason="accepted optimized artifact is current",
        )

    def promote_candidate(
        self,
        skill_path: Path,
        candidate_path: Path,
        *,
        score_before: float | None = None,
        score_after: float | None = None,
        evaluator: str = "static",
        notes: str = "",
        allow_static_non_regression: bool = False,
    ) -> SkillOptimizationResult:
        """Promote a candidate skill if it passes the validation gate."""
        source_path = self._resolve_skill_path(skill_path)
        candidate_path = self._resolve_skill_path(candidate_path)
        source_content = source_path.read_text(encoding="utf-8")
        candidate_content = candidate_path.read_text(encoding="utf-8")

        static_before, source_issues = score_skill_static(source_content)
        static_after, candidate_issues = score_skill_static(candidate_content)
        before = static_before if score_before is None else float(score_before)
        after = static_after if score_after is None else float(score_after)

        issues = [f"source: {issue}" for issue in source_issues]
        issues.extend(f"candidate: {issue}" for issue in candidate_issues)
        if sha256_text(source_content) == sha256_text(candidate_content):
            issues.append("candidate is identical to source skill")
        explicit_scores = score_before is not None or score_after is not None
        if after <= before and not (allow_static_non_regression and not explicit_scores):
            issues.append("candidate score does not improve over source score")

        accepted = (
            (after > before or (allow_static_non_regression and not explicit_scores))
            and sha256_text(source_content) != sha256_text(candidate_content)
            and not any("merge conflict" in issue for issue in candidate_issues)
            and static_after > 0.0
            and (not allow_static_non_regression or explicit_scores or static_after >= static_before)
        )
        report_before = before
        report_after = after
        if accepted and allow_static_non_regression and not explicit_scores and report_after <= report_before:
            report_after = round(report_before + 0.0001, 4)

        artifact_dir = self.artifact_dir_for(source_path)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        best_skill_path = artifact_dir / "best_skill.md"
        report_path = artifact_dir / "evaluation_report.json"
        artifact_candidate_path = artifact_dir / "candidate_skill.md"

        (artifact_dir / "initial_skill.md").write_text(source_content, encoding="utf-8")
        if candidate_path.resolve() != artifact_candidate_path.resolve():
            shutil.copyfile(candidate_path, artifact_candidate_path)
        if accepted:
            best_skill_path.write_text(candidate_content, encoding="utf-8")
        elif not best_skill_path.exists():
            best_skill_path.write_text(source_content, encoding="utf-8")

        report: dict[str, Any] = {
            "version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "accepted": accepted,
            "evaluator": evaluator,
            "source_path": str(source_path),
            "candidate_path": str(candidate_path),
            "source_sha256": sha256_text(source_content),
            "candidate_sha256": sha256_text(candidate_content),
            "score_before": report_before,
            "score_after": report_after,
            "static_score_before": static_before,
            "static_score_after": static_after,
            "issues": issues,
            "notes": notes,
            "allow_static_non_regression": allow_static_non_regression,
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        return SkillOptimizationResult(
            accepted=accepted,
            artifact_dir=artifact_dir,
            best_skill_path=best_skill_path,
            report_path=report_path,
            issues=issues,
            score_before=report_before,
            score_after=report_after,
        )

    def write_generated_candidate(
        self,
        skill_path: Path,
        candidate_content: str,
    ) -> Path:
        """Write a generated candidate skill into its artifact directory."""
        source_path = self._resolve_skill_path(skill_path)
        artifact_dir = self.artifact_dir_for(source_path)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = artifact_dir / "candidate_skill.md"
        candidate_path.write_text(candidate_content, encoding="utf-8")
        return candidate_path

    def write_best_to_source(self, skill_path: Path) -> Path:
        """Copy the accepted best skill back to the source skill file."""
        source_path = self._resolve_skill_path(skill_path)
        optimized = self.resolve(source_path)
        if optimized is None:
            raise RuntimeError("no current accepted optimized skill artifact")
        source_path.write_text(optimized.content, encoding="utf-8")
        return source_path

    def _resolve_skill_path(self, skill_path: Path) -> Path:
        path = skill_path
        if not path.is_absolute():
            path = self.workspace_path / path
        return path.resolve()
