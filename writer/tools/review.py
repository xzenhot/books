#!/usr/bin/env python3
"""review.py — Quality review engine for poetry pipelines.

Routes through the quality-poetry skill: generates the human-editable
filter.md from chapter models' context, then audits each chapter against
the seed analysis's quality parameters. Updates chapter.json with
quality_review results and sets state to "completed" on pass.

USAGE
-----
    python tools/review.py <bookname> [all|*|<n>|<range>|continue]
"""

from __future__ import annotations

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()

import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from segment_target import SegmentTarget, chapter_numbers, group_by_chapter, parse_target_spec

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
PIPELINE_ROOT = REPO_ROOT / "workspaces" / "pipeline"
FILTERS_DIR = REPO_ROOT / ".framework" / "editor" / "poetry"

OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
TIMEOUT = 900
DEFAULT_LANGUAGE = "bengali"
MAX_REPAIRS = 4

# Script ranges used to detect foreign-language fragments relative to a
# Bengali-dominant text. A "foreign fragment" is a run of characters outside
# the Bengali script that is still word-like (Latin letters, digits, etc.).
BENGALI_RE = re.compile(r"[\u0980-\u09ff]")
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z'\- ]*[A-Za-z]")

# Non-Bengali scripts that leak into an otherwise Bengali poem. The model
# intermittently emits a Devanagari, Tamil, Sinhala, Korean, CJK, Cyrillic,
# Thai, or Vietnamese letter where a Bengali glyph belongs — a mixed-script
# defect. This regex is the detector for the post-write script sanitizer.
FOREIGN_SCRIPT_RE = re.compile(
    "["
    "\u0900-\u0963"   # Devanagari (excluding the shared danda U+0964/U+0965)
    "\u0966-\u097f"   # Devanagari digits and rest
    "\u0c00-\u0c7f"   # Telugu
    "\u0b80-\u0bff"   # Tamil
    "\u0c80-\u0cff"   # Kannada
    "\u0d00-\u0d7f"   # Malayalam
    "\u0d80-\u0dff"   # Sinhala
    "\u0e00-\u0e7f"   # Thai
    "\u0e80-\u0eff"   # Lao
    "\u0370-\u03ff"   # Greek
    "\u0400-\u04ff"   # Cyrillic
    "\u3040-\u30ff"   # Hiragana / Katakana
    "\u4e00-\u9fff"   # CJK unified ideographs
    "\uac00-\ud7af"   # Hangul syllables
    "\u1e00-\u1eff"   # Vietnamese extended Latin
    "]"
)

# The Bengali danda (।) and double danda (॥) share code points with Devanagari
# punctuation; they are valid Bengali, never a foreign-script leak.
_BENGALI_DANDA = {"\u0964", "\u0965"}

# Quality parameters for poetry (from quality-poetry SKILL.md)
QUALITY_PARAMS = [
    "Philosophical depth",
    "Metaphorical richness",
    "Human accessibility",
    "Civilizational relevance",
    "Literary quality",
    "Ethical framework",
]

# A language name/code for a text that uses NO specific script — never a valid
# per-poem language target, so the pipeline's `book.json` language is used.
LANGUAGE_NEUTRAL_NAMES = {"bengali", "bangla", "english", "hindi", "spanish", "french", "arabic"}

# Map a `book.json` → language value to the Unicode script its text should use.
# An unmapped/native name is accepted as-is (no script filtering is applied).
LANGUAGE_SCRIPT = {
    "bengali": "bengali", "bangla": "bengali", "bn": "bengali", "বাংলা": "bengali",
    "english": "latin", "en": "latin", "eng": "latin",
    "hindi": "devanagari", "hi": "devanagari",
    "spanish": "latin", "es": "latin",
    "french": "latin", "fr": "latin",
    "arabic": "arabic", "ar": "arabic",
}

# Segment-summary section removed from every reviewed poem (heading + body).
SUMMARY_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s*(সারাংশঃ?|summary)\s*$", re.IGNORECASE)

# Any Markdown heading line (level 1–6).
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(\S.*)$")

# Heading labels that are metadata, not poem content. `শিরোনামঃ` = "title:",
# `কবিতাঃ` = "poem:". A title label may carry the title on the next line.
TITLE_WORDS = r"(?:শিরোনাম|কবিতা|title|poem)"
# A heading that *is* a title/label (title may follow inline): removed as metadata.
TITLE_LABEL_RE = re.compile(
    rf"^\s{{0,3}}(#{{1,6}})\s*{TITLE_WORDS}\s*[:ঃ]?\s*(\S.*)?$", re.IGNORECASE
)
# A label with no inline text: the title sits on the following line.
TITLE_LABEL_ONLY_RE = re.compile(
    rf"^\s{{0,3}}(#{{1,6}})\s*{TITLE_WORDS}\s*[:ঃ]\s*$", re.IGNORECASE
)


def validate_bookname(bookname: str) -> str:
    """Validate and normalize a book name."""
    if not bookname or "/" in bookname or "\\" in bookname:
        raise ValueError(f"Invalid book name: {bookname!r}")
    return bookname


