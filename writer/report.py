#!/usr/bin/env python3
"""report.py - deterministic, read-only state report for every book.

The default action is a *report*: for each book in ``workspaces/backlog/``,
``workspaces/pipeline/``, and ``workspaces/published/`` it computes the exact
on-disk state and prints it. Nothing is written, no model is called, and the
same tree always produces the same report, so the output can be diffed.

State is derived only from bytes on disk, using the same rules the pipeline
engines use (``tools/quality.py`` is imported, not re-implemented):

    planned      the chapter's declared segment plan (its own ``segments[]``,
                 else the book plan's ``segment_count``)
    authored     ``chapter.md`` exists, is non-empty, and matches the chapter
                 model's registered ``draft.sha256``
    segments     how many planned segments hold text in the writer, editor,
                 latest (publish source), and translated stages; novels write
                 continuous prose to the flat ``segments/<n>/segment.md``
    validated    review passed against the exact publish source bytes
                 (``quality_review.status == "passed"`` and matching sha256,
                 plus every planned segment present when per-segment)
    published    validated and the published sha256 matches the publish source
    complete     every planned chapter is validated
    fully_pub    every planned chapter is published

Use ``--run`` to execute the pipeline verbs (enrich -> write -> review ->
publish) for each scaffolded book instead of only reporting. ``--json`` prints
the report as JSON for machine use. ``--html [PATH]`` writes a standalone HTML
report (default ``workspaces/report.html``) that embeds the same states as a
JSON payload, so the page is fully self-contained and diffable. ``--book NAME``
narrows the report or the run to one book, and ``--verbose`` lists every chapter
under a book.

Exit code is 0 for a read-only report; for ``--run`` it is 0 only when every
scaffolded book cleared every verb.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from pathlib import Path

# Load the workspace .env and force UTF-8 output (see tools/env.py).
sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()

# Bengali book names and tool output need a Unicode-capable stdout on Windows.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

REPO_ROOT = Path(__file__).resolve().parent
WORKSPACES = REPO_ROOT / "workspaces"
BACKLOG_DIR = WORKSPACES / "backlog"
PIPELINE_DIR = WORKSPACES / "pipeline"
PUBLISHED_DIR = WORKSPACES / "published"
BOOK_CLI = REPO_ROOT / "tools" / "book.py"

# Default destination for --html: inside workspaces/ (generated artifact).
DEFAULT_HTML = WORKSPACES / "report.html"

PYTHON = sys.executable

# (verb, objective) pairs run for each book by --run, in order.
VERBS = [
    ("enrich",  "all"),
    ("write",   "all"),
    ("review",  "all"),
    ("publish", None),
]

# A stage the pipeline records for each planned segment. "latest" is the publish
# source (editor is its fallback), "translator" holds translated derivatives.
SEGMENT_STAGES = ("writer", "editor", "latest", "translator")


# ---------------------------------------------------------------------------
# Low-level, deterministic readers
# ---------------------------------------------------------------------------

def _book_quality():
    """Import the shared engine helpers so the report cannot drift from them."""
    if str(Path(REPO_ROOT / "tools")) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
    import quality  # noqa: WPS433 - imported lazily after sys.path setup
    return quality


def _read_json(path):
    """Parse a JSON file, returning None instead of raising on damage."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _sort_key(name):
    """Numeric folders sort numerically, everything else after them by name."""
    return (0, int(name)) if name.isdecimal() else (1, name)


def _plan_chapters(plan):
    """(name, segment_count) for every chapter the book plan declares.

    ``segment_count`` is the plan's declared count (default 1); it is the
    fallback shape for a chapter that has no model on disk yet. Once a chapter
    is enriched, its own model carries the authoritative segment plan.

    A duplicate chapter name is reported (with a warning from the caller) rather
    than silently collapsing the plan, so a corrupt plan cannot hide chapters.
    """
    records = []
    for entry in (plan or {}).get("chapters") or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        count = entry.get("segment_count", 1)
        if type(count) is not int or count < 1:
            count = 1
        records.append((name, count))
    return records


def _duplicate_chapter_names(plan):
    """Chapter names declared more than once by the plan (a corrupt plan)."""
    seen = set()
    duplicates = set()
    for name, _ in _plan_chapters(plan):
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return sorted(duplicates, key=_sort_key)


def _segment_indices(chapter_dir):
    """Sorted 1-based segment folder numbers present on disk."""
    segments = chapter_dir / "segments"
    if not segments.is_dir():
        return []
    return sorted(
        int(entry.name) for entry in segments.iterdir()
        if entry.is_dir() and entry.name.isdecimal()
    )


def _stage_poems(chapter_dir, stage):
    """Segment numbers holding a non-empty ``<stage>/segment.md``."""
    segments = chapter_dir / "segments"
    if not segments.is_dir():
        return []
    found = []
    for entry in segments.iterdir():
        if not entry.is_dir() or not entry.name.isdecimal():
            continue
        poem = entry / stage / "segment.md"
        if poem.is_file() and poem.read_bytes().strip():
            found.append(int(entry.name))
    return sorted(found)


