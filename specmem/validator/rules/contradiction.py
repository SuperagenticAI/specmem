"""Contradiction detection rule for SpecValidator.

Detects contradictory requirements using negation patterns and semantic analysis.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue
from specmem.validator.rules.base import ValidationRule


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class ContradictionRule(ValidationRule):
    """Detect contradictory requirements between specifications."""

    rule_id = "contradiction"
    name = "Contradiction Detection"
    description = "Finds requirements that contradict each other"
    default_severity = IssueSeverity.ERROR

    # Negation patterns: (positive, negative)
    NEGATION_PATTERNS = [
        ("shall", "shall not"),
        ("must", "must not"),
        ("will", "will not"),
        ("can", "cannot"),
        ("should", "should not"),
        ("may", "may not"),
        ("is required", "is not required"),
        ("is allowed", "is not allowed"),
        ("enable", "disable"),
        ("allow", "deny"),
        ("permit", "prohibit"),
    ]

    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Find contradictory requirements.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of contradiction issues found
        """
        issues: list[ValidationIssue] = []

        # Check for negation pattern contradictions between specs
        for i, spec1 in enumerate(specs):
            for spec2 in specs[i + 1 :]:
                contradiction = self._check_negation_contradiction(spec1, spec2)
                if contradiction:
                    issues.append(
                        self.create_issue(
                            message=f"Contradiction detected: {contradiction['explanation']}",
                            spec_id=spec1.id,
                            config=config,
                            file_path=spec1.source,
                            context={
                                "conflicting_spec_id": spec2.id,
                                "conflicting_spec_source": spec2.source,
                                "spec1_text": spec1.text[:200],
                                "spec2_text": spec2.text[:200],
                                "conflict_type": contradiction["type"],
                                "subject": contradiction.get("subject", ""),
                            },
                            suggestion="Review both requirements and resolve the contradiction",
                        )
                    )

        return issues

    def _check_negation_contradiction(self, spec1: SpecBlock, spec2: SpecBlock) -> dict | None:
        """Check if two specs have negation pattern contradictions.

        Args:
            spec1: First spec to compare
            spec2: Second spec to compare

        Returns:
            Dictionary with contradiction details or None
        """
        text1 = spec1.text.lower()
        text2 = spec2.text.lower()

        for positive, negative in self.NEGATION_PATTERNS:
            # Check if spec1 has positive and spec2 has negative
            subject1 = self._extract_subject_after_modal(text1, positive)
            subject2 = self._extract_subject_after_modal(text2, negative)

            if subject1 and subject2 and self._subjects_overlap(subject1, subject2):
                return {
                    "type": "negation_pattern",
                    "explanation": f"'{positive}' vs '{negative}' on similar subjects",
                    "subject": subject1,
                }

            # Check reverse: spec1 has negative and spec2 has positive
            subject1 = self._extract_subject_after_modal(text1, negative)
            subject2 = self._extract_subject_after_modal(text2, positive)

            if subject1 and subject2 and self._subjects_overlap(subject1, subject2):
                return {
                    "type": "negation_pattern",
                    "explanation": f"'{negative}' vs '{positive}' on similar subjects",
                    "subject": subject1,
                }

        return None

    def _extract_subject_after_modal(self, text: str, modal: str) -> str | None:
        """Extract the subject phrase after a modal verb.

        Args:
            text: Text to search
            modal: Modal verb to find

        Returns:
            Subject phrase or None
        """
        # Match modal followed by up to 5 words
        pattern = rf"\b{re.escape(modal)}\s+((?:\w+\s*){{1,5}})"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None

    def _subjects_overlap(self, subject1: str, subject2: str) -> bool:
        """Check if two subjects have significant word overlap.

        Args:
            subject1: First subject phrase
            subject2: Second subject phrase

        Returns:
            True if subjects overlap significantly
        """
        # Remove common stop words and context words
        stop_words = {
            "the",
            "a",
            "an",
            "be",
            "to",
            "of",
            "and",
            "or",
            "in",
            "on",
            "at",
            "when",
            "under",
            "any",
            "all",
            "circumstances",
            "requested",
            "if",
            "then",
            "while",
            "during",
            "after",
            "before",
            "with",
            "without",
        }

        words1 = set(subject1.lower().split()) - stop_words
        words2 = set(subject2.lower().split()) - stop_words

        if not words1 or not words2:
            return False

        intersection = words1 & words2

        # If there's any meaningful word overlap, consider it a match
        # This catches cases like "AAA" appearing in both subjects
        return bool(intersection)
