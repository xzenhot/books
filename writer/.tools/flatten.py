#!/usr/bin/env python3
"""Flatten a chapter model.json into context.md.

Renders every JSON leaf with its unambiguous JSON path as a heading so the
downstream writer prompt can cite exact provenance. context.md is written
beside the model.json.

Usage:
    python .tools/flatten.py ma 1
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def flatten_json_to_markdown(data: object) -> str:
    """Render every JSON leaf with its unambiguous JSON path as a heading."""
    sections = ["# Chapter model context"]

    def visit(value: object, path: str) -> None:
        if isinstance(value, dict) and value:
            for key, child in value.items():
                visit(child, f"{path}[{json.dumps(key, ensure_ascii=False)}]")
        elif isinstance(value, list) and value:
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        else:
            rendered = json.dumps(value, ensure_ascii=False, indent=2)
            fence = "`" * max(3, 1 + max(
                (len(run) for run in re.findall(r"`+", rendered)), default=0
            ))
            sections.append(f"## {path}\n\n{fence}json\n{rendered}\n{fence}")

    visit(data, "$")
    return "\n\n".join(sections) + "\n"


def flatten_chapter(model_file: Path) -> Path:
    """Flatten one chapter model.json into its sibling context.md."""
    data = json.loads(model_file.read_text(encoding="utf-8-sig"))
    context = flatten_json_to_markdown(data)
    context_file = model_file.with_name("context.md")
    context_file.write_text(context, encoding="utf-8")
    return context_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flatten a chapter model.json into context.md."
    )
    parser.add_argument("bookname", help="Book folder under .space/pipeline/.")
    parser.add_argument("chapter", help="Chapter number (e.g. 1).")
    args = parser.parse_args()

    chapter_dir = (
        REPO_ROOT / ".space" / "pipeline" / args.bookname
        / "chapters" / args.chapter
    )
    model_file = chapter_dir / "chapter.json"
    if not model_file.is_file():
        model_file = chapter_dir / "model.json"
    if not model_file.is_file():
        print(f"Model not found: {chapter_dir}", file=sys.stderr)
        return 1

    context_file = flatten_chapter(model_file)
    print(f"Flattened -> {context_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
