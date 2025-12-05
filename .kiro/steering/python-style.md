---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Python Code Style for SpecMem

## Formatting

- Use `ruff` for linting and formatting
- Line length: 100 characters
- Use type hints for all function signatures
- Use docstrings (Google style)

## Imports

```python
from __future__ import annotations

import stdlib_module
from typing import TYPE_CHECKING

import third_party

from specmem.module import Class


if TYPE_CHECKING:
    from specmem.other import OtherClass
```

## Classes

```python
class MyClass:
    """Brief description.

    Longer description if needed.

    Attributes:
        attr: Description of attribute
    """

    def __init__(self, param: str) -> None:
        """Initialize the class.

        Args:
            param: Description of parameter
        """
        self.attr = param

    def method(self, arg: int) -> str:
        """Brief description.

        Args:
            arg: Description

        Returns:
            Description of return value

        Raises:
            ValueError: When arg is invalid
        """
        return str(arg)
```

## Testing

- Property tests: `tests/property/test_*_props.py`
- Unit tests: `tests/unit/test_*.py`
- Use `hypothesis` for property-based testing
- Use `pytest` fixtures for setup
