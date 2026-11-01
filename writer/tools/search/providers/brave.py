"""Brave Search API provider adapter."""

import os
from typing import Any, List, Optional

import requests

from ..adapter import SearchProvider
from ..schema import SearchResult


class BraveProvider(SearchProvider):
    """Adapter for the Brave Search API.

    Free tier: 2,000 queries/month at the time of writing.
    Requires BRAVE_API_KEY in the environment.
    """

    name = "brave"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("BRAVE_API_KEY", "")

    def search(
        self,
        query: str,
        max_results: int,
        **kwargs: Any,
    ) -> List[SearchResult]:
        """Run a Brave Search API query and normalize results."""
        if not self.api_key:
            raise ValueError(
                "Brave provider requested but BRAVE_API_KEY is not set. "
                "Get a free key at https://api.search.brave.com/"
            )

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": min(max_results, 20),
            "offset": 0,
            "mkt": "en-US",
        }

        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        raw = response.json()

        results: List[SearchResult] = []
        for rank, item in enumerate(
            raw.get("web", {}).get("results", [])[:max_results], start=1
        ):
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled"),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source=self.name,
                    published=item.get("age") or None,
                    rank=rank,
                )
            )
        return results
