#!/usr/bin/env python3
"""
Pipeline chapter writer.

Reads chapters/<n>/model.json, flattens the complete JSON into context.md,
builds a prompt from poetry.md + that context, runs it through Ollama,
and saves the result to chapters/<n>/chapter.md.

Usage:
    python tools/write.py behula 2       # single chapter
    python tools/write.py behula 2-5     # inclusive range
    python tools/write.py behula 2,5,8   # list
    python tools/write.py behula 2-5,8   # mixed
    python tools/write.py behula all     # all chapters
    python tools/write.py behula "*"     # all chapters (quote the wildcard)
"""

import argparse
import json
import os
import tempfile
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from quality import register_draft, read_json, digest, read_chapter_model, chapter_model_file

BASE_DIR = Path(__file__).resolve().parent
# Repo root is one level above tools/
REPO_ROOT = BASE_DIR.parent

# The single-page Pijush/Dehlij master prompt lives in the framework.

PRESET_DIR = REPO_ROOT / ".framework" / "templates" / "preset"
POETRY_FILE = PRESET_DIR / "pijush.behula.md"
DEFAULT_STYLE = "pijush"          # poetry default style
DEFAULT_STYLE_NOVEL = "dialogue"  # novel default style
DEFAULT_PRESET = PRESET_DIR / "pijush.md"
SUBJECTS_FILE = REPO_ROOT / ".framework" / "context" / "poetry" / "syntax" / "gosai_bangla" / "syntax.md"

# Form-specific writer templates (system prompts + user prompt template) live
# per book in workspaces/pipeline/<bookname>/layout/write-{poetry|novel}/. They
# are cloned into each pipeline at scaffold time and are the sole source of
# truth for the writer; the framework is no longer consulted for these.
_ACTIVE_DIR: Path | None = None

MODEL = "gemma4:latest"
CONTEXT_WINDOW = 64000  # num_ctx: token context window size
TEMPERATURE = 0.7      # low temperature for focused, consistent output
TOP_P = 0.9            # nucleus sampling

# Novel segmentation: a novel chapter targets a large word count (often 4000+),
# which a single Ollama generation cannot reliably produce in one coherent pass.
# We split each novel chapter into continuous segments of roughly this many words,
# each generated in sequence while threading the prior segments' prose so context,
# theme, and style stay continuous across the chapter.
WORDS_PER_SEGMENT = 1200
# Cap how much prior prose is threaded forward, to stay well inside the context
# window while still carrying continuity into the next segment.
MAX_CONTINUITY_CHARS = 16000


def resolve_model(chapter_dir: Path) -> str:
    """Resolve the Ollama model name from the book's pipeline book plan.

    Reads `workspaces/pipeline/<bookname>/progress.json` → `model`, falling
    back to `book.json` → `model`. If no model is declared, raises ValueError —
    the writer never assumes a model.
    """
    pipeline = chapter_dir.parents[1]
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
    raise ValueError(
        f"No model declared for this book. Set 'model' in {pipeline / 'book.json'} before writing."
    )

# Writer system prompts + user prompt template, loaded per form at runtime.
SYSTEM_PROMPT_BN: str = ""
SYSTEM_PROMPT_EN: str = ""
USER_PROMPT_TEMPLATE: str = ""
USER_PROMPT_SEGMENT_TEMPLATE: str = ""

# Use 127.0.0.1 (IPv4) explicitly. On this machine "localhost" resolves to
# ::1 (IPv6) first, which hits a *different* Ollama server (native Windows)
# that does NOT have the `writer-gemma` model. The WSL Ollama instance that
# does host `writer-gemma` is bound to 127.0.0.1 only.
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
TIMEOUT = 900  # seconds; long chapters can take a while


def _load_text(filename: str) -> str:
    """Read a template text file, tolerating a UTF-8 BOM."""
    if _ACTIVE_DIR is None:
        raise FileNotFoundError("No layout directory resolved; load_templates() must run first.")
    path = _ACTIVE_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing writer template: {path}")
    return path.read_text(encoding="utf-8-sig")


def _render(template: str, **values) -> str:
    """Substitute `{name}` placeholders with values (safe for values containing braces)."""
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def load_templates(form: str, layout_dir: Path) -> None:
    """(Re)load the writer templates for a book form (`poetry` or `novel`).

    Templates are read from the book's own pipeline folder
    `workspaces/pipeline/<bookname>/layout/write-{form}/` (passed as
    *layout_dir*). This is the sole source of writer templates; the shared
    `.framework/templates/backlog` tree is no longer consulted.
    """
    global _ACTIVE_DIR, SYSTEM_PROMPT_BN, SYSTEM_PROMPT_EN, USER_PROMPT_TEMPLATE
    global USER_PROMPT_SEGMENT_TEMPLATE
    form = (form or "poetry").strip().casefold()
    if form not in {"poetry", "novel"}:
        raise ValueError(f"Unsupported write form: {form!r}")
    _ACTIVE_DIR = layout_dir / f"write-{form}"
    SYSTEM_PROMPT_BN = _load_text("system_prompt_bn.md")
    SYSTEM_PROMPT_EN = _load_text("system_prompt_en.md")
    USER_PROMPT_TEMPLATE = _load_text("user_prompt_template.md")
    # The novel form carries an extra per-segment prompt template (continuous
    # multi-segment chapters). Poetry never needs it; leave it empty there.
    if form == "novel":
        USER_PROMPT_SEGMENT_TEMPLATE = _load_text("user_prompt_segment_template.md")
    else:
        USER_PROMPT_SEGMENT_TEMPLATE = ""

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

