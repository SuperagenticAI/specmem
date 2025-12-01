"""Acceptance criteria validation rule for SpecValidator.

Validates that specifications have proper acceptance criteria following EARS patterns.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue
from specmem.validator.rules.base import ValidationRule


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class AcceptanceCriteriaRule(ValidationRule):
    """Validate acceptance criteria completeness and format."""

    rule_id = "acceptance_criteria"
    name = "Acceptance Criteria Validation"
    description = "Ensures requirements have proper acceptance criteria"
    default_severity = IssueSeverity.ERROR

    # EARS (Easy Approach to Requirements Syntax) patterns
    EARS_PATTERNS = [
        r"WHEN\s+.+\s+THEN\s+.+\s+SHALL",  # Event-driven
        r"WHILE\s+.+\s+THE\s+.+\s+SHALL",  # State-driven
        r"IF\s+.+\s+THEN\s+.+\s+SHALL",  # Unwanted behavior
        r"WHERE\s+.+\s+THE\s+.+\s+SHALL",  # Optional feature
        r"THE\s+.+\s+SHALL",  # Ubiquitous
    ]

    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Validate acceptance criteria in specs.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of validation issues found
        """
        issues: list[ValidationIssue] = []
        min_criteria = config.min_acceptance_criteria

        for spec in specs:
            # Check for acceptance criteria section
            has_ac_section = self._has_acceptance_criteria_section(spec.text)

            if not has_ac_section:
                issues.append(
                    self.create_issue(
                        message="Missing acceptance criteria section",
                        spec_id=spec.id,
                        config=config,
                        file_path=spec.source,
                        suggestion="Add an 'Acceptance Criteria' section with testable conditions",
                    )
                )
                continue

            # Count criteria
            criteria_count = self._count_acceptance_criteria(spec.text)
            if criteria_count < min_criteria:
                issues.append(
                    self.create_issue(
                        message=f"Insufficient acceptance criteria: found {criteria_count}, minimum {min_criteria}",
                        spec_id=spec.id,
                        config=config,
                        file_path=spec.source,
                        context={"criteria_count": criteria_count, "minimum": min_criteria},
                        suggestion=f"Add {min_criteria - criteria_count} more acceptance criteria",
                    )
                )

            # Check EARS pattern compliance
            if not self._has_ears_patterns(spec.text):
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=IssueSeverity.WARNING,  # Warning, not error
                        message="Acceptance criteria should follow EARS patterns (WHEN...THEN...SHALL)",
                        spec_id=spec.id,
                        file_path=spec.source,
                        suggestion="Use EARS patterns: WHEN <condition> THEN <system> SHALL <response>",
                    )
                )

            # Check for undefined term references
            undefined_terms = self._find_undefined_terms(spec.text)
            for term in undefined_terms:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=IssueSeverity.WARNING,
                        message=f"Potentially undefined term: '{term}'",
                        spec_id=spec.id,
                        file_path=spec.source,
                        context={"term": term},
                        suggestion=f"Define '{term}' in the glossary or requirements",
                    )
                )

        return issues

    def _has_acceptance_criteria_section(self, text: str) -> bool:
        """Check if text has an acceptance criteria section.

        Args:
            text: Spec text to check

        Returns:
            True if acceptance criteria section exists
        """
        patterns = [
            r"acceptance\s+criteria",
            r"##\s*acceptance",
            r"###\s*acceptance",
            r"\*\*acceptance\s+criteria\*\*",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in patterns)

    def _count_acceptance_criteria(self, text: str) -> int:
        """Count numbered acceptance criteria in text.

        Args:
            text: Spec text to analyze

        Returns:
            Number of acceptance criteria found
        """
        lines = text.split("\n")
        in_criteria_section = False
        count = 0

        for line in lines:
            line_stripped = line.strip()
            line_lower = line_stripped.lower()

            # Check if entering acceptance criteria section
            if "acceptance criteria" in line_lower or ("acceptance" in line_lower and "##" in line):
                in_criteria_section = True
                continue

            # Check if leaving section (new heading)
            if (
                in_criteria_section
                and line_stripped.startswith("#")
                and "acceptance" not in line_lower
            ):
                break

            # Count numbered items in criteria section
            if in_criteria_section:
                # Match numbered lists: "1.", "1)", "- 1.", etc.
                if re.match(r"^\d+[\.\)]\s+", line_stripped) or any(
                    re.search(p, line_stripped, re.IGNORECASE) for p in self.EARS_PATTERNS
                ):
                    count += 1

        return count

    def _has_ears_patterns(self, text: str) -> bool:
        """Check if text contains EARS patterns.

        Args:
            text: Spec text to check

        Returns:
            True if EARS patterns found
        """
        text_upper = text.upper()
        return any(re.search(p, text_upper) for p in self.EARS_PATTERNS)

    def _find_undefined_terms(self, text: str) -> list[str]:
        """Find potentially undefined terms in text.

        Looks for capitalized terms that might need definition.

        Args:
            text: Spec text to analyze

        Returns:
            List of potentially undefined terms
        """
        # Find capitalized multi-word terms (potential domain terms)
        pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
        matches = re.findall(pattern, text)

        # Filter out common phrases
        common_phrases = {
            "Acceptance Criteria",
            "User Story",
            "As A",
            "So That",
            "The System",
            "The User",
            "When The",
            "Then The",
        }

        undefined = []
        for match in matches:
            if match not in common_phrases and match not in undefined:
                # Check if term is defined in glossary
                if not self._is_term_defined(text, match):
                    undefined.append(match)

        return undefined[:5]  # Limit to 5 terms

    def _is_term_defined(self, text: str, term: str) -> bool:
        """Check if a term is defined in the text.

        Args:
            text: Full spec text
            term: Term to check

        Returns:
            True if term appears to be defined
        """
        # Check for glossary definition patterns
        patterns = [
            rf"\*\*{re.escape(term)}\*\*\s*:",  # **Term**: definition
            rf"- {re.escape(term)}:",  # - Term: definition
            rf"{re.escape(term)}\s*-\s*",  # Term - definition
        ]

        return any(re.search(p, text) for p in patterns)
