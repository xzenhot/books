#!/usr/bin/env python3
"""layout.py — Scaffold a novel pipeline from the canonical v1 segment-based template.

Python equivalent of ``layout.ps1``. Use this when PowerShell is not available.

Usage:
    python layout.py <bookname> [--chapter-count N] [--gist "one-line premise"]

Produces:
    .space/pipeline/book_<name>/   (folder tree + state files + planning artifacts)
    source/books/book_<name>/      (empty destination for finished chapters)

The layout is static and deterministic: book -> chapters/<n> -> segments/<x>
-> writer/editor/translator. Planning artifacts (book.json, characters.json,
masterprompt.md, workshop_metadata.md) are seeded with placeholders that the
writing agents fill in later.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# --- Resolve paths relative to this script ---------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent          # .framework/scripts/
FRAMEWORK = SCRIPT_DIR.parent                          # .framework/
REPO_ROOT = FRAMEWORK.parent                           # novelist/
TEMPLATE = FRAMEWORK / "templates" / "novel"
PIPELINE_DIR = REPO_ROOT / ".space" / "pipeline"
SOURCE_DIR = REPO_ROOT / "source" / "books"

# The ordered, prefixed pipeline filters. Each filter owns a folder under
# filters/ and is recorded in book.json's "filters" array.
FILTERS = [
    ("1_workshop", "workshop", "Per-chapter workshop narratives — the flat, continuous prose that becomes the chapter."),
    ("2_research", "research", "Per-chapter research — the subject, era, place, figures, and events the chapter is grounded in."),
    ("3_seeds", "seeds", "Per-chapter character and quality seeds — who appears and what quality bar to meet."),
    ("4_correctness", "correctness", "Fact-checking — verify every fact, term, and claim."),
    ("5_theme", "theme", "Contemporary theme — map the timeless theme onto a present-day concern."),
    ("6_syntax", "syntax", "Contemporary syntax — keep the prophetic voice but modernize the sentence structure."),
    ("7_override", "override", "Human-in-the-loop — the human's override.md transformation."),
    ("8_quality", "quality", "Quality review — audit against the seed analysis's quality metrics."),
]


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def new_state_files(path: Path, data: dict) -> None:
    """Create the level state file at a given level."""
    path.mkdir(parents=True, exist_ok=True)
    level = data.get("level")
    extra = {k: v for k, v in data.items() if k != "level"}

    returning = {"level": level, "state": "returning", **extra}

    write_json(path / "model.json", returning)


def copy_template_dir(src: Path, dst: Path) -> None:
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            target = dst / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)


def scaffold(book_name: str, chapter_count: int, gist: str) -> None:
    book_dir = PIPELINE_DIR / f"book_{book_name}"
    out_dir = SOURCE_DIR / f"book_{book_name}"

    # --- Guards -------------------------------------------------------------
    if not TEMPLATE.is_dir():
        raise FileNotFoundError(f"Canonical template not found: {TEMPLATE}")
    if book_dir.exists():
        print(f"WARNING: Pipeline already exists: {book_dir} "
              f"(skipping folder creation; state files will be repaired)")

    now = datetime.now().strftime("%Y-%m-%d")

    # --- 1. Book root -------------------------------------------------------
    book_dir.mkdir(parents=True, exist_ok=True)

    # Book-level state files
    new_state_files(book_dir, {
        "level": "book",
        "book_name": book_name,
        "chapter_count": chapter_count,
    })

    # --- 2. Root planning artifacts ----------------------------------------
    chapters = [
        {
            "chapter_index": i,
            "name": f"Chapter {i}",
            "chapter_title": f"Chapter {i} title",
            "chapter_summary": f"Summary of chapter {i}.",
        }
        for i in range(1, chapter_count + 1)
    ]

    book_json = {
        "book_name": book_name,
        "book_long_title": "Provide a long title",
        "generic": "Historical Epic",
        "era": "TBD",
        "language": "en",
        "target_audience": "general public",
        "chapter_count": chapter_count,
        "created_at": now,
        "user_name": "novelist",
        "book_summary": gist if gist else "Provide a one-line summary of the book.",
        "gist": gist if gist else "Provide a one-line summary of the book.",
        "epic_path": f".space/backlog/epic/{book_name}/epic.md",
        "filters": [
            {"order": i + 1, "name": name, "folder": f"filters/{folder}/", "purpose": purpose}
            for i, (folder, name, purpose) in enumerate(FILTERS)
        ],
        "chapters": chapters,
        "all_characters": [],
        "history": [
            {
                "timestamp": f"{now}T00:00:00Z",
                "action": "Initial scaffold created",
                "details": f"Book pipeline structure established with {chapter_count} chapters",
            }
        ],
    }
    write_json(book_dir / "book.json", book_json)

    characters_json = {
        "version": "1.0",
        "created_at": now,
        "book_name": book_name,
        "characters": [],
        "character_groups": [],
        "notes": f"Character roster for '{book_name}'.",
    }
    write_json(book_dir / "characters.json", characters_json)

    premise = gist if gist else "Provide the central premise of the book."
    masterprompt = f"""# Master Prompt — {book_name}

