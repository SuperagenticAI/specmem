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
    db_path=".specmem/vectordb",
)
store.initialize()
```

### Installation

```bash
pip install "specmem[local]"
```

### Features

- ✅ Embedded (no server)
- ✅ Fast similarity search
- ✅ Metadata filtering
- ✅ Persistent storage
- ✅ Apache Arrow format

## ChromaDB

Popular open-source vector database.

```python
from specmem.vectordb.chroma_store import ChromaDBStore

store = ChromaDBStore(
    path=".specmem/chroma",
    collection_name="specs",
)
```

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
from specmem.vectordb.qdrant_store import QdrantStore

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
```

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
from specmem.vectordb.factory import get_vector_store

# Create a LanceDB store
store = get_vector_store(
    backend="lancedb",
    db_path=".specmem/vectordb",
)
```

## Embedding Providers

### Local Embeddings (Default)

Uses SentenceTransformers locally - no API key required.

```python
from specmem.vectordb.embeddings import LocalEmbeddingProvider

embeddings = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
vectors = embeddings.embed(["authentication requirements", "user login"])
```

### OpenAI Embeddings

```python
from specmem.vectordb.embeddings import OpenAIEmbeddingProvider

embeddings = OpenAIEmbeddingProvider(
    model="text-embedding-3-small",
    api_key="sk-...",  # Or use OPENAI_API_KEY env var
)
vectors = embeddings.embed(["authentication requirements"])
```

### Factory Function

The recommended way to get an embedding provider:

```python
from specmem.vectordb.embeddings import get_embedding_provider

# Local embeddings (default)
local = get_embedding_provider(provider="local")

# OpenAI embeddings
openai = get_embedding_provider(
    provider="openai",
    model="text-embedding-3-small",
    api_key="sk-...",
)
```

## Custom Vector Store

Implement the `VectorStore` base class:

```python
from specmem.vectordb.base import VectorStore, QueryResult

class MyVectorStore(VectorStore):
    def initialize(self) -> None:
        # Initialize the store
        pass

    def add_block(self, block, embedding: list[float]) -> None:
        # Store the embedding
        pass

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[QueryResult]:
        # Search for similar embeddings
        return []

    def get_block(self, block_id: str):
        # Get by ID
        return None

    def delete_block(self, block_id: str) -> bool:
        # Delete by ID
        return False

    def count(self) -> int:
        # Return count
        return 0

    def clear(self) -> None:
        # Clear all data
        pass
```
