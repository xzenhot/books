#!/usr/bin/env python3
"""Publish validated latest-stage segments and legacy chapter-root drafts."""

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()
import argparse
import os
import re
import shutil
import tempfile
from pathlib import Path
from quality import (read_json, write_json, canonical_names, require_publishable,
                     digest, now, audit_timestamp, stamp_json, stamp_markdown_file,
                     sync_progress, read_book_plan, read_chapter_model,
                     planned_segment_count, assemble_publish_md,
                     publish_stage_is_complete, publish_poem_sources,
                     publish_poems)

ROOT = str(Path(__file__).resolve().parent.parent)

PUBLISH_STAGE = "latest"
PUBLISH_STAGE_FALLBACK = "editor"


def publish_body(chapter):
    """Return the chapter's body assembled from its publish-stage poems.

    The publish stage is ``segments/<m>/latest/segment.md`` (the most recent
    finalized copy), falling back to ``segments/<m>/editor/segment.md`` when a
    segment has no latest copy. Returns ``None`` when no poems exist
    (legacy/novel chapters fall back to `chapter.md`).
    """
    body = assemble_publish_md(chapter)
    return body if body else None


def stamp_published_source(stage, bookname, version):
    """Record the published source in the print profile copied into *stage*.

    A pipeline's profile names the pipeline as the folder its content comes from.
    A published version holds the content itself, so the copy is rewritten to
    name the version folder - relative to ``workspaces/published`` - which is what
    lets a profile read on its own be followed back to its book.
    """
    path = stage / "profile" / "publish" / "default" / "profile.json"
    if not path.is_file():
        return
    profile = read_json(path)
    profile["source"] = {
        "book_name": bookname,
        "source_format": "published",
        "source_path": bookname,
        "version": version,
    }
    write_json(path, profile)


def collect_draft(chapter):
    """Read a chapter's draft bytes and model for publication.

    For a per-segment chapter the publish stage (``latest/``, else ``editor/``)
    is the **only** source — the writer stage is never published. For a
    legacy/novel chapter (no per-segment plan) the chapter-root `chapter.md` is
    used. Draft mode bypasses the quality-pass and hash checks but not the stage
    requirement.
    """
    if planned_segment_count(chapter) > 0:
        data = publish_body(chapter)
        if not data:
            raise ValueError(f"{chapter.name}: missing latest-stage poems")
        data = data.encode("utf-8")
    else:
        data = (chapter / "chapter.md").read_bytes()
    if not data.strip():
        raise ValueError(f"{chapter.name}: missing draft")
    return data, read_chapter_model(chapter)


def collect_publish_segments(chapter):
    """Return non-empty publish-stage segment files as ``[(name, bytes, stage), ...]``.

    Prefers ``latest/segment.md``; falls back to ``editor/segment.md`` per
    segment. ``stage`` records which file supplied the bytes.
    """
    return publish_poem_sources(chapter)


