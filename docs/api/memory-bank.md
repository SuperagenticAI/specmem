# Memory Bank

The Memory Bank coordinates chunking, embedding generation, vector storage, and
retrieval for `SpecBlock` objects.

## Import

```python
from specmem.core.memory_bank import MemoryBank
```

## Constructor

```python
MemoryBank(
    vector_store: VectorStore,
    embedding_provider: EmbeddingProvider,
    chunk_size: int = 1000,
)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `vector_store` | `VectorStore` | Vector database backend |
| `embedding_provider` | `EmbeddingProvider` | Embedding generator |
| `chunk_size` | `int` | Maximum characters per stored chunk |

## Example

```python
from specmem.core.memory_bank import MemoryBank
from specmem.core.specir import SpecBlock, SpecStatus, SpecType
from specmem.vectordb import LanceDBStore, get_embedding_provider

vector_store = LanceDBStore(db_path=".specmem/vectordb")
embedding_provider = get_embedding_provider(
    provider="local",
    model="all-MiniLM-L6-v2",
)

memory = MemoryBank(vector_store=vector_store, embedding_provider=embedding_provider)
memory.initialize()

blocks = [
    SpecBlock(
        id="auth-001",
        type=SpecType.REQUIREMENT,
        text="Users must authenticate with short-lived access tokens.",
        source=".kiro/specs/auth/requirements.md",
        status=SpecStatus.ACTIVE,
        tags=["auth", "security"],
        pinned=True,
    )
]

added = memory.add_blocks(blocks)
results = memory.query("How should authentication work?", top_k=5)
```

## from_config

Create a memory bank from `SpecMemConfig`.

```python
from specmem.core.config import SpecMemConfig
from specmem.core.memory_bank import MemoryBank

config = SpecMemConfig.load()
memory = MemoryBank.from_config(config)
memory.initialize()
```

`from_config` honors the configured vector backend, including LanceDB, Chroma,
Qdrant, and AgentVectorDB when the corresponding extra is installed.

## initialize

Initialize the underlying vector store.

```python
memory.initialize()
```

## add_blocks

Add one or more `SpecBlock` objects to memory.

```python
count = memory.add_blocks(blocks)
```

Large blocks are split into overlapping chunks before embedding. The return
value is the number of stored blocks after chunking.

## query

Query memory using natural language.

```python
results = memory.query(
    query_text="What are the auth requirements?",
    top_k=10,
    include_legacy=False,
    include_pinned=True,
)
```

Returns `list[QueryResult]`, sorted by descending score.

```python
for result in results:
    print(result.score, result.block.source, result.block.text[:120])
```

Pinned blocks can be included automatically so critical project rules and
architectural constraints are not lost to vector ranking.

## get_statistics

Return counts by type, status, source, and pinned status.

```python
stats = memory.get_statistics()
print(stats.to_dict())
```

## update_status

Update a block lifecycle status.

```python
memory.update_status("auth-001", SpecStatus.DEPRECATED)
```

The vector store validates lifecycle transitions and can move obsolete blocks to
an audit log when the backend supports it.

## clear

Clear all indexed memory from the configured vector store.

```python
memory.clear()
```

!!! warning
    This deletes the indexed memory store. Source specification files are not
    deleted.

## Related Types

`QueryResult` comes from `specmem.vectordb.base`:

```python
from specmem.vectordb.base import QueryResult
```

It contains:

| Field | Description |
|-------|-------------|
| `block` | Matched `SpecBlock` |
| `score` | Similarity score |
| `distance` | Distance metric when provided by the backend |
| `deprecation_warning` | Warning for deprecated memory |
| `importance_score` | Optional backend-specific importance score |
