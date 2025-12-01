"""Tessl adapter for SpecMem.

Tessl (https://tessl.io) is an AI-first development platform that generates
code from natural language specifications. This adapter handles:
- .tessl specification files
- .spec.ts/.spec.js executable specifications
- tessl.config.* configuration files
- tessl.yaml/tessl.json manifests
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from specmem.adapters.base import SpecAdapter
from specmem.core.specir import SpecBlock, SpecStatus, SpecType


logger = logging.getLogger(__name__)


class TesslAdapter(SpecAdapter):
    """Experimental adapter for Tessl specifications.

    Detects and parses:
    - .tessl specification files (YAML frontmatter + content)
    - .spec.ts/.spec.js executable specifications
    - tessl.config.* configuration files
    - tessl.yaml/tessl.json manifests
    """

    FILE_PATTERNS = [
        "**/*.tessl",
        "**/*.spec.ts",
        "**/*.spec.js",
        "**/tessl.config.*",
        "**/tessl.yaml",
        "**/tessl.json",
    ]

    @property
    def name(self) -> str:
        return "Tessl"

    def is_experimental(self) -> bool:
        """Tessl adapter is experimental."""
        return True

    def detect(self, repo_path: str) -> bool:
        """Check if Tessl specs exist in the repository."""
        path = Path(repo_path)
        if not path.exists():
            return False

        return any(list(path.glob(pattern)) for pattern in self.FILE_PATTERNS)

    def load(self, repo_path: str) -> list[SpecBlock]:
        """Load and parse all Tessl spec files."""
        self.warn_if_experimental()
        blocks: list[SpecBlock] = []
        path = Path(repo_path)

        if not path.exists():
            return blocks

        # Find all Tessl files
        tessl_files: list[Path] = []
        for pattern in self.FILE_PATTERNS:
            tessl_files.extend(path.glob(pattern))

        for file_path in tessl_files:
            try:
                file_blocks = self._parse_file(file_path)
                blocks.extend(file_blocks)
            except Exception as e:
                logger.warning(f"Failed to parse Tessl file {file_path}: {e}")
                # Continue processing other files (graceful degradation)

        logger.info(f"Loaded {len(blocks)} SpecBlocks from Tessl specs")
        return blocks

    def _parse_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse a Tessl file based on its type."""
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()

        if suffix == ".tessl":
            return self._parse_tessl_spec(file_path)
        elif suffix in (".ts", ".js") and ".spec." in name:
            return self._parse_executable_spec(file_path)
        elif "tessl.config" in name:
            return self._parse_config_file(file_path)
        elif name in ("tessl.yaml", "tessl.json"):
            return self._parse_manifest_file(file_path)
        else:
            logger.debug(f"Unknown Tessl file type: {file_path}")
            return []

    def _parse_tessl_spec(self, file_path: Path) -> list[SpecBlock]:
        """Parse a .tessl specification file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract YAML frontmatter and content
        metadata, spec_text = self._extract_frontmatter(content)

        # Extract dependencies from content
        dependencies = self._extract_dependencies(content)

        # Create main spec block
        block_id = SpecBlock.generate_id(source, f"tessl_{file_path.stem}")
        tags = ["tessl", "specification"]

        # Add metadata tags
        if metadata:
            if "tags" in metadata:
                if isinstance(metadata["tags"], list):
                    tags.extend(metadata["tags"])
                elif isinstance(metadata["tags"], str):
                    tags.extend(t.strip() for t in metadata["tags"].split(","))
            if "category" in metadata:
                tags.append(metadata["category"])

        blocks.append(
            SpecBlock(
                id=block_id,
                type=SpecType.REQUIREMENT,
                text=spec_text if spec_text else content[:500],
                source=source,
                status=SpecStatus.ACTIVE,
                tags=list(set(tags)),
                links=dependencies,
                pinned=metadata.get("pinned", False) if metadata else False,
            )
        )

        return blocks

    def _parse_executable_spec(self, file_path: Path) -> list[SpecBlock]:
        """Parse executable specification (.spec.ts/.spec.js)."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return blocks

        # Extract JSDoc comments as specifications
        jsdoc_specs = self._extract_jsdoc_specs(content)

        # Extract test case names
        test_cases = self._extract_test_cases(content)

        # Combine into spec text
        spec_text = jsdoc_specs
        if test_cases:
            spec_text += "\n\nTest Cases:\n" + "\n".join(f"- {tc}" for tc in test_cases)

        if spec_text.strip():
            block_id = SpecBlock.generate_id(source, f"tessl_spec_{file_path.stem}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.KNOWLEDGE,  # Test specs are knowledge artifacts
                    text=spec_text,
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["tessl", "executable", "test"],
                    links=[],
                    pinned=False,
                )
            )

        return blocks

    def _parse_config_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse Tessl configuration file."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
            suffix = file_path.suffix.lower()

            if suffix == ".json":
                config_data = json.loads(content)
            elif suffix in (".yaml", ".yml"):
                config_data = yaml.safe_load(content)
            else:
                # Try to parse as JSON first, then YAML
                try:
                    config_data = json.loads(content)
                except json.JSONDecodeError:
                    config_data = yaml.safe_load(content)

            config_text = self._format_config_as_text(config_data)

            block_id = SpecBlock.generate_id(source, f"tessl_config_{file_path.stem}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.DESIGN,
                    text=f"Tessl Configuration:\n{config_text}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["tessl", "config"],
                    links=[],
                    pinned=True,  # Config files are usually important
                )
            )

        except Exception as e:
            logger.warning(f"Failed to parse Tessl config {file_path}: {e}")

        return blocks

    def _parse_manifest_file(self, file_path: Path) -> list[SpecBlock]:
        """Parse Tessl manifest file (tessl.yaml/tessl.json)."""
        blocks: list[SpecBlock] = []
        source = str(file_path)

        try:
            content = file_path.read_text(encoding="utf-8")
            suffix = file_path.suffix.lower()

            manifest_data = json.loads(content) if suffix == ".json" else yaml.safe_load(content)

            # Extract dependencies from manifest
            dependencies = manifest_data.get("dependencies", [])
            if isinstance(dependencies, dict):
                dependencies = list(dependencies.keys())

            manifest_text = self._format_manifest_as_text(manifest_data)

            block_id = SpecBlock.generate_id(source, f"tessl_manifest_{file_path.stem}")
            blocks.append(
                SpecBlock(
                    id=block_id,
                    type=SpecType.DESIGN,
                    text=f"Tessl Manifest:\n{manifest_text}",
                    source=source,
                    status=SpecStatus.ACTIVE,
                    tags=["tessl", "manifest"],
                    links=dependencies,
                    pinned=True,
                )
            )

        except Exception as e:
            logger.warning(f"Failed to parse Tessl manifest {file_path}: {e}")

        return blocks

    def _extract_frontmatter(self, content: str) -> tuple[dict[str, Any] | None, str]:
        """Extract YAML frontmatter and content from a file."""
        if not content.startswith("---"):
            return None, content

        try:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                spec_text = parts[2].strip()
                return metadata, spec_text
        except Exception as e:
            logger.debug(f"Failed to parse YAML frontmatter: {e}")

        return None, content

    def _extract_dependencies(self, content: str) -> list[str]:
        """Extract dependency references from specification content."""
        dependencies: list[str] = []

        # Common dependency patterns
        patterns = [
            r"depends\s+on:\s*([^\n]+)",
            r"requires:\s*([^\n]+)",
            r"@depends\(([^)]+)\)",
            r'import\s+.*\s+from\s+["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Split comma-separated values
                deps = [d.strip() for d in match.split(",")]
                dependencies.extend(deps)

        return list(set(dependencies))  # Remove duplicates

    def _extract_jsdoc_specs(self, content: str) -> str:
        """Extract specification text from JSDoc comments."""
        jsdoc_pattern = r"/\*\*(.*?)\*/"
        matches = re.findall(jsdoc_pattern, content, re.DOTALL)

        specs: list[str] = []
        for match in matches:
            lines = match.split("\n")
            cleaned_lines: list[str] = []
            for line in lines:
                line = line.strip()
                if line.startswith("*"):
                    line = line[1:].strip()
                # Skip JSDoc tags like @param, @returns
                if line and not line.startswith("@"):
                    cleaned_lines.append(line)
            if cleaned_lines:
                specs.append("\n".join(cleaned_lines))

        return "\n\n".join(specs)

    def _extract_test_cases(self, content: str) -> list[str]:
        """Extract test case names from executable specification."""
        test_cases: list[str] = []

        # Common test patterns
        patterns = [
            r'test\(["\']([^"\']+)["\']',
            r'it\(["\']([^"\']+)["\']',
            r'describe\(["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            test_cases.extend(matches)

        return test_cases

    def _format_config_as_text(self, config_data: dict[str, Any]) -> str:
        """Format configuration data as readable text."""
        lines: list[str] = []
        for key, value in config_data.items():
            if isinstance(value, dict):
                lines.append(f"\n{key}:")
                for subkey, subvalue in value.items():
                    lines.append(f"  - {subkey}: {subvalue}")
            elif isinstance(value, list):
                lines.append(f"\n{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    def _format_manifest_as_text(self, manifest_data: dict[str, Any]) -> str:
        """Format manifest data as readable text."""
        lines: list[str] = []

        # Extract key manifest fields
        if "name" in manifest_data:
            lines.append(f"Name: {manifest_data['name']}")
        if "version" in manifest_data:
            lines.append(f"Version: {manifest_data['version']}")
        if "description" in manifest_data:
            lines.append(f"Description: {manifest_data['description']}")

        # Add dependencies
        if "dependencies" in manifest_data:
            deps = manifest_data["dependencies"]
            if isinstance(deps, dict):
                lines.append("\nDependencies:")
                for dep, version in deps.items():
                    lines.append(f"  - {dep}: {version}")
            elif isinstance(deps, list):
                lines.append("\nDependencies:")
                for dep in deps:
                    lines.append(f"  - {dep}")

        return "\n".join(lines)
