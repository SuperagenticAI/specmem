"""Test framework detection and patterns.

Provides framework-agnostic test detection for pytest, jest, vitest,
playwright, mocha, and other test frameworks.
"""

import logging
from enum import Enum
from pathlib import Path


logger = logging.getLogger(__name__)


class TestFramework(str, Enum):
    """Supported test frameworks."""

    PYTEST = "pytest"
    JEST = "jest"
    VITEST = "vitest"
    PLAYWRIGHT = "playwright"
    MOCHA = "mocha"
    UNKNOWN = "unknown"


# File patterns for each framework
FRAMEWORK_PATTERNS: dict[TestFramework, list[str]] = {
    TestFramework.PYTEST: [
        "test_*.py",
        "*_test.py",
        "tests/**/*.py",
        "test/**/*.py",
    ],
    TestFramework.JEST: [
        "*.test.js",
        "*.test.ts",
        "*.test.jsx",
        "*.test.tsx",
        "*.spec.js",
        "*.spec.ts",
        "__tests__/**/*.js",
        "__tests__/**/*.ts",
    ],
    TestFramework.VITEST: [
        "*.test.ts",
        "*.test.tsx",
        "*.spec.ts",
        "*.spec.tsx",
    ],
    TestFramework.PLAYWRIGHT: [
        "*.spec.ts",
        "*.spec.js",
        "e2e/**/*.ts",
        "e2e/**/*.js",
        "tests/**/*.spec.ts",
    ],
    TestFramework.MOCHA: [
        "test/**/*.js",
        "test/**/*.ts",
        "*.test.js",
        "spec/**/*.js",
    ],
}

# Config files that indicate framework usage
FRAMEWORK_CONFIG_FILES: dict[TestFramework, list[str]] = {
    TestFramework.PYTEST: ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"],
    TestFramework.JEST: ["jest.config.js", "jest.config.ts", "jest.config.json"],
    TestFramework.VITEST: ["vitest.config.ts", "vitest.config.js", "vite.config.ts"],
    TestFramework.PLAYWRIGHT: ["playwright.config.ts", "playwright.config.js"],
    TestFramework.MOCHA: [".mocharc.js", ".mocharc.json", ".mocharc.yaml"],
}


def detect_frameworks(workspace_path: Path) -> list[TestFramework]:
    """Detect test frameworks in a workspace.

    Args:
        workspace_path: Path to the workspace root

    Returns:
        List of detected TestFramework values
    """
    detected: set[TestFramework] = set()

    # Check for config files
    for framework, config_files in FRAMEWORK_CONFIG_FILES.items():
        for config_file in config_files:
            if (workspace_path / config_file).exists():
                detected.add(framework)
                logger.debug(f"Detected {framework.value} via config file: {config_file}")
                break

    # Check for test files matching patterns
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        if framework in detected:
            continue

        for pattern in patterns:
            # Convert glob pattern to check
            if "**" in pattern:
                matches = list(workspace_path.glob(pattern))
            else:
                matches = list(workspace_path.glob(pattern))

            if matches:
                detected.add(framework)
                logger.debug(f"Detected {framework.value} via file pattern: {pattern}")
                break

    # Check package.json for JS frameworks
    package_json = workspace_path / "package.json"
    if package_json.exists():
        try:
            import json

            data = json.loads(package_json.read_text())
            deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
            }

            if "jest" in deps:
                detected.add(TestFramework.JEST)
            if "vitest" in deps:
                detected.add(TestFramework.VITEST)
            if "@playwright/test" in deps or "playwright" in deps:
                detected.add(TestFramework.PLAYWRIGHT)
            if "mocha" in deps:
                detected.add(TestFramework.MOCHA)
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")

    # Check pyproject.toml for pytest
    pyproject = workspace_path / "pyproject.toml"
    if pyproject.exists() and TestFramework.PYTEST not in detected:
        try:
            content = pyproject.read_text()
            if "[tool.pytest" in content or "pytest" in content.lower():
                detected.add(TestFramework.PYTEST)
        except Exception as e:
            logger.warning(f"Failed to parse pyproject.toml: {e}")

    result = sorted(detected, key=lambda f: f.value)
    logger.info(f"Detected frameworks: {[f.value for f in result]}")
    return result


def get_test_file_pattern(framework: TestFramework) -> list[str]:
    """Get file patterns for a framework.

    Args:
        framework: Test framework

    Returns:
        List of glob patterns for test files
    """
    return FRAMEWORK_PATTERNS.get(framework, [])


def is_test_file(path: Path, framework: TestFramework | None = None) -> bool:
    """Check if a file is a test file.

    Args:
        path: File path to check
        framework: Optional framework to check against

    Returns:
        True if the file matches test patterns
    """
    name = path.name

    if framework:
        patterns = FRAMEWORK_PATTERNS.get(framework, [])
    else:
        # Check all frameworks
        patterns = []
        for fw_patterns in FRAMEWORK_PATTERNS.values():
            patterns.extend(fw_patterns)

    for pattern in patterns:
        # Simple pattern matching
        if "**" in pattern:
            # Skip recursive patterns for single file check
            pattern = pattern.split("**/")[-1]

        if pattern.startswith("*"):
            suffix = pattern[1:]
            if name.endswith(suffix):
                return True
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            if name.startswith(prefix):
                return True
        elif name == pattern:
            return True

    return False
