#!/usr/bin/env python3
"""Create, resume, or extend a poetry pipeline without replacing existing work."""

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()
import argparse
import shutil
from pathlib import Path
from quality import (read_json, write_json, atomic_bytes, canonical_names, sync_progress,
                     reconcile_filter_chain, stamp_json, audit_timestamp,
                     stamp_markdown_file)

ROOT = str(Path(__file__).resolve().parent.parent)
AUDIT_FIELDS = ("updated_by", "updated_date", "updated_at")

# The quality dimensions a poetry pipeline assigns per poem, mirroring the
# filter registry. Each dimension owns a folder under qualities/ and is recorded
# in qualities/qualities.json. Novel pipelines use the shorter NOVEL list.
# `theme` and `syntax` moved here from the filter chain. See
# `.framework/what_i_need.md` Part 2 and the book plan's `quality_chain`.
POETRY_QUALITY_DIMENSIONS = ("subject", "genre", "theme", "syntax", "signature")
NOVEL_QUALITY_DIMENSIONS = ("genre", "theme", "syntax", "signature")

# Every filter resolves by form: `.framework/editor/<form>/filters/<name>/SKILL.md`.
# (Formerly some filters lived in a shared, form-agnostic tree; that has been
# folded into the per-form `editor/<form>/filters/` folders.)


def _filter_skill_path(root, name, form):
    """Resolve a filter name to its SKILL.md, always by form."""
    return root / ".framework" / "editor" / form / "filters" / name / "SKILL.md"


def _content(document):
    """Return a JSON document without its audit fields, for equality checks."""
    return {key: value for key, value in document.items() if key not in AUDIT_FIELDS}


def _write_if_changed(path, document):
    """Write a JSON document only when its content (ignoring audit fields) changed.

    A newly stamped document whose content is unchanged is also refreshed, so a
    file written before audit stamping gains the fields on the next run.
    """
    if path.exists():
        current = read_json(path)
        if _content(current) == _content(document) and all(field in current for field in ("updated_by", "updated_date")):
            return False
    write_json(path, document)
    return True


