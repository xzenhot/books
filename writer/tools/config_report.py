#!/usr/bin/env python3
"""config_report.py — generate the pipeline `config.json` report and `profile.json`.

Rebuilds `workspaces/pipeline/<bookname>/config.json` from the authoritative
pipeline state, so the report can never drift from what the book actually is:

- `book.json`     -> title, language, form, model, provider, factory, counts
- `chapter.json`  -> chapter title
- `segment.json`  -> segment title
- `progress.json` -> status, written/validated/published flags, versions
- publish stages  -> each segment's canonical `file_path` and `validated` flag

The reference shape is `.framework/templates/backlog/v1/config.json`.

The publisher print profile — page setup, covers, publishing details and the
designed pages — is *not* part of the report. It lives in the book source, in
`profile/publish/default/profile.json` beside the `pages/` folders it prints,
staged from `.framework/templates/profile/publish/default/profile.json` and
customized for the book. Print data that an older `config.json` still records
under `display`/`printing`/`layout`, `pages` or `overriden` is moved onto the
profile once, and then removed from the configuration. A `profile.json` or a
`pages/` folder an older version kept at the root of the source is moved into
the profile folder the same way.

It runs automatically after `enrich` and `write` (through
`workplan.sync_outputs`) and can be run by hand:

    python tools/config_report.py <bookname>
"""

from __future__ import annotations

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()

import json
import sys
from pathlib import Path

from quality import (read_json, read_book_plan, read_chapter_model,
                     planned_segment_count, assemble_publish_md, digest,
                     publish_poem_sources, audit_timestamp, atomic_bytes)

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_ROOT = REPO_ROOT / "workspaces" / "pipeline"

# The reference shape staged into a pipeline after a write: the profile that
# prints the book's pages, and the page designs it prints. A book keeps the copy
# it prints with in `profile/publish/default` of its own source, so the print
# setup travels with the content and never shares a file with the pipeline state.
PROFILE_TEMPLATE = REPO_ROOT / ".framework" / "templates" / "profile" / "publish" / "default"
TEMPLATE_PROFILE = PROFILE_TEMPLATE / "profile.json"
TEMPLATE_PAGES = PROFILE_TEMPLATE / "pages"

# The print profile of a pipeline, and the folders it prints, in print order.
PROFILE_FILE = "profile.json"
DEFAULT_PROFILE_NAME = "default"
# Version of the print profile this build writes. Version 2 dropped the `content`
# section a profile used to carry, so the file describes the publisher side of
# the book - its paper, its details and its page folders - and nothing the
# pipeline records about the author's writing. Version 3 added the `source`
# section, which records the folder the content is printed from - the pipeline
# the book is written in, or the version folder it was published as - so a copy
# that travels into a published edition can still be followed back to its book.
PROFILE_VERSION = 3
PROFILE_FOLDER = Path("profile") / "publish" / DEFAULT_PROFILE_NAME
PROFILE_PAGES = PROFILE_FOLDER / "pages"
PAGE_FORMATS = {
    "cover": "image",
    "blurb": "rtf",
    "publisher": "rtf",
    "index": "markdown",
    "content": "markdown",
    "appendix": "rtf",
    "backcover": "image",
}

# What a page file is printed as, by its extension. A page records its own
# `content_type`; the `format` of its folder is only the preference it falls
# back on, so an image put in a folder of designs still prints as an image.
CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jpe": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".rtf": "application/rtf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
}
PAGE_CONTENT_TYPES = {
    "image": "image/jpeg",
    "rtf": "application/rtf",
    "markdown": "text/markdown",
}
UNKNOWN_CONTENT_TYPE = "application/octet-stream"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}

# Keys this module owns. Anything else already in config.json (for example a
# human-supplied `layout` block) is preserved verbatim.
OWNED_TOP_KEYS = (
    "title", "language", "context", "total_chapters", "completed_chapters",
    "current_chapter", "factory", "model", "provider", "book_name", "form",
    "updated_by", "updated_date", "written_chapters", "published",
    "published_version", "published_at", "chapters",
)

# The keys a pipeline used to record its print data under. `display` is the name
# it had last, `printing` and `layout` the names before it; `pages` and
# `overriden` held the designed pages and the publishing details. All of it now
# belongs to `profile.json`, so a legacy `config.json` is migrated once and the
# keys are dropped.
LEGACY_DISPLAY_KEYS = ("display", "printing", "layout")
LEGACY_PRINT_KEYS = LEGACY_DISPLAY_KEYS + ("pages", "overriden")

