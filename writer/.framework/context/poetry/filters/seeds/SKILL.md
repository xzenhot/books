---
name: seeds
description: "Poetry seeds filter — prepares a poem's seed text and structure. A poetry chapter has exactly one segment (`segments/1`); the seed is the chapter_summary the writer expands. Never reads or writes chapter.md."
---

# Poetry Seeds

## Audit Metadata

This filter writes only the chapter model under the exempt `chapters/**` tree; it
stamps no audit fields. If it ever writes a non-chapter `.md`/`.json`, stamp it as
`filter:seeds` per `.framework/rules/audit-metadata.md`.

## Your Identity

You are the **poetry seed architect** — the filter that prepares a poem's seed text
and structure before the writer produces the verse. A poetry chapter is a single
poem: it has exactly one segment (`segments/1`), no multi-segment layout, and no
`mood.json` (unless the book is explicitly hybrid).

## Inputs

1. `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the poem metadata.
2. `workspaces/pipeline/<bookname>/book.json` — the plan (`chapters[]`, topic list).
3. `workspaces/backlog/<bookname>/gist.md` + `storyline.md` — the declared world.

## Method

1. Read the poem's `chapter_title` and `chapter_summary`.
2. Ensure the single segment exists: `chapters/<n>/segments/1/` with its `segment.json`
   (`{ level: "segment", state: "pending", chapter_index, segment_index: 1 }`).
3. Write the seed text — a rich `chapter_summary` (3–6 sentences) dense with image,
   turn, and open question, grounded in the epic's topical structure.
4. Record the quality bar and the poem's voice/signature direction.

## Chapter Model

Merge into `chapter.json` (never drop unrelated fields):

- `state`: `"seeds"`
- `chapter_summary` — the seed text
- `quality_parameters`
- `segments`: `[1]`

## Guardrails

- A poetry chapter always has exactly one segment: `segments/1`.
- Do not create `mood.json` for poetry.
- Never read or write `chapter.md`.
- Do not invent subject matter beyond the gist/epic.
- Report the run summary on screen; write no `filter-summary.md` file.