VERBOSE = False
SHOW_PROMPT = False

# Retry behaviour for transient Ollama failures.
MAX_RETRIES = 3
RETRY_DELAY = 5.0  # seconds between attempts (linear backoff)


def vlog(*args) -> None:
    """Print a verbose-only message (prefixed with a dim '[v]' marker)."""
    if VERBOSE:
        print("[v]", *args)


def info(*args) -> None:
    print(*args)


def parse_chapter_input(value: str, chapters_root: Path | None = None) -> list[int]:
    """Parse numbers/ranges, or discover all numeric chapter folders in order."""
    if value.strip().lower() == "continue":
        if chapters_root is None:
            raise ValueError("A chapters directory is required")
        for number in parse_chapter_input("all", chapters_root):
            folder = chapters_root / str(number)
            draft = folder / "chapter.md"
            model = read_chapter_model(folder)
            if not draft.exists() or model.get("draft", {}).get("sha256") != digest(draft.read_bytes()):
                return [number]
        return []
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


def resolve_chapters_root(bookname: str) -> Path:
    """Resolve a book folder relative to this script's repository root."""
    if not bookname.strip() or bookname in {".", ".."} or any(
        char in bookname for char in '/\\:<>"|?*'
    ):
        raise ValueError("Bookname must be a single pipeline folder name")
    chapters_root = REPO_ROOT / "workspaces" / "pipeline" / bookname / "chapters"
    if not chapters_root.is_dir():
        raise ValueError(f"Chapters directory not found: {chapters_root}")
    return chapters_root


def resolve_preset(style: str | None = None) -> Path:
    """Resolve a style nickname to its preset file under ``.framework/templates/preset/``.

    The write command always uses a **preset** — a fixed, pre-authored style
    document — never a style composed on the fly. Resolution:

    1. If a `<style>` nickname is supplied, match a preset file whose stem's
       first segment equals the nickname (case-insensitive): ``desh`` ->
       ``preset/desh.md``, ``pijush`` -> ``preset/pijush.md`` (and
       ``pijush.behula.md``).
    2. If the nickname cannot be matched, fall back to ``preset/pijush.md``.
    3. If no nickname is supplied, default to ``pijush`` (and thus
       ``preset/pijush.md``).

    Raises ValueError only when ``preset/pijush.md`` itself is missing, listing
    the presets available for guidance.
    """
    nickname = (style or DEFAULT_STYLE).strip().lower()
    presets = sorted(PRESET_DIR.glob("*.md")) if PRESET_DIR.is_dir() else []
    if presets:
        # Prefer an exact-stem match (``pijush`` -> ``pijush.md``) before a
        # dot-prefix match (``pijush.behula.md``).
        for preset in presets:
            if preset.stem.lower() == nickname:
                return preset
        for preset in presets:
            if preset.stem.lower().split(".", 1)[0] == nickname:
                return preset
    # Unmatched (or no presets dir): use the default preset if it exists.
    if DEFAULT_PRESET.is_file():
        return DEFAULT_PRESET
    # Legacy fallback, then an explicit error with guidance.
    if POETRY_FILE.is_file():
        return POETRY_FILE
    names = ", ".join(p.stem for p in presets) if presets else "(none)"
    raise ValueError(
        f"No preset for style '{style}' and default preset 'pijush.md' is missing. "
        f"Available presets: {names}."
    )


def resolve_novel_style(nickname: str) -> Path:
    """Resolve a novel style nickname to its preset under ``.framework/templates/preset/``.

    Novel styles are presets just like poetry styles; both forms resolve from the
    same ``.framework/templates/preset/`` directory. A preset file must exist
    whose stem (or first dot-segment) matches the nickname. Raises FileNotFoundError
    if no matching preset is found.
    """
    return resolve_preset(nickname)


def default_style_for_form(form: str) -> str:
    """Return the default style nickname for a book form."""
    return DEFAULT_STYLE if (form or "poetry").strip().casefold() == "poetry" else DEFAULT_STYLE_NOVEL


