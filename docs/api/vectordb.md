# Vector Stores

SpecMem supports multiple vector database backends for storing and searching embeddings.

## Base Interface

All vector stores implement the `VectorStore` protocol:

```python
from specmem.vectordb.base import VectorStore

class VectorStore(Protocol):
    def add(self, id: str, embedding: list[float], metadata: dict) -> None: ...
    def search(self, embedding: list[float], top_k: int, filters: dict | None) -> list[SearchResult]: ...
    def get(self, id: str) -> dict | None: ...
    def delete(self, id: str) -> bool: ...
    def count(self) -> int: ...
    def clear(self) -> None: ...
```

## LanceDB (Default)

High-performance embedded vector database.

```python
from specmem.vectordb import LanceDBStore

store = LanceDBStore(
    path=".specmem/vectordb",
    table_name="specs",
)
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `path` | `str \| Path` | Database path | required |
| `table_name` | `str` | Table name | `"specs"` |

### Features

- ✅ Embedded (no server)
- ✅ Fast similarity search
- ✅ Metadata filtering
- ✅ Persistent storage
- ✅ Apache Arrow format

## ChromaDB

Popular open-source vector database.

```python
from specmem.vectordb import ChromaDBStore

store = ChromaDBStore(
    path=".specmem/chroma",
    collection_name="specs",
)
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `path` | `str \| Path` | Database path | required |
| `collection_name` | `str` | Collection name | `"specs"` |

### Installation

```bash
pip install "specmem[chroma]"
```

### Features

- ✅ Embedded or client-server
- ✅ Metadata filtering
- ✅ Multiple distance metrics
- ✅ Persistent storage

## Qdrant

Production-grade vector database.

```python
from specmem.vectordb import QdrantStore

# Local (embedded)
store = QdrantStore(
    path=".specmem/qdrant",
    collection_name="specs",
)

# Remote server
store = QdrantStore(
    url="http://localhost:6333",
    collection_name="specs",
)

# Qdrant Cloud
store = QdrantStore(
    url="https://your-cluster.qdrant.io",
    api_key="your-api-key",
    collection_name="specs",
)
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `path` | `str \| Path \| None` | Local path | `None` |
| `url` | `str \| None` | Server URL | `None` |
| `api_key` | `str \| None` | API key | `None` |
| `collection_name` | `str` | Collection name | `"specs"` |

### Installation

```bash
pip install "specmem[qdrant]"
```

### Features

- ✅ Embedded or client-server
- ✅ Cloud hosting available
- ✅ Advanced filtering
- ✅ High scalability
- ✅ HNSW indexing

## Factory

Use the factory to create stores from configuration:

```python
from specmem.vectordb import create_vectordb

# From config
store = create_vectordb(
    backend="lancedb",
    path=".specmem/vectordb",
)

# From config file
store = create_vectordb_from_config(config)
```

## Embedding Providers

### Local Embeddings

```python
from specmem.vectordb.embeddings import LocalEmbeddings

embeddings = LocalEmbeddings(
    model="all-MiniLM-L6-v2",
)

vector = embeddings.embed("authentication requirements")
vectors = embeddings.embed_batch(["query1", "query2"])
```

### OpenAI Embeddings

```python
from specmem.vectordb.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key="sk-...",  # Or use OPENAI_API_KEY env var
)
```

### Anthropic Embeddings

```python
from specmem.vectordb.embeddings import AnthropicEmbeddings

embeddings = AnthropicEmbeddings(
    model="claude-3-haiku-20240307",
    api_key="sk-ant-...",  # Or use ANTHROPIC_API_KEY env var
)
```

### Google Embeddings

```python
from specmem.vectordb.embeddings import GoogleEmbeddings

embeddings = GoogleEmbeddings(
    model="embedding-001",
    api_key="...",  # Or use GOOGLE_API_KEY env var
)
```

## Custom Vector Store

Implement the `VectorStore` protocol:

```python
from specmem.vectordb.base import VectorStore, SearchResult

class MyVectorStore(VectorStore):
    def add(self, id: str, embedding: list[float], metadata: dict) -> None:
        # Store the embedding
        pass

    def search(
        self,
        embedding: list[float],
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        # Search for similar embeddings
        return []

    def get(self, id: str) -> dict | None:
        # Get by ID
        return None

    def delete(self, id: str) -> bool:
        # Delete by ID
        return False

    def count(self) -> int:
        # Return count
        return 0

    def clear(self) -> None:
        # Clear all data
        pass
```

Register your custom store:

```python
from specmem.vectordb import register_backend

register_backend("mystore", MyVectorStore)
```
