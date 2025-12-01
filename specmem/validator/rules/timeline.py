"""Timeline validation rule for SpecValidator.

Detects impossible or conflicting timeline constraints.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue
from specmem.validator.rules.base import ValidationRule


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class TimelineRule(ValidationRule):
    """Validate timeline constraints in specifications."""

    rule_id = "timelines"
    name = "Timeline Validation"
    description = "Finds impossible or conflicting timelines"
    default_severity = IssueSeverity.ERROR

    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Find timeline issues in specs.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of timeline issues found
        """
        issues: list[ValidationIssue] = []

        for spec in specs:
            issues.extend(self._check_past_deadlines(spec, config))
            issues.extend(self._check_missing_time_units(spec, config))

        return issues

    def _check_past_deadlines(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for deadlines in the past.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text = spec.text
        today = datetime.now().date()

        # Match date patterns
        patterns = [
            (r"deadline[:\s]+(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
            (r"due\s+(?:by\s+)?(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
            (r"complete\s+by\s+(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
            (r"target\s+date[:\s]+(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
            (r"(\d{4}-\d{2}-\d{2})\s+deadline", "%Y-%m-%d"),
        ]

        for pattern, date_format in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group(1)
                try:
                    deadline = datetime.strptime(date_str, date_format).date()
                    if deadline < today:
                        issues.append(
                            self.create_issue(
                                message=f"Deadline in the past: {date_str}",
                                spec_id=spec.id,
                                config=config,
                                file_path=spec.source,
                                context={
                                    "deadline": date_str,
                                    "today": str(today),
                                    "type": "past_deadline",
                                },
                                suggestion="Update the deadline to a future date",
                            )
                        )
                except ValueError:
                    # Invalid date format, skip
                    pass

        return issues

    def _check_missing_time_units(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for time values without units.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text = spec.text

        # Match patterns like "response time: 100" without units
        patterns = [
            r"(?:response\s+time|latency|timeout|duration)[:\s]+(\d+)(?!\s*(?:ms|milliseconds?|seconds?|minutes?|hours?|days?))",
            r"(?:within|under|less\s+than)\s+(\d+)(?!\s*(?:ms|milliseconds?|seconds?|minutes?|hours?|days?|%))",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=IssueSeverity.WARNING,
                        message=f"Time value '{value}' missing units",
                        spec_id=spec.id,
                        file_path=spec.source,
                        context={"value": value, "type": "missing_units"},
                        suggestion="Add time units (ms, seconds, minutes, etc.)",
                    )
                )

        return issues