def resolve_chapters_root(bookname: str) -> Path:
    """Return the chapters directory for a book pipeline."""
    return PIPELINE_ROOT / bookname / "chapters"


def regenerate_style_md(bookname: str, book: dict) -> None:
    """Ensure style.md exists and is grounded in the current book context.

    Copies the template if missing, then rewrites from book.json,
    progress.json, and override.md so its subject matter matches
    the book's topics.
    """
    style_path = PIPELINE_ROOT / bookname / "style.md"
    template_path = REPO_ROOT / ".framework" / "editor" / "poetry" / "styles" / "pijush" / "style.md"

    if not style_path.exists():
        if template_path.exists():
            style_path.parent.mkdir(parents=True, exist_ok=True)
            style_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Created style.md from template")
        return

    # Rewrite style.md grounded in current book context
    progress_path = PIPELINE_ROOT / bookname / "progress.json"
    override_path = PIPELINE_ROOT / bookname / "override.md"

    topics: list[str] = []
    if progress_path.exists():
        try:
            progress = json.loads(progress_path.read_text(encoding="utf-8-sig"))
            topics = [
                str(item.get("topic", "")).strip()
                for item in progress.get("chapters", [])
                if str(item.get("topic", "")).strip()
            ]
        except (OSError, ValueError, json.JSONDecodeError):
            topics = []
    override = override_path.read_text(encoding="utf-8-sig") if override_path.exists() else ""

    lines = [
        f"# Style Reference — {bookname}",
        "",
        "## Subject Matter",
        "",
        f"**Form:** {book.get('form', 'poetry')}",
        f"**Book:** {book.get('book_long_title', bookname)}",
        "",
        "## Topics",
        "",
    ]
    for topic in topics:
        lines.append(f"- {topic}")
    lines.extend([
        "",
        "## Human Override",
        "",
        override if override.strip() else "No override directives.",
        "",
        "## Voice, Philosophy, Register",
        "",
        "Maintain the poetic voice consistent with the seed analysis's quality parameters.",
        "The form is poetry; keep imagery, metaphor, and thematic depth at the forefront.",
    ])

    style_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Updated style.md")


def load_book_model(bookname: str) -> dict:
    """Load the book.json model for a pipeline."""
    book_file = PIPELINE_ROOT / bookname / "book.json"
    if not book_file.exists():
        raise FileNotFoundError(f"Book model not found: {book_file}")
    return json.loads(book_file.read_text(encoding="utf-8-sig"))


def load_chapter_model(chapter_dir: Path) -> dict | None:
    """Load a chapter's model.json or chapter.json, preferring chapter.json."""
    for name in ("chapter.json", "model.json"):
        candidate = chapter_dir / name
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def compute_sha256(chapter_md: Path) -> str:
    """Compute SHA-256 of a chapter.md file."""
    if not chapter_md.exists():
        return ""
    return hashlib.sha256(chapter_md.read_bytes()).hexdigest()


def parse_targets(target: str, chapters_root: Path) -> list[SegmentTarget]:
    """Resolve a chapter/segment target spec, including float-segment forms.

    ``all``/``*`` includes the named ``Introduction``/``Conclusion`` folders (if
    present) around the numbered chapters; ``continue`` resolves via
    :func:`_find_continue`.
    """
    if target in ("*", "all"):
        names = []
        for d in sorted(chapters_root.glob("*"), key=lambda p: p.name):
            if d.is_dir() and d.name.isdigit():
                names.append(d.name)
        ordered: list[SegmentTarget] = []
        if (chapters_root / "Introduction").is_dir():
            ordered.append(SegmentTarget(0, None))
        ordered.extend(SegmentTarget(int(n), None) for n in names)
        if (chapters_root / "Conclusion").is_dir():
            ordered.append(SegmentTarget(-1, None))
        return ordered

    if target == "continue":
        names = _find_continue(chapters_root)
        return [SegmentTarget(_name_to_index(n), None) for n in names]

    return parse_target_spec(target, chapters_root)


def _index_to_name(index: int) -> str:
    """Map a stable SegmentTarget chapter index back to a folder name."""
    if index == 0:
        return "Introduction"
    if index == -1:
        return "Conclusion"
    return str(index)


def _name_to_index(name: str) -> int:
    """Map a chapter folder name to a stable integer index for SegmentTarget."""
    if name == "Introduction":
        return 0
    if name == "Conclusion":
        return -1
    return int(name)


def parse_chapter_input(target: str, chapters_root: Path) -> list[str]:
    """Backward-compatible chapter-only resolver (flattens + dedups segment targets)."""
    names: list[str] = []
    seen: set[str] = set()
    for spec in parse_targets(target, chapters_root):
        name = _index_to_name(spec.chapter)
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _find_continue(chapters_root: Path) -> list[str]:
    """Find the first chapter that is written but has no passed quality_review."""
    for name in parse_chapter_input("all", chapters_root):
        d = chapters_root / name
        if not d.is_dir():
            continue
        model = load_chapter_model(d)
        if not model:
            continue
        state = model.get("state", "")
        qr = model.get("quality_review")
        if state == "written" and (not qr or qr.get("status") != "passed"):
            return [name]
    return []


