"""Internet search adapter package for the novelist MCP server."""

from .adapter import SearchAdapter, SearchProvider
from .schema import SearchResponse, SearchResult

__all__ = [
    "SearchAdapter",
    "SearchProvider",
    "SearchResponse",
    "SearchResult",
]
