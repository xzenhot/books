#!/usr/bin/env python3
"""Syntax filter runner.

Applies the syntax filter to a poetry/novel pipeline: selects the chapter's
syntax sample from the form's stereotype templates and records a `syntax`
object (form + sample + modernization directives) into each target chapter's
model.json, updating `state` and `filter_history`. Creates the lazy
`filters/syntax/` folder on first run.

Usage:
    python .tools/syntax_filter.py <bookname> [all|1|1-5|continue]
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent
SYNTAX_POETRY = REPO_ROOT / ".framework" / "templates" / "stereotypes" / "poetry" / "syntax"
SYNTAX_NOVEL = REPO_ROOT / ".framework" / "templates" / "stereotypes" / "novel" / "syntax"

# Default syntax sample per form (matches the pipeline's configured voice).
DEFAULT_SAMPLE_POETRY = "gosai_bangla.md"
DEFAULT_SAMPLE_NOVEL = "generic.md"


def resolve_chapters_root(bookname: str) -> Path:
    chapters_root = REPO_ROOT / ".space" / "pipeline" / bookname / "chapters"
    if not chapters_root.is_dir():
        raise ValueError(f"Chapters directory not found: {chapters_root}")
    return chapters_root


def parse_chapter_input(value: str, chapters_root: Path) -> list[int]:
    if value.strip().lower() in {"all", "*"}:
        return sorted(
            int(f.name)
            for f in chapters_root.iterdir()
            if f.is_dir() and re.fullmatch(r"[0-9]+", f.name) and int(f.name) > 0
        )
    numbers = []
    for token in value.split(","):
        m = re.fullmatch(r"([0-9]+)(?:-([0-9]+))?", token.strip())
        if m is None:
            raise ValueError("Expected all, '*', or chapter numbers, e.g. 1, 1-5, 1-5,8")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        numbers.extend(range(start, end + 1))
    return list(dict.fromkeys(numbers))


def load_book_form(bookname: str) -> str:
    pipeline = REPO_ROOT / ".space" / "pipeline" / bookname
    model = pipeline / "book.json"
    if not model.exists():
        model = pipeline / "model.json"
    data = json.loads(model.read_text(encoding="utf-8-sig"))
    form = data.get("form", "poetry")
    if form not in {"poetry", "novel"}:
        raise ValueError(f"Book model form is {form!r}; expected poetry or novel.")
    return form


def syntax_object(form: str) -> dict:
    sample = DEFAULT_SAMPLE_POETRY if form == "poetry" else DEFAULT_SAMPLE_NOVEL
    return {
        "form": form,
        "sample": sample,
        "register": "archaic/literary — songlike, incantatory cadence",
        "directives": [
            "Keep the elevated Bengali voice and sacred cadence; modernize only the sentence structure.",
            "Prefer long, flowing sentences that unfold through clauses, images, and emotional turns.",
            "Remove dead constructions and obsolete grammar; the poem must read naturally aloud.",
            "Use repetition and refrain to carry the movement, matching the Baul-Fakir cadence.",
        ],
    }


def chapter_file(chapter_dir: Path) -> Path:
    """Resolve a chapter's metadata file, preferring `chapter.json` over `model.json`."""
    for name in ("chapter.json", "model.json"):
        candidate = chapter_dir / name
        if candidate.exists():
            return candidate
    return chapter_dir / "chapter.json"


def snapshot_model(model_file: Path) -> None:
    history = model_file.parent / "history"
    history.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = history / f"model_syntax_{stamp}.json"
    target.write_bytes(model_file.read_bytes())
    print(f"  snapshot -> {target.name}")


def apply_syntax(model_file: Path, form: str) -> None:
    data = json.loads(model_file.read_text(encoding="utf-8-sig"))
    if data.get("syntax") == syntax_object(form):
        print(f"  [{model_file.parent.name}] unchanged (syntax already recorded)")
        return
    snapshot_model(model_file)
    data["syntax"] = syntax_object(form)
    data["state"] = "syntax"
    history = data.setdefault("filter_history", [])
    if not isinstance(history, list):
        history = [history]
    history.append({"filter": "syntax", "ran_at": datetime.now(timezone.utc).isoformat()})
    data["filter_history"] = history
    model_file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  [{model_file.parent.name}] syntax recorded (sample={data['syntax']['sample']})")


def write_filter_outputs(bookname: str, form: str, numbers: list[int]) -> None:
    filters_dir = REPO_ROOT / ".space" / "pipeline" / bookname / "filters" / "syntax"
    filters_dir.mkdir(parents=True, exist_ok=True)
    records = [
        {"chapter_index": n, "form": form, "sample": syntax_object(form)["sample"]}
        for n in numbers
    ]
    (filters_dir / "syntax.json").write_text(
        json.dumps({"filter": "syntax", "form": form, "chapters": records},
                   indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (filters_dir / "filter-summary.md").write_text(
        f"# syntax filter\n\nBook: {bookname} ({form}). Chapters processed: {len(numbers)}.\n"
        f"Syntax sample: {syntax_object(form)['sample']}.\n",
        encoding="utf-8",
    )
    lines = [f"# Syntax Filter - Content Output", "",
             f"Book: {bookname} ({form}). Scope: chapters {numbers[0]}-{numbers[-1]}.",
             "", "| # | Chapter |", "|---|---------|"]
    for n in numbers:
        chapter_dir = REPO_ROOT / ".space" / "pipeline" / bookname / "chapters" / str(n)
        title = ""
        if chapter_dir.is_dir():
            m = json.loads(chapter_file(chapter_dir).read_text(encoding="utf-8-sig"))
            title = m.get("chapter_title", "")
        lines.append(f"| {n} | {title} |")
    (filters_dir / "content-output.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote filters/syntax/ (syntax.json, filter-summary.md, content-output.md)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply the syntax filter to a pipeline.")
    parser.add_argument("bookname")
    parser.add_argument("target", nargs="?", default="all")
    args = parser.parse_args()

    form = load_book_form(args.bookname)
    chapters_root = resolve_chapters_root(args.bookname)
    numbers = parse_chapter_input(args.target, chapters_root)

    print(f"Syntax filter: {args.bookname} ({form}), chapters {numbers[0]}-{numbers[-1]}")
    for n in numbers:
        apply_syntax(chapter_file(chapters_root / str(n)), form)
    write_filter_outputs(args.bookname, form, numbers)
    print(f"Syntax complete. {len(numbers)} chapter(s) processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
