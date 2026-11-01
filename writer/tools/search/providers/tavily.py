"""Tavily search provider adapter."""

import os
from typing import Any, List, Optional

from ..adapter import SearchProvider
from ..schema import SearchResult


class TavilyProvider(SearchProvider):
    """Adapter for the Tavily search API."""

    name = "tavily"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY", "")

    def search(
        self,
        query: str,
        max_results: int,
        **kwargs: Any,
    ) -> List[SearchResult]:
        """Run a Tavily search and normalize results to the common schema."""
        if not self.api_key:
            raise ValueError(
                "Tavily provider requested but TAVILY_API_KEY is not set."
            )

        try:
            from tavily import TavilyClient
        except ImportError as exc:
            raise ImportError(
                "Tavily provider requires the 'tavily' package to be installed."
            ) from exc

        client = TavilyClient(api_key=self.api_key)
        raw = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_raw_content=False,
        )

        results: List[SearchResult] = []
        for rank, item in enumerate(raw.get("results", []), start=1):
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled"),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=self.name,
                    published=item.get("published_date") or None,
                    rank=rank,
                )
            )
        return results