DEFAULT_LAYOUT_OPTIONS = {
    "page_width_mm": 139.7,
    "page_height_mm": 203.2,
    "margin_mm": 20.066,
    "size_unit": "Inches",
    "font_family": "AdorshoLipi",
    "font_size": 8,
    "page_number_format": "Page {page} of {total}",
    "background_image_path": "",
    "front_cover_image_path": "",
    "back_cover_image_path": "",
    "include_covers": True,
    "layout": "ChapterPages",
}


def _optional_json(path: Path) -> dict:
    try:
        if path.is_file():
            return read_json(path)
    except (OSError, ValueError):
        pass
    return {}


def _display_section(config: dict) -> dict | None:
    """Return the legacy print block of *config*, whichever name it is written under."""
    for key in LEGACY_DISPLAY_KEYS:
        section = config.get(key)
        if isinstance(section, dict):
            return section
    return None


def _segment_stage(chapter_dir: Path, segment_name: str) -> tuple[str, bool]:
    """Return ``(stage, validated)`` for one segment's publish source.

    The stage is ``latest`` when a non-empty ``latest/segment.md`` exists, else
    ``editor``, else ``writer``. ``validated`` is True when the segment has a
    non-empty publish-stage poem.
    """
    for stage in ("latest", "editor", "writer"):
        candidate = chapter_dir / "segments" / segment_name / stage / "segment.md"
        if candidate.is_file() and candidate.read_bytes().strip():
            return stage, True
    return "latest", False


def _chapter_status(progress_row: dict, chapter_model: dict) -> str:
    """Prefer the reconciled progress status, else derive it from the model."""
    status = progress_row.get("status")
    if isinstance(status, str) and status:
        return status
    state = chapter_model.get("state")
    return state if isinstance(state, str) and state else "pending"


def _segment_title(segment_dir: Path, plan_record: dict, number: str) -> str:
    model = _optional_json(segment_dir / "segment.json")
    title = str(model.get("segment_title") or "").strip()
    if not title:
        title = str(plan_record.get("segment_title") or "").strip()
    return title or number


