# Testing

Guidelines for writing and running tests in SpecMem.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests
│   ├── test_client.py
│   ├── test_memory.py
│   └── ...
├── integration/         # Integration tests
│   ├── test_cli.py
│   └── ...
└── property/            # Property-based tests
    ├── test_memory_props.py
    └── ...
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Property tests
pytest tests/property/ -v

# Specific file
pytest tests/unit/test_client.py -v

# Specific test
pytest tests/unit/test_client.py::test_query -v

# With coverage
pytest tests/ --cov=specmem --cov-report=html

# Parallel execution
pytest tests/ -n auto
```

## Unit Tests

Test individual functions and classes in isolation.

```python
# tests/unit/test_memory.py
import pytest
from specmem.core import MemoryBank, SpecBlock, SpecType

class TestMemoryBank:
    """Tests for MemoryBank class."""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create a test memory bank."""
        return MemoryBank(path=tmp_path / "test.db")

    @pytest.fixture
    def sample_spec(self):
        """Create a sample spec."""
        return SpecBlock(
            id="test-001",
            path="test/spec.md",
            framework="test",
            spec_type=SpecType.REQUIREMENT,
            title="Test Spec",
            content="Test content",
            summary="Test summary",
        )

    def test_add_spec(self, memory, sample_spec):
        """Test adding a spec to memory."""
        spec_id = memory.add(sample_spec)

        assert spec_id == "test-001"
        assert memory.count() == 1

    def test_get_spec(self, memory, sample_spec):
        """Test retrieving a spec."""
        memory.add(sample_spec)

        result = memory.get("test-001")

        assert result is not None
        assert result.title == "Test Spec"

    def test_get_nonexistent(self, memory):
        """Test getting a spec that doesn't exist."""
        result = memory.get("nonexistent")

        assert result is None

    def test_search(self, memory, sample_spec):
        """Test searching specs."""
        memory.add(sample_spec)

        results = memory.search("test", top_k=5)

        assert len(results) >= 1
        assert results[0].spec.id == "test-001"
```

## Integration Tests

Test components working together.

```python
# tests/integration/test_cli.py
import subprocess
import pytest

class TestCLI:
    """Integration tests for CLI."""

    def test_init(self, tmp_path):
        """Test specmem init command."""
        result = subprocess.run(
            ["specmem", "init"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert (tmp_path / ".specmem.toml").exists()

    def test_scan(self, project_with_specs):
        """Test specmem scan command."""
        result = subprocess.run(
            ["specmem", "scan"],
            cwd=project_with_specs,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "specifications indexed" in result.stdout
```

## Property-Based Tests

Use Hypothesis for property-based testing.

```python
# tests/property/test_memory_props.py
import pytest
from hypothesis import given, strategies as st
from specmem.core import MemoryBank, SpecBlock, SpecType

class TestMemoryProperties:
    """Property-based tests for MemoryBank."""

    @given(st.text(min_size=1, max_size=100))
    def test_add_then_get_roundtrip(self, memory, title):
        """Property: Adding then getting returns same spec."""
        spec = SpecBlock(
            id=f"prop-{hash(title)}",
            path="test.md",
            framework="test",
            spec_type=SpecType.REQUIREMENT,
            title=title,
            content="content",
            summary="summary",
        )

        memory.add(spec)
        result = memory.get(spec.id)

        assert result is not None
        assert result.title == title

    @given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
    def test_count_equals_added(self, memory, titles):
        """Property: Count equals number of specs added."""
        for i, title in enumerate(titles):
            spec = SpecBlock(
                id=f"prop-{i}",
                path="test.md",
                framework="test",
                spec_type=SpecType.REQUIREMENT,
                title=title,
                content="content",
                summary="summary",
            )
            memory.add(spec)

        assert memory.count() == len(titles)

    @given(st.text(min_size=1))
    def test_delete_removes_spec(self, memory, title):
        """Property: Delete removes the spec."""
        spec = SpecBlock(
            id="to-delete",
            path="test.md",
            framework="test",
            spec_type=SpecType.REQUIREMENT,
            title=title,
            content="content",
            summary="summary",
        )

        memory.add(spec)
        memory.delete(spec.id)

        assert memory.get(spec.id) is None
```

## Fixtures

Shared fixtures in `conftest.py`:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from specmem.core import MemoryBank
from specmem.vectordb import LanceDBStore
from specmem.vectordb.embeddings import LocalEmbeddingProvider

@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test.db"

@pytest.fixture
def embeddings():
    """Create test embeddings provider."""
    return LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")

@pytest.fixture
def vectordb(tmp_db):
    """Create test vector store."""
    return LanceDBStore(db_path=str(tmp_db))

@pytest.fixture
def memory(vectordb, embeddings):
    """Create test memory bank."""
    return MemoryBank(vector_store=vectordb, embedding_provider=embeddings)

@pytest.fixture
def project_with_specs(tmp_path):
    """Create a project with sample specs."""
    # Create .kiro/specs structure
    specs_dir = tmp_path / ".kiro" / "specs" / "auth"
    specs_dir.mkdir(parents=True)

    (specs_dir / "requirements.md").write_text("""
# Requirements

## Requirement 1
**User Story:** As a user, I want to log in.
""")

    return tmp_path
```

## Markers

Use markers to categorize tests:

```python
@pytest.mark.slow
def test_large_dataset():
    """Test with large dataset (slow)."""
    ...

@pytest.mark.integration
def test_full_workflow():
    """Integration test."""
    ...

@pytest.mark.property
def test_roundtrip_property():
    """Property-based test."""
    ...
```

Run specific markers:

```bash
# Skip slow tests
pytest tests/ -m "not slow"

# Only integration tests
pytest tests/ -m integration
```

## Coverage

Maintain >70% code coverage:

```bash
# Generate coverage report
pytest tests/ --cov=specmem --cov-report=html

# View report
open htmlcov/index.html
```

## Best Practices

1. **One assertion per test** (when practical)
2. **Descriptive test names** - `test_<what>_<condition>_<expected>`
3. **Use fixtures** for setup/teardown
4. **Test edge cases** - empty inputs, None, boundaries
5. **Property tests** for invariants
6. **Mock external services** - APIs, databases
