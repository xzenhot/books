#!/usr/bin/env python3
"""book.py — Unified book workflow CLI for the writer agentic framework.

This tool manages the full book lifecycle from backlog creation through
pipeline scaffolding and chapter execution. It wraps Ollama for AI-assisted
layout generation and delegates enrichment, writing, and publishing to the
dedicated engine modules (enrich.py, write.py, publish.py).

USAGE
-----
    python .tools/book.py <bookname> <verb> [options...]

VERBS
-----
    init      Create backlog artifacts (gist.md, epic.md, book.json) then
              generate book.json layout via Ollama.

              python .tools/book.py <bookname> init ["seed text"] [novel|poetry]

              python .tools/book.py <bookname> init idea   # rewrite the gist with AI

    build     Alias for init with an optional chapter count as the first
              positional argument after the verb.

              python .tools/book.py <bookname> build 20 novel

    layout    Regenerate book.json from an existing epic.md via Ollama.
              Does not touch gist.md or epic.md.

              python .tools/book.py <bookname> layout [novel|poetry]

    scaffold  Build the pipeline folder structure (.space/pipeline/<bookname>/)
              from the backlog book.json. Requires init to have run first.

              python .tools/book.py <bookname> scaffold [count] [novel|poetry]

    enrich    Run the enrich engine (enrich.py) on selected chapters.

              python .tools/book.py <bookname> enrich [all|1|1-5|continue]

    write     Run the chapter writer (write.py) on selected chapters.

              python .tools/book.py <bookname> write [all|1|1-5|continue]

    publish   Promote pipeline segments to source/books/ via publish.py.

              python .tools/book.py <bookname> publish

COMMON FLAGS
------------
    -t, --type  poetry|novel   Override book form (default: poetry)
    -r, --refresh              Overwrite existing gist.md when running init
    --gist "text"              Explicit seed text (alternative to positional arg)

EXAMPLES
--------
    # Create a Bengali poetry book from scratch
    python .tools/book.py cosmos init "মহাবিশ্বের অসীম রহস্য" poetry

    # Regenerate layout from an existing epic (large book, batched)
    python .tools/book.py cosmos layout 30 poetry

    # Scaffold novel pipeline then enrich all chapters
    python .tools/book.py mynovel scaffold 15 novel
    python .tools/book.py mynovel enrich all

    # Write chapters 1–5 then publish
    python .tools/book.py mynovel write 1-5
    python .tools/book.py mynovel publish
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent          # .tools/
REPO_ROOT = BASE_DIR.parent                          # repo root
EPIC_ROOT = REPO_ROOT / ".space" / "backlog" / "epic"
BOOK_TEMPLATE = REPO_ROOT / ".framework" / "templates" / "book.json"

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

LAYOUT_SYSTEM_PROMPT = (
    "You are the book-plan architect for a literary pipeline.\n"
    "Your task is structural planning, not prose generation.\n\n"
    "CONTRACT:\n"
    "- Return exactly one valid JSON object — no Markdown fences, no commentary.\n"
    "- Use only the field names present in the supplied template.\n"
    "- Derive chapter count, titles, summaries, and references from the epic; never invent a different premise.\n"
    "- Every chapter must have: chapter_index, name, chapter_title, chapter_summary, "
    "word_target (positive integer), further_references (array).\n"
    "- Every chapter_summary must be 2–4 sentences (roughly 150–200 words) describing what "
    "the chapter explores — its conflict, imagery, and open question; never a one-line placeholder.\n"
    "- chapter_count must equal the length of the chapters array.\n"
    "- filter_chain must be a non-empty ordered array of filter names.\n"
    "- Do not write chapter prose, filter results, or runtime pipeline state."
)

EPIC_SYSTEM_PROMPT = (
    "You are the founding author and narrative architect for a Bengali literary book.\n"
    "You expand a short seed (gist) into the book's epic.md — the narrative source of truth\n"
    "that later guides chapter writing, filtering, and editing.\n\n"
    "CONTRACT:\n"
    "- Write entirely in fluent, literary Bengali (বাংলা).\n"
    "- Produce Markdown using only the section headings given in the prompt, in that order.\n"
    "- Expand and deepen the seed; never contradict or replace its core idea.\n"
    "- Be concrete and specific: images, tensions, motifs, names — not generic filler.\n"
    "- The epic is a plan and compass, not final prose; keep summaries evocative but open.\n"
    "- Preserve the exact chapter count and titles supplied; do not add or remove chapters.\n"
    "- Leave open questions that later chapters will resolve.\n"
    "- Output the epic body only; do not invent a metadata header."
)

# Minimal chapter schema description sent in batch prompts
BATCH_CHAPTER_SCHEMA = (
    '{"chapter_index": 1, "name": "1", "word_target": 500, '
    '"chapter_title": "Title", '
    '"chapter_summary": "A 2–4 sentence, 150–200 word description of what this chapter '
    'explores — its central conflict, key imagery, and the open question it leaves.", '
    '"further_references": []}'
)


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
    return {
        "book_name": bookname,
        "book_long_title": make_title(bookname, form),
        "generic": "আত্মঅনুসন্ধানী কবিতা" if form == "poetry" else "সাহিত্যিক কাহিনি",
        "era": "সমকালীন ও রূপক সময়",
        "language": "বাংলা",
        "target_audience": "বাংলা সাহিত্য ও মননশীল পাঠের পাঠক",
        "chapter_count": len(chapters),
        "form": form,
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


def make_epic(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
    now: str,
) -> str:
    """Render a Bengali epic.md from the backlog plan.

    The epic is the narrative source of truth for the book.  This function
    produces the initial scaffold version; human editing or Ollama can
    enrich it later.
    """
    form_label = "কবিতা" if form == "poetry" else "উপন্যাস"
    lines = [
        f"# {make_title(bookname, form)}",
        "",
        f"- **Book name:** {bookname}",
        f"- **Epic path:** .space/backlog/{bookname}/epic.md",
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
    """Build the deterministic metadata header for an epic.md file.

    This block carries the fields the pipeline parses (form, chapter count,
    gist, language) and must precede any Ollama-enriched narrative body.
    """
    form_label = "কবিতা" if form == "poetry" else "উপন্যাস"
    return "\n".join([
        f"# {make_title(bookname, form)}",
        "",
        f"- **Book name:** {bookname}",
        f"- **Epic path:** .space/backlog/{bookname}/epic.md",
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
    return (
        f"Expand the seed (gist) below into the complete narrative foundation "
        f"(epic) for a Bengali {form_label}.\n\n"
        f"BOOK NAME: {bookname}\n"
        f"FORM: {form} ({form_label})\n"
        f"GIST (seed):\n{gist}\n\n"
        f"CHAPTER PLAN ({len(chapters)} chapters — keep this exact count and these titles):\n"
        f"{chapter_plan}\n\n"
        "Write the epic body as Markdown using EXACTLY these sections, in order:\n\n"
        "## মূল ভাবনা\n"
        "Restate and deepen the gist into one unifying thesis. Explain why this "
        "subject matters and what the book hopes to reveal.\n\n"
        "## বিষয়গত সূত্র\n"
        "List 3–5 recurring motifs, images, or questions that thread through the chapters.\n\n"
        "## পর্বের বিন্যাস\n"
        "One '### {index}. {title}' heading per chapter, followed by a 2–3 sentence "
        "summary that deepens the supplied chapter_summary. Keep the exact titles and count.\n\n"
        "## চরিত্র ও কণ্ঠস্বর\n"
        "For a novel: name key characters, their desires and conflicts. "
        "For poetry: describe the speaking voice(s) and the recurring 'I'.\n\n"
        "## ভাষা ও কাব্যিক/আখ্যানিক অভিমুখ\n"
        "Describe the register, rhythm, and imagery strategy.\n\n"
        "## আবেগের গন্তব্য\n"
        "Where the book should leave the reader, and which questions stay open.\n\n"
        "RULES:\n"
        "- Write entirely in fluent literary Bengali.\n"
        "- Be specific and concrete; avoid generic filler.\n"
        "- The epic is a compass for later writing — evocative but open, never final prose.\n"
        "- Do not change the book name, form, or chapter count.\n"
        "- Output only the epic body — the metadata header is added separately."
    )


def generate_epic(
    bookname: str,
    form: str,
    gist: str,
    chapters: list[dict[str, object]],
    now: str,
) -> str:
    """Enrich the gist into a full epic.md via Ollama, falling back to the scaffold.

    Calls Ollama with the epic prompt; on success, prepends the deterministic
    metadata header to the model's narrative body.  On any network/parse error
    it degrades gracefully to the deterministic make_epic() scaffold.
    """
    try:
        prompt = build_epic_prompt(bookname, form, gist, chapters)
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

def extract_json(
    response: str,
    expect_list: bool = False,
) -> list[object] | dict[str, object]:
    """Parse a JSON value from a raw Ollama response string.

    Handles two common Ollama output patterns:
    1. A bare JSON object or array.
    2. JSON wrapped in a Markdown code fence (```json ... ```).

    When *expect_list* is True the result must be a list; a dict with a
    'chapters' key is unwrapped automatically.  Raises ValueError when the
    result type does not match the expectation.
    """
    cleaned = response.strip()

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
        # Fall back: locate the outermost bracket pair and parse that slice
        open_char, close_char = ("[", "]") if expect_list else ("{", "}")
        start = cleaned.find(open_char)
        end = cleaned.rfind(close_char)
        if start < 0 or end <= start:
            raise ValueError(
                f"Ollama response does not contain a JSON {'array' if expect_list else 'object'}.\n"
                f"Raw response (first 300 chars): {response[:300]}"
            )
        data = json.loads(cleaned[start : end + 1])

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
        if _summary_word_count(summary) < SUMMARY_MIN_WORDS:
            raise ValueError(
                f"Chapter {i} has an under-written chapter_summary "
                f"({_summary_word_count(summary)} words; expected 150–200)."
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

def _summary_word_count(summary: object) -> int:
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
        if chapter is not None and _summary_word_count(chapter.get("chapter_summary", "")) < SUMMARY_MIN_WORDS:
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
    prompt = (
        f"Generate ONLY these chapters for the book described below: {indices_str}.\n"
        "Return a JSON array of chapter objects — one object per index listed. "
        "Use this schema for each object:\n"
        f"{BATCH_CHAPTER_SCHEMA}\n\n"
        "IMPORTANT: chapter_summary must be 2–4 sentences (150–200 words) describing "
        "what the chapter explores — its conflict, imagery, and open question. "
        "Never write a one-line placeholder.\n"
        "Derive each chapter's title and summary from the epic. "
        "Set chapter_index to the matching index and name to its string form.\n\n"
        f"EPIC:\n{epic}"
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
    for attempt in range(1, OLLAMA_MAX_RETRIES + 1):
        needed = _incomplete_chapters(chapters_by_index, chapter_count)
        if not needed:
            break
        print(f"  completeness pass {attempt}: re-requesting chapters {needed}")
        for chapter in _generate_chapter_batch(epic, needed, 0, 0):
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
        "book_summary": "Generated via batched layout — update from epic.md",
        "created_at": now,
        "updated_at": now,
        "user_name": "pijush",
        "gist": "Generated via batched layout — update from epic.md",
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
    prompt = (
        "Create the complete backlog book plan as valid JSON. "
        "Return JSON only — no Markdown fence, no explanation.\n"
        "Use the exact structural shape and field names of the template below.\n"
        f"Set book_name to {json.dumps(bookname, ensure_ascii=False)} "
        f"and form to {json.dumps(form)}.\n"
        "Derive chapter count, titles, summaries, references, book summary, "
        "and filter chain from the epic. "
        "Preserve every topic or chapter in the epic; do not invent a different premise.\n"
        "Each chapter must include: chapter_index, name, word_target, "
        "chapter_title, chapter_summary, further_references.\n"
        "IMPORTANT: every chapter_summary must be 2–4 sentences (150–200 words) "
        "describing what the chapter explores — never a one-line placeholder.\n\n"
        f"TEMPLATE book.json:\n{template}\n\n"
        f"EPIC:\n{epic}"
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
) -> None:
    """Generate (or regenerate) book.json from epic.md using the local Ollama model.

    epic.md is the source of truth: its chapter structure is expanded into the
    complete book.json plan.  When *chapter_count* exceeds OLLAMA_BATCH_SIZE the
    chapters are generated in batches of 10 with a completeness loop so the
    resulting book.json is always complete.  The plan is validated before it
    overwrites book.json, so a failed generation never clobbers an existing plan.

    Args:
        book_dir:      Path to the backlog epic folder for this book.
        bookname:      Validated book name string.
        form:          'novel' or 'poetry'. Inferred from epic.md if None.
        chapter_count: Target chapter count. If None, read from the existing book.json.
    """
    epic_file = book_dir / "epic.md"
    if not epic_file.exists():
        raise FileNotFoundError(
            f"Epic not found: {epic_file}\n"
            "Create the backlog first with: python .tools/book.py <bookname> init"
        )
    if not BOOK_TEMPLATE.exists():
        raise FileNotFoundError(f"Book template not found: {BOOK_TEMPLATE}")

    epic = epic_file.read_text(encoding="utf-8")
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

    print(f"Generating layout via Ollama ({OLLAMA_MODEL}) — form: {form}")

    use_batching = bool(chapter_count) and chapter_count > OLLAMA_BATCH_SIZE
    if use_batching:
        print(f"Chapter count {chapter_count} > {OLLAMA_BATCH_SIZE}; using batched generation.")
        layout = _generate_layout_batched(epic, bookname, form, chapter_count, template)
    else:
        layout = _generate_layout_single(epic, bookname, form, template)

    # Validate the plan is complete before overwriting book.json.
    validate_layout(layout, bookname, form)  # type: ignore[arg-type]

    # Stamp timestamps
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    layout.setdefault("created_at", now)
    layout["updated_at"] = now

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

IDEA_SYSTEM_PROMPT = (
    "You are the founding idea-gardener for a literary book.\n"
    "Given a seed (an existing one-line gist, or a bare book name), you rewrite it\n"
    "into a stronger, more dramatically charged single-sentence premise.\n\n"
    "CONTRACT:\n"
    "- Return exactly one valid JSON object — no Markdown fences, no commentary.\n"
    "- Use exactly two fields: 'gist' and 'expansion'.\n"
    "- 'gist' is a single sentence that names a person, a place, a problem, and a consequence.\n"
    "- 'expansion' is 2–4 sentences naming the protagonist, the conflict, and the transformation.\n"
    "- Preserve the seed's core idea; elevate it, do not replace it with an unrelated story.\n"
    "- Write in English unless the seed is in another language, in which case match it."
)


def rewrite_gist_idea(bookname: str) -> None:
    """Rewrite the book's gist with AI assistance (the `init idea` subcommand).

    Reads the existing gist.md one-liner (or the book name if gist.md is absent),
    asks Ollama for a stronger single-sentence premise plus a short expansion,
    and writes both back to gist.md. It does not touch epic.md or book.json.
    """
    book_dir = EPIC_ROOT / validate_bookname(bookname)
    book_dir.mkdir(parents=True, exist_ok=True)
    gist_file = book_dir / "gist.md"

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

    prompt = (
        f"Rewrite this book idea into a stronger one-line gist and a short expansion.\n\n"
        f"SEED: {seed}\n\n"
        "Return JSON with 'gist' (one sentence) and 'expansion' (2–4 sentences)."
    )

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

    expansion_block = f"\n\n## Expansion\n\n{expansion}\n" if expansion else "\n"
    gist_file.write_text(gist + expansion_block, encoding="utf-8")

    print(f"Gist rewritten → {gist_file}")
    print(f"  gist: {gist}")
    print(f"  expansion: {expansion or '(none)'}")
    print("  Note: epic.md and book.json are unchanged; re-run init to re-derive them.")


def create_backlog(
    bookname: str,
    gist: str | None,
    form: str,
    refresh: bool,
    chapter_count: int | None = None,
) -> None:
    """Create or refresh the three backlog artifacts for a book.

    Artifacts created/updated:
        gist.md   — one-line seed (only written if missing or *refresh* is True)
        epic.md   — full narrative foundation (always written)
        book.json — chapter layout plan (always written)

    Args:
        bookname:      Validated book name.
        gist:          Optional seed text supplied by the user.
        form:          'novel' or 'poetry'.
        refresh:       When True, overwrites an existing gist.md.
        chapter_count: Optional explicit chapter count override.
    """
    book_dir = EPIC_ROOT / validate_bookname(bookname)
    book_dir.mkdir(parents=True, exist_ok=True)

    gist_file = book_dir / "gist.md"
    epic_file = book_dir / "epic.md"
    book_file = book_dir / "book.json"

    seed = read_seed(book_dir)

    # Resolve the gist: user argument → existing gist.md → auto-generated default
    resolved_gist = (gist.strip() if gist and gist.strip() else None)
    if resolved_gist is None and gist_file.exists():
        resolved_gist = gist_file.read_text(encoding="utf-8").strip() or None
    resolved_gist = resolved_gist or default_gist(bookname, form)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    chapters = make_chapters(bookname, form, seed, chapter_count)
    plan = make_book_json(bookname, form, resolved_gist, chapters, now)
    epic_text = generate_epic(bookname, form, resolved_gist, chapters, now)

    # Write gist.md only if it doesn't exist or refresh is requested
    if not gist_file.exists() or refresh:
        gist_file.write_text(resolved_gist + "\n", encoding="utf-8")

    epic_file.write_text(epic_text, encoding="utf-8")
    book_file.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Backlog created → {book_dir}")
    print(f"  gist.md  : {gist_file}")
    print(f"  epic.md  : {epic_file}")
    print(f"  book.json: {book_file}")
    print(f"  form: {form} | chapters: {len(chapters)} | refreshed: {refresh}")


# ---------------------------------------------------------------------------
# Pipeline scaffold
# ---------------------------------------------------------------------------

def scaffold_novel(bookname: str, chapter_count: int, gist: str = "") -> None:
    """Build the .space/pipeline/<bookname>/ folder tree for a novel.

    Reads the backlog book.json to get the chapter plan and filter chain,
    then creates all required pipeline folders and placeholder files.

    The pipeline structure created:
        book.json, bookseed.txt, characters.json, override.txt
        filters/filters.json (registry only — no per-filter folders)
        chapters/<name>/model.json, chapter.md, history/
        chapters/<name>/segments/1/{model.json, writer/, editor/, translator/, version/}

    Raises FileNotFoundError if the backlog book.json is missing (run init first).
    Raises FileExistsError  if the pipeline already exists (avoid silent re-scaffold).
    Raises ValueError        if the book.json does not match the requested novel form.
    """
    book_dir = EPIC_ROOT / bookname
    plan_file = book_dir / "book.json"
    if not plan_file.exists():
        raise FileNotFoundError(
            f"Backlog book plan not found: {plan_file}\n"
            "Run init first: python .tools/book.py <bookname> init"
        )

    plan = json.loads(plan_file.read_text(encoding="utf-8-sig"))
    if plan.get("book_name") != bookname:
        raise ValueError(
            f"book.json book_name is {plan.get('book_name')!r} but expected {bookname!r}."
        )
    if plan.get("form") != "novel":
        raise ValueError(
            "scaffold_novel requires form='novel' in book.json. "
            "For poetry use: python .tools/book.py <bookname> scaffold [count] poetry"
        )

    chapters = plan.get("chapters", [])
    if chapter_count != len(chapters):
        raise ValueError(
            f"Requested scaffold chapter count ({chapter_count}) does not match "
            f"book.json chapters ({len(chapters)}). "
            "Update book.json or supply the correct count."
        )

    pipeline = REPO_ROOT / ".space" / "pipeline" / bookname
    if pipeline.exists():
        raise FileExistsError(
            f"Pipeline already exists: {pipeline}\n"
            "Delete it manually if you want to re-scaffold."
        )
    pipeline.mkdir(parents=True)

    # --- Root pipeline files ---
    (pipeline / "book.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (pipeline / "bookseed.txt").write_text(
        "\n".join(str(ch["chapter_title"]) for ch in chapters) + "\n",
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
                "agent": f".framework/agents/{name}/agent.md",
                "summary_file": "filter-summary.md",
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

        # Bare chapter.md placeholder — postlayout will seed content
        chapter_title = ch.get("chapter_title", ch_name)
        chapter_summary = ch.get("chapter_summary", "")
        (chapter_dir / "chapter.md").write_text(
            f"# {chapter_title}\n\n## Workshop\n\n{chapter_summary}\n\n"
            "## Story\n\n## Discussion\n",
            encoding="utf-8",
        )

        # Segment-level model.json
        (segment_dir / "model.json").write_text(
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
    """Dynamically load a .tools/ Python module by file path.

    This avoids adding .tools/ to sys.path while still allowing book.py to
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
            f"Ensure {script} is present in .tools/."
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
    """Invoke a .tools/ script as a subprocess with the current interpreter.

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

    Skips known keyword values (form names, structural keywords) so that
    'python book.py mybook write all novel' correctly resolves target='all'.
    """
    reserved = {"gist", "epic", "count", "chapter-count", "poetry", "novel"}
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

    # Ensure the pipeline style.md exists and is grounded in the current book.
    enrich.regenerate_style_md(bookname, book)

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
            enrich.enrich_chapter(_chapter_model_file(chapters_root / str(num)), book, all_models)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{num}] FAILED: {exc}", file=sys.stderr)
            failures += 1

    successes = len(numbers) - failures
    print(f"Enrich complete. {successes} succeeded, {failures} failed.")
    if failures:
        raise RuntimeError(f"{failures} chapter(s) failed enrichment.")


