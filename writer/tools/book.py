#!/usr/bin/env python3
"""book.py — Unified book workflow CLI for the writer agentic framework.

This tool manages the full book lifecycle from backlog creation through
pipeline scaffolding and chapter execution. It wraps Ollama for AI-assisted
layout generation and delegates enrichment, writing, and publishing to the
dedicated engine modules (enrich.py, write.py, publish.py).

USAGE
-----
    python tools/book.py <bookname> <verb> [options...]

VERBS
-----
    init      Create backlog artifacts (gist.md, storyline.md, book.json) then
              generate book.json layout via Ollama.

              python tools/book.py <bookname> init ["seed text"] [novel|poetry]

              python tools/book.py <bookname> init idea   # rewrite the gist with AI

    build     Alias for init with an optional chapter count as the first
              positional argument after the verb.

              python tools/book.py <bookname> build 20 novel

    layout    Regenerate book.json from an existing storyline.md via Ollama.
              Does not touch gist.md or storyline.md.

              python tools/book.py <bookname> layout [novel|poetry]

    scaffold  Build the pipeline folder structure (workspaces/pipeline/<bookname>/)
              from the backlog book.json. Requires init to have run first.

              python tools/book.py <bookname> scaffold [count] [novel|poetry]

    enrich    Run the enrich engine (enrich.py) on selected chapters.

              python tools/book.py <bookname> enrich [all|1|1-5|continue]

    write     Run the chapter writer (write.py) on selected chapters.

              python tools/book.py <bookname> write [all|1|1-5|continue]

    publish   Promote pipeline segments to workspaces/published/ via publish.py.

              python tools/book.py <bookname> publish

    preview   Assemble the same output as publish, but skip the quality gate
              and review. Equivalent to publish --draft.

              python tools/book.py <bookname> preview

    cleanup   Reset selected pipeline chapters back to their scaffolded
              baseline: delete chapter.md/context.md, clear history/ and
              segment output folders, and reinitialize chapter.json +
              segment.json from the book plan.

              python tools/book.py <bookname> cleanup [all|1|1-5|continue]

COMMON FLAGS
------------
    -t, --type  poetry|novel   Override book form (default: poetry)
    -r, --refresh              Overwrite existing gist.md when running init
    --gist "text"              Explicit seed text (alternative to positional arg)

EXAMPLES
--------
    # Create a Bengali poetry book from scratch
    python tools/book.py cosmos init "মহাবিশ্বের অসীম রহস্য" poetry

    # Regenerate layout from an existing epic (large book, batched)
    python tools/book.py cosmos layout 30 poetry

    # Scaffold novel pipeline then enrich all chapters
    python tools/book.py mynovel scaffold 15 novel
    python tools/book.py mynovel enrich all

    # Write chapters 1–5 then publish
    python tools/book.py mynovel write 1-5
    python tools/book.py mynovel publish
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from promptkit import PromptSet, framework_layout_dir, render
from quality import read_json, write_json

# Reconfigure stdio for UTF-8 so status arrows (e.g. U+2192) never crash on a
# Windows console whose default codec (cp1252/charmap) cannot encode them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent          # tools/
REPO_ROOT = BASE_DIR.parent                          # repo root
BACKLOG_ROOT = REPO_ROOT / "workspaces" / "backlog"
BACKLOG_V1_TEMPLATE = REPO_ROOT / ".framework" / "templates" / "backlog" / "v1"
BOOK_TEMPLATE = BACKLOG_V1_TEMPLATE / "book.json"
BOOK_MIN_TEMPLATE = BACKLOG_V1_TEMPLATE / "book.min.json"
BOOK_PROMPTS = PromptSet(framework_layout_dir(REPO_ROOT), "book")


def _template_model_provider() -> tuple[str, str]:
    """Read the LLM ``model`` and ``provider`` defaults from the backlog template.

    The template (``.framework/templates/backlog/book.json``) is the single
    source of truth for these fields. They flow: template → backlog ``book.json``
    (via ``make_book_json`` / layout) → scaffold copies verbatim → pipeline
    ``book.json`` → consumed by enrich/write. Returns
    ``("gemma4:latest", "ollama")`` when the template is absent or lacks them.
    """
    model, provider = "gemma4:latest", "ollama"
    if BOOK_TEMPLATE.is_file():
        try:
            data = json.loads(BOOK_TEMPLATE.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            data = {}
        if isinstance(data.get("model"), str) and data["model"].strip():
            model = data["model"].strip()
        if isinstance(data.get("provider"), str) and data["provider"].strip():
            provider = data["provider"].strip()
    return model, provider


def _template_filter_chain() -> list[str]:
    """Read the canonical ``filter_chain`` from the backlog template.

    The template (``.framework/templates/backlog/book.json``) is the single
    source of truth for the ordered filter sequence. It is stored there as a
    list of ``{sl, filter, autorun, reference}`` objects; this helper normalizes
    it to the list of filter-name strings the pipeline consumes. Returns an
    empty list when the template is absent or lacks a valid chain.
    """
    if BOOK_TEMPLATE.is_file():
        try:
            data = json.loads(BOOK_TEMPLATE.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            data = {}
        chain = data.get("filter_chain")
        if isinstance(chain, list):
            names: list[str] = []
            for entry in chain:
                if isinstance(entry, str):
                    names.append(entry)
                elif isinstance(entry, dict) and entry.get("filter"):
                    names.append(str(entry["filter"]))
            return [name for name in names if name]
    return []

# ---------------------------------------------------------------------------
# Ollama configuration
# ---------------------------------------------------------------------------

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "gemma4:latest"
OLLAMA_TIMEOUT = 900       # seconds — large books need time
OLLAMA_BATCH_SIZE = 10     # chapters per Ollama call when count > 10
OLLAMA_TEMPERATURE = 0.2   # low temperature → consistent, structured output
OLLAMA_TOP_P = 0.9
OLLAMA_MAX_RETRIES = 3     # retries per chapter batch and completeness pass
SUMMARY_MIN_WORDS = 150    # minimum chapter_summary length in words (target 150–200)

# ---------------------------------------------------------------------------
# Filter chains — canonical defaults per form
# ---------------------------------------------------------------------------

FILTER_CHAIN_NOVEL = [
    "workshop", "research", "seeds", "correctness", "theme", "syntax",
]
FILTER_CHAIN_POETRY = [
    "workshop", "research", "correctness", "theme", "syntax", "override", "quality",
]

# ---------------------------------------------------------------------------
# System prompt for layout generation
# ---------------------------------------------------------------------------

LAYOUT_SYSTEM_PROMPT = BOOK_PROMPTS.text("layout_system_prompt.md")

EPIC_SYSTEM_PROMPT = BOOK_PROMPTS.text("epic_system_prompt.md")

# Minimal chapter schema description sent in batch prompts
BATCH_CHAPTER_SCHEMA = BOOK_PROMPTS.text("batch_chapter_schema.json").strip()

# User-prompt templates (rendered with render(...) at call time)
_EPIC_USER_PROMPT = BOOK_PROMPTS.text("epic_user_prompt.md")
_CHAPTER_BATCH_PROMPT = BOOK_PROMPTS.text("chapter_batch_prompt.md")
_CHAPTER_ONE_PROMPT = BOOK_PROMPTS.text("chapter_one_prompt.md")
_LAYOUT_SINGLE_PROMPT = BOOK_PROMPTS.text("layout_single_prompt.md")
_GIST_IDEA_PROMPT = BOOK_PROMPTS.text("gist_idea_prompt.md")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_bookname(bookname: str) -> str:
    """Reject booknames that would produce unsafe or ambiguous folder names.

    Raises ValueError if the name is blank, a relative path component,
    or contains any character that is illegal in a cross-platform filename.
    Returns the stripped name on success.
    """
    stripped = bookname.strip()
    illegal_chars = set('/\\:<">|?*')
    if not stripped or stripped in {".", ".."} or illegal_chars.intersection(stripped):
        raise ValueError(
            f"Invalid bookname {bookname!r}. "
            "Use a single safe folder name with no path separators or special characters."
        )
    return stripped


def resolve_form(candidates: list[str | None], fallback: str = "poetry") -> str:
    """Return the first 'novel' or 'poetry' value found in *candidates*, else *fallback*.

    Useful for resolving form from multiple positional argument slots without
    repeating the same next()-pattern throughout the dispatcher.
    """
    for value in candidates:
        if value in {"novel", "poetry"}:
            return value
    return fallback


def resolve_count(candidates: list[str | None]) -> int | None:
    """Return the first decimal-only string in *candidates* as an int, or None."""
    for value in candidates:
        if value and value.isdecimal():
            return int(value)
    return None


# ---------------------------------------------------------------------------
# Backlog content helpers
# ---------------------------------------------------------------------------

def read_seed(book_dir: Path) -> list[str]:
    """Read non-empty lines from seed.txt if it exists, else return empty list.

    seed.txt is an optional human-authored topic list — one topic per line.
    When present it seeds the chapter titles instead of generating them.
    """
    seed_file = book_dir / "seed.txt"
    if not seed_file.exists():
        return []
    return [
        line.strip()
        for line in seed_file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def read_materials(book_dir: Path) -> str:
    """Read the user's research materials from materials/ into one text block.

    Concatenates the text of every file under materials/ (recursively), each
    preceded by its relative path, so the storyline/layout prompt can ground
    itself in the user's sources. Returns an empty string when the folder is
    absent or empty.
    """
    materials_dir = book_dir / "materials"
    if not materials_dir.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(materials_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeDecodeError):
            continue
        if text:
            rel = path.relative_to(materials_dir).as_posix()
            parts.append(f"--- {rel} ---\n{text}")
    return "\n\n".join(parts)


def default_gist(bookname: str, form: str) -> str:
    """Generate a placeholder Bengali gist when the user has not provided one."""
    if form == "poetry":
        return (
            f"একটি আত্মঅনুসন্ধানী কবিতার সংকলন, যেখানে {bookname} "
            "মানুষের অভিজ্ঞতার রূপক হয়ে ওঠে।"
        )
    return (
        f"{bookname}কে কেন্দ্র করে মানুষের পরিবর্তন, সংঘাত ও অর্থের "
        "একটি সাহিত্যিক কাহিনি।"
    )


def make_title(bookname: str, form: str) -> str:
    """Produce a Bengali book title from the book name and form."""
    suffix = "এর কবিতা" if form == "poetry" else "এর কাহিনি"
    return f"{bookname}: {suffix}"


def format_gist_md(bookname: str, form: str, gist: str, expansion: str = "",
                   comment: str = "") -> str:
    """Render gist.md in the canonical structure.

    Format:
        # <bookname> — <title>
        ## Canonical gist
        <gist>
        ## Expansion
        <expansion>
        ## Author Comment
        <comment>
    """
    title = make_title(bookname, form)
    lines = [f"# {bookname} — {title}", "", "## Canonical gist", "", gist]
    lines += ["", "## Expansion", ""]
    if expansion:
        lines.append(expansion)
    lines += ["", "## Author Comment", ""]
    if comment:
        lines.append(comment)
    return "\n".join(lines).rstrip() + "\n"


def make_chapters(
    bookname: str,
    form: str,
    seed: list[str],
    chapter_count: int | None = None,
) -> list[dict[str, object]]:
    """Build the chapters array for the backlog book plan.

    Topics come from seed.txt when available; remaining slots are filled with
    numbered placeholders.  *chapter_count* overrides both seed length and the
    default of 15.
    """
    count = chapter_count or len(seed) or 15
    topics = list(seed[:count])
    # Pad with numbered placeholders if seed is shorter than requested count
    topics.extend(
        f"{bookname} — পর্ব {i}"
        for i in range(len(topics) + 1, count + 1)
    )
    word_target = 500 if form == "poetry" else 4500
    return [
        {
            "chapter_index": idx,
            "name": str(idx),
            "word_target": word_target,
            "chapter_title": topic,
            "chapter_summary": (
                f"{topic}কে কেন্দ্র করে {bookname}-এর মূল ভাবনা, মানবিক অভিজ্ঞতা "
                "এবং একটি খোলা প্রশ্ন অনুসরণ করা হবে।"
            ),
            "further_references": [],
        }
        for idx, topic in enumerate(topics, 1)
    ]


def make_book_json(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
    now: str,
) -> dict[str, object]:
    """Assemble the full book.json dict from its component parts.

    This is the backlog book plan — the blueprint scaffold reads.
    Ollama may later replace it with a richer version via generate_layout().
    """
    model, provider = _template_model_provider()
    return {
        "book_name": bookname,
        "book_long_title": make_title(bookname, form),
        "generic": "আত্মঅনুসন্ধানী কবিতা" if form == "poetry" else "সাহিত্যিক কাহিনি",
        "era": "সমকালীন ও রূপক সময়",
        "language": "বাংলা",
        "target_audience": "বাংলা সাহিত্য ও মননশীল পাঠের পাঠক",
        "chapter_count": len(chapters),
        "form": form,
        "model": model,
        "provider": provider,
        "book_summary": gist,
        "created_at": now,
        "updated_at": now,
        "user_name": "pijush",
        "gist": gist,
        "chapters": chapters,
        "all_characters": [],
        "filter_chain": FILTER_CHAIN_POETRY if form == "poetry" else FILTER_CHAIN_NOVEL,
        "word_target": 500 if form == "poetry" else 4500,
    }


def write_backlog_progress(book_dir: Path) -> Path:
    """Create the backlog ``progress.json`` from the template, customized to the plan.

    Copies the shape of ``.framework/templates/backlog/progress.json`` and re-seeds it
    with the book's actual chapters (topic, category, pending status) so the backlog
    holds a ready-made progress plan. ``scaffold`` later copies this file verbatim into
    the pipeline as the initial progress state.

    Args:
        book_dir: Path to the backlog folder (must already contain ``book.json``).
    """
    template = REPO_ROOT / ".framework" / "templates" / "backlog" / "v1" / "progress.json"
    plan_file = book_dir / "book.json"
    plan = json.loads(plan_file.read_text(encoding="utf-8-sig"))
    chapters = plan.get("chapters", [])

    template_data: dict = {}
    if template.is_file():
        try:
            template_data = json.loads(template.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            template_data = {}

    factory = plan.get("factory") or template_data.get("factory") or "online"
    model = plan.get("model") or template_data.get("model") or "gemma4:latest"
    provider = plan.get("provider") or template_data.get("provider") or "ollama"
    progress = {
        "total_chapters": len(chapters),
        "completed_chapters": 0,
        "current_chapter": 1,
        "factory": factory,
        "model": model,
        "provider": provider,
        "book_name": plan.get("book_name") or template_data.get("book_name"),
        "form": plan.get("form") or template_data.get("form"),
        "chapters": [
            {
                "chapter_number": ch.get("chapter_index", i),
                "topic": ch.get("chapter_title") or ch.get("name") or f"Chapter {i}",
                "category": "",
                "status": "pending",
                "file_path": f"chapters/{ch.get('name', i)}/chapter.md",
                "completed_date": None,
            }
            for i, ch in enumerate(chapters, 1)
        ],
    }

    out = book_dir / "progress.json"
    out.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def make_epic(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
    now: str,
) -> str:
    """Render a Bengali storyline.md from the backlog plan.

    The epic is the narrative source of truth for the book.  This function
    produces the initial scaffold version; human editing or Ollama can
    enrich it later.
    """
    form_label = "কবিতা" if form == "poetry" else "উপন্যাস"
    lines = [
        f"# {make_title(bookname, form)}",
        "",
        f"- **Book name:** {bookname}",
        f"- **Storyline path:** workspaces/backlog/{bookname}/storyline.md",
        f"- **Created:** {now}",
        f"- **Updated:** {now}",
        "- **Updated by:** book.py",
        f"- **Form:** {form}",
        "- **Language:** বাংলা",
        f"- **Genre:** {form_label}",
        "- **Era:** সমকালীন ও রূপক সময়",
        f"- **Chapter count:** {len(chapters)}",
        f"- **Gist:** {gist}",
        "",
        "## মূল ভাবনা",
        "",
        gist,
        "",
        (
            "এই বইয়ের প্রতিটি অধ্যায় মূল বীজের একটি আলাদা দিক অনুসরণ করবে। "
            "বিষয়, মানুষের অভিজ্ঞতা, রূপক এবং খোলা প্রশ্ন একসঙ্গে এগিয়ে যাবে; "
            "অধ্যায়ের সারাংশগুলি পরিকল্পনা, চূড়ান্ত লেখা নয়।"
        ),
        "",
        "## পর্বের বিন্যাস",
        "",
    ]
    for ch in chapters:
        lines += [
            f"### {ch['chapter_index']}. {ch['chapter_title']}",
            "",
            str(ch["chapter_summary"]),
            "",
        ]
    lines += [
        "## ভাষা ও কাব্যিক/আখ্যানিক অভিমুখ",
        "",
        (
            "ভাষা হবে প্রাঞ্জল বাংলা; রচনা তার নির্ধারিত form অনুসরণ করবে। "
            "বিষয়কে ব্যাখ্যা করার বদলে দৃশ্য, অনুভব, সংঘাত ও রূপকের মাধ্যমে প্রকাশ করা হবে।"
        ),
        "",
        "## আবেগের গন্তব্য",
        "",
        (
            "শেষে সব প্রশ্ন বন্ধ হবে না; মূল বীজের প্রতিধ্বনি রেখে "
            "পাঠককে পরবর্তী ভাবনার দিকে এগিয়ে দেওয়া হবে।"
        ),
        "",
    ]
    return "\n".join(lines)


def _epic_header(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
    now: str,
) -> str:
    """Build the deterministic metadata header for an storyline.md file.

    This block carries the fields the pipeline parses (form, chapter count,
    gist, language) and must precede any Ollama-enriched narrative body.
    """
    form_label = "কবিতা" if form == "poetry" else "উপন্যাস"
    return "\n".join([
        f"# {make_title(bookname, form)}",
        "",
        f"- **Book name:** {bookname}",
        f"- **Storyline path:** workspaces/backlog/{bookname}/storyline.md",
        f"- **Created:** {now}",
        f"- **Updated:** {now}",
        "- **Updated by:** book.py",
        f"- **Form:** {form}",
        "- **Language:** বাংলা",
        f"- **Genre:** {form_label}",
        "- **Era:** সমকালীন ও রূপক সময়",
        f"- **Chapter count:** {len(chapters)}",
        f"- **Gist:** {gist}",
        "",
    ])


def build_epic_prompt(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
) -> str:
    """Assemble the Ollama prompt that expands a gist into a rich epic."""
    form_label = "কবিতা" if form == "poetry" else "উপন্যাস"
    chapter_plan = "\n".join(
        f"{ch['chapter_index']}. {ch['chapter_title']} — {ch['chapter_summary']}"
        for ch in chapters
    )
    return render(
        _EPIC_USER_PROMPT,
        bookname=bookname,
        form=form,
        form_label=form_label,
        gist=gist,
        chapter_count=len(chapters),
        chapter_plan=chapter_plan,
    )


def generate_epic(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
    now: str,
    materials: str = "",
) -> str:
    """Enrich the gist into a full storyline.md via Ollama, falling back to the scaffold.

    Calls Ollama with the epic prompt; on success, prepends the deterministic
    metadata header to the model's narrative body.  On any network/parse error
    it degrades gracefully to the deterministic make_epic() scaffold.

    *materials* is optional research-material text read from the book's
    materials/ folder; when non-empty it is appended to the prompt so the
    storyline stays grounded in the user's sources.
    """
    try:
        prompt = build_epic_prompt(bookname, form, gist, chapters)
        if materials:
            prompt += (
                "\n\nRESEARCH MATERIALS (ground the storyline in these; "
                "never contradict them):\n" + materials + "\n"
            )
        body = _ollama_post(_ollama_payload(prompt, system=EPIC_SYSTEM_PROMPT))
        body = body.strip()
        if not body:
            raise ValueError("Ollama returned an empty epic.")
        return _epic_header(bookname, form, gist, chapters, now) + body + "\n"
    except (RuntimeError, ValueError) as exc:
        print(f"  warning: epic enrichment failed ({exc}); using scaffold epic.")
        return make_epic(bookname, form, gist, chapters, now)


# ---------------------------------------------------------------------------
# JSON parsing helpers
# ---------------------------------------------------------------------------

def _first_balanced_block(text: str, open_char: str, close_char: str) -> str:
    """Return the first balanced ``open_char ... close_char`` block in *text*.

    Scans character by character, tracking nesting depth (ignoring brackets
    inside JSON strings), so trailing prose, a second concatenated array, or a
    Markdown fence after the payload do not corrupt the slice. Returns an empty
    string when no balanced block is found.
    """
    start = text.find(open_char)
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        char = text[i]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def extract_json(
    response: str,
    expect_list: bool = False,
) -> list[object] | dict[str, object]:
    """Parse a JSON value from a raw Ollama response string.

    Handles common Ollama output patterns:
    1. A bare JSON object or array.
    2. JSON wrapped in a Markdown code fence (```json ... ```).
    3. JSON followed by trailing prose/commentary, or two concatenated values.

    When *expect_list* is True the result must be a list; a dict with a
    'chapters' key is unwrapped automatically.  Raises ValueError when the
    result type does not match the expectation.
    """
    cleaned = response.strip().lstrip("\ufeff")

    # Strip Markdown fences if present
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove opening fence line (e.g. ```json)
        lines = lines[1:] if lines and lines[0].startswith("```") else lines
        # Remove closing fence line
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Attempt direct parse first
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back: extract the first balanced JSON block (tolerates trailing
        # prose and concatenated values), preferring the expected container.
        open_char, close_char = ("[", "]") if expect_list else ("{", "}")
        candidate = _first_balanced_block(cleaned, open_char, close_char)
        if not candidate:
            # The model may have returned the other container type; try it too.
            alt_open, alt_close = ("{", "}") if expect_list else ("[", "]")
            candidate = _first_balanced_block(cleaned, alt_open, alt_close)
        if not candidate:
            raise ValueError(
                f"Ollama response does not contain a JSON {'array' if expect_list else 'object'}.\n"
                f"Raw response (first 300 chars): {response[:300]}"
            )
        data = json.loads(candidate)

    # Type validation and unwrapping
    if expect_list:
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "chapters" in data:
            return data["chapters"]  # type: ignore[return-value]
        raise ValueError(
            "Expected a JSON array from Ollama (or a dict with 'chapters'), "
            f"got {type(data).__name__}."
        )

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object from Ollama, got {type(data).__name__}."
        )
    return data


def validate_layout(
    data: dict[str, object],
    bookname: str,
    form: str,
) -> dict[str, object]:
    """Validate an Ollama-generated book plan against the minimum runtime contract.

    Checks presence of required top-level fields, correct book_name and form,
    non-empty chapters array, chapter_count consistency, and per-chapter required
    keys.  Raises ValueError with a descriptive message on any violation.
    Returns *data* unchanged on success so callers can chain the call.
    """
    required_top = ("book_name", "book_long_title", "chapter_count", "form", "chapters", "filter_chain")
    missing = [key for key in required_top if key not in data]
    if missing:
        raise ValueError(f"Layout JSON is missing required fields: {', '.join(missing)}")

    if data["book_name"] != bookname:
        raise ValueError(
            f"Layout book_name is {data['book_name']!r} but expected {bookname!r}."
        )
    if data["form"] != form:
        raise ValueError(
            f"Layout form is {data['form']!r} but expected {form!r}."
        )

    chapters = data["chapters"]
    if not isinstance(chapters, list) or not chapters:
        raise ValueError("Layout 'chapters' must be a non-empty array.")
    if data["chapter_count"] != len(chapters):
        raise ValueError(
            f"Layout chapter_count ({data['chapter_count']}) does not match "
            f"chapters array length ({len(chapters)})."
        )

    if not isinstance(data["filter_chain"], list) or not data["filter_chain"]:
        raise ValueError("Layout 'filter_chain' must be a non-empty array.")

    required_chapter = ("chapter_index", "name", "chapter_title", "chapter_summary")
    for i, chapter in enumerate(chapters, 1):
        if not isinstance(chapter, dict):
            raise ValueError(f"Chapter {i} must be a JSON object, got {type(chapter).__name__}.")
        for key in required_chapter:
            if key not in chapter or not str(chapter[key]).strip():
                raise ValueError(f"Chapter {i} is missing or has an empty '{key}' field.")
        summary = str(chapter["chapter_summary"]).strip()
        if _summary_word_target(summary) < SUMMARY_MIN_WORDS:
            raise ValueError(
                f"Chapter {i} has an under-written chapter_summary "
                f"({_summary_word_target(summary)} words; expected 150–200)."
            )

    return data


# ---------------------------------------------------------------------------
# Ollama communication
# ---------------------------------------------------------------------------

def _ollama_post(payload: dict[str, object]) -> str:
    """Send a POST request to the local Ollama endpoint and return the response text.

    Raises RuntimeError on network errors, timeouts, or non-JSON API responses.
    """
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_URL}. Is it running?\n  Detail: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError(
            f"Ollama request timed out after {OLLAMA_TIMEOUT}s. "
            "Try reducing the chapter count or increasing OLLAMA_TIMEOUT."
        ) from exc

    try:
        response_obj = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned a non-JSON API response.") from exc

    return response_obj.get("response", "")


def _ollama_payload(prompt: str, system: str = LAYOUT_SYSTEM_PROMPT) -> dict[str, object]:
    """Build a standard Ollama generate payload dict."""
    return {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "think": False,
        "options": {
            "temperature": OLLAMA_TEMPERATURE,
            "top_p": OLLAMA_TOP_P,
        },
    }


# ---------------------------------------------------------------------------
# Layout generation
# ---------------------------------------------------------------------------

def _summary_word_target(summary: object) -> int:
    """Count whitespace-separated words in a chapter_summary value."""
    return len(str(summary).split())


def _short_summary_indices(
    chapters_by_index: dict[int, dict[str, object]],
    chapter_count: int,
) -> list[int]:
    """Return indices whose chapter_summary is shorter than the richness floor."""
    short = []
    for i in range(1, chapter_count + 1):
        chapter = chapters_by_index.get(i)
        if chapter is not None and _summary_word_target(chapter.get("chapter_summary", "")) < SUMMARY_MIN_WORDS:
            short.append(i)
    return short


def _incomplete_chapters(
    chapters_by_index: dict[int, dict[str, object]],
    chapter_count: int,
) -> list[int]:
    """Return indices that are missing or have an under-written summary."""
    missing = [i for i in range(1, chapter_count + 1) if i not in chapters_by_index]
    short = _short_summary_indices(chapters_by_index, chapter_count)
    return sorted(set(missing) | set(short))


def _generate_chapter_batch(
    epic: str,
    indices: list[int],
    batch_num: int,
    total_batches: int,
) -> list[dict[str, object]]:
    """Generate one batch of chapters, retrying on failure.

    Returns the parsed chapter objects (one per requested index).  Raises
    RuntimeError if every attempt fails.
    """
    indices_str = ", ".join(str(i) for i in indices)
    prompt = render(
        _CHAPTER_BATCH_PROMPT,
        indices=indices_str,
        schema=BATCH_CHAPTER_SCHEMA,
        epic=epic,
    )
    last_error: Exception | None = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        try:
            generated = _ollama_post(_ollama_payload(prompt))
            chapters = extract_json(generated, expect_list=True)
            chapters = [
                ch for ch in chapters
                if isinstance(ch, dict) and ch.get("chapter_index") is not None
            ]
            if not chapters:
                raise ValueError("Ollama returned an empty chapter batch.")
            return chapters  # type: ignore[return-value]
        except (RuntimeError, ValueError) as exc:
            last_error = exc
            print(f"  [batch {batch_num}] attempt {attempt}/{OLLAMA_MAX_RETRIES} failed: {exc}")
    raise RuntimeError(
        f"Chapter batch {batch_num} failed after {OLLAMA_MAX_RETRIES} attempts: {last_error}"
    )


def _min_chapter_schema() -> str:
    """Return the minimal single-chapter schema from book.min.json.

    ``.framework/templates/backlog/book.min.json`` carries one truncated chapter
    entry; this is the smallest schema we send so the model stays on a tiny,
    parseable payload. Falls back to the inline ``BATCH_CHAPTER_SCHEMA`` when the
    file is absent or malformed.
    """
    if BOOK_MIN_TEMPLATE.is_file():
        try:
            data = json.loads(BOOK_MIN_TEMPLATE.read_text(encoding="utf-8-sig"))
            chapters = data.get("chapters")
            if isinstance(chapters, list) and chapters and isinstance(chapters[0], dict):
                return json.dumps(chapters[0], ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, OSError):
            pass
    return BATCH_CHAPTER_SCHEMA


def _placeholder_chapter(index: int) -> dict[str, object]:
    """A deterministic chapter entry used when Ollama fails to produce one."""
    return {
        "chapter_index": index,
        "name": str(index),
        "word_target": 500,
        "chapter_title": f"Chapter {index}",
        "chapter_summary": f"Chapter {index} — to be written from the storyline.",
        "further_references": [],
    }


def _generate_chapter_one(
    epic: str,
    bookname: str,
    form: str,
    index: int,
    schema: str,
) -> dict[str, object]:
    """Generate exactly one chapter (smallest payload) via Ollama.

    Returns a single chapter dict. Raises RuntimeError if every attempt fails.
    """
    prompt = render(
        _CHAPTER_ONE_PROMPT,
        index=index,
        schema=schema,
        epic=epic,
    )
    last_error: Exception | None = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        try:
            generated = _ollama_post(_ollama_payload(prompt))
            data = extract_json(generated)
            if isinstance(data, list):
                data = data[0] if data else {}
            if not isinstance(data, dict):
                raise ValueError("response was not a single chapter object")
            if data.get("chapter_index") is None:
                data["chapter_index"] = index
            return data
        except (RuntimeError, ValueError) as exc:
            last_error = exc
            print(f"  [chapter {index}] attempt {attempt}/{OLLAMA_MAX_RETRIES} failed: {exc}")
    raise RuntimeError(f"Chapter {index} failed after {OLLAMA_MAX_RETRIES} attempts: {last_error}")


def _generate_layout_batched(
    epic: str,
    bookname: str,
    form: str,
    chapter_count: int,
    template: str,
) -> dict[str, object]:
    """Generate a complete book plan by batching chapters and looping to completion.

    Pass 1 requests chapters in contiguous batches of OLLAMA_BATCH_SIZE.  Pass 2
    is a completeness loop that re-requests any missing or under-written chapters
    until every chapter is present with a rich (150–200 word) summary, or the
    retry budget is exhausted.

    Returns the assembled book plan dict (not yet written to disk).
    """
    chapters_by_index: dict[int, dict[str, object]] = {}
    total_batches = (chapter_count + OLLAMA_BATCH_SIZE - 1) // OLLAMA_BATCH_SIZE

    # Pass 1 — contiguous batches of OLLAMA_BATCH_SIZE.
    for batch_num, batch_start in enumerate(range(0, chapter_count, OLLAMA_BATCH_SIZE), 1):
        batch_end = min(batch_start + OLLAMA_BATCH_SIZE, chapter_count)
        indices = list(range(batch_start + 1, batch_end + 1))
        print(f"  [{batch_num}/{total_batches}] Generating chapters {indices[0]}–{indices[-1]}…")
        for chapter in _generate_chapter_batch(epic, indices, batch_num, total_batches):
            chapters_by_index[int(chapter["chapter_index"])] = chapter
        print(f"  → {len(chapters_by_index)}/{chapter_count} chapters collected")

    # Pass 2 — completeness loop: fill missing and under-written chapters.
    # Re-request in chunks of OLLAMA_BATCH_SIZE so a single prompt never asks
    # for more than one batch of chapters (large one-shot requests make the
    # model emit malformed JSON).
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        needed = _incomplete_chapters(chapters_by_index, chapter_count)
        if not needed:
            break
        print(f"  completeness pass {attempt}: re-requesting chapters {needed}")
        for offset in range(0, len(needed), OLLAMA_BATCH_SIZE):
            chunk = needed[offset : offset + OLLAMA_BATCH_SIZE]
            for chapter in _generate_chapter_batch(epic, chunk, 0, 0):
                chapters_by_index[int(chapter["chapter_index"])] = chapter

    # Assemble in index order and normalize required fields.
    word_target = 500 if form == "poetry" else 4500
    chapters: list[dict[str, object]] = []
    for i in range(1, chapter_count + 1):
        chapter = chapters_by_index.get(i)
        if chapter is None:
            continue
        chapter.setdefault("name", str(i))
        chapter.setdefault("word_target", word_target)
        chapter.setdefault("further_references", [])
        chapters.append(chapter)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "book_name": bookname,
        "book_long_title": make_title(bookname, form),
        "generic": "আত্মঅনুসন্ধানী কবিতা" if form == "poetry" else "সাহিত্যিক কাহিনি",
        "era": "সমকালীন ও রূপক সময়",
        "language": "বাংলা",
        "target_audience": "বাংলা সাহিত্য ও মননশীল পাঠের পাঠক",
        "chapter_count": chapter_count,
        "form": form,
        "book_summary": "Generated via batched layout — update from storyline.md",
        "created_at": now,
        "updated_at": now,
        "user_name": "pijush",
        "gist": "Generated via batched layout — update from storyline.md",
        "chapters": chapters,
        "all_characters": [],
        "filter_chain": FILTER_CHAIN_POETRY if form == "poetry" else FILTER_CHAIN_NOVEL,
        "word_target": word_target,
    }


def _generate_layout_single(
    epic: str,
    bookname: str,
    form: str,
    template: str,
) -> dict[str, object]:
    """Generate a complete book plan in one Ollama call, with retries.

    Suitable for books with up to OLLAMA_BATCH_SIZE chapters.
    Returns the validated book plan dict.
    """
    prompt = render(
        _LAYOUT_SINGLE_PROMPT,
        bookname=json.dumps(bookname, ensure_ascii=False),
        form=json.dumps(form),
        template=template,
        epic=epic,
    )
    last_error: Exception | None = None
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        try:
            generated = _ollama_post(_ollama_payload(prompt))
            layout = extract_json(generated)
            validate_layout(layout, bookname, form)  # type: ignore[arg-type]
            return layout  # type: ignore[return-value]
        except (RuntimeError, ValueError) as exc:
            last_error = exc
            print(f"  layout attempt {attempt}/{OLLAMA_MAX_RETRIES} failed: {exc}")
    raise RuntimeError(
        f"Layout generation failed after {OLLAMA_MAX_RETRIES} attempts: {last_error}"
    )


def generate_layout(
    book_dir: Path,
    bookname: str,
    form: str | None = None,
    chapter_count: int | None = None,
    materials: str = "",
) -> None:
    """Generate (or regenerate) book.json from storyline.md using the local Ollama model.

    storyline.md is the source of truth: its chapter structure is expanded into the
    complete book.json plan.  When *chapter_count* exceeds OLLAMA_BATCH_SIZE the
    chapters are generated in batches of 10 with a completeness loop so the
    resulting book.json is always complete.  The plan is validated before it
    overwrites book.json, so a failed generation never clobbers an existing plan.

    *materials* is optional research-material text read from the book's
    materials/ folder; when non-empty it is appended to the prompt so the
    layout stays grounded in the user's sources.

    Args:
        book_dir:      Path to the backlog folder for this book.
        bookname:      Validated book name string.
        form:          'novel' or 'poetry'. Inferred from storyline.md if None.
        chapter_count: Target chapter count. If None, read from the existing book.json.
    """
    epic_file = book_dir / "storyline.md"
    legacy_epic_file = book_dir / "epic.md"
    if not epic_file.exists() and legacy_epic_file.exists():
        epic_file = legacy_epic_file
    if not epic_file.exists():
        raise FileNotFoundError(
            f"Epic not found: {epic_file}\n"
            "Create the backlog first with: python tools/book.py <bookname> init"
        )
    if not BOOK_TEMPLATE.exists():
        raise FileNotFoundError(f"Book template not found: {BOOK_TEMPLATE}")

    epic = epic_file.read_text(encoding="utf-8")
    if materials:
        epic = (
            epic
            + "\n\nRESEARCH MATERIALS (ground the layout in these; never contradict them):\n"
            + materials
            + "\n"
        )
    template = BOOK_TEMPLATE.read_text(encoding="utf-8")

    # Infer form from epic content when not supplied explicitly
    if form is None:
        form = "novel" if ("উপন্যাস" in epic or "novel" in epic.lower()) else "poetry"

    # Resolve chapter_count from the existing book.json when not supplied.
    if chapter_count is None:
        plan_file = book_dir / "book.json"
        if plan_file.exists():
            try:
                chapter_count = json.loads(
                    plan_file.read_text(encoding="utf-8")
                ).get("chapter_count")
            except (json.JSONDecodeError, OSError):
                chapter_count = None

    print(f"Generating layout via Ollama ({OLLAMA_MODEL}) — form: {form}, {chapter_count} chapters (one per request)")

    schema = _min_chapter_schema()
    chapters_by_index: dict[int, dict[str, object]] = {}
    for index in range(1, chapter_count + 1):
        try:
            chapter = _generate_chapter_one(epic, bookname, form, index, schema)
        except RuntimeError as exc:
            print(f"  [chapter {index}] generation failed ({exc}); using placeholder")
            chapter = _placeholder_chapter(index)
        chapters_by_index[index] = chapter
        title = chapter.get("chapter_title") or f"Chapter {index}"
        print(f"  → chapter {index}/{chapter_count}: {title}")

    word_target = 500 if form == "poetry" else 4500
    chapters: list[dict[str, object]] = []
    for i in range(1, chapter_count + 1):
        chapter = chapters_by_index.get(i) or _placeholder_chapter(i)
        chapter.setdefault("name", str(i))
        chapter.setdefault("word_target", word_target)
        chapter.setdefault("further_references", [])
        chapters.append(chapter)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    layout = {
        "book_name": bookname,
        "book_long_title": make_title(bookname, form),
        "generic": "আত্মঅনুসন্ধানী কবিতা" if form == "poetry" else "সাহিত্যিক কাহিনি",
        "era": "সমকালীন ও রূপক সময়",
        "language": "বাংলা",
        "target_audience": "বাংলা সাহিত্য ও মননশীল পাঠের পাঠক",
        "chapter_count": chapter_count,
        "form": form,
        "book_summary": "Generated via per-chapter layout — update from storyline.md",
        "created_at": now,
        "updated_at": now,
        "user_name": "pijush",
        "gist": "Generated via per-chapter layout — update from storyline.md",
        "chapters": chapters,
        "all_characters": [],
        "filter_chain": FILTER_CHAIN_POETRY if form == "poetry" else FILTER_CHAIN_NOVEL,
        "word_target": word_target,
    }

    # Propagate the LLM model/provider from the backlog template so every plan
    # pins its generation backend.
    model, provider = _template_model_provider()
    layout["model"] = model
    layout["provider"] = provider

    # Canonical filter_chain: poetry uses the poetry chain; novel copies the
    # authoritative template chain (which includes `seeds`).
    if form == "poetry":
        layout["filter_chain"] = FILTER_CHAIN_POETRY
    else:
        chain = _template_filter_chain()
        if chain:
            layout["filter_chain"] = chain

    out_file = book_dir / "book.json"
    out_file.write_text(
        json.dumps(layout, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Layout written → {out_file}\n"
        f"  model: {OLLAMA_MODEL} | chapters: {layout['chapter_count']} | form: {layout['form']}"
    )


# ---------------------------------------------------------------------------
# Backlog creation
# ---------------------------------------------------------------------------

IDEA_SYSTEM_PROMPT = BOOK_PROMPTS.text("idea_system_prompt.md")


def rewrite_gist_idea(bookname: str) -> None:
    """Rewrite the book's gist with AI assistance (the `init idea` subcommand).

    Reads the existing gist.md one-liner (or the book name if gist.md is absent),
    asks Ollama for a stronger single-sentence premise plus a short expansion,
    and writes both back to gist.md. It does not touch storyline.md or book.json.
    """
    book_dir = BACKLOG_ROOT / validate_bookname(bookname)
    book_dir.mkdir(parents=True, exist_ok=True)
    gist_file = book_dir / "gist.md"

    # Resolve the form (for the title) from the existing book plan, else novel.
    form = "novel"
    plan_file = book_dir / "book.json"
    if plan_file.exists():
        try:
            plan_form = json.loads(plan_file.read_text(encoding="utf-8-sig")).get("form")
            if plan_form in {"novel", "poetry"}:
                form = plan_form
        except (json.JSONDecodeError, OSError):
            pass

    # Preserve any existing `## Author Comment` section before rewriting.
    author_comment = ""
    if gist_file.exists():
        text = gist_file.read_text(encoding="utf-8-sig")
        marker = "## Author Comment"
        idx = text.find(marker)
        if idx != -1:
            author_comment = text[idx:].replace("## Author Comment", "").strip() + "\n"

    # Seed source: existing gist.md one-liner, else the book name.
    if gist_file.exists():
        lines = [
            line.strip()
            for line in gist_file.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.strip().startswith("##")
        ]
        seed = lines[0] if lines else bookname
    else:
        seed = bookname

    prompt = render(_GIST_IDEA_PROMPT, seed=seed)

    try:
        raw = _ollama_post(_ollama_payload(prompt, system=IDEA_SYSTEM_PROMPT))
        data = extract_json(raw, expect_list=False)
        if not isinstance(data, dict):
            raise ValueError("Idea response must be a JSON object.")
        gist = str(data.get("gist", "")).strip()
        expansion = str(data.get("expansion", "")).strip()
        if not gist:
            raise ValueError("Idea response is missing a non-empty 'gist'.")
    except (RuntimeError, ValueError) as exc:
        print(f"  warning: idea rewrite failed ({exc}); gist unchanged.")
        return

    body = format_gist_md(bookname, form, gist, expansion=expansion,
                          comment=author_comment.strip())
    gist_file.write_text(body, encoding="utf-8")

    print(f"Gist rewritten → {gist_file}")
    print(f"  gist: {gist}")
    print(f"  expansion: {expansion or '(none)'}")
    print("  Note: storyline.md and book.json are unchanged; re-run init to re-derive them.")


def create_gist(bookname: str, gist: str | None, form: str, refresh: bool) -> None:
    """Create or edit only gist.md for a book (the `init` command, no refresh).

    This is the gist-only boundary: it writes gist.md and nothing else. It never
    creates or rewrites storyline.md or book.json — those are produced by the
    `layout` command (or by `init` with the `refresh` flag).

    Args:
        bookname: Validated book name.
        gist:     Optional seed text supplied by the user.
        form:     'novel' or 'poetry' (used only to build a default gist when absent).
        refresh:  When True, overwrites an existing gist.md.
    """
    book_dir = BACKLOG_ROOT / validate_bookname(bookname)
    book_dir.mkdir(parents=True, exist_ok=True)

    gist_file = book_dir / "gist.md"

    # Resolve the gist: user argument → existing gist.md → auto-generated default.
    resolved_gist = gist.strip() if gist and gist.strip() else None
    if resolved_gist is None and gist_file.exists():
        resolved_gist = gist_file.read_text(encoding="utf-8").strip() or None
    resolved_gist = resolved_gist or default_gist(bookname, form)

    # Preserve any existing `## Author Comment` section when overwriting.
    existing_comment = ""
    if gist_file.exists():
        text = gist_file.read_text(encoding="utf-8-sig")
        marker = "## Author Comment"
        idx = text.find(marker)
        if idx != -1:
            existing_comment = text[idx:].rstrip()

    if not gist_file.exists() or refresh:
        comment_body = existing_comment.replace("## Author Comment", "").strip()
        body = format_gist_md(bookname, form, resolved_gist, comment=comment_body)
        gist_file.write_text(body, encoding="utf-8")

    print(f"Gist written → {gist_file}")
    print(f"  gist: {resolved_gist}")
    print("  Note: storyline.md and book.json are unchanged. "
          "Run `/book <bookname> layout` to derive them, "
          "or `/book <bookname> init ... refresh` to regenerate the full backlog.")


def create_backlog(
    bookname: str,
    gist: str | None,
    form: str,
    refresh: bool,
    chapter_count: int | None = None,
) -> None:
    """Create or refresh the full backlog (gist + storyline + book.json).

    This is the full-bootstrap path used by `init` with `refresh`. It writes:

        gist.md   — one-line seed (only written if missing or *refresh* is True)
        storyline.md   — full narrative foundation (always written)
        book.json — chapter layout plan (always written)
        materials/ — human-authored research materials folder (created empty)

    Args:
        bookname:      Validated book name.
        gist:          Optional seed text supplied by the user.
        form:          'novel' or 'poetry'.
        refresh:       When True, overwrites an existing gist.md.
        chapter_count: Optional explicit chapter count override.
    """
    book_dir = BACKLOG_ROOT / validate_bookname(bookname)
    book_dir.mkdir(parents=True, exist_ok=True)

    # Human-authored research materials folder — created empty, never overwritten.
    materials_dir = book_dir / "materials"
    materials_dir.mkdir(exist_ok=True)

    gist_file = book_dir / "gist.md"
    epic_file = book_dir / "storyline.md"
    legacy_epic_file = book_dir / "epic.md"
    if not epic_file.exists() and legacy_epic_file.exists():
        legacy_epic_file.replace(epic_file)
    book_file = book_dir / "book.json"

    seed = read_seed(book_dir)
    materials = read_materials(book_dir)

    # Resolve the gist: user argument → existing gist.md → auto-generated default
    resolved_gist = (gist.strip() if gist and gist.strip() else None)
    if resolved_gist is None and gist_file.exists():
        resolved_gist = gist_file.read_text(encoding="utf-8").strip() or None
    resolved_gist = resolved_gist or default_gist(bookname, form)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    # On refresh, preserve the existing plan (chapter count, chapters, and
    # book-level metadata) rather than regenerating placeholders. This matches
    # the documented refresh contract: "refresh preserves the chapter count and
    # the existing chapters array verbatim."
    existing_plan: dict[str, object] | None = None
    if refresh and book_file.exists():
        try:
            existing_plan = json.loads(book_file.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            existing_plan = None

    if existing_plan is not None:
        chapters = existing_plan.get("chapters", [])
        plan = dict(existing_plan)
        # Refresh only the premise-derived fields; keep identity and chapters.
        plan["gist"] = resolved_gist
        plan["book_summary"] = resolved_gist
        plan["updated_at"] = now
        plan["form"] = form
        plan["filter_chain"] = (
            FILTER_CHAIN_POETRY if form == "poetry" else FILTER_CHAIN_NOVEL
        )
        if chapter_count is not None and chapter_count != len(chapters):
            chapters = make_chapters(bookname, form, seed, chapter_count)
            plan["chapters"] = chapters
            plan["chapter_count"] = len(chapters)
    else:
        chapters = make_chapters(bookname, form, seed, chapter_count)
        plan = make_book_json(bookname, form, resolved_gist, chapters, now)

    epic_text = generate_epic(bookname, form, resolved_gist, chapters, now, materials)

    # Write gist.md only if it doesn't exist or refresh is requested
    if not gist_file.exists() or refresh:
        gist_file.write_text(format_gist_md(bookname, form, resolved_gist), encoding="utf-8")

    epic_file.write_text(epic_text, encoding="utf-8")
    book_file.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Backlog progress.json — customized from the template, copied to the
    # pipeline at scaffold time.
    progress_file = write_backlog_progress(book_dir)

    print(f"Backlog created → {book_dir}")
    print(f"  gist.md  : {gist_file}")
    print(f"  storyline.md  : {epic_file}")
    print(f"  book.json: {book_file}")
    print(f"  progress.json: {progress_file}")
    print(f"  materials/ : {materials_dir}")
    print(f"  form: {form} | chapters: {len(chapters)} | refreshed: {refresh}")


def run_layout(
    book_dir: Path,
    bookname: str,
    form: str,
    chapter_count: int | None,
    gist: str | None,
) -> None:
    """Run the `layout` command: rewrite storyline.md from gist.md + materials,
    then derive book.json (the layout).

    This is the layout boundary:

    1. storyline.md is (re)written from the gist in gist.md, grounded in any
       research materials under materials/.
    2. book.json is then derived from that storyline.md; an explicit chapter
       count and form control the resulting plan.

    Args:
        book_dir:      Path to the backlog folder for this book.
        bookname:      Validated book name string.
        form:          'novel' or 'poetry'.
        chapter_count: Optional explicit chapter count; None defers to book.json.
        gist:          Optional seed text supplied by the user.
    """
    gist_file = book_dir / "gist.md"

    # Resolve the gist from gist.md (user-supplied gist overrides it).
    resolved_gist = gist.strip() if gist and gist.strip() else None
    if resolved_gist is None and gist_file.exists():
        resolved_gist = gist_file.read_text(encoding="utf-8").strip() or None
    resolved_gist = resolved_gist or default_gist(bookname, form)

    materials = read_materials(book_dir)

    # 1. Rewrite storyline.md from the gist (+ materials).
    seed = read_seed(book_dir)
    chapters = make_chapters(bookname, form, seed, chapter_count)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    epic_text = generate_epic(bookname, form, resolved_gist, chapters, now, materials)
    (book_dir / "storyline.md").write_text(epic_text, encoding="utf-8")

    # 2. Derive book.json (the layout) from the (possibly refreshed) storyline.md.
    generate_layout(book_dir, bookname, form, chapter_count, materials)

    # 3. Create the backlog progress.json from the template, customized to the plan.
    progress_file = write_backlog_progress(book_dir)

    print(f"Layout complete → {book_dir}")
    print(f"  storyline.md  : {book_dir / 'storyline.md'}")
    print(f"  book.json: {book_dir / 'book.json'}")
    print(f"  progress.json: {progress_file}")
    print(f"  form: {form} | chapters: {chapter_count or '(from book.json)'}")


# ---------------------------------------------------------------------------
# Pipeline scaffold
# ---------------------------------------------------------------------------

def scaffold_novel(bookname: str, chapter_count: int, gist: str = "") -> None:
    """Build the workspaces/pipeline/<bookname>/ folder tree for a novel.

    Reads the backlog book.json to get the chapter plan and filter chain,
    then creates all required pipeline folders and placeholder files.

    The pipeline structure created:
        book.json, characters.json, override.txt
        filters/filters.json (registry only — no per-filter folders)
        chapters/<name>/model.json, chapter.md, history/
        chapters/<name>/segments/1/{segment.json, writer/, editor/, translator/, version/}

    Raises FileNotFoundError if the backlog book.json is missing (run init first).
    Raises FileExistsError  if the pipeline already exists (avoid silent re-scaffold).
    Raises ValueError        if the book.json does not match the requested novel form.
    """
    book_dir = BACKLOG_ROOT / bookname
    plan_file = book_dir / "book.json"
    if not plan_file.exists():
        raise FileNotFoundError(
            f"Backlog book plan not found: {plan_file}\n"
            "Run init first: python tools/book.py <bookname> init"
        )

    plan = json.loads(plan_file.read_text(encoding="utf-8-sig"))
    if plan.get("book_name") != bookname:
        raise ValueError(
            f"book.json book_name is {plan.get('book_name')!r} but expected {bookname!r}."
        )
    if plan.get("form") != "novel":
        raise ValueError(
            "scaffold_novel requires form='novel' in book.json. "
            "For poetry use: python tools/book.py <bookname> scaffold [count] poetry"
        )

    chapters = plan.get("chapters", [])
    # The chapter count is authoritative from book.json; ignore any supplied
    # count and scaffold exactly the chapters declared in the plan.
    chapter_count = len(chapters)

    pipeline = REPO_ROOT / "workspaces" / "pipeline" / bookname
    if pipeline.exists():
        raise FileExistsError(
            f"Pipeline already exists: {pipeline}\n"
            "Delete it manually if you want to re-scaffold."
        )
    pipeline.mkdir(parents=True)

    # --- Clone the complete v1 template tree into the pipeline root. ---
    # The pipeline starts as a verbatim copy of the backlog v1 template
    # (book.json, book.min.json, gist.md, gist copy.md,
    # override.txt, progress.json, storyline.md, and the layout/ form-tool
    # templates), then scaffold customizes it below. The layout/ folder it
    # clones holds the form tool templates (write-novel, write-poetry,
    # enrich-novel, enrich-poetry); the book's own chapter folders are created
    # afterwards in chapters/ alongside it.
    if BACKLOG_V1_TEMPLATE.is_dir():
        for child in BACKLOG_V1_TEMPLATE.iterdir():
            dest = pipeline / child.name
            if child.is_dir():
                shutil.copytree(child, dest)
            else:
                shutil.copy2(child, dest)

    # --- Copy the backlog source files (gist.md, storyline.md, progress.json) verbatim ---
    for src_name in ("gist.md", "storyline.md", "progress.json"):
        src = book_dir / src_name
        if src.is_file():
            shutil.copy2(src, pipeline / src_name)

    # --- Root pipeline files ---
    (pipeline / "book.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (pipeline / "characters.json").write_text(
        json.dumps(
            {"book_name": bookname, "characters": [], "character_groups": []},
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    (pipeline / "override.txt").write_text("No transform required.\n", encoding="utf-8")

    # --- Filter registry (filters.json only; no per-filter folders) ---
    filter_chain = plan.get("filter_chain", FILTER_CHAIN_NOVEL)
    filters_dir = pipeline / "filters"
    filters_dir.mkdir()

    registry = {
        "filters": [
            {
                "order": order,
                "name": name,
                "agent": f".framework/filters/{name}/SKILL.md",
                "autorun": name not in {"workshop", "override"},  # batch-disabled by default
            }
            for order, name in enumerate(filter_chain, 1)
        ]
    }
    (filters_dir / "filters.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Filter folders are created lazily on first run, not at scaffold.

    # --- Chapter folders ---
    chapters_dir = pipeline / "chapters"
    for ch in chapters:
        ch_name = str(ch["name"])
        chapter_dir = chapters_dir / ch_name
        segment_dir = chapter_dir / "segments" / "1"

        # Create all required sub-folders
        for sub in (
            chapter_dir / "history",
            segment_dir / "writer",
            segment_dir / "editor",
            segment_dir / "translator",
            segment_dir / "version",
        ):
            sub.mkdir(parents=True, exist_ok=True)

        # Chapter-level chapter.json (runtime metadata)
        chapter_model = {
            **ch,
            "level": "chapter",
            "state": "scaffolded",
            "segments": [1],
        }
        (chapter_dir / "chapter.json").write_text(
            json.dumps(chapter_model, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Bare chapter.md placeholder — layout agent (Phase 2) will seed content
        chapter_title = ch.get("chapter_title", ch_name)
        chapter_summary = ch.get("chapter_summary", "")
        (chapter_dir / "chapter.md").write_text(
            f"# {chapter_title}\n\n## Workshop\n\n{chapter_summary}\n\n"
            "## Story\n\n## Discussion\n",
            encoding="utf-8",
        )

        # Segment-level segment.json
        (segment_dir / "segment.json").write_text(
            json.dumps(
                {
                    "level": "segment",
                    "state": "returning",
                    "chapter_index": ch.get("chapter_index"),
                    "segment_index": 1,
                },
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )

    print(f"Scaffolded novel pipeline → {pipeline} ({chapter_count} chapters)")


# ---------------------------------------------------------------------------
# Sub-module loaders
# ---------------------------------------------------------------------------

def _load_module(name: str, script: str):
    """Dynamically load a tools/ Python module by file path.

    This avoids adding tools/ to sys.path while still allowing book.py to
    dispatch to enrich.py, write.py, and publish.py without subprocess overhead.

    Args:
        name:   Internal module identifier (used as the module's __name__).
        script: Filename relative to BASE_DIR (e.g. 'enrich.py').

    Raises RuntimeError if the module file is not found or cannot be loaded.
    """
    module_path = BASE_DIR / script
    if not module_path.exists():
        raise RuntimeError(
            f"Required tool not found: {module_path}\n"
            f"Ensure {script} is present in tools/."
        )
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to create module spec for {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _chapter_model_file(chapter_dir: Path) -> Path:
    """Resolve a chapter's metadata file, preferring `chapter.json` over `model.json`."""
    for name in ("chapter.json", "model.json"):
        candidate = chapter_dir / name
        if candidate.exists():
            return candidate
    return chapter_dir / "chapter.json"


def run_tool(script: str, arguments: list[str]) -> None:
    """Invoke a tools/ script as a subprocess with the current interpreter.

    Use this for tools that cannot be loaded as modules (e.g. they use
    if __name__ == '__main__' guards with side effects at import time).
    """
    command = [sys.executable, str(BASE_DIR / script), *arguments]
    subprocess.run(command, check=True)


# ---------------------------------------------------------------------------
# Workflow helpers
# ---------------------------------------------------------------------------

def positional_target(args: argparse.Namespace, default: str = "all") -> str:
    """Extract a chapter/filter range from the uniform positional argument slots.

    Skips known keyword values (form names, structural keywords, and the
    `offline`/`online` execution-mode tokens) so that
    'python book.py mybook write all novel' correctly resolves target='all',
    and 'python book.py mybook enrich * offline' resolves target='*'.
    """
    reserved = {"gist", "epic", "count", "chapter-count", "poetry", "novel",
                "offline", "online"}
    for value in (args.range, args.option, args.objective):
        if value and value not in reserved:
            return value
    return default


def enrich_workflow(bookname: str, target: str) -> None:
    """Run the enrich engine (enrich.py) in-process for the given chapter range.

    Loads enrich.py as a module, resolves the chapter list, loads all chapter
    models for cross-chapter context, then enriches each requested chapter.
    Prints a summary of successes and failures.
    """
    enrich = _load_module("writer_enrich_engine", "enrich.py")
    chapters_root = enrich.resolve_chapters_root(bookname)
    numbers = enrich.parse_chapter_input(target, chapters_root)
    book = enrich.load_book_model(bookname)
    gist, storyline = enrich.load_book_sources(bookname)
    sources = "\n\n".join(part for part in (gist, storyline) if part)

    # Load the form-specific templates (lenses, twists, prompts) before enriching,
    # so the engine never runs with an empty lens/twist set. Prefer the book's own
    # pipeline layout/ folder; fall back to the shared framework template.
    enrich.load_templates(enrich.resolve_book_form(bookname), enrich.resolve_layout_dir(bookname))

    # Resolve the model BEFORE any Ollama call (style regeneration included). If
    # the pipeline book.json declares no model, resolve_model raises and the agent
    # stops without assuming a default.
    model_name = enrich.resolve_model(bookname)

    # Ensure the pipeline style.md exists and is grounded in the current book.
    enrich.regenerate_style_md(bookname, book, model_name=model_name)

    # Pre-load all chapter models to give the enrich engine cross-chapter context
    all_models: dict[int, object] = {}
    for num in enrich.parse_chapter_input("all", chapters_root):
        try:
            all_models[num] = enrich.read_model(_chapter_model_file(chapters_root / str(num)))
        except (OSError, ValueError) as exc:
            if getattr(enrich, "VERBOSE", False):
                print(f"[v] [{num}] model unreadable (skipped as context): {exc}")

    failures = 0
    for num in numbers:
        try:
            enrich.enrich_chapter(_chapter_model_file(chapters_root / str(num)), book, all_models,
                                  model_name=model_name, sources=sources)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{num}] FAILED: {exc}", file=sys.stderr)
            failures += 1

    successes = len(numbers) - failures
    print(f"Enrich complete. {successes} succeeded, {failures} failed.")
    if failures:
        raise RuntimeError(f"{failures} chapter(s) failed enrichment.")