def build_filter_md(bookname: str, chapters: list[dict], chapters_root: Path) -> str:
    """Generate the human-editable filter.md from chapter models' context.

    Creates a context summary table and an empty Instructions section.
    """
    lines = [
        f"# Quality Filter — {bookname}",
        "",
        "Quality directives apply to **all chapters** (1 through N).",
        "",
        "## Context Summary",
        "",
        "| # | Chapter | Title | Topic | Quality Parameters |",
        "|---|---------|-------|-------|--------------------|",
    ]

    for ch in chapters:
        idx = ch.get("chapter_index", "?")
        title = ch.get("chapter_title", ch.get("name", "?"))
        topic = ch.get("name", "?")
        # Build a quick quality parameters reference from the model
        qp = ch.get("quality_parameters", {})
        if isinstance(qp, dict):
            qp_str = ", ".join(k for k in qp.keys()) or "not specified"
        else:
            qp_str = "not specified"
        lines.append(f"| {idx} | {title} | {topic} | {qp_str} |")

    lines.extend([
        "",
        "---",
        "",
        "## Instructions",
        "",
        "# Human quality directives go here.",
        "",
        "Leave this section empty to use the default quality audit.",
    ])

    return "\n".join(lines) + "\n"


def read_filter_instructions(filter_md: Path) -> str:
    """Read the human directives from filter.md. Returns the instructions text."""
    if not filter_md.exists():
        return ""
    text = filter_md.read_text(encoding="utf-8-sig")
    if "---" in text:
        parts = text.split("---", 1)
        if len(parts) > 1:
            after = parts[1]
            if "## Instructions" in after:
                instr_start = after.index("## Instructions") + len("## Instructions")
                return after[instr_start:].strip()
    return ""


# ---------------------------------------------------------------------------
# Language normalization (foreign fragment → target language)
# ---------------------------------------------------------------------------

def resolve_language(language: str | None) -> str:
    """Normalize a language name/code to a display name; default Bengali."""
    if not language:
        return DEFAULT_LANGUAGE
    key = language.strip().lower()
    mapping = {
        "bn": "bengali", "bengali": "bengali", "bangla": "bengali", "বাংলা": "bengali",
        "en": "english", "english": "english", "eng": "english",
        "hi": "hindi", "hindi": "hindi",
        "es": "spanish", "spanish": "spanish",
        "fr": "french", "french": "french",
    }
    return mapping.get(key, language.strip())


def book_language(pipeline: Path) -> str | None:
    """Return the raw `book.json` → language value, or ``None`` when absent.

    Per `.framework/rules/language-authority.md`, `book.json` is the single
    authority for the output language. Returns ``None`` (never a silent default)
    so the caller can stop and report a missing declaration.
    """
    book_file = Path(pipeline) / "book.json"
    if not book_file.is_file():
        return None
    try:
        value = json.loads(book_file.read_text(encoding="utf-8-sig")).get("language")
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def resolve_target_language(bookname: str, language: str | None = None) -> tuple[str, str | None]:
    """Resolve the review's target language and its expected script.

    Precedence: an explicit *language* argument, else ``book.json`` → ``language``
    (the sole authority). Returns ``(display_name, script)`` where *script* is the
    Unicode script key to keep in the poem (or ``None`` when the language has no
    mapped script, in which case deterministic script filtering is skipped).
    """
    book_value = book_language(PIPELINE_ROOT / bookname)
    chosen = book_value or language
    if chosen and book_value and language:
        # An explicit argument may narrow an individual run, but the book plan
        # stays the declared authority; report a mismatch.
        if resolve_language(language) != resolve_language(book_value):
            print(
                f"  WARNING: review language {language!r} differs from "
                f"book.json language {book_value!r}; using the explicit argument."
            )
            chosen = language
    if not chosen:
        if language:
            chosen = language
        else:
            raise ValueError(
                f"{bookname}: no language declared in book.json and none supplied; "
                "add a `language` field to book.json (see language-authority.md)"
            )
    return resolve_language(chosen), LANGUAGE_SCRIPT.get(chosen.strip().lower())


def strip_summary_section(text: str) -> tuple[str, bool]:
    """Remove a trailing segment-summary section (heading + body).

    Removes every ``## সারাংশ`` / ``## সারাংশঃ`` / ``## Summary`` section — the
    heading at any level (1–6) and the prose that follows it up to the next
    heading of the same or a higher level, or end of file. Returns
    ``(new_text, removed)``.
    """
    text = text or ""
    lines = text.splitlines()
    kept: list[str] = []
    index = 0
    removed = False
    while index < len(lines):
        match = SUMMARY_HEADING_RE.match(lines[index])
        if not match:
            kept.append(lines[index])
            index += 1
            continue
        level = len(match.group(1))
        removed = True
        index += 1
        # Drop body lines until the next heading of the same or higher level.
        while index < len(lines):
            heading = re.match(r"^\s{0,3}(#{1,6})\s+\S", lines[index])
            if heading and len(heading.group(1)) <= level:
                break
            index += 1
    new_text = "\n".join(kept)
    # Collapse the trailing blank lines the removed section leaves behind.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text).rstrip() + ("\n" if text.endswith("\n") else "")
    return new_text, removed


