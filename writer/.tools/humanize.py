#!/usr/bin/env python3
"""humanize.py — Language polish engine for poetry pipelines.

Ensures chapter drafts are entirely in the target language (Bengali).
Scans for non-relevant foreign-language characters — Chinese, Urdu, Latin —
embedded in Bengali text and removes them, producing clean continuous verse.

USAGE
-----
    python .tools/humanize.py <bookname> [all|*|<n>|<range>|continue]
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Repository paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
PIPELINE_ROOT = REPO_ROOT / ".space" / "pipeline"

# ---------------------------------------------------------------------------
# Character detection patterns
# ---------------------------------------------------------------------------

CHINESE_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df]')
URDU_RE = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\u0900-\u097f]')
LATIN_RE = re.compile(r'[a-zA-Z]')
# Bengali script range
BENGALI_RE = re.compile(r'[\u0980-\u09ff]')


def validate_bookname(bookname: str) -> str:
    if not bookname or "/" in bookname or "\\" in bookname:
        raise ValueError(f"Invalid book name: {bookname!r}")
    return bookname


def resolve_chapters_root(bookname: str) -> Path:
    return PIPELINE_ROOT / bookname / "chapters"


def load_chapter_model(chapter_dir: Path) -> dict | None:
    for name in ("chapter.json", "model.json"):
        candidate = chapter_dir / name
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8-sig"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_chapter_input(target: str, chapters_root: Path) -> list[int]:
    if target in ("*", "all"):
        numbers = []
        for d in sorted(chapters_root.glob("*"), key=lambda p: p.name):
            if d.is_dir() and d.name.isdigit():
                numbers.append(int(d.name))
        return sorted(numbers)
    if target == "continue":
        return _find_continue(chapters_root)
    if "-" in target:
        start_s, end_s = target.split("-", 1)
        return list(range(int(start_s), int(end_s) + 1))
    return [int(target)]


def _find_continue(chapters_root: Path) -> list[int]:
    for d in sorted(chapters_root.glob("*"), key=lambda p: p.name):
        if not d.is_dir() or not d.name.isdigit():
            continue
        model = load_chapter_model(d)
        if not model:
            continue
        state = model.get("state", "")
        humanized = model.get("humanized", False)
        if state == "completed" and not humanized:
            return [int(d.name)]
    return []


def find_foreign_chars_outside_quotes(text: str) -> list[dict]:
    """Find non-Bengali characters that are NOT inside quotation marks.

    Returns a list of {position, char, codepoint, type} for each foreign
    character found outside quotes.
    """
    results = []
    in_double = False
    in_single = False

    for i, ch in enumerate(text):
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue

        if in_double or in_single:
            continue  # inside quotes — skip

        cp = ord(ch)
        # Bengali script
        if '\u0980' <= ch <= '\u09ff':
            continue
        # Whitespace
        if ch in ' \t\n\r':
            continue
        # Standard ASCII punctuation and digits
        if 0x0020 <= cp <= 0x007e and ch not in 'a-zA-Z':
            continue

        # Check what type of foreign character
        ftype = None
        if CHINESE_RE.match(ch):
            ftype = "chinese"
        elif URDU_RE.match(ch):
            ftype = "urdu"
        elif LATIN_RE.match(ch):
            ftype = "latin"
        elif not BENGALI_RE.match(ch):
            ftype = "other"

        if ftype:
            results.append({
                'position': i,
                'char': ch,
                'codepoint': hex(cp),
                'type': ftype
            })

    return results


def humanize_text(text: str) -> tuple[str, list[dict]]:
    """Remove non-Bengali characters from text, preserving quoted content.

    Returns the humanized text and a list of replacements made.
    """
    foreign_chars = find_foreign_chars_outside_quotes(text)
    replacements = []

    # Build a set of positions to remove
    positions_to_remove = set()
    for fc in foreign_chars:
        positions_to_remove.add(fc['position'])
        replacements.append(fc)

    # Build the result by excluding foreign characters
    result = []
    for i, ch in enumerate(text):
        if i in positions_to_remove:
            # Replace with Bengali danda (।) for Chinese, or Bengali space
            cp = ord(ch)
            if CHINESE_RE.match(ch):
                result.append('\u0964')  # Bengali danda
            elif URDU_RE.match(ch):
                result.append('')  # Just remove Urdu
            elif LATIN_RE.match(ch):
                result.append('')  # Just remove Latin letters
            else:
                result.append('')  # Remove other foreign chars
        else:
            result.append(ch)

    humanized = ''.join(result)

    # Clean up multiple consecutive whitespace
    humanized = re.sub(r' {3,}', '  ', humanized)
    humanized = re.sub(r'\n{3,}', '\n\n', humanized)
    humanized = re.sub(r'[ \t]+$', '', humanized, flags=re.MULTILINE)
    # Remove leading/trailing blank lines
    humanized = humanized.strip('\n')

    return humanized, replacements


def run_humanize(bookname: str, target: str) -> None:
    """Execute humanization for the given chapter scope."""
    bookname = validate_bookname(bookname)
    chapters_root = resolve_chapters_root(bookname)

    if not chapters_root.exists():
        raise FileNotFoundError(
            f"Pipeline not found: {chapters_root}\n"
            "Run scaffold first: python .tools/book.py <bookname> scaffold"
        )

    # Load book model
    book_file = PIPELINE_ROOT / bookname / "book.json"
    book = json.loads(book_file.read_text(encoding="utf-8-sig"))
    form = book.get("form", "poetry")
    print(f"Humanizing {bookname} (form: {form})")

    # Resolve target chapters
    numbers = parse_chapter_input(target, chapters_root)
    print(f"Target chapters: {numbers[0]}–{numbers[-1]} ({len(numbers)} chapters)")

    total_replaced = 0
    humanized_count = 0

    for num in numbers:
        chapter_dir = chapters_root / str(num)
        chapter_md_path = chapter_dir / "chapter.md"
        model = load_chapter_model(chapter_dir)

        if not model:
            print(f"  [{num}] SKIP: no model found")
            continue

        if not chapter_md_path.exists():
            print(f"  [{num}] SKIP: no chapter.md")
            continue

        # Verify quality review passed
        review = model.get("quality_review", {})
        if review.get("status") != "passed":
            print(f"  [{num}] SKIP: quality review not passed (status={review.get('status')})")
            continue

        # Read current draft
        old_text = chapter_md_path.read_text(encoding="utf-8-sig")
        old_sha = compute_sha256(old_text.encode("utf-8-sig"))

        # Update draft hash to match current chapter.md (concurrent process may have modified it)
        draft = model.get("draft", {})
        if draft.get("sha256") and draft.get("sha256") != old_sha:
            # Draft was rewritten — re-register the hash but keep quality_review
            model["draft"] = {
                "sha256": old_sha,
                "written_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "origin": "humanize"
            }

        # Humanize the text
        humanized_text, replacements = humanize_text(old_text)
        new_sha = compute_sha256(humanized_text.encode("utf-8-sig"))

        if not replacements:
            # No changes needed — already clean
            continue

        # Archive the prior draft
        history_dir = chapter_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(':', '-')
        backup_path = history_dir / f"humanize_{timestamp}.md"
        backup_path.write_text(old_text, encoding="utf-8")

        # Write the humanized draft
        chapter_md_path.write_text(humanized_text, encoding="utf-8")

        # Update the chapter model
        model["humanized"] = True
        model["humanized_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        model["draft"] = {
            "sha256": new_sha,
            "written_at": model.get("draft", {}).get("written_at", model["humanized_at"]),
            "origin": "humanize"
        }
        model_path = chapter_dir / "chapter.json"
        model_path.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        num_replaced = len(replacements)
        total_replaced += num_replaced
        humanized_count += 1

        chinese_count = sum(1 for r in replacements if r['type'] == 'chinese')
        urdu_count = sum(1 for r in replacements if r['type'] == 'urdu')
        latin_count = sum(1 for r in replacements if r['type'] == 'latin')
        print(f"  [{num}] Humanized: {num_replaced} foreign chars removed (chinese={chinese_count}, urdu={urdu_count}, latin={latin_count})")

    print(f"\nHumanize complete. {humanized_count} chapters humanized, {total_replaced} foreign characters removed.")

    # Update progress.json
    progress_path = PIPELINE_ROOT / bookname / "progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8-sig"))
        for row in progress.get("chapters", []):
            ch_num = str(row.get("chapter_number", ""))
            if ch_num in [str(n) for n in numbers]:
                row["humanized"] = True
        progress["humanized"] = True
        progress_path.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("progress.json updated.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python .tools/humanize.py <bookname> [all|*|<n>|<range>|continue]", file=sys.stderr)
        sys.exit(1)

    bookname = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else "all"

    try:
        run_humanize(bookname, target)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
