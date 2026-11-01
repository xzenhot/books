#!/usr/bin/env python3
"""workplan.py — print a "plan of works" banner before a long enrich/write run.

Enrich and write are slow, per-chapter Ollama loops. Before spending minutes on
them, the operator should see exactly what is about to happen: which model, which
book, how many chapters, the chapter range, the estimated finish time, and where
the run will stop first.

Measured pacing (from `_logs/notifications.jsonl` across this workspace):

    enrich  ~14 s/chapter (median 13.6 s, mean 14.3 s)
    write   ~15 s/chapter (median 12.7 s, mean 14.6 s)

The estimate uses the median and is reported as a range, because per-chapter cost
depends on the model, the context size, and whether the chapter needs repairs.

This module prints only. It never writes a file and never calls Ollama.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent

# Measured seconds per chapter: (median, mean) — see the module docstring.
PACING: dict[str, tuple[float, float]] = {
    "enrich": (13.6, 14.3),
    "write": (12.7, 14.6),
}

# The first and last chapter of a long run are the useful sanity check.
PREVIEW_COUNT = 3


def _resolve_pipeline(bookname: str) -> Path:
    return REPO_ROOT / "workspaces" / "pipeline" / bookname


def sync_progress(bookname: str) -> bool:
    """Rebuild `progress.json` from `book.json` and the chapter models.

    `book.json` is the single source of truth: chapter list, order, titles, and
    the model all come from the plan. This wrapper keeps the two tools identical
    and never invents state. Returns True when the file was rewritten.
    """
    import sys

    tools_dir = str(Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)

    from quality import read_json, sync_progress as _sync

    pipeline = _resolve_pipeline(bookname)
    progress_path = pipeline / "progress.json"
    before = read_json(progress_path) if progress_path.exists() else {}
    _sync(pipeline)
    after = read_json(progress_path) if progress_path.exists() else {}
    return before != after


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def _resolve_model(pipeline: Path, override: Optional[str] = None) -> tuple[str, str]:
    """Return (model name, where it came from).

    ``book.json`` is authoritative: it is the book plan every agent reads. A
    stale `progress.json` (an older run's cached model) must never win over the
    plan, so it is not consulted here. ``override`` is the *CLI* value only —
    never a value the caller already resolved, or the source attribution would
    falsely read ``--model``.
    """
    if override:
        return override, "--model"
    data = _read_json(pipeline / "book.json")
    model = data.get("model")
    if isinstance(model, str) and model.strip():
        return model.strip(), "book.json"
    return "<not declared>", "none"


def _describe_range(numbers: Sequence[int]) -> str:
    """Compress [1,2,3,5] into '1-3, 5' — and say when a run is contiguous."""
    if not numbers:
        return "-"
    ordered = sorted(set(numbers))
    spans: list[tuple[int, int]] = []
    start = prev = ordered[0]
    for n in ordered[1:]:
        if n == prev + 1:
            prev = n
            continue
        spans.append((start, prev))
        start = prev = n
    spans.append((start, prev))

    parts = []
    for first, last in spans:
        parts.append(str(first) if first == last else f"{first}-{last}")
    return ", ".join(parts)


def _format_duration(seconds: float) -> str:
    seconds = max(0.0, seconds)
    if seconds < 90:
        return f"{seconds:.0f}s"
    minutes, secs = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def _format_clock(moment: datetime) -> str:
    local = moment.astimezone()
    return local.strftime("%H:%M:%S")


def print_plan(
    command: str,
    bookname: str,
    numbers: Iterable[int],
    *,
    model: Optional[str] = None,
    style: Optional[str] = None,
    form: Optional[str] = None,
    notes: Sequence[str] = (),
    dry_run: bool = False,
) -> None:
    """Print the plan-of-works banner for an enrich or write run."""
    numbers = sorted({int(n) for n in numbers})
    pipeline = _resolve_pipeline(bookname)
    book = _read_json(pipeline / "book.json")
    progress = _read_json(pipeline / "progress.json")

    resolved_model, model_source = _resolve_model(pipeline, model)
    form = form or book.get("form") or progress.get("form") or "?"
    total = book.get("chapter_count") or progress.get("total_chapters") or len(book.get("chapters") or [])
    word_target = book.get("word_target") or "-"

    median, mean = PACING.get(command, (15.0, 15.0))
    count = len(numbers)
    now = datetime.now(timezone.utc)
    low = timedelta(seconds=median * count)
    high = timedelta(seconds=max(mean, median * 1.35) * count)

    # Chapters already written/enriched change what the run actually costs.
    done = 0
    for n in numbers:
        chapter = _read_json(pipeline / "chapters" / str(n) / "chapter.json")
        if command == "write" and chapter.get("state") in {"written", "reviewed", "published"}:
            done += 1
        elif command == "enrich" and (chapter.get("enrich") or {}).get("status") == "enriched":
            done += 1

    bar = "=" * 68
    print()
    print(bar)
    print(f" PLAN OF WORKS — {command.upper()}")
    print(bar)
    print(f"  Model          : {resolved_model}   (from {model_source})")
    print(f"  Book           : {bookname}   (form: {form})")
    print(f"  Chapters       : {count} selected of {total} in the book")
    print(f"  Range          : {_describe_range(numbers)}")
    if len(numbers) > PREVIEW_COUNT * 2:
        head = ", ".join(str(n) for n in numbers[:PREVIEW_COUNT])
        tail = ", ".join(str(n) for n in numbers[-PREVIEW_COUNT:])
        print(f"  Order          : {head} ... {tail}")
    elif len(numbers) > 1:
        print(f"  Order          : {', '.join(str(n) for n in numbers)}")
    if style:
        print(f"  Style          : {style}")
    print(f"  Word target    : {word_target} per chapter")
    print(f"  Pace           : ~{median:.0f}s/chapter (measured median)")
    if done:
        print(f"  Already done   : {done} of {count} (will be redone)")
    print(f"  Estimated time : {_format_duration(low.total_seconds())} – {_format_duration(high.total_seconds())}")
    print(f"  Started        : {_format_clock(now)}")
    print(f"  Est. finish    : {_format_clock(now + low)} – {_format_clock(now + high)}")
    if dry_run:
        print("  Mode           : DRY RUN — nothing will be written")
    for note in notes:
        print(f"  Note           : {note}")
    print(bar)
    print()