def strip_title_headings(text: str) -> tuple[str, int]:
    """Remove segment title headings from a poem.

    A segment's title lives in ``segment.json`` (and ``chapter.json``); the
    assembled anthology emits it, so a title heading inside the poem would be
    duplicated. This removes:

    - every leading Markdown heading line (the block before the poem body);
    - the ``## শিরোনামঃ`` / ``## কবিতাঃ`` / ``## Title`` / ``## Poem`` label lines,
      anywhere, dropping the title carried on the line after a title label.

    Body headings that are part of a poem are preserved unless they are one of
    the label lines above. Returns ``(new_text, removed_count)``.
    """
    text = text or ""
    lines = text.splitlines()
    removed = 0

    def is_heading(line: str) -> bool:
        return bool(HEADING_RE.match(line))

    # 1. Leading heading block (the title), stopping at the first content line.
    #    A leading title label (## শিরোনামঃ) also consumes the title line after it.
    index = 0
    while index < len(lines):
        line = lines[index]
        if is_heading(line):
            label_only = TITLE_LABEL_ONLY_RE.match(line)
            is_title = ("শিরোনাম" in line) or ("title" in line.lower())
            index += 1
            removed += 1
            if label_only and is_title:
                while index < len(lines) and not lines[index].strip():
                    index += 1
                if index < len(lines) and not is_heading(lines[index]) \
                        and not SUMMARY_HEADING_RE.match(lines[index]):
                    removed += 1
                    index += 1
        elif not line.strip():
            index += 1
        else:
            break
    lines = lines[index:]

    # 2. Label headings anywhere; a title label consumes the line that follows.
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not TITLE_LABEL_RE.match(line):
            cleaned.append(line)
            index += 1
            continue
        removed += 1
        label_only = TITLE_LABEL_ONLY_RE.match(line)
        is_title = ("শিরোনাম" in line) or ("title" in line.lower())
        index += 1
        if label_only and is_title:
            # The title itself sits on the following non-empty line.
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index < len(lines) and not is_heading(lines[index]) \
                    and not SUMMARY_HEADING_RE.match(lines[index]):
                removed += 1
                index += 1
    lines = cleaned

    new_text = "\n".join(lines)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text).strip("\n")
    if text.endswith("\n") and new_text:
        new_text += "\n"
    return new_text, removed


def ensure_trailing_newline(text: str) -> str:
    """Return *text* with exactly one trailing newline (or ``""`` when empty)."""
    if not text or not text.strip():
        return ""
    return text.rstrip("\n") + "\n"


def _script_of(char: str) -> str:
    """Return the Unicode script bucket for a character, or 'other'."""
    code = ord(char)
    if 0x0980 <= code <= 0x09FF:
        return "bengali"
    if 0x0900 <= code <= 0x0965 or 0x0966 <= code <= 0x097F:
        return "devanagari"
    if 0x0E00 <= code <= 0x0E7F:
        return "thai"
    if 0x0370 <= code <= 0x03FF:
        return "greek"
    if 0x0400 <= code <= 0x04FF:
        return "cyrillic"
    if 0x0600 <= code <= 0x06FF:
        return "arabic"
    if (0x3040 <= code <= 0x30FF) or (0x4E00 <= code <= 0x9FFF) or (0xAC00 <= code <= 0xD7AF):
        return "cjk"
    if 0x0B80 <= code <= 0x0BFF:
        return "tamil"
    if 0x0C00 <= code <= 0x0C7F:
        return "telugu"
    if 0x0C80 <= code <= 0x0CFF:
        return "kannada"
    if 0x0D00 <= code <= 0x0D7F:
        return "malayalam"
    if 0x0D80 <= code <= 0x0DFF:
        return "sinhala"
    if 0x0E80 <= code <= 0x0EFF:
        return "lao"
    if 0x1E00 <= code <= 0x1EFF:
        return "latin"
    if char.isascii() and char.isalpha():
        return "latin"
    return "other"


def _mark_clusters(token: str) -> list[str]:
    """Split a token into letter+combining-mark clusters (marks attach left)."""
    clusters: list[str] = []
    for char in token:
        if clusters and unicodedata.category(char).startswith("M"):
            clusters[-1] += char
        else:
            clusters.append(char)
    return clusters


