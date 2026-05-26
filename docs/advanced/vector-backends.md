# Vector Backends

Configure and optimize vector database backends for your use case.

## Choosing a Backend

| Backend | Best For | Persistence | Scalability | Setup |
|---------|----------|-------------|-------------|-------|
| LanceDB | Local development, small to medium projects | File-based | Medium | Zero config |
| AgentVectorDB | Agent-oriented local memory with importance scoring | File-based | Medium | Easy |
| ChromaDB | Prototyping, experimentation | File-based | Medium | Easy |
| Qdrant | Production, large scale | Server/Cloud | High | Moderate |

## LanceDB (Default)

High-performance embedded vector database using Apache Arrow.

### Configuration

```toml
[vectordb]
backend = "lancedb"
path = ".specmem/vectordb"

[vectordb.lancedb]
# Table name
table = "specs"

# Index type: "IVF_PQ", "IVF_FLAT", "HNSW"
index_type = "IVF_PQ"

# Number of partitions (for IVF)
num_partitions = 256

# Number of sub-vectors (for PQ)
num_sub_vectors = 96

# Use memory-mapped files
use_mmap = true
```

### Performance Tuning

```python
from specmem.vectordb import LanceDBStore

store = LanceDBStore(
    path=".specmem/vectordb",
    # Increase for better recall, decrease for speed
    num_partitions=512,
    # More sub-vectors = better compression
    num_sub_vectors=128,
)
```

### When to Use

- Local development
- CI/CD pipelines
- Single-user applications
- Projects with fewer than 100,000 specs or memory blocks

Use a server backend instead for multi-user concurrent access or distributed
systems.

## AgentVectorDB

AgentVectorDB is an agent-oriented local memory backend. It stores SpecMem
blocks with importance scoring, namespace isolation, and memory decay support.

### Installation

```bash
pip install "specmem[agentvectordb]"
```

### Configuration

```toml
[vectordb]
backend = "agentvectordb"
path = ".specmem/agentvectordb"
```

### Python Usage

```python
from specmem.vectordb import get_vector_store

store = get_vector_store(
    backend="agentvectordb",
    path=".specmem/agentvectordb",
    namespace="default",
    enable_importance_scoring=True,
    enable_memory_decay=True,
)
```

### When to Use

- Local agent memory experiments
- Repositories that benefit from importance scoring
- Single-user memory stores with namespace isolation
- Demonstrations of agent-specific memory behavior

Use Qdrant for hosted deployments or multi-user server access.

## ChromaDB

Popular open-source vector database with simple API.

### Installation

```bash
pip install "specmem[chroma]"
```

### Configuration

```toml
[vectordb]
backend = "chroma"
path = ".specmem/chroma"

[vectordb.chroma]
# Collection name
collection = "specs"

# Distance metric: "l2", "ip", "cosine"
distance_metric = "cosine"

# Persistence mode: "local", "memory"
mode = "local"
```

### Client-Server Mode

```python
from specmem.vectordb import ChromaDBStore

# Connect to Chroma server
store = ChromaDBStore(
    host="localhost",
    port=8000,
    collection="specs",
)
```

### When to Use

- Quick prototyping
- Experimentation
- Simple deployments
- Projects with fewer than 50,000 specs or memory blocks

Use Qdrant for high-performance requirements or large production deployments.

## Qdrant

Production-grade vector database with advanced features.

### Installation

```bash
pip install "specmem[qdrant]"
```

### Local (Embedded)

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"

qdrant_collection = "specs"
```

### Server Mode

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"

qdrant_url = "http://localhost:6333"
qdrant_collection = "specs"
```

### Qdrant Cloud

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"

qdrant_url = "https://your-cluster.qdrant.io"
qdrant_api_key = "${QDRANT_API_KEY}"
qdrant_collection = "specs"
```

### Advanced Configuration

```python
from specmem.vectordb import QdrantStore

store = QdrantStore(
    url="http://localhost:6333",
    collection_name="specs",
    audit_collection_name="specs_audit",
    vector_dim=1536,  # Match the embedding model dimension
)
```

SpecMem creates the Qdrant collection with the active embedding dimension. When
you use `specmem build`, the configured backend is honored, so setting
`backend = "qdrant"` writes the memory index to Qdrant instead of the default
LanceDB store.

### When to Use

- Production deployments
- Large repositories with more than 100,000 specs or memory blocks
- Multi-user applications
- High availability requirements
- Advanced filtering needs

For simple local development, use LanceDB unless you specifically need to test
Qdrant behavior.

## Migration Between Backends

### Export from Current Backend

```python
from specmem import SpecMemClient

sm = SpecMemClient()

# Export all specs
specs = sm.get_all_specs()

# Save to file
import json
with open("specs_backup.json", "w") as f:
    json.dump([s.to_dict() for s in specs], f)
```

### Import to New Backend

```python
# Update config to new backend
# Then import

from specmem import SpecMemClient
from specmem.core import SpecBlock
import json

sm = SpecMemClient()

with open("specs_backup.json") as f:
    specs_data = json.load(f)

specs = [SpecBlock.from_dict(s) for s in specs_data]
sm.memory_bank.add_batch(specs)
```

## Performance Benchmarks

Tested on MacBook Pro M2, 16GB RAM:

| Operation | LanceDB | ChromaDB | Qdrant |
|-----------|---------|----------|--------|
| Index 1k specs | 2.1s | 3.4s | 2.8s |
| Index 10k specs | 18s | 45s | 22s |
| Query (top-10) | 5ms | 12ms | 8ms |
| Query (top-100) | 15ms | 35ms | 20ms |
| Memory (10k specs) | 120MB | 280MB | 180MB |

## Custom Backend

Implement the `VectorStore` protocol:

```python
from specmem.vectordb.base import VectorStore, SearchResult

class MyVectorStore(VectorStore):
    def add(self, id: str, embedding: list[float], metadata: dict) -> None:
        pass

    def search(self, embedding: list[float], top_k: int, filters: dict | None) -> list[SearchResult]:
        pass

    def get(self, id: str) -> dict | None:
        pass

    def delete(self, id: str) -> bool:
        pass

    def count(self) -> int:
        pass

    def clear(self) -> None:
        pass

# Register
from specmem.vectordb import register_backend
register_backend("mystore", MyVectorStore)
```
