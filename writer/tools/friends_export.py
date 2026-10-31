#!/usr/bin/env python3
"""
friends_export.py — read a friend list out of a Facebook "Download Your Information" export.

Facebook removed API access to a user's friend list in 2018 (`/me/friends`
returns only friends who use the same app, which is normally nobody). The
*only* legitimate source is the data export Facebook itself produces.

This tool turns that export into a clean list — no scraping, no ToS risk.

Getting the export
------------------
1. Facebook -> Settings & privacy -> Settings -> Your Facebook Information
2. "Download your information" -> **Deselect all**, then tick only **Friends**
3. Format **JSON** (smaller and exact) or **HTML**, media quality low, date range "All time"
4. Wait for the notification, download the ZIP, and extract it.

Usage
-----
    # point at the extracted folder OR the downloaded .zip
    python tools/friends_export.py "C:\\Users\\me\\Downloads\\facebook-username-2026-10-31"

    # write a table/JSON/markdown summary
    python tools/friends_export.py <path> --format md --out friends.md
    python tools/friends_export.py <path> --format json --out friends.json

    # filter
    python tools/friends_export.py <path> --search bhattacharya --limit 20

The parser accepts the JSON export layout
(`your_activity_across_facebook/connections/friends/*.json`), the HTML layout
(`.../friends_and_followers/friends.html`), and a hand-saved CSV.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

FRIEND_HINTS = ("friends.json", "friends.html", "friends_and_followers", "friends.csv")


def _candidate_members(path: Path) -> Iterable[tuple[str, bytes]]:
    """Yield (name, bytes) for every plausibly relevant file in a folder or zip."""
    if path.is_file() and path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                lowered = info.filename.lower()
                if any(h in lowered for h in FRIEND_HINTS) or "friend" in lowered:
                    yield info.filename, archive.read(info)
        return

    if path.is_file():
        yield path.name, path.read_bytes()
        return

    for file in sorted(path.rglob("*")):
        if not file.is_file():
            continue
        lowered = file.name.lower()
        if any(h in lowered for h in FRIEND_HINTS) or "friend" in lowered:
            yield str(file.relative_to(path)), file.read_bytes()


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _normalise(friend: dict[str, Any], source: str) -> dict[str, str]:
    name = (
        friend.get("name")
        or friend.get("Name")
        or " ".join(
            part for part in (friend.get("first name"), friend.get("last name")) if part
        )
        or ""
    ).strip()
    timestamp = (
        friend.get("timestamp")
        or friend.get("Timestamp")
        or friend.get("friendship_since")
        or ""
    )
    if isinstance(timestamp, (int, float)):
        try:
            timestamp = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")
        except (OverflowError, OSError, ValueError):
            timestamp = str(timestamp)
    return {"name": name, "since": str(timestamp), "source": source}


def parse_json(payload: bytes, source: str) -> list[dict[str, str]]:
    """Parse the JSON export: a list of {name, timestamp} objects."""
    try:
        data = json.loads(payload.decode("utf-8-sig", errors="replace"))
    except json.JSONDecodeError:
        return []

    rows: list[dict[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            # The export wraps entries under "friends_v2"; detect a friend record
            # by a name field rather than hardcoding the wrapper key.
            if isinstance(node.get("name"), str) and node["name"].strip():
                rows.append(_normalise(node, source))
            else:
                for value in node.values():
                    walk(value)

    walk(data)
    return rows


_HTML_BLOCK = re.compile(r'<div class="[^"]*friend[^"]*"[^>]*>(.*?)</div>\s*</div>', re.I | re.S)
_HTML_LINK = re.compile(r'<a[^>]*href="([^"]*profile\.php\?id=\d+)"[^>]*>(.*?)</a>', re.I | re.S)
_TAG = re.compile(r"<[^>]+>")


def parse_html(payload: bytes, source: str) -> list[dict[str, str]]:
    """Parse the HTML export, whose friend names live in profile links."""
    text = payload.decode("utf-8", errors="replace")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for _href, raw_name in _HTML_LINK.findall(text):
        name = html.unescape(_TAG.sub("", raw_name)).strip()
        # The export encodes names in its own charset; this is already decoded.
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({"name": name, "since": "", "source": source})
    return rows


def parse_csv(payload: bytes, source: str) -> list[dict[str, str]]:
    text = payload.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(text.splitlines())
    rows: list[dict[str, str]] = []
    if not reader.fieldnames:
        return rows
    name_key = next(
        (k for k in reader.fieldnames if k and k.strip().lower() in {"name", "full name", "friend"}),
        reader.fieldnames[0],
    )
    for record in reader:
        name = (record.get(name_key) or "").strip()
        if name:
            rows.append({"name": name, "since": "", "source": source})
    return rows


def parse_any(name: str, payload: bytes) -> list[dict[str, str]]:
    lowered = name.lower()
    if lowered.endswith(".json"):
        return parse_json(payload, name)
    if lowered.endswith((".html", ".htm")):
        return parse_html(payload, name)
    if lowered.endswith(".csv"):
        return parse_csv(payload, name)
    return []


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def render(rows: list[dict[str, str]], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    if fmt == "md":
        lines = ["# Facebook friends", "", f"Total: **{len(rows)}**", "", "| # | Name | Friends since |", "|---|------|---------------|"]
        for index, row in enumerate(rows, 1):
            lines.append(f"| {index} | {row['name']} | {row['since'] or '—'} |")
        return "\n".join(lines) + "\n"
    width = max((len(r["name"]) for r in rows), default=10)
    return "\n".join(f"{i:>4}. {r['name']:<{width}}  {r['since']}".rstrip() for i, r in enumerate(rows, 1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="List the friends from a Facebook Download Your Information export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", help="Extracted export folder, the downloaded .zip, or friends.json/csv/html")
    parser.add_argument("--format", choices=("text", "json", "md"), default="text")
    parser.add_argument("--out", help="Write to this file instead of stdout")
    parser.add_argument("--search", help="Only names containing this text (case-insensitive)")
    parser.add_argument("--limit", type=int, help="Show at most N names")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.exists():
        print(f"Not found: {root}", file=sys.stderr)
        return 2

    rows: list[dict[str, str]] = []
    scanned: list[str] = []
    for name, payload in _candidate_members(root):
        parsed = parse_any(name, payload)
        if parsed:
            scanned.append(f"{name} -> {len(parsed)}")
            rows.extend(parsed)

    if not rows:
        print(
            "No friends found.\n"
            f"Looked in: {root}\n"
            "Expected the export's Friends data, e.g.\n"
            "  your_activity_across_facebook/connections/friends/friends.json\n"
            "Make sure you ticked only 'Friends' when creating the export, and note\n"
            "that HTML exports use a custom charset which this parser handles.",
            file=sys.stderr,
        )
        return 1

    # De-duplicate on name, keeping the first sighting.
    unique: dict[str, dict[str, str]] = {}
    for row in rows:
        unique.setdefault(row["name"].casefold(), row)
    rows = sorted(unique.values(), key=lambda r: r["name"].casefold())

    if args.search:
        needle = args.search.casefold()
        rows = [r for r in rows if needle in r["name"].casefold()]
    if args.limit:
        rows = rows[: args.limit]

    output = render(rows, args.format)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Wrote {len(rows)} friend(s) to {args.out}", file=sys.stderr)
        for line in scanned:
            print(f"  source: {line}", file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