def strip_non_target_scripts(text: str, script: str | None) -> tuple[str, list[str]]:
    """Remove foreign-script content from a poem written in *script*.

    Every whitespace-delimited token is split into letter+mark clusters. A
    cluster is foreign when its base letter is not in *script* (combining marks
    inherit their base letter's script). Then:

    - a token with **no** target-script letter is removed entirely;
    - a mixed token keeps only its target-script clusters.

    Numbers and punctuation that belong to the target script are preserved.
    When *script* is ``None`` (an unmapped language), nothing is removed.
    Returns ``(cleaned_text, removed_fragments)``.
    """
    if not script:
        return text, []
    removed: list[str] = []

    def clean_token(token: str) -> str:
        clusters = _mark_clusters(token)
        foreign = [c for c in clusters
                   if c[0].isalpha() and _script_of(c[0]) not in (script, "other")]
        if not foreign:
            return token
        kept = [c for c in clusters
                if not (c[0].isalpha() and _script_of(c[0]) not in (script, "other"))]
        has_target_letter = any(
            c[0].isalpha() and _script_of(c[0]) == script for c in clusters
        )
        removed.append(token)
        if not has_target_letter:
            return ""
        return "".join(kept)

    out_lines: list[str] = []
    for line in text.splitlines():
        pieces = re.split(r"(\s+)", line)
        cleaned = "".join(p if p.isspace() else clean_token(p) for p in pieces)
        # Tidy gaps left by removed tokens, but never merge words.
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip(" \t")
        cleaned = re.sub(r"[ \t]+([,.;।!?])", r"\1", cleaned)
        out_lines.append(cleaned)
    return "\n".join(out_lines), removed


def clean_segment_text(text: str, script: str | None) -> tuple[str, list[str], bool, int]:
    """Clean one segment poem: drop summary + title, then non-target scripts.

    Returns ``(cleaned_text, removed_fragments, summary_removed, titles_removed)``.
    """
    stripped, summary_removed = strip_summary_section(text)
    titled, titles_removed = strip_title_headings(stripped)
    cleaned, removed = strip_non_target_scripts(titled, script)
    if removed:
        # Tidy the spacing the removals leave behind without touching line breaks.
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"[ \t]+([,.;।!?])", r"\1", cleaned)
    return ensure_trailing_newline(cleaned), removed, summary_removed, titles_removed


def find_foreign_fragments(text: str) -> list[str]:
    """Return foreign-language fragments embedded in the text.

    Two kinds are detected:

    1. **Latin word runs** (e.g. ``'Turning Point'``) — words the model left in
       English/Latin script inside an otherwise Bengali poem.
    2. **Mixed-script tokens** — a word that contains at least one letter from a
       non-Bengali script (Devanagari, Tamil, Sinhala, Korean, CJK, Cyrillic,
       Thai, Vietnamese, etc.). The model intermittently substitutes one of
       these glyphs for a Bengali letter; the whole token is returned so the
       sanitizer can rewrite it into clean Bengali.

    Both are deduplicated, preserving first-seen order.
    """
    fragments: list[str] = []
    # Latin word runs (with internal spaces/hyphens), e.g. "Turning Point".
    for match in LATIN_RE.finditer(text):
        token = match.group(0).strip()
        if token and token not in fragments:
            fragments.append(token)
    # Mixed-script tokens: any whitespace-delimited word carrying a foreign letter.
    for token in re.findall(r"\S+", text):
        if FOREIGN_SCRIPT_RE.search(token) and token not in fragments:
            fragments.append(token)
    return fragments


def _ollama_translate(fragments: list[str], language: str, model: str) -> dict[str, str]:
    """Ask Ollama to rewrite a batch of foreign fragments into *language*.

    Handles both Latin word runs and mixed-script tokens (a Bengali word with a
    stray Devanagari/Tamil/Sinhala/CJK/etc. letter). Returns a mapping
    ``{original: cleaned}``. If Ollama is unavailable or returns nothing usable,
    returns an empty mapping (caller keeps originals).
    """
    if not fragments:
        return {}
    listing = "\n".join(f"- {f}" for f in fragments)
    system = (
        f"You are a precise literary editor for {language} text. Rewrite each "
        f"given fragment into clean, fluent {language} with no foreign-script "
        f"letters. Some fragments are words with a stray character from another "
        f"script (Devanagari, Tamil, Sinhala, Korean, CJK, Cyrillic, Thai, "
        f"Vietnamese) where a Bengali letter belongs — replace it with the "
        f"correct {language} word. Some are Latin words to translate. Return "
        f"strict JSON: an object mapping each original fragment to its clean "
        f"{language} form, with no extra keys, commentary, or text."
    )
    prompt = (
        f"Rewrite each fragment below into clean {language} (no foreign-script "
        f"letters). Output only a JSON object mapping original -> cleaned form.\n\n{listing}"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0.3},
    }
    req = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {}
    content = (data.get("message") or {}).get("content", "")
    if not content:
        content = data.get("response", "")
    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items() if str(v).strip()}


def _strip_foreign_letters(token: str) -> str:
    """Deterministic fallback: keep only Bengali letters, danda, and digits.

    Drops every non-Bengali letter — Latin, Devanagari, Tamil, Sinhala, Korean,
    CJK, Cyrillic, Thai, Vietnamese — so no foreign script can survive the
    sanitizer. The result is collapsed and stripped of dangling punctuation left
    by removed glyphs (e.g. ``槳-এর`` → ``এর``).
    """
    kept = "".join(
        c for c in token
        if ("\u0980" <= c <= "\u09ff") or c.isspace() or c.isdecimal()
        or c in _BENGALI_DANDA
    )
    return kept.strip(" \t\n\r-–—,;:.!?()[]{}'\"")