def load_poetry(chapter_dir: Path | None = None, style: str | None = None,
                form: str = "poetry") -> str:
    """Load the style prompt for the write command.

    Priority:
    1. If a <style> is explicitly provided in the command, resolve it as a 
       preset under ``.framework/templates/preset/``.
    2. Otherwise, if a local ``style.md`` exists in the book pipeline root, 
       use it exclusively.
    3. Fall back to the form's default preset (pijush/dialogue).
    """
    form = (form or "poetry").strip().casefold()
    
    # 1. Explicit style requested? Use preset.
    if style:
        default = default_style_for_form(form)
        nickname = style.strip().lower()
        source = resolve_preset(nickname)
        style_name = source.stem
        info(f"Style: {style_name} ({source})")
        vlog(f"Loading style from: {source}")
        text = source.read_text(encoding="utf-8")
        vlog(f"  style loaded: {len(text)} chars, {text.count(chr(10)) + 1} lines")
        return text

    # 2. No explicit style? Prefer local style.md.
    if chapter_dir:
        local_style = chapter_dir.parents[1] / "style.md"
        if local_style.exists():
            info(f"Style: local ({local_style})")
            vlog(f"Loading style from: {local_style}")
            text = local_style.read_text(encoding="utf-8")
            vlog(f"  style loaded: {len(text)} chars, {text.count(chr(10)) + 1} lines")
            return text

    # 3. Fallback to form default preset.
    default = default_style_for_form(form)
    source = resolve_preset(default)
    style_name = source.stem
    info(f"Style: {style_name} ({source})")
    vlog(f"Loading style from: {source}")
    text = source.read_text(encoding="utf-8")
    vlog(f"  style loaded: {len(text)} chars, {text.count(chr(10)) + 1} lines")
    return text


def load_subjects() -> str:
    """Load thematic subjects from gosai_bangla.md for aligned generation."""
    vlog(f"Loading subjects from: {SUBJECTS_FILE}")
    if not SUBJECTS_FILE.exists():
        vlog(f"  subjects file not found, continuing without it")
        return ""
    text = SUBJECTS_FILE.read_text(encoding="utf-8")
    vlog(f"  subjects loaded: {len(text)} chars, {text.count(chr(10)) + 1} lines")
    return text


def build_system_prompt(language: str = "bn", override: str = "",
                        gist: str = "", storyline: str = "", style: str = "") -> str:
    """Combine the base persona directive with style, subject, guardrail, theme,
    and override references — the book-stable directives.

    *language* selects the persona directive language: 'en' (or 'English') uses
    the English prompt, anything else uses the Bengali prompt. The style directive
    (the book's resolved style.md / preset) and the gist guardrail and storyline
    theme grounding are appended here so the per-chapter user prompt stays short
    (title, word target, output format, and chapter context).
    """
    lang = language.strip().lower()
    is_en = lang in {"en", "english", "eng"}
    base = SYSTEM_PROMPT_EN if is_en else SYSTEM_PROMPT_BN
    subjects = load_subjects() if not is_en else ""
    parts = [base]
    # Override first — the human mandate is the most impactful directive and
    # must sit immediately after the base persona.
    if override:
        parts.append(
            "\n\nবিশেষ-নির্দেশনা (Human Override): নিচের নির্দেশনাগুলো কঠোরভাবে মেনে চলো।\n\n"
            + override
        )
    if subjects:
        parts.append(
            "\n\nথিম-নির্দেশনা (বিষয়ভিত্তিক রেফারেন্স): নিচের বিষয়বস্তু কাঠামো, রূপক পরিবার "
            "এবং পবিত্র শব্দগুলির সাথে সামঞ্জস্যপূর্ণ থাকো, যেন রচনা নির্দিষ্ট থিমের "
            "মর্মবাণী প্রতিফলিত করে।\n\n"
            + subjects
        )
    if storyline:
        parts.append(
            "\n\n" + frame_theme(storyline)
        )
    if gist:
        parts.append(
            "\n\n" + frame_guardrail(gist)
        )
    if style:
        parts.append(
            "\n\nশৈলী-নির্দেশনা (Style): নিচের কণ্ঠ, দর্শন ও গঠন মেনে চলো।\n\n"
            + style
        )
    return "".join(parts)


def load_context(model_file: Path) -> str:
    """Flatten the model via flatten.py, save context.md, and return Markdown.

    The shared flatten routine lives in flatten.py (single source of truth).
    Every chapter is flattened fresh, immediately before writing, so context.md
    always reflects the current model.json.
    """
    import flatten as flatten_module

    context_file = flatten_module.flatten_chapter(model_file)
    context = context_file.read_text(encoding="utf-8")
    vlog(f"Context saved -> {context_file} ({len(context)} chars)")
    return context


def load_override(model_file: Path) -> str:
    """Read the book's human override mandate (override.txt), if present.

    Returns the file's content, or an empty string when absent or holding only
    the default "No transform required." line.
    """
    # model_file is chapters/<n>/chapter.json (or model.json), so the pipeline
    # root is two parents up.
    override_file = model_file.parents[2] / "override.txt"
    if not override_file.exists():
        return ""
    text = override_file.read_text(encoding="utf-8-sig").strip()
    if not text or text == "No transform required.":
        return ""
    vlog(f"Override mandate loaded: {len(text)} chars")
    return text


def load_gist(model_file: Path) -> str:
    """Read the book's seed premise (gist.md) as a guardrail.

    The gist is the author's declared essence — the one-line high concept plus
    its expansion. Every chapter's consciousness must never drift away from it.
    It is a guardrail (an anchor), never a quotation source. Returns the
    content, or an empty string when absent.
    """
    gist_file = model_file.parents[2] / "gist.md"
    if not gist_file.exists():
        return ""
    text = gist_file.read_text(encoding="utf-8-sig").strip()
    if not text:
        return ""
    vlog(f"Gist guardrail loaded: {len(text)} chars")
    return text


