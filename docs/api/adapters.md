# Adapters

Adapters parse specifications from various AI coding agent frameworks.

## Base Interface

All adapters implement the `SpecAdapter` protocol:

```python
from specmem.adapters.base import SpecAdapter

class SpecAdapter(Protocol):
    name: str

    def can_parse(self, path: Path) -> bool: ...
    def parse(self, path: Path) -> list[SpecBlock]: ...
    def parse_directory(self, directory: Path) -> list[SpecBlock]: ...
```

## Built-in Adapters

### Kiro Adapter

```python
from specmem.adapters import KiroAdapter

adapter = KiroAdapter()

# Check if can parse
if adapter.can_parse(Path(".kiro/specs/auth/requirements.md")):
    specs = adapter.parse(Path(".kiro/specs/auth/requirements.md"))

# Parse entire directory
specs = adapter.parse_directory(Path(".kiro/specs"))
```

### Cursor Adapter

```python
from specmem.adapters import CursorAdapter

adapter = CursorAdapter()

# Parse cursor.json
specs = adapter.parse(Path("cursor.json"))

# Parse .cursorrules
specs = adapter.parse(Path(".cursorrules"))
```

### Claude Adapter

```python
from specmem.adapters import ClaudeAdapter

adapter = ClaudeAdapter()

# Parse Claude.md
specs = adapter.parse(Path("Claude.md"))
```

### SpecKit Adapter

```python
from specmem.adapters import SpecKitAdapter

adapter = SpecKitAdapter()

# Parse YAML specs
specs = adapter.parse_directory(Path(".speckit"))
```

### Tessl Adapter

```python
from specmem.adapters import TesslAdapter

adapter = TesslAdapter()

# Parse Tessl specs
specs = adapter.parse_directory(Path(".tessl/specs"))
```

## Adapter Registry

Use the registry to get adapters:

```python
from specmem.adapters import get_adapter, get_all_adapters

# Get specific adapter
kiro = get_adapter("kiro")

# Get all enabled adapters
adapters = get_all_adapters()
```

## Creating Custom Adapters

### Basic Adapter

```python
from pathlib import Path
from specmem.adapters.base import SpecAdapter
from specmem.core import SpecBlock, SpecType, Lifecycle, Priority

class MyAdapter(SpecAdapter):
    name = "myadapter"

    def can_parse(self, path: Path) -> bool:
        """Check if this adapter can parse the given path."""
        return path.suffix == ".myspec"

    def parse(self, path: Path) -> list[SpecBlock]:
        """Parse a single file."""
        content = path.read_text()

        return [SpecBlock(
            id=f"my-{path.stem}",
            path=str(path),
            framework=self.name,
            spec_type=SpecType.REQUIREMENT,
            title=path.stem,
            content=content,
            summary=content[:100],
            tags=[],
            lifecycle=Lifecycle.ACTIVE,
            priority=Priority.MEDIUM,
        )]

    def parse_directory(self, directory: Path) -> list[SpecBlock]:
        """Parse all files in a directory."""
        specs = []
        for path in directory.rglob("*.myspec"):
            specs.extend(self.parse(path))
        return specs
```

### Register Custom Adapter

```python
from specmem.adapters import register_adapter

register_adapter(MyAdapter())
```

### Configuration

Enable in `.specmem.toml`:

```toml
[adapters]
myadapter = true

[adapters.myadapter]
# Custom settings
file_pattern = "*.myspec"
```

## Adapter Utilities

### Parse Markdown

```python
from specmem.adapters.utils import parse_markdown_spec

content = """
# Requirements

## Requirement 1
**User Story:** As a user, I want to log in.

### Acceptance Criteria
1. Valid credentials grant access
2. Invalid credentials show error
"""

sections = parse_markdown_spec(content)
# Returns structured sections
```

### Parse YAML Frontmatter

```python
from specmem.adapters.utils import parse_frontmatter

content = """
---
title: Authentication
priority: critical
tags: [auth, security]
---

# Content here
"""

frontmatter, body = parse_frontmatter(content)
# frontmatter = {"title": "Authentication", "priority": "critical", ...}
# body = "# Content here"
```

### Extract Requirements

```python
from specmem.adapters.utils import extract_requirements

content = """
WHEN a user logs in THEN the system SHALL authenticate
WHEN invalid credentials THEN the system SHALL reject
"""

requirements = extract_requirements(content)
# Returns list of EARS-formatted requirements
```

## Testing Adapters

```python
import pytest
from specmem.adapters import MyAdapter

def test_can_parse():
    adapter = MyAdapter()
    assert adapter.can_parse(Path("test.myspec"))
    assert not adapter.can_parse(Path("test.md"))

def test_parse():
    adapter = MyAdapter()
    specs = adapter.parse(Path("fixtures/test.myspec"))

    assert len(specs) == 1
    assert specs[0].framework == "myadapter"
```