def _bengali_number(value) -> str:
    """Render an integer using Bengali digits (matches the reference report)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value)
    return str(number).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))


def _context(book: dict, chapters: list[dict]) -> str | None:
    """Build the short human-readable context line for the report.

    Mirrors the reference shape, e.g. ``১০টি কবিতা; প্রতিটি কবিতায় ৮টি
    পরিকল্পিত segment; প্রতি segment-এর word_target 500।`` — derived from the
    plan, never from the (much longer) book summary.
    """
    form = book.get("form")
    total = len(chapters)
    segment_count = book.get("segment_count")
    if not isinstance(segment_count, int) or segment_count < 1:
        counts = {len(chapter.get("segments", [])) for chapter in chapters}
        segment_count = counts.pop() if len(counts) == 1 else None
    word_target = book.get("word_target")

    if form != "poetry" or not isinstance(segment_count, int) or segment_count < 1:
        return book.get("book_summary") or None
    if not isinstance(word_target, int) or word_target < 1:
        return book.get("book_summary") or None
    return (
        f"{_bengali_number(total)}টি কবিতা; প্রতিটি কবিতায় "
        f"{_bengali_number(segment_count)}টি পরিকল্পিত segment; "
        f"প্রতি segment-এর word_target {word_target}।"
    )


def _template_profile() -> dict:
    """Return the reference print profile from the framework templates."""
    reference = _optional_json(TEMPLATE_PROFILE)
    return reference if isinstance(reference, dict) else {}


def _starter_profile(bookname: str) -> dict:
    """Return a minimal print profile for a pipeline the templates did not stage."""
    options = dict(DEFAULT_LAYOUT_OPTIONS)
    options["footer_text"] = bookname
    return {
        "version": PROFILE_VERSION,
        "name": DEFAULT_PROFILE_NAME,
        "source": _pipeline_source(bookname),
        "book": {
            "options": options,
            "pages": [
                {"order": index, "file_path": f"pages/{name}/", "format": fmt, "paths": []}
                for index, (name, fmt) in enumerate(PAGE_FORMATS.items(), 1)
            ],
        },
    }


def stage_templates(bookname: str) -> list[str]:
    """Copy the reference `profile.json` and the files it points at into the book's pipeline.

    Runs after a write so every pipeline carries the same page designs the
    framework templates ship: the print profile, the `pages/` folders it points
    at and the files kept beside it - the publisher's logo - all inside
    `profile/publish/default`. An existing file is never overwritten - a
    pipeline's own profile and designs win - so this only fills in what is
    missing. Returns the relative paths that were created.
    """
    pipeline = PIPELINE_ROOT / bookname
    if not (pipeline / "book.json").is_file():
        return []

    folder = pipeline / PROFILE_FOLDER
    created: list[str] = []
    if TEMPLATE_PAGES.is_dir():
        for source in sorted(TEMPLATE_PAGES.rglob("*")):
            if not source.is_file():
                continue
            target = folder / "pages" / source.relative_to(TEMPLATE_PAGES)
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_bytes(target, source.read_bytes())
            created.append(target.relative_to(pipeline).as_posix())

    if PROFILE_TEMPLATE.is_dir():
        for source in sorted(PROFILE_TEMPLATE.iterdir()):
            if not source.is_file() or source.name == PROFILE_FILE:
                continue
            target = folder / source.name
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_bytes(target, source.read_bytes())
            created.append(target.relative_to(pipeline).as_posix())

    target = folder / PROFILE_FILE
    if TEMPLATE_PROFILE.is_file() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_bytes(target, TEMPLATE_PROFILE.read_bytes())
        created.append(target.relative_to(pipeline).as_posix())
    return created


def content_type_of(path: str | Path, preference: str = "rtf") -> str:
    """Return the MIME type a page file is printed as.

    The extension decides it; the `format` of the page folder is only the
    preference a file whose extension says nothing falls back on.
    """
    suffix = Path(str(path)).suffix.casefold()
    return CONTENT_TYPES.get(suffix) or PAGE_CONTENT_TYPES.get(preference, UNKNOWN_CONTENT_TYPE)


def _page_paths(folder: Path, pipeline_folder: Path, preference: str = "rtf",
                recorded: dict[str, str] | None = None) -> list[dict]:
    """Return the page files of *folder* as ordered `{order, file_path, content_type}` records."""
    files = [path for path in sorted(folder.iterdir(), key=_page_sort_key) if path.is_file()]
    paths = []
    for index, path in enumerate(files, 1):
        relative = (pipeline_folder / path.name).as_posix()
        kept = (recorded or {}).get(relative.casefold())
        paths.append({
            "order": index,
            "file_path": relative,
            "content_type": kept or content_type_of(path, preference),
        })
    return paths


def _page_sort_key(path: Path) -> tuple:
    """Order a page file: a front cover first, a back cover last, the rest by name."""
    name = path.name.casefold()
    if "front" in name:
        return (0, name)
    if "back" in name:
        return (2, name)
    return (1, name)


def _customize_pages(profile: dict, pipeline: Path, bookname: str) -> None:
    """Align the profile's `pages` with the folders the pipeline actually holds.

    The staged template names the same page folders for every book, so its
    entries are kept - order, folder, format - and only the page files are
    re-derived from the pipeline's `pages/<folder>` contents. An absolute path
    left by a design tool is dropped, because a pipeline records its pages
    relative to itself. A folder the profile does not name yet is added, so
    every part of the book is printed.
    """
    book = profile.setdefault("book", {})
    if not isinstance(book, dict):
        book = {}
        profile["book"] = book

    pages = book.get("pages")
    pages = [entry for entry in pages if isinstance(entry, dict)] if isinstance(pages, list) else []

    named = {str(entry.get("file_path") or "").strip().strip("/") for entry in pages}
    for name, fmt in PAGE_FORMATS.items():
        if f"pages/{name}" not in named:
            pages.append({
                "order": len(pages) + 1,
                "file_path": f"pages/{name}/",
                "format": fmt,
                "paths": [],
            })

    customized = []
    for entry in pages:
        relative = str(entry.get("file_path") or "").strip().strip("/")
        folder = pipeline / PROFILE_FOLDER / relative
        item = dict(entry)
        item["file_path"] = f"{relative}/" if relative else ""
        item.setdefault("format", PAGE_FORMATS.get(Path(relative).name, "rtf"))
        # A page keeps the content type it records; a page that records none is
        # typed from its extension, falling back on the format of its folder.
        recorded = {
            str(path.get("file_path") or "").strip().casefold(): str(path.get("content_type") or "").strip()
            for path in item.get("paths") or []
            if isinstance(path, dict)
        }
        item["paths"] = (
            _page_paths(folder, Path(relative), item["format"], recorded)
            if folder.is_dir() else []
        )
        customized.append(item)

    customized.sort(key=lambda item: _order_of(item.get("order")))
    for index, item in enumerate(customized, 1):
        item["order"] = index
    book["pages"] = customized


def _order_of(value) -> int:
    """Return the numeric order of a page record, 0 when it records none."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def _pipeline_source(bookname: str) -> dict:
    """Return the `source` block of a profile that prints a book from its pipeline.

    The block names the folder the content is printed from, so the profile can be
    copied into a published edition - or handed to a printer - and still be
    followed back to the `book.json` it describes. `source_path` is relative to
    `workspaces/pipeline`, so the workspace can be moved to another machine.
    """
    return {
        "book_name": bookname,
        "source_format": "pipeline",
        "source_path": bookname,
        "version": None,
    }


