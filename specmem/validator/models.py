"""Data models for SpecValidator.

Defines core data structures for validation issues and results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A specific problem found during validation."""

    rule_id: str
    severity: IssueSeverity
    message: str
    spec_id: str
    file_path: str | None = None
    line_number: int | None = None
    context: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "spec_id": self.spec_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "context": self.context,
            "suggestion": self.suggestion,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationIssue:
        """Deserialize from dictionary."""
        return cls(
            rule_id=data["rule_id"],
            severity=IssueSeverity(data["severity"]),
            message=data["message"],
            spec_id=data["spec_id"],
            file_path=data.get("file_path"),
            line_number=data.get("line_number"),
            context=data.get("context", {}),
            suggestion=data.get("suggestion"),
        )


@dataclass
class ValidationResult:
    """Result of running validation."""

    issues: list[ValidationIssue] = field(default_factory=list)
    specs_validated: int = 0
    rules_run: int = 0
    duration_ms: float = 0.0
    validated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_valid(self) -> bool:
        """True if no errors found."""
        return not any(i.severity == IssueSeverity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Count of info-level issues."""
        return sum(1 for i in self.issues if i.severity == IssueSeverity.INFO)

    def get_by_severity(self, severity: IssueSeverity) -> list[ValidationIssue]:
        """Get issues filtered by severity."""
        return [i for i in self.issues if i.severity == severity]

    def get_by_spec(self, spec_id: str) -> list[ValidationIssue]:
        """Get issues filtered by spec ID."""
        return [i for i in self.issues if i.spec_id == spec_id]

    def get_by_rule(self, rule_id: str) -> list[ValidationIssue]:
        """Get issues filtered by rule ID."""
        return [i for i in self.issues if i.rule_id == rule_id]

    def get_errors(self) -> list[ValidationIssue]:
        """Get all error-level issues."""
        return self.get_by_severity(IssueSeverity.ERROR)

    def get_warnings(self) -> list[ValidationIssue]:
        """Get all warning-level issues."""
        return self.get_by_severity(IssueSeverity.WARNING)

    def get_info(self) -> list[ValidationIssue]:
        """Get all info-level issues."""
        return self.get_by_severity(IssueSeverity.INFO)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "issues": [i.to_dict() for i in self.issues],
            "specs_validated": self.specs_validated,
            "rules_run": self.rules_run,
            "duration_ms": self.duration_ms,
            "validated_at": self.validated_at.isoformat(),
            "summary": {
                "is_valid": self.is_valid,
                "error_count": self.error_count,
                "warning_count": self.warning_count,
                "info_count": self.info_count,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationResult:
        """Deserialize from dictionary."""
        return cls(
            issues=[ValidationIssue.from_dict(i) for i in data.get("issues", [])],
            specs_validated=data.get("specs_validated", 0),
            rules_run=data.get("rules_run", 0),
            duration_ms=data.get("duration_ms", 0.0),
            validated_at=datetime.fromisoformat(data["validated_at"])
            if data.get("validated_at")
            else datetime.now(),
        )
