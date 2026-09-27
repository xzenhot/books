# Novelist Search MCP Server

A Model Context Protocol (MCP) server that exposes a single, uniform `search` tool backed by multiple internet search providers.

## Quick start

Run the server directly:

```bash
cd .tools
python server.py
```

Or connect it as an MCP client in your editor using one of the provided config files:

- `mcp-vscode.json` — VS Code
- `mcp-claude.json` — Claude Desktop
- `mcp-codex.json` — Codex / other MCP hosts

## Architecture

- `server.py` — thin MCP server entrypoint.
- `search/adapter.py` — orchestrator: `SearchProvider` interface and `SearchAdapter` registry.
- `search/providers/*.py` — one concrete adapter per search provider.
- `search/schema.py` — shared `SearchResult` / `SearchResponse` Pydantic schema.

## Default provider

SearXNG is the default provider.

## Supported providers

| Provider  | Env variable(s)                            | Notes                                              |
|-----------|--------------------------------------------|----------------------------------------------------|
| searxng   | `SEARCHXNG_DEV_URL` or `SEARCHXNG_URL`    | Self-hosted or public SearXNG instance               |
| brave     | `BRAVE_API_KEY`                            | Free tier at https://api.search.brave.com/           |
| tavily    | `TAVILY_API_KEY`                           | Requires the `tavily` Python package               |

## Configuration

Create or edit `.tools/.env`:

```dotenv
# Default provider used when the caller does not pass 'backend'
DEFAULT_SEARCH_PROVIDER=searxng

# Provider-specific credentials
SEARCHXNG_DEV_URL=http://localhost:8080/
# BRAVE_API_KEY=your_key
# TAVILY_API_KEY=your_key
```

You can override the provider per-call via the `backend` argument of the `search` tool.

## Tools

- `search(query, max_results=5, backend=None, engines=None)` — web search returning uniform JSON.
- `calculate_reading_time(word_count, wpm=200)` — estimate reading time.
- `format_quote(author, quote)` — format a Markdown blockquote.

## Testing

Run the stdio smoke test:

```bash
cd .tools
python test_searxng_client.py
```

## CLI usage

You can also call the search adapter directly from any terminal without an MCP host:

```bash
cd .tools
python search-cli.py "Bengal famine 1943" --backend searxng --max 3 --pretty
```

This is useful when GitHub Copilot CLI suggests search commands, or when you want to pipe search JSON into other shell tools.

## Adding a new provider

1. Add a file under `search/providers/<name>.py`.
2. Subclass `SearchProvider` and set `name = "<name>"`.
3. Implement `search(query, max_results, **kwargs) -> List[SearchResult]`.
4. Restart the server. The orchestrator auto-discovers the new provider.

See `search/README.md` for more provider-adapter details.
