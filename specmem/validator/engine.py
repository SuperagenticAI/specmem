"""Validation engine for SpecValidator.

Orchestrates validation rules and aggregates results.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from specmem.validator.config import ValidationConfig
from specmem.validator.models import ValidationIssue, ValidationResult


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.rules.base import ValidationRule


class ValidationEngine:
    """Engine that runs validation rules against specifications."""

    def __init__(self, config: ValidationConfig | None = None) -> None:
        """Initialize the validation engine.

        Args:
            config: Validation configuration. Uses defaults if not provided.
        """
        self.config = config or ValidationConfig()
        self._rules: list[ValidationRule] = []

    def register_rule(self, rule: ValidationRule) -> None:
        """Register a validation rule.

        Args:
            rule: The validation rule to register
        """
        self._rules.append(rule)

    def register_rules(self, rules: list[ValidationRule]) -> None:
        """Register multiple validation rules.

        Args:
            rules: List of validation rules to register
        """
        for rule in rules:
            self.register_rule(rule)

    def validate(self, specs: list[SpecBlock]) -> ValidationResult:
        """Run all enabled validation rules against specs.

        Args:
            specs: List of specifications to validate

        Returns:
            ValidationResult with all issues found
        """
        start_time = time.perf_counter()
        all_issues: list[ValidationIssue] = []
        rules_run = 0

        for rule in self._rules:
            if rule.is_enabled(self.config):
                try:
                    issues = rule.validate(specs, self.config)
                    all_issues.extend(issues)
                    rules_run += 1
                except Exception as e:
                    # Create an error issue for rule failures
                    all_issues.append(
                        ValidationIssue(
                            rule_id=rule.rule_id,
                            severity=rule.default_severity,
                            message=f"Rule execution failed: {e}",
                            spec_id="__engine__",
                            context={"error": str(e), "rule_name": rule.name},
                        )
                    )
                    rules_run += 1

        duration_ms = (time.perf_counter() - start_time) * 1000

        return ValidationResult(
            issues=all_issues,
            specs_validated=len(specs),
            rules_run=rules_run,
            duration_ms=duration_ms,
        )

    def validate_single(self, spec: SpecBlock) -> ValidationResult:
        """Validate a single specification.

        Args:
            spec: The specification to validate

        Returns:
            ValidationResult with issues found
        """
        return self.validate([spec])

    @property
    def rules(self) -> list[ValidationRule]:
        """Get registered rules."""
        return self._rules.copy()

    @property
    def enabled_rules(self) -> list[ValidationRule]:
        """Get only enabled rules."""
        return [r for r in self._rules if r.is_enabled(self.config)]

    def clear_rules(self) -> None:
        """Remove all registered rules."""
        self._rules.clear()
