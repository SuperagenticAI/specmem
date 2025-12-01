"""Data models for SpecMemClient API."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProposalStatus(str, Enum):
    """Status of a spec edit proposal."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class SpecSummary:
    """Condensed spec for context bundles."""

    id: str
    type: str
    title: str
    summary: str
    source: str
    relevance: float = 0.0
    pinned: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "relevance": self.relevance,
            "pinned": self.pinned,
        }


@dataclass
class TestMapping:
    """Framework-agnostic test reference."""

    spec_id: str
    framework: str  # pytest, jest, playwright, etc.
    path: str  # tests/test_auth.py::test_login
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "spec_id": self.spec_id,
            "framework": self.framework,
            "path": self.path,
            "tags": self.tags,
        }


@dataclass
class ContextBundle:
    """Optimized context bundle for agent consumption."""

    specs: list[SpecSummary] = field(default_factory=list)
    designs: list[SpecSummary] = field(default_factory=list)
    tests: list[TestMapping] = field(default_factory=list)
    tldr: str = ""
    total_tokens: int = 0
    token_budget: int = 4000
    changed_files: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "specs": [s.to_dict() for s in self.specs],
            "designs": [d.to_dict() for d in self.designs],
            "tests": [t.to_dict() for t in self.tests],
            "tldr": self.tldr,
            "total_tokens": self.total_tokens,
            "token_budget": self.token_budget,
            "changed_files": self.changed_files,
            "message": self.message,
        }

    def to_markdown(self) -> str:
        """Format as markdown for agent context."""
        lines = ["# Context Bundle", ""]

        if self.tldr:
            lines.extend(["## TL;DR", "", self.tldr, ""])

        if self.specs:
            lines.append("## Specifications")
            lines.append("")
            for spec in self.specs:
                pinned = "📌 " if spec.pinned else ""
                lines.append(f"### {pinned}{spec.title}")
                lines.append(f"*Type: {spec.type} | Source: {spec.source}*")
                lines.append("")
                lines.append(spec.summary)
                lines.append("")

        if self.designs:
            lines.append("## Designs")
            lines.append("")
            for design in self.designs:
                lines.append(f"### {design.title}")
                lines.append(f"*Source: {design.source}*")
                lines.append("")
                lines.append(design.summary)
                lines.append("")

        if self.tests:
            lines.append("## Related Tests")
            lines.append("")
            for test in self.tests:
                lines.append(f"- `{test.path}` ({test.framework})")
            lines.append("")

        if self.changed_files:
            lines.append("## Changed Files")
            lines.append("")
            for f in self.changed_files:
                lines.append(f"- `{f}`")
            lines.append("")

        lines.append(f"*Tokens: {self.total_tokens}/{self.token_budget}*")

        return "\n".join(lines)


@dataclass
class Proposal:
    """Agent-proposed spec edit."""

    id: str
    spec_id: str
    edits: dict[str, Any]
    rationale: str
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "edits": self.edits,
            "rationale": self.rationale,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Proposal":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            spec_id=data["spec_id"],
            edits=data["edits"],
            rationale=data["rationale"],
            status=ProposalStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            resolved_at=datetime.fromisoformat(data["resolved_at"])
            if data.get("resolved_at")
            else None,
        )
