"""Base class for validation rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class ValidationRule(ABC):
    """Base class for validation rules."""

    rule_id: str = "base"
    name: str = "Base Rule"
    description: str = "Base validation rule"
    default_severity: IssueSeverity = IssueSeverity.WARNING

    @abstractmethod
    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Run validation and return issues found.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of validation issues found
        """
        pass

    def is_enabled(self, config: ValidationConfig) -> bool:
        """Check if this rule is enabled in config."""
        return config.is_rule_enabled(self.rule_id)

    def get_severity(self, config: ValidationConfig) -> IssueSeverity:
        """Get severity for this rule from config."""
        return config.get_severity(self.rule_id, self.default_severity)

    def create_issue(
        self,
        message: str,
        spec_id: str,
        config: ValidationConfig,
        file_path: str | None = None,
        line_number: int | None = None,
        context: dict | None = None,
        suggestion: str | None = None,
    ) -> ValidationIssue:
        """Create a validation issue with this rule's settings."""
        return ValidationIssue(
            rule_id=self.rule_id,
            severity=self.get_severity(config),
            message=message,
            spec_id=spec_id,
            file_path=file_path,
            line_number=line_number,
            context=context or {},
            suggestion=suggestion,
        )
