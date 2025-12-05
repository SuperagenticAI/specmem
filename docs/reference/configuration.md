# Configuration Options

Complete reference for all `.specmem.toml` configuration options.

## Embedding

```toml
[embedding]
# Embedding provider
# Options: "local", "openai", "anthropic", "google", "together"
provider = "local"

# Model name (provider-specific)
model = "all-MiniLM-L6-v2"

# Embedding dimensions (auto-detected for most models)
dimensions = 384

# Batch size for embedding generation
batch_size = 32

# API key (can also use environment variable)
# api_key = "..."
```

### Provider-Specific Models

| Provider | Models | Status |
|----------|--------|--------|
| local | all-MiniLM-L6-v2, all-mpnet-base-v2 | ✅ Supported |
| openai | text-embedding-3-small, text-embedding-3-large | ✅ Supported |
| anthropic | (planned) | 🔜 Coming soon |
| google | (planned) | 🔜 Coming soon |
| together | (planned) | 🔜 Coming soon |

## Vector Database

```toml
[vectordb]
# Backend type
# Options: "lancedb", "chroma", "qdrant"
backend = "lancedb"

# Storage path (relative to project root)
path = ".specmem/vectordb"

# Collection/table name
collection = "specs"
```

### LanceDB Options

```toml
[vectordb.lancedb]
table = "specs"
index_type = "IVF_PQ"
num_partitions = 256
num_sub_vectors = 96
use_mmap = true
```

### ChromaDB Options

```toml
[vectordb.chroma]
collection = "specs"
distance_metric = "cosine"
mode = "local"
# For server mode:
# host = "localhost"
# port = 8000
```

### Qdrant Options

```toml
[vectordb.qdrant]
collection = "specs"
# Local mode:
# path = ".specmem/qdrant"
# Server mode:
# url = "http://localhost:6333"
# Cloud mode:
# url = "https://your-cluster.qdrant.io"
# api_key = "..."
```

## Adapters

```toml
[adapters]
# Enable/disable adapters
kiro = true
cursor = true
claude = true
speckit = true
tessl = true

# Framework priority (first = highest)
priority = ["kiro", "cursor", "claude", "speckit", "tessl"]

# Custom adapter paths
# custom = ["./my-adapter.py"]
```

### Adapter-Specific Options

```toml
[adapters.kiro]
spec_dir = ".kiro/specs"

[adapters.cursor]
config_file = "cursor.json"
rules_file = ".cursorrules"

[adapters.claude]
files = ["Claude.md", "CLAUDE.md"]
```

## Impact Analysis

```toml
[impact]
# Maximum traversal depth
max_depth = 2

# Include transitive dependencies
transitive = true

# File patterns to include
include_patterns = ["*.py", "*.ts", "*.js", "*.go", "*.rs"]

# File patterns to exclude
exclude_patterns = ["*_test.py", "*.spec.ts", "test_*.py"]
```

## Scanning

```toml
[scan]
# Directories to scan
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
```

## Output

```toml
[output]
# Output directory
path = ".specmem"

# Generate human-readable context
generate_context = true

# Generate knowledge index
generate_index = true

# Generate impact graph
generate_graph = true
```

## Validation

```toml
[validation]
# Enabled rules
rules = [
    "structure",
    "timeline",
    "duplicates",
    "constraints",
    "acceptance_criteria",
    "contradiction",
]

# Minimum severity to report
# Options: "error", "warning", "info"
min_severity = "warning"

# Custom vague terms to flag
vague_terms = [
    "fast", "slow", "good", "bad",
    "quickly", "adequate", "appropriate",
]

# Custom absolutes to flag
absolutes = [
    "always", "never", "all", "none", "100%", "0%",
]
```

## SpecDiff

```toml
[specdiff]
# Days before spec is considered stale
stale_threshold_days = 90

# Enable contradiction detection
detect_contradictions = true

# History retention
retention_days = 365

# Auto-snapshot on scan
auto_snapshot = true
```

## Coverage

```toml
[coverage]
# Minimum confidence threshold for "covered" status
# Range: 0.0 to 1.0
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

# Supported test frameworks
# Options: "pytest", "jest", "vitest", "playwright", "mocha"
frameworks = ["pytest", "jest", "vitest", "playwright", "mocha"]

# Badge color thresholds
badge_red_threshold = 50    # Below this = red
badge_yellow_threshold = 80 # Below this = yellow, above = green
```

## Selective Testing

```toml
[selective_testing]
# Include integration tests
include_integration = true

# Include slow tests
include_slow = false

# Minimum confidence threshold
confidence_threshold = 0.8

# Always run these tests
always_run = [
    "tests/test_smoke.py",
    "tests/test_critical.py",
]

# Never skip these tests
never_skip = [
    "tests/test_security.py",
]

# Test file patterns
test_patterns = [
    "tests/**/test_*.py",
    "tests/**/*_test.py",
]

# Fallback behavior
# Options: "all", "none", "smoke"
fallback = "smoke"
```

## Web UI

```toml
[ui]
# Server host
host = "127.0.0.1"

# Server port
port = 8000

# Enable hot reload
reload = true

# Enable authentication
auth_enabled = false

# API key (if auth enabled)
# api_key = "..."
```

## Logging

```toml
[logging]
# Log level
# Options: "debug", "info", "warning", "error"
level = "info"

# Log format
# Options: "text", "json"
format = "text"

# Log file (optional)
# file = ".specmem/specmem.log"
```

## Caching

```toml
[cache]
# Enable embedding cache
enabled = true

# Cache path
path = ".specmem/cache"

# Cache TTL in days
ttl_days = 30

# Maximum cache size in MB
max_size_mb = 500
```
