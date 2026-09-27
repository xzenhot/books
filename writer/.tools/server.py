#!/usr/bin/env python3
"""A standard Model Context Protocol (MCP) server in Python.

Exposes a uniform `search` tool backed by a configurable adapter of internet
search providers. SearXNG is the default provider.
"""

import json
import os
from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from search.adapter import SearchAdapter, build_adapter
from search.schema import SearchResponse

# Load .tools/.env next to this script if it exists.
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)

# Initialize the server
mcp = FastMCP("novelist-search")

# ---------------------------------------------------------------------------
# Adapter setup
# ---------------------------------------------------------------------------
adapter: SearchAdapter = build_adapter()
DEFAULT_PROVIDER = os.getenv("DEFAULT_SEARCH_PROVIDER", "searxng").lower()

# ---------------------------------------------------------------------------
# Load external schema
# ---------------------------------------------------------------------------
SCHEMA_PATH = SCRIPT_DIR / "search-response-schema.json"


def _load_schema() -> dict[str, Any]:
    """Load the uniform search-response JSON schema from disk."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Search response schema not found at {SCHEMA_PATH}. "
            "Please regenerate it or place it next to this script."
        )
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


SEARCH_RESPONSE_JSON_SCHEMA: dict[str, Any] = _load_schema()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def search(
    query: str,
    max_results: int = 5,
    backend: Optional[str] = None,
    engines: Optional[List[str]] = None,
) -> str:
    """Search the web and return results in a uniform JSON schema.

    Args:
        query: The search query.
        max_results: Maximum number of results to return (default 5).
        backend: Search provider to use. Defaults to the value of the
            DEFAULT_SEARCH_PROVIDER environment variable, or 'searxng' if unset.
            Available providers are discovered from .tools/search/providers/.
        engines: Optional list of SearXNG engines to use (e.g. ['wikipedia',
            'google']). When omitted, SearXNG uses its default engine set.
            Use this to skip problematic engines such as DuckDuckGo.
            Only applies to the 'searxng' provider.

    Returns:
        A JSON string conforming to the SearchResponse schema.
    """
    selected = (backend or DEFAULT_PROVIDER).lower()

    if engines and selected != "searxng":
        raise ValueError("'engines' is only supported for the 'searxng' provider")

    kwargs: dict[str, Any] = {}
    if selected == "searxng":
        kwargs["engines"] = engines

    results = adapter.search(
        provider_name=selected,
        query=query,
        max_results=max_results,
        **kwargs,
    )

    response = SearchResponse.from_results(query=query, results=results)
    return response.model_dump_json(indent=2)


@mcp.tool()
def calculate_reading_time(word_count: int, wpm: int = 200) -> float:
    """Calculate the estimated reading time in minutes for a given word count.

    Args:
        word_count: Total number of words in the text.
        wpm: Words read per minute (default is 200).
    """
    if word_count < 0:
        raise ValueError("Word count must be non-negative.")
    return round(word_count / wpm, 2)


@mcp.tool()
def format_quote(author: str, quote: str) -> str:
    """Format an author attribution and quote in Markdown blockquote style."""
    return f'> "{quote.strip()}"\n>\n> — *{author.strip()}*'


@mcp.resource("config://app-settings")
def get_app_settings() -> dict:
    """Expose application configuration settings."""
    return {
        "version": "2.0.0",
        "environment": "development",
        "supported_formats": ["markdown", "json", "txt"],
        "default_search_provider": DEFAULT_PROVIDER,
        "configured_providers": adapter.list_providers(),
        "search_response_schema": SEARCH_RESPONSE_JSON_SCHEMA,
    }


@mcp.prompt()
def critique_draft(draft_text: str) -> str:
    """Prompt template for critiquing draft content."""
    return f"""Please review the following draft text for clarity, tone, and pacing:

{draft_text}

Provide three concrete suggestions for improvement."""


if __name__ == "__main__":
    # Stdio servers communicate via JSON-RPC over stdout.
    # Never use unredirected print() statements, as they corrupt stdout frames.
    mcp.run()
