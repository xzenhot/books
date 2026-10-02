#!/usr/bin/env python3
"""Publish a complete validated collection from current chapter-root drafts."""
import argparse
import os
import re
import tempfile
from pathlib import Path
from quality import read_json, write_json, canonical_names, require_publishable, digest, now, sync_progress, read_book_plan, read_chapter_model

ROOT = str(Path(__file__).resolve().parent.parent)


def collect_draft(chapter):
    """Read a chapter's draft bytes and model for draft-mode publication.

    Draft mode bypasses the quality-pass requirement and the registered-draft
    hash check: it reads whatever `chapter.md` currently holds and its model,
    requiring only a non-empty draft. The caller is responsible for the
    title/body sanity checks that follow.
    """
    data = (chapter / "chapter.md").read_bytes()
    if not data.strip():
        raise ValueError(f"{chapter.name}: missing draft")
    return data, read_chapter_model(chapter)


def publish(bookname, draft=False):
    if not bookname or bookname in {".", ".."} or any(c in bookname for c in '/\\:<>"|?*'):
        raise ValueError("Expected a single book folder name")
    pipeline = Path(ROOT) / ".space/pipeline" / bookname
    model = read_book_plan(pipeline)
    selected = []
    blocked = []
    # Fail closed before allocating a reader-facing version, including missing poems.
    for name in canonical_names(model):
        try:
            chapter = pipeline / "chapters" / name
            if draft:
                data, metadata = collect_draft(chapter)
            else:
                data, metadata = require_publishable(chapter)
            title = metadata.get("chapter_title")
            if not isinstance(title, str) or not title.strip():
                raise ValueError("missing chapter title")
            body = data.decode("utf-8-sig").strip()
            lines = body.splitlines()
            if re.match(r"^#{1,6}\s+", lines[0]):
                body = "\n".join(lines[1:]).strip()
            if not body:
                raise ValueError("draft contains only a heading")
            selected.append((name, " ".join(title.split()), body, data, metadata))
        except (OSError, ValueError, KeyError) as error:
            blocked.append(str(error))
    if blocked:
        raise ValueError(
            "Publication blocked; every planned poem needs a matching quality pass. "
            + " | ".join(blocked)
        )

    destination = Path(ROOT) / "source/books" / bookname
    destination.mkdir(parents=True, exist_ok=True)
    # Build privately, then rename the complete directory into its immutable version.
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=destination) as temporary:
        stage = Path(temporary) / "collection"
        stage.mkdir()
        sections = []
        for name, title, body, data, metadata in selected:
            folder = stage / "chapters" / name
            folder.mkdir(parents=True)
            (folder / "chapter.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
            write_json(folder / "chapter.json", metadata)
            sections.append(f"## {title}\n\n{body}")
        title = model.get("book_long_title") or bookname
        (stage / "book.md").write_text(f"# {title}\n\n" + "\n\n---\n\n".join(sections) + "\n", encoding="utf-8")
        write_json(stage / "manifest.json", {"published_at": now(), "chapters": [{"name": n, "sha256": digest(d)} for n, _, _, d, _ in selected]})
        for name, _, _, data, metadata in selected:
            chapter = pipeline / "chapters" / name
            live, current_model = collect_draft(chapter) if draft else require_publishable(chapter)
            if live != data or current_model != metadata:
                raise ValueError(f"{name}: changed during publication; retry")
        # Include legacy numeric versions when choosing the next unused number.
        numbers = [int(m.group(1)) for p in destination.iterdir() if p.is_dir()
                   and (m := re.fullmatch(r"(?:version)?([0-9]+)", p.name))]
        version = max(numbers, default=0) + 1
        while True:
            version_dir = destination / f"version{version}"
            if version_dir.exists():
                version += 1
                continue
            try:
                os.rename(stage, version_dir)
                break
            except FileExistsError:
                version += 1
    sync_progress(pipeline)
    progress_path = pipeline / "progress.json"
    progress = read_json(progress_path)
    hashes = {n: digest(d) for n, _, _, d, _ in selected}
    for row in progress["chapters"]:
        row["published_sha256"] = hashes[str(row["chapter_number"])]
        row["published_version"] = version
    progress.update(published_version=version, published_at=now())
    progress.pop("published_language", None)
    write_json(progress_path, progress)
    sync_progress(pipeline)
    print(f"Published {len(selected)} chapters to {version_dir}")
    return version_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bookname")
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Publish from current chapter-root drafts, bypassing the quality-pass "
             "and registered-draft validation (forceful publication).",
    )
    args = parser.parse_args()
    try:
        publish(args.bookname, draft=args.draft)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\n")