def write_workflow(bookname: str, target: str, style: str | None = None) -> None:
    """Run the chapter writer (write.py) in-process for the given chapter range.

    Loads write.py as a module, resolves the chapter list, and writes each
    requested chapter.  An optional *style* nickname selects the transformer
    style; when omitted, the book's own style.md (or the form-bound default —
    `pijush` for poetry, `dialogue` for novel) is used.
    """
    writer = _load_module("writer_write_engine", "write.py")
    chapters_root = writer.resolve_chapters_root(bookname)
    numbers = writer.parse_chapter_input(target, chapters_root)

    if style:
        # Validate the nickname early so an unknown style fails fast. The check
        # is form-aware: poetry resolves presets, novels resolve novel styles.
        form = writer.resolve_book_form(chapters_root / str(numbers[0])) if numbers else "poetry"
        if form == "poetry":
            writer.resolve_preset(style)
        else:
            writer.resolve_novel_style(style)

    failures = 0
    total = len(numbers)
    for position, num in enumerate(numbers, 1):
        print(f"[{position}/{total}] Writing chapter {num} ...", flush=True)
        try:
            # Pass style=None when omitted so the writer falls back to the
            # book's style.md / form-bound default instead of a hardcoded preset.
            writer.write_chapter(
                _chapter_model_file(chapters_root / str(num)),
                style=style,
            )
            print(f"[{position}/{total}] Chapter {num} done.", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{num}] FAILED: {exc}", file=sys.stderr)
            failures += 1

    successes = len(numbers) - failures
    print(f"Write complete. {successes} succeeded, {failures} failed.")
    if failures:
        raise RuntimeError(f"{failures} chapter(s) failed writing.")


