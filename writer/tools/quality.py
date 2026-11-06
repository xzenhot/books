"""Shared draft identity, atomic metadata, and publication eligibility.

Quality decisions belong to the reviewing agent/human, never this module.
"""

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


# Canonical poetry filter chain: workshop-through-quality, in order.
# `theme` and `syntax` moved to the quality chain; `genre`, `history`, `spatality`,
# and `movement` joined the filter chain.
POETRY_FILTER_CHAIN = ("workshop", "research", "genre", "history", "spatality", "movement", "correctness", "override", "quality")
# Canonical novel filter chain, as declared by the backlog book template.
NOVEL_FILTER_CHAIN = ("workshop", "research", "seeds", "genre", "history", "spatality", "movement", "correctness", "override", "quality")


def filter_chain_names(chain):
    """Normalize a plan's `filter_chain` to plain filter names.

    Accepts the string form the pipeline consumes and the
    `{sl, filter|name, autorun, reference}` object form found in templates,
    dropping blank and placeholder entries.
    """
    names = []
    for entry in chain or []:
        if isinstance(entry, str):
            name = entry.strip()
        elif isinstance(entry, dict):
            name = str(entry.get("name") or entry.get("filter") or "").strip()
        else:
            name = ""
        if name:
            names.append(name)
    return names


def poetry_filter_chain(chain):
    """Return the declared chain when it satisfies the poetry contract, else the canonical one.

    A poetry book plan that was laid out with the novel preset carries the novel
    chain (`research, seeds, ..., quality`), which lacks `workshop`. Poetry needs
    the ordered workshop-through-quality chain, so such a plan is reconciled to
    the canonical poetry chain rather than rejected. Extra filters are preserved
    when the required order is already satisfied.
    """
    names = filter_chain_names(chain)
    required = tuple(name for name in names if name in POETRY_FILTER_CHAIN)
    if required != POETRY_FILTER_CHAIN:
        return list(POETRY_FILTER_CHAIN)
    return names


def reconcile_filter_chain(plan):
    """Return the filter chain the plan's declared form requires.

    Poetry books need the ordered workshop-through-quality chain; a plan laid out
    with the novel option carries the novel chain and is reconciled here. Novel
    plans keep their declared chain.
    """
    if plan.get("form") == "poetry":
        return poetry_filter_chain(plan.get("filter_chain"))
    return filter_chain_names(plan.get("filter_chain"))


def audit_timestamp():
    """Current UTC timestamp in the audit-metadata format, `YYYY-MM-DDTHH:MM:SSZ`."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_json(value, agent, timestamp=None):
    """Stamp a JSON document with `updated_by`/`updated_date` in place.

    Keeps a legacy `updated_at` in sync and never touches creation timestamps.
    Returns *value* so callers can chain the call.
    """
    timestamp = timestamp or audit_timestamp()
    value["updated_by"] = agent
    value["updated_date"] = timestamp
    if "updated_at" in value:
        value["updated_at"] = timestamp
    return value


def stamp_markdown_file(path, agent, timestamp=None):
    """Stamp a Markdown file after it has been copied into a workspace."""
    path = Path(path)
    original = path.read_bytes()
    has_bom = original.startswith(b"\xef\xbb\xbf")
    text = original.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    has_trailing_newline = text.endswith(("\n", "\r"))
    lines = text.splitlines()
    timestamp = timestamp or audit_timestamp()
    metadata = [
        f"- **updated_by:** {agent}",
        f"- **updated_date:** {timestamp}",
    ]

    frontmatter_end = None
    if lines and lines[0].strip() == "---":
        frontmatter_end = next(
            (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
            None,
        )
    # Only a *title* H1 counts: the first content line of the document. A file
    # that opens with prose may contain H1 headings far below; stamping after
    # one of those would corrupt the body, so such a file is treated as having
    # no title heading and gets the block at the top instead.
    body_start = frontmatter_end + 1 if frontmatter_end is not None else 0
    first_content = next(
        (index for index in range(body_start, len(lines)) if lines[index].strip()),
        None,
    )
    heading_index = (
        first_content
        if first_content is not None and lines[first_content].startswith("# ")
        else None
    )
    if heading_index is not None:
        block_start = heading_index + 1
    elif frontmatter_end is not None:
        block_start = frontmatter_end + 1
    else:
        block_start = 0
    content_start = block_start
    while content_start < len(lines) and not lines[content_start].strip():
        content_start += 1
    block_end = content_start
    while block_end < len(lines) and lines[block_end].startswith("- "):
        block_end += 1

    if content_start < block_end:
        retained = [
            line for line in lines[content_start:block_end]
            if not re.match(
                r"- \*\*(?:updated_by|updated_date|Updated by|Updated):\*\*",
                line,
            )
        ]
        lines[content_start:block_end] = retained + metadata
    elif heading_index is None and frontmatter_end is None:
        lines[0:0] = metadata + [""]
    else:
        lines[content_start:content_start] = metadata + [""]

    stamped = newline.join(lines)
    if has_trailing_newline:
        stamped += newline
    if has_bom:
        stamped = "\ufeff" + stamped
    atomic_bytes(path, stamped.encode("utf-8"))


def read_book_plan(pipeline):
    """Read the book-level plan (the root blueprint cloned from the backlog).

    Canonically named `book.json`; falls back to the legacy `model.json` for
    pipelines that were scaffolded before the rename. Chapter-level and
    segment-level `model.json` files are unaffected by this helper.
    """
    pipeline = Path(pipeline)
    for name in ("book.json", "model.json"):
        candidate = pipeline / name
        if candidate.exists():
            return read_json(candidate)
    raise FileNotFoundError(f"No book plan (book.json) found in {pipeline}")


def chapter_model_file(chapter):
    """Resolve a chapter's metadata file, preferring `chapter.json` over `model.json`.

    Returns the existing file when one is present (so reads and writes stay
    symmetric and never orphan a legacy file); defaults to `chapter.json` for a
    brand-new chapter. Segment-level `segments/<x>/segment.json` (legacy `model.json`) is unaffected.
    """
    chapter = Path(chapter)
    for name in ("chapter.json", "model.json"):
        candidate = chapter / name
        if candidate.exists():
            return candidate
    return chapter / "chapter.json"


def read_chapter_model(chapter):
    """Read a chapter's metadata, preferring `chapter.json` over `model.json`."""
    return read_json(chapter_model_file(chapter))


