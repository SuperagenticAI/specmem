"""Constraint validation rule for SpecValidator.

Detects invalid or impossible constraints in specifications.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue
from specmem.validator.rules.base import ValidationRule


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class ConstraintRule(ValidationRule):
    """Detect invalid constraints in specifications."""

    rule_id = "constraints"
    name = "Constraint Validation"
    description = "Finds impossible or invalid constraints"
    default_severity = IssueSeverity.ERROR

    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Find invalid constraints in specs.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of constraint issues found
        """
        issues: list[ValidationIssue] = []

        for spec in specs:
            issues.extend(self._check_impossible_percentages(spec, config))
            issues.extend(self._check_negative_counts(spec, config))
            issues.extend(self._check_conflicting_ranges(spec, config))
            issues.extend(self._check_negative_time(spec, config))

        return issues

    def _check_impossible_percentages(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for percentages > 100%.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text = spec.text

        # Match percentages like "150%", "200.5%" but not scientific notation
        # Negative lookbehind to avoid matching exponents like "e-135"
        pattern = r"(?<![eE][-+])(\d+(?:\.\d+)?)\s*%"
        for match in re.finditer(pattern, text):
            value = float(match.group(1))
            if value > 100:
                issues.append(
                    self.create_issue(
                        message=f"Impossible percentage: {value}%",
                        spec_id=spec.id,
                        config=config,
                        file_path=spec.source,
                        context={"value": value, "type": "percentage"},
                        suggestion="Percentages should be between 0% and 100%",
                    )
                )

        return issues

    def _check_negative_counts(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for negative count values.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text = spec.text

        # Match negative numbers followed by count-related words
        patterns = [
            r"(-\d+)\s+(?:users?|items?|requests?|connections?|records?|entries?)",
            r"(?:count|number|total)\s*[=:]\s*(-\d+)",
            r"(?:minimum|min)\s*[=:]\s*(-\d+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = int(match.group(1))
                if value < 0:
                    issues.append(
                        self.create_issue(
                            message=f"Negative count value: {value}",
                            spec_id=spec.id,
                            config=config,
                            file_path=spec.source,
                            context={"value": value, "type": "count"},
                            suggestion="Count values should be non-negative",
                        )
                    )

        return issues

    def _check_conflicting_ranges(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for min > max constraints.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text = spec.text

        # Match min/max patterns
        patterns = [
            # "minimum: 100, maximum: 50" or "min=100, max=50"
            r"min(?:imum)?\s*[=:]\s*(\d+(?:\.\d+)?)[^\d]*max(?:imum)?\s*[=:]\s*(\d+(?:\.\d+)?)",
            # "between 100 and 50"
            r"between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)",
            # "from 100 to 50"
            r"from\s+(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                min_val = float(match.group(1))
                max_val = float(match.group(2))
                if min_val > max_val:
                    issues.append(
                        self.create_issue(
                            message=f"Invalid range: minimum ({min_val}) > maximum ({max_val})",
                            spec_id=spec.id,
                            config=config,
                            file_path=spec.source,
                            context={"min": min_val, "max": max_val, "type": "range"},
                            suggestion="Ensure minimum value is less than or equal to maximum",
                        )
                    )

        return issues

    def _check_negative_time(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for negative time constraints.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text = spec.text

        # Match negative time values
        patterns = [
            r"(-\d+(?:\.\d+)?)\s*(?:ms|milliseconds?|seconds?|minutes?|hours?|days?)",
            r"(?:response\s+time|latency|duration|timeout)\s*[=:]\s*(-\d+(?:\.\d+)?)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(match.group(1))
                if value < 0:
                    issues.append(
                        self.create_issue(
                            message=f"Negative time constraint: {value}",
                            spec_id=spec.id,
                            config=config,
                            file_path=spec.source,
                            context={"value": value, "type": "time"},
                            suggestion="Time constraints should be non-negative",
                        )
                    )

        return issues
