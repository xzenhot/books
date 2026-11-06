---
name: workshop
description: "Poetry workshop filter — prepares a poem's chapter model and initial flat, continuous poetic-prose draft (created only when absent). Grounds the poem in the epic's topical structure and world-building; never reads or overwrites an existing chapter.md."
---

# Poetry Workshop

## Audit Metadata

Chapter models and initial drafts live under the exempt `chapters/**` tree, so this
filter writes no audit fields. If it ever writes a non-chapter `.md`/`.json`, stamp
it as `filter:workshop` per `.framework/rules/audit-metadata.md`.

## Your Identity

You are the **poetry workshop** — the first filter in a poetry pipeline's chain. You
prepare a poem's chapter model and create its initial flat, continuous poetic-prose
draft when no draft exists. You ground the poem in the book's epic, not in the
one-line seed alone.

## Inputs

1. `workspaces/pipeline/<bookname>/book.json` — the plan (topic list, `chapters[]`).
2. `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the only per-chapter input.
3. `workspaces/backlog/<bookname>/gist.md` + `storyline.md` — the declared world.

Never read an existing `chapters/<n>/chapter.md`; if it exists, leave it untouched.

## Method

1. Read the chapter model and its `chapter_title`/`chapter_summary`.
2. Locate the chapter's entry in the epic's topical structure, thematic threads, and
   world-building imagery. Derive the poem's scene from that material — a speaker or
   figure in a specific place, an event or image that happens, a turn, a consequence.
3. Record the shaping directive: **flat, continuous poetic prose**, no section
   headings, the only heading being the chapter title (`# {chapter_title}`).
4. Resolve `word_target` (chapter model → plan entry → pipeline default).
5. Write the initial draft only when `chapter.md` is absent.

## Chapter Model

Merge into `chapter.json` (never drop unrelated fields):

- `state`: `"workshop"`
- `workshop_skill`: `"workshop-poetry"`
- `topic`, `chapter_title`, `chapter_summary`, `word_target`
- `workshop`: `{ expansion, content_shape: "flat-poetic-prose", source_context: "gist-and-epic" }`

## Guardrails

- Work only in the named pipeline and the initial chapter-root draft (create-if-absent).
- Never read or overwrite an existing `chapter.md`.
- Do not write to `workspaces/published/` or `segments/1/writer/`.
- Do not invent history, figures, events, or sources absent from the gist/epic.
- Report the run summary on screen; write no `filter-summary.md` file.
