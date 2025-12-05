# 📦 Installation

Install SpecMem using your preferred package manager.

## Basic Installation

=== "pip"

    ```bash
    pip install specmem
    ```

=== "uv"

    ```bash
    uv pip install specmem
    ```

=== "pipx"

    ```bash
    pipx install specmem
    ```

## Optional Dependencies

SpecMem supports various optional features. Install them based on your needs:

### ☁️ Cloud Embedding Providers

=== "OpenAI"

    ```bash
    pip install "specmem[openai]"
    ```

=== "Google"

    ```bash
    pip install "specmem[google]"
    ```

=== "Together AI"

    ```bash
    pip install "specmem[together]"
    ```

=== "All Providers"

    ```bash
    pip install "specmem[cloud]"
    ```

### 🗄️ Alternative Vector Stores

=== "ChromaDB"

    ```bash
    pip install "specmem[chroma]"
    ```

=== "Qdrant"

    ```bash
    pip install "specmem[qdrant]"
    ```

### 🌐 Web UI

```bash
pip install "specmem[ui]"
```

### 🔧 Development

```bash
pip install "specmem[dev]"
```

### 📚 Documentation

```bash
pip install "specmem[docs]"
```

### 🎯 Everything

```bash
pip install "specmem[all]"
```

## Verify Installation

After installation, verify SpecMem is working:

```bash
specmem --version
```

Expected output:

```
SpecMem v0.1.0
```

## From Source

For the latest development version:

```bash
git clone https://github.com/Shashikant86/specmem.git
cd specmem
pip install -e ".[dev]"
```

## Docker

Run SpecMem in a container:

```bash
docker run -v $(pwd):/workspace ghcr.io/shashikant86/specmem:latest scan
```

## Troubleshooting

### Common Issues

!!! warning "Python Version"
    SpecMem requires Python 3.11 or higher. Check your version:
    ```bash
    python --version
    ```

!!! tip "Virtual Environment"
    We recommend using a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # macOS/Linux
    .venv\Scripts\activate     # Windows
    pip install specmem
    ```

!!! note "Apple Silicon"
    On Apple Silicon Macs, some dependencies may need Rosetta:
    ```bash
    arch -x86_64 pip install specmem
    ```

## Next Steps

Once installed, proceed to the [Quick Start](quickstart.md) guide.