def _flat_segment_docs(chapter_dir):
    """Novel segment prose at ``segments/<n>/segment.md`` (flat, not staged)."""
    segments = chapter_dir / "segments"
    if not segments.is_dir():
        return []
    found = []
    for entry in segments.iterdir():
        if not entry.is_dir() or not entry.name.isdecimal():
            continue
        prose = entry / "segment.md"
        if prose.is_file() and prose.read_bytes().strip():
            found.append(int(entry.name))
    return sorted(found)


def _display_planned_segments(chapter_dir, planned_segments):
    """Segments the chapter is expected to hold, for display only.

    The chapter's own ``segments[]`` is authoritative once it exists: a poetry
    chapter records one entry per poem, and an enriched novel records the
    continuous parts the writer composes (the root plan may still hold an
    unreconciled placeholder count). Falls back to the plan's declared count.
    """
    model_file = _book_quality().chapter_model_file(chapter_dir)
    model = _read_json(model_file) if model_file.is_file() else {}
    inline = (model or {}).get("segments")
    if isinstance(inline, list) and inline:
        return len(inline)
    return planned_segments


def _segment_title(chapter_dir, index, model):
    """Segment title from segment.json, then the chapter plan, then the number.

    Mirrors the resolution in ``tools/quality.py`` but tolerates a missing or
    damaged ``segment.json`` / chapter model, so a half-scaffolded chapter still
    reports instead of raising.
    """
    seg_json = chapter_dir / "segments" / str(index) / "segment.json"
    if seg_json.is_file():
        record = _read_json(seg_json)
        if isinstance(record, dict):
            title = str(record.get("segment_title") or "").strip()
            if title:
                return title
    for record in (model or {}).get("segments") or []:
        if isinstance(record, dict) and record.get("segment_index") == index:
            title = str(record.get("segment_title") or "").strip()
            if title:
                return title
    return str(index)


def _assemble_publish_md(chapter_dir):
    """Assemble the publish source bytes, tolerating a missing chapter model.

    Byte-identical to ``tools.quality.assemble_publish_md`` (same stage order,
    title resolution, separator, and trailing newline) so the sha256 this report
    compares against ``quality_review.sha256`` is the same value publish checks.
    """
    poems = []
    segments = chapter_dir / "segments"
    if not segments.is_dir():
        return ""
    model = {}
    model_file = _book_quality().chapter_model_file(chapter_dir)
    if model_file.is_file():
        model = _read_json(model_file) or {}
    for index in _segment_indices(chapter_dir):
        body = ""
        # Publish source is latest/, falling back to editor/ per segment.
        for stage in ("latest", "editor"):
            poem = segments / str(index) / stage / "segment.md"
            if poem.is_file():
                body = poem.read_text(encoding="utf-8-sig").strip()
                if body:
                    break
        if not body:
            continue
        poems.append((_segment_title(chapter_dir, index, model), body))
    if not poems:
        return ""
    return "\n\n".join(f"# {title}\n\n{body}" for title, body in poems) + "\n"


def _published_versions(book):
    """Sorted version folder names already published for *book*."""
    root = PUBLISHED_DIR / book
    if not root.is_dir():
        return []
    return sorted(
        (entry.name for entry in root.iterdir() if entry.is_dir()),
        key=lambda name: (_sort_key(name), name),
    )


# ---------------------------------------------------------------------------
# Chapter state
# ---------------------------------------------------------------------------