def write_chapter_model(chapter, value):
    """Write a chapter's metadata back to its resolved metadata file."""
    write_json(chapter_model_file(chapter), value)


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def canonical_names(model):
    names = [entry["name"] for entry in model["chapters"]]
    if not names or len(names) != len(set(names)):
        raise ValueError("Book plan must have unique chapter names")
    for name in names:
        if not isinstance(name, str) or name in {"", ".", ".."} or any(c in name for c in '/\\:<>"|?*'):
            raise ValueError("Unsafe chapter name in book plan")
    return names


def sync_progress(pipeline):
    pipeline = Path(pipeline)
    book = read_book_plan(pipeline)
    path = pipeline / "progress.json"
    progress = read_json(path) if path.exists() else {}
    previous = {str(c.get("chapter_number")): c for c in progress.get("chapters", [])}
    rows = []
    for name in canonical_names(book):
        chapter = pipeline / "chapters" / name
        model = read_chapter_model(chapter)
        row = dict(previous.get(name, {}))
        row.update(chapter_number=int(name) if name.isdecimal() else name,
                   topic=model.get("chapter_title", name), file_path=f"chapters/{name}/chapter.md")
        draft = chapter / "chapter.md"
        data = draft.read_bytes() if draft.exists() else b""
        authored = bool(data.strip()) and model.get("draft", {}).get("sha256") == digest(data)
        review = model.get("quality_review", {})
        validated = authored and review.get("status") == "passed" and review.get("sha256") == digest(data)
        published = validated and row.get("published_sha256") == digest(data)
        row.update(written=authored, validated=validated, published=published,
                   status="published" if published else "validated" if validated else "written" if authored else "pending",
                   completed_date=review.get("reviewed_at") if validated else None)
        rows.append(row)
    progress.update(chapters=rows, total_chapters=len(rows),
                    written_chapters=sum(r["written"] for r in rows),
                    completed_chapters=sum(r["validated"] for r in rows),
                    published=all(r["published"] for r in rows),
                    current_chapter=next((r["chapter_number"] for r in rows if not r["written"]), None))
    # The pipeline book.json is the source of truth for book-level settings, so
    # these always overwrite a stale cached value (an earlier run may have
    # recorded a different model). Never write an empty value over a real one.
    for key in ("model", "provider", "book_name", "form", "factory"):
        value = book.get(key)
        if value not in (None, ""):
            progress[key] = value
    # Do not rewrite the file when nothing changed (audit-metadata: no-op writes
    # must not bump the timestamp).
    if not path.exists() or read_json(path) != progress:
        write_json(path, progress)


def register_draft(chapter, origin="write"):
    """Register a successfully authored draft; stage exact bytes for quality."""
    chapter = Path(chapter)
    data = (chapter / "chapter.md").read_bytes()
    if not data.strip():
        raise ValueError("An empty draft cannot be registered")
    model = read_chapter_model(chapter)
    model["draft"] = {"sha256": digest(data), "written_at": now(), "origin": origin}
    model.pop("quality_review", None)
    model["state"] = "written"
    snapshot = chapter.parents[1] / "filters" / "quality" / chapter.name / "draft.md"
    atomic_bytes(snapshot, data)
    write_chapter_model(chapter, model)
    sync_progress(chapter.parents[1])


def require_publishable(chapter):
    chapter = Path(chapter)
    data = (chapter / "chapter.md").read_bytes()
    model = read_chapter_model(chapter)
    sha = digest(data)
    review = model.get("quality_review", {})
    if not data.strip() or model.get("draft", {}).get("sha256") != sha:
        raise ValueError(f"{chapter.name}: missing or unregistered authored draft")
    if review.get("status") != "passed" or review.get("sha256") != sha or not review.get("reviewer") or not review.get("reviewed_at"):
        raise ValueError(f"{chapter.name}: current draft needs a quality pass")
    return data, model


def register_existing_book(pipeline, origin="legacy"):
    pipeline = Path(pipeline)
    book = read_book_plan(pipeline)
    registered = []
    skipped = []
    for name in canonical_names(book):
        chapter = pipeline / "chapters" / name
        draft = chapter / "chapter.md"
        if not draft.exists() or not draft.read_bytes().strip():
            skipped.append(name)
            continue
        model = read_chapter_model(chapter)
        current = digest(draft.read_bytes())
        if model.get("draft", {}).get("sha256") != current:
            register_draft(chapter, origin=origin)
            registered.append(name)
    sync_progress(pipeline)
    return registered, skipped


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Register existing chapter drafts without rewriting their text.")
    parser.add_argument("bookname")
    parser.add_argument("command", choices=("register-existing",))
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    pipeline = root / "workspaces" / "pipeline" / args.bookname
    try:
        registered, skipped = register_existing_book(pipeline)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(f"Registered {len(registered)} existing drafts; skipped {len(skipped)} empty or missing drafts.")
