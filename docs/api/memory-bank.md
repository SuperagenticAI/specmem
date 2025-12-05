# Memory Bank

The Memory Bank manages specification storage and retrieval using vector embeddings.

## Import

```python
from specmem.core import MemoryBank
```

## Constructor

```python
MemoryBank(
    vectordb: VectorStore,
    embedding_provider: EmbeddingProvider,
)
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `vectordb` | `VectorStore` | Vector database backend |
| `embedding_provider` | `EmbeddingProvider` | Embedding generator |

### Example

```python
from specmem.vectordb import LanceDBStore
from specmem.vectordb.embeddings import LocalEmbeddingProvider

vectordb = LanceDBStore(db_path=".specmem/vectordb")
embeddings = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")

memory = MemoryBank(vector_store=vectordb, embedding_provider=embeddings)
```

## Methods

### add

Add a specification to the memory bank.

```python
def add(spec: SpecBlock) -> str
```

#### Returns

The ID of the added specification.

#### Example

```python
spec = SpecBlock(
    id="auth-001",
    path="auth/requirements.md",
    framework="kiro",
    spec_type=SpecType.REQUIREMENT,
    title="User Authentication",
    content="...",
    summary="JWT-based auth",
)

spec_id = memory.add(spec)
```

---

### add_batch

Add multiple specifications efficiently.

```python
def add_batch(specs: list[SpecBlock]) -> list[str]
```

#### Example

```python
specs = [spec1, spec2, spec3]
ids = memory.add_batch(specs)
```

---

### search

Search for similar specifications.

```python
def search(
    query: str,
    top_k: int = 5,
    filters: dict | None = None,
    threshold: float = 0.0,
) -> list[SearchResult]
```

#### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `query` | `str` | Search query | required |
| `top_k` | `int` | Number of results | `5` |
| `filters` | `dict \| None` | Metadata filters | `None` |
| `threshold` | `float` | Minimum score | `0.0` |

#### Example

```python
results = memory.search(
    query="authentication",
    top_k=10,
    filters={"spec_type": "requirement"},
    threshold=0.5
)

for result in results:
    print(f"{result.spec.path}: {result.score}")
```

---

### get

Get a specification by ID.

```python
def get(spec_id: str) -> SpecBlock | None
```

#### Example

```python
spec = memory.get("auth-001")
```

---

### update

Update an existing specification.

```python
def update(spec: SpecBlock) -> bool
```

#### Returns

`True` if updated, `False` if not found.

#### Example

```python
spec.summary = "Updated summary"
memory.update(spec)
```

---

### delete

Delete a specification.

```python
def delete(spec_id: str) -> bool
```

#### Example

```python
memory.delete("auth-001")
```

---

### pin

Pin a specification for guaranteed recall.

```python
def pin(spec_id: str) -> None
```

Pinned specifications are always included in context bundles.

#### Example

```python
memory.pin("security-requirements")
```

---

### unpin

Unpin a specification.

```python
def unpin(spec_id: str) -> None
```

---

### get_pinned

Get all pinned specifications.

```python
def get_pinned() -> list[SpecBlock]
```

#### Example

```python
pinned = memory.get_pinned()
for spec in pinned:
    print(f"Pinned: {spec.path}")
```

---

### get_all

Get all specifications.

```python
def get_all(
    filters: dict | None = None,
) -> list[SpecBlock]
```

#### Example

```python
# All specs
all_specs = memory.get_all()

# Filtered
requirements = memory.get_all(filters={"spec_type": "requirement"})
```

---

### count

Get the number of specifications.

```python
def count(filters: dict | None = None) -> int
```

#### Example

```python
total = memory.count()
requirements = memory.count(filters={"spec_type": "requirement"})
```

---

### clear

Clear all specifications.

```python
def clear() -> None
```

!!! warning
    This permanently deletes all indexed specifications.

---

### rebuild_index

Rebuild the vector index.

```python
def rebuild_index() -> None
```

Use after bulk updates or when the index becomes corrupted.

## SearchResult

```python
@dataclass
class SearchResult:
    spec: SpecBlock      # The matched specification
    score: float         # Similarity score (0-1)
    highlights: list[str] # Matching text snippets
```
