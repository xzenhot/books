#!/usr/bin/env python3
"""Enrich chapter model.json files with book-aware, variety-driven planning tags.

Usage:
    python tools/enrich.py <bookname> <number|range|list|all|*>
    python tools/enrich.py <bookname> --list-lenses

Two models are read for every enriched chapter:

1. the pipeline book model  workspaces/pipeline/<bookname>/model.json      (context)
2. the chapter model        workspaces/pipeline/<bookname>/chapters/<n>/model.json

The tool asks a local Ollama model for one additive patch that (a) fills empty
planning tags whose meaning is clear and (b) adds fresh angles, subject rotations,
story seeds, and sensory detail so neighbouring chapters stop repeating each other.
A per-chapter variation lens and a secondary twist are derived from the run seed, so
the same seed reproduces the same briefs, and every new suggestion is checked for
near-duplication against the material neighbouring chapters already hold.

Existing values are preserved; only validated additions are merged into model.json.
Original bytes are backed up to the chapter history directory before replacement.
chapter.md is never read or written.
"""
import argparse
import copy
import json
import os
import re
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = REPO_ROOT / ".framework" / "templates" / "tools"
# The active form's template folder, resolved once the book's form is known.
_ACTIVE_DIR = TEMPLATE_ROOT / "enrich-novel"
STYLE_BASE = REPO_ROOT / ".framework" / "templates" / "stereotypes" / "poetry" / "styles" / "pijush" / "style.md"

MODEL = "gemma4:latest"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
TIMEOUT = 900
CONTEXT_WINDOW = 64000
DEFAULT_TEMPERATURE = 0.95
MAX_RETRIES = 3
MAX_REPAIRS = 2
DUPLICATE_THRESHOLD = 0.72
# Pipeline scaffolding writes models with platform newlines; match that convention.
NEWLINE = os.linesep
SIBLING_WINDOW = 3
POOL_LIMIT = 40
VERBOSE = False
DRY_RUN = False

# Variation lenses: every chapter is briefed with one primary direction plus one twist
# so a long book stops giving adjacent subjects the same treatment.
# Loaded per form from .framework/templates/tools/enrich-{novel|poetry}/lenses.json.
LENSES: tuple = ()
TWISTS: tuple = ()
CREATIVE_REQUIRED: dict = {}
CREATIVE_OPTIONAL: dict = {}
CREATIVE_FIELDS: tuple = ()
ENRICH_SYSTEM_PROMPT: str = ""
ENRICH_USER_PROMPT_TEMPLATE: str = ""
REPAIR_PROMPT_TEMPLATE: str = ""
STYLE_REGENERATE_SYSTEM_PROMPT: str = ""


RUNTIME_KEYS = {"state", "status", "filter_history", "completed_date", "word_count", "enrich", "override"}
IDENTITY_KEYS = {"chapter_index", "name", "word_target", "level", "segments"}
PROTECTED_KEYS = RUNTIME_KEYS | IDENTITY_KEYS
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
# Punctuation stripped from token edges. Letters are never used as separators, so Indic
# scripts (Bengali, Devanagari) tokenise on word boundaries instead of vowel signs.
PUNCTUATION = "!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~।॥—“”‘’…"


def resolve_template_dir(form: str) -> Path:
    """Resolve the template folder for a book form (novel or poetry)."""
    form = (form or "novel").strip().casefold()
    if form not in {"novel", "poetry"}:
        raise ValueError(f"Unsupported enrich form: {form!r}")
    return TEMPLATE_ROOT / f"enrich-{form}"


def _load_text(filename: str) -> str:
    """Read a template text file, tolerating a UTF-8 BOM."""
    path = _ACTIVE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing enrich template: {path}")
    return path.read_text(encoding="utf-8-sig")


def _load_json(filename: str):
    """Read a template JSON file (tolerating a UTF-8 BOM)."""
    return json.loads(_load_text(filename))


