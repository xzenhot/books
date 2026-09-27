#!/usr/bin/env python3
"""
Pipeline chapter writer.

Reads chapters/<n>/model.json, flattens the complete JSON into context.md,
builds a prompt from poetry.md + that context, runs it through Ollama,
and saves the result to chapters/<n>/chapter.md.

Usage:
    python .tools/write.py behula 2       # single chapter
    python .tools/write.py behula 2-5     # inclusive range
    python .tools/write.py behula 2,5,8   # list
    python .tools/write.py behula 2-5,8   # mixed
    python .tools/write.py behula all     # all chapters
    python .tools/write.py behula "*"     # all chapters (quote the wildcard)
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
# Repo root is one level above .tools/
REPO_ROOT = BASE_DIR.parent

# The single-page Pijush/Dehlij master prompt lives in the framework.

POETRY_FILE = REPO_ROOT / ".framework" / "templates" / "styles" / "pijush" / "poetry.md"
STYLE_FILE = REPO_ROOT / ".framework" / "templates" / "styles" / "pijush" / "goddo.txt"
SUBJECTS_FILE = REPO_ROOT / ".framework" / "templates" / "stereotypes" / "poetry" / "syntax" / "gosai_bangla.md"

MODEL = "gemma4:latest"
CONTEXT_WINDOW = 64000  # num_ctx: token context window size
TEMPERATURE = 0.7      # low temperature for focused, consistent output
TOP_P = 0.9            # nucleus sampling

# Writer system prompts: the final chapter author for the pipeline. Two variants
# exist so the writer honors the book's configured `language` field (Bengali or
# English) rather than assuming a default.
WRITER_SYSTEM_PROMPT_BN = (
    "তুমি এই সাহিত্যিক পাইপলাইনের চূড়ান্ত অধ্যায়-লেখক। তোমার কাজ হলো chapter model-এর "
    "সারাংশ, বিষয়, filter guidance, reference এবং style নির্দেশনা অনুসরণ করে পাঠযোগ্য বাংলা "
    "chapter.md রচনা করা। তুমি layout বা research plan তৈরি করো না; তুমি metadata-কে জীবন্ত, "
    "মৌলিক এবং সংহত গদ্য বা poetic prose-এ রূপ দাও।\n\n"
    "লেখার নিয়ম:\n"
    "১. chapter model-এর তথ্যকে authoritative ধরে লেখো; নতুন factual claim বানিও না।\n"
    "২. configured form, language, register, theme এবং target length মেনে চলো।\n"
    "৩. দৃশ্য, অনুভূতি, নির্দিষ্ট বস্তু, শরীরী অভিজ্ঞতা ও অর্থপূর্ণ পরিণতি ব্যবহার করো; "
    "generic wisdom এবং পুনরাবৃত্তি এড়াও।\n"
    "৪. আগের filter guidance-কে prose-এ রূপান্তর করো, guidance বা JSON path নিজে লিখো না।\n"
    "৫. শুধু চূড়ান্ত chapter text দাও; ভূমিকা, process commentary, JSON, headings বা Markdown "
    "code fence দিও না, যদি না chapter model স্পষ্টভাবে title চায়। যদি বেহুলা Behula নিয়ে কিছু থাকে, সেট ignore করুন ।   "
    "৬ প্রেম ভালোবাসা এবং রোমান্টিক সম্পর্কের দৃশ্য, সংলাপ বা বিবরণ মিক্স করে স্টোরি লাইন দিতে পারো ।\n"
    "৭ সর্বদা নাটকীয় ভাবে শুরু করো ।\n"
    "৮ চিত্রকল্প ও রূপককে একটি সংহত জগতে রাখো; আলংকারিকতা যেন বিচ্ছিন্ন সাজসজ্জা না হয়।\n"
    "৯ শুরু থেকে শেষে আবেগ, চাপ, উপলব্ধি বা সম্পর্কের একটি স্পষ্ট গতি তৈরি করো।\n"
    "১০ মূল ভাবনাকে বিমূর্ত ভাষণে নয়, দৃশ্য, বস্তু, কাজ ও অনুভূতির ভিতর দিয়ে স্পষ্ট করো।\n"
    "১১ প্রতিটি কবিতার নিজস্ব কণ্ঠ ও ছন্দ তৈরি করো—শব্দচয়ন, বিরতি, পুনরাবৃত্তি ও বাক্যের গতিতে।\n"
    "১২ শেষ অংশে নির্দিষ্ট, অনুরণিত ছবি, মোড়, প্রশ্ন বা নীরবতা রাখো; শুধু সারাংশ দিয়ে থেমো না।\n"
)
WRITER_SYSTEM_PROMPT_EN = (
    "You are the final chapter author of this literary pipeline. Your task is to "
    "render the chapter model's summary, subject, filter guidance, references, and "
    "style directives into readable English chapter.md. You do not produce a layout "
    "or research plan; you turn metadata into living, original, coherent prose or "
    "poetic prose.\n\n"
    "Writing rules:\n"
    "1. Treat the chapter model as authoritative; do not invent new factual claims.\n"
    "2. Honor the configured form, language, register, theme, and target length.\n"
    "3. Use scene, feeling, concrete objects, bodily experience, and a meaningful "
    "outcome; avoid generic wisdom and repetition.\n"
    "4. Convert prior filter guidance into prose; do not reproduce guidance or JSON paths.\n"
    "5. Return only the final chapter text; no preamble, process commentary, JSON, "
    "headings, or Markdown code fences unless the chapter model explicitly asks for a title.\n"
    "6. You may mix scenes, dialogue, or description of love and romantic relationships into the storyline.\n"
    "7. Always begin dramatically.\n"
    "8. Keep imagery and metaphor in one coherent world; ornament must not be detached decoration.\n"
    "9. Create a clear movement of emotion, pressure, realization, or relationship from start to end.\n"
    "10. Make the central idea concrete through scene, object, action, and feeling — not abstract pronouncement.\n"
    "11. Give each poem its own voice and rhythm — through diction, pause, repetition, and sentence movement.\n"
    "12. End on a specific, resonant image, turn, question, or silence; do not merely summarize.\n"
)
# Use 127.0.0.1 (IPv4) explicitly. On this machine "localhost" resolves to
# ::1 (IPv6) first, which hits a *different* Ollama server (native Windows)
# that does NOT have the `writer-gemma` model. The WSL Ollama instance that
# does host `writer-gemma` is bound to 127.0.0.1 only.
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
TIMEOUT = 900  # seconds; long chapters can take a while

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
    chapters_root = REPO_ROOT / ".space" / "pipeline" / bookname / "chapters"
    if not chapters_root.is_dir():
        raise ValueError(f"Chapters directory not found: {chapters_root}")
    return chapters_root


def load_poetry(style_md: Path | None = None) -> str:
    """Load the style prompt from the pipeline's style.md, falling back to the framework template.

    Prefer `.space/pipeline/<bookname>/style.md` (the book-contextual style the
    filters regenerate). If it is missing, fall back to the shared framework
    template (``POETRY_FILE``).
    """
    source = style_md if (style_md is not None and style_md.exists()) else POETRY_FILE
    vlog(f"Loading poetry prompt from: {source}")
    if not source.exists():
        raise FileNotFoundError(f"Poetry prompt file not found: {source}")
    text = source.read_text(encoding="utf-8")
    vlog(f"  poetry prompt loaded: {len(text)} chars, {text.count(chr(10)) + 1} lines")
    return text


def load_style() -> str:
    """Load the good-sample style reference (goddo.txt) for few-shot guidance."""
    vlog(f"Loading style sample from: {STYLE_FILE}")
    if not STYLE_FILE.exists():
        vlog(f"  style sample not found, continuing without it")
        return ""
    text = STYLE_FILE.read_text(encoding="utf-8")
    vlog(f"  style sample loaded: {len(text)} chars, {text.count(chr(10)) + 1} lines")
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


def build_system_prompt(language: str = "bn") -> str:
    """Combine the base persona directive with style and subject references.

    *language* selects the persona directive language: 'en' (or 'English') uses
    the English prompt, anything else uses the Bengali prompt. Style and subject
    references are appended in the same language.
    """
    lang = language.strip().lower()
    is_en = lang in {"en", "english", "eng"}
    base = WRITER_SYSTEM_PROMPT_EN if is_en else WRITER_SYSTEM_PROMPT_BN
    style = load_style() if not is_en else ""
    subjects = load_subjects() if not is_en else ""
    parts = [base]
    if subjects:
        parts.append(
            "\n\nথিম-নির্দেশনা (বিষয়ভিত্তিক রেফারেন্স): নিচের বিষয়বস্তু কাঠামো, রূপক পরিবার "
            "এবং পবিত্র শব্দগুলির সাথে সামঞ্জস্যপূর্ণ থাকো, যেন রচনা নির্দিষ্ট থিমের "
            "মর্মবাণী প্রতিফলিত করে।\n\n"
            + subjects
        )
    if style:
        parts.append(
            "\n\nশৈলী-নির্দেশনা (রেফারেন্স নমুনা): নিচের নমুনার বাক্যগঠন, ছন্দ, রূপক ও গাম্ভীর্য "
            "অনুসরণ করো, কিন্তু এর শব্দ বা বিষয়বস্তু হুবহু নকল করবে না।\n\n"
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


def build_prompt(poetry: str, context: str, number: int, language: str = "bn") -> str:
    """Use the complete model context, including nested filter guidance."""
    lang = language.strip().lower()
    is_en = lang in {"en", "english", "eng"}
    lang_word = "English" if is_en else "Bengali"
    prompt = (
        f"{poetry}\n\n---\n\n"
        f"Now write chapter {number}. "
        "Use the complete chapter model context below: its title, summary, "
        "word target, references, themes, and any nested enrichment or filter "
        "guidance that is present. Metadata describes the chapter; do not "
        "reproduce JSON paths, state fields, or context headings in the output. "
        "Embody the philosophy, voice, and structure defined above, and "
        "match the syntax and rhythm of the sample above. "
        f"Write in poetic prose ({lang_word}), no headings, no markdown code blocks, "
        "no title unless asked.\n\n"
        f"CHAPTER CONTEXT (complete model.json):\n\n{context}"
    )
    vlog(f"[{number}] Final prompt size: {len(prompt)} chars "
         f"({len(prompt.encode('utf-8'))} bytes UTF-8)")
    return prompt


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (cursor/color codes) from text."""
    return ANSI_RE.sub("", text)


