#!/usr/bin/env python3
"""Verify a scaffolded book pipeline against its backlog book plan.

Implements the scaffold contract of `.framework/workflows/pipeline.md`
(step 12: "Verify the model contract before completing scaffold"):

    python tools/verify_pipeline.py <bookname>

Checks: root `book.json` equals the backlog plan as parsed JSON; every plan
chapter has a matching `chapter.json` carrying all source fields; `history/`
and the configured segment folders and state files exist; form invariants hold
(poetry: no `mood.json`); `filters/filters.json` mirrors the plan's
`filter_chain` order with resolvable agents and boolean `autorun` flags; and
the root planning files (`progress.json`, `override.md`) exist and match.

Exit code 0 means the pipeline matches the contract; 1 means at least one error.
"""

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()
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

    backlog = os.path.join(ROOT, "workspaces", "backlog", bookname)
    pipeline = os.path.join(ROOT, "workspaces", "pipeline", bookname)
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
    # The clone is compared ignoring audit fields, per `.framework/rules/audit-metadata.md`.
    audit = ("updated_by", "updated_date", "updated_at")
    if {k: v for k, v in plan.items() if k not in audit} != {k: v for k, v in model.items() if k not in audit}:
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
        segment_count = entry.get("segment_count", 1) if form == "poetry" else 1
        if type(segment_count) is not int or segment_count < 1:
            errors.append(f"chapters/{name} segment_count must be a positive integer")
            segment_count = 1
        if chapter_model.get("segment_count", segment_count) != segment_count:
            errors.append(
                f"chapters/{name}/chapter.json segment_count does not match the plan"
            )
        segment_plans = chapter_model.get("segments")
        legacy_single_segment = segment_count == 1 and segment_plans == [1]
        if segment_plans not in (None, []) and not legacy_single_segment:
            if not isinstance(segment_plans, list) or len(segment_plans) != segment_count:
                errors.append(
                    f"chapters/{name}/chapter.json segments must contain "
                    f"{segment_count} records after enrichment"
                )
            elif any(
                not isinstance(segment, dict)
                or segment.get("segment_index") != position
                or segment.get("name") != str(position)
                for position, segment in enumerate(segment_plans, 1)
            ):
                errors.append(
                    f"chapters/{name}/chapter.json segments have invalid identities"
                )
        if not os.path.isdir(os.path.join(chapter_dir, "history")):
            errors.append(f"missing chapters/{name}/history/")
        segments_root = os.path.join(chapter_dir, "segments")
        expected_segments = {str(i) for i in range(1, segment_count + 1)}
        actual_segments = {
            entry_name for entry_name in os.listdir(segments_root)
            if os.path.isdir(os.path.join(segments_root, entry_name))
            and entry_name.isdecimal()
        } if os.path.isdir(segments_root) else set()
        for extra in sorted(actual_segments - expected_segments, key=int):
            errors.append(f"unexpected segment folder: chapters/{name}/segments/{extra}/")
        for segment_name in sorted(expected_segments, key=int):
            segment_dir = os.path.join(segments_root, segment_name)
            if not os.path.isdir(segment_dir):
                errors.append(f"missing chapters/{name}/segments/{segment_name}/")
                continue
            segment_model_path = os.path.join(segment_dir, "segment.json")
            if not os.path.isfile(segment_model_path):
                # Fall back to legacy segment model.json for pipelines scaffolded before the rename.
                legacy_path = os.path.join(segment_dir, "model.json")
                if os.path.isfile(legacy_path):
                    segment_model_path = legacy_path
            if not os.path.isfile(segment_model_path):
                errors.append(f"missing chapters/{name}/segments/{segment_name}/segment.json")
            else:
                segment = load(segment_model_path)
                if (segment.get("level") != "segment" or segment.get("chapter_index") != index
                        or segment.get("segment_index") != int(segment_name)):
                    errors.append(
                        f"chapters/{name}/segments/{segment_name}/segment.json identity fields are wrong"
                    )
                if isinstance(segment_plans, list) and len(segment_plans) == segment_count:
                    plan_segment = segment_plans[int(segment_name) - 1]
                    for key in ("segment_title", "segment_summary", "word_target"):
                        if key in plan_segment and segment.get(key) != plan_segment[key]:
                            errors.append(
                                f"chapters/{name}/segments/{segment_name}/segment.json "
                                f"{key} differs from chapter.json"
                            )
            for sub in ("writer", "editor", "translator", "latest", "version"):
                if not os.path.isdir(os.path.join(segment_dir, sub)):
                    errors.append(
                        f"missing chapters/{name}/segments/{segment_name}/{sub}/"
                    )
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

    for name in ("progress.json", "override.md"):
        if not os.path.isfile(os.path.join(pipeline, name)):
            errors.append(f"missing pipeline root file: {name}")

    if form == "poetry":
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

    if os.path.isdir(os.path.join(ROOT, "workspaces", "published", bookname)):
        notes.append("workspaces/published/<bookname> exists (scaffold must not create it)")

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
        sys.exit("Usage: python tools/verify_pipeline.py <bookname>")
    sys.exit(verify(sys.argv[1]))
