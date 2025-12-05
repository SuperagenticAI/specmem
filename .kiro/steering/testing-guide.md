---
inclusion: fileMatch
fileMatchPattern: "tests/**/*.py"
---

# Testing Guide for SpecMem

## Property-Based Testing

Use `hypothesis` for property-based tests. Each property should:
1. Reference a correctness property from the design doc
2. Use the format: `**Feature: {feature}, Property {n}: {description}**`

### Example

```python
from hypothesis import given, strategies as st

class TestMyFeatureProps:
    """Property tests for MyFeature.
    
    **Feature: my-feature, Property 1: Round-trip consistency**
    **Validates: Requirements 1.2**
    """

    @given(st.text(min_size=1))
    def test_round_trip(self, value: str) -> None:
        """Encoding then decoding returns original value."""
        encoded = encode(value)
        decoded = decode(encoded)
        assert decoded == value
```

## Common Property Patterns

1. **Round-trip**: `decode(encode(x)) == x`
2. **Invariants**: Properties preserved after operations
3. **Idempotence**: `f(f(x)) == f(x)`
4. **Metamorphic**: Known relationships between inputs/outputs

## Running Tests

```bash
# All tests
pytest tests/

# Property tests only
pytest tests/property/ -m property

# With coverage
pytest --cov=specmem tests/
```

## Test Organization

- `tests/property/` - Property-based tests
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests (if any)
