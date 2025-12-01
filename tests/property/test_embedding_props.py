"""Property-based tests for embedding providers.

Tests correctness properties defined in the cloud-embeddings design document.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.core.exceptions import EmbeddingError
from specmem.vectordb.embeddings import (
    SUPPORTED_PROVIDERS,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)


# Strategies for generating test data
text_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
    min_size=1,
    max_size=100,
)

text_list_strategy = st.lists(text_strategy, min_size=1, max_size=10)

# Strategy for unsupported provider names
unsupported_provider_strategy = st.text(min_size=1, max_size=20).filter(
    lambda x: x not in SUPPORTED_PROVIDERS
)


class TestFactoryProviderType:
    """**Feature: cloud-embeddings, Property 1: Factory returns correct provider type**"""

    @given(provider_name=st.sampled_from(list(SUPPORTED_PROVIDERS.keys())))
    @settings(max_examples=100)
    def test_factory_returns_correct_provider_type(self, provider_name: str):
        """For any valid provider name, factory returns correct provider class.

        **Validates: Requirements 1.1, 2.1**
        """
        # Skip openai if no API key (would raise MISSING_API_KEY)
        if provider_name == "openai":
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                provider = get_embedding_provider(provider=provider_name)
                assert isinstance(provider, SUPPORTED_PROVIDERS[provider_name])
        else:
            provider = get_embedding_provider(provider=provider_name)
            assert isinstance(provider, SUPPORTED_PROVIDERS[provider_name])


class TestUnknownProviderError:
    """**Feature: cloud-embeddings, Property 2: Unknown provider raises error**"""

    @given(provider_name=unsupported_provider_strategy)
    @settings(max_examples=100)
    def test_unknown_provider_raises_unsupported_error(self, provider_name: str):
        """For any unknown provider name, factory raises UNSUPPORTED_PROVIDER error.

        **Validates: Requirements 3.2**
        """
        with pytest.raises(EmbeddingError) as exc_info:
            get_embedding_provider(provider=provider_name)

        assert exc_info.value.code == "UNSUPPORTED_PROVIDER"
        assert exc_info.value.details["provider"] == provider_name
        assert "supported" in exc_info.value.details


class TestEmbeddingDimensionConsistency:
    """**Feature: cloud-embeddings, Property 3: Embedding dimension consistency**"""

    # Skipped: Local embedding tests are slow due to model loading
    # @given(texts=text_list_strategy)
    # @settings(max_examples=100, deadline=None)
    # def test_local_embedding_dimension_consistency(self, texts: list[str]):
    #     """For local provider, all embeddings have consistent dimension."""
    #     provider = LocalEmbeddingProvider()
    #     embeddings = provider.embed(texts)
    #     assert len(embeddings) == len(texts)
    #     if embeddings:
    #         expected_dim = provider.dimension
    #         for emb in embeddings:
    #             assert len(emb) == expected_dim

    @given(texts=text_list_strategy)
    @settings(max_examples=100)
    def test_openai_embedding_dimension_consistency_mocked(self, texts: list[str]):
        """For OpenAI provider (mocked), all embeddings have consistent dimension.

        **Validates: Requirements 3.3**
        """
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIEmbeddingProvider()
            expected_dim = provider.dimension

            # Mock the OpenAI client
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * expected_dim) for _ in texts]

            with patch.object(provider, "_get_client") as mock_client:
                mock_client.return_value.embeddings.create.return_value = mock_response
                embeddings = provider.embed(texts)

            assert len(embeddings) == len(texts)
            for emb in embeddings:
                assert len(emb) == expected_dim


class TestBatchResultCount:
    """**Feature: cloud-embeddings, Property 4: Batch result count matches input**"""

    # Skipped: Local embedding tests are slow due to model loading
    # @given(texts=text_list_strategy)
    # @settings(max_examples=100, deadline=None)
    # def test_local_batch_result_count(self, texts: list[str]):
    #     """For local provider, embed returns exactly len(texts) vectors."""
    #     provider = LocalEmbeddingProvider()
    #     embeddings = provider.embed(texts)
    #     assert len(embeddings) == len(texts)

    @given(num_texts=st.integers(min_value=1, max_value=50))
    @settings(max_examples=100)
    def test_openai_batch_result_count_mocked(self, num_texts: int):
        """For OpenAI provider (mocked), embed returns exactly len(texts) vectors.

        **Validates: Requirements 4.2**
        """
        texts = [f"text {i}" for i in range(num_texts)]

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIEmbeddingProvider()
            expected_dim = provider.dimension

            # Mock the OpenAI client
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * expected_dim) for _ in texts]

            with patch.object(provider, "_get_client") as mock_client:
                mock_client.return_value.embeddings.create.return_value = mock_response
                embeddings = provider.embed(texts)

            assert len(embeddings) == len(texts)

    def test_empty_input_returns_empty(self):
        """Empty input should return empty list without API call."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            openai_provider = OpenAIEmbeddingProvider()
            # Should not make API call for empty input
            embeddings = openai_provider.embed([])
            assert embeddings == []