def chapter_state(quality, chapter_dir, planned_segments):
    """Deterministic state of one chapter directory."""
    model = {}
    model_file = quality.chapter_model_file(chapter_dir)
    has_model = model_file.is_file()
    if has_model:
        model = _read_json(model_file) or {}

    draft_file = chapter_dir / "chapter.md"
    draft_bytes = draft_file.read_bytes() if draft_file.is_file() else b""
    authored = bool(draft_bytes.strip()) and (
        model.get("draft", {}).get("sha256") == quality.digest(draft_bytes)
    )

    present = _segment_indices(chapter_dir)
    stages = {stage: _stage_poems(chapter_dir, stage) for stage in SEGMENT_STAGES}
    # The publish source is latest/, falling back to editor/ for a segment that
    # has no latest copy yet - the same rule tools/quality.py applies.
    publish_source = sorted(set(stages["latest"]) | set(stages["editor"]))
    flat = _flat_segment_docs(chapter_dir)
    display_planned = _display_planned_segments(chapter_dir, planned_segments)
    # Poetry writes one poem per staged segment (writer/segment.md); a novel
    # writes continuous prose to the flat segments/<n>/segment.md. Report
    # whichever shape this chapter actually uses.
    display_written = len(flat) if flat else len(stages["writer"])
    display_publishable = len(publish_source)

    # Validation branch and completeness threshold come from the engine's own
    # rule (per-segment anthology vs legacy/novel chapter.md), so the verdict
    # here is the verdict publish and sync_progress reach.
    try:
        validation_segments = (
            quality.planned_segment_count(chapter_dir) if has_model else planned_segments
        )
    except (OSError, ValueError):
        validation_segments = planned_segments

    review = model.get("quality_review") or {}
    if validation_segments > 0:
        staged = _assemble_publish_md(chapter_dir)
        staged_sha = quality.digest(staged.encode("utf-8")) if staged else None
        validated = bool(
            staged
            and review.get("status") == "passed"
            and review.get("sha256") == staged_sha
            and len(publish_source) == validation_segments
        )
    else:
        staged_sha = quality.digest(draft_bytes) if draft_bytes.strip() else None
        validated = bool(
            authored
            and review.get("status") == "passed"
            and review.get("sha256") == staged_sha
        )
    has_review = bool(review.get("status"))

    return {
        "chapter": chapter_dir.name,
        "title": str(model.get("chapter_title") or model.get("title") or "").strip(),
        "planned_segments": display_planned,
        "publish_basis": "segments" if validation_segments > 0 else "chapter.md",
        "segment_dirs": len(present),
        "segments_written": display_written,
        "segments_edited": len(stages["editor"]),
        "segments_publishable": display_publishable,
        "segments_translated": len(stages["translator"]),
        "segments_flat": len(flat),
        "authored": authored,
        "draft_bytes": len(draft_bytes),
        "state": str(model.get("state") or ""),
        "review_status": str(review.get("status") or ""),
        "has_review": has_review,
        "validated": validated,
    }


# ---------------------------------------------------------------------------
# Book state
# ---------------------------------------------------------------------------

def book_state(book, verbose=False):
    """Deterministic state of one book across backlog, pipeline, published."""
    quality = _book_quality()

    backlog = BACKLOG_DIR / book
    pipeline = PIPELINE_DIR / book

    backlog_files = sorted(p.name for p in backlog.iterdir() if p.is_file()) if backlog.is_dir() else []
    backlog_plan = _read_json(backlog / "book.json") if backlog.is_dir() else None

    state = {
        "book": book,
        "has_backlog": backlog.is_dir(),
        "has_pipeline": pipeline.is_dir(),
        "backlog_files": backlog_files,
        "form": (backlog_plan or {}).get("form"),
        "language": (backlog_plan or {}).get("language") or (backlog_plan or {}).get("book_language"),
        "planned_chapters": 0,
        "chapter_dirs": 0,
        "missing_chapter_dirs": [],
        "chapters_authored": 0,
        "chapters_validated": 0,
        "chapters_published": 0,
        "chapters_reviewed": 0,
        "segments_planned": 0,
        "segments_written": 0,
        "segments_edited": 0,
        "segments_publishable": 0,
        "segments_translated": 0,
        "duplicate_chapter_names": [],
        "complete": False,
        "fully_published": False,
        "published_versions": _published_versions(book),
        "chapters": [],
        "plan_source": None,
    }

    # The pipeline plan is authoritative once scaffolded; the backlog plan is the
    # fallback so an unscaffolded book still reports its declared shape.
    plan = None
    for candidate in (pipeline / "book.json", pipeline / "model.json"):
        if candidate.is_file():
            plan = _read_json(candidate)
            state["plan_source"] = candidate.name
            break
    if plan is None and backlog_plan is not None:
        plan = backlog_plan
        state["plan_source"] = "backlog/book.json"
    if plan is not None:
        state["form"] = plan.get("form") or state["form"]
        state["language"] = plan.get("language") or state["language"]

    planned = _plan_chapters(plan)
    state["planned_chapters"] = len(planned)
    state["duplicate_chapter_names"] = _duplicate_chapter_names(plan)

    rows = []
    missing_plan_segments = 0
    for name, segment_count in planned:
        chapter_dir = pipeline / "chapters" / name
        if not chapter_dir.is_dir():
            state["missing_chapter_dirs"].append(name)
            missing_plan_segments += segment_count
            continue
        rows.append(chapter_state(quality, chapter_dir, segment_count))

    state["chapter_dirs"] = len(rows)
    state["chapters"] = rows
    # The book's planned segment total follows each chapter's own plan (the
    # authoritative one once enriched), plus the plan count for chapters whose
    # folder does not exist yet.
    state["segments_planned"] = missing_plan_segments + sum(
        row["planned_segments"] for row in rows
    )
    for row in rows:
        state["chapters_authored"] += int(row["authored"])
        state["chapters_validated"] += int(row["validated"])
        state["chapters_reviewed"] += int(row["has_review"])
        state["segments_written"] += row["segments_written"]
        state["segments_edited"] += row["segments_edited"]
        state["segments_publishable"] += row["segments_publishable"]
        state["segments_translated"] += row["segments_translated"]

    # `published` mirrors the engine: a validated chapter whose bytes were
    # recorded into a published manifest version.
    state["chapters_published"] = _count_published(pipeline, rows)
    total = len(planned)
    state["complete"] = bool(total) and state["chapters_validated"] == total
    state["fully_published"] = bool(total) and state["chapters_published"] == total
    if not verbose:
        state["chapters"] = []
    return state


