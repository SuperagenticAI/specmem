# Code Style

Coding standards and conventions for SpecMem.

## Python Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

### Running Ruff

```bash
# Check for issues
ruff check .

# Fix automatically
ruff check . --fix

# Format code
ruff format .
```

### Key Rules

- Line length: 100 characters
- Indent: 4 spaces
- Quotes: Double quotes
- Imports: Sorted, grouped

### Example

```python
"""Module docstring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from specmem.core import SpecBlock

if TYPE_CHECKING:
    from specmem.vectordb import VectorStore


@dataclass
class MyClass:
    """Class docstring.

    Attributes:
        name: The name of the thing.
        value: The value of the thing.
    """

    name: str
    value: int

    def my_method(self, arg: str) -> str:
        """Method docstring.

        Args:
            arg: The argument.

        Returns:
            The result string.
        """
        return f"{self.name}: {arg}"


def my_function(
    param1: str,
    param2: int,
    *,
    optional: bool = False,
) -> dict[str, int]:
    """Function docstring.

    Args:
        param1: First parameter.
        param2: Second parameter.
        optional: Optional flag.

    Returns:
        A dictionary mapping strings to integers.

    Raises:
        ValueError: If param2 is negative.
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")

    return {param1: param2}
```

## Type Hints

All code must have type hints.

### Basic Types

```python
def process(name: str, count: int, enabled: bool) -> str:
    ...
```

### Collections

```python
def process(
    items: list[str],
    mapping: dict[str, int],
    options: set[str],
) -> tuple[str, int]:
    ...
```

### Optional and Union

```python
from typing import Optional, Union

def process(
    value: str | None,  # Preferred
    other: Optional[str],  # Also acceptable
) -> str | int:
    ...
```

### Generics

```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value
```

## Docstrings

Use Google-style docstrings.

### Module

```python
"""Module for handling specifications.

This module provides utilities for parsing and
validating specification files.

Example:
    >>> from specmem.core import parse_spec
    >>> spec = parse_spec("path/to/spec.md")
"""
```

### Class

```python
class SpecParser:
    """Parser for specification files.

    This class handles parsing of various specification
    formats into the canonical SpecIR format.

    Attributes:
        adapters: List of enabled adapters.
        config: Parser configuration.

    Example:
        >>> parser = SpecParser()
        >>> specs = parser.parse("path/to/specs")
    """
```

### Function

```python
def parse_spec(
    path: str,
    *,
    strict: bool = False,
) -> SpecBlock:
    """Parse a specification file.

    Args:
        path: Path to the specification file.
        strict: If True, raise on warnings.

    Returns:
        The parsed specification block.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ParseError: If the file is malformed.

    Example:
        >>> spec = parse_spec("auth/requirements.md")
        >>> print(spec.title)
        'User Authentication'
    """
```

## Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Module | snake_case | `memory_bank.py` |
| Class | PascalCase | `MemoryBank` |
| Function | snake_case | `get_specs()` |
| Variable | snake_case | `spec_count` |
| Constant | UPPER_SNAKE | `MAX_RETRIES` |
| Private | _prefix | `_internal_method()` |

## File Organization

```python
"""Module docstring."""

# Future imports
from __future__ import annotations

# Standard library
import json
from pathlib import Path

# Third-party
import numpy as np

# Local imports
from specmem.core import SpecBlock

# Type checking imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from specmem.vectordb import VectorStore

# Constants
MAX_RETRIES = 3

# Module-level code
logger = logging.getLogger(__name__)


# Classes
class MyClass:
    ...


# Functions
def my_function():
    ...


# Main block (if applicable)
if __name__ == "__main__":
    main()
```

## Error Handling

```python
# Use specific exceptions
class SpecMemError(Exception):
    """Base exception for SpecMem."""

class ParseError(SpecMemError):
    """Raised when parsing fails."""

class ValidationError(SpecMemError):
    """Raised when validation fails."""

# Raise with context
def parse(path: str) -> SpecBlock:
    try:
        content = Path(path).read_text()
    except FileNotFoundError as e:
        raise ParseError(f"Spec file not found: {path}") from e
```

## Testing Style

See [Testing](testing.md) for test conventions.
