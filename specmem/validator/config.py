"""Configuration for SpecValidator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from specmem.validator.models import IssueSeverity


@dataclass
class RuleConfig:
    """Configuration for a single validation rule."""

    enabled: bool = True
    severity: IssueSeverity | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationConfig:
    """Configuration for validation."""

    rules: dict[str, RuleConfig] = field(default_factory=dict)
    similarity_threshold: float = 0.85
    min_acceptance_criteria: int = 2
    max_spec_length: int = 5000

    def is_rule_enabled(self, rule_id: str) -> bool:
        """Check if a rule is enabled."""
        if rule_id not in self.rules:
            return True  # Enabled by default
        return self.rules[rule_id].enabled

    def get_severity(self, rule_id: str, default: IssueSeverity) -> IssueSeverity:
        """Get severity for a rule, using default if not configured."""
        if rule_id in self.rules and self.rules[rule_id].severity:
            return self.rules[rule_id].severity
        return default

    def get_rule_option(self, rule_id: str, option: str, default: Any = None) -> Any:
        """Get a rule-specific option."""
        if rule_id in self.rules:
            return self.rules[rule_id].options.get(option, default)
        return default

    @classmethod
    def from_toml(cls, config: dict[str, Any]) -> ValidationConfig:
        """Load from .specmem.toml validation section."""
        validation = config.get("validation", {})

        rules = {}
        for rule_id, rule_config in validation.get("rules", {}).items():
            severity = None
            if "severity" in rule_config:
                severity = IssueSeverity(rule_config["severity"])
            rules[rule_id] = RuleConfig(
                enabled=rule_config.get("enabled", True),
                severity=severity,
                options=rule_config.get("options", {}),
            )

        return cls(
            rules=rules,
            similarity_threshold=validation.get("similarity_threshold", 0.85),
            min_acceptance_criteria=validation.get("min_acceptance_criteria", 2),
            max_spec_length=validation.get("max_spec_length", 5000),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "rules": {
                rule_id: {
                    "enabled": rc.enabled,
                    "severity": rc.severity.value if rc.severity else None,
                    "options": rc.options,
                }
                for rule_id, rc in self.rules.items()
            },
            "similarity_threshold": self.similarity_threshold,
            "min_acceptance_criteria": self.min_acceptance_criteria,
            "max_spec_length": self.max_spec_length,
        }