def cleanup_workflow(bookname: str, target: str) -> None:
    """Reset the selected pipeline chapters back to their scaffolded baseline.

    For each chapter in ``target`` (a number/range/list/'all'/'*'):

    - Delete ``chapter.md`` and ``context.md``.
    - Clear ``history/`` and the per-segment ``writer/``, ``editor/``,
      ``translator/``, and ``version/`` folders.
    - Reinitialize ``chapter.json`` from the root ``book.json`` plan entry,
      dropping runtime fields (``creative_enrichment``, ``draft``,
      ``state`` → ``scaffolded``, ``level``, ``segments``).
    - Reinitialize ``segment.json`` to the pending baseline.

    The root ``book.json`` is never touched. Prior content is removed
    permanently; this is a destructive reset.
    """
    writer = _load_module("writer_write_engine", "write.py")
    chapters_root = writer.resolve_chapters_root(bookname)
    numbers = writer.parse_chapter_input(target, chapters_root)

    pipeline = chapters_root.parent
    book_file = pipeline / "book.json"
    if not book_file.exists():
        book_file = pipeline / "model.json"
    book = read_json(book_file)
    plan_by_name = {str(entry.get("name")): entry for entry in book.get("chapters", [])}

    cleared = 0
    for num in numbers:
        chapter_dir = chapters_root / str(num)
        if not chapter_dir.is_dir():
            print(f"  [{num}] SKIP: chapter folder not found", file=sys.stderr)
            continue

        name = str(num)
        baseline = plan_by_name.get(name)
        if baseline is None:
            print(f"  [{num}] SKIP: no baseline entry in book.json", file=sys.stderr)
            continue

        # 1. Delete the live draft and flattened context.
        for fname in ("chapter.md", "context.md"):
            f = chapter_dir / fname
            if f.exists():
                f.unlink()

        # 2. Clear history/ and per-segment output folders.
        for folder in ("history", "segments/1/writer", "segments/1/editor",
                       "segments/1/translator", "segments/1/version"):
            path = chapter_dir / folder
            if path.is_dir():
                for child in path.iterdir():
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()

        # 3. Reinitialize chapter.json from the baseline plan entry.
        chapter_json = chapter_dir / "chapter.json"
        write_json(chapter_json, dict(
            baseline,
            level="chapter",
            state="scaffolded",
            segments=[1],
        ))
        # Drop a legacy model.json if present, to avoid dual sources of truth.
        legacy_model = chapter_dir / "model.json"
        if legacy_model.exists():
            legacy_model.unlink()

        # 4. Reinitialize segment.json to the pending baseline.
        seg_json = chapter_dir / "segments/1/segment.json"
        write_json(seg_json, {
            "level": "segment",
            "state": "pending",
            "chapter_index": baseline.get("chapter_index", num),
            "segment_index": 1,
        })

        print(f"  [{num}] Cleaned and reinitialized.")
        cleared += 1

    print(f"Cleanup complete. {cleared} chapter(s) reset, "
          f"{len(numbers) - cleared} skipped.")