def load_storyline(model_file: Path) -> str:
    """Read the book's storyline (storyline.md) for thematic grounding.

    The storyline is the source of the book's declared themes, imagery, and
    world. Every chapter's theme must trace to it; the writer must not invent
    subject matter absent from it. Returns the content, or an empty string when
    absent.
    """
    storyline_file = model_file.parents[2] / "storyline.md"
    if not storyline_file.exists():
        return ""
    text = storyline_file.read_text(encoding="utf-8-sig").strip()
    if not text:
        return ""
    vlog(f"Storyline theme grounding loaded: {len(text)} chars")
    return text


def frame_guardrail(gist: str) -> str:
    """Frame the gist as the author's core premise — the book's essential identity."""
    if not gist:
        return "(none — no gist guardrail available)"
    return (
        "CORE PREMISE (the author's one-line essence of the book — this is what "
        "the whole work is about; keep every chapter anchored to this idea, never "
        "contradict it):\n\n"
        + gist
    )


def frame_theme(storyline: str) -> str:
    """Frame the storyline as the book's thematic world — themes, imagery, symbols."""
    if not storyline:
        return "(none — no storyline theme grounding available)"
    return (
        "THEME GROUNDING (the book's declared themes, imagery, and world — draw "
        "your symbols and imagery from this reservoir, invent nothing beyond it):\n\n"
        + storyline
    )


def build_prompt(context: str, number: int, language: str = "bn",
                 title: str = "", word_target: int = 0) -> str:
    """Build the per-chapter user prompt from the chapter model.

    Kept deliberately short: the chapter number, title, word target, and the
    flattened chapter context. Book-stable directives — the style directive,
    gist guardrail, storyline theme grounding, and the human override — are
    handled in the system prompt (``build_system_prompt``).
    """
    lang = language.strip().lower()
    is_en = lang in {"en", "english", "eng"}
    lang_word = "English" if is_en else "Bengali"
    return _render(
        USER_PROMPT_TEMPLATE,
        number=number,
        title=title or "",
        word_target=word_target or 0,
        lang_word=lang_word,
        context=context,
    )


