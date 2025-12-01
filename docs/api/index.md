# 🐍 Python API

SpecMem provides a comprehensive Python API for programmatic access.

## Installation

```bash
pip install specmem
```

## Quick Start

```python
from specmem import SpecMemClient

# Initialize client
sm = SpecMemClient()

# Query specifications
results = sm.query("authentication")

# Get context for changes
bundle = sm.get_context_for_change(["auth/service.py"])

# Analyze impact
impacted = sm.get_impacted_specs(["auth/service.py"])

# Validate specs
issues = sm.validate()
```

## Core Classes

<div class="feature-grid">
  <div class="feature-card">
    <h3><span class="emoji">🔌</span> SpecMemClient</h3>
    <p>Main entry point for all SpecMem operations.</p>
    <a href="client/" class="md-button">Reference →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🧠</span> Memory Bank</h3>
    <p>Vector-based specification storage and retrieval.</p>
    <a href="memory-bank/" class="md-button">Reference →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🗄️</span> Vector Stores</h3>
    <p>Backend storage implementations.</p>
    <a href="vectordb/" class="md-button">Reference →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🔌</span> Adapters</h3>
    <p>Framework-specific spec parsers.</p>
    <a href="adapters/" class="md-button">Reference →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">📊</span> Impact Graph</h3>
    <p>Relationship tracking and analysis.</p>
    <a href="impact-graph/" class="md-button">Reference →</a>
  </div>
</div>

## Data Classes

### SpecBlock

```python
from specmem.core import SpecBlock, SpecType, Lifecycle, Priority

spec = SpecBlock(
    id="auth-001",
    path="auth/requirements.md",
    framework="kiro",
    spec_type=SpecType.REQUIREMENT,
    title="User Authentication",
    content="...",
    summary="JWT-based authentication",
    tags=["auth", "security"],
    lifecycle=Lifecycle.ACTIVE,
    priority=Priority.CRITICAL,
)
```

### ContextBundle

```python
from specmem.client import ContextBundle

bundle = sm.get_context_for_change(["auth/service.py"])

print(bundle.tldr)              # Brief summary
print(bundle.specs)             # Relevant specs
print(bundle.pinned)            # Pinned specs
print(bundle.impacted)          # Impacted specs
print(bundle.recommended_tests) # Tests to run
print(bundle.warnings)          # Validation warnings
```

### QueryResult

```python
from specmem.client import QueryResult

results = sm.query("authentication", top_k=5)

for result in results:
    print(result.spec)      # SpecBlock
    print(result.score)     # Similarity score (0-1)
    print(result.highlights) # Matching text highlights
```

## Async Support

```python
import asyncio
from specmem import AsyncSpecMemClient

async def main():
    sm = AsyncSpecMemClient()

    results = await sm.query("authentication")
    bundle = await sm.get_context_for_change(["auth/service.py"])

asyncio.run(main())
```

## Type Hints

SpecMem is fully typed. Enable type checking in your IDE:

```python
from specmem import SpecMemClient
from specmem.core import SpecBlock

sm: SpecMemClient = SpecMemClient()
specs: list[SpecBlock] = sm.get_all_specs()
```