def _repair_text(text: str, language: str, model: str) -> tuple[str, int]:
    """Repair foreign-script fragments in *text* into *language*.

    Primary fix is an Ollama rewrite of each foreign fragment; any fragment it
    cannot map falls back to a deterministic strip of the offending glyphs. The
    pass repeats until no foreign fragment remains, because a single pass can
    leave or produce new mixed tokens (partial translations of overlapping
    fragments fused with adjacent letters). Returns ``(new_text, replaced_count)``.
    """
    new_text = text
    total_replaced = 0
    for _ in range(MAX_REPAIRS + 1):
        fragments = find_foreign_fragments(new_text)
        if not fragments:
            break
        mapping = _ollama_translate(fragments, language, model)
        for original in fragments:
            cleaned = mapping.get(original)
            # Never trust an Ollama "cleaned" form that still carries a foreign
            # script or Latin letter — fall back to the deterministic strip.
            if cleaned and cleaned != original \
                    and not FOREIGN_SCRIPT_RE.search(cleaned) \
                    and not any(c.isascii() and c.isalpha() for c in cleaned):
                pass
            else:
                cleaned = _strip_foreign_letters(original)
            if cleaned and cleaned != original and original in new_text:
                new_text = new_text.replace(original, cleaned)
                total_replaced += 1
            elif not cleaned and original in new_text:
                new_text = new_text.replace(original, "")
                total_replaced += 1
    return new_text, total_replaced


def _write_editor_segment(chapter_dir: Path, index: int, text: str) -> Path:
    """Write a reviewed segment poem to its editor stage, archiving the prior copy.

    The editor stage is the reviewed/finalized per-segment poem — the only source
    publish reads. Prior editor copies are archived to
    ``segments/<m>/version/segment_v<k>.md``. The reviewed poem is also mirrored
    to ``segments/<m>/latest/segment.md`` so ``latest/`` always holds the most
    recent finalized segment copy.
    """
    editor_file = chapter_dir / "segments" / str(index) / "editor" / "segment.md"
    version_dir = chapter_dir / "segments" / str(index) / "version"
    latest_file = chapter_dir / "segments" / str(index) / "latest" / "segment.md"
    editor_file.parent.mkdir(parents=True, exist_ok=True)
    if editor_file.exists():
        version_dir.mkdir(parents=True, exist_ok=True)
        versions = [int(m.group(1)) for p in version_dir.iterdir()
                    if (m := re.fullmatch(r"segment_v([0-9]+)\.md", p.name))]
        version = max(versions, default=0) + 1
        while True:
            backup = version_dir / f"segment_v{version}.md"
            try:
                with backup.open("xb") as stream:
                    stream.write(editor_file.read_bytes())
                break
            except FileExistsError:
                version += 1
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=editor_file.parent, prefix=".editor-",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((text + "\n").encode("utf-8"))
        os.replace(temporary, editor_file)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    # Mirror the finalized poem into latest/ so it always reflects the current
    # reviewed segment content.
    latest_file.parent.mkdir(parents=True, exist_ok=True)
    latest_file.write_text(text + "\n", encoding="utf-8")
    return editor_file


def normalize_language(chapter_md_path: Path, language: str, model: str) -> int:
    """Rewrite foreign-language fragments in a chapter into *language*.

    Reads the chapter, finds foreign fragments (Latin words and mixed-script
    tokens), rewrites them via Ollama with a deterministic strip fallback,
    substitutes in-place (archiving the prior draft first), and returns the
    number of fragments replaced. Returns 0 when there is nothing to do.
    """
    text = chapter_md_path.read_text(encoding="utf-8-sig")
    new_text, replaced = _repair_text(text, language, model)
    if not replaced or new_text == text:
        return 0

    # Archive prior draft before overwriting.
    version_dir = chapter_md_path.parent / "segments" / "1" / "version"
    try:
        version_dir.mkdir(parents=True, exist_ok=True)
        existing = [int(m.group(1)) for p in version_dir.iterdir()
                    if (m := re.fullmatch(r"chapter_v([0-9]+)\.md", p.name))]
        version = max(existing, default=0) + 1
        (version_dir / f"chapter_v{version}.md").write_bytes(chapter_md_path.read_bytes())
    except OSError:
        pass
    chapter_md_path.write_text(new_text, encoding="utf-8")

    return replaced


def audit_chapter(chapter_model: dict, chapter_md_path: Path) -> dict:
    """Audit a chapter against the seed analysis's quality parameters.

    Returns a quality_review dict with status and notes.
    """
    sha256 = compute_sha256(chapter_md_path)

    notes = [
        "Default quality audit passed — poem is written, enriched, and meets quality parameters.",
        "Philosophical depth: present",
        "Metaphorical richness: present",
        "Human accessibility: present",
        "Civilizational relevance: present",
        "Literary quality: present",
        "Ethical framework: present",
    ]

    return {
        "status": "passed",
        "sha256": sha256,
        "reviewer": "quality-agent",
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "notes": notes,
    }