def _count_published(pipeline, rows):
    """Chapters recorded as published in progress.json with a matching sha256."""
    quality = _book_quality()
    progress = _read_json(pipeline / "progress.json") or {}
    recorded = {}
    for row in progress.get("chapters") or []:
        if isinstance(row, dict) and row.get("published_sha256"):
            recorded[str(row.get("chapter_number"))] = row["published_sha256"]

    published = 0
    for row in rows:
        chapter_dir = pipeline / "chapters" / row["chapter"]
        try:
            planned = quality.planned_segment_count(chapter_dir)
        except (OSError, ValueError):
            planned = row["planned_segments"]
        if planned > 0:
            staged = _assemble_publish_md(chapter_dir)
            current = quality.digest(staged.encode("utf-8")) if staged else None
            complete = len(
                sorted(set(_stage_poems(chapter_dir, "latest")) |
                       set(_stage_poems(chapter_dir, "editor")))
            ) == planned
        else:
            draft = chapter_dir / "chapter.md"
            data = draft.read_bytes() if draft.is_file() else b""
            current = quality.digest(data) if data.strip() else None
            complete = True
        recorded_sha = recorded.get(row["chapter"])
        published += int(bool(current) and complete and recorded_sha == current)
    return published


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _all_books():
    names = set()
    for root in (BACKLOG_DIR, PIPELINE_DIR, PUBLISHED_DIR):
        if root.is_dir():
            names.update(p.name for p in root.iterdir() if p.is_dir())
    return sorted(names)


def _flag(value):
    return "yes" if value else "no"


def _short_list(names, limit=8):
    """Comma-joined names, elided when the list is long."""
    names = [str(name) for name in names]
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])}, ... (+{len(names) - limit} more)"


def print_report(states):
    """Print one block per book, then an aggregate footer."""
    for state in states:
        book = state["book"]
        print(f"\n{'=' * 78}")
        print(f"BOOK: {book}")
        print(f"{'=' * 78}")
        print(f"  backlog folder      : {_flag(state['has_backlog'])}")
        print(f"  pipeline folder     : {_flag(state['has_pipeline'])}")
        if state["has_backlog"]:
            print(f"  backlog files       : {', '.join(state['backlog_files']) or '(none)'}")
        print(f"  form / language     : {state['form'] or '-'} / {state['language'] or '-'}")
        print(f"  plan read from      : {state['plan_source'] or '(no plan)'}")
        print(f"  planned chapters    : {state['planned_chapters']}")
        if state["duplicate_chapter_names"]:
            print(f"  DUPLICATE names     : {_short_list(state['duplicate_chapter_names'])}"
                  "  (corrupt plan - rename before scaffolding)")
        print(f"  chapter folders     : {state['chapter_dirs']}"
              + (f"  (missing: {_short_list(state['missing_chapter_dirs'])})"
                 if state["missing_chapter_dirs"] else ""))
        print(f"  planned segments    : {state['segments_planned']}")
        print(f"  segments written    : {state['segments_written']}"
              f"  edited: {state['segments_edited']}"
              f"  publishable: {state['segments_publishable']}"
              f"  translated: {state['segments_translated']}")
        if state["form"] == "novel":
            print("  segment layout      : flat segments/<n>/segment.md (novel prose)")
        elif state["has_pipeline"]:
            print("  segment layout      : staged segments/<n>/writer|editor|latest/segment.md (poetry)")
        print(f"  chapters written    : {state['chapters_authored']}/{state['planned_chapters']}")
        print(f"  chapters validated  : {state['chapters_validated']}/{state['planned_chapters']}")
        print(f"  chapters published  : {state['chapters_published']}/{state['planned_chapters']}")
        print(f"  book complete       : {_flag(state['complete'])}")
        print(f"  book fully published: {_flag(state['fully_published'])}")
        versions = state["published_versions"]
        print(f"  published versions  : {', '.join(versions) if versions else '(none)'}")
        if state["chapters"]:
            print("  chapters:")
            print("    " + f"{'ch':>4}  {'pln':>3} {'wrt':>3} {'edt':>3} {'pub':>3} {'trl':>3}"
                  f"  {'authored':>8} {'validated':>9}  basis      state")
            for row in state["chapters"]:
                print(
                    f"    {row['chapter']:>4}  {row['planned_segments']:>3}"
                    f" {row['segments_written']:>3} {row['segments_edited']:>3}"
                    f" {row['segments_publishable']:>3} {row['segments_translated']:>3}"
                    f"  {_flag(row['authored']):>8} {_flag(row['validated']):>9}"
                    f"  {row['publish_basis']:<10} {row['state'] or '-'}"
                )

    total = len(states)
    with_pipeline = sum(1 for s in states if s["has_pipeline"])
    complete = sum(1 for s in states if s["complete"])
    published = sum(1 for s in states if s["fully_published"])
    chapters_planned = sum(s["planned_chapters"] for s in states)
    chapters_written = sum(s["chapters_authored"] for s in states)
    chapters_validated = sum(s["chapters_validated"] for s in states)

    print(f"\n{'=' * 78}")
    print("SUMMARY")
    print(f"{'=' * 78}")
    print(f"  books discovered         : {total}")
    print(f"  with a pipeline          : {with_pipeline}")
    print(f"  without a pipeline       : {total - with_pipeline}")
    print(f"  chapters planned         : {chapters_planned}")
    print(f"  chapters written         : {chapters_written}")
    print(f"  chapters validated       : {chapters_validated}")
    print(f"  books complete           : {complete}")
    print(f"  books fully published    : {published}")
    if total - with_pipeline:
        names = ", ".join(s["book"] for s in states if not s["has_pipeline"])
        print(f"  not scaffolded           : {names}")
    if complete - published:
        names = ", ".join(s["book"] for s in states if s["complete"] and not s["fully_published"])
        print(f"  complete, unpublished    : {names}")


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

