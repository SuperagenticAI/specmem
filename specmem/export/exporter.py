"""Static dashboard data exporter.

This module provides the StaticExporter class for generating
data bundles for static dashboard deployment.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from specmem.export.models import (
    ExportBundle,
    ExportMetadata,
    FeatureCoverage,
    GuidelineData,
    HealthBreakdown,
    SpecData,
)


def get_specmem_version() -> str:
    """Get the current SpecMem version."""
    try:
        from specmem import __version__
        return __version__
    except ImportError:
        return "unknown"


def get_git_info() -> tuple[str | None, str | None]:
    """Get current git commit SHA and branch.

    Returns:
        Tuple of (commit_sha, branch_name)
    """
    commit_sha = None
    branch = None

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commit_sha = result.stdout.strip()[:12]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return commit_sha, branch


class StaticExporter:
    """Exports spec data for static dashboard deployment."""

    def __init__(self, workspace: Path, output_dir: Path | None = None):
        """Initialize the exporter.

        Args:
            workspace: Path to the workspace root
            output_dir: Output directory for export (default: .specmem/export/)
        """
        self.workspace = Path(workspace)
        self.output_dir = output_dir or (self.workspace / ".specmem" / "export")

    def export(self) -> ExportBundle:
        """Generate complete data export.

        Returns:
            ExportBundle containing all spec data
        """
        commit_sha, branch = get_git_info()

        metadata = ExportMetadata(
            generated_at=datetime.now(),
            commit_sha=commit_sha,
            branch=branch,
            specmem_version=get_specmem_version(),
        )

        bundle = ExportBundle(metadata=metadata)

        # Collect coverage data
        cov_data = self._run_coverage()
        bundle.coverage_percentage = cov_data.get("coverage_percentage", 0.0)
        bundle.features = self._parse_features(cov_data.get("features", []))

        # Collect health data
        health_data = self._run_health()
        bundle.health_score = health_data.get("overall_score", 0.0)
        bundle.health_grade = health_data.get("letter_grade", "N/A")
        bundle.health_breakdown = self._parse_breakdown(health_data.get("breakdown", []))

        # Collect validation data
        validate_data = self._run_validate()
        bundle.validation_errors = validate_data.get("errors", [])
        bundle.validation_warnings = validate_data.get("warnings", [])

        # Collect spec content
        bundle.specs = self._collect_specs()

        # Collect guidelines
        bundle.guidelines = self._collect_guidelines()

        return bundle

    def _run_coverage(self) -> dict[str, Any]:
        """Run specmem cov and return results."""
        return self._run_command("cov")

    def _run_health(self) -> dict[str, Any]:
        """Run specmem health and return results."""
        return self._run_command("health")

    def _run_validate(self) -> dict[str, Any]:
        """Run specmem validate and return results."""
        return self._run_command("validate")

    def _run_command(self, cmd: str) -> dict[str, Any]:
        """Run a specmem command with --robot flag.

        Args:
            cmd: The subcommand to run

        Returns:
            Parsed JSON output or empty dict on failure
        """
        try:
            result = subprocess.run(
                ["specmem", cmd, "--robot"],
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=300,
            )
            if result.stdout.strip():
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
        return {}

    def _parse_features(self, features: list[dict]) -> list[FeatureCoverage]:
        """Parse feature coverage data."""
        return [
            FeatureCoverage(
                feature_name=f.get("feature_name", "unknown"),
                coverage_percentage=f.get("coverage_percentage", 0.0),
                tested_count=f.get("tested_count", 0),
                total_count=f.get("total_count", 0),
            )
            for f in features
        ]

    def _parse_breakdown(self, breakdown: list[dict]) -> list[HealthBreakdown]:
        """Parse health breakdown data."""
        return [
            HealthBreakdown(
                category=b.get("category", "unknown"),
                score=b.get("score", 0.0),
                weight=b.get("weight", 0.0),
            )
            for b in breakdown
        ]

    def _collect_specs(self) -> list[SpecData]:
        """Collect all spec content from workspace."""
        specs = []
        specs_dir = self.workspace / ".kiro" / "specs"

        if not specs_dir.exists():
            return specs

        for spec_dir in specs_dir.iterdir():
            if not spec_dir.is_dir():
                continue

            req_file = spec_dir / "requirements.md"
            if not req_file.exists():
                continue

            spec = SpecData(
                name=spec_dir.name,
                path=str(spec_dir.relative_to(self.workspace)),
                requirements=req_file.read_text(encoding="utf-8"),
            )

            design_file = spec_dir / "design.md"
            if design_file.exists():
                spec.design = design_file.read_text(encoding="utf-8")

            tasks_file = spec_dir / "tasks.md"
            if tasks_file.exists():
                tasks_content = tasks_file.read_text(encoding="utf-8")
                spec.tasks = tasks_content
                spec.task_total, spec.task_completed = self._count_tasks(tasks_content)

            specs.append(spec)

        return specs

    def _count_tasks(self, tasks_content: str) -> tuple[int, int]:
        """Count total and completed tasks in tasks.md content.

        Args:
            tasks_content: Content of tasks.md file

        Returns:
            Tuple of (total_tasks, completed_tasks)
        """
        # Match checkbox patterns: - [ ] or - [x]
        unchecked = len(re.findall(r"- \[ \]", tasks_content))
        checked = len(re.findall(r"- \[x\]", tasks_content, re.IGNORECASE))
        return unchecked + checked, checked

    def _collect_guidelines(self) -> list[GuidelineData]:
        """Collect all coding guidelines from workspace."""
        guidelines = []

        # Check Kiro steering files
        steering_dir = self.workspace / ".kiro" / "steering"
        if steering_dir.exists():
            for md_file in steering_dir.glob("*.md"):
                guidelines.append(
                    GuidelineData(
                        name=md_file.stem,
                        path=str(md_file.relative_to(self.workspace)),
                        content=md_file.read_text(encoding="utf-8"),
                        source_format="kiro",
                    )
                )

        # Check Claude CLAUDE.md
        claude_file = self.workspace / "CLAUDE.md"
        if claude_file.exists():
            guidelines.append(
                GuidelineData(
                    name="CLAUDE",
                    path="CLAUDE.md",
                    content=claude_file.read_text(encoding="utf-8"),
                    source_format="claude",
                )
            )

        # Check Cursor .cursorrules
        cursor_file = self.workspace / ".cursorrules"
        if cursor_file.exists():
            guidelines.append(
                GuidelineData(
                    name="cursorrules",
                    path=".cursorrules",
                    content=cursor_file.read_text(encoding="utf-8"),
                    source_format="cursor",
                )
            )

        return guidelines

    def save(self, bundle: ExportBundle) -> Path:
        """Save bundle to JSON file.

        Args:
            bundle: The export bundle to save

        Returns:
            Path to the saved JSON file
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = self.output_dir / "data.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(bundle.to_dict(), f, indent=2)

        return output_file
