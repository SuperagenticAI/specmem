# ☁️ Cloud Embeddings

Use cloud embedding providers for higher quality embeddings.

## Overview

| Provider | Model | Dimensions | Quality | Cost |
|----------|-------|------------|---------|------|
| Local | all-MiniLM-L6-v2 | 384 | ⭐⭐⭐ | Free |
| OpenAI | text-embedding-3-small | 1536 | ⭐⭐⭐⭐ | $0.02/1M tokens |
| OpenAI | text-embedding-3-large | 3072 | ⭐⭐⭐⭐⭐ | $0.13/1M tokens |
| Anthropic | claude-3-haiku | 1024 | ⭐⭐⭐⭐ | $0.25/1M tokens |
| Google | embedding-001 | 768 | ⭐⭐⭐⭐ | $0.025/1M chars |
| Together | togethercomputer/m2-bert | 768 | ⭐⭐⭐⭐ | $0.008/1M tokens |

## OpenAI

### Installation

```bash
pip install "specmem[openai]"
```

### Configuration

```toml
[embedding]
provider = "openai"
model = "text-embedding-3-small"
```

### Environment Variable

```bash
export OPENAI_API_KEY="sk-..."
```

### Python Usage

```python
from specmem.vectordb.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key="sk-...",  # Or use env var
)

vector = embeddings.embed("authentication requirements")
```

### Available Models

| Model | Dimensions | Max Tokens | Best For |
|-------|------------|------------|----------|
| text-embedding-3-small | 1536 | 8191 | General use |
| text-embedding-3-large | 3072 | 8191 | High accuracy |
| text-embedding-ada-002 | 1536 | 8191 | Legacy |

## Anthropic

### Installation

```bash
pip install "specmem[anthropic]"
```

### Configuration

```toml
[embedding]
provider = "anthropic"
model = "claude-3-haiku-20240307"
```

### Environment Variable

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Python Usage

```python
from specmem.vectordb.embeddings import AnthropicEmbeddings

embeddings = AnthropicEmbeddings(
    model="claude-3-haiku-20240307",
    api_key="sk-ant-...",
)
```

## Google

### Installation

```bash
pip install "specmem[google]"
```

### Configuration

```toml
[embedding]
provider = "google"
model = "embedding-001"
```

### Environment Variable

```bash
export GOOGLE_API_KEY="..."
```

### Python Usage

```python
from specmem.vectordb.embeddings import GoogleEmbeddings

embeddings = GoogleEmbeddings(
    model="embedding-001",
    api_key="...",
)
```

## Together AI

### Installation

```bash
pip install "specmem[together]"
```

### Configuration

```toml
[embedding]
provider = "together"
model = "togethercomputer/m2-bert-80M-8k-retrieval"
```

### Environment Variable

```bash
export TOGETHER_API_KEY="..."
```

### Available Models

| Model | Dimensions | Context |
|-------|------------|---------|
| m2-bert-80M-8k-retrieval | 768 | 8192 |
| m2-bert-80M-32k-retrieval | 768 | 32768 |

## Batch Processing

For large spec collections, use batch processing:

```python
from specmem.vectordb.embeddings import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    batch_size=100,  # Process 100 at a time
)

texts = ["spec 1", "spec 2", "spec 3", ...]
vectors = embeddings.embed_batch(texts)
```

## Caching

Enable embedding caching to reduce API calls:

```toml
[embedding]
provider = "openai"
model = "text-embedding-3-small"

[embedding.cache]
enabled = true
path = ".specmem/embedding_cache"
ttl_days = 30
```

```python
from specmem.vectordb.embeddings import CachedEmbeddings, OpenAIEmbeddings

base = OpenAIEmbeddings(model="text-embedding-3-small")
embeddings = CachedEmbeddings(
    base=base,
    cache_path=".specmem/embedding_cache",
)
```

## Rate Limiting

Handle rate limits gracefully:

```toml
[embedding]
provider = "openai"

[embedding.rate_limit]
requests_per_minute = 3000
tokens_per_minute = 1000000
retry_attempts = 3
retry_delay = 1.0
```

## Cost Estimation

Estimate embedding costs before indexing:

```python
from specmem import SpecMemClient

sm = SpecMemClient()

# Estimate cost
estimate = sm.estimate_embedding_cost()
print(f"Specs to index: {estimate.spec_count}")
print(f"Total tokens: {estimate.total_tokens}")
print(f"Estimated cost: ${estimate.cost:.4f}")

# Proceed if acceptable
if estimate.cost < 1.0:
    sm.scan()
```

## Hybrid Approach

Use local embeddings for development, cloud for production:

```toml
# .specmem.toml (committed)
[embedding]
provider = "local"
model = "all-MiniLM-L6-v2"
```

```toml
# .specmem.local.toml (not committed)
[embedding]
provider = "openai"
model = "text-embedding-3-small"
```

## Custom Provider

Implement your own embedding provider:

```python
from specmem.vectordb.embeddings import EmbeddingProvider, register_provider

@register_provider("custom")
class CustomEmbeddings(EmbeddingProvider):
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.dimensions = 768

    def embed(self, text: str) -> list[float]:
        # Your embedding logic
        return [0.0] * self.dimensions

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
```

Use in config:

```toml
[embedding]
provider = "custom"
model = "my-model"
```
