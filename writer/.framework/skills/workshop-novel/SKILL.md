---
name: workshop-novel
description: Expand a novel chapter seed into chapter-model guidance and an initial live chapter draft. Workshop creates chapter.md only when absent and never reads or overwrites an existing draft.
---

# Novel Workshop

Use this skill for a novel pipeline after scaffold and before research or later filters. It prepares the chapter model and creates the initial chapter draft when no draft exists.

## Inputs

Read, in order:

1. The pipeline book plan (cloned from the backlog):
   - .space/pipeline/<bookname>/book.json
2. The matching chapter model (the only per-chapter input):
   - .space/pipeline/<bookname>/chapters/<n>/chapter.json
3. The novel backlog source:
   - .space/backlog/<bookname>/storyline.md
   - .space/backlog/<bookname>/gist.md
4. Any available upstream research and seed files in the pipeline.

Never read an existing `.space/pipeline/<bookname>/chapters/<n>/chapter.md`. If it already exists, leave it untouched. The initial draft may be created only when the file is absent.

The epic is the story source of truth. Use the gist only to orient the premise. Do not invent characters, events, history, or outcomes beyond the epic and available research.

## Shaping Contract

Record the shaping directive for the authored chapter: **flat, continuous prose** — no `## Workshop`, `## Story`, or `## Discussion` headings, merged into continuous paragraphs, the only permitted heading being the chapter title (`# {chapter_title}`). The prose should enact this shape in the initial draft.

Direct that the prose open with the chapter's central question, carry the continuous historical or fictional narrative drawn from the epic, and close with a meaningful handoff to the next chapter. Preserve the chapter title and canonical order. Do not use poetry-only sections.

## Word Target

Resolve the target from chapter model word_target first, then the matching book plan entry, then the pipeline model default. The target is authoritative and is recorded in the model. The initial workshop draft is a starting point for later filters and writer revision; do not claim a measured count unless one is actually measured.

## Metadata And Files

Merge into the existing chapter model without dropping unrelated fields:

- state: workshop
- workshop_skill: workshop-novel
- chapter_name and chapter_title
- chapter_summary
- word_target
- workshop: { expansion: <story/shaping guidance>, content_shape: flat-prose, source_context: epic-and-research }
- source_context: epic-and-research

Preserve chapter_index, level, segments, and all existing runtime fields. If `chapter.md` is absent, write a basic flat-prose draft using only the chapter model and workshop guidance, with no section headings. If it already exists, do not read or modify it. This is an initial working draft, not final output; later writing agents may revise it under the version-before-overwrite contract.

Write one run summary to .space/pipeline/<bookname>/filters/workshop/filter-summary.md. Include the processed chapters, word targets, source grounding, and any unresolved research need. Do not write runtime content into other filter folders.

## Guardrails

- Work only in the named pipeline, its chapter models, and the initial chapter-root draft when creating it for the first time.
- Do not create or modify source/books.
- Do not run research, correctness, theme, syntax, override, or quality.
- Do not place writer output in segments/1/writer; that is a later stage.
- The result must remain a prose narrative with a continuous story.