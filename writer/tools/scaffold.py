#!/usr/bin/env python3
"""Create, resume, or extend a poetry pipeline without replacing existing work."""
import argparse
import shutil
from pathlib import Path
from quality import read_json, write_json, atomic_bytes, canonical_names, sync_progress, read_book_plan

ROOT = str(Path(__file__).resolve().parent.parent)
REQUIRED_FILTERS = ["workshop", "research", "correctness", "theme", "syntax", "override", "quality"]


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
    # rewriting the plan.
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
    if plan.get("chapter_count") != len(names):
        raise ValueError("chapter_count must equal the number of poems")
    for i, entry in enumerate(plan["chapters"], 1):
        if entry.get("name") != str(i) or type(entry.get("chapter_index")) is not int or entry["chapter_index"] != i:
            raise ValueError("Poetry identities must be sequential, starting at 1")
        if type(entry.get("word_target")) is not int or entry["word_target"] <= 0:
            raise ValueError("word_target must be a positive integer")
        if any(not isinstance(entry.get(k), str) or not entry[k].strip() for k in ("chapter_title", "chapter_summary")) or not isinstance(entry.get("further_references"), list):
            raise ValueError("Incomplete chapter model")
    chain = plan.get("filter_chain", [])
    if not isinstance(chain, list) or any(not isinstance(n, str) or not n.isidentifier() for n in chain):
        raise ValueError("Invalid filter chain")
    if len(set(chain)) != len(chain) or [n for n in chain if n in REQUIRED_FILTERS] != REQUIRED_FILTERS:
        raise ValueError("Poetry requires the ordered workshop-through-quality chain")
    for name in chain:
        if not (root / ".framework/filters" / name / "SKILL.md").is_file():
            raise ValueError(f"Missing filter skill: {name}")

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
            raise ValueError("Existing filter chain changed; reconcile explicitly")
    else:
        old_names = []

    # Validate existing identities and auxiliary JSON before any mutation.
    for entry in plan["chapters"]:
        path = pipeline / "chapters" / entry["name"] / "model.json"
        if path.exists():
            live = read_json(path)
            if live.get("name") != entry["name"] or live.get("chapter_index") != entry["chapter_index"]:
                raise ValueError(f"Conflicting chapter identity: {path}")
    for relative in ("progress.json", "filters/filters.json"):
        path = pipeline / relative
        if path.exists():
            read_json(path)

    pipeline.mkdir(parents=True, exist_ok=True)

    # --- Copy the backlog source files (gist.md, storyline.md) verbatim ---
    backlog_dir = root / "workspaces/backlog" / bookname
    for src_name in ("gist.md", "storyline.md", "progress.json"):
        src = backlog_dir / src_name
        if src.is_file():
            shutil.copy2(src, pipeline / src_name)
        if src.is_file():
            shutil.copy2(src, pipeline / src_name)

    model = dict(existing or plan)
    if existing and len(names) > len(old_names):
        model["chapters"] = existing["chapters"] + plan["chapters"][len(old_names):]
        model["chapter_count"] = len(names)
    # Each chapter is complete before publishing the expanded root model.
    for entry in plan["chapters"]:
        chapter = pipeline / "chapters" / entry["name"]
        segment = chapter / "segments/1"
        for folder in (chapter / "history", segment / "writer", segment / "editor", segment / "translator", segment / "version"):
            folder.mkdir(parents=True, exist_ok=True)
        if not (chapter / "chapter.json").exists() and not (chapter / "model.json").exists():
            write_json(chapter / "chapter.json", dict(entry, level="chapter", state="scaffolded", segments=[1]))
        if not (segment / "model.json").exists():
            write_json(segment / "model.json", {"level": "segment", "state": "pending", "chapter_index": entry["chapter_index"], "segment_index": 1})
    if not existing or model != existing:
        write_json(model_path, model)
    seed = pipeline / "bookseed.txt"
    if not seed.exists():
        atomic_bytes(seed, ("\n".join(c["chapter_title"] for c in model["chapters"]) + "\n").encode("utf-8"))
    elif len(names) > len(old_names):
        # Preserve human-edited topic text; append only missing positions.
        lines = seed.read_text(encoding="utf-8-sig").splitlines()
        if len(lines) < len(names):
            atomic_bytes(seed, ("\n".join(lines + [c["chapter_title"] for c in model["chapters"][len(lines):]]) + "\n").encode("utf-8"))
    registry = pipeline / "filters/filters.json"
    if not registry.exists():
        write_json(registry, {"filters": [{"order": i, "name": name, "agent": f".framework/filters/{name}/SKILL.md", "autorun": True} for i, name in enumerate(chain, 1)]})
    prompt = pipeline / "override.txt"
    if not prompt.exists():
        atomic_bytes(prompt, b"No transform required.\n")
    # Override filter.md remains lazy; existing human instructions are untouched.
    sync_progress(pipeline)
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