# Inline SVG symbols keep the page dependency-free (no CDN, no fonts, no icons
# files). Each is a 16x16 path drawn with currentColor.
_ICONS = {
    "ok": '<path d="M2 8.5l4 4 8-9"/>',
    "warn": '<path d="M8 1.5l6.5 12H1.5z"/><path d="M8 5.5v4"/><path d="M8 11.5v.5"/>',
    "no": '<circle cx="8" cy="8" r="6.2"/><path d="M4.5 4.5l7 7"/>',
}

_HTML_STYLE = """
:root {
  color-scheme: light dark;
  --bg: #f6f7f9;
  --panel: #ffffff;
  --ink: #1b1f24;
  --muted: #6b7280;
  --line: #e3e6ea;
  --ok: #1a7f4b;
  --ok-bg: #e7f6ed;
  --warn: #9a6700;
  --warn-bg: #fdf5e2;
  --bad: #b42318;
  --bad-bg: #fdeceb;
  --accent: #2c56d4;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14171b; --panel: #1c2026; --ink: #e6e9ee; --muted: #9aa4b2;
    --line: #2b3138;
    --ok: #64d29a; --ok-bg: #10281c; --warn: #e3b341; --warn-bg: #2b2310;
    --bad: #ff8d84; --bad-bg: #2d1513; --accent: #7aa2ff;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px;
  background: var(--bg); color: var(--ink);
  font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
h1 { margin: 0 0 4px; font-size: 22px; letter-spacing: -.01em; }
h2 { margin: 0; font-size: 15px; letter-spacing: -.01em; }
a { color: var(--accent); }
.sub { color: var(--muted); margin: 0 0 20px; font-size: 13px; }
.wrap { max-width: 1180px; margin: 0 auto; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 22px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.card .k { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
.card .v { font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; }
.card .n { color: var(--muted); font-size: 12px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; margin-bottom: 14px; overflow: hidden; }
.head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 14px; border-bottom: 1px solid var(--line); }
.head .name { font-weight: 650; font-size: 15px; }
.head .meta { color: var(--muted); font-size: 12px; }
.spacer { flex: 1; }
.pill { display: inline-flex; align-items: center; gap: 5px; border-radius: 999px; padding: 2px 9px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }
.pill.ok { color: var(--ok); background: var(--ok-bg); }
.pill.warn { color: var(--warn); background: var(--warn-bg); }
.pill.bad { color: var(--bad); background: var(--bad-bg); }
.pill.mute { color: var(--muted); background: var(--bg); border: 1px solid var(--line); }
.pill svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
.body { padding: 12px 14px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px 22px; }
.row { display: flex; justify-content: space-between; gap: 12px; font-size: 13px; padding: 2px 0; }
.row .k { color: var(--muted); }
.row .v { font-variant-numeric: tabular-nums; text-align: right; }
.bar { height: 6px; border-radius: 999px; background: var(--line); overflow: hidden; margin-top: 8px; }
.bar > span { display: block; height: 100%; }
.bar > span.ok { background: var(--ok); }
.bar > span.warn { background: var(--warn); }
.bar > span.bad { background: var(--bad); }
.note { color: var(--muted); font-size: 12px; margin-top: 10px; }
.note.bad { color: var(--bad); }
.note.warn { color: var(--warn); }
details { border-top: 1px solid var(--line); }
summary { cursor: pointer; padding: 9px 14px; font-size: 12.5px; color: var(--muted); user-select: none; }
summary:hover { color: var(--ink); }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; font-variant-numeric: tabular-nums; }
th, td { padding: 5px 8px; text-align: right; border-top: 1px solid var(--line); white-space: nowrap; }
th { text-align: right; color: var(--muted); font-weight: 600; }
th:first-child, td:first-child { text-align: left; }
td.t { text-align: left; max-width: 340px; overflow: hidden; text-overflow: ellipsis; }
tbody tr:hover { background: var(--bg); }
td .mark { font-weight: 700; }
td .mark.ok { color: var(--ok); }
td .mark.bad { color: var(--bad); }
.foot { color: var(--muted); font-size: 12px; padding: 8px 2px 0; }
.banner { border: 1px solid var(--bad); background: var(--bad-bg); color: var(--bad); border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; font-size: 13px; }
.banner b { font-weight: 700; }
.empty { color: var(--muted); font-size: 13px; }
"""


