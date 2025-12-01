"""Structure validation rule for SpecValidator.

Validates specification document structure and formatting.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue
from specmem.validator.rules.base import ValidationRule


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class StructureRule(ValidationRule):
    """Validate specification structure and formatting."""

    rule_id = "structure"
    name = "Structure Validation"
    description = "Validates document structure and formatting"
    default_severity = IssueSeverity.WARNING

    REQUIRED_SECTIONS = [
        "requirement",
        "user story",
        "acceptance criteria",
    ]

    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Validate spec structure.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of structure issues found
        """
        issues: list[ValidationIssue] = []

        for spec in specs:
            issues.extend(self._check_required_sections(spec, config))
            issues.extend(self._check_numbering_consistency(spec, config))
            issues.extend(self._check_spec_length(spec, config))
            issues.extend(self._check_markdown_formatting(spec, config))

        return issues

    def _check_required_sections(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for required sections.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        text_lower = spec.text.lower()

        # Check for at least one required section
        has_any_section = any(section in text_lower for section in self.REQUIRED_SECTIONS)

        if not has_any_section:
            issues.append(
                self.create_issue(
                    message="Missing required sections (requirement, user story, or acceptance criteria)",
                    spec_id=spec.id,
                    config=config,
                    file_path=spec.source,
                    suggestion="Add a User Story and Acceptance Criteria section",
                )
            )

        return issues

    def _check_numbering_consistency(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for consistent requirement numbering.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        lines = spec.text.split("\n")

        # Track numbered items
        numbers_found: list[int] = []
        for line in lines:
            match = re.match(r"^\s*(\d+)\.\s+", line)
            if match:
                numbers_found.append(int(match.group(1)))

        if len(numbers_found) >= 2:
            # Check for gaps or duplicates
            expected = list(range(1, len(numbers_found) + 1))
            if numbers_found != expected:
                # Check for duplicates
                if len(numbers_found) != len(set(numbers_found)):
                    issues.append(
                        self.create_issue(
                            message="Duplicate requirement numbers found",
                            spec_id=spec.id,
                            config=config,
                            file_path=spec.source,
                            context={"numbers": numbers_found},
                            suggestion="Ensure each requirement has a unique number",
                        )
                    )
                # Check for gaps
                elif sorted(numbers_found) != expected:
                    issues.append(
                        ValidationIssue(
                            rule_id=self.rule_id,
                            severity=IssueSeverity.INFO,
                            message="Requirement numbering has gaps",
                            spec_id=spec.id,
                            file_path=spec.source,
                            context={"numbers": numbers_found, "expected": expected},
                            suggestion="Consider renumbering for consistency",
                        )
                    )

        return issues

    def _check_spec_length(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check if spec exceeds maximum length.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        max_length = config.max_spec_length

        if len(spec.text) > max_length:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=IssueSeverity.WARNING,
                    message=f"Spec exceeds maximum length ({len(spec.text)} > {max_length})",
                    spec_id=spec.id,
                    file_path=spec.source,
                    context={
                        "length": len(spec.text),
                        "max_length": max_length,
                    },
                    suggestion="Consider splitting into smaller specifications",
                )
            )

        return issues

    def _check_markdown_formatting(
        self, spec: SpecBlock, config: ValidationConfig
    ) -> list[ValidationIssue]:
        """Check for common markdown formatting issues.

        Args:
            spec: Spec to check
            config: Validation configuration

        Returns:
            List of issues found
        """
        issues: list[ValidationIssue] = []
        lines = spec.text.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for unclosed bold/italic markers
            bold_count = line.count("**")
            if bold_count % 2 != 0:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=IssueSeverity.INFO,
                        message=f"Unclosed bold marker on line {i}",
                        spec_id=spec.id,
                        file_path=spec.source,
                        line_number=i,
                        suggestion="Close the bold marker with **",
                    )
                )

            # Check for heading without space
            if re.match(r"^#+[^#\s]", line):
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=IssueSeverity.INFO,
                        message=f"Heading missing space after # on line {i}",
                        spec_id=spec.id,
                        file_path=spec.source,
                        line_number=i,
                        suggestion="Add a space after the # characters",
                    )
                )

        return issues