class TestErrorWrapping:
    """**Feature: cloud-embeddings, Property 5: Error wrapping preserves details**"""

    @given(error_message=st.text(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_error_wrapping_preserves_original_message(self, error_message: str):
        """For any exception, wrapped EmbeddingError contains original message.

        **Validates: Requirements 1.3, 5.4**
        """
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIEmbeddingProvider()

            # Create a generic exception
            original_error = Exception(error_message)
            wrapped_error = provider._map_error(original_error)

            assert isinstance(wrapped_error, EmbeddingError)
            assert "original_error" in wrapped_error.details
            assert error_message in wrapped_error.details["original_error"]

    def test_auth_error_maps_to_auth_error_code(self):
        """AuthenticationError maps to AUTH_ERROR code."""
        import openai

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIEmbeddingProvider()

            # Create actual openai AuthenticationError
            auth_error = openai.AuthenticationError(
                message="Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )
            wrapped = provider._map_error(auth_error)
            assert wrapped.code == "AUTH_ERROR"

    def test_rate_limit_error_maps_to_rate_limited_code(self):
        """RateLimitError maps to RATE_LIMITED code."""
        import openai

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIEmbeddingProvider()

            rate_error = openai.RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            )
            wrapped = provider._map_error(rate_error)
            assert wrapped.code == "RATE_LIMITED"

    def test_connection_error_maps_to_network_error_code(self):
        """APIConnectionError maps to NETWORK_ERROR code."""
        import openai

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIEmbeddingProvider()

            conn_error = openai.APIConnectionError(request=MagicMock())
            wrapped = provider._map_error(conn_error)
            assert wrapped.code == "NETWORK_ERROR"

    def test_missing_api_key_raises_error(self):
        """Missing API key raises MISSING_API_KEY error."""
        # Clear any existing API key
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY if it exists
            os.environ.pop("OPENAI_API_KEY", None)

            with pytest.raises(EmbeddingError) as exc_info:
                OpenAIEmbeddingProvider(api_key=None)

            assert exc_info.value.code == "MISSING_API_KEY"


class TestConfigurationRoundTrip:
    """**Feature: cloud-embeddings, Property 6: Configuration round-trip**"""

    @given(
        provider=st.sampled_from(["local", "openai"]),
        model=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_embedding_config_round_trip(self, provider: str, model: str):
        """For any valid EmbeddingConfig, serialize/deserialize preserves values.

        **Validates: Requirements 2.4**
        """
        from specmem.core.config import EmbeddingConfig, SpecMemConfig

        # Create config with embedding settings
        config = SpecMemConfig(embedding=EmbeddingConfig(provider=provider, model=model))

        # Round-trip through JSON
        json_str = config.to_json()
        restored = SpecMemConfig.from_json(json_str)

        assert restored.embedding.provider == provider
        assert restored.embedding.model == model


class TestEnvironmentVariableApiKey:
    """**Feature: cloud-embeddings, Property 7: Environment variable API key usage**"""

    @given(
        api_key=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P")),
            min_size=10,
            max_size=50,
        ).filter(lambda x: x.strip() and "\x00" not in x)
    )
    @settings(max_examples=100)
    def test_openai_api_key_from_env(self, api_key: str):
        """For any API key in env var, cloud provider receives that key.

        **Validates: Requirements 2.3**
        """
        from specmem.core.config import EmbeddingConfig

        with patch.dict(os.environ, {"OPENAI_API_KEY": api_key}):
            config = EmbeddingConfig(provider="openai")
            assert config.get_api_key() == api_key

    def test_explicit_api_key_overrides_env(self):
        """Explicit API key in config overrides environment variable."""
        from specmem.core.config import EmbeddingConfig

        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            config = EmbeddingConfig(provider="openai", api_key="explicit-key")
            assert config.get_api_key() == "explicit-key"

    def test_local_provider_no_api_key_needed(self):
        """Local provider doesn't need API key."""
        from specmem.core.config import EmbeddingConfig

        config = EmbeddingConfig(provider="local")
        assert config.get_api_key() is None