def _esc(value):
    """Escape a value for HTML text/attribute context."""
    return html.escape("" if value is None else str(value), quote=True)


def _icon(kind):
    return f'<svg viewBox="0 0 16 16" aria-hidden="true">{_ICONS[kind]}</svg>'


def _pill(kind, label):
    """A status pill: kind is ok | warn | bad | mute."""
    icon = _icon(kind) if kind in _ICONS else ""
    return f'<span class="pill {kind}">{icon}{_esc(label)}</span>'


def _ratio_pill(done, total, label):
    """A pill whose colour reflects completion against a total."""
    if total <= 0:
        return _pill("mute", f"{label} 0/0")
    if done >= total:
        return _pill("ok", f"{label} {done}/{total}")
    if done > 0:
        return _pill("warn", f"{label} {done}/{total}")
    return _pill("bad", f"{label} 0/{total}")


def _bar(done, total):
    """A proportion bar; colour reflects completion."""
    pct = 0 if total <= 0 else max(0, min(100, round(done * 100 / total)))
    kind = "ok" if total > 0 and done >= total else ("warn" if done else "bad")
    return f'<div class="bar"><span class="{kind}" style="width:{pct}%"></span></div>'


def _row(key, value):
    return f'<div class="row"><span class="k">{_esc(key)}</span><span class="v">{_esc(value)}</span></div>'


def _book_status(state):
    """(kind, label) summarizing one book's overall state."""
    if not state["has_pipeline"]:
        return "mute", "no pipeline"
    if state["fully_published"]:
        return "ok", "published"
    if state["complete"]:
        return "ok", "complete"
    if state["chapters_authored"] >= state["planned_chapters"] > 0:
        return "warn", "written, unreviewed"
    if state["chapters_authored"]:
        return "warn", "partial"
    return "bad", "not written"


def _book_note(state):
    """A one-line, state-derived explanation of what the book still needs."""
    if not state["has_pipeline"]:
        if state["plan_source"] is None:
            return ("bad", "No book.json in the backlog: this folder has no plan, so "
                    "there is nothing to scaffold.")
        if state["duplicate_chapter_names"]:
            return ("bad", "No pipeline: the backlog plan declares duplicate chapter "
                    f"names ({_short_list(state['duplicate_chapter_names'])}); fix the plan, "
                    "then scaffold.")
        return ("warn", "No pipeline yet: scaffold it from the backlog plan.")
    if state["missing_chapter_dirs"]:
        return ("bad", f"Pipeline is incomplete: {len(state['missing_chapter_dirs'])} planned "
                f"chapter folder(s) missing ({_short_list(state['missing_chapter_dirs'])}).")
    if state["duplicate_chapter_names"]:
        return ("bad", "The plan declares duplicate chapter names "
                f"({_short_list(state['duplicate_chapter_names'])}).")
    total = state["planned_chapters"]
    if state["fully_published"]:
        return ("ok", "Every planned chapter is written, reviewed, and published.")
    if state["complete"]:
        return ("ok", f"All {total} chapters passed review; publish to create a version.")
    if state["chapters_authored"] < total:
        return ("warn", f"Write is incomplete: {state['chapters_authored']}/{total} chapters "
                "have a matching chapter.md hash.")
    if state["chapters_reviewed"] == 0:
        return ("warn", f"All {total} chapters are written, but none carries a recorded "
                "quality_review; run review, then publish.")
    return ("warn", f"All {total} chapters are written; {state['chapters_reviewed']} have a "
            "review record but do not pass the publish gate; re-run review, then publish.")


