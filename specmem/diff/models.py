"""Data models for SpecDiff temporal intelligence.

Defines the core data structures for tracking spec evolution,
changes, staleness, drift, and deprecations.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ChangeType(str, Enum):
    """Type of specification change."""

    SEMANTIC = "semantic"  # Meaning changed
    COSMETIC = "cosmetic"  # Formatting only
    BREAKING = "breaking"  # Breaking change
    ADDITION = "addition"  # New content added
    REMOVAL = "removal"  # Content removed


class Severity(str, Enum):
    """Severity level for warnings and drift."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SpecVersion:
    """A version of a specification at a point in time."""

    spec_id: str
    version_id: str
    timestamp: datetime
    content: str
    commit_ref: str | None = None
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute content hash if not provided."""
        if not self.content_hash:
            self.content_hash = self._compute_hash(self.content)

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spec_id": self.spec_id,
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "commit_ref": self.commit_ref,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecVersion:
        """Deserialize from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            version_id=data["version_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content=data["content"],
            commit_ref=data.get("commit_ref"),
            content_hash=data.get("content_hash", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ChangeReason:
    """Inferred reason for a specification change."""

    reason: str
    confidence: float
    source: str  # Where the reason was inferred from
    alternatives: list[ChangeReason] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "reason": self.reason,
            "confidence": self.confidence,
            "source": self.source,
            "alternatives": [alt.to_dict() for alt in self.alternatives],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeReason:
        """Deserialize from dictionary."""
        return cls(
            reason=data["reason"],
            confidence=data["confidence"],
            source=data["source"],
            alternatives=[cls.from_dict(alt) for alt in data.get("alternatives", [])],
        )


@dataclass
class ModifiedSection:
    """A section of a spec that was modified."""

    old_text: str
    new_text: str
    line_start: int = 0
    line_end: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "old_text": self.old_text,
            "new_text": self.new_text,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModifiedSection:
        """Deserialize from dictionary."""
        return cls(
            old_text=data["old_text"],
            new_text=data["new_text"],
            line_start=data.get("line_start", 0),
            line_end=data.get("line_end", 0),
        )


@dataclass
class SpecChange:
    """Changes between two specification versions."""

    spec_id: str
    from_version: str
    to_version: str
    timestamp: datetime
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    modified: list[ModifiedSection] = field(default_factory=list)
    change_type: ChangeType = ChangeType.SEMANTIC
    inferred_reason: ChangeReason | None = None

    def is_breaking(self) -> bool:
        """Check if this is a breaking change."""
        return self.change_type == ChangeType.BREAKING

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spec_id": self.spec_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "timestamp": self.timestamp.isoformat(),
            "added": self.added,
            "removed": self.removed,
            "modified": [m.to_dict() for m in self.modified],
            "change_type": self.change_type.value,
            "inferred_reason": self.inferred_reason.to_dict() if self.inferred_reason else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpecChange:
        """Deserialize from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            from_version=data["from_version"],
            to_version=data["to_version"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            added=data.get("added", []),
            removed=data.get("removed", []),
            modified=[ModifiedSection.from_dict(m) for m in data.get("modified", [])],
            change_type=ChangeType(data.get("change_type", "semantic")),
            inferred_reason=ChangeReason.from_dict(data["inferred_reason"])
            if data.get("inferred_reason")
            else None,
        )


@dataclass
class StalenessWarning:
    """Warning about stale specification memory."""

    spec_id: str
    cached_version: str
    current_version: str
    changes_since: list[SpecChange] = field(default_factory=list)
    severity: Severity = Severity.MEDIUM
    acknowledged: bool = False
    acknowledged_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spec_id": self.spec_id,
            "cached_version": self.cached_version,
            "current_version": self.current_version,
            "changes_since": [c.to_dict() for c in self.changes_since],
            "severity": self.severity.value,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StalenessWarning:
        """Deserialize from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            cached_version=data["cached_version"],
            current_version=data["current_version"],
            changes_since=[SpecChange.from_dict(c) for c in data.get("changes_since", [])],
            severity=Severity(data.get("severity", "medium")),
            acknowledged=data.get("acknowledged", False),
            acknowledged_at=datetime.fromisoformat(data["acknowledged_at"])
            if data.get("acknowledged_at")
            else None,
        )


@dataclass
class DriftItem:
    """A piece of code that has drifted from its specification."""

    code_path: str
    spec_id: str
    spec_change: SpecChange
    severity: float
    suggested_action: str = ""

    def __post_init__(self) -> None:
        """Validate severity range."""
        if not 0.0 <= self.severity <= 1.0:
            raise ValueError(f"Severity must be between 0.0 and 1.0, got {self.severity}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "code_path": self.code_path,
            "spec_id": self.spec_id,
            "spec_change": self.spec_change.to_dict(),
            "severity": self.severity,
            "suggested_action": self.suggested_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriftItem:
        """Deserialize from dictionary."""
        return cls(
            code_path=data["code_path"],
            spec_id=data["spec_id"],
            spec_change=SpecChange.from_dict(data["spec_change"]),
            severity=data["severity"],
            suggested_action=data.get("suggested_action", ""),
        )


@dataclass
class DriftReport:
    """Complete drift analysis report."""

    drifted_code: list[DriftItem] = field(default_factory=list)
    total_drift_score: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "drifted_code": [d.to_dict() for d in self.drifted_code],
            "total_drift_score": self.total_drift_score,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DriftReport:
        """Deserialize from dictionary."""
        return cls(
            drifted_code=[DriftItem.from_dict(d) for d in data.get("drifted_code", [])],
            total_drift_score=data.get("total_drift_score", 0.0),
            generated_at=datetime.fromisoformat(data["generated_at"])
            if data.get("generated_at")
            else datetime.now(),
        )

    def get_by_severity(self, min_severity: float) -> list[DriftItem]:
        """Get drift items above severity threshold."""
        return [d for d in self.drifted_code if d.severity >= min_severity]


@dataclass
class Contradiction:
    """A contradiction between spec versions."""

    spec_id: str
    old_text: str
    new_text: str
    conflict_type: str = "semantic"
    resolution_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spec_id": self.spec_id,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "conflict_type": self.conflict_type,
            "resolution_hint": self.resolution_hint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Contradiction:
        """Deserialize from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            old_text=data["old_text"],
            new_text=data["new_text"],
            conflict_type=data.get("conflict_type", "semantic"),
            resolution_hint=data.get("resolution_hint", ""),
        )


@dataclass
class Deprecation:
    """A deprecated specification."""

    spec_id: str
    deprecated_at: datetime
    deadline: datetime | None = None
    replacement_spec_id: str | None = None
    affected_code: list[str] = field(default_factory=list)
    urgency: float = 0.5

    def __post_init__(self) -> None:
        """Validate urgency range."""
        if not 0.0 <= self.urgency <= 1.0:
            raise ValueError(f"Urgency must be between 0.0 and 1.0, got {self.urgency}")

    def days_remaining(self) -> int | None:
        """Calculate days until deadline."""
        if not self.deadline:
            return None
        delta = self.deadline - datetime.now()
        return max(0, delta.days)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "spec_id": self.spec_id,
            "deprecated_at": self.deprecated_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "replacement_spec_id": self.replacement_spec_id,
            "affected_code": self.affected_code,
            "urgency": self.urgency,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Deprecation:
        """Deserialize from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            deprecated_at=datetime.fromisoformat(data["deprecated_at"]),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            replacement_spec_id=data.get("replacement_spec_id"),
            affected_code=data.get("affected_code", []),
            urgency=data.get("urgency", 0.5),
        )
