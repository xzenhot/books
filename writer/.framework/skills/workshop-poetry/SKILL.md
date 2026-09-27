---
name: workshop-poetry
description: Expand a poetry chapter seed into chapter-model guidance and an initial live chapter draft. Workshop creates chapter.md only when absent and never reads or overwrites an existing draft.
---

# Poetry Workshop

Use this skill for a poetry pipeline after scaffold and before research or later filters. It prepares the chapter model and creates the initial poem draft when no draft exists.

## Inputs

Read, in order:

1. The pipeline book plan (cloned from the backlog):
   - .space/pipeline/<bookname>/book.json
2. The matching chapter model (the only per-chapter input):
   - .space/pipeline/<bookname>/chapters/<n>/chapter.json
3. The backlog sources:
   - .space/backlog/<bookname>/gist.md
   - .space/backlog/<bookname>/storyline.md

Never read an existing `.space/pipeline/<bookname>/chapters/<n>/chapter.md`. If it already exists, leave it untouched. The initial draft may be created only when the file is absent.

The chapter_summary is the seed, not the finished work. The epic is the primary source of truth: derive every chapter's guidance from the epic's premise, setting, thematic threads, topical structure, and world-building, so each poem is grounded in the book's full narrative foundation rather than the one-line seed alone. Use the gist for the high concept and the epic for the concrete material. Do not invent historical claims, figures, events, or sources that are absent from those inputs.

## Story Requirement

Record guidance so the authored chapter carries at least a basic story, not a bare meditation. A story means a concrete movement: a speaker or figure in a specific place and time, an event or image that happens, a turn or change, and a consequence that lands. Ground it in the epic's topical structure and world-building — the ridge, the vanished river, the volcanic fire, the dynasties, the woman who is Delhi — so the poem reads as a scene with a beginning, a middle, and an end, not a list of abstractions. This guidance is the foundation the writer uses, so it must be substantial enough to survive the later filter chain (research, correctness, theme, syntax, override, quality).

## Shaping Contract

Record the shaping directive for the authored chapter: **flat, continuous poetic prose** — no `## Question`, `## Oration`, or `## Benediction` headings, merged into continuous paragraphs, the only permitted heading being the chapter title (`# {chapter_title}`). The initial draft should enact this shape.

Keep the chapter title and topic. Direct that the prose open with the chapter's central tension, carry the substantive image, context, movement, and reflection, and close with an earned consequence, opening, or responsibility. Do not add novel-only sections and do not force a signature or subject that the chapter metadata does not support.

## Word Target

Resolve the target from chapter model word_target first, then the matching book plan entry, then the pipeline model default. The target is authoritative and is recorded in the model. The initial workshop draft is a starting point for later filters and writer revision; do not claim a measured count unless one is actually measured.

## Metadata And Files

Merge into the existing chapter model without dropping unrelated fields:

- state: workshop
- workshop_skill: workshop-poetry
- chapter_name and chapter_title
- topic
- chapter_summary
- word_target
- workshop: { expansion: <story/shaping guidance>, content_shape: flat-poetic-prose, source_context: gist-and-epic }
- source_context: gist-and-epic

If `chapter.md` is absent, write a basic flat, continuous poetic-prose draft from the chapter model and workshop guidance, without section headings. If it already exists, do not read or modify it. This is an initial working draft, not final output; later writing agents may revise it under the version-before-overwrite contract.

Preserve chapter_index, level, segments, and all existing runtime fields.

## Epic Grounding

Before expanding a chapter, read `.space/backlog/<bookname>/storyline.md` in full and locate the material that belongs to this chapter: its entry in the topical structure, the relevant thematic threads, and the world-building images that fit the chapter's subject. Extend the chapter from that material so the poem is recognizably part of the book's larger narrative arc. If the epic has no direct entry for a chapter, derive the story from the epic's premise, setting, and recurring images rather than from the seed alone. The resulting draft must be substantial enough to serve as the input for the full filter chain (research, correctness, theme, syntax, override, quality) that prepares it for publish.

Write one run summary to .space/pipeline/<bookname>/filters/workshop/filter-summary.md. Include the processed chapters, target word counts, and any grounding limitation. Report measured word count only when actually measured. Do not write runtime content into other filter folders.

## Guardrails

- Work only in the named pipeline, its chapter history, and the initial chapter-root draft when creating it for the first time.
- Do not create or modify source/books.
- Do not run research, correctness, theme, syntax, override, or quality.
- Do not place writer output in segments/1/writer; that is a later stage.
- Preserve human-edited chapter content; never replace an existing chapter-root draft.
- The result must remain a poetry draft even when the book's subject is historical, political, ecological, or philosophical.