def scaffold(bookname, chapter_count=None, form=None, gist=None,
             word_target=None, filter_chain=None):
    if not bookname or bookname in {".", ".."} or any(c in bookname for c in '/\\:<>"|?*'):
        raise ValueError("Expected a single book folder name")
    root = Path(ROOT)
    plan_path = root / "workspaces/backlog" / bookname / "book.json"
    plan = read_json(plan_path)

    # --- Parameter overrides (online scaffold sends explicit values) ---
    # These let the online (agentic) scaffold delegate the large per-chapter
    # loop to Python with explicit deterministic parameters instead of
    # hand-writing every chapter folder itself. Every override must stay
    # consistent with the backlog plan; scaffold refuses rather than silently
    # rewriting the plan — the one exception is the filter chain, reconciled
    # below to the form the plan declares.
    if form is not None:
        if form != "poetry":
            raise ValueError(
                "tools/scaffold.py is the poetry scaffold; use scaffold_novel for novels"
            )
        plan["form"] = form
    if chapter_count is not None:
        if chapter_count <= 0:
            raise ValueError("chapter_count must be a positive integer")
        plan["chapter_count"] = chapter_count
    if word_target is not None:
        if word_target <= 0:
            raise ValueError("word_target must be a positive integer")
        for entry in plan.get("chapters", []):
            entry["word_target"] = word_target
    if filter_chain is not None:
        plan["filter_chain"] = list(filter_chain)
    if gist is not None:
        plan["gist"] = gist

    names = canonical_names(plan)
    if plan.get("form") != "poetry" or plan.get("book_name") != bookname:
        raise ValueError("Plan must identify the requested poetry book")
    style = plan.get("style") or "pijush"
    if (
        not isinstance(style, str)
        or not style.strip()
        or style in {".", ".."}
        or any(char in style for char in "/\\")
    ):
        raise ValueError("Book style must be a single style nickname")
    if plan.get("chapter_count") != len(names):
        raise ValueError("chapter_count must equal the number of poems")
    for i, entry in enumerate(plan["chapters"], 1):
        if entry.get("name") != str(i) or type(entry.get("chapter_index")) is not int or entry["chapter_index"] != i:
            raise ValueError("Poetry identities must be sequential, starting at 1")
        if type(entry.get("word_target")) is not int or entry["word_target"] <= 0:
            raise ValueError("word_target must be a positive integer")
        if any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in ("chapter_title", "chapter_summary")) or not isinstance(entry.get("further_references"), list):
            raise ValueError("Incomplete chapter model")
    chain = reconcile_filter_chain(plan)
    for name in chain:
        if not _filter_skill_path(root, name, plan.get("form", "poetry")).is_file():
            raise ValueError(f"Missing filter skill: {name}")
    # A plan laid out with the novel option declares the novel chain. Poetry
    # requires the ordered workshop-through-quality chain, so reconcile the plan
    # instead of refusing to scaffold it.
    chain_repaired = plan.get("filter_chain") != chain
    plan["filter_chain"] = chain

    pipeline = root / "workspaces/pipeline" / bookname
    model_path = pipeline / "book.json"
    existing = None
    if model_path.exists():
        existing = read_json(model_path)
    elif (pipeline / "model.json").exists():
        existing = read_json(pipeline / "model.json")
    if existing:
        old_names = canonical_names(existing)
        if existing.get("form") != "poetry" or names[:len(old_names)] != old_names:
            raise ValueError("Scaffold can append only; form changes/removals require explicit migration")
        # Root chapter entries are the original plan, separate from enriched chapter models.
        if existing["chapters"] != plan["chapters"][:len(old_names)]:
            raise ValueError("Existing plan entries changed; reconcile explicitly before scaffold")
        if existing.get("filter_chain") != chain:
            # A pipeline cloned from a novel-preset layout carries the novel
            # chain; poetry reconciles it to the canonical chain instead of
            # refusing. A genuinely different human chain still stops scaffold.
            if reconcile_filter_chain(existing) != chain:
                raise ValueError("Existing filter chain changed; reconcile explicitly")
            existing["filter_chain"] = chain
    else:
        old_names = []

    # Validate existing identities and auxiliary JSON before any mutation.
    for entry in plan["chapters"]:
        path = pipeline / "chapters" / entry["name"] / "model.json"
        if path.exists():
            live = read_json(path)
            if live.get("name") != entry["name"] or live.get("chapter_index") != entry["chapter_index"]:
                raise ValueError(f"Conflicting chapter identity: {path}")
    for relative in ("progress.json", "filters/filters.json", "qualities/qualities.json"):
        path = pipeline / relative
        if path.exists():
            read_json(path)

    pipeline.mkdir(parents=True, exist_ok=True)
    stamp = audit_timestamp()

    # --- Clone the form-tool template tree (layout/) into the pipeline. ---
    # enrich.py (and write.py) read their lenses/twists/prompts from the book's
    # own pipeline layout/ folder, not the shared framework tree. Clone the
    # v1 layout/ subtree so the pipeline is self-contained before enrichment.
    layout_src = root / ".framework" / "templates" / "backlog" / "v1" / "layout"
    layout_dst = pipeline / "layout"
    if layout_src.is_dir() and not layout_dst.exists():
        shutil.copytree(layout_src, layout_dst)

    # --- Copy the backlog sources into the pipeline verbatim ---
    # Scaffold never writes to the backlog. It copies the sources the backlog
    # phase staged: the plan inputs (gist, storyline, progress) and the book's
    # vocabulary seed. Never overwrite an existing pipeline file: progress.json
    # holds live writing state, and the sources are cloned only on first scaffold.
    backlog_dir = root / "workspaces/backlog" / bookname
    for src_name in ("gist.md", "storyline.md", "progress.json", "bookseed.md"):
        src = backlog_dir / src_name
        dest = pipeline / src_name
        if src.is_file() and not dest.exists():
            shutil.copy2(src, dest)

    # The selected style's signature lives with the framework, not in the
    # backlog, so scaffold resolves it directly from the style folder. Plain
    # text seed files are copied verbatim; the Markdown signature is stamped.
    signature_source = root / ".framework/editor/poetry/styles" / style / "signature.md"
    signature_dest = pipeline / "signature.md"
    if signature_dest.exists():
        print("Preserving existing pipeline style signature")
    elif signature_source.is_file():
        shutil.copy2(signature_source, signature_dest)
        stamp_markdown_file(signature_dest, "scaffold", stamp)
        print("Copied style signature into the pipeline")
    else:
        print(f"No style signature found for poetry style '{style}'; continuing without one")

    model = dict(existing or plan)
    if existing and len(names) > len(old_names):
        model["chapters"] = existing["chapters"] + plan["chapters"][len(old_names):]
        model["chapter_count"] = len(names)
    # The pipeline plan is a verbatim clone of the backlog plan; the audit
    # fields are the only permitted difference (see audit-metadata.md). Stamp
    # both with one timestamp so the clone stays equal to its source.
    stamp_json(model, "scaffold", stamp)
    if chain_repaired:
        write_json(plan_path, stamp_json(plan, "scaffold", stamp))
        print(f"Reconciled poetry filter chain: {' -> '.join(chain)}")
    _write_if_changed(model_path, model)
    # Each chapter is complete before publishing the expanded root model.
    for entry in plan["chapters"]:
        chapter = pipeline / "chapters" / entry["name"]
        segment = chapter / "segments/1"
        for folder in (chapter / "history", segment / "writer", segment / "editor", segment / "translator", segment / "version"):
            folder.mkdir(parents=True, exist_ok=True)
        if not (chapter / "chapter.json").exists() and not (chapter / "model.json").exists():
            write_json(chapter / "chapter.json", dict(entry, level="chapter", state="scaffolded", segments=[1]))
        if not (segment / "segment.json").exists():
            # Migrate legacy segment model.json -> segment.json (copy, keep legacy until verified).
            legacy = segment / "model.json"
            if legacy.exists() and not (segment / "segment.json").exists():
                write_json(segment / "segment.json", read_json(legacy))
            else:
                write_json(segment / "segment.json", {"level": "segment", "state": "pending", "chapter_index": entry["chapter_index"], "segment_index": 1})
    registry = pipeline / "filters/filters.json"
    if not registry.exists():
        form = plan.get("form", "poetry")
        write_json(registry, stamp_json(
            {"filters": [
                {"order": i, "name": name,
                 "agent": f".framework/editor/{form}/filters/{name}/SKILL.md",
                 "autorun": True}
                for i, name in enumerate(chain, 1)]},
            "scaffold"))
    # The quality registry is scaffold's counterpart to filters.json: it names the
    # book's quality dimensions, one folder each under qualities/, resolved by form.
    # The book plan's `quality_chain` is authoritative; when absent, fall back to
    # the form's canonical dimensions. Scaffold creates only the registry JSON
    # (like filters.json); each quality folder is created on first use by its agent.
    quality_registry = pipeline / "qualities/qualities.json"
    if not quality_registry.exists():
        quality_names = list(plan.get("quality_chain") or [])
        if not quality_names:
            quality_names = NOVEL_QUALITY_DIMENSIONS if plan.get("form") == "novel" else POETRY_QUALITY_DIMENSIONS
        write_json(quality_registry, stamp_json(
            {"form": plan.get("form"), "qualities": [
                {"order": i, "name": name, "autorun": True}
                for i, name in enumerate(quality_names, 1)]},
            "scaffold"))
    prompt = pipeline / "override.md"
    if not prompt.exists():
        # Copy the author's master prompt from the backlog. Once the pipeline
        # exists the backlog is never read again, so this is the only chance to
        # carry the mandated voice, craft rules and sample poems across. The
        # neutral stub is used only when the backlog has no override.
        source = plan_path.parent / "override.md"
        if source.is_file():
            atomic_bytes(prompt, source.read_bytes())
        else:
            atomic_bytes(prompt, b"No transform required.\n")
    # Override filter.md remains lazy; existing human instructions are untouched.
    sync_progress(pipeline)
    progress_path = pipeline / "progress.json"
    if progress_path.exists():
        _write_if_changed(progress_path, stamp_json(read_json(progress_path), "scaffold", stamp))
    print(f"Scaffold ready: {bookname}, {len(names)} poems; existing drafts and metadata preserved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bookname")
    parser.add_argument("--count", "--chapter-count", type=int, default=None,
                        help="Number of poems to scaffold (default: from book.json).")
    parser.add_argument("--form", choices=("poetry", "novel"), default=None,
                        help="Book form (default: poetry, from book.json).")
    parser.add_argument("--gist", default=None,
                        help="Seed text for the book (default: from book.json).")
    parser.add_argument("--word-target", type=int, default=None,
                        help="Per-poem word target (default: from book.json).")
    parser.add_argument("--filter-chain", nargs="*", default=None,
                        help="Ordered filter chain (default: from book.json).")
    args = parser.parse_args()
    try:
        scaffold(args.bookname, chapter_count=args.count, form=args.form,
                 gist=args.gist, word_target=args.word_target,
                 filter_chain=args.filter_chain)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"ERROR: {error}\n")