def _customize_source(profile: dict, bookname: str) -> None:
    """Point the profile's `source` at the pipeline of *bookname*."""
    profile["source"] = _pipeline_source(bookname)


def _migrate_profile_schema(profile: dict) -> dict:
    """Bring an older print profile up to the schema this build writes.

    A profile written before version 2 also described the author's content - its
    name, language, form and parser. That is what the pipeline records, not how
    the book prints, so the section is dropped instead of being written back.
    """
    version = profile.get("version")
    if not isinstance(version, int) or version < PROFILE_VERSION:
        profile["version"] = PROFILE_VERSION
    profile.pop("content", None)
    return profile


def _customize_identity(profile: dict, bookname: str, book: dict) -> dict:
    """Point the profile's identity at *bookname*, returning its `book` block."""
    _migrate_profile_schema(profile)
    profile["name"] = profile.get("name") or DEFAULT_PROFILE_NAME

    block = profile.get("book")
    if not isinstance(block, dict):
        block = {}
        profile["book"] = block
    # A staged template still names the book it was copied from, so the book's
    # own title wins.
    block["display_name"] = (
        book.get("book_long_title") or book.get("book_name")
        or block.get("display_name") or bookname
    )
    return block


def _customize_options(profile: dict, pipeline: Path, bookname: str, book: dict) -> None:
    """Point the profile's page setup at this book's identity and its own covers."""
    block = _customize_identity(profile, bookname, book)

    options = block.get("options")
    if not isinstance(options, dict):
        options = dict(DEFAULT_LAYOUT_OPTIONS)
        block["options"] = options

    if not options.get("footer_text"):
        options["footer_text"] = book.get("book_long_title") or bookname

    # A pipeline without page designs has nothing to point at, so its options
    # stay exactly as recorded (a hand-supplied footer included).
    pages = pipeline / PROFILE_PAGES
    if not pages.is_dir():
        return

    cover = pages / "cover"
    images = []
    if cover.is_dir():
        images = sorted(path for path in cover.iterdir()
                        if path.suffix.lower() in IMAGE_SUFFIXES)
    front = next((path for path in images if "front" in path.name.casefold()), None)
    back = next((path for path in images if "back" in path.name.casefold()), None)
    if front is None and images:
        front, images = images[0], images[1:]
    if back is None:
        back = next((path for path in images if path != front), None)

    # A cover is recorded relative to the pipeline, so a profile that travels
    # with the source still points at the book's own page files.
    for key, path in (("front_cover_image_path", front), ("back_cover_image_path", back)):
        if path is not None:
            options[key] = f"pages/cover/{path.name}"


def align_profile(bookname: str, profile: dict) -> dict:
    """Re-derive the book-specific parts of *profile* from the pipeline's files.

    Called for a freshly staged profile and again on every rebuild, so the
    identity, the covers, the source and the recorded page files follow the
    pipeline.
    """
    pipeline = PIPELINE_ROOT / bookname
    book = read_book_plan(pipeline)
    _customize_pages(profile, pipeline, bookname)
    _customize_options(profile, pipeline, bookname, book)
    _customize_source(profile, bookname)
    return profile


def build_profile(bookname: str, document: dict | None = None) -> dict:
    """Build the ``profile.json`` object of *bookname* from its pipeline state.

    The schema is the framework's profile template; a profile the pipeline
    already carries is kept - its designs, page setup and publishing details
    win - and only the book-specific parts are re-derived.
    """
    source = document if isinstance(document, dict) and document else _template_profile()
    profile = json.loads(json.dumps(source)) if source else _starter_profile(bookname)
    return align_profile(bookname, profile)