## Identity
You are a master novelist writing a frame-story novel. The book interleaves a
**modern frame** (a workshop) with a **historical narrative**.

## Central Premise
{premise}

## Frame
A modern workshop where characters gather to hear a story.

## Style Mandate
- Serious, descriptive, image-rich literary register.
- Weave the book's subject matter into every chapter.
- Highlight the protagonist's conflict and victory.
- Preserve the contrast between the modern frame and the historical setting.
- End each chapter with a narrative handoff that sustains curiosity.

## Section Structure
1. **Section 1 — Workshop:** the modern frame scene (kept unchanged).
2. **Section 2 — Story:** the narrated historical narrative (rewritten in the selected style).
3. **Section 3 — Discussion:** the characters' response (kept unchanged).
"""
    write_text(book_dir / "masterprompt.md", masterprompt)

    workshop_meta = f"""# Workshop Metadata — {book_name}

## Workshop Team
| Role | Character | Description |
|------|-----------|-------------|
| Narrator | TBD | Guides the workshop through the story |
| Participant | TBD | A modern participant questioning the story |

## Schedule
| Chapter | Title | Focus |
|---------|-------|-------|
"""
    for i in range(1, chapter_count + 1):
        workshop_meta += f"| {i} | Chapter {i} | TBD |\n"
    workshop_meta += """
## Grounding Notes
- Ground the narrative in accurate detail.
- Weave the book's subject matter into the story.
"""
    write_text(book_dir / "workshop_metadata.md", workshop_meta)

    # Filter folders (one per pipeline filter, ordered and prefixed)
    for folder, _name, _purpose in FILTERS:
        (book_dir / "filters" / folder).mkdir(parents=True, exist_ok=True)

    # --- 3. Chapters and segments ------------------------------------------
    template_moods = TEMPLATE / "moods"
    # Select one mood to copy as each chapter's mood.json (default: default.json)
    selected_mood = template_moods / "default.json"
    if not selected_mood.is_file():
        selected_mood = next(template_moods.glob("*.json"), None)

    for i in range(1, chapter_count + 1):
        chapter_dir = book_dir / "chapters" / str(i)
        chapter_dir.mkdir(parents=True, exist_ok=True)

        # Copy a single selected mood as mood.json (not the whole moods/ folder)
        if selected_mood is not None and selected_mood.is_file():
            shutil.copy2(selected_mood, chapter_dir / "mood.json")

        # Chapter-level state files
        new_state_files(chapter_dir, {"level": "chapter", "chapter_index": i})

        # Segment 1 (canonical single segment)
        segment_dir = chapter_dir / "segments" / "1"
        segment_dir.mkdir(parents=True, exist_ok=True)

        # writer/editor/translator agent folders
        for agent in ("writer", "editor", "translator"):
            (segment_dir / agent).mkdir(parents=True, exist_ok=True)

        # Segment-level state files
        new_state_files(segment_dir, {
            "level": "segment",
            "chapter_index": i,
            "segment_index": 1,
        })

    # --- 4. Output destination ---------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- 5. Report ----------------------------------------------------------
    print()
    print(f"Scaffolded book pipeline: {book_dir}")
    print(f"  chapters: 1..{chapter_count} (each with segments/1 -> writer/editor/translator)")
    print("  planning: book.json, characters.json, masterprompt.md, workshop_metadata.md")
    print("  filters:  1_workshop, 2_research, 3_seeds, 4_correctness, 5_theme, 6_syntax, 7_override, 8_quality")
    print(f"  output:   {out_dir}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a novel pipeline from the canonical v1 segment-based template."
    )
    parser.add_argument("bookname", help="The book's name; pipeline is .space/pipeline/book_<name>/")
    parser.add_argument("--chapter-count", type=int, default=5,
                        help="Number of chapters (default: 5)")
    parser.add_argument("--gist", default="",
                        help="Optional one-line premise of the book")
    args = parser.parse_args(argv)

    try:
        scaffold(args.bookname, args.chapter_count, args.gist)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
