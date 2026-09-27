# Internet Search MCP server adapter

This package implements an **adapter-pattern** internet search layer used by the novelist MCP server. It lets callers use a single `search` tool while switching between multiple search providers.

## Default provider

SearXNG is the default provider.

## Supported providers

| Provider  | Env variable(s)                              | Notes                                              |
|-----------|----------------------------------------------|----------------------------------------------------|
| searxng   | `SEARCHXNG_DEV_URL` or `SEARCHXNG_URL`      | Self-hosted or public SearXNG instance             |
| brave     | `BRAVE_API_KEY`                              | Free tier at https://api.search.brave.com/         |
| tavily    | `TAVILY_API_KEY`                             | Requires `tavily` Python package                   |

## How it works

- `search/adapter.py` defines `SearchProvider` (abstract) and `SearchAdapter` (registry/dispatcher).
- `search/providers/*.py` contain concrete provider adapters.
- `SearchAdapter` auto-discovers provider classes in `search/providers/`.
- `server.py` exposes the MCP `search` tool and dispatches through the adapter.

## Adding a new provider

1. Create `search/providers/<name>.py`.
2. Subclass `SearchProvider` and set `name = "<name>"`.
3. Implement `search(query, max_results, **kwargs) -> List[SearchResult]`.
4. The adapter will discover it automatically on the next server start.

## Configuration

Set `DEFAULT_SEARCH_PROVIDER` in `.tools/.env` to change the default. The `backend` argument on the `search` tool overrides it per-call.
