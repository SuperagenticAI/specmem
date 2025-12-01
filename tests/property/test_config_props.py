"""Property-based tests for Configuration models.

These tests use Hypothesis to verify universal properties that should hold
across all valid configuration inputs.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.core.config import EmbeddingConfig, SpecMemConfig, VectorDBConfig


# Strategies for generating valid config data
embedding_provider_strategy = st.sampled_from(
    ["local", "openai", "anthropic", "gemini", "together"]
)
vectordb_backend_strategy = st.sampled_from(
    ["lancedb", "agentvectordb", "chroma", "qdrant", "sqlite-vec"]
)

# Model names (non-empty strings)
model_name_strategy = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Paths (non-empty strings)
path_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())

# Adapter names
adapter_strategy = st.lists(
    st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    min_size=1,
    max_size=10,
)

# Optional API keys
api_key_strategy = st.one_of(
    st.none(),
    st.text(min_size=10, max_size=100).filter(lambda x: x.strip()),
)


@st.composite
def valid_embedding_config_strategy(draw: st.DrawFn) -> EmbeddingConfig:
    """Generate valid EmbeddingConfig instances."""
    return EmbeddingConfig(
        provider=draw(embedding_provider_strategy),
        model=draw(model_name_strategy),
        api_key=draw(api_key_strategy),
    )


@st.composite
def valid_vectordb_config_strategy(draw: st.DrawFn) -> VectorDBConfig:
    """Generate valid VectorDBConfig instances."""
    return VectorDBConfig(
        backend=draw(vectordb_backend_strategy),
        path=draw(path_strategy),
        agentvectordb_api_key=draw(api_key_strategy),
        agentvectordb_endpoint=draw(api_key_strategy),  # Reuse for endpoint
    )


@st.composite
def valid_specmem_config_strategy(draw: st.DrawFn) -> SpecMemConfig:
    """Generate valid SpecMemConfig instances."""
    return SpecMemConfig(
        embedding=draw(valid_embedding_config_strategy()),
        vectordb=draw(valid_vectordb_config_strategy()),
        adapters=draw(adapter_strategy),
    )


# Feature: specmem-mvp, Property 9: Configuration Validation
# Validates: Requirements 11.1, 11.5
@given(config=valid_specmem_config_strategy())
@settings(max_examples=100)
def test_config_serialization_roundtrip(config: SpecMemConfig) -> None:
    """For any valid configuration, serializing to JSON and deserializing back
    SHALL produce equivalent configuration values.
    """
    # Serialize to JSON
    json_str = config.to_json()

    # Deserialize back
    restored = SpecMemConfig.from_json(json_str)

    # Verify all fields are equivalent
    assert restored.embedding.provider == config.embedding.provider
    assert restored.embedding.model == config.embedding.model
    assert restored.embedding.api_key == config.embedding.api_key

    assert restored.vectordb.backend == config.vectordb.backend
    assert restored.vectordb.path == config.vectordb.path
    assert restored.vectordb.agentvectordb_api_key == config.vectordb.agentvectordb_api_key
    assert restored.vectordb.agentvectordb_endpoint == config.vectordb.agentvectordb_endpoint

    assert restored.adapters == config.adapters


@given(embedding_config=valid_embedding_config_strategy())
@settings(max_examples=100)
def test_embedding_config_roundtrip(embedding_config: EmbeddingConfig) -> None:
    """EmbeddingConfig should survive JSON round-trip."""
    json_str = embedding_config.model_dump_json()
    restored = EmbeddingConfig.model_validate_json(json_str)

    assert restored.provider == embedding_config.provider
    assert restored.model == embedding_config.model
    assert restored.api_key == embedding_config.api_key


@given(vectordb_config=valid_vectordb_config_strategy())
@settings(max_examples=100)
def test_vectordb_config_roundtrip(vectordb_config: VectorDBConfig) -> None:
    """VectorDBConfig should survive JSON round-trip."""
    json_str = vectordb_config.model_dump_json()
    restored = VectorDBConfig.model_validate_json(json_str)

    assert restored.backend == vectordb_config.backend
    assert restored.path == vectordb_config.path
    assert restored.agentvectordb_api_key == vectordb_config.agentvectordb_api_key
    assert restored.agentvectordb_endpoint == vectordb_config.agentvectordb_endpoint


def test_default_config_values() -> None:
    """Default configuration should have expected values."""
    config = SpecMemConfig()

    assert config.embedding.provider == "local"
    assert config.embedding.model == "all-MiniLM-L6-v2"
    assert config.embedding.api_key is None

    assert config.vectordb.backend == "lancedb"
    assert config.vectordb.path == ".specmem/vectordb"

    assert config.adapters == ["kiro"]
