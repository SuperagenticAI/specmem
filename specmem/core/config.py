"""Configuration management for SpecMem.

Handles loading and validation of SpecMem configuration from
.specmem.toml or .specmem.json files.
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


try:
    import tomli
    import tomli_w

    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False

from specmem.core.exceptions import ConfigurationError


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation.

    Attributes:
        provider: Embedding provider (local uses SentenceTransformers)
        model: Model name/identifier for the provider
        api_key: API key for cloud providers (optional, falls back to env var)
    """

    provider: Literal["local", "openai", "anthropic", "gemini", "together"] = "local"
    model: str = "all-MiniLM-L6-v2"
    api_key: str | None = None

    def get_api_key(self) -> str | None:
        """Get API key from config or environment variable.

        Returns:
            API key from config, or from environment variable based on provider.
        """
        import os

        if self.api_key:
            return self.api_key

        # Environment variable mapping per provider
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "together": "TOGETHER_API_KEY",
        }

        env_var = env_vars.get(self.provider)
        if env_var:
            return os.environ.get(env_var)

        return None


class VectorDBConfig(BaseModel):
    """Vector database configuration.

    Backends:
        - lancedb (default): Fast DiskANN-based search, serverless, columnar storage
        - agentvectordb: Agent-optimized memory from Superagentic AI
        - chroma: ChromaDB for simple use cases
        - qdrant: Qdrant for distributed deployments
        - sqlite-vec: SQLite-based for minimal dependencies

    Attributes:
        backend: Vector database backend to use
        path: Path to store vector database files
        agentvectordb_api_key: API key for AgentVectorDB (optional)
        agentvectordb_endpoint: Custom endpoint for AgentVectorDB (optional)
    """

    backend: Literal["lancedb", "agentvectordb", "chroma", "qdrant", "sqlite-vec"] = "lancedb"
    path: str = ".specmem/vectordb"
    agentvectordb_api_key: str | None = None
    agentvectordb_endpoint: str | None = None


class SpecMemConfig(BaseModel):
    """Main SpecMem configuration.

    Attributes:
        embedding: Embedding generation configuration
        vectordb: Vector database configuration
        adapters: List of enabled adapter names
    """

    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    vectordb: VectorDBConfig = Field(default_factory=VectorDBConfig)
    adapters: list[str] = Field(default_factory=lambda: ["kiro"])

    @classmethod
    def load(cls, config_path: Path | None = None) -> "SpecMemConfig":
        """Load configuration from file.

        Searches for .specmem.toml or .specmem.json in the current directory
        or uses the provided path.

        Args:
            config_path: Optional explicit path to config file

        Returns:
            Loaded configuration or defaults if no config found

        Raises:
            ConfigurationError: If config file exists but is invalid
        """
        if config_path is not None:
            return cls._load_from_path(config_path)

        # Search for config files in current directory
        cwd = Path.cwd()
        toml_path = cwd / ".specmem.toml"
        json_path = cwd / ".specmem.json"

        if toml_path.exists():
            return cls._load_from_path(toml_path)
        elif json_path.exists():
            return cls._load_from_path(json_path)
        else:
            # Return defaults
            return cls()

    @classmethod
    def _load_from_path(cls, path: Path) -> "SpecMemConfig":
        """Load configuration from a specific file path."""
        if not path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                code="CONFIG_NOT_FOUND",
                details={"path": str(path)},
            )

        try:
            content = path.read_text()

            if path.suffix == ".toml":
                if not TOML_AVAILABLE:
                    raise ConfigurationError(
                        "TOML support not available. Install tomli and tomli-w.",
                        code="TOML_NOT_AVAILABLE",
                    )
                data = tomli.loads(content)
            elif path.suffix == ".json":
                data = json.loads(content)
            else:
                raise ConfigurationError(
                    f"Unsupported config format: {path.suffix}",
                    code="UNSUPPORTED_FORMAT",
                    details={"path": str(path), "suffix": path.suffix},
                )

            return cls.model_validate(data)

        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in config file: {e}",
                code="INVALID_JSON",
                details={"path": str(path), "error": str(e)},
            ) from e
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to load config: {e}",
                code="CONFIG_LOAD_ERROR",
                details={"path": str(path), "error": str(e)},
            ) from e

    def save(self, path: Path) -> None:
        """Save configuration to file.

        Args:
            path: Path to save config file (.toml or .json)

        Raises:
            ConfigurationError: If save fails
        """
        try:
            data = self.model_dump(exclude_none=True)

            if path.suffix == ".toml":
                if not TOML_AVAILABLE:
                    raise ConfigurationError(
                        "TOML support not available. Install tomli and tomli-w.",
                        code="TOML_NOT_AVAILABLE",
                    )
                content = tomli_w.dumps(data)
            elif path.suffix == ".json":
                content = json.dumps(data, indent=2)
            else:
                raise ConfigurationError(
                    f"Unsupported config format: {path.suffix}",
                    code="UNSUPPORTED_FORMAT",
                    details={"path": str(path), "suffix": path.suffix},
                )

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to save config: {e}",
                code="CONFIG_SAVE_ERROR",
                details={"path": str(path), "error": str(e)},
            ) from e

    def to_json(self) -> str:
        """Serialize config to JSON string."""
        return self.model_dump_json(indent=2, exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> "SpecMemConfig":
        """Deserialize config from JSON string."""
        return cls.model_validate_json(json_str)