def segment_count_for(chapter_model: dict, form: str) -> int:
    """How many continuous segments a chapter's target length implies.

    Poetry always has a single segment per chapter (a small word target). A
    novel chapter targets a large word count (often 4000+ words), which a single
    generation cannot produce coherently; it is split into continuous segments
    so their summed word targets are almost equal to the chapter's `word_target`.

    The chapter's `segments` list (written by enrich) is authoritative: it holds
    the exact segment plan. When it declares more than one segment, that count is
    used. Otherwise the count is derived from `word_target / WORDS_PER_SEGMENT`.
    """
    if form == "poetry":
        return 1
    segments = chapter_model.get("segments")
    if isinstance(segments, list) and len(segments) > 1:
        return len(segments)
    word_target = chapter_model.get("word_target")
    if isinstance(word_target, (int, float)) and word_target > 0:
        return max(1, -(-int(word_target) // WORDS_PER_SEGMENT))
    # No word target and no multi-segment plan: a single continuous segment.
    return 1


def build_segment_prompt(context: str, number: int,
                         segment: int, total: int, word_target: int,
                         prior_text: str, language: str = "bn") -> str:
    """Build the prompt for one segment of a multi-segment novel chapter.

    Threads the prior segments' prose (``prior_text``) so the generated segment
    continues the same context, theme, and style without re-opening the chapter.
    """
    lang = language.strip().lower()
    is_en = lang in {"en", "english", "eng"}
    lang_word = "English" if is_en else "Bengali"
    return _render(
        USER_PROMPT_SEGMENT_TEMPLATE,
        number=number,
        segment=segment,
        total=total,
        word_target=word_target,
        prior_text=prior_text or "(this is the first segment — no prior prose)",
        lang_word=lang_word,
        context=context,
    )


def continuity_window(text: str) -> str:
    """Clip prior-segment prose to a bounded tail for continuity threading."""
    if not text:
        return ""
    if len(text) <= MAX_CONTINUITY_CHARS:
        return text
    return text[-MAX_CONTINUITY_CHARS:].lstrip()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (cursor/color codes) from text."""
    return ANSI_RE.sub("", text)


_ACTIVE_SESSION: "WriteSession | None" = None


class WriteSession:
    """A stateful Ollama ``/api/chat`` session for one book-write command.

    The system prompt is sent once (as the first message) and the model is kept
    loaded via ``keep_alive``. Each chapter is a fresh user turn; a short rolling
    window of the last ``rolling`` chapters (user+assistant pairs) is retained for
    cross-chapter continuity, and older turns are trimmed so the context does not
    grow unbounded.
    """

    def __init__(self, system_prompt: str, model: str = MODEL, rolling: int = 2):
        self.system_prompt = system_prompt
        self.model = model
        self.rolling = max(0, rolling)
        self.messages: list[dict[str, str]] = []
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})
        info(f"\n--- SYSTEM PROMPT (session start) ---\n{system_prompt}\n"
             f"--- END SYSTEM PROMPT ---\n")

    def chat(self, user_prompt: str) -> str:
        """Send one user turn and return the assistant's reply."""
        self.messages.append({"role": "user", "content": user_prompt})
        reply = _chat_once(self.model, self.messages)
        self.messages.append({"role": "assistant", "content": reply})
        self._trim()
        return reply

    def _trim(self) -> None:
        """Keep the system message plus the last ``rolling`` (user, assistant) pairs."""
        head = 1 if (self.messages and self.messages[0]["role"] == "system") else 0
        body = self.messages[head:]
        if self.rolling <= 0:
            body = []
        else:
            body = body[-(self.rolling * 2):]
        self.messages = self.messages[:head] + body


def _chat_once(model: str, messages: list[dict[str, str]]) -> str:
    """POST one /api/chat request and return the assistant text (with retries)."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {
            "num_ctx": CONTEXT_WINDOW,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
        },
    }
    vlog(f"[ollama] POST {OLLAMA_CHAT_URL} model='{model}' think=False stream=False "
         f"keep_alive=30m num_ctx={CONTEXT_WINDOW} temperature={TEMPERATURE} top_p={TOP_P}")
    encoded = json.dumps(payload).encode("utf-8")

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(
            OLLAMA_CHAT_URL,
            data=encoded,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
            vlog(f"[ollama] attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * attempt
                vlog(f"[ollama] retrying in {delay:.1f}s ...")
                time.sleep(delay)
                continue
            raise RuntimeError(f"Ollama request failed after {MAX_RETRIES} attempts: {e}") from e

        elapsed = time.time() - t0
        vlog(f"[ollama] Completed in {elapsed:.2f}s (attempt {attempt})")
        data = json.loads(body)
        content = (data.get("message") or {}).get("content", "")
        if not content:
            # Fall back to the /api/generate-style "response" field just in case.
            content = data.get("response", "")
        cleaned = strip_ansi(content)
        if cleaned != content:
            vlog(f"[ollama] Removed {len(content) - len(cleaned)} ANSI escape chars")
        return cleaned.strip()

    raise RuntimeError(f"Ollama request failed: {last_error}")


def reset_write_session() -> None:
    """Drop the active session so a fresh one starts for the next write command."""
    global _ACTIVE_SESSION
    _ACTIVE_SESSION = None


def run_ollama(prompt: str, language: str = "bn", model: str = MODEL, override: str = "",
               gist: str = "", storyline: str = "", style: str = "") -> str:
    """Send one user turn within the book's shared write session.

    Builds the book-stable system prompt, reuses the active session when its
    system prompt and model match, and otherwise starts a new session (system
    prompt sent once). Returns the generated text.
    """
    global _ACTIVE_SESSION
    sys_prompt = build_system_prompt(language, override, gist, storyline, style)
    if _ACTIVE_SESSION is None or _ACTIVE_SESSION.model != model \
            or _ACTIVE_SESSION.system_prompt != sys_prompt:
        _ACTIVE_SESSION = WriteSession(sys_prompt, model)
    return _ACTIVE_SESSION.chat(prompt)


def resolve_version_dir(model_file: Path, segment: int | None = None) -> Path:
    """Resolve the owning segment; segment indices are not revision numbers."""
    chapter = json.loads(model_file.read_text(encoding="utf-8-sig"))
    pipeline = model_file.parents[2]
    book_file = pipeline / "book.json"
    if not book_file.exists():
        book_file = pipeline / "model.json"
    book = json.loads(book_file.read_text(encoding="utf-8-sig"))
    form = book.get("form", chapter.get("form"))
    if form == "poetry":
        if segment not in (None, 1):
            raise ValueError("Poetry has exactly one segment: 1")
        segment = 1
    elif form == "novel":
        segments = chapter.get("segments", [])
        if not segments:
            segments = [int(p.name) for p in (model_file.parent / "segments").iterdir()
                        if p.is_dir() and p.name.isdecimal()]
        if segment is None:
            # The novel write path composes the whole chapter continuously across
            # all segments and archives the prior chapter-level draft once; when no
            # single segment is requested, default to the first segment's folder.
            segment = min(segments) if segments else 1
        if type(segment) is not int or segment < 1 or (segments and segment not in segments):
            raise ValueError("Segment must match an existing novel chapter segment")
    else:
        raise ValueError("Book model must declare form as poetry or novel")
    folder = model_file.parent / "segments" / str(segment)
    if not folder.is_dir():
        raise ValueError(f"Segment directory not found: {folder}")
    return folder / "version"


def save_chapter(out_file: Path, output: str, previous: bytes | None, version_dir: Path) -> Path | None:
    """Verify and archive the prior draft, then atomically install its replacement."""
    if not output.strip():
        raise ValueError("Empty output; preserving the current draft")
    def check_unchanged():
        current = out_file.read_bytes() if out_file.exists() else None
        if current != previous:
            raise RuntimeError(f"Draft changed during generation; not overwriting {out_file}")

    check_unchanged()
    backup = None
    if previous is not None:
        version_dir.mkdir(parents=True, exist_ok=True)
        versions = [int(match.group(1)) for path in version_dir.iterdir()
                    if (match := re.fullmatch(r"chapter_v([0-9]+)\.md", path.name))]
        version = max(versions, default=0) + 1
        while True:
            backup = version_dir / f"chapter_v{version}.md"
            try:
                with backup.open("xb") as stream:
                    stream.write(previous)
                break
            except FileExistsError:
                version += 1
        if backup.read_bytes() != previous:
            raise RuntimeError(f"Backup verification failed: {backup}")

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=out_file.parent, prefix=".chapter-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((output + "\n").encode("utf-8"))
        check_unchanged()
        os.replace(temporary, out_file)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return backup


def resolve_book_form(chapter_dir: Path) -> str:
    """Resolve the book's declared form (`poetry` or `novel`) from the pipeline book model.

    Falls back to `poetry` when the field is missing or unreadable.
    """
    pipeline = chapter_dir.parents[1]
    for name in ("book.json", "model.json"):
        book_file = pipeline / name
        if book_file.exists():
            try:
                book = json.loads(book_file.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                continue
            form = book.get("form")
            if isinstance(form, str) and form.strip():
                return form.strip()
    return "poetry"


def book_language(chapter_dir: Path) -> str:
    """Resolve the book's configured language from the pipeline book model.

    Falls back to Bengali when the field is missing or unreadable, preserving
    the legacy default for books scaffolded without an explicit language.
    """
    pipeline = chapter_dir.parents[1]
    for name in ("book.json", "model.json"):
        book_file = pipeline / name
        if book_file.exists():
            try:
                book = json.loads(book_file.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                continue
            lang = book.get("language") or book.get("lang")
            if isinstance(lang, str) and lang.strip():
                return lang.strip()
    return "bn"


def write_chapter(model_file: Path, segment: int | None = None, style: str | None = None) -> None:
    number = int(model_file.parent.name)
    info(f"\n=== Chapter {number} ===")
    chapter_dir = model_file.parent
    vlog(f"[{number}] Chapter dir ready: {chapter_dir}")

    out_file = chapter_dir / "chapter.md"
    previous = out_file.read_bytes() if out_file.exists() else None
    # Load the form-specific writer templates before writing, from the book's
    # own pipeline layout/ folder — the sole source of writer templates.
    form = resolve_book_form(chapter_dir)
    # For a novel, `--segment <x>` means "write the whole chapter across all
    # segments" — the chapter is composed continuously, so the per-segment
    # selector is ignored and the first segment's version folder is used for
    # archiving. Poetry always uses segment 1.
    version_dir = resolve_version_dir(model_file, segment if form == "poetry" else None)
    layout_dir = chapter_dir.parents[1] / "layout"
    load_templates(form, layout_dir)
    model = resolve_model(chapter_dir)
    # Style resolution: a provided <style> selects a preset (poetry) or a novel
    # style (novel); otherwise the book's own style.md is used, falling back to
    # the form's default — pijush for poetry, dialogue for novel.
    poetry = load_poetry(chapter_dir, style, form)
    context = load_context(model_file)
    language = book_language(chapter_dir)
    override = load_override(model_file)
    gist = load_gist(model_file)
    storyline = load_storyline(model_file)
    chapter_model = read_chapter_model(chapter_dir)
    title = str(chapter_model.get("chapter_title") or chapter_model.get("title") or "").strip()
    word_target = chapter_model.get("word_target")
    if not isinstance(word_target, (int, float)) or word_target <= 0:
        word_target = 0
    vlog(f"[{number}] Language resolved: {language}")
    vlog(f"[{number}] Model resolved: {model}")
    vlog(f"[{number}] Form resolved: {form}")
    vlog(f"[{number}] Title resolved: {title!r}")
    vlog(f"[{number}] Word target resolved: {word_target}")

    # Poetry: a single segment per chapter — one generation, one draft.
    if form == "poetry":
        prompt = build_prompt(
            context, number, language,
            title, word_target,
        )
        
        # Strictly enforce the requested Bengali format
        format_directive = (
            f"\n\nOUTPUT FORMAT (Strictly follow this structure):\n"
            f"## শিরোনামঃ \n{title}\n\n"
            f"## কবিতাঃ\n[Write the poetry content here]\n\n"
            f"## সারাংশঃ\n[Write the chapter summary here]"
        )
        prompt += format_directive

        if SHOW_PROMPT:
            _show_request(number, model, language, prompt, override=override,
                          gist=gist, storyline=storyline, style=poetry)
        info(f"[{number}] Generating chapter from complete model context ...")
        t0 = time.time()
        output = run_ollama(prompt, language, model, override, gist, storyline, poetry)
        elapsed = time.time() - t0
        # If the body came out short of the target, extend it until it is close.
        output = _ensure_length(number, output, word_target, language, model, override)
        _finish_chapter(chapter_dir, out_file, output, previous, version_dir, number, elapsed)
        return

    # Novel: the chapter targets a large word count and is split into
    # continuous segments, each generated in sequence while threading the prior
    # segments' prose so context, theme, and style stay continuous. Each
    # segment is written to its own segments/<idx>/segment.md, and the full
    # concatenated prose is written to the chapter's chapter.md.
    chapter_model = read_chapter_model(chapter_dir)
    total = segment_count_for(chapter_model, form)
    per_segment_words = -(-int(chapter_model.get("word_target", WORDS_PER_SEGMENT)) // total)
    info(f"[{number}] Novel chapter → {total} continuous segment(s) "
         f"(~{per_segment_words} words each)")
    t0 = time.time()
    segments: list[str] = []
    for idx in range(1, total + 1):
        prior_text = continuity_window("\n\n".join(segments))
        prompt = build_segment_prompt(
            context, number, idx, total, per_segment_words,
            prior_text, language,
        )
        if SHOW_PROMPT:
            _show_request(number, model, language, prompt, label=f"segment {idx}/{total}",
                          override=override, gist=gist, storyline=storyline, style=poetry)
        info(f"[{number}] Generating segment {idx}/{total} ...")
        seg_out = run_ollama(prompt, language, model, override, gist, storyline, poetry)
        if not seg_out.strip():
            raise ValueError(f"Segment {idx}/{total} returned empty output")
        segments.append(seg_out.strip())
        # Write this segment's prose to its own segment.md.
        _write_segment(chapter_dir, idx, seg_out.strip())
        vlog(f"[{number}] segment {idx}/{total}: {len(seg_out)} chars")
    output = "\n\n".join(segments)
    elapsed = time.time() - t0
    _finish_chapter(chapter_dir, out_file, output, previous, version_dir, number, elapsed)


def _write_segment(chapter_dir: Path, segment_index: int, text: str) -> Path:
    """Write one novel segment's prose to segments/<idx>/segment.md atomically."""
    seg_file = chapter_dir / "segments" / str(segment_index) / "segment.md"
    seg_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=seg_file.parent, prefix=".segmd-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((text + "\n").encode("utf-8"))
        os.replace(temporary, seg_file)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return seg_file


def _show_request(number: int, model: str, language: str, prompt: str,
                  label: str = "chapter", override: str = "",
                  gist: str = "", storyline: str = "", style: str = "") -> None:
    """Print a single full request (system prompt + user prompt) for -p mode."""
    info(f"\n[{number}] ============ COMPLETE REQUEST ({label}) ============")
    info(f"[{number}] model      = {model}")
    info(f"[{number}] language   = {language}")
    info(f"[{number}] num_ctx    = {CONTEXT_WINDOW}")
    info(f"[{number}] temperature= {TEMPERATURE}")
    info(f"[{number}] top_p      = {TOP_P}")
    info(f"[{number}] think      = False, stream = False")
    sys_prompt = build_system_prompt(language, override, gist, storyline, style)
    info(f"\n[{number}] ----- SYSTEM PROMPT ({len(sys_prompt)} chars) -----")
    info(sys_prompt)
    info(f"[{number}] ----- END SYSTEM PROMPT -----")
    info(f"\n[{number}] ----- PROMPT ({len(prompt)} chars) -----")
    info(prompt)
    info(f"[{number}] ----- END PROMPT -----")
    info(f"[{number}] ============ END REQUEST ============\n")


def _count_body_words(output: str) -> int:
    """Count words in the poetry body, ignoring the title/summary headings."""
    text = output.strip()
    # If the output uses the structured format, drop the শিরোনাম and সারাংশ sections
    # and count only the কবিতাঃ body. Headings may be "## " or "# " prefixed.
    for marker in ("## কবিতাঃ", "# কবিতাঃ", "# কবিতা:", "## কবিতা:"):
        if marker in text:
            body = text.split(marker, 1)[1]
            for end_marker in ("## সারাংশঃ", "# সারাংশঃ", "# সারাংশ:", "## সারাংশ:"):
                if end_marker in body:
                    body = body.split(end_marker, 1)[0]
                    break
            return len(body.split())
    return len(text.split())


def _ensure_length(number: int, output: str, word_target: int, language: str,
                   model: str, override: str) -> str:
    """Extend a short poetry draft until its body is close to word_target.

    When the generated body falls well below the target (under 75%), ask the
    model to continue the same poem, deepening it without starting over. This
    iterates up to a few times, growing the body toward the target.
    """
    if not word_target or word_target <= 0:
        return output
    text = output.strip()
    current = _count_body_words(text)
    lower = int(word_target * 0.75)
    info(f"[{number}] Body words: {current} (target {word_target}, lower {lower})")

    attempts = 0
    while current < lower and attempts < MAX_RETRIES:
        attempts += 1
        extend_prompt = (
            f"The poem above is currently {current} words but the required length "
            f"is {word_target} words. Continue and deepen the SAME poem — do not "
            f"restart, do not add a new title or summary. Weave in more of the "
            f"riverine and sensory imagery (flora, fauna, silt, monsoon, folk-myth) "
            f"until the body alone reaches close to {word_target} words. Keep the "
            f"same voice, language, and structure. Output only the complete, "
            f"expanded poem body.\n\nExisting poem:\n\n{text}"
        )
        info(f"[{number}] Extending body (attempt {attempts}) ...")
        extended = run_ollama(extend_prompt, language, model, override)
        if not extended.strip():
            break
        text = extended.strip()
        new_count = _count_body_words(text)
        info(f"[{number}] After extension: {new_count} body words")
        if new_count <= current:
            # No growth; stop to avoid an infinite loop.
            break
        current = new_count

    if current < lower:
        info(f"[{number}] WARNING: body at {current} words, still below target {word_target}")
    return text


def _finish_chapter(chapter_dir: Path, out_file: Path, output: str, previous: bytes | None,
                    version_dir: Path, number: int, elapsed: float) -> None:
    """Archive the prior draft, install the new one, and register it for quality."""
    backup = save_chapter(out_file, output, previous, version_dir)
    register_draft(chapter_dir)
    if backup is not None:
        info(f"[{number}] Previous version -> {backup}")
    
    # Word count validation: ensure output is within 75% - 125% of word_target.
    chapter_model = read_chapter_model(chapter_dir)
    target = chapter_model.get("word_target", 0)
    actual = _count_body_words(output)
    vlog(f"[{number}] Output: {len(output)} chars, ~{actual} body words (Target: {target})")
    
    if target > 0:
        lower = target * 0.75
        upper = target * 1.25
        if actual < lower or actual > upper:
            info(f"[{number}] WARNING: Word count {actual} is outside target range [{int(lower)}-{int(upper)}]")
    
    info(f"[{number}] Saved -> {out_file} "
         f"({len(output)} chars in {elapsed:.2f}s)")


def main() -> int:
    global VERBOSE, SHOW_PROMPT
    parser = argparse.ArgumentParser(
        description="Generate pipeline chapters via Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python tools/write.py behula 2          Single chapter
  python tools/write.py behula 2-5        Inclusive range
  python tools/write.py behula 2,5,8      Chapter list
  python tools/write.py behula 2-5,8      Range and list combined
  python tools/write.py behula all        All numbered chapters, in order
  python tools/write.py behula "*"        All chapters (quote the wildcard)
  python tools/write.py behula 2 -v      Verbose logging
  python tools/write.py behula 2 -p      Show prompt, then generate
  python tools/write.py help             Show this help
  python tools/write.py --help           Show this help (also -h)

Input:  workspaces/pipeline/<bookname>/chapters/<n>/model.json
Context: workspaces/pipeline/<bookname>/chapters/<n>/context.md (regenerated from full JSON)
Output: workspaces/pipeline/<bookname>/chapters/<n>/chapter.md
Previous drafts: chapters/<n>/segments/<x>/version/chapter_v<k>.md
Poetry: x=1. Novels: --segment selects an existing segment (1, 2, ...).
Paths are resolved relative to the repository, regardless of your current directory.
""",
    )
    parser.add_argument("bookname", help="Book folder under workspaces/pipeline/.")
    parser.add_argument(
        "chapters",
        help="Chapter number, range, list (2, 2-5, 2-5,8), all, or '*'.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "-p", "--show-prompt",
        action="store_true",
        help="Print the full prompt to stdout before invoking Ollama.",
    )
    if sys.argv[1:] == ["help"]:
        parser.print_help()
        return 0
    parser.add_argument("--segment", type=int, help="For novels, selects all segments (the whole chapter); poetry always uses 1.")
    parser.add_argument(
        "--style",
        metavar="NICKNAME",
        default=None,
        help=(
            "Preset style to write in (a file under .framework/templates/preset/). "
            "If omitted, the book's style.md is used. Default fallback: pijush.md."
        ),
    )
    args = parser.parse_args()
    VERBOSE = args.verbose
    SHOW_PROMPT = args.show_prompt

    vlog(f"BASE_DIR       = {BASE_DIR}")
    vlog(f"POETRY_FILE    = {POETRY_FILE}")
    vlog(f"PRESET_DIR     = {PRESET_DIR}")
    vlog(f"style          = {args.style}")
    vlog(f"MODEL          = {MODEL}")
    vlog(f"Verbose mode   = {VERBOSE}")

    try:
        # Validate an explicit style early (unknown nickname → clear guidance).
        # When omitted, the book's style.md governs; no early resolution needed.
        if args.style:
            resolve_preset(args.style)
        chapters_root = resolve_chapters_root(args.bookname)
        numbers = parse_chapter_input(args.chapters, chapters_root)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    info(f"Processing {args.bookname}: {len(numbers)} chapter(s): {numbers}")
    failures = 0
    for number in numbers:
        model_file = chapter_model_file(chapters_root / str(number))
        try:
            write_chapter(model_file, args.segment, args.style)
        except Exception as e:
            print(f"[{number}] FAILED: {e}", file=sys.stderr)
            failures += 1
    info(f"Done. {len(numbers) - failures} succeeded, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
