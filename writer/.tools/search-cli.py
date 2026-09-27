#!/usr/bin/env python3
"""CLI wrapper around the novelist search adapter.

Usage:
    python search-cli.py "your query" [--backend searxng] [--max 5] [--engines wikipedia]

This is useful for invoking the same search providers from any terminal,
including GitHub Copilot CLI suggested commands, without needing a full
MCP client host.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from search.adapter import build_adapter
from search.schema import SearchResponse

# Load .tools/.env next to this script if it exists.
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search the web using a configured provider adapter.",
    )
    parser.add_argument("query", help="Search query string.")
    parser.add_argument(
        "--backend",
        default=os.getenv("DEFAULT_SEARCH_PROVIDER", "searxng"),
        help="Search provider to use (default: searxng).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=5,
        dest="max_results",
        help="Maximum number of results to return (default: 5).",
    )
    parser.add_argument(
        "--engines",
        nargs="+",
        default=None,
        help="SearXNG engine list, e.g. wikipedia google.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    adapter = build_adapter()
    kwargs: dict = {}
    if args.engines:
        if args.backend.lower() != "searxng":
            print(
                "error: --engines is only supported for the 'searxng' backend.",
                file=sys.stderr,
            )
            return 1
        kwargs["engines"] = args.engines

    results = adapter.search(
        provider_name=args.backend,
        query=args.query,
        max_results=args.max_results,
        **kwargs,
    )
    response = SearchResponse.from_results(query=args.query, results=results)

    indent = 2 if args.pretty else None
    print(response.model_dump_json(indent=indent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
