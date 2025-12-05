# 🔧 Configuration

Configure SpecMem to match your project's needs.

## Configuration File

SpecMem uses `.specmem.toml` in your project root:

```bash
specmem init
```

## Full Configuration Reference

```toml
# .specmem.toml - SpecMem Configuration

# =============================================================================
# Embedding Configuration
# =============================================================================
[embedding]
# Provider: "local", "openai", "google", "together"
provider = "local"

# Model name (provider-specific)
model = "all-MiniLM-L6-v2"

# Embedding dimensions (auto-detected for most models)
# dimensions = 384

# Batch size for embedding generation
batch_size = 32

# =============================================================================
# Vector Database Configuration
# =============================================================================
[vectordb]
# Backend: "lancedb", "chroma", "qdrant"
backend = "lancedb"

# Storage path (relative to project root)
path = ".specmem/vectordb"

# Collection name
collection = "specs"

# =============================================================================
# Adapter Configuration
# =============================================================================
[adapters]
# Enable/disable specific adapters
kiro = true
cursor = true
claude = true
speckit = true
tessl = true

# Custom adapter paths
# custom = ["./my-adapter.py"]

# =============================================================================
# Impact Graph Configuration
# =============================================================================
[impact]
# Maximum traversal depth for impact analysis
max_depth = 2

# Include transitive dependencies
transitive = true

# File patterns to include in analysis
include_patterns = ["*.py", "*.ts", "*.js", "*.go", "*.rs"]

# File patterns to exclude
exclude_patterns = ["*_test.py", "*.spec.ts", "test_*.py"]

# =============================================================================
# Scanning Configuration
# =============================================================================
[scan]
# Directories to scan for specs
spec_dirs = [
    ".kiro/specs",
    ".cursor",
    ".speckit",
    ".tessl",
]

# Files to scan
spec_files = [
    "cursor.json",
    ".cursorrules",
    "Claude.md",
    "CLAUDE.md",
]

# Ignore patterns
ignore = [
    "node_modules",
    ".git",
    ".venv",
    "__pycache__",
]

# =============================================================================
# Output Configuration
# =============================================================================
[output]
# Output directory
path = ".specmem"

# Generate human-readable context
generate_context = true

# Generate knowledge index
generate_index = true

# Generate impact graph
generate_graph = true

# =============================================================================
# Validation Configuration
# =============================================================================
[validation]
# Enable validation rules
rules = [
    "structure",
    "timeline",
    "duplicates",
    "constraints",
    "acceptance_criteria",
    "contradiction",
]

# Severity threshold: "error", "warning", "info"
min_severity = "warning"

# =============================================================================
# Coverage Configuration
# =============================================================================
[coverage]
# Minimum confidence threshold for a criterion to be "covered"
confidence_threshold = 0.5

# Test file patterns to scan
test_patterns = [
    "test_*.py",
    "*_test.py",
    "*.test.ts",
    "*.test.js",
    "*.spec.ts",
    "*.spec.js",
]

# Directories to scan for tests
test_dirs = ["tests", "test", "spec", "__tests__"]

# Exclude patterns
exclude_patterns = ["node_modules", ".venv", "__pycache__"]

# =============================================================================
# Web UI Configuration
# =============================================================================
[ui]
# Server host
host = "127.0.0.1"

# Server port
port = 8000

# Enable hot reload
reload = true

# =============================================================================
# Logging Configuration
# =============================================================================
[logging]
# Log level: "debug", "info", "warning", "error"
level = "info"

# Log format: "text", "json"
format = "text"

# Log file (optional)
# file = ".specmem/specmem.log"
```

## Environment Variables

Override configuration with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SPECMEM_EMBEDDING_PROVIDER` | Embedding provider | `local` |
| `SPECMEM_EMBEDDING_MODEL` | Embedding model | `all-MiniLM-L6-v2` |
| `SPECMEM_VECTORDB_BACKEND` | Vector database | `lancedb` |
| `SPECMEM_VECTORDB_PATH` | Vector DB path | `.specmem/vectordb` |
| `SPECMEM_LOG_LEVEL` | Log level | `info` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GOOGLE_API_KEY` | Google API key | - |
| `TOGETHER_API_KEY` | Together AI API key | - |

## Cloud Embeddings

### OpenAI

```toml
[embedding]
provider = "openai"
model = "text-embedding-3-small"
```

```bash
export OPENAI_API_KEY="sk-..."
```

!!! note "Additional Providers"
    Support for Google and Together AI embeddings is planned for future releases.
    Currently, only `local` and `openai` providers are supported.

## Alternative Vector Stores

### ChromaDB

```toml
[vectordb]
backend = "chroma"
path = ".specmem/chroma"
```

### Qdrant

```toml
[vectordb]
backend = "qdrant"
path = ".specmem/qdrant"
# Or use Qdrant Cloud:
# url = "https://your-cluster.qdrant.io"
# api_key = "your-api-key"
```

## Local Overrides

Create `.specmem.local.toml` for local overrides (gitignored):

```toml
# .specmem.local.toml - Local overrides (not committed)

[embedding]
provider = "openai"
model = "text-embedding-3-large"

[logging]
level = "debug"
```

## Validation

Validate your configuration:

```bash
specmem config validate
```

## Show Current Config

Display the resolved configuration:

```bash
specmem config show
```