def _render(template: str, **values) -> str:
    """Substitute `{name}` placeholders with values (safe for values containing braces)."""
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def load_templates(form: str) -> None:
    """(Re)load every form-specific template into the module globals.

    Call once the book's form is known. `novel` reads `enrich-novel/`,
    `poetry` reads `enrich-poetry/`.
    """
    global _ACTIVE_DIR, LENSES, TWISTS
    global CREATIVE_REQUIRED, CREATIVE_OPTIONAL, CREATIVE_FIELDS
    global ENRICH_SYSTEM_PROMPT, ENRICH_USER_PROMPT_TEMPLATE
    global REPAIR_PROMPT_TEMPLATE, STYLE_REGENERATE_SYSTEM_PROMPT

    _ACTIVE_DIR = resolve_template_dir(form)
    print(f"Loading enrich templates for form '{form}' from {_ACTIVE_DIR} ...", flush=True)
    LENSES = tuple((name, guidance) for name, guidance in _load_json("lenses.json"))
    TWISTS = tuple(_load_json("twists.json"))
    _schema = _load_json("schema.json")
    CREATIVE_REQUIRED = _schema["creative_required"]
    CREATIVE_OPTIONAL = _schema["creative_optional"]
    CREATIVE_FIELDS = tuple(_schema["creative_fields"])
    ENRICH_SYSTEM_PROMPT = _load_text("enrich_system_prompt.md")
    ENRICH_USER_PROMPT_TEMPLATE = _load_text("enrich_user_prompt_template.md")
    REPAIR_PROMPT_TEMPLATE = _load_text("repair_prompt_template.md")
    STYLE_REGENERATE_SYSTEM_PROMPT = _load_text("style_regenerate_system_prompt.md")
    print(
        f"Loaded {len(LENSES)} lenses and {len(TWISTS)} twists "
        f"({len(CREATIVE_FIELDS)} creative fields).",
        flush=True,
    )


def vlog(*args):
    if VERBOSE:
        print("[v]", *args)


def reject_constant(value):
    raise ValueError(f"Nonstandard JSON value: {value}")


def read_model(path):
    """Read one chapter metadata file (tolerating a UTF-8 BOM) as a JSON object."""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject_constant)


def _chapter_file(chapter_dir):
    """Resolve a chapter's metadata file, preferring `chapter.json` over `model.json`."""
    chapter_dir = Path(chapter_dir)
    for name in ("chapter.json", "model.json"):
        candidate = chapter_dir / name
        if candidate.exists():
            return candidate
    return chapter_dir / "chapter.json"


def check_bookname(bookname):
    if not bookname.strip() or bookname in {".", ".."} or any(
        char in bookname for char in '/\\:<>"|?*'
    ):
        raise ValueError("Bookname must be a single pipeline folder name")
    return bookname


def resolve_chapters_root(bookname):
    """Resolve a book folder relative to this script's repository root."""
    chapters_root = REPO_ROOT / "workspaces" / "pipeline" / check_bookname(bookname) / "chapters"
    if not chapters_root.is_dir():
        raise ValueError(f"Chapters directory not found: {chapters_root}")
    return chapters_root


def load_book_model(bookname):
    """Read the pipeline book plan (book.json, falling back to model.json) that gives every chapter its context."""
    pipeline = REPO_ROOT / "workspaces" / "pipeline" / check_bookname(bookname)
    for name in ("book.json", "model.json"):
        book_file = pipeline / name
        if book_file.is_file():
            break
    else:
        raise ValueError(
            f"Book plan not found in {pipeline}. Run `/book {bookname} scaffold` first."
        )
    book = read_model(book_file)
    if not isinstance(book, dict) or not book:
        raise ValueError(f"Book model must be a nonempty JSON object: {book_file}")
    return book


def resolve_book_form(bookname):
    """Read the book's form from workspaces/pipeline/<bookname>/book.json.

    Falls back to the legacy `model.json` only when `book.json` is absent, so the
    form is always taken from the canonical book plan.
    """
    book = load_book_model(bookname)
    form = book.get("form")
    if not form:
        form = "novel"
    return str(form)


def resolve_model(bookname, default=MODEL):
    """Resolve the Ollama model name from the book's progress.json.

    Reads `workspaces/pipeline/<bookname>/progress.json` → `model` (falling
    back to `book.json` → `model`, then the module default).
    """
    pipeline = REPO_ROOT / "workspaces" / "pipeline" / check_bookname(bookname)
    for name in ("progress.json", "book.json"):
        f = pipeline / name
        if not f.is_file():
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        model = data.get("model")
        if isinstance(model, str) and model.strip():
            return model.strip()
    return default


