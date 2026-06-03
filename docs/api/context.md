# Context API

The context API retrieves specification memory and optimizes it for an agent token budget.

Use it when you need to serve context to an agent through an API, MCP tool, web UI, or custom orchestration layer.

## Components

| Component | Purpose |
|-----------|---------|
| `TokenEstimator` | Counts tokens and estimates format overhead |
| `ContextOptimizer` | Sorts, truncates, and fits memory chunks into a budget |
| `ContextFormatter` | Formats optimized chunks as JSON, Markdown, or text |
| `ProfileManager` | Applies per-agent context preferences |
| `StreamingContextAPI` | Synchronous and async streaming context retrieval |

## Synchronous Context

```python
from specmem.context import StreamingContextAPI

api = StreamingContextAPI(memory_bank, default_budget=4000)

response = api.get_context(
    query="authentication requirements and impacted tests",
    token_budget=4000,
    format="markdown",
    top_k=20,
)

print(response.formatted_content)
print(response.total_tokens)
```

## Streaming Context

```python
from specmem.context import ContextChunk, StreamCompletion, StreamingContextAPI

api = StreamingContextAPI(memory_bank)

async for item in api.stream_query(
    "payment retry behavior",
    token_budget=3000,
    format="json",
    timeout_ms=1500,
):
    if isinstance(item, ContextChunk):
        print(item.text)
    elif isinstance(item, StreamCompletion):
        print(item.to_dict())
```

## Optimization Rules

The optimizer prioritizes:

1. pinned memory
2. higher relevance scores
3. complete chunks over truncated chunks
4. sentence-boundary truncation when a chunk is too large

The response includes:

| Field | Description |
|-------|-------------|
| `chunks` | Optimized context chunks |
| `total_tokens` | Token count after optimization |
| `token_budget` | Budget used for the request |
| `truncated_count` | Number of chunks shortened to fit |
| `formatted_content` | Rendered JSON, Markdown, or text payload |

## Agent Profiles

Pass `profile` to apply a stored agent profile:

```python
response = api.get_context(
    "database migration plan",
    profile="claude-code",
)
```

Profiles can set token budgets, preferred output format, and type filters. This lets different coding agents share the same memory bank while receiving context in the shape they work best with.