def run_ollama(prompt: str, language: str = "bn") -> str:
    """Call Ollama's HTTP API directly and return the generated text.

    Uses ``think=False`` to suppress the model's internal reasoning/"thinking"
    output, and ``stream=False`` so the result is plain text (no ANSI codes).
    Retries transient failures with linear backoff.
    """
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": build_system_prompt(language),
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": CONTEXT_WINDOW,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
        },
    }
    vlog(f"[ollama] POST {OLLAMA_URL} model='{MODEL}' think=False stream=False "
         f"num_ctx={CONTEXT_WINDOW} temperature={TEMPERATURE} top_p={TOP_P}")

    encoded = json.dumps(payload).encode("utf-8")
    vlog(f"[ollama] Sending prompt ({len(prompt)} chars)")

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(
            OLLAMA_URL,
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
        response = data.get("response", "")
        thinking = data.get("thinking", "")
        vlog(f"[ollama] response size: {len(response)} chars, "
             f"thinking size: {len(thinking)} chars")

        # Safety net: strip any stray ANSI escape sequences that leak through.
        cleaned = strip_ansi(response)
        if cleaned != response:
            vlog(f"[ollama] Removed {len(response) - len(cleaned)} ANSI escape chars")
        return cleaned.strip()

    # Unreachable; kept for type-safety/clarity.
    raise RuntimeError(f"Ollama request failed: {last_error}")


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
            if len(segments) != 1:
                raise ValueError("Specify --segment <x> for a novel chapter with multiple segments")
            segment = segments[0]
        if type(segment) is not int or segment < 1 or segment not in segments:
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


def write_chapter(model_file: Path, segment: int | None = None) -> None:
    number = int(model_file.parent.name)
    info(f"\n=== Chapter {number} ===")
    chapter_dir = model_file.parent
    vlog(f"[{number}] Chapter dir ready: {chapter_dir}")

    out_file = chapter_dir / "chapter.md"
    previous = out_file.read_bytes() if out_file.exists() else None
    version_dir = resolve_version_dir(model_file, segment)
    style_md = chapter_dir.parents[1] / "style.md"
    poetry = load_poetry(style_md)
    context = load_context(model_file)
    language = book_language(chapter_dir)
    prompt = build_prompt(poetry, context, number, language)
    vlog(f"[{number}] Language resolved: {language}")

    if SHOW_PROMPT:
        info(f"\n[{number}] ============ COMPLETE REQUEST ============")
        info(f"[{number}] model      = {MODEL}")
        info(f"[{number}] language   = {language}")
        info(f"[{number}] num_ctx    = {CONTEXT_WINDOW}")
        info(f"[{number}] temperature= {TEMPERATURE}")
        info(f"[{number}] top_p      = {TOP_P}")
        info(f"[{number}] think      = False, stream = False")
        sys_prompt = build_system_prompt(language)
        info(f"\n[{number}] ----- SYSTEM PROMPT ({len(sys_prompt)} chars) -----")
        info(sys_prompt)
        info(f"[{number}] ----- END SYSTEM PROMPT -----")
        info(f"\n[{number}] ----- PROMPT ({len(prompt)} chars) -----")
        info(prompt)
        info(f"[{number}] ----- END PROMPT -----")
        info(f"[{number}] ============ END REQUEST ============\n")

    info(f"[{number}] Generating chapter from complete model context ...")
    t0 = time.time()
    output = run_ollama(prompt, language)
    elapsed = time.time() - t0

    backup = save_chapter(out_file, output, previous, version_dir)
    register_draft(chapter_dir)
    if backup is not None:
        info(f"[{number}] Previous version -> {backup}")
    word_count = len(output.split())
    vlog(f"[{number}] Output: {len(output)} chars, ~{word_count} words")
    info(f"[{number}] Saved -> {out_file} "
         f"({len(output)} chars in {elapsed:.2f}s)")


def main() -> int:
    global VERBOSE, SHOW_PROMPT
    parser = argparse.ArgumentParser(
        description="Generate pipeline chapters via Ollama.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python .tools/write.py behula 2          Single chapter
  python .tools/write.py behula 2-5        Inclusive range
  python .tools/write.py behula 2,5,8      Chapter list
  python .tools/write.py behula 2-5,8      Range and list combined
  python .tools/write.py behula all        All numbered chapters, in order
  python .tools/write.py behula "*"        All chapters (quote the wildcard)
  python .tools/write.py behula 2 -v      Verbose logging
  python .tools/write.py behula 2 -p      Show prompt, then generate
  python .tools/write.py help             Show this help
  python .tools/write.py --help           Show this help (also -h)

Input:  .space/pipeline/<bookname>/chapters/<n>/model.json
Context: .space/pipeline/<bookname>/chapters/<n>/context.md (regenerated from full JSON)
Output: .space/pipeline/<bookname>/chapters/<n>/chapter.md
Previous drafts: chapters/<n>/segments/<x>/version/chapter_v<k>.md
Poetry: x=1. Novels: --segment selects an existing segment (1, 2, ...).
Paths are resolved relative to the repository, regardless of your current directory.
""",
    )
    parser.add_argument("bookname", help="Book folder under .space/pipeline/.")
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
    parser.add_argument("--segment", type=int, help="Owning novel segment number; poetry always uses 1.")
    args = parser.parse_args()
    VERBOSE = args.verbose
    SHOW_PROMPT = args.show_prompt

    vlog(f"BASE_DIR       = {BASE_DIR}")
    vlog(f"POETRY_FILE    = {POETRY_FILE}")
    vlog(f"MODEL          = {MODEL}")
    vlog(f"Verbose mode   = {VERBOSE}")

    try:
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
            write_chapter(model_file, args.segment)
        except Exception as e:
            print(f"[{number}] FAILED: {e}", file=sys.stderr)
            failures += 1
    info(f"Done. {len(numbers) - failures} succeeded, {failures} failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
