"""Duplicate detection rule for SpecValidator.

Detects duplicate or semantically similar specifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from specmem.validator.models import IssueSeverity, ValidationIssue
from specmem.validator.rules.base import ValidationRule


if TYPE_CHECKING:
    from specmem.core.specir import SpecBlock
    from specmem.validator.config import ValidationConfig


class DuplicateRule(ValidationRule):
    """Detect duplicate or similar specifications."""

    rule_id = "duplicates"
    name = "Duplicate Detection"
    description = "Finds semantically similar specifications"
    default_severity = IssueSeverity.WARNING

    def validate(
        self,
        specs: list[SpecBlock],
        config: ValidationConfig,
    ) -> list[ValidationIssue]:
        """Find duplicate or similar specs.

        Args:
            specs: List of specs to validate
            config: Validation configuration

        Returns:
            List of duplicate issues found
        """
        issues: list[ValidationIssue] = []
        threshold = config.similarity_threshold

        # Check for identical IDs
        seen_ids: dict[str, SpecBlock] = {}
        for spec in specs:
            if spec.id in seen_ids:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=IssueSeverity.ERROR,  # Duplicate IDs are errors
                        message=f"Duplicate spec ID: {spec.id}",
                        spec_id=spec.id,
                        file_path=spec.source,
                        context={
                            "original_source": seen_ids[spec.id].source,
                            "duplicate_source": spec.source,
                        },
                        suggestion="Use unique IDs for each specification",
                    )
                )
            else:
                seen_ids[spec.id] = spec

        # Check for semantic similarity
        for i, spec1 in enumerate(specs):
            for spec2 in specs[i + 1 :]:
                if spec1.id == spec2.id:
                    continue  # Already reported as duplicate ID

                similarity = self._calculate_similarity(spec1.text, spec2.text)
                if similarity >= threshold:
                    issues.append(
                        self.create_issue(
                            message=f"Potential duplicate: {similarity:.0%} similarity with {spec2.id}",
                            spec_id=spec1.id,
                            config=config,
                            file_path=spec1.source,
                            context={
                                "similar_spec_id": spec2.id,
                                "similar_spec_source": spec2.source,
                                "similarity_score": similarity,
                                "threshold": threshold,
                            },
                            suggestion="Consider consolidating similar specifications",
                        )
                    )

        return issues

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Tokenize and normalize
        words1 = set(self._tokenize(text1))
        words2 = set(self._tokenize(text2))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into normalized words.

        Args:
            text: Text to tokenize

        Returns:
            List of normalized words
        """
        # Simple word tokenization
        words = text.lower().split()

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "just",
            "and",
            "but",
            "if",
            "or",
        }

        return [w for w in words if w not in stop_words and len(w) > 2]