def _review_target_and_language(args: argparse.Namespace) -> tuple[str, str | None]:
    """Split the review command into a chapter scope and an optional language.

    ``/book <book> review all bengali`` → ``("all", "bengali")``. The chapter
    scope is the first slot that looks like a target (``all``, ``*``, a number,
    or a range ``N-M``); any other non-reserved token is the language. Defaults
    to ``("all", None)`` — the engine then defaults the language to Bengali.
    """
    slots = [args.objective, args.option, args.range, *args.extra]
    reserved = {"gist", "epic", "count", "chapter-count", "poetry", "novel",
                "offline", "online"}

    def _is_target(value: str) -> bool:
        v = value.strip()
        if v in {"all", "*"}:
            return True
        if v.isdigit():
            return True
        if re.fullmatch(r"[0-9]+-[0-9]+", v):
            return True
        return False

    target = "all"
    language = None
    for value in slots:
        if not value:
            continue
        if _is_target(value):
            if target == "all":
                target = value
            continue
        if value not in reserved:
            language = value
            break
    return target, language


def _write_style(args: argparse.Namespace) -> tuple[str, str | None]:
    """Split the write target from an optional 'style <nickname>' modifier.

    ``/book <book> write * style desh`` puts ``*`` in ``objective``,
    ``style`` in ``option``, and ``desh`` in ``range``. This returns the
    effective chapter target plus the style nickname when present.
    """
    style = None
    target = positional_target(args)
    slots = [args.objective, args.option, args.range, *args.extra]
    lowered = [s.lower() if s else s for s in slots]
    if "style" in lowered:
        idx = lowered.index("style")
        if idx + 1 < len(slots) and slots[idx + 1]:
            style = slots[idx + 1]
        # The chapter target is the first slot that is neither 'style' nor its value.
        reserved = {"style", style.lower() if style else None, "gist", "epic", "count", "chapter-count", "poetry", "novel"}
        for value in slots:
            if value and value not in reserved and value not in {"all", "*", ""}:
                target = value
                break
            if value in {"all", "*"}:
                target = value
                break
    return target, style


