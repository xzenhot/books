"""Uniform search-result schema shared across all search providers."""

from datetime import datetime, timezone
from typing import Any, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class SearchResult(BaseModel):
    """A single search result returned by any provider.

    All fields follow a fixed schema so callers can consume results from
    different backends without changing their parser.
    """

    title: str = Field(description="The title of the result.")
    url: HttpUrl = Field(description="The canonical URL of the result.")
    snippet: str = Field(
        description="A plain-text summary or excerpt of the result content."
    )
    source: str = Field(
        default="unknown",
        description="The search backend or source that produced the result.",
    )
    published: Optional[str] = Field(
        default=None,
        description="Publication date in ISO-8601 format, if known.",
    )
    rank: Optional[int] = Field(
        default=None,
        description="The rank/order of this result in the result set.",
    )


class SearchResponse(BaseModel):
    """The uniform response envelope for any search operation."""

    query: str = Field(description="The original search query.")
    results: List[SearchResult] = Field(
        default_factory=list,
        description="List of search results matching the uniform schema.",
    )
    total: int = Field(
        default=0,
        description="Number of results returned in this response.",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO-8601 timestamp of when the response was generated.",
    )

    @classmethod
    def from_results(
        cls,
        query: str,
        results: List[SearchResult],
    ) -> "SearchResponse":
        """Build a response from a list of already-normalized results."""
        return cls(
            query=query,
            results=results,
            total=len(results),
        )