def _write_profile(pipeline: Path, profile: dict) -> None:
    """Write *profile* as the print profile of *pipeline*, inside its profile folder."""
    path = pipeline / PROFILE_FOLDER / PROFILE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_bytes(
        path,
        (json.dumps(profile, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )


def _profile_path(pipeline: Path) -> Path:
    """Return the `profile.json` of *pipeline*."""
    return pipeline / PROFILE_FOLDER / PROFILE_FILE


def migrate_legacy_layout(bookname: str) -> bool:
    """Move a profile and page folders kept at the root of a source into its profile folder.

    An older version of the app kept `profile.json` and `pages/` beside the
    content of the book. Both belong to the print profile now, so they are moved
    into `profile/publish/default`, where the app reads them. A file that is
    already there wins, so nothing is overwritten. Returns True when anything
    moved.
    """
    pipeline = PIPELINE_ROOT / bookname
    folder = pipeline / PROFILE_FOLDER
    moved = False

    for name in (PROFILE_FILE, PROFILE_FILE + ".bak"):
        source = pipeline / name
        if not source.is_file():
            continue
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            source.unlink()
        else:
            source.replace(target)
        moved = True

    pages = pipeline / "pages"
    if pages.is_dir():
        for source in sorted(pages.rglob("*")):
            if not source.is_file():
                continue
            target = folder / "pages" / source.relative_to(pages)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                source.unlink()
            else:
                source.replace(target)
            moved = True
        for path in sorted(pages.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        if not any(pages.iterdir()):
            pages.rmdir()

    return moved


def _migrate_legacy_profile(bookname: str) -> bool:
    """Move the print data of a legacy ``config.json`` onto ``profile.json``.

    A pipeline that still records its print setup in ``config.json`` - under
    ``display`` or its older names, with ``pages`` and ``overriden`` beside it -
    gets a profile built from those records, and the keys are then removed from
    the configuration. Returns True when a profile was written.
    """
    pipeline = PIPELINE_ROOT / bookname
    if _profile_path(pipeline).is_file():
        return False

    config = _optional_json(pipeline / "config.json")
    display = _display_section(config)
    pages = config.get("pages")
    overriden = config.get("overriden")
    if display is None and not isinstance(pages, list) and not isinstance(overriden, dict):
        return False

    profile = _starter_profile(bookname)
    block = profile["book"]
    block.pop("pages", None)
    block.pop("options", None)
    if isinstance(display, dict) and isinstance(display.get("options"), dict):
        block["options"] = json.loads(json.dumps(display["options"]))
    if isinstance(overriden, dict):
        block.update(json.loads(json.dumps(overriden)))
    if isinstance(pages, list):
        block["pages"] = json.loads(json.dumps(pages))

    _write_profile(pipeline, align_profile(bookname, profile))
    drop_legacy_sections(bookname)
    return True


def drop_legacy_sections(bookname: str) -> bool:
    """Remove the print keys a legacy ``config.json`` still carries."""
    path = PIPELINE_ROOT / bookname / "config.json"
    config = _optional_json(path)
    if not any(key in config for key in LEGACY_PRINT_KEYS):
        return False
    for key in LEGACY_PRINT_KEYS:
        config.pop(key, None)
    path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return True


def build_config(bookname: str, updated_by: str = "config") -> dict:
    """Build the config.json object for *bookname* from current pipeline state."""
    pipeline = PIPELINE_ROOT / bookname
    book = read_book_plan(pipeline)
    progress = _optional_json(pipeline / "progress.json")
    existing = _optional_json(pipeline / "config.json")

    progress_rows = {
        str(row.get("chapter_number")): row
        for row in progress.get("chapters", [])
        if isinstance(row, dict)
    }

    chapters: list[dict] = []
    written = validated = 0
    for name in [str(entry.get("name")) for entry in book.get("chapters", [])]:
        chapter_dir = pipeline / "chapters" / name
        model = read_chapter_model(chapter_dir) if chapter_dir.is_dir() else {}
        row = progress_rows.get(name, {})

        segments: list[dict] = []
        if planned_segment_count(chapter_dir) > 0:
            plan_records = {
                str(record.get("segment_index")): record
                for record in model.get("segments", [])
                if isinstance(record, dict) and "segment_index" in record
            }
            segment_dirs = sorted(
                (path for path in (chapter_dir / "segments").iterdir()
                 if path.is_dir() and path.name.isdecimal()),
                key=lambda path: int(path.name),
            ) if (chapter_dir / "segments").is_dir() else []
            for segment_dir in segment_dirs:
                stage, is_validated = _segment_stage(chapter_dir, segment_dir.name)
                segments.append({
                    "segment_number": int(segment_dir.name),
                    "segment_title": _segment_title(
                        segment_dir, plan_records.get(segment_dir.name, {}), segment_dir.name
                    ),
                    "file_path": (
                        f"chapters/{name}/segments/{segment_dir.name}"
                        f"/{stage}/segment.md"
                    ),
                    "validated": is_validated,
                })

        chapter_written = bool(row.get("written"))
        chapter_validated = bool(row.get("validated"))
        written += int(chapter_written)
        validated += int(chapter_validated)

        chapters.append({
            "chapter_number": int(name) if name.isdecimal() else name,
            "topic": str(model.get("chapter_title") or row.get("topic") or name),
            "category": str(row.get("category") or ""),
            "status": _chapter_status(row, model),
            "file_path": f"chapters/{name}/chapter.md",
            "segments": segments,
        })

    config = {
        "title": book.get("book_long_title") or book.get("book_name") or bookname,
        "language": book.get("language"),
        # `context` is a short human-readable summary line derived from the plan.
        # Keep an existing curated value; otherwise (re)derive it.
        "context": existing.get("context") or _context(book, chapters),
        "total_chapters": len(chapters),
        "completed_chapters": validated,
        "current_chapter": progress.get("current_chapter"),
        "factory": book.get("factory"),
        "model": book.get("model"),
        "provider": book.get("provider"),
        "book_name": bookname,
        "form": book.get("form"),
        "updated_by": updated_by,
        "updated_date": audit_timestamp(),
        "written_chapters": written,
        "published": bool(progress.get("published")),
        "published_version": progress.get("published_version"),
        "published_at": progress.get("published_at"),
        "chapters": chapters,
    }
    # Keep any additional human keys that are not ours, in their original order.
    # The print keys are not kept: they belong to `profile.json` now.
    for key, value in existing.items():
        if key not in OWNED_TOP_KEYS and key not in LEGACY_PRINT_KEYS:
            config[key] = value
    return config


def sync_config(bookname: str, updated_by: str = "config") -> bool:
    """Write ``config.json`` and ``profile.json`` when they differ from the report.

    Returns True when either file was (re)written. A no-op write is skipped so
    the audit timestamp never bumps without a real change.
    """
    pipeline = PIPELINE_ROOT / bookname
    if not (pipeline / "book.json").is_file():
        return False
    # Stage the reference profile and page designs (never overwriting a
    # pipeline's own file), move any print data an older layout kept beside the
    # content onto the profile, then rebuild both documents from state.
    migrate_legacy_layout(bookname)
    _migrate_legacy_profile(bookname)
    stage_templates(bookname)
    path = pipeline / "config.json"
    config = build_config(bookname, updated_by=updated_by)
    existing = _optional_json(path)
    # Compare ignoring the two audit fields so an unchanged report is a no-op.
    def _body(value: dict) -> dict:
        return {k: v for k, v in value.items()
                if k not in ("updated_by", "updated_date")}
    changed = sync_profile(bookname)
    if path.is_file() and _body(existing) == _body(config):
        return changed
    path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return True


def sync_profile(bookname: str) -> bool:
    """Write ``profile.json`` when it differs from the freshly built profile.

    Returns True when the file was (re)written.
    """
    pipeline = PIPELINE_ROOT / bookname
    if not (pipeline / "book.json").is_file():
        return False
    path = _profile_path(pipeline)
    existing = _optional_json(path)
    profile = build_profile(bookname, existing if path.is_file() else None)
    if path.is_file() and existing == profile:
        return False
    _write_profile(pipeline, profile)
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python tools/config_report.py <bookname>", file=sys.stderr)
        return 2
    bookname = argv[0].strip()
    if not bookname or "/" in bookname or "\\" in bookname:
        print(f"invalid book name: {bookname!r}", file=sys.stderr)
        return 2
    try:
        changed = sync_config(bookname)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"config.json and profile.json {'updated' if changed else 'already current'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
