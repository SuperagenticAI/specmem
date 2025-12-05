# ☁️ Cloud Embeddings

Use cloud embedding providers for higher quality embeddings.

## Overview

SpecMem currently supports two embedding providers:

| Provider | Model | Dimensions | Quality | Cost |
|----------|-------|------------|---------|------|
| Local | all-MiniLM-L6-v2 | 384 | ⭐⭐⭐ | Free |
| OpenAI | text-embedding-3-small | 1536 | ⭐⭐⭐⭐ | $0.02/1M tokens |
| OpenAI | text-embedding-3-large | 3072 | ⭐⭐⭐⭐⭐ | $0.13/1M tokens |

## Local Embeddings (Default)

Uses SentenceTransformers locally - no API key required.

### Installation

```bash
pip install "specmem[local]"
```

### Configuration

```toml
[embedding]
provider = "local"
model = "all-MiniLM-L6-v2"
```

### Python Usage

```python
from specmem.vectordb.embeddings import LocalEmbeddingProvider

embeddings = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
vectors = embeddings.embed(["authentication requirements"])
```

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
from specmem.vectordb.embeddings import OpenAIEmbeddingProvider

embeddings = OpenAIEmbeddingProvider(
    model="text-embedding-3-small",
    api_key="sk-...",  # Or use OPENAI_API_KEY env var
)

vectors = embeddings.embed(["authentication requirements"])
```

### Available Models

| Model | Dimensions | Max Tokens | Best For |
|-------|------------|------------|----------|
| text-embedding-3-small | 1536 | 8191 | General use |
| text-embedding-3-large | 3072 | 8191 | High accuracy |
| text-embedding-ada-002 | 1536 | 8191 | Legacy |

## Using the Factory Function

The recommended way to get an embedding provider:

```python
from specmem.vectordb.embeddings import get_embedding_provider

# Local embeddings (default)
local = get_embedding_provider(provider="local")

# OpenAI embeddings
openai = get_embedding_provider(
    provider="openai",
    model="text-embedding-3-small",
    api_key="sk-...",  # Or set OPENAI_API_KEY env var
)

# Generate embeddings
vectors = openai.embed(["spec 1", "spec 2", "spec 3"])
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
from specmem.vectordb.embeddings import EmbeddingProvider, SUPPORTED_PROVIDERS

class CustomEmbeddingProvider(EmbeddingProvider):
    """Custom embedding provider."""

    def __init__(self, model_name: str = "custom-model") -> None:
        self._model_name = model_name
        self._dimension = 768

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Your embedding logic here
        return [[0.0] * self._dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

# Register the provider
SUPPORTED_PROVIDERS["custom"] = CustomEmbeddingProvider
```

Use in config:

```toml
[embedding]
provider = "custom"
model = "my-model"
```

## Future Providers

Support for additional providers (Anthropic, Google, Together AI) is planned for future releases.
