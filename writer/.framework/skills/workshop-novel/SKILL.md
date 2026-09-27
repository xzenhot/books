---
name: workshop-novel
description: Expand a novel chapter seed into expansion and shaping guidance recorded in the chapter model. The workshop filter never reads or writes chapter.md — prose is authored only later by the write/chapter/poet path.
---

# Novel Workshop

Use this skill for a novel pipeline after scaffold and before research or later filters. It prepares the chapter model for authoring; it does not write the chapter.

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

Never read `.space/pipeline/<bookname>/chapters/<n>/chapter.md` — it is an output file owned by the write path.

The epic is the story source of truth. Use the gist only to orient the premise. Do not invent characters, events, history, or outcomes beyond the epic and available research.

## Shaping Contract

Record the shaping directive for the authored chapter: **flat, continuous prose** — no `## Workshop`, `## Story`, or `## Discussion` headings, merged into continuous paragraphs, the only permitted heading being the chapter title (`# {chapter_title}`). The writer enacts this; the workshop filter only records it.

Direct that the prose open with the chapter's central question, carry the continuous historical or fictional narrative drawn from the epic, and close with a meaningful handoff to the next chapter. Preserve the chapter title and canonical order. Do not use poetry-only sections.

## Word Target

Resolve the target from chapter model word_target first, then the matching book plan entry, then the pipeline model default. The target is authoritative and is recorded for the writer; the writer measures and retains it in `word_count` after authoring. The workshop filter writes no prose, so it never records a measured count.

## Metadata And Files

Merge into the existing chapter model without dropping unrelated fields:

- state: workshop
- workshop_skill: workshop-novel
- chapter_name and chapter_title
- chapter_summary
- word_target
- workshop: { expansion: <story/shaping guidance>, content_shape: flat-prose, source_context: epic-and-research }
- source_context: epic-and-research

Preserve chapter_index, level, segments, and all existing runtime fields. Write nothing to `chapter.md`.

Write one run summary to .space/pipeline/<bookname>/filters/workshop/filter-summary.md. Include the processed chapters, word targets, source grounding, and any unresolved research need. Do not write runtime content into other filter folders.

## Guardrails

- Work only in the named pipeline and its chapter models.
- Do not create or modify source/books.
- Do not run research, correctness, theme, syntax, override, or quality.
- Do not place writer output in segments/1/writer; that is a later stage.
- The result must remain a prose narrative with a continuous story.