"""Test Mapping and Code Reference models for SpecMem.

This module defines the data models for mapping specifications to tests
and implementation code.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestMapping:
    """Framework-agnostic test reference.

    Maps a specification to a test that validates it.

    Attributes:
        framework: Test framework (pytest, jest, vitest, playwright, mocha)
        path: Test file path
        selector: Test selector (e.g., test_auth::test_login for pytest)
        confidence: Confidence score 0.0-1.0 for this mapping
        spec_ids: List of spec IDs this test validates
    """

    framework: str
    path: str
    selector: str
    confidence: float = 1.0
    spec_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.framework:
            raise ValueError("framework cannot be empty")
        if not self.path:
            raise ValueError("path cannot be empty")
        if not self.selector:
            raise ValueError("selector cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of the TestMapping
        """
        return {
            "framework": self.framework,
            "path": self.path,
            "selector": self.selector,
            "confidence": self.confidence,
            "spec_ids": self.spec_ids,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestMapping":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with TestMapping fields

        Returns:
            TestMapping instance
        """
        return cls(
            framework=data["framework"],
            path=data["path"],
            selector=data["selector"],
            confidence=data.get("confidence", 1.0),
            spec_ids=data.get("spec_ids", []),
        )


@dataclass
class CodeRef:
    """Reference linking a specification to implementation code.

    Attributes:
        language: Programming language (python, javascript, typescript)
        file_path: Source file path
        symbols: List of function/class names
        line_range: Optional tuple of (start_line, end_line)
        confidence: Confidence score 0.0-1.0 for this reference
    """

    language: str
    file_path: str
    symbols: list[str] = field(default_factory=list)
    line_range: tuple[int, int] | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.language:
            raise ValueError("language cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.line_range is not None:
            if not isinstance(self.line_range, tuple) or len(self.line_range) != 2:
                raise ValueError("line_range must be a tuple of (start, end)")
            start, end = self.line_range
            if not isinstance(start, int) or not isinstance(end, int):
                raise ValueError("line_range values must be integers")
            if start < 0 or end < 0:
                raise ValueError("line_range values must be non-negative")
            if start > end:
                raise ValueError("line_range start must be <= end")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation of the CodeRef
        """
        result = {
            "language": self.language,
            "file_path": self.file_path,
            "symbols": self.symbols,
            "confidence": self.confidence,
        }
        if self.line_range is not None:
            result["line_range"] = list(self.line_range)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodeRef":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with CodeRef fields

        Returns:
            CodeRef instance
        """
        line_range = data.get("line_range")
        if line_range is not None:
            line_range = tuple(line_range)

        return cls(
            language=data["language"],
            file_path=data["file_path"],
            symbols=data.get("symbols", []),
            line_range=line_range,
            confidence=data.get("confidence", 1.0),
        )
