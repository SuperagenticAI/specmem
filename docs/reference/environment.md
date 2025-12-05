# Environment Variables

All environment variables supported by SpecMem.

## Core Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SPECMEM_CONFIG` | Path to config file | `.specmem.toml` |
| `SPECMEM_LOG_LEVEL` | Log level (debug, info, warning, error) | `info` |
| `SPECMEM_NO_COLOR` | Disable colored output | `false` |
| `SPECMEM_DATA_DIR` | Data directory path | `.specmem` |

## Embedding Providers

### OpenAI

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `OPENAI_ORG_ID` | Organization ID | No |
| `OPENAI_BASE_URL` | Custom API base URL | No |

### Google

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google API key | Yes |

### Together AI

| Variable | Description | Required |
|----------|-------------|----------|
| `TOGETHER_API_KEY` | Together AI API key | Yes |

## Vector Databases

### Qdrant

| Variable | Description | Required |
|----------|-------------|----------|
| `QDRANT_URL` | Qdrant server URL | No |
| `QDRANT_API_KEY` | Qdrant API key | No |

### ChromaDB

| Variable | Description | Required |
|----------|-------------|----------|
| `CHROMA_HOST` | ChromaDB server host | No |
| `CHROMA_PORT` | ChromaDB server port | No |

## Configuration Overrides

Override any config option via environment variable:

```bash
# Pattern: SPECMEM_<SECTION>_<KEY>
export SPECMEM_EMBEDDING_PROVIDER="openai"
export SPECMEM_EMBEDDING_MODEL="text-embedding-3-small"
export SPECMEM_VECTORDB_BACKEND="qdrant"
export SPECMEM_IMPACT_MAX_DEPTH="3"
```

## CI/CD Variables

Recommended variables for CI environments:

```bash
# Disable interactive prompts
export SPECMEM_CI="true"

# Use JSON logging
export SPECMEM_LOG_FORMAT="json"

# Strict validation
export SPECMEM_VALIDATION_STRICT="true"
```

## Docker Variables

```dockerfile
ENV SPECMEM_CONFIG=/app/.specmem.toml
ENV SPECMEM_DATA_DIR=/data/specmem
ENV SPECMEM_LOG_LEVEL=info
```

## Example .env File

```bash
# .env (add to .gitignore)

# Embedding provider
OPENAI_API_KEY=sk-...

# Vector database
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=...

# Logging
SPECMEM_LOG_LEVEL=debug
```

## Loading Environment Variables

### Python

```python
from dotenv import load_dotenv
load_dotenv()

from specmem import SpecMemClient
sm = SpecMemClient()  # Uses env vars automatically
```

### Shell

```bash
# Load from .env
export $(cat .env | xargs)

# Run SpecMem
specmem scan
```

## Security Notes

!!! warning "Never Commit API Keys"
    - Add `.env` to `.gitignore`
    - Use secret management in CI/CD
    - Rotate keys regularly

!!! tip "Use .specmem.local.toml"
    For local overrides that shouldn't be committed:
    ```toml
    # .specmem.local.toml (gitignored)
    [embedding]
    provider = "openai"
    api_key = "sk-..."
    ```
