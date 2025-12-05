"""Sample guidelines provider for demonstration."""

from __future__ import annotations

from specmem.guidelines.models import Guideline, SourceType


class SampleGuidelinesProvider:
    """Provides sample guideline files for demonstration."""

    def get_sample_claude(self) -> list[Guideline]:
        """Get sample CLAUDE.md guidelines.

        Returns:
            List of sample Claude guidelines
        """
        content = """This project uses Python 3.11+ with type hints.

Key conventions:
- Use ruff for linting and formatting
- Line length: 100 characters
- Use Google-style docstrings
- All functions must have type hints

Testing:
- Use pytest for testing
- Property-based tests with hypothesis
- Aim for 80%+ coverage"""

        return [
            Guideline(
                id=Guideline.generate_id("sample/CLAUDE.md", "Project Guidelines"),
                title="Project Guidelines",
                content=content,
                source_type=SourceType.SAMPLE,
                source_file="sample/CLAUDE.md",
                tags=["sample", "claude", "guidelines"],
                is_sample=True,
            )
        ]

    def get_sample_cursorrules(self) -> list[Guideline]:
        """Get sample .cursorrules guidelines.

        Returns:
            List of sample Cursor guidelines
        """
        content = """You are an expert Python developer.

When writing code:
- Follow PEP 8 style guidelines
- Use meaningful variable names
- Add docstrings to all public functions
- Handle errors gracefully

When reviewing code:
- Check for security vulnerabilities
- Ensure proper error handling
- Verify type hints are present"""

        return [
            Guideline(
                id=Guideline.generate_id("sample/.cursorrules", "Cursor Rules"),
                title="Cursor Rules",
                content=content,
                source_type=SourceType.SAMPLE,
                source_file="sample/.cursorrules",
                tags=["sample", "cursor", "rules"],
                is_sample=True,
            )
        ]

    def get_sample_agents(self) -> list[Guideline]:
        """Get sample AGENTS.md guidelines.

        Returns:
            List of sample Agents guidelines
        """
        content = """Agent Instructions for this project:

1. Always read existing code before making changes
2. Follow the established patterns in the codebase
3. Write tests for new functionality
4. Update documentation when adding features
5. Use semantic commit messages"""

        return [
            Guideline(
                id=Guideline.generate_id("sample/AGENTS.md", "Agent Instructions"),
                title="Agent Instructions",
                content=content,
                source_type=SourceType.SAMPLE,
                source_file="sample/AGENTS.md",
                tags=["sample", "agents", "instructions"],
                is_sample=True,
            )
        ]

    def get_all_samples(self) -> list[Guideline]:
        """Get all sample guidelines.

        Returns:
            List of all sample guidelines
        """
        samples: list[Guideline] = []
        samples.extend(self.get_sample_claude())
        samples.extend(self.get_sample_cursorrules())
        samples.extend(self.get_sample_agents())
        return samples
