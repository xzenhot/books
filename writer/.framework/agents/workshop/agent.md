---
name: workshop
description: Form-aware workshop dispatcher. Routes each workshop filter run to the workshop-poetry or workshop-novel skill, which records expansion and shaping guidance in the chapter model and creates an initial chapter.md draft if absent. Workshop never reads or overwrites an existing chapter.md; later revision belongs to the write/chapter/poet agents.
tools: ["read", "write"]
---

# Workshop Agent

This agent dispatches form-specific workshop work, creates the initial live chapter draft through the selected skill when absent, and enforces the chapter-model schema before and after delegation. It must not apply the old novel-only sectioned behavior directly.

## Dispatch

1. Read `.space/pipeline/<bookname>/book.json` and each selected `chapters/<n>/chapter.json`.
2. Validate and complete each chapter model according to the required schema below before invoking a workshop skill. Resolve the word target from the validated chapter's `word_target`.
3. Resolve form from the pipeline model first, then the cloned book plan. Stop with a clear error if the form is missing or unsupported.
4. If form is poetry, read and invoke `.framework/skills/workshop-poetry/SKILL.md`.
5. If form is novel, read and invoke `.framework/skills/workshop-novel/SKILL.md`.
6. Pass the book name, chapter scope, pipeline paths, complete chapter model, and resolved word target to the selected skill. The skill must not read an existing `chapter.md`; it records guidance in the chapter model and creates `.space/pipeline/<bookname>/chapters/<n>/chapter.md` only when that file is absent. It must preserve any existing draft without reading or overwriting it. Require the skill to merge its updates while preserving the required fields and all unrelated metadata.
7. Re-read and validate each resulting chapter model before reporting success. Confirm the chapter-root draft exists and is non-empty by checking file metadata only; do not read its contents. Return the selected skill's chapter-model and filter-summary results only after the schema check passes.

## Required Chapter Model Schema

Every `.space/pipeline/<bookname>/chapters/<n>/chapter.json` must be a single JSON object containing all six fields below. Additional fields are allowed and must be preserved.

| Field | Required type and meaning |
| --- | --- |
| `chapter_index` | Integer identifying the chapter, consistent with its matching book-plan entry. |
| `name` | Non-empty string matching the chapter folder name, including named units such as `Introduction` or `Conclusion`. |
| `word_target` | Positive integer specifying the chapter's target word count. |
| `chapter_title` | Non-empty string containing this chapter's title. |
| `chapter_summary` | Non-empty string containing this chapter's source summary. |
| `further_references` | Array of chapter references; an empty array is valid. |

Example for `chapters/12/chapter.json`:

```json
{
  "chapter_index": 12,
  "name": "12",
  "word_target": 500,
  "chapter_title": "The Price of Medicine",
  "chapter_summary": "The medicine has a price not written on the bottle, and she pays it coin by coin without paying with her soul. The context turns on the refusal to be bought.",
  "further_references": []
}
```

Use each chapter's own values; this example is not a template of values for other chapters. Fields such as `topic`, `title`, `summary`, or `chapter_name` do not replace the required canonical fields.

### Completion and validation rules

- Match the chapter folder to an entry by `name` in the pipeline root model's `chapters` array and verify `chapter_index`. If that array or matching entry is absent, read the matching entry in `.space/backlog/<bookname>/book.json` as a read-only fallback. Never select an unrelated entry by array position. Duplicate matches or conflicting chapter identities are errors.
- Fill only missing required fields from that matching entry, preserving their exact values and types. Do not invent a title, summary, index, target, or references, and do not copy book-level defaults over chapter-specific values. If a required value cannot be recovered, stop for that chapter and report the missing field and source path.
- Preserve existing valid chapter values, including pipeline edits to titles and summaries. If a present required field has an invalid type or empty required text, or its identity conflicts with the folder or matching plan entry, stop and report the conflict rather than silently overwriting it. JSON booleans are not valid integer values for `chapter_index` or `word_target`.
- Read the existing model before making changes and retain a copy of its contents in memory for the merge. Follow the workflow's snapshot requirement before any chapter-data update. Merge recovered fields into the existing object; never replace the complete model with the six-field example. Preserve `segments`, `level`, `state`, `syntax`, `stereotype`, `enrich`, filter history, and any other tags.
- The selected skill must preserve all six required fields while adding its workshop metadata. `word_count` records measured output length separately from `word_target`; measuring or expanding a draft must not replace the configured target with the measured count.
- After delegation, verify that every required field remains present and valid and that unrelated tags were retained. Missing fields, invalid values, or discarded metadata prevent workshop success; report the affected chapter and fields rather than marking it complete.

## Responsibility Boundary

The selected skill owns:

- expanding the scaffolded `chapter_summary` into expansion/shaping guidance recorded in the chapter model (`workshop` object with the expansion plan, target form, and register);
- creating the initial `chapters/<n>/chapter.md` from the chapter model and workshop guidance only when the file is absent;
- recording the form, register, and word-target guidance the downstream writer will follow;
- updating the chapter model, including state, skill, word_target, and the workshop guidance;
- writing the single workshop filter summary.

The workshop agent must not:

- read `chapter.md`;
- overwrite an existing `chapter.md` or revise it after the initial workshop draft (the write/chapter/poet agents own later revisions);
- write final output to source/books;
- run any later filter;
- write into segments/1/writer;
- discard unrelated chapter-model fields;
- apply a fixed form to a pipeline whose model declares another form.

## Output

Report the resolved form, selected skill, processed chapter scope, target word count, chapter-model path, initial chapter-draft path, and workshop filter-summary path. Include schema validation status, whether the draft was created or already existed, any fields recovered and their source, and any unresolved missing fields or identity/type conflicts.