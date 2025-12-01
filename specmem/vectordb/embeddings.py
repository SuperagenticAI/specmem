"""Embedding provider abstraction for SpecMem.

Supports local embeddings via SentenceTransformers and cloud providers.
"""

import logging
import os
from abc import ABC, abstractmethod

from specmem.core.exceptions import EmbeddingError


logger = logging.getLogger(__name__)

# Provider registry for factory
SUPPORTED_PROVIDERS: dict[str, type] = {}

# Default models per provider
DEFAULT_MODELS = {
    "local": "all-MiniLM-L6-v2",
    "openai": "text-embedding-3-small",
}

# Model dimensions for OpenAI models
OPENAI_MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation.

    Implementations:
        - LocalEmbeddingProvider: Uses SentenceTransformers locally
        - OpenAIEmbeddingProvider: Uses OpenAI API (future)
        - AnthropicEmbeddingProvider: Uses Anthropic API (future)
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (same length as texts)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension size.

        Returns:
            Number of dimensions in the embedding vectors
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name/identifier.

        Returns:
            Model name string
        """
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using SentenceTransformers.

    Uses the all-MiniLM-L6-v2 model by default, which provides
    good quality embeddings with fast inference.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize the local embedding provider.

        Args:
            model_name: SentenceTransformers model to use
        """
        self._model_name = model_name
        self._model = None
        self._dimension: int | None = None

    def _load_model(self) -> None:
        """Lazy load the model on first use."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded, dimension: {self._dimension}")

        except ImportError as e:
            raise EmbeddingError(
                "SentenceTransformers not installed. Install with: pip install sentence-transformers",
                code="MISSING_DEPENDENCY",
                details={"package": "sentence-transformers"},
            ) from e
        except Exception as e:
            raise EmbeddingError(
                f"Failed to load embedding model: {e}",
                code="MODEL_LOAD_ERROR",
                details={"model": self._model_name, "error": str(e)},
            ) from e

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using SentenceTransformers.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        self._load_model()

        try:
            # SentenceTransformer returns numpy array, convert to list
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]

        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate embeddings: {e}",
                code="EMBEDDING_GENERATION_ERROR",
                details={"num_texts": len(texts), "error": str(e)},
            ) from e

    @property
    def dimension(self) -> int:
        """Return the embedding dimension size."""
        self._load_model()
        return self._dimension or 384  # Default for all-MiniLM-L6-v2

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model_name


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider using the OpenAI API.

    Uses text-embedding-3-small model by default, which provides
    high-quality embeddings suitable for semantic search.
    """

    DEFAULT_MODEL = "text-embedding-3-small"
    MAX_BATCH_SIZE = 2048  # OpenAI batch limit

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
    ) -> None:
        """Initialize the OpenAI embedding provider.

        Args:
            model: OpenAI embedding model to use
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)

        Raises:
            EmbeddingError: If API key is not provided
        """
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        self._dimension = OPENAI_MODEL_DIMENSIONS.get(model, 1536)

        if not self._api_key:
            raise EmbeddingError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.",
                code="MISSING_API_KEY",
                details={"provider": "openai"},
            )

    def _get_client(self):
        """Lazy load the OpenAI client."""
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
            return self._client
        except ImportError as e:
            raise EmbeddingError(
                "OpenAI package not installed. Install with: pip install openai",
                code="MISSING_DEPENDENCY",
                details={"package": "openai"},
            ) from e

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch of texts."""
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self._model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise self._map_error(e) from e

    def _map_error(self, error: Exception) -> EmbeddingError:
        """Map OpenAI exceptions to EmbeddingError."""
        try:
            import openai

            if isinstance(error, openai.AuthenticationError):
                return EmbeddingError(
                    f"OpenAI authentication failed: {error}",
                    code="AUTH_ERROR",
                    details={"provider": "openai", "original_error": str(error)},
                )
            elif isinstance(error, openai.RateLimitError):
                return EmbeddingError(
                    f"OpenAI rate limit exceeded: {error}",
                    code="RATE_LIMITED",
                    details={"provider": "openai", "original_error": str(error)},
                )
            elif isinstance(error, openai.APIConnectionError):
                return EmbeddingError(
                    f"OpenAI connection error: {error}",
                    code="NETWORK_ERROR",
                    details={"provider": "openai", "original_error": str(error)},
                )
            else:
                return EmbeddingError(
                    f"OpenAI API error: {error}",
                    code="API_ERROR",
                    details={"provider": "openai", "original_error": str(error)},
                )
        except ImportError:
            return EmbeddingError(
                f"OpenAI error: {error}",
                code="API_ERROR",
                details={"provider": "openai", "original_error": str(error)},
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API with automatic batching.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Split into batches if needed
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.MAX_BATCH_SIZE):
            batch = texts[i : i + self.MAX_BATCH_SIZE]
            batch_embeddings = self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    @property
    def dimension(self) -> int:
        """Return the embedding dimension size."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the model name."""
        return self._model


# Register providers
SUPPORTED_PROVIDERS["local"] = LocalEmbeddingProvider
SUPPORTED_PROVIDERS["openai"] = OpenAIEmbeddingProvider


def get_embedding_provider(
    provider: str = "local",
    model: str | None = None,
    api_key: str | None = None,
) -> EmbeddingProvider:
    """Factory function to get an embedding provider.

    Args:
        provider: Provider type (local, openai, etc.)
        model: Model name/identifier (uses provider default if not specified)
        api_key: API key for cloud providers

    Returns:
        EmbeddingProvider instance

    Raises:
        EmbeddingError: If provider is not supported
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise EmbeddingError(
            f"Unsupported embedding provider: {provider}",
            code="UNSUPPORTED_PROVIDER",
            details={"provider": provider, "supported": list(SUPPORTED_PROVIDERS.keys())},
        )

    # Use default model for provider if not specified
    if model is None:
        model = DEFAULT_MODELS.get(provider, "all-MiniLM-L6-v2")

    provider_class = SUPPORTED_PROVIDERS[provider]

    if provider == "local":
        return provider_class(model_name=model)
    elif provider == "openai":
        return provider_class(model=model, api_key=api_key)
    else:
        # Generic fallback for future providers
        return provider_class(model=model, api_key=api_key)
