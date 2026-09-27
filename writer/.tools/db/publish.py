#!/usr/bin/env python3
"""
Reusable publish tool.

Promotes the latest writer-stage (or translator-stage) segments from the
pipeline to a new versioned folder under `source/books/<bookname>/` and
assembles the consolidated `book.md`.

Usage:
    python .tools/publish.py <bookname> [<language>]

- Without <language>: publishes writer-stage segments (latest chapter_v*.md).
- With <language>: publishes translator-stage segments matching that language.
"""
import datetime
import json
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def publish(bookname: str, language: str | None = None) -> None:
    BOOK = bookname
    PIPE = os.path.join(ROOT, ".space", "pipeline", BOOK)
    SRC = os.path.join(ROOT, "source", "books", BOOK)

    if not os.path.isdir(PIPE):
        sys.exit(f"ERROR: pipeline missing for '{BOOK}'. Run scaffold first.")

    os.makedirs(SRC, exist_ok=True)

    # version allocation
    existing = [d for d in os.listdir(SRC) if d.startswith("version") and os.path.isdir(os.path.join(SRC, d))]
    nums = [int(d.replace("version", "")) for d in existing if d.replace("version", "").isdigit()]
    k = max(nums) + 1 if nums else 1
    ver = f"version{k}"
    ver_dir = os.path.join(SRC, ver)
    chapters_out = os.path.join(ver_dir, "chapters")
    os.makedirs(chapters_out, exist_ok=True)

    # canonical order
    with open(os.path.join(PIPE, "bookseed.txt"), encoding="utf-8") as f:
        topics = [l.strip() for l in f if l.strip()]
    total = len(topics)

    def version_key(fname):
        if fname.startswith("chapter_v") and fname[len("chapter_v"):-3].isdigit():
            return int(fname[len("chapter_v"):-3])
        return 0

    published = []  # list of (n, out_chapter_path)
    skipped = []
    for n in range(1, total + 1):
        if language:
            seg_dir = os.path.join(PIPE, "chapters", str(n), "segments", "1", "translator")
            if not os.path.isdir(seg_dir):
                skipped.append((n, f"no translator segment for '{language}'"))
                continue
            candidates = [f for f in os.listdir(seg_dir) if f.lower().startswith(language.lower()) and f.endswith(".md")]
            if not candidates:
                skipped.append((n, f"no translator segment for '{language}'"))
                continue
            src_file = os.path.join(seg_dir, candidates[0])
            out_dir = os.path.join(chapters_out, str(n), language)
        else:
            seg_dir = os.path.join(PIPE, "chapters", str(n), "segments", "1", "writer")
            if not os.path.isdir(seg_dir):
                skipped.append((n, "no writer segment"))
                continue
            files = [f for f in os.listdir(seg_dir) if f.endswith(".md")]
            if not files:
                skipped.append((n, "no writer segment"))
                continue
            files.sort(key=version_key)
            src_file = os.path.join(seg_dir, files[-1])
            out_dir = os.path.join(chapters_out, str(n))

        os.makedirs(out_dir, exist_ok=True)
        out_chapter = os.path.join(out_dir, "chapter.md")
        shutil.copyfile(src_file, out_chapter)
        published.append((n, out_chapter))

    # assemble book.md
    title = "Book"
    model_path = os.path.join(PIPE, "book.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(PIPE, "model.json")
    if os.path.exists(model_path):
        with open(model_path, encoding="utf-8") as f:
            model = json.load(f)
        title = model.get("book_long_title", "Book")

    parts = [f"# {title}\n"]
    for n, cp in published:
        with open(cp, encoding="utf-8") as f:
            parts.append(f.read().strip())
        parts.append("\n---\n")
    book_md = "\n\n".join(parts).rstrip() + "\n"

    book_name = f"book_{language}.md" if language else "book.md"
    with open(os.path.join(ver_dir, book_name), "w", encoding="utf-8") as f:
        f.write(book_md)

    # progress update
    pp = os.path.join(PIPE, "progress.json")
    if os.path.exists(pp):
        with open(pp, encoding="utf-8") as f:
            prog = json.load(f)
        prog["published"] = True
        prog["published_at"] = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        prog["published_version"] = k
        if language:
            prog["published_language"] = language
        with open(pp, "w", encoding="utf-8") as f:
            json.dump(prog, f, indent=2, ensure_ascii=False)

    print(f"Published {len(published)} chapters to {ver_dir}")
    print(f"Skipped: {len(skipped)}")
    for n, r in skipped:
        print(f"  chapter {n}: {r}")
    print(f"Assembled: {os.path.join(ver_dir, book_name)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python .tools/publish.py <bookname> [<language>]")
    lang = sys.argv[2] if len(sys.argv) > 2 else None
    publish(sys.argv[1], lang)