def write_workflow(bookname: str, target: str) -> None:
    """Run the chapter writer (write.py) in-process for the given chapter range.

    Loads write.py as a module, resolves the chapter list, and writes each
    requested chapter.  Prints a summary of successes and failures.
    """
    writer = _load_module("writer_write_engine", "write.py")
    chapters_root = writer.resolve_chapters_root(bookname)
    numbers = writer.parse_chapter_input(target, chapters_root)

    failures = 0
    for num in numbers:
        try:
            writer.write_chapter(_chapter_model_file(chapters_root / str(num)))
        except Exception as exc:  # noqa: BLE001
            print(f"  [{num}] FAILED: {exc}", file=sys.stderr)
            failures += 1

    successes = len(numbers) - failures
    print(f"Write complete. {successes} succeeded, {failures} failed.")
    if failures:
        raise RuntimeError(f"{failures} chapter(s) failed writing.")


def publish_workflow(bookname: str, language: str | None = None) -> None:
    """Promote pipeline segments to source/books/ via publish.py.

    The current publisher supports writer-stage chapter drafts only; the
    *language* parameter is reserved for future translator-stage support.
    """
    if language:
        raise ValueError(
            "Language-specific publish is not yet supported. "
            "Omit the language argument to publish writer-stage drafts."
        )
    publisher = _load_module("writer_publish_engine", "publish.py")
    publisher.publish(bookname)


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
            "  python .tools/book.py cosmos init \"মহাবিশ্বের রহস্য\" poetry\n"
            "  python .tools/book.py cosmos layout 30 poetry\n"
            "  python .tools/book.py mynovel scaffold 15 novel\n"
            "  python .tools/book.py mynovel enrich all\n"
            "  python .tools/book.py mynovel write 1-5\n"
            "  python .tools/book.py mynovel publish\n\n"
            "Run 'python .tools/book.py help' to show full usage."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "bookname",
        help="Book folder name under .space/backlog/ (no path separators).",
    )
    parser.add_argument(
        "verb",
        nargs="?",
        choices=("build", "layout", "backlog", "init", "scaffold", "filter", "enrich", "write", "publish"),
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
        help="Explicit seed text for gist.md and epic.md (alternative to positional argument).",
    )
    parser.add_argument(
        "-t", "--type",
        dest="book_type",
        choices=("poetry", "novel"),
        default="poetry",
        help="Book form override (default: poetry).",
    )
    parser.add_argument(
        "-r", "--refresh",
        action="store_true",
        help="Overwrite existing gist.md when running init or build.",
    )
    parser.add_argument(
        "--layout",
        action="store_true",
        help="Regenerate book.json from epic.md via Ollama after backlog creation.",
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
        form = resolve_form([args.range, args.option, args.book_type])
        count = resolve_count([args.option, args.range, args.objective])
        if count is None:
            # Fall back to chapter_count from the existing book plan
            plan_file = book_dir / "book.json"
            if plan_file.exists():
                count = json.loads(plan_file.read_text(encoding="utf-8")).get("chapter_count")
        if count is None:
            raise ValueError(
                "scaffold requires a chapter count.\n"
                "Supply it as a positional argument or ensure book.json has 'chapter_count'."
            )
        if form == "poetry":
            run_tool("scaffold_poetry.py", [bookname])
        else:
            scaffold_novel(bookname, count, args.gist or "")
        return

    if verb == "write":
        write_workflow(bookname, positional_target(args))
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
        publish_workflow(bookname, language)
        return

    if verb == "filter":
        raise ValueError(
            "'filter' has no standalone runner in .tools/.\n"
            "Invoke the registered filter agent through /book or run the filter agent directly."
        )

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
        book_dir = EPIC_ROOT / bookname

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
        elif args.objective and args.objective not in {"gist", "build", "epic", "novel", "poetry", "refresh"}:
            gist = args.objective
        gist = gist or args.gist

        # --- init ---
        if args.verb == "init":
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
            create_backlog(bookname, resolved_gist, resolved_form, refresh=args.refresh)
            # Layout is a separate, best-effort task: a failure here must not
            # mask the backlog artifacts (epic.md/book.json) already written.
            try:
                generate_layout(book_dir, bookname, resolved_form)
            except (RuntimeError, ValueError, FileNotFoundError) as exc:
                print(f"Warning: layout generation skipped — {exc}", file=sys.stderr)
            return 0

        # --- build / layout ---
        if args.verb in {"build", "layout"}:
            count = resolve_count([args.objective, args.option, args.range])
            layout_form = resolve_form([args.range, args.option], fallback=form)
            if count is not None:
                # Numeric first argument → full backlog creation + layout
                create_backlog(bookname, gist, layout_form, args.refresh, count)
            generate_layout(book_dir, bookname, layout_form, count)
            return 0

        # --- backlog validation ---
        if args.verb == "backlog" and args.objective not in (None, "gist", "build"):
            raise ValueError(
                f"Unknown backlog objective: {args.objective!r}. "
                "Expected 'build', 'gist', or omit."
            )

        # --- all other pipeline verbs ---
        dispatch_workflow(args, bookname, book_dir)
        return 0

    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
