# 🗄️ Vector Backends

Configure and optimize vector database backends for your use case.

## Choosing a Backend

| Backend | Best For | Persistence | Scalability | Setup |
|---------|----------|-------------|-------------|-------|
| LanceDB | Local development, small-medium projects | File-based | Medium | Zero config |
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

- ✅ Local development
- ✅ CI/CD pipelines
- ✅ Single-user applications
- ✅ Projects with <100k specs
- ❌ Multi-user concurrent access
- ❌ Distributed systems

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

- ✅ Quick prototyping
- ✅ Experimentation
- ✅ Simple deployments
- ✅ Projects with <50k specs
- ❌ High-performance requirements
- ❌ Large-scale production

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

[vectordb.qdrant]
collection = "specs"
```

### Server Mode

```toml
[vectordb]
backend = "qdrant"

[vectordb.qdrant]
url = "http://localhost:6333"
collection = "specs"
```

### Qdrant Cloud

```toml
[vectordb]
backend = "qdrant"

[vectordb.qdrant]
url = "https://your-cluster.qdrant.io"
api_key = "${QDRANT_API_KEY}"
collection = "specs"
```

### Advanced Configuration

```python
from specmem.vectordb import QdrantStore
from qdrant_client.models import Distance, VectorParams

store = QdrantStore(
    url="http://localhost:6333",
    collection="specs",
    vector_params=VectorParams(
        size=384,
        distance=Distance.COSINE,
    ),
    # HNSW index parameters
    hnsw_config={
        "m": 16,
        "ef_construct": 100,
    },
    # Optimizers
    optimizer_config={
        "indexing_threshold": 20000,
    },
)
```

### When to Use

- ✅ Production deployments
- ✅ Large-scale projects (>100k specs)
- ✅ Multi-user applications
- ✅ High availability requirements
- ✅ Advanced filtering needs
- ❌ Simple local development

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
