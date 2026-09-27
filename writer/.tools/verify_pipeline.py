#!/usr/bin/env python3
"""Verify a scaffolded book pipeline against its backlog book plan.

Implements the scaffold contract of `.framework/workflows/pipeline.md`
(step 12: "Verify the model contract before completing scaffold"):

    python .tools/verify_pipeline.py <bookname>

Checks: root `model.json` equals the backlog `book.json` as parsed JSON; every
plan chapter has a matching `chapters/<name>/model.json` carrying all source
fields with identical values and types plus runtime metadata; `history/` and a
complete `segments/1/` state exist; form invariants hold (poetry: no
`mood.json`); `filters/filters.json` mirrors the plan's `filter_chain` order
with resolvable agents and boolean `autorun` flags; and the root planning files
(`bookseed.txt`, `progress.json`, `override.txt`) exist and match the plan.

Exit code 0 means the pipeline matches the contract; 1 means at least one error.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def verify(bookname: str) -> int:
    errors: list[str] = []
    notes: list[str] = []

    backlog = os.path.join(ROOT, ".space", "backlog", "epic", bookname)
    pipeline = os.path.join(ROOT, ".space", "pipeline", bookname)
    plan_path = os.path.join(backlog, "book.json")
    model_path = os.path.join(pipeline, "book.json")
    if not os.path.isfile(model_path):
        model_path = os.path.join(pipeline, "model.json")

    if not os.path.isfile(plan_path):
        sys.exit(f"ERROR: backlog book plan missing: {plan_path}")
    if not os.path.isfile(model_path):
        sys.exit(f"ERROR: pipeline book plan (book.json) missing: {model_path}")

    plan = load(plan_path)
    model = load(model_path)
    if plan != model:
        errors.append("root book.json does not equal backlog book.json as parsed JSON")
    with open(plan_path, "rb") as handle:
        plan_bytes = handle.read()
    with open(model_path, "rb") as handle:
        model_bytes = handle.read()
    if plan_bytes != model_bytes:
        notes.append("root book.json is JSON-equal but not byte-identical to the backlog book.json")

    form = plan.get("form")
    chapters = plan.get("chapters", [])
    if plan.get("chapter_count") != len(chapters):
        errors.append("chapter_count does not match the chapters array length")

    chapters_dir = os.path.join(pipeline, "chapters")
    for entry in chapters:
        name = entry.get("name")
        index = entry.get("chapter_index")
        if name != str(index):
            errors.append(f"plan entry mismatch: name={name!r} chapter_index={index!r}")
            continue
        chapter_dir = os.path.join(chapters_dir, str(name))
        chapter_model_path = os.path.join(chapter_dir, "chapter.json")
        if not os.path.isfile(chapter_model_path):
            chapter_model_path = os.path.join(chapter_dir, "model.json")
        if not os.path.isfile(chapter_model_path):
            errors.append(f"missing chapters/{name}/chapter.json")
            continue
        chapter_model = load(chapter_model_path)
        for key, value in entry.items():
            if key not in chapter_model:
                errors.append(f"chapters/{name}/chapter.json missing source field {key!r}")
            elif chapter_model[key] != value:
                errors.append(f"chapters/{name}/chapter.json field {key!r} differs from the plan")
            elif type(chapter_model[key]) is not type(value):
                errors.append(f"chapters/{name}/chapter.json field {key!r} has a different type")
        if chapter_model.get("level") != "chapter":
            errors.append(f"chapters/{name}/chapter.json level must be 'chapter'")
        if chapter_model.get("segments") != [1]:
            errors.append(f"chapters/{name}/chapter.json segments must be [1]")
        if not os.path.isdir(os.path.join(chapter_dir, "history")):
            errors.append(f"missing chapters/{name}/history/")
        segment_dir = os.path.join(chapter_dir, "segments", "1")
        segment_model_path = os.path.join(segment_dir, "model.json")
        if not os.path.isfile(segment_model_path):
            errors.append(f"missing chapters/{name}/segments/1/model.json")
        else:
            segment = load(segment_model_path)
            if (segment.get("level") != "segment" or segment.get("chapter_index") != index
                    or segment.get("segment_index") != 1):
                errors.append(f"chapters/{name}/segments/1/model.json identity fields are wrong")
        for sub in ("writer", "editor", "translator", "version"):
            if not os.path.isdir(os.path.join(segment_dir, sub)):
                errors.append(f"missing chapters/{name}/segments/1/{sub}/")
        if form == "poetry":
            if os.path.exists(os.path.join(chapter_dir, "mood.json")):
                errors.append(f"poetry chapter {name} must not have mood.json")
            if os.path.exists(os.path.join(chapter_dir, "chapter.md")):
                notes.append(f"chapters/{name}/chapter.md exists (write/poet path owns it)")
        elif not os.path.isfile(os.path.join(chapter_dir, "chapter.md")):
            errors.append(f"novel chapter {name} is missing chapter.md")

    if os.path.isdir(chapters_dir):
        expected = [str(entry["name"]) for entry in chapters]
        existing = sorted(d for d in os.listdir(chapters_dir) if os.path.isdir(os.path.join(chapters_dir, d)))
        for extra in [d for d in existing if d not in expected]:
            errors.append(f"unexpected chapter folder: chapters/{extra}/")
        for missing in [d for d in expected if d not in existing]:
            errors.append(f"missing chapter folder: chapters/{missing}/")

    if isinstance(plan.get("filter_chain"), list) and plan["filter_chain"] and isinstance(plan["filter_chain"][0], dict):
        chain = [entry.get("name") for entry in plan["filter_chain"]]
    else:
        chain = plan.get("filter_chain", [])

    registry_path = os.path.join(pipeline, "filters", "filters.json")
    if not os.path.isfile(registry_path):
        errors.append("missing filters/filters.json")
    else:
        registry = load(registry_path)
        entries = registry.get("filters", [])
        names = [entry.get("name") for entry in entries]
        if names != chain:
            errors.append(f"registry order {names} does not match the plan filter_chain {chain}")
        for position, entry in enumerate(entries, 1):
            if entry.get("order") != position:
                errors.append(f"registry entry {entry.get('name')} has order {entry.get('order')}, expected {position}")
            agent = str(entry.get("agent", ""))
            if not agent or not os.path.isfile(os.path.join(ROOT, agent.replace("/", os.sep))):
                errors.append(f"registry entry {entry.get('name')} points at a missing agent: {agent!r}")
            if not isinstance(entry.get("autorun"), bool):
                errors.append(f"registry entry {entry.get('name')} autorun must be a boolean")
        filters_dir = os.path.join(pipeline, "filters")
        folders = sorted(d for d in os.listdir(filters_dir) if os.path.isdir(os.path.join(filters_dir, d)))
        if folders:
            notes.append("filter folders exist at scaffold (spec: created lazily on first run): " + ", ".join(folders))

    for name in ("bookseed.txt", "progress.json", "override.txt"):
        if not os.path.isfile(os.path.join(pipeline, name)):
            errors.append(f"missing pipeline root file: {name}")

    if form == "poetry":
        seed_path = os.path.join(pipeline, "bookseed.txt")
        if os.path.isfile(seed_path):
            with open(seed_path, encoding="utf-8") as handle:
                topics = [line.strip() for line in handle if line.strip()]
            if topics != [entry["chapter_title"] for entry in chapters]:
                errors.append("bookseed.txt topics do not match the plan chapter titles")
        progress_path = os.path.join(pipeline, "progress.json")
        if os.path.isfile(progress_path):
            progress = load(progress_path)
            if progress.get("total_chapters") != len(chapters):
                errors.append("progress.json total_chapters does not match the plan")
            if progress.get("completed_chapters") != 0 or progress.get("current_chapter") != 1:
                errors.append("progress.json must start with 0 completed chapters at chapter 1")
            numbers = [item.get("chapter_number") for item in progress.get("chapters", [])]
            if numbers != [entry["chapter_index"] for entry in chapters]:
                errors.append("progress.json chapter numbers do not match the plan")
            for item in progress.get("chapters", []):
                if item.get("status") != "pending" or item.get("completed_date") is not None:
                    errors.append(f"progress.json chapter {item.get('chapter_number')} is not pending/null")
                if not str(item.get("category", "")).strip():
                    notes.append(f"progress.json chapter {item.get('chapter_number')} has an empty category")

    if os.path.isdir(os.path.join(ROOT, "source", "books", bookname)):
        notes.append("source/books/<bookname> exists (scaffold must not create it)")

    print(f"book: {bookname} | form: {form} | chapters: {len(chapters)}")
    print(f"filter chain: {' -> '.join(chain)}")
    for note in notes:
        print(f"NOTE: {note}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: pipeline matches the backlog book plan and the scaffold contract.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python .tools/verify_pipeline.py <bookname>")
    sys.exit(verify(sys.argv[1]))
