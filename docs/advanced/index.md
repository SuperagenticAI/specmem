# 🔧 Advanced

Advanced topics for power users and contributors.

## Topics

<div class="feature-grid">
  <div class="feature-card">
    <h3><span class="emoji">✍️</span> Writing Adapters</h3>
    <p>Create custom adapters for new frameworks.</p>
    <a href="writing-adapters/" class="md-button">Learn →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🗄️</span> Vector Backends</h3>
    <p>Configure and optimize vector databases.</p>
    <a href="vector-backends/" class="md-button">Configure →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">☁️</span> Cloud Embeddings</h3>
    <p>Use cloud embedding providers.</p>
    <a href="cloud-embeddings/" class="md-button">Setup →</a>
  </div>
  <div class="feature-card">
    <h3><span class="emoji">🔗</span> Agent Integration</h3>
    <p>Integrate SpecMem with AI agents.</p>
    <a href="agent-integration/" class="md-button">Integrate →</a>
  </div>
</div>

## Architecture Deep Dive

```mermaid
graph TB
    subgraph Input
        A1[Kiro Specs]
        A2[Cursor Config]
        A3[Claude.md]
        A4[Custom]
    end

    subgraph Adapters
        B1[KiroAdapter]
        B2[CursorAdapter]
        B3[ClaudeAdapter]
        B4[CustomAdapter]
    end

    subgraph Core
        C1[SpecIR]
        C2[Memory Bank]
        C3[Impact Graph]
        C4[SpecDiff]
        C5[Validator]
    end

    subgraph Storage
        D1[LanceDB]
        D2[ChromaDB]
        D3[Qdrant]
    end

    subgraph Output
        E1[CLI]
        E2[Python API]
        E3[Web UI]
        E4[Agent Pack]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4

    B1 --> C1
    B2 --> C1
    B3 --> C1
    B4 --> C1

    C1 --> C2
    C1 --> C3
    C1 --> C4
    C1 --> C5

    C2 --> D1
    C2 --> D2
    C2 --> D3

    C2 --> E1
    C2 --> E2
    C2 --> E3
    C3 --> E4
```

## Performance Tuning

### Embedding Batch Size

```toml
[embedding]
batch_size = 64  # Increase for faster indexing
```

### Vector Index Settings

```toml
[vectordb]
# LanceDB specific
index_type = "IVF_PQ"
num_partitions = 256
num_sub_vectors = 96
```

### Memory Usage

```toml
[memory]
# Limit in-memory cache
max_cache_size = 1000
# Enable disk-based storage
use_mmap = true
```

## Extending SpecMem

### Custom Validation Rules

```python
from specmem.validator import ValidationRule, register_rule

@register_rule
class MyRule(ValidationRule):
    name = "my_rule"

    def validate(self, spec):
        # Custom validation logic
        pass
```

### Custom Embedding Providers

```python
from specmem.vectordb.embeddings import EmbeddingProvider, register_provider

@register_provider("custom")
class CustomEmbeddings(EmbeddingProvider):
    def embed(self, text: str) -> list[float]:
        # Custom embedding logic
        pass
```

### Hooks and Events

```python
from specmem import on_scan, on_build

@on_scan
def my_scan_hook(result):
    print(f"Scanned {result.count} specs")

@on_build
def my_build_hook(result):
    print(f"Built pack at {result.path}")
```
