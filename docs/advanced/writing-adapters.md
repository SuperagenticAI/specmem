# ✍️ Writing Adapters

Create custom adapters to parse specifications from any framework.

## Overview

Adapters convert framework-specific specification formats into SpecMem's canonical SpecIR format.

## Basic Adapter

```python
from pathlib import Path
from specmem.adapters.base import SpecAdapter
from specmem.core import SpecBlock, SpecType, Lifecycle, Priority
from datetime import datetime

class MyFrameworkAdapter(SpecAdapter):
    """Adapter for MyFramework specifications."""

    name = "myframework"

    def can_parse(self, path: Path) -> bool:
        """Check if this adapter can parse the given path."""
        # Check file extension
        if path.suffix == ".myspec":
            return True
        # Check directory structure
        if path.is_dir() and (path / "specs").exists():
            return True
        return False

    def parse(self, path: Path) -> list[SpecBlock]:
        """Parse a single specification file."""
        content = path.read_text()

        # Parse your format here
        title = self._extract_title(content)
        summary = self._extract_summary(content)
        spec_type = self._determine_type(path)

        return [SpecBlock(
            id=self._generate_id(path),
            path=str(path),
            framework=self.name,
            spec_type=spec_type,
            title=title,
            content=content,
            summary=summary,
            tags=self._extract_tags(content),
            lifecycle=Lifecycle.ACTIVE,
            priority=self._determine_priority(content),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={},
        )]

    def parse_directory(self, directory: Path) -> list[SpecBlock]:
        """Parse all specifications in a directory."""
        specs = []
        for path in directory.rglob("*.myspec"):
            try:
                specs.extend(self.parse(path))
            except Exception as e:
                print(f"Error parsing {path}: {e}")
        return specs

    # Helper methods
    def _generate_id(self, path: Path) -> str:
        return f"{self.name}-{path.stem}"

    def _extract_title(self, content: str) -> str:
        # Extract title from content
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Untitled"

    def _extract_summary(self, content: str) -> str:
        # First 200 chars as summary
        return content[:200].replace("\n", " ").strip()

    def _extract_tags(self, content: str) -> list[str]:
        # Extract tags from content
        tags = []
        if "authentication" in content.lower():
            tags.append("auth")
        if "security" in content.lower():
            tags.append("security")
        return tags

    def _determine_type(self, path: Path) -> SpecType:
        if "requirements" in path.stem:
            return SpecType.REQUIREMENT
        elif "design" in path.stem:
            return SpecType.DESIGN
        elif "task" in path.stem:
            return SpecType.TASK
        return SpecType.REQUIREMENT

    def _determine_priority(self, content: str) -> Priority:
        if "critical" in content.lower():
            return Priority.CRITICAL
        elif "high" in content.lower():
            return Priority.HIGH
        return Priority.MEDIUM
```

## Registering Your Adapter

```python
from specmem.adapters import register_adapter

# Register the adapter
register_adapter(MyFrameworkAdapter())
```

Or in your package's `__init__.py`:

```python
# mypackage/__init__.py
from specmem.adapters import register_adapter
from .adapter import MyFrameworkAdapter

register_adapter(MyFrameworkAdapter())
```

## Configuration

Enable your adapter in `.specmem.toml`:

```toml
[adapters]
myframework = true

[adapters.myframework]
# Custom configuration
spec_dir = ".myframework/specs"
file_pattern = "*.myspec"
```

Access configuration in your adapter:

```python
class MyFrameworkAdapter(SpecAdapter):
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.spec_dir = self.config.get("spec_dir", ".myframework/specs")
        self.file_pattern = self.config.get("file_pattern", "*.myspec")
```

## Parsing Utilities

SpecMem provides utilities for common parsing tasks:

### Markdown Parsing

```python
from specmem.adapters.utils import (
    parse_markdown_spec,
    extract_sections,
    extract_frontmatter,
)

# Parse markdown into sections
sections = parse_markdown_spec(content)
# {"title": "...", "sections": [...]}

# Extract specific sections
sections = extract_sections(content, ["Requirements", "Design"])

# Parse YAML frontmatter
frontmatter, body = extract_frontmatter(content)
```

### EARS Pattern Extraction

```python
from specmem.adapters.utils import extract_ears_requirements

content = """
WHEN a user logs in THEN the system SHALL authenticate
IF invalid credentials THEN the system SHALL reject
"""

requirements = extract_ears_requirements(content)
# [{"pattern": "event_driven", "trigger": "user logs in", ...}]
```

### Code Reference Extraction

```python
from specmem.adapters.utils import extract_code_references

content = """
This spec is implemented in `src/auth/service.py`.
See also: `src/auth/models.py`
"""

refs = extract_code_references(content)
# ["src/auth/service.py", "src/auth/models.py"]
```

## Testing Your Adapter

```python
import pytest
from pathlib import Path
from mypackage import MyFrameworkAdapter

@pytest.fixture
def adapter():
    return MyFrameworkAdapter()

@pytest.fixture
def sample_spec(tmp_path):
    spec_file = tmp_path / "test.myspec"
    spec_file.write_text("""
# Test Specification

This is a test spec for authentication.

## Requirements
- User can log in
- User can log out
""")
    return spec_file

def test_can_parse(adapter, sample_spec):
    assert adapter.can_parse(sample_spec)
    assert not adapter.can_parse(Path("test.md"))

def test_parse(adapter, sample_spec):
    specs = adapter.parse(sample_spec)

    assert len(specs) == 1
    assert specs[0].framework == "myframework"
    assert specs[0].title == "Test Specification"
    assert "auth" in specs[0].tags

def test_parse_directory(adapter, tmp_path):
    # Create multiple specs
    (tmp_path / "spec1.myspec").write_text("# Spec 1")
    (tmp_path / "spec2.myspec").write_text("# Spec 2")

    specs = adapter.parse_directory(tmp_path)
    assert len(specs) == 2
```

## Best Practices

1. **Handle errors gracefully** - Don't crash on malformed specs
2. **Generate stable IDs** - IDs should be deterministic
3. **Extract meaningful metadata** - Tags, priority, lifecycle
4. **Support incremental parsing** - Check file modification times
5. **Document your format** - Help users write valid specs

## Publishing Your Adapter

Create a Python package:

```
myframework-specmem/
├── pyproject.toml
├── README.md
└── myframework_specmem/
    ├── __init__.py
    └── adapter.py
```

```toml
# pyproject.toml
[project]
name = "myframework-specmem"
dependencies = ["specmem>=0.1.0"]

[project.entry-points."specmem.adapters"]
myframework = "myframework_specmem:MyFrameworkAdapter"
```

Users can then install:

```bash
pip install myframework-specmem
```
