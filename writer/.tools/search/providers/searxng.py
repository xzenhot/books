"""SearXNG search provider adapter."""

import os
from typing import Any, List, Optional

import requests

from ..adapter import SearchProvider
from ..schema import SearchResult


class SearxngProvider(SearchProvider):
    """Adapter for a self-hosted or public SearXNG instance."""

    name = "searxng"

    def __init__(self, base_url: Optional[str] = None) -> None:
        if base_url is None:
            base_url = os.environ.get(
                "SEARCHXNG_DEV_URL", os.environ.get("SEARCHXNG_URL", "")
            )
        self.base_url = base_url.rstrip("/")

    def search(
        self,
        query: str,
        max_results: int,
        engines: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[SearchResult]:
        """Run a SearXNG search and normalize results to the common schema."""
        if not self.base_url:
            raise ValueError(
                "SearXNG provider requires SEARCHXNG_DEV_URL/SEARCHXNG_URL "
                "to be set, or a base_url argument."
            )

        url = f"{self.base_url}/search"
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }
        if engines:
            params["engines"] = ",".join(engines)
        else:
            params["disabled_engines"] = "none"

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        raw = response.json()

        results: List[SearchResult] = []
        for rank, item in enumerate(raw.get("results", [])[:max_results], start=1):
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled"),
                    url=item.get("url", ""),
                    snippet=item.get("content", item.get("abstract", "")),
                    source=self.name,
                    published=item.get("publishedDate") or None,
                    rank=rank,
                )
            )
        return results