def publish(bookname, draft=False):
    if not bookname or bookname in {".", ".."} or any(c in bookname for c in '/\\:<>"|?*'):
        raise ValueError("Expected a single book folder name")
    pipeline = Path(ROOT) / "workspaces/pipeline" / bookname
    model = read_book_plan(pipeline)
    selected = []
    warnings = []
    fallbacks = []
    # Publish every available chapter; record (rather than block on) chapters that
    # are missing, unregistered, or lacking a quality pass.
    for name in canonical_names(model):
        try:
            chapter = pipeline / "chapters" / name
            if draft:
                data, metadata = collect_draft(chapter)
            else:
                planned = planned_segment_count(chapter)
                if planned > 0:
                    # Per-segment chapter: publish only the publish stage
                    # (latest/, else editor/), and require every planned segment
                    # to have a poem whose assembly matches the recorded quality
                    # review hash.
                    if not publish_stage_is_complete(chapter):
                        raise ValueError(
                            f"publish stage incomplete "
                            f"({len(publish_poems(chapter))}/{planned} segments)"
                        )
                    publish_md = publish_body(chapter)
                    data, metadata = require_publishable(chapter, data=publish_md.encode("utf-8"))
                else:
                    # Legacy/novel: validate the chapter-root draft.
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
            per_segment = planned_segment_count(chapter) > 0
            selected.append({
                "name": name,
                "title": " ".join(title.split()),
                "body": body,
                "data": data,
                "metadata": metadata,
                "per_segment": per_segment,
                "segments": collect_publish_segments(chapter) if per_segment else [],
            })
        except (OSError, ValueError, KeyError) as error:
            warnings.append(f"{name}: {error}")
    if warnings:
        print("Publication warnings (skipped):")
        for warning in warnings:
            print(f"  - {warning}")
    if not selected:
        raise ValueError("No publishable chapters found")

    destination = Path(ROOT) / "workspaces/published" / bookname
    destination.mkdir(parents=True, exist_ok=True)
    audit_date = audit_timestamp()
    # Build privately, then rename the complete directory into its immutable version.
    with tempfile.TemporaryDirectory(prefix=".publish-", dir=destination) as temporary:
        stage = Path(temporary) / "collection"
        stage.mkdir()
        sections = []
        for item in selected:
            folder = stage / "chapters" / item["name"]
            folder.mkdir(parents=True)
            chapter_md = folder / "chapter.md"
            chapter_md.write_text(
                f"# {item['title']}\n\n{item['body']}\n", encoding="utf-8"
            )
            stamp_markdown_file(chapter_md, "publish", audit_date)
            chapter_metadata = stamp_json(dict(item["metadata"]), "publish", audit_date)
            write_json(folder / "chapter.json", chapter_metadata)
            for segment_name, segment_data, _source_stage in item["segments"]:
                # Both published folders are sourced from the publish stage
                # (latest/, else editor/), so the published version always
                # mirrors the pipeline's final text.
                for published_stage in ("editor", "latest"):
                    segment_md = (
                        folder / "segments" / segment_name / published_stage / "segment.md"
                    )
                    segment_md.parent.mkdir(parents=True, exist_ok=True)
                    segment_md.write_bytes(segment_data)
                    stamp_markdown_file(segment_md, "publish", audit_date)
            sections.append(f"## {item['title']}\n\n{item['body']}")
        title = model.get("book_long_title") or bookname
        book_md = stage / "book.md"
        book_md.write_text(
            f"# {title}\n\n" + "\n\n---\n\n".join(sections) + "\n",
            encoding="utf-8",
        )
        stamp_markdown_file(book_md, "publish", audit_date)
        manifest = stamp_json({
            "published_at": now(),
            "chapters": [
                {"name": item["name"], "sha256": digest(item["data"])}
                for item in selected
            ],
        }, "publish", audit_date)
        write_json(stage / "manifest.json", manifest)
        # The print profile travels with the published source, so a version
        # prints without the pipeline beside it. Its page paths are relative to
        # the profile folder, so they stay valid in the copy.
        profile_source = pipeline / "profile" / "publish" / "default"
        if profile_source.is_dir():
            shutil.copytree(profile_source, stage / "profile" / "publish" / "default")
        for item in selected:
            name = item["name"]
            chapter = pipeline / "chapters" / name
            live, current_model = collect_draft(chapter)
            current_segments = (
                collect_publish_segments(chapter) if item["per_segment"] else []
            )
            if (
                live != item["data"]
                or current_model != item["metadata"]
                or current_segments != item["segments"]
            ):
                raise ValueError(f"{name}: changed during publication; retry")
        # Include legacy numeric versions when choosing the next unused number.
        numbers = [int(m.group(1)) for p in destination.iterdir() if p.is_dir()
                   and (m := re.fullmatch(r"(?:version)?([0-9]+)", p.name))]
        version = max(numbers, default=0) + 1
        # Mirror each published editor poem into the pipeline's segment latest/
        # folder before the version is committed, so a mirror failure cannot
        # leave a published version without its pipeline latest/ copy.
        for item in selected:
            if not item["per_segment"]:
                continue
            for segment_name, segment_data, source_stage in item["segments"]:
                # Refresh the pipeline latest/ mirror; report segments that
                # published from editor/ because no latest copy existed yet.
                latest_md = (
                    pipeline / "chapters" / item["name"] / "segments" / segment_name
                    / "latest" / "segment.md"
                )
                if source_stage == PUBLISH_STAGE_FALLBACK:
                    fallbacks.append(f"{item['name']}/{segment_name}")
                latest_md.parent.mkdir(parents=True, exist_ok=True)
                latest_md.write_bytes(segment_data)
        while True:
            version_dir = destination / f"version{version}"
            if version_dir.exists():
                version += 1
                continue
            # The copy of the print profile records where the content of this
            # version comes from, so a profile read on its own - or shared with a
            # printer - still finds the published book it describes.
            stamp_published_source(stage, bookname, version)
            try:
                os.rename(stage, version_dir)
                break
            except FileExistsError:
                version += 1
    sync_progress(pipeline)
    progress_path = pipeline / "progress.json"
    progress = read_json(progress_path)
    hashes = {item["name"]: digest(item["data"]) for item in selected}
    for row in progress["chapters"]:
        key = str(row["chapter_number"])
        if key not in hashes:
            continue
        row["published_sha256"] = hashes[key]
        row["published_version"] = version
    progress.update(published_version=version, published_at=now())
    progress.pop("published_language", None)
    stamp_json(progress, "publish", audit_date)
    write_json(progress_path, progress)
    sync_progress(pipeline)
    progress = read_json(progress_path)
    stamp_json(progress, "publish", audit_date)
    write_json(progress_path, progress)
    print(f"Published {len(selected)} chapters to {version_dir}")
    if fallbacks:
        print(
            f"Note: {len(fallbacks)} segment(s) had no latest/ copy and were "
            f"published from editor/ (latest/ now refreshed): {', '.join(fallbacks)}"
        )
    return version_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bookname")
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Publish available editor-stage segments or legacy chapter drafts, "
             "bypassing the quality-pass validation (forceful publication).",
    )
    args = parser.parse_args()
    try:
        publish(args.bookname, draft=args.draft)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\n")
