#!/usr/bin/env python3
"""config.py — Edit book.json attributes at the book level and chapter level.

Sets top-level attributes on the book plan and per-chapter attributes on the
`chapters[]` entries, writing the result back to `book.json` atomically.

USAGE
-----
    python tools/config.py <bookname> book <attr>=<value> [<attr>=<value> ...]
    python tools/config.py <bookname> chapter <range> <attr>=<value> [<attr>=<value> ...]

The two clauses may be combined in one invocation:

    python tools/config.py <bookname> book <attr>=<value> chapter <range> <attr>=<value>

<bookname>  Logical book name, e.g. `fresco`.
<range>     `*` | `all` | `<n>` | `<n>-<m>` | `<n>,<m>,...` — selects chapters by name.
<attr>=<value>  A key and its new value. Values are parsed as JSON when
            possible (so `500` becomes an int, `true` a bool, `["a","b"]` a
            list); anything unparseable is kept as a plain string.

EXAMPLES
--------
    python tools/config.py fresco book form=novel language=Bengali
    python tools/config.py fresco chapter 1-5 word_target=800
    python tools/config.py fresco chapter all chapter_title="The Wall"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
PIPELINE_ROOT = REPO_ROOT / "workspaces" / "pipeline"
BACKLOG_ROOT = REPO_ROOT / "workspaces" / "backlog"


def validate_bookname(bookname: str) -> str:
    if not bookname or "/" in bookname or "\\" in bookname:
        raise ValueError(f"Invalid book name: {bookname!r}")
    return bookname


def resolve_book_json(bookname: str) -> Path:
    """Resolve the book plan to edit: pipeline first, then backlog."""
    for root in (PIPELINE_ROOT, BACKLOG_ROOT):
        candidate = root / bookname / "book.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"No book.json found for {bookname!r} in pipeline or backlog.\n"
        "Run scaffold first: python tools/book.py <bookname> scaffold"
    )


def coerce_value(raw: str):
    """Parse a value token as JSON when possible, else keep it as a string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def parse_assignment(token: str) -> tuple[str, object]:
    if "=" not in token:
        raise ValueError(f"Expected '<attr>=<value>', got {token!r}")
    key, value = token.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Empty attribute name in {token!r}")
    return key, coerce_value(value.strip())


def parse_range(target: str, chapters: list[dict]) -> list[int]:
    """Resolve a chapter range token into indices into the `chapters` list."""
    by_name = {str(c.get("name")): i for i, c in enumerate(chapters)}

    if target in ("*", "all"):
        return list(range(len(chapters)))

    if "," in target:
        indices: list[int] = []
        for part in target.split(","):
            indices.extend(parse_range(part.strip(), chapters))
        return sorted(set(indices))

    if "-" in target:
        start_s, end_s = target.split("-", 1)
        start, end = int(start_s), int(end_s)
        if start > end:
            start, end = end, start
        numeric = sorted(
            (name for name in by_name if name.isdigit()),
            key=lambda name: int(name),
        )
        return [by_name[name] for name in numeric if start <= int(name) <= end]

    if target in by_name:
        return [by_name[target]]

    raise ValueError(f"Unknown chapter: {target!r}")


def apply_book(book: dict, assignments: list[str]) -> list[str]:
    for token in assignments:
        key, value = parse_assignment(token)
        book[key] = value
    return [parse_assignment(t)[0] for t in assignments]


def apply_chapter(book: dict, target: str, assignments: list[str]) -> tuple[list[int], list[str]]:
    chapters = book.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("book.json has no 'chapters' array")
    indices = parse_range(target, chapters)
    keys: list[str] = []
    for token in assignments:
        key, value = parse_assignment(token)
        keys.append(key)
        for i in indices:
            chapters[i][key] = value
    return indices, keys


def chapter_metadata_file(bookname: str, name: str) -> Path | None:
    """Resolve a chapter's runtime metadata file (chapter.json, else model.json)."""
    chapter_dir = PIPELINE_ROOT / bookname / "chapters" / str(name)
    for candidate in ("chapter.json", "model.json"):
        path = chapter_dir / candidate
        if path.exists():
            return path
    return None


def sync_chapter_models(bookname: str, chapters: list[dict], indices: list[int], assignments: list[str]) -> int:
    """Write the same assignments into each selected chapter's runtime metadata file.

    Mirrors the book.json `chapters[]` edit into `chapters/<name>/chapter.json`
    (falling back to `model.json`) so the per-chapter runtime file stays in sync.
    Returns the number of chapter metadata files updated.
    """
    updated = 0
    for i in indices:
        entry = chapters[i]
        name = entry.get("name")
        if name is None:
            continue
        path = chapter_metadata_file(bookname, name)
        if path is None:
            continue
        model = json.loads(path.read_text(encoding="utf-8-sig"))
        for token in assignments:
            key, value = parse_assignment(token)
            model[key] = value
        path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        updated += 1
    return updated


def parse_args(argv: list[str]) -> tuple[str, list[tuple[str, object]]]:
    """Parse the argument sequence into (bookname, clauses).

    A clause is ("book", [assignments...]) or ("chapter", range, [assignments...]).
    """
    if not argv:
        raise ValueError("Missing bookname")

    bookname = validate_bookname(argv[0])
    tokens = argv[1:]
    clauses: list[tuple[str, object]] = []

    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == "book":
            i += 1
            assignments = []
            while i < len(tokens) and tokens[i] != "chapter":
                assignments.append(tokens[i])
                i += 1
            if not assignments:
                raise ValueError("'book' clause requires at least one <attr>=<value>")
            clauses.append(("book", assignments))
        elif token == "chapter":
            i += 1
            if i >= len(tokens):
                raise ValueError("'chapter' clause requires a <range> and <attr>=<value>")
            target = tokens[i]
            i += 1
            assignments = []
            while i < len(tokens) and tokens[i] != "book":
                assignments.append(tokens[i])
                i += 1
            if not assignments:
                raise ValueError("'chapter' clause requires at least one <attr>=<value>")
            clauses.append(("chapter", target, assignments))
        else:
            raise ValueError(f"Unknown clause token: {token!r}")

    if not clauses:
        raise ValueError("No 'book' or 'chapter' clause provided")

    return bookname, clauses


def run(bookname: str, clauses: list[tuple[str, object]]) -> None:
    book_path = resolve_book_json(bookname)
    book = json.loads(book_path.read_text(encoding="utf-8-sig"))

    for clause in clauses:
        kind = clause[0]
        if kind == "book":
            assignments = clause[1]
            keys = apply_book(book, assignments)
            print(f"book: set {', '.join(keys)}")
        elif kind == "chapter":
            _, target, assignments = clause
            indices, keys = apply_chapter(book, target, assignments)
            synced = sync_chapter_models(bookname, book["chapters"], indices, assignments)
            print(f"chapter {target}: set {', '.join(keys)} on {len(indices)} chapter(s)"
                  f" | synced {synced} chapter metadata file(s)")

    # Write atomically
    book_path.write_text(json.dumps(book, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {book_path}")


def main() -> int:
    try:
        bookname, clauses = parse_args(sys.argv[1:])
        run(bookname, clauses)
        return 0
    except (FileNotFoundError, RuntimeError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