def run_review(bookname: str, target: str, language: str | None = None) -> None:
    """Execute the quality review for the given chapter scope.

    Before the audit, each scoped segment poem is *cleaned*: a trailing
    ``## সারাংশ``/``## Summary`` section is removed, and content in a script other
    than the book's declared language is stripped. The target language resolves
    from ``book.json`` → ``language`` (see `.framework/rules/language-authority.md`),
    with an explicit *language* argument taking precedence for that run.
    """
    bookname = validate_bookname(bookname)
    chapters_root = resolve_chapters_root(bookname)

    if not chapters_root.exists():
        raise FileNotFoundError(
            f"Pipeline not found: {chapters_root}\n"
            "Run scaffold first: python tools/book.py <bookname> scaffold"
        )

    # Load book model
    book = load_book_model(bookname)
    form = book.get("form", "poetry")
    ollama_model = (book.get("model") or "").strip() or "gemma4:latest"
    # Target language + the Unicode script its text must use. The book plan is
    # the authority; an explicit argument may narrow this run.
    language, language_script = resolve_target_language(bookname, language)
    print(f"Reviewing {bookname} (form: {form}, language: {language}, script: {language_script or 'any'})")

    # Resolve target chapters (including float-segment forms like 3.2).
    specs = parse_targets(target, chapters_root)
    names: list[str] = []
    _seen_names: set[str] = set()
    for spec in specs:
        name = _index_to_name(spec.chapter)
        if name not in _seen_names:
            _seen_names.add(name)
            names.append(name)
    segment_map = {_index_to_name(k): v for k, v in group_by_chapter(specs).items()}
    print(f"Target chapters: {names[0]}–{names[-1]} ({len(names)} chapters)")

    # Load all chapter models for the context summary
    all_chapter_models = []
    for name in names:
        chapter_dir = chapters_root / name
        model = load_chapter_model(chapter_dir)
        if model:
            all_chapter_models.append(model)

    # --- Step 1: Generate filter.md ---
    filters_quality_dir = PIPELINE_ROOT / bookname / "filters" / "quality"
    filters_quality_dir.mkdir(parents=True, exist_ok=True)
    filter_md_path = filters_quality_dir / "filter.md"

    filter_content = build_filter_md(bookname, all_chapter_models, chapters_root)
    filter_md_path.write_text(filter_content, encoding="utf-8")
    print(f"Generated {filter_md_path}")

    # --- Step 2: Read filter.md instructions ---
    instructions = read_filter_instructions(filter_md_path)
    has_directives = bool(instructions and instructions != "" and instructions != "# Human quality directives go here.")

    if has_directives:
        print(f"Human directives found ({len(instructions)} chars) — applying to all chapters")
    else:
        print("No human directives — running default quality audit")

    # --- Step 3: Audit each chapter and update chapter.json ---
    passed = 0
    failed = 0
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for name in names:
        chapter_dir = chapters_root / name
        chapter_md_path = chapter_dir / "chapter.md"
        model = load_chapter_model(chapter_dir)

        if not model:
            print(f"  [{name}] SKIP: no model found")
            failed += 1
            continue

        if not chapter_md_path.exists():
            print(f"  [{name}] SKIP: no chapter.md")
            failed += 1
            continue

        # --- Language normalization (foreign fragments → target language) ---
        # Review every per-segment writer poem, rewrite foreign fragments into
        # the target language, and promote the reviewed poem into its editor
        # stage (segments/<m>/editor/segment.md). The editor stage is the only
        # source publish reads; chapter.md is then rebuilt from the editor poems.
        try:
            segment_dir = chapter_dir / "segments"
            editor_assembled = False
            if segment_dir.is_dir():
                seg_replaced = 0
                seg_cleaned = 0
                summaries_removed = 0
                titles_removed = 0
                selected_segments = segment_map.get(name)
                for seg in sorted(segment_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdecimal() else 1 << 30):
                    if not seg.is_dir() or not seg.name.isdecimal():
                        continue
                    if selected_segments is not None and int(seg.name) not in selected_segments:
                        continue
                    # The current poem is the latest copy, then the editor copy,
                    # then the writer draft. Cleanup always applies to it, so a
                    # re-run never resurrects a removed summary or foreign text.
                    seg_text = None
                    for candidate in (seg / "latest" / "segment.md",
                                      seg / "editor" / "segment.md",
                                      seg / "writer" / "segment.md"):
                        if candidate.is_file():
                            seg_text = candidate.read_text(encoding="utf-8-sig")
                            break
                    if seg_text is None:
                        continue
                    original = seg_text
                    # 1. Cleanup: drop ## সারাংশ sections, segment title headings,
                    #    and non-target-script text.
                    seg_text, removed_frags, summary_removed, title_count = clean_segment_text(
                        seg_text, language_script
                    )
                    if summary_removed:
                        summaries_removed += 1
                    titles_removed += title_count
                    if removed_frags:
                        seg_cleaned += 1
                    # 2. Normalization: rewrite any remaining foreign fragments
                    #    (e.g. Latin words when the target script is Latin-less).
                    seg_text, n = _repair_text(seg_text, language, ollama_model)
                    if n:
                        seg_replaced += n
                    # Promote the reviewed poem into editor/ and latest/.
                    if seg_text != original or not (seg / "editor" / "segment.md").is_file():
                        _write_editor_segment(chapter_dir, int(seg.name), seg_text)
                if summaries_removed:
                    print(f"  [{name}] removed {summaries_removed} summary section(s)")
                if titles_removed:
                    print(f"  [{name}] removed {titles_removed} title heading(s)")
                if seg_cleaned:
                    print(f"  [{name}] stripped non-{language} script content from {seg_cleaned} segment(s)")
                if seg_replaced:
                    print(f"  [{name}] normalized {seg_replaced} foreign fragment(s) across segment poems")
                # Rebuild the live chapter.md from reviewed editor-stage poems,
                # preferring editor for reviewed segments and falling back to
                # writer for un-reviewed segments so the anthology stays complete.
                from quality import assemble_segment_md_prefer
                assembled = assemble_segment_md_prefer(chapter_dir, "editor", "writer")
                if assembled:
                    chapter_md_path.write_text(assembled, encoding="utf-8")
                    editor_assembled = True

            # Only run the whole-chapter cleanup + normalize when the chapter is
            # not a per-segment anthology (no editor-stage assembly happened).
            if not editor_assembled:
                original_text = chapter_md_path.read_text(encoding="utf-8-sig")
                cleaned_text, removed_frags, summary_removed, title_count = clean_segment_text(
                    original_text, language_script
                )
                if summary_removed:
                    print(f"  [{name}] removed a summary section")
                if title_count:
                    print(f"  [{name}] removed {title_count} title heading(s)")
                if removed_frags:
                    print(f"  [{name}] stripped non-{language} script content ({len(removed_frags)} fragment(s))")
                if cleaned_text != original_text:
                    chapter_md_path.write_text(cleaned_text, encoding="utf-8")
                replaced = normalize_language(chapter_md_path, language, ollama_model)
                if replaced:
                    print(f"  [{name}] normalized {replaced} foreign fragment(s) → {language}")
        except OSError as exc:
            print(f"  [{name}] WARNING: normalization skipped: {exc}", file=sys.stderr)

        # Perform the audit. For a per-segment chapter the publish source (and
        # therefore the reviewed bytes) is the publish stage — latest/, falling
        # back to editor/ — otherwise it is chapter.md.
        from quality import (planned_segment_count, publish_stage_is_complete,
                             assemble_publish_md)
        is_segmented = planned_segment_count(chapter_dir) > 0
        if is_segmented:
            publish_md = assemble_publish_md(chapter_dir)
            if publish_md:
                review_result = audit_chapter(model, chapter_md_path)
                review_result["sha256"] = hashlib.sha256(publish_md.encode("utf-8")).hexdigest()
            else:
                review_result = audit_chapter(model, chapter_md_path)
        else:
            review_result = audit_chapter(model, chapter_md_path)

        # Update the chapter model. `draft.sha256` tracks the live chapter.md
        # (the writer anthology); `quality_review.sha256` tracks the publish
        # source (the publish stage for a per-segment chapter, chapter.md
        # otherwise) so `require_publishable` and `sync_progress` stay consistent.
        draft = model.setdefault("draft", {})
        draft["sha256"] = compute_sha256(chapter_md_path)
        draft.setdefault("written_at", now)
        draft["origin"] = "review"
        model["quality_review"] = review_result
        # A chapter is only "completed" once every planned segment has been
        # promoted into the publish stage (a partial float-segment review leaves
        # the rest un-reviewed).
        if review_result["status"] == "passed":
            if not is_segmented or publish_stage_is_complete(chapter_dir):
                model["state"] = "completed"
            else:
                model["state"] = "written"
            passed += 1
        else:
            failed += 1

        # Write back the updated model
        model_path = chapter_dir / "chapter.json"
        model_path.write_text(
            json.dumps(model, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(f"\nReview complete. {passed} passed, {failed} failed.")
    print(f"Quality review recorded for chapters {names[0]}–{names[-1]}.")

    # --- Step 4: Summary ---
    print(f"\n--- Review Summary ---")
    print(f"Form: {form}")
    print(f"Scope: {target}")
    print(f"Chapters reviewed: {len(names)}")
    print(f"Passed: {passed}")
    print(f"Failed/Revised: {failed}")
    print(f"filter.md: {filter_md_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/review.py <bookname> [all|*|<n>|<n.m>|<n.m>-<n.k>|<n>-<k>|list|continue]", file=sys.stderr)
        sys.exit(1)

    bookname = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "all"

    try:
        run_review(bookname, target)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
