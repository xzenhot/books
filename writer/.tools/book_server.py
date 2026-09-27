#!/usr/bin/env python3
"""Model Context Protocol (MCP) server exposing the Novelist book API.

Wraps ``.tools/lib/bookclient.py`` so the publish service's book/chapter
CRUD and publish features are available as MCP tools, without the caller
knowing the HTTP server details.

Run:
    python .tools/book_server.py

Configure as an MCP server in your editor (e.g. .tools/mcp-vscode.json).
The underlying HTTP service must be running first (see .tools/db/publish_api.py).
"""

import json
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from lib.bookclient import BookClient, PublishApiError

# Load .tools/.env next to this script if it exists.
SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)

mcp = FastMCP("novelist-book")

client = BookClient()


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def _handle(exc: Exception) -> str:
    """Convert a client error into a JSON string result."""
    return _json({"ok": False, "error": str(exc)})


# ---------------------------------------------------------------------------
# Book tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_book(
    book_name: str,
    form: str = "poetry",
    book_long_title: Optional[str] = None,
    language: Optional[str] = None,
    generic: Optional[str] = None,
    era: Optional[str] = None,
    target_audience: Optional[str] = None,
    gist: Optional[str] = None,
    book_summary: Optional[str] = None,
) -> str:
    """Create a new book (backlog artifacts + pipeline skeleton).

    Args:
        book_name: Logical book name (e.g. "mybook").
        form: "novel" or "poetry" (default "poetry").
        book_long_title: Optional display title.
        language: e.g. "English".
        generic: Genre.
        era: Time period.
        target_audience: Intended readership.
        gist: One-line premise.
        book_summary: 5-10 sentence outline.
    """
    try:
        result = client.create_book(
            book_name,
            form=form,
            book_long_title=book_long_title,
            language=language,
            generic=generic,
            era=era,
            target_audience=target_audience,
            gist=gist,
            book_summary=book_summary,
        )
        return _json(result)
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def get_book(book_name: str) -> str:
    """Return a book's plan (book.json)."""
    try:
        return _json(client.get_book(book_name))
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def edit_book(book_name: str, **fields: Any) -> str:
    """Update editable metadata on a book.

    Pass any subset of: book_long_title, form, language, generic, era,
    target_audience, gist, book_summary.
    """
    try:
        return _json(client.edit_book(book_name, **fields))
    except PublishApiError as exc:
        return _handle(exc)


# ---------------------------------------------------------------------------
# Chapter tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_chapters(book_name: str) -> str:
    """List all chapters in a book's plan."""
    try:
        return _json(client.list_chapters(book_name))
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def add_chapter(
    book_name: str,
    chapter_title: Optional[str] = None,
    chapter_summary: Optional[str] = None,
    chapter_index: Optional[int] = None,
    word_target: int = 500,
) -> str:
    """Add a chapter to a book's plan and scaffold its pipeline folder.

    Args:
        book_name: Logical book name.
        chapter_title: Optional chapter title (defaults to the index).
        chapter_summary: Optional short summary.
        chapter_index: Optional explicit index; defaults to next available.
        word_target: Target word count (default 500).
    """
    try:
        result = client.add_chapter(
            book_name,
            chapter_title=chapter_title,
            chapter_summary=chapter_summary,
            chapter_index=chapter_index,
            word_target=word_target,
        )
        return _json(result)
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def get_chapter(book_name: str, chapter: str) -> str:
    """Return a chapter's metadata (model.json).

    Args:
        book_name: Logical book name.
        chapter: Chapter index/name (e.g. "1").
    """
    try:
        return _json(client.get_chapter(book_name, chapter))
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def get_chapter_content(book_name: str, chapter: str) -> str:
    """Return a chapter's written content (chapter.md)."""
    try:
        return client.get_chapter_content(book_name, chapter)
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def edit_chapter(book_name: str, chapter: str, **fields: Any) -> str:
    """Update a chapter's metadata and/or content.

    Pass any subset of: chapter_title, chapter_summary, word_target, content.
    """
    try:
        return _json(client.edit_chapter(book_name, chapter, **fields))
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def delete_chapter(book_name: str, chapter: str) -> str:
    """Delete a chapter from the plan and its pipeline folder."""
    try:
        client.delete_chapter(book_name, chapter)
        return _json({"ok": True, "deleted": chapter})
    except PublishApiError as exc:
        return _handle(exc)


# ---------------------------------------------------------------------------
# Version / publish tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_versions(book_name: str) -> str:
    """List a book's published version folders."""
    try:
        return _json(client.list_versions(book_name))
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def get_chapter_content_by_version(
    book_name: str, version: str, chapter: str
) -> str:
    """Return a chapter's content from a specific published version."""
    try:
        return client.get_chapter_content_by_version(book_name, version, chapter)
    except PublishApiError as exc:
        return _handle(exc)


@mcp.tool()
def publish(book_name: str, language: Optional[str] = None) -> str:
    """Publish a book to a new versioned folder under source/books/.

    Args:
        book_name: Logical book name.
        language: Optional language to publish translator-stage segments.
    """
    try:
        return _json(client.publish(book_name, language))
    except PublishApiError as exc:
        return _handle(exc)


if __name__ == "__main__":
    mcp.run()
