#!/usr/bin/env python3
"""Flatten a chapter model.json into a readable context.md.

Renders the JSON as a clean Markdown document: object keys become headings,
scalar values become inline text, lists of strings become bullet lists, and
lists of objects become one sub-section each. The result is meant to be read by
a writer (or a human), not to reproduce the raw JSON tree. context.md is written
beside the model.json.

Usage:
    python tools/flatten.py ma 1
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _scalar(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_json_to_markdown(data: object, title: str = "Chapter model context") -> str:
    """Render a JSON object as clean, human-readable Markdown.

    - Object keys become headings (one level deeper per nesting).
    - Scalar values become a plain line under their heading.
    - A list of strings/numbers becomes a bullet list.
    - A list of objects becomes one "Item N" sub-section per entry.

    ``title`` sets the H1 heading; callers rendering non-chapter JSON may pass
    their own title.
    """
    lines: list[str] = []

    def render(value, depth: int) -> None:
        if isinstance(value, dict):
            if not value:
                return
            for key, child in value.items():
                if isinstance(child, (dict, list)) and child:
                    lines.append(f"{'#' * depth} {key}")
                    lines.append("")
                    render(child, depth + 1)
                else:
                    lines.append(f"{'#' * depth} {key}")
                    lines.append("")
                    if child not in (None, "", [], {}):
                        lines.append(_scalar(child))
                    lines.append("")
        elif isinstance(value, list):
            if not value:
                return
            if all(isinstance(i, dict) for i in value):
                for i, item in enumerate(value, 1):
                    lines.append(f"{'#' * depth} Item {i}")
                    lines.append("")
                    render(item, depth + 1)
            else:
                for item in value:
                    if isinstance(item, (dict, list)) and item:
                        render(item, depth)
                    else:
                        lines.append(f"- {_scalar(item)}")
                lines.append("")
        else:
            lines.append(_scalar(value))
            lines.append("")

    lines.append(f"# {title}")
    lines.append("")
    render(data, 2)
    # Trim trailing blank lines.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def flatten_chapter(model_file: Path) -> Path:
    """Flatten one chapter model.json into its sibling context.md."""
    data = json.loads(model_file.read_text(encoding="utf-8-sig"))
    context = flatten_json_to_markdown(data)
    context_file = model_file.with_name("context.md")
    context_file.write_text(context, encoding="utf-8")
    return context_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Flatten a chapter model.json into a readable context.md."
    )
    parser.add_argument("bookname", help="Book folder under workspaces/pipeline/.")
    parser.add_argument("chapter", help="Chapter number (e.g. 1).")
    args = parser.parse_args()

    chapter_dir = (
        REPO_ROOT / "workspaces" / "pipeline" / args.bookname
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
