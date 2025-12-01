"""Test Mapping Engine for SpecMem.

Maps specifications to tests and provides test suggestions for code changes.
"""

import logging
import re
from pathlib import Path

from specmem.core import SpecBlock, TestMapping
from specmem.testing.frameworks import (
    TestFramework,
    detect_frameworks,
    get_test_file_pattern,
)


logger = logging.getLogger(__name__)


class TestMappingEngine:
    """Engine for mapping specs to tests and vice versa.

    Provides framework-agnostic test mapping capabilities.
    """

    def __init__(self, workspace_path: Path | str) -> None:
        """Initialize the test mapping engine.

        Args:
            workspace_path: Path to the workspace root
        """
        self.workspace_path = Path(workspace_path).resolve()
        self._frameworks: list[TestFramework] | None = None
        self._test_files: dict[TestFramework, list[Path]] | None = None

    @property
    def frameworks(self) -> list[TestFramework]:
        """Get detected test frameworks."""
        if self._frameworks is None:
            self._frameworks = detect_frameworks(self.workspace_path)
        return self._frameworks

    def get_tests_for_files(
        self,
        changed_files: list[str],
        max_results: int = 50,
    ) -> list[TestMapping]:
        """Get tests related to changed files.

        Args:
            changed_files: List of changed file paths
            max_results: Maximum number of results

        Returns:
            List of TestMapping objects ordered by confidence
        """
        if not changed_files:
            return []

        mappings: list[TestMapping] = []

        for file_path in changed_files:
            file_mappings = self._find_tests_for_file(file_path)
            mappings.extend(file_mappings)

        # Deduplicate by (framework, path, selector)
        seen: set[tuple[str, str, str]] = set()
        unique_mappings: list[TestMapping] = []
        for m in mappings:
            key = (m.framework, m.path, m.selector)
            if key not in seen:
                seen.add(key)
                unique_mappings.append(m)

        # Sort by confidence descending
        unique_mappings.sort(key=lambda m: m.confidence, reverse=True)

        return unique_mappings[:max_results]

    def get_tests_for_spec(self, spec: SpecBlock) -> list[TestMapping]:
        """Get tests mapped to a specific spec.

        Args:
            spec: SpecBlock to get tests for

        Returns:
            List of TestMapping objects
        """
        return spec.get_test_mappings()

    def parse_test_file(
        self,
        path: Path,
        framework: TestFramework | None = None,
    ) -> list[TestMapping]:
        """Parse a test file and extract test mappings.

        Args:
            path: Path to the test file
            framework: Optional framework (auto-detected if not provided)

        Returns:
            List of TestMapping objects
        """
        if not path.exists():
            return []

        # Auto-detect framework if not provided
        if framework is None:
            framework = self._detect_file_framework(path)

        content = path.read_text()
        rel_path = str(path.relative_to(self.workspace_path))

        if framework == TestFramework.PYTEST:
            return self._parse_pytest_file(content, rel_path)
        elif framework in (TestFramework.JEST, TestFramework.VITEST):
            return self._parse_jest_file(content, rel_path, framework.value)
        elif framework == TestFramework.PLAYWRIGHT:
            return self._parse_playwright_file(content, rel_path)
        elif framework == TestFramework.MOCHA:
            return self._parse_mocha_file(content, rel_path)
        else:
            return self._parse_generic_file(content, rel_path)

    def _find_tests_for_file(self, file_path: str) -> list[TestMapping]:
        """Find tests related to a source file."""
        mappings: list[TestMapping] = []
        path = Path(file_path)

        # Get the base name without extension
        stem = path.stem

        # Look for test files with matching names
        for framework in self.frameworks:
            test_files = self._get_test_files(framework)

            for test_file in test_files:
                # Check if test file name relates to source file
                test_stem = test_file.stem

                # Common patterns: test_foo.py for foo.py, foo.test.ts for foo.ts
                confidence = 0.0

                if test_stem in (f"test_{stem}", f"{stem}_test") or test_stem in (
                    f"{stem}.test",
                    f"{stem}.spec",
                ):
                    confidence = 0.9
                elif stem in test_stem:
                    confidence = 0.6
                elif test_stem in stem:
                    confidence = 0.5

                if confidence > 0:
                    # Parse the test file to get individual tests
                    file_mappings = self.parse_test_file(test_file, framework)
                    for m in file_mappings:
                        # Adjust confidence based on file match
                        m.confidence = min(m.confidence * confidence, 1.0)
                    mappings.extend(file_mappings)

        return mappings

    def _get_test_files(self, framework: TestFramework) -> list[Path]:
        """Get all test files for a framework."""
        if self._test_files is None:
            self._test_files = {}

        if framework not in self._test_files:
            patterns = get_test_file_pattern(framework)
            files: list[Path] = []

            for pattern in patterns:
                files.extend(self.workspace_path.glob(pattern))

            # Deduplicate
            self._test_files[framework] = list(set(files))

        return self._test_files[framework]

    def _detect_file_framework(self, path: Path) -> TestFramework:
        """Detect framework for a specific file."""
        name = path.name
        suffix = path.suffix

        if suffix == ".py":
            return TestFramework.PYTEST
        elif suffix in (".ts", ".tsx", ".js", ".jsx"):
            # Check for playwright patterns
            if ".spec." in name or "e2e" in str(path):
                if TestFramework.PLAYWRIGHT in self.frameworks:
                    return TestFramework.PLAYWRIGHT

            # Check for vitest vs jest
            if TestFramework.VITEST in self.frameworks:
                return TestFramework.VITEST
            elif TestFramework.JEST in self.frameworks:
                return TestFramework.JEST

            return TestFramework.JEST  # Default for JS/TS

        return TestFramework.UNKNOWN

    def _parse_pytest_file(self, content: str, path: str) -> list[TestMapping]:
        """Parse pytest test file."""
        mappings: list[TestMapping] = []

        # Find test functions
        func_pattern = r"^def\s+(test_\w+)\s*\("
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            selector = f"{path}::{func_name}"
            mappings.append(
                TestMapping(
                    framework="pytest",
                    path=path,
                    selector=selector,
                    confidence=1.0,
                )
            )

        # Find test classes and methods
        class_pattern = r"^class\s+(Test\w+)\s*[:\(]"
        method_pattern = r"^\s+def\s+(test_\w+)\s*\("

        current_class = None
        for line in content.split("\n"):
            class_match = re.match(class_pattern, line)
            if class_match:
                current_class = class_match.group(1)
                continue

            if current_class:
                method_match = re.match(method_pattern, line)
                if method_match:
                    method_name = method_match.group(1)
                    selector = f"{path}::{current_class}::{method_name}"
                    mappings.append(
                        TestMapping(
                            framework="pytest",
                            path=path,
                            selector=selector,
                            confidence=1.0,
                        )
                    )

        return mappings

    def _parse_jest_file(
        self,
        content: str,
        path: str,
        framework: str = "jest",
    ) -> list[TestMapping]:
        """Parse jest/vitest test file."""
        mappings: list[TestMapping] = []

        # Find describe blocks
        describe_pattern = r"describe\s*\(\s*['\"]([^'\"]+)['\"]"
        test_pattern = r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]"

        describes = re.findall(describe_pattern, content)
        tests = re.findall(test_pattern, content)

        # Add describe-level tests
        for describe in describes:
            selector = f"{describe}"
            mappings.append(
                TestMapping(
                    framework=framework,
                    path=path,
                    selector=selector,
                    confidence=0.8,
                )
            )

        # Add individual tests
        for test in tests:
            selector = test
            mappings.append(
                TestMapping(
                    framework=framework,
                    path=path,
                    selector=selector,
                    confidence=1.0,
                )
            )

        return mappings

    def _parse_playwright_file(self, content: str, path: str) -> list[TestMapping]:
        """Parse playwright test file."""
        mappings: list[TestMapping] = []

        # Find test blocks
        test_pattern = r"test\s*\(\s*['\"]([^'\"]+)['\"]"
        describe_pattern = r"test\.describe\s*\(\s*['\"]([^'\"]+)['\"]"

        describes = re.findall(describe_pattern, content)
        tests = re.findall(test_pattern, content)

        for describe in describes:
            mappings.append(
                TestMapping(
                    framework="playwright",
                    path=path,
                    selector=describe,
                    confidence=0.8,
                )
            )

        for test in tests:
            mappings.append(
                TestMapping(
                    framework="playwright",
                    path=path,
                    selector=test,
                    confidence=1.0,
                )
            )

        return mappings

    def _parse_mocha_file(self, content: str, path: str) -> list[TestMapping]:
        """Parse mocha test file."""
        return self._parse_jest_file(content, path, "mocha")

    def _parse_generic_file(self, content: str, path: str) -> list[TestMapping]:
        """Parse generic test file."""
        mappings: list[TestMapping] = []

        # Look for common test patterns
        patterns = [
            r"def\s+(test_\w+)",
            r"(?:it|test)\s*\(\s*['\"]([^'\"]+)['\"]",
            r"@Test\s+.*?void\s+(\w+)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                selector = match.group(1)
                mappings.append(
                    TestMapping(
                        framework="unknown",
                        path=path,
                        selector=selector,
                        confidence=0.5,
                    )
                )

        return mappings