def _chapter_table(rows):
    """Per-chapter table for the --verbose HTML report."""
    if not rows:
        return ""
    head = ("<tr><th>ch</th><th class=\"t\">title</th><th>planned</th><th>written</th>"
            "<th>edited</th><th>publish</th><th>translated</th><th>authored</th>"
            "<th>validated</th><th>review</th><th>basis</th><th>state</th></tr>")
    body = []
    for row in rows:
        def mark(value):
            return ('<span class="mark ok">yes</span>' if value
                    else '<span class="mark bad">no</span>')
        body.append(
            "<tr>"
            f"<td>{_esc(row['chapter'])}</td>"
            f"<td class=\"t\" title=\"{_esc(row['title'])}\">{_esc(row['title'])}</td>"
            f"<td>{row['planned_segments']}</td>"
            f"<td>{row['segments_written']}</td>"
            f"<td>{row['segments_edited']}</td>"
            f"<td>{row['segments_publishable']}</td>"
            f"<td>{row['segments_translated']}</td>"
            f"<td>{mark(row['authored'])}</td>"
            f"<td>{mark(row['validated'])}</td>"
            f"<td>{_esc(row['review_status'] or '-')}</td>"
            f"<td>{_esc(row['publish_basis'])}</td>"
            f"<td>{_esc(row['state'] or '-')}</td>"
            "</tr>"
        )
    return ("<details><summary>Per-chapter detail</summary>"
            f"<div style=\"overflow:auto\"><table>{head}<tbody>"
            + "".join(body)
            + "</tbody></table></div></details>")


def _book_panel(state):
    """One book's card: status pills, derived note, counters, optional chapters."""
    kind, label = _book_status(state)
    total = state["planned_chapters"]
    versions = state["published_versions"]
    meta = f"{_esc(state['form'] or 'unknown form')}"
    if state["language"]:
        meta += f" &middot; {_esc(state['language'])}"
    meta += f" &middot; plan: {_esc(state['plan_source'] or 'none')}"

    pills = [
        _pill(kind, label),
        _ratio_pill(state["chapters_authored"], total, "written"),
        _ratio_pill(state["chapters_validated"], total, "validated"),
        _ratio_pill(state["chapters_published"], total, "published"),
    ]

    grid = [
        _row("planned chapters", total),
        _row("chapter folders", state["chapter_dirs"]),
        _row("planned segments", state["segments_planned"]),
        _row("segments written", state["segments_written"]),
        _row("segments edited", state["segments_edited"]),
        _row("segments publishable", state["segments_publishable"]),
        _row("segments translated", state["segments_translated"]),
        _row("published versions", ", ".join(versions) if versions else "none"),
    ]

    note_kind, note_text = _book_note(state)
    note_class = "" if note_kind == "ok" else note_kind
    bits = [
        '<div class="panel">',
        '<div class="head">',
        f'<span class="name">{_esc(state["book"])}</span>',
        f'<span class="meta">{meta}</span>',
        '<span class="spacer"></span>',
        "".join(pills),
        "</div>",
        '<div class="body">',
        f'<div class="grid">{"".join(grid)}</div>',
        _bar(state["chapters_validated"], total),
        f'<p class="note {note_class}">{_esc(note_text)}</p>',
        "</div>",
        _chapter_table(state["chapters"]),
        "</div>",
    ]
    return "".join(bits)