def regenerate_style_md(bookname, book):
    """Ensure the pipeline style.md exists and regenerate it from the current book.

    Mirrors the quality/enrich agents' style-reference step. The rewrite is driven
    by an Ollama call, not deterministic string replacement: the model re-grounds
    the style document's subject matter to this book's summary and topics, removing
    any prior/foreign narrative (e.g. a Behula template) and re-rooting the persona,
    examples, and topic list in the current book. On any model failure the existing
    (or freshly seeded) style.md is left intact.
    """
    pipeline = REPO_ROOT / "workspaces" / "pipeline" / check_bookname(bookname)
    style_file = pipeline / "style.md"

    # Ensure the base exists (copy the template if missing).
    if not style_file.exists():
        if not STYLE_BASE.is_file():
            return None
        style_file.write_text(STYLE_BASE.read_text(encoding="utf-8"), encoding="utf-8")
        vlog(f"style.md seeded from template -> {style_file}")

    current = style_file.read_text(encoding="utf-8")
    title = book.get("book_long_title") or book.get("book_name") or bookname
    summary = book.get("book_summary", "")
    chapters = book.get("chapters") or []
    topics = [
        f"{ch.get('chapter_index')}. {ch.get('chapter_title') or ch.get('name')}"
        for ch in chapters
        if isinstance(ch, dict) and (ch.get("chapter_title") or ch.get("name"))
    ]

    prompt = (
        "Regenerate the style document below so its subject matter is grounded in "
        "THIS book, removing any prior or foreign narrative (e.g. Behula, Lakhindar, "
        "a bamboo raft, a wedding chamber) and re-rooting the persona, examples, and "
        "topic list in the current book.\n\n"
        f"BOOK TITLE: {title}\n\n"
        f"BOOK SUMMARY:\n{clip(summary, 2000)}\n\n"
        f"BOOK TOPICS:\n" + "\n".join(topics) + "\n\n"
        "CURRENT STYLE DOCUMENT:\n" + current + "\n\n"
        "Return the full rewritten style document as Markdown only."
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = run_ollama(
                prompt,
                secrets.randbelow(2**31) + attempt,
                0.5,
                MODEL,
                system=STYLE_REGENERATE_SYSTEM_PROMPT,
                format_json=False,
            )
            regenerated = (raw or "").strip()
            if regenerated and len(regenerated) > 200:
                style_file.write_text(regenerated + "\n", encoding="utf-8")
                vlog(f"style.md regenerated via Ollama -> {style_file}")
                return style_file
            raise ValueError("Ollama returned an empty or too-short style document")
        except (RuntimeError, ValueError) as exc:
            vlog(f"style regeneration attempt {attempt}/{MAX_RETRIES} failed: {exc}")

    # Fall back: keep the existing (or seeded) style.md unchanged.
    vlog("style regeneration failed; keeping existing style.md")
    return style_file


def parse_chapter_input(value, chapters_root=None):
    """Parse numbers/ranges, or discover all numeric chapter folders in order."""
    if value.strip().lower() in {"all", "*"}:
        if chapters_root is None:
            raise ValueError("A chapters directory is required for all or '*'")
        numbers = sorted({
            int(folder.name)
            for folder in chapters_root.iterdir()
            if folder.is_dir() and re.fullmatch(r"[0-9]+", folder.name)
            and int(folder.name) > 0
        })
        if not numbers:
            raise ValueError(f"No numbered chapters found in {chapters_root}")
        return numbers
    numbers = []
    for token in value.split(","):
        match = re.fullmatch(r"([0-9]+)(?:-([0-9]+))?", token.strip())
        if match is None:
            raise ValueError("Expected all, '*', or chapter numbers, e.g. 2, 2-5, or 2-5,8")
        start = int(match.group(1))
        end = int(match.group(2)) if match.group(2) else start
        if start < 1 or end < start:
            raise ValueError("Chapter numbers must be positive and ranges ascending")
        numbers.extend(range(start, end + 1))
    return list(dict.fromkeys(numbers))


def empty(value):
    return value is None or (isinstance(value, str) and not value.strip()) or value == [] or value == {}


def clip(value, limit):
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def book_digest(book):
    """Prompt-sized view of the book model (never the whole 60-chapter plan)."""
    digest = {}
    for key in ("book_name", "book_long_title", "form", "language", "register", "generic",
                "era", "target_audience", "gist", "book_summary", "chapter_count", "word_target"):
        value = book.get(key)
        if not empty(value):
            digest[key] = clip(value, 1400)
    for key in ("themes", "quality", "reference", "index"):
        value = book.get(key)
        if not empty(value):
            digest[key] = Path(str(value)).name
    vocabulary = book.get("sacred_vocabulary")
    if isinstance(vocabulary, dict) and vocabulary:
        digest["sacred_vocabulary"] = vocabulary
    guide = book.get("translation_guide")
    if isinstance(guide, dict) and guide:
        digest["translation_guide_sample"] = dict(list(guide.items())[:8])
    return digest


def creative_strings(model):
    """Every creative suggestion a chapter model already holds."""
    creative = model.get("creative_enrichment") if isinstance(model, dict) else None
    if not isinstance(creative, dict):
        return []
    found = []
    for field in CREATIVE_FIELDS:
        values = creative.get(field)
        if isinstance(values, list):
            found.extend(value for value in values if isinstance(value, str) and value.strip())
    return found


def chapter_arc(book):
    chapters = book.get("chapters")
    if not isinstance(chapters, list):
        return []
    return [
        {"chapter_index": entry.get("chapter_index"), "chapter_title": entry.get("chapter_title", "")}
        for entry in chapters
        if isinstance(entry, dict)
    ]


def neighbour_context(book, models, index):
    """What nearby chapters cover, plus every suggestion the book has already spent."""
    neighbours = []
    pool = []
    for entry in chapter_arc(book):
        number = entry.get("chapter_index")
        if not isinstance(number, int) or number == index or abs(number - index) > SIBLING_WINDOW:
            continue
        used = [clip(value, 160) for value in creative_strings(models.get(number, {}))]
        summarised = models.get(number, {}).get("chapter_summary") or entry.get("chapter_summary") or ""
        neighbours.append({
            "chapter_index": number,
            "chapter_title": entry.get("chapter_title", ""),
            "chapter_summary": clip(summarised, 200),
            "suggestions_already_used": used[:6],
        })
        pool.extend(used)
    return neighbours, pool


def _stream(seed, salt, size):
    """Deterministic splitmix64 index so one run seed reproduces the same briefs."""
    mixed = (seed + salt * 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    mixed = ((mixed ^ (mixed >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    mixed = ((mixed ^ (mixed >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    mixed ^= mixed >> 31
    return mixed % size


def forced_lens(name):
    """Resolve a lens by name (case-insensitive) for --lens."""
    wanted = name.strip().casefold()
    for lens in LENSES:
        if lens[0] == wanted:
            return lens
    raise ValueError(f"Unknown lens '{name}'. Use --list-lenses to see the options.")


def lens_order(run_seed):
    """Seeded permutation of every lens index (Fisher-Yates over a splitmix64 stream)."""
    order = list(range(len(LENSES)))
    state = run_seed & 0xFFFFFFFFFFFFFFFF
    for position in range(len(order) - 1, 0, -1):
        state = (state * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        swap = (state >> 33) % (position + 1)
        order[position], order[swap] = order[swap], order[position]
    return order


def lens_for(run_seed, index):
    """Give every lens once per block of chapters, and never repeat a neighbour's lens."""
    size = len(LENSES)
    block = (index - 1) // size
    order = lens_order(run_seed + block)
    if block:
        previous_last = lens_order(run_seed + block - 1)[size - 1]
        if order[0] == previous_last:
            order[0], order[1] = order[1], order[0]
    return LENSES[order[(index - 1) % size]]


def pick_twist(chapter_seed):
    return TWISTS[_stream(chapter_seed, 2, len(TWISTS))]


def tokens(text):
    """Content words of a string; safe for Indic scripts (never splits vowel signs)."""
    found = set()
    for raw in str(text).split():
        word = raw.strip(PUNCTUATION).casefold()
        if len(word) > 2:
            found.add(word)
    return found


def similarity(candidate, existing):
    """Jaccard overlap of content words; cheap near-duplicate detection."""
    left, right = tokens(candidate), tokens(existing)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def select_novel(values, pool, threshold=DUPLICATE_THRESHOLD):
    """Drop near-duplicates of the pool and keep the rest in their original order.

    A dropped duplicate is never replaced by a weaker one, so a field may end up with
    fewer entries than the model supplied. A field is never emptied completely: its
    least repetitive entry is always retained.
    """
    scored = []
    for position, value in enumerate(values):
        worst = max((similarity(value, other) for other in pool), default=0.0)
        scored.append((worst, position, value))
    ranked = sorted(scored, key=lambda item: (item[0], item[1]))
    kept = [item for item in ranked if item[0] < threshold]
    if not kept and ranked:
        kept = [ranked[0]]
    kept_positions = {item[1] for item in kept}
    kept.sort(key=lambda item: item[1])
    dropped = [item[2] for item in ranked if item[1] not in kept_positions]
    return [item[2] for item in kept], dropped


def merge_gaps(current, patch, path=()):
    """Fill gaps recursively; preserve populated values, runtime state, and identity."""
    if isinstance(current, dict) and isinstance(patch, dict):
        result = copy.deepcopy(current)
        for key, value in patch.items():
            # Runtime ownership and chapter identity cannot be fabricated by this tool.
            if key in RUNTIME_KEYS:
                continue
            if not path and key in IDENTITY_KEYS:
                continue
            if key not in result:
                if not empty(value):
                    result[key] = copy.deepcopy(value)
            else:
                result[key] = merge_gaps(result[key], value, path + (key,))
        return result
    if path[:1] == ("creative_enrichment",) and isinstance(current, list) and isinstance(patch, list):
        return copy.deepcopy(current + [value for value in patch if value not in current])
    if empty(current) and not empty(patch):
        if current is not None and not isinstance(patch, type(current)):
            return copy.deepcopy(current)
        return copy.deepcopy(patch)
    return copy.deepcopy(current)


def trim_patch(patch, chapter):
    """Drop keys this tool may never write, and any tag the chapter has already filled."""
    cleaned = {key: value for key, value in patch.items() if key not in PROTECTED_KEYS}
    for key in ("chapter_title", "chapter_summary"):
        if not empty(chapter.get(key)):
            cleaned.pop(key, None)
    if not empty(chapter.get("further_references")):
        cleaned.pop("further_references", None)
    return cleaned


def flatten_entry(value):
    """Turn one model-supplied entry into a single readable string.

    Local models often answer a structured request with an object (setting, desire,
    obstacle, turn). Downstream writers read plain strings, so structure is flattened to
    text instead of being rejected.
    """
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if isinstance(item, str) and item.strip():
                parts.append(f"{key}: {item.strip()}")
            elif isinstance(item, bool):
                parts.append(f"{key}: {item}")
            elif isinstance(item, (int, float)):
                parts.append(f"{key}: {item}")
            elif isinstance(item, list):
                nested = "; ".join(str(part).strip() for part in item if isinstance(part, str) and part.strip())
                if nested:
                    parts.append(f"{key}: {nested}")
        return ", ".join(parts)
    return ""


def check_string_list(values, label, minimum, problems, required=True):
    if values is None and not required:
        return
    if not isinstance(values, list):
        problems.append(f"{label} must be a list of at least {minimum} strings")
        return
    cleaned = [flatten_entry(value) for value in values]
    cleaned = [value for value in cleaned if value]
    if len(cleaned) < minimum:
        problems.append(f"{label} needs at least {minimum} usable entries (got {len(cleaned)})")
        return
    if len(set(cleaned)) != len(cleaned):
        problems.append(f"{label} entries must be distinct")
        return
    values[:] = cleaned


def normalize_references(value, problems):
    """Canonicalise further_references; strip link-like text, never keep a URL."""
    if not isinstance(value, list):
        problems.append("further_references must be a list of reference topics")
        return None
    normalized = []
    for position, entry in enumerate(value, 1):
        if isinstance(entry, str):
            topic = entry
        elif isinstance(entry, dict):
            unexpected = set(entry) - {"no", "reference", "weblink"}
            if unexpected:
                problems.append(f"further_references[{position}] has unsupported keys: {sorted(unexpected)}")
            topic = str(entry.get("reference", ""))
        else:
            problems.append(f"further_references[{position}] must be a topic string or an object")
            continue
        topic = URL_RE.sub("", topic).strip()
        if not topic:
            problems.append(f"further_references[{position}] needs a reference topic")
            continue
        normalized.append({"no": str(len(normalized) + 1), "reference": topic, "weblink": ""})
    return normalized or None


def fold_creative_keys(patch):
    """Fold model-invented top-level creative keys back into creative_enrichment.

    Local models sometimes answer with e.g. "structural_variants_for_the_chapter" at the
    top level. Those values belong under creative_enrichment, so they are merged there
    instead of being stored as oddly named standalone tags.
    """
    creative = patch.get("creative_enrichment")
    creative = creative if isinstance(creative, dict) else {}
    for key in list(patch):
        if key == "creative_enrichment" or key in PROTECTED_KEYS:
            continue
        normalized = re.sub(r"[^a-z]", "", key.casefold())
        for field in CREATIVE_FIELDS + ("variety_note",):
            if field.replace("_", "") not in normalized:
                continue
            value = patch.pop(key)
            if field == "variety_note":
                if not flatten_entry(creative.get(field)) and flatten_entry(value):
                    creative[field] = flatten_entry(value)
            else:
                entries = value if isinstance(value, list) else [value]
                existing = creative.get(field)
                existing = list(existing) if isinstance(existing, list) else []
                existing.extend(entry for entry in (flatten_entry(item) for item in entries) if entry)
                creative[field] = existing
            break
    if creative:
        patch["creative_enrichment"] = creative
    return patch


def validate_patch(raw):
    try:
        patch = json.loads(raw, parse_constant=reject_constant)
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"response was not valid JSON ({error})")
    if not isinstance(patch, dict) or not patch:
        raise ValueError("response must be one nonempty JSON object")
    patch = fold_creative_keys(patch)
    problems = []
    creative = patch.get("creative_enrichment")
    if not isinstance(creative, dict):
        problems.append("creative_enrichment must be an object")
        creative = {}
    for field, minimum in CREATIVE_REQUIRED.items():
        check_string_list(creative.get(field), f"creative_enrichment.{field}", minimum, problems)
    for field, minimum in CREATIVE_OPTIONAL.items():
        if field in creative:
            check_string_list(creative.get(field), f"creative_enrichment.{field}", minimum, problems, required=False)
    variety_note = flatten_entry(creative.get("variety_note"))
    if not variety_note:
        problems.append("creative_enrichment.variety_note must be a nonempty sentence")
    else:
        creative["variety_note"] = variety_note
    if "further_references" in patch:
        normalized = normalize_references(patch["further_references"], problems)
        if normalized is None:
            patch.pop("further_references", None)
        else:
            patch["further_references"] = normalized
    if problems:
        raise ValueError("; ".join(problems))
    patch["creative_enrichment"] = creative
    return patch


def enforce_novelty(patch, chapter, pool):
    """Drop suggestions that near-duplicate this chapter's own or a neighbour's material."""
    creative = patch.get("creative_enrichment")
    if not isinstance(creative, dict):
        return patch, []
    existing = chapter.get("creative_enrichment")
    existing = existing if isinstance(existing, dict) else {}
    dropped = []
    for field in CREATIVE_REQUIRED:
        values = creative.get(field)
        if not isinstance(values, list):
            continue
        own = existing.get(field)
        own = [value for value in own if isinstance(value, str)] if isinstance(own, list) else []
        creative[field], rejected = select_novel(values, own + pool)
        dropped.extend(f"{field}: {value}" for value in rejected)
    patch["creative_enrichment"] = creative
    return patch, dropped


def describe_additions(before, after):
    """Human-readable list of what the merge actually added."""
    added = []
    for key, value in after.items():
        if key not in before:
            added.append(key)
        elif key == "creative_enrichment" and isinstance(value, dict):
            previous = before.get("creative_enrichment")
            previous = previous if isinstance(previous, dict) else {}
            for field, entries in value.items():
                if isinstance(entries, list):
                    old = previous.get(field)
                    gained = len(entries) - (len(old) if isinstance(old, list) else 0)
                    if gained > 0:
                        added.append(f"creative_enrichment.{field}(+{gained})")
                elif field not in previous:
                    added.append(f"creative_enrichment.{field}")
        elif empty(before.get(key)) and not empty(value):
            added.append(key)
    return ", ".join(added) if added else "nothing"


def build_prompt(book_context, chapter, neighbours, arc, pool, lens, twist, seed):
    return _render(
        ENRICH_USER_PROMPT_TEMPLATE,
        book_context=json.dumps(book_context, ensure_ascii=False, indent=2),
        arc=json.dumps(arc, ensure_ascii=False, indent=2),
        neighbours=json.dumps(neighbours, ensure_ascii=False, indent=2),
        pool=json.dumps(pool[:POOL_LIMIT], ensure_ascii=False, indent=2),
        chapter=json.dumps(chapter, ensure_ascii=False, indent=2),
        seed=seed,
        lens_name=lens[0],
        lens_guidance=lens[1],
        twist=twist,
    )


def repair_prompt(previous, problems):
    return _render(
        REPAIR_PROMPT_TEMPLATE,
        problems=problems,
        previous=clip(previous, 4000),
    )


def run_ollama(prompt, seed, temperature, model_name, system=None, format_json=True):
    payload = {
        "model": model_name,
        "system": system if system is not None else ENRICH_SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "options": {"num_ctx": CONTEXT_WINDOW, "temperature": temperature, "top_p": 0.95,
                    "top_k": 60, "repeat_penalty": 1.12, "seed": seed},
    }
    if format_json:
        payload["format"] = "json"
    vlog(f"[ollama] POST {OLLAMA_URL} model={model_name} seed={seed} temperature={temperature} prompt={len(prompt)} chars")
    for attempt in range(MAX_RETRIES):
        request = urllib.request.Request(OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                result = json.loads(response.read().decode("utf-8"))
            if result.get("error"):
                raise ValueError(result["error"])
            return result["response"]
        except (urllib.error.URLError, TimeoutError):
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(5 * (attempt + 1))


def request_patch(prompt, seed, temperature, model_name):
    """Ask for a patch, and give the model a couple of chances to repair a bad reply."""
    reply = None
    last_error = None
    for attempt in range(MAX_REPAIRS + 1):
        ask = prompt if reply is None else repair_prompt(reply, last_error)
        reply = run_ollama(ask, seed + attempt, temperature, model_name)
        try:
            return validate_patch(reply)
        except ValueError as error:
            last_error = str(error)
            vlog(f"patch rejected ({attempt + 1}): {last_error}")
    raise ValueError(f"model returned no usable patch: {last_error}")


def enrich_chapter(model_file, book, models, show_prompt=False, seed=None, lens_name=None,
                   temperature=DEFAULT_TEMPERATURE, model_name=MODEL):
    """Enrich one chapter model.json in place and return a short result record."""
    model_file = Path(model_file)
    original = model_file.read_bytes()
    chapter = json.loads(original.decode("utf-8-sig"), parse_constant=reject_constant)
    if not isinstance(chapter, dict) or not chapter:
        raise ValueError("Chapter model must be a nonempty JSON object")
    index = chapter.get("chapter_index")
    if not isinstance(index, int):
        raise ValueError("Chapter model needs an integer chapter_index")
    creative = chapter.get("creative_enrichment")
    if creative is not None and not isinstance(creative, dict):
        raise ValueError("Existing creative_enrichment must be an object or null")

    run_seed = secrets.randbelow(2**31) if seed is None else seed
    chapter_seed = (run_seed * 1_000_003 + index) % (2**31)
    lens = forced_lens(lens_name) if lens_name else lens_for(run_seed, index)
    twist = pick_twist(chapter_seed)
    neighbours, pool = neighbour_context(book, models, index)
    prompt = build_prompt(book_digest(book), chapter, neighbours, chapter_arc(book), pool,
                          lens, twist, chapter_seed)
    if show_prompt:
        print(f"=== SYSTEM PROMPT ===\n{ENRICH_SYSTEM_PROMPT}\n\n=== USER PROMPT ===\n{prompt}\n")

    patch = request_patch(prompt, chapter_seed, temperature, model_name)
    patch = trim_patch(patch, chapter)
    patch, dropped = enforce_novelty(patch, chapter, pool)
    merged = merge_gaps(chapter, patch)
    additions = describe_additions(chapter, merged)
    title = chapter.get("chapter_title") or chapter.get("name") or str(index)
    record = {"index": index, "title": title, "lens": lens[0], "twist": twist,
              "added": additions, "dropped": len(dropped), "written": False}
    if merged == chapter:
        print(f"[{index}] {title} — nothing new to add.")
        return record
    if DRY_RUN:
        print(f"[{index}] {title} — DRY RUN would add: {additions}")
        return record

    text = json.dumps(merged, ensure_ascii=False, indent=2, allow_nan=False)
    encoded = (text.replace("\n", NEWLINE) + NEWLINE).encode("utf-8")
    if model_file.read_bytes() != original:
        raise RuntimeError("Model changed during generation; refusing to overwrite concurrent edits")
    history = model_file.parent / "history"
    history.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = history / f"model_enrich_{stamp}_{secrets.token_hex(4)}.json"
    with backup.open("xb") as stream:
        stream.write(original)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=model_file.parent, prefix=".enrich-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
        if model_file.read_bytes() != original:
            raise RuntimeError("Model changed before save; original retained")
        os.replace(temporary, model_file)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    models[index] = merged
    record["written"] = True
    print(f"[{index}] {title} — enriched.")
    vlog(f"variety_note: {patch.get('creative_enrichment', {}).get('variety_note', '')}")
    return record


def main():
    global VERBOSE, DRY_RUN
    parser = argparse.ArgumentParser(
        description="Enrich chapter model.json with book-aware, variety-driven tags via Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python tools/enrich.py lau 15
  python tools/enrich.py lau 2-5,8
  python tools/enrich.py lau all --seed 42
  python tools/enrich.py lau 15 --lens witness --show-prompt
  python tools/enrich.py lau 15 --dry-run
  python tools/enrich.py lau --list-lenses
  python tools/enrich.py help

Reads:   workspaces/pipeline/<bookname>/book.json               (book context + form)
         workspaces/pipeline/<bookname>/chapters/<n>/model.json  (target chapter)
Backups: workspaces/pipeline/<bookname>/chapters/<n>/history/model_enrich_<timestamp>_<id>.json
Writes:  only the target model.json; chapter.md is never read or written.
""",
    )
    parser.add_argument("bookname", help="Book folder under workspaces/pipeline/.")
    parser.add_argument("chapters", nargs="?", help="Number, range, list, all, or '*'.")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-p", "--show-prompt", action="store_true",
                        help="Print the prompts before enriching.")
    parser.add_argument("--seed", type=int,
                        help="Run seed; chapter seeds, lenses, and twists derive from it.")
    parser.add_argument("--lens", help="Force one lens for every selected chapter.")
    parser.add_argument("--model", default=None, help="Ollama model name (default: from progress.json, else %(default)s).")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE,
                        help="Sampling temperature (default: %(default)s).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report the additions without writing anything.")
    parser.add_argument("--list-lenses", action="store_true",
                        help="List the variation lenses and exit.")
    if sys.argv[1:] == ["help"]:
        parser.print_help()
        return 0
    args = parser.parse_args()
    VERBOSE = args.verbose
    DRY_RUN = args.dry_run

    if args.list_lenses:
        load_templates(resolve_book_form(args.bookname))
        width = max(len(name) for name, _ in LENSES)
        for name, guidance in LENSES:
            print(f"{name.ljust(width)}  {guidance}")
        return 0
    if not args.chapters:
        parser.error("chapters is required (a number, range, list, all, or '*')")

    try:
        chapters_root = resolve_chapters_root(args.bookname)
        numbers = parse_chapter_input(args.chapters, chapters_root)
        book = load_book_model(args.bookname)
        load_templates(resolve_book_form(args.bookname))
        regenerate_style_md(args.bookname, book)
        if args.lens:
            forced_lens(args.lens)
    except ValueError as error:
        parser.error(str(error))

    # Resolve the model: CLI override → progress.json → default.
    model_name = args.model or resolve_model(args.bookname)

    # Load every chapter model once so neighbours can be compared with each other.
    models = {}
    for number in parse_chapter_input("all", chapters_root):
        try:
            models[number] = read_model(_chapter_file(chapters_root / str(number)))
        except (OSError, ValueError) as error:
            vlog(f"[{number}] unreadable model (skipped as context): {error}")

    results = []
    failures = 0
    for number in numbers:
        try:
            results.append(enrich_chapter(_chapter_file(chapters_root / str(number)), book, models,
                                          args.show_prompt, args.seed, args.lens,
                                          args.temperature, model_name))
        except Exception as error:
            print(f"[{number}] FAILED: {error}", file=sys.stderr)
            failures += 1

    enriched = [r for r in results if r.get("written")]
    unchanged = [r for r in results if not r.get("written")]
    lenses = {}
    for result in results:
        lenses[result["lens"]] = lenses.get(result["lens"], 0) + 1
    applied = ", ".join(f"{name}({count})" for name, count in sorted(lenses.items()))

    print()
    print("=" * 60)
    print(f"Enrichment complete for '{args.bookname}' ({book.get('form', 'novel')})")
    print(f"  Total chapters selected : {len(numbers)}")
    print(f"  Enriched               : {len(enriched)}")
    print(f"  Unchanged              : {len(unchanged)}")
    print(f"  Failed                 : {failures}")
    if applied:
        print(f"  Lenses used            : {applied}")
    if enriched:
        print("  Chapters enriched:")
        for result in enriched:
            print(f"    [{result['index']}] {result['title']} — {result['lens']}")
    if unchanged:
        print("  Chapters with nothing new:")
        for result in unchanged:
            print(f"    [{result['index']}] {result['title']} — {result['lens']}")
    print("=" * 60)
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())