def publish_workflow(bookname: str, language: str | None = None, draft: bool = False) -> None:
    """Promote pipeline segments to workspaces/published/ via publish.py.

    The current publisher supports writer-stage chapter drafts only; the
    *language* parameter is reserved for future translator-stage support.
    When *draft* is True, publication bypasses the quality-pass and
    registered-draft validation and publishes the current drafts forcefully.
    """
    if language:
        raise ValueError(
            "Language-specific publish is not yet supported. "
            "Omit the language argument to publish writer-stage drafts."
        )
    publisher = _load_module("writer_publish_engine", "publish.py")
    publisher.publish(bookname, draft=draft)


def review_workflow(bookname: str, target: str, language: str | None = None) -> None:
    """Run the quality review engine (review.py) on selected chapters.

    *language* is the normalization target (default Bengali): foreign-language
    fragments in each chapter are rewritten into it before the audit.
    """
    review = _load_module("writer_review_engine", "review.py")
    chapters_root = review.resolve_chapters_root(bookname)
    numbers = review.parse_chapter_input(target, chapters_root)
    if not numbers:
        print("No chapters to review.")
        return
    book = review.load_book_model(bookname)
    review.regenerate_style_md(bookname, book)
    review.run_review(bookname, target, language=language)


def humanize_workflow(bookname: str, target: str) -> None:
    """Run the humanize engine (humanize.py) on selected chapters."""
    humanize = _load_module("writer_humanize_engine", "humanize.py")
    chapters_root = humanize.resolve_chapters_root(bookname)
    numbers = humanize.parse_chapter_input(target, chapters_root)
    if not numbers:
        print("No chapters to humanize. Write chapters first.")
        return
    humanize.run_humanize(bookname, target)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    The parser uses a uniform positional command shape:
        book.py <bookname> <verb> <objective> <option> <range> [extra...]

    Named flags (--gist, --type, --refresh, --layout) are available for
    cases where positional disambiguation is ambiguous.
    """
    parser = argparse.ArgumentParser(
        prog="book.py",
        description="Unified book workflow CLI for the writer agentic framework.",
        epilog=(
            "Uniform command shape:\n"
            "  book.py <bookname> <verb> <objective> <option> <range>\n\n"
            "Quick examples:\n"
            "  python tools/book.py cosmos init \"মহাবিশ্বের রহস্য\" poetry\n"
            "  python tools/book.py cosmos layout 30 poetry\n"
            "  python tools/book.py mynovel scaffold 15 novel\n"
            "  python tools/book.py mynovel enrich all\n"
            "  python tools/book.py mynovel write 1-5\n"
            "  python tools/book.py mynovel publish\n\n"
            "Run 'python tools/book.py help' to show full usage."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "bookname",
        help="Book folder name under workspaces/backlog/ (no path separators).",
    )
    parser.add_argument(
        "verb",
        nargs="?",
        choices=("build", "layout", "backlog", "init", "scaffold", "filter", "enrich", "review", "humanize", "write", "publish", "preview", "cleanup", "style", "poet", "poetry", "poem", "line", "rhyme", "lyrics", "limerick", "limeric", "haiku"),
        help="Workflow action to perform.",
    )
    parser.add_argument(
        "objective",
        nargs="?",
        help="Primary target — e.g. 'gist', 'epic', or a chapter number.",
    )
    parser.add_argument(
        "option",
        nargs="?",
        help="Secondary option — e.g. seed text, form ('novel'/'poetry'), or count.",
    )
    parser.add_argument(
        "range",
        nargs="?",
        help="Range or modifier — e.g. 'all', '1-5', 'continue', 'novel', 'poetry'.",
    )
    parser.add_argument(
        "extra",
        nargs="*",
        help="Optional trailing modifiers such as 'refresh'.",
    )
    parser.add_argument(
        "--gist",
        metavar="TEXT",
        help="Explicit seed text for gist.md and storyline.md (alternative to positional argument).",
    )
    parser.add_argument(
        "-t", "--type",
        dest="book_type",
        choices=("poetry", "novel"),
        default=None,
        help="Book form override (defaults to the book plan's form, else poetry).",
    )
    parser.add_argument(
        "-r", "--refresh",
        action="store_true",
        help="Overwrite existing gist.md when running init or build.",
    )
    parser.add_argument(
        "--layout",
        action="store_true",
        help="Regenerate book.json from storyline.md via Ollama after backlog creation.",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Publish from current chapter-root drafts, bypassing quality-pass validation.",
    )
    return parser


# ---------------------------------------------------------------------------
# Workflow dispatcher
# ---------------------------------------------------------------------------

def dispatch_workflow(args: argparse.Namespace, bookname: str, book_dir: Path) -> None:
    """Route a parsed verb to the appropriate workflow function.

    This is the central dispatch table for all pipeline-stage verbs.  Each
    branch reads the relevant positional slots, resolves ambiguous values, and
    calls the matching workflow function.
    """
    verb = args.verb

    if verb == "scaffold":
        # A form is only explicit when the user passed `novel` or `poetry` in a
        # positional slot; resolve_form's default must not mask the book plan.
        form_explicit = any(
            value in {"novel", "poetry"} for value in (args.range, args.option, args.book_type)
        )
        form = resolve_form([args.range, args.option, args.book_type])
        count = resolve_count([args.option, args.range, args.objective])
        # Fall back to the backlog book plan for form and count when not supplied
        # positionally, so `scaffold` honors the book's declared form.
        plan_file = book_dir / "book.json"
        plan: dict[str, object] = {}
        if plan_file.exists():
            try:
                plan = json.loads(plan_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                plan = {}
        if count is None:
            count = plan.get("chapter_count") if isinstance(plan.get("chapter_count"), int) else None
        if not form_explicit:
            plan_form = plan.get("form")
            if plan_form in {"novel", "poetry"}:
                form = plan_form
        if count is None:
            raise ValueError(
                "scaffold requires a chapter count.\n"
                "Supply it as a positional argument or ensure book.json has 'chapter_count'."
            )
        if form == "poetry":
            tool_args = [bookname, "--count", str(count), "--form", form]
            if args.gist:
                tool_args += ["--gist", args.gist]
            run_tool("scaffold.py", tool_args)
        else:
            scaffold_novel(bookname, count, args.gist or "")
        return

    if verb == "write":
        target, style = _write_style(args)
        write_workflow(bookname, target, style)
        return

    if verb == "cleanup":
        cleanup_workflow(bookname, positional_target(args))
        return

    if verb == "enrich":
        enrich_workflow(bookname, positional_target(args))
        return

    if verb == "publish":
        language = next(
            (v for v in (args.objective, args.option, args.range)
             if v and v not in {"all", "*"}),
            None,
        )
        publish_workflow(bookname, language, draft=args.draft)
        return

    if verb == "preview":
        # Assemble the same output as publish but skip the quality gate/review.
        publish_workflow(bookname, None, draft=True)
        return

    if verb == "filter":
        raise ValueError(
            "'filter' has no standalone runner in tools/.\n"
            "Invoke the registered filter agent through /book or run the filter agent directly."
        )

    # Agentic-only verbs — no standalone Python runner. Route through their agent.
    if verb in {"style", "poet", "poetry", "poem", "line", "rhyme", "lyrics", "limerick", "limeric", "haiku"}:
        raise ValueError(
            f"'{verb}' has no standalone runner in tools/.\n"
            "Invoke it through /book (or .framework/workflows/book.md) so the "
            "corresponding agent (and its skill) handles the work directly."
        )

    if verb == "review":
        target, language = _review_target_and_language(args)
        review_workflow(bookname, target, language)
        return

    if verb == "humanize":
        humanize_workflow(bookname, positional_target(args))
        return

    raise ValueError(f"Unsupported workflow verb: {verb!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse arguments, resolve the workflow, and dispatch.

    Returns 0 on success, 1 on any handled error.
    """
    args = build_parser().parse_args()

    # Allow 'python book.py help' as an alias for --help
    if args.bookname in {"help", "--help"} and args.verb is None:
        build_parser().print_help()
        return 0

    try:
        bookname = validate_bookname(args.bookname)
        book_dir = BACKLOG_ROOT / bookname

        # Treat 'refresh' as a modifier flag regardless of which positional
        # slot it lands in (objective, option, range, or extra).
        all_positional = [args.objective, args.option, args.range, *args.extra]
        if any(item and item.lower() == "refresh" for item in all_positional):
            args.refresh = True

        # Resolve form: positional slots take priority over the --type flag
        form = resolve_form([args.option, args.range], fallback=args.book_type)

        # Resolve gist: positional objective (when objective == 'gist' → use option),
        # else option itself if it's not a keyword, else --gist flag.
        gist: str | None = None
        if args.objective == "gist" and args.option:
            gist = args.option
        elif args.objective and args.objective not in {"gist", "build", "epic", "novel", "poetry", "refresh"} \
                and not (args.objective.isdecimal()):
            gist = args.objective
        gist = gist or args.gist

        # --- init (and alias backlog) ---
        if args.verb in {"init", "backlog"}:
            # Subcommand: 'idea' rewrites the gist with AI and stops.
            if args.objective == "idea":
                rewrite_gist_idea(bookname)
                return 0
            resolved_form = resolve_form([args.option, args.range], fallback=form)
            # Gist: first non-keyword positional argument wins
            resolved_gist = next(
                (v for v in (args.objective, args.option)
                 if v and v not in {"gist", "build", "epic", "novel", "poetry", "refresh"}),
                args.gist,
            )
            if args.refresh:
                # refresh → full bootstrap: gist.md + storyline.md + book.json
                create_backlog(bookname, resolved_gist, resolved_form, refresh=True)
            else:
                # no refresh → gist.md only
                create_gist(bookname, resolved_gist, resolved_form, refresh=False)
            return 0

        # --- layout / build ---
        if args.verb in {"build", "layout"}:
            count = resolve_count([args.objective, args.option, args.range])
            layout_form = resolve_form([args.range, args.option], fallback=form)
            run_layout(book_dir, bookname, layout_form, count, gist)
            return 0

        # --- all other pipeline verbs ---
        dispatch_workflow(args, bookname, book_dir)
        return 0

    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