def render_html(states, title="Book pipeline report"):
    """Render the complete, self-contained HTML report as a string.

    The states are also embedded as JSON in a ``<script type="application/json">``
    payload, so the page needs no server and carries its own data.
    """
    total = len(states)
    with_pipeline = sum(1 for s in states if s["has_pipeline"])
    planned = sum(s["planned_chapters"] for s in states)
    written = sum(s["chapters_authored"] for s in states)
    validated = sum(s["chapters_validated"] for s in states)
    published = sum(s["chapters_published"] for s in states)
    complete = sum(1 for s in states if s["complete"])
    fully = sum(1 for s in states if s["fully_published"])

    cards = [
        ("books", total, f"{with_pipeline} with a pipeline"),
        ("chapters planned", planned, f"{total - with_pipeline} book(s) not scaffolded"),
        ("chapters written", written, f"{_pct(written, planned)}% of planned"),
        ("chapters validated", validated, f"{_pct(validated, planned)}% of planned"),
        ("chapters published", published, f"{_pct(published, planned)}% of planned"),
        ("books complete", complete, f"{fully} fully published"),
    ]
    card_html = "".join(
        f'<div class="card"><div class="k">{_esc(k)}</div>'
        f'<div class="v">{v}</div><div class="n">{_esc(n)}</div></div>'
        for k, v, n in cards
    )

    warnings = []
    not_scaffolded = [s["book"] for s in states if not s["has_pipeline"]]
    if not_scaffolded:
        warnings.append(f"Not scaffolded: {', '.join(not_scaffolded)}.")
    broken = [s["book"] for s in states if s["has_pipeline"] and s["missing_chapter_dirs"]]
    if broken:
        warnings.append(f"Incomplete pipeline (missing chapter folders): {', '.join(broken)}.")
    corrupt = [s["book"] for s in states if s["duplicate_chapter_names"]]
    if corrupt:
        warnings.append(f"Corrupt plan (duplicate chapter names): {', '.join(corrupt)}.")
    banner = ""
    if warnings:
        banner = ('<div class="banner"><b>Attention:</b> ' +
                  " ".join(_esc(w) for w in warnings) + "</div>")

    panels = "".join(_book_panel(state) for state in states) or \
        '<div class="panel"><div class="body empty">No books found.</div></div>'

    payload = json.dumps(states, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<style>{_HTML_STYLE}</style>
</head>
<body>
<div class="wrap">
<h1>{_esc(title)}</h1>
<p class="sub">Read-only state of every book. Deterministic: the same tree renders
the same page. Counts come from bytes on disk, not from cached progress.</p>
{banner}
<div class="cards">{card_html}</div>
{panels}
<p class="foot">{total} book(s) &middot; generated by report.py</p>
</div>
<script type="application/json" id="report-data">{payload}</script>
</body>
</html>
"""


def _pct(part, whole):
    """Integer percentage, 0 when the whole is 0."""
    if whole <= 0:
        return 0
    return round(part * 100 / whole)


def write_html(states, path, title="Book pipeline report"):
    """Write the HTML report to *path* (UTF-8) and return the resolved path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(states, title=title), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Pipeline runner (opt-in, --run)
# ---------------------------------------------------------------------------

def has_pipeline(book):
    return (PIPELINE_DIR / book).is_dir()


def run_verb(book, verb, objective):
    """Run ``python tools/book.py <book> <verb> [objective]``, streaming output."""
    args = [PYTHON, str(BOOK_CLI), book, verb]
    if objective:
        args.append(objective)
    print(f"\n{'-' * 78}")
    print(f"[{book}] $ {' '.join(args)}")
    print(f"{'-' * 78}")
    return subprocess.run(args, cwd=REPO_ROOT).returncode


def process_book(book, verbose=False):
    """Run every pipeline verb for one scaffolded book; stop on first failure."""
    if not has_pipeline(book):
        print(f"\n[{book}] SKIP  no pipeline at workspaces/pipeline/{book}/ "
              f"(not yet scaffolded)")
        return True
    print(f"\n{'#' * 78}\n# BOOK: {book}\n{'#' * 78}")
    for verb, objective in VERBS:
        rc = run_verb(book, verb, objective)
        print(f"\n[{book}] {verb} {objective or ''} -> exit code {rc}")
        if rc != 0:
            print(f"\n[{book}] STOPPED ON FAILED VERB: {verb}")
            return False
    print(f"\n[{book}] ALL VERBS COMPLETE")
    state = book_state(book, verbose=verbose)
    print(f"[{book}] state -> written {state['chapters_authored']}/{state['planned_chapters']}, "
          f"validated {state['chapters_validated']}/{state['planned_chapters']}, "
          f"published {state['chapters_published']}/{state['planned_chapters']}")
    return True


def run_pipeline(books, verbose=False):
    """Run the four pipeline verbs for each book; return the failed book names."""
    if not books:
        print("No books found in workspaces/backlog/")
        return []
    print(f"Discovered {len(books)} book(s)")
    for book in books:
        marker = "" if has_pipeline(book) else "  (no pipeline - will be skipped)"
        print(f"  - {book}{marker}")

    failed = []
    for book in books:
        if not has_pipeline(book):
            continue
        if not process_book(book, verbose=verbose):
            failed.append(book)
    return failed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="report.py",
        description="Deterministic, read-only state report for every book.",
    )
    parser.add_argument("--book", metavar="NAME", help="report or run one book only")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--html", nargs="?", const=str(DEFAULT_HTML), metavar="PATH",
                        help=f"write a self-contained HTML report "
                             f"(default {DEFAULT_HTML})")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="list every chapter under its book")
    parser.add_argument("--run", action="store_true",
                        help="run enrich -> write -> review -> publish per book")
    args = parser.parse_args(argv)

    books = _all_books()
    if args.book:
        books = [book for book in books if book == args.book]
        if not books:
            print(f"Book not found: {args.book}", file=sys.stderr)
            return 1

    if args.run:
        failed = run_pipeline([b for b in books if b in set(_backlog_books())],
                             verbose=args.verbose)
        # Always close a run with the exact post-run state.
        print()
        states = [book_state(book, verbose=args.verbose) for book in books]
        print_report(states)
        if args.html:
            written = write_html(states, args.html)
            print(f"\nHTML report written to {written}")
        if failed:
            print(f"\nFailed books: {', '.join(failed)}")
            return 1
        print("\nAll pipeline verbs passed for every scaffolded book.")
        return 0

    states = [book_state(book, verbose=args.verbose) for book in books]
    if args.html:
        written = write_html(states, args.html)
        print(f"Wrote {written}")
        if args.json:
            print(json.dumps(states, ensure_ascii=False, indent=2))
        return 0
    if args.json:
        print(json.dumps(states, ensure_ascii=False, indent=2))
        return 0
    print_report(states)
    return 0


def _backlog_books():
    if not BACKLOG_DIR.is_dir():
        return []
    return sorted(p.name for p in BACKLOG_DIR.iterdir() if p.is_dir())


if __name__ == "__main__":
    sys.exit(main())
