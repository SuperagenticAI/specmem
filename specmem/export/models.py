"""Data models for static dashboard export.

This module defines the data structures used for exporting spec data
to a static dashboard deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypedDict


class FeatureCoverageDict(TypedDict):
    """TypedDict for feature coverage in JSON output."""

    feature_name: str
    coverage_percentage: float
    tested_count: int
    total_count: int


class HealthBreakdownDict(TypedDict):
    """TypedDict for health breakdown in JSON output."""

    category: str
    score: float
    weight: float


class SpecDataDict(TypedDict, total=False):
    """TypedDict for spec data in JSON output."""

    name: str
    path: str
    requirements: str
    design: str | None
    tasks: str | None
    task_total: int
    task_completed: int


class GuidelineDataDict(TypedDict):
    """TypedDict for guideline data in JSON output."""

    name: str
    path: str
    content: str
    source_format: str


class HistoryEntryDict(TypedDict):
    """TypedDict for history entry in JSON output."""

    timestamp: str
    coverage_percentage: float
    health_score: float
    validation_errors: int


class ExportBundleDict(TypedDict, total=False):
    """TypedDict for complete export bundle in JSON output."""

    metadata: dict
    coverage: dict
    health: dict
    validation: dict
    specs: list[SpecDataDict]
    guidelines: list[GuidelineDataDict]
    history: list[HistoryEntryDict] | None


@dataclass
class FeatureCoverage:
    """Coverage data for a single feature."""

    feature_name: str
    coverage_percentage: float
    tested_count: int
    total_count: int

    def to_dict(self) -> FeatureCoverageDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "feature_name": self.feature_name,
            "coverage_percentage": self.coverage_percentage,
            "tested_count": self.tested_count,
            "total_count": self.total_count,
        }


@dataclass
class HealthBreakdown:
    """Health score breakdown by category."""

    category: str
    score: float
    weight: float

    def to_dict(self) -> HealthBreakdownDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "score": self.score,
            "weight": self.weight,
        }


@dataclass
class SpecData:
    """Data for a single specification."""

    name: str
    path: str
    requirements: str
    design: str | None = None
    tasks: str | None = None
    task_total: int = 0
    task_completed: int = 0

    def to_dict(self) -> SpecDataDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "requirements": self.requirements,
            "design": self.design,
            "tasks": self.tasks,
            "task_total": self.task_total,
            "task_completed": self.task_completed,
        }


@dataclass
class GuidelineData:
    """Data for a single coding guideline."""

    name: str
    path: str
    content: str
    source_format: str

    def to_dict(self) -> GuidelineDataDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "content": self.content,
            "source_format": self.source_format,
        }


@dataclass
class HistoryEntry:
    """Historical data point for trends."""

    timestamp: datetime
    coverage_percentage: float
    health_score: float
    validation_errors: int

    def to_dict(self) -> HistoryEntryDict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "coverage_percentage": self.coverage_percentage,
            "health_score": self.health_score,
            "validation_errors": self.validation_errors,
        }

    @classmethod
    def from_dict(cls, data: HistoryEntryDict) -> HistoryEntry:
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            coverage_percentage=data["coverage_percentage"],
            health_score=data["health_score"],
            validation_errors=data["validation_errors"],
        )


@dataclass
class ExportMetadata:
    """Metadata about the export."""

    generated_at: datetime
    commit_sha: str | None
    branch: str | None
    specmem_version: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "specmem_version": self.specmem_version,
        }


@dataclass
class ExportBundle:
    """Complete data bundle for static dashboard."""

    metadata: ExportMetadata
    coverage_percentage: float = 0.0
    features: list[FeatureCoverage] = field(default_factory=list)
    health_score: float = 0.0
    health_grade: str = "N/A"
    health_breakdown: list[HealthBreakdown] = field(default_factory=list)
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)
    specs: list[SpecData] = field(default_factory=list)
    guidelines: list[GuidelineData] = field(default_factory=list)
    history: list[HistoryEntry] | None = None

    def to_dict(self) -> ExportBundleDict:
        """Convert to dictionary for JSON serialization."""
        result: ExportBundleDict = {
            "metadata": self.metadata.to_dict(),
            "coverage": {
                "coverage_percentage": self.coverage_percentage,
                "features": [f.to_dict() for f in self.features],
            },
            "health": {
                "overall_score": self.health_score,
                "letter_grade": self.health_grade,
                "breakdown": [b.to_dict() for b in self.health_breakdown],
            },
            "validation": {
                "errors": self.validation_errors,
                "warnings": self.validation_warnings,
            },
            "specs": [s.to_dict() for s in self.specs],
            "guidelines": [g.to_dict() for g in self.guidelines],
        }
        if self.history is not None:
            result["history"] = [h.to_dict() for h in self.history]
        return result

    @property
    def required_keys(self) -> set[str]:
        """Return the set of required top-level keys."""
        return {"metadata", "coverage", "health", "validation", "specs", "guidelines"}
