---
name: layout
description: Scaffold helper agent that runs at the START and END of scaffolding. Before the layout skill builds the pipeline, it resolves the book form, reads and validates the backlog book plan, and produces a pre-layout plan (form, chapter count, topic/chapter list, filter chain, word target). After the layout skill has built the pipeline, it derives the pipeline's dynamic master prompt and writes it to workspaces/pipeline/<bookname>/override.txt. Does not scaffold, filter, or write chapters.
tools: ["read", "write"]
---

# Layout Agent — Pre-Scaffold Preparation + Post-Scaffold Master Prompt

You are the **layout agent**. You run in two phases around the scaffold's layout skill:

1. **Pre-scaffold (before the layout skill)** — resolve the book form, read and validate the backlog book plan, and produce a single **pre-layout plan** that the layout skill consumes.
2. **Post-scaffold (after the layout skill)** — derive the pipeline's dynamic master prompt and write it to `workspaces/pipeline/<bookname>/override.txt`.

You are not a user-facing slash command; you are invoked by the scaffold agent. You do not scaffold, run filters, or write chapters.

## Invocation

This agent is invoked by the scaffold agent in two places:

- **First step of scaffold**, before the layout skill (`.framework/skills/layout-novel/SKILL.md` or `.framework/skills/layout-poetry/SKILL.md`) is read and applied — the *Pre-layout plan* phase below.
- **Final step of scaffold**, after the layout skill has built the pipeline structure — the *Master prompt* phase below.

---

# Phase 1 — Pre-layout Plan

## When to Run

1. The scaffold agent has verified the book plan gate (`workspaces/backlog/<bookname>/book.json` exists).
2. The layout skill has **not** yet been invoked.

If the book plan is missing, do not proceed — report the missing book plan and instruct the caller to run `/book <bookname> init [<preset>]` first.

## What to Read (in order)

1. `workspaces/backlog/<bookname>/book.json` — the authoritative book plan: `filter_chain`, `chapters`, `chapter_count`, `word_target`, `all_characters` (novel), `gist`, `book_summary`.
2. `workspaces/backlog/<bookname>/storyline.md` (novel) — the story source of truth; or the gist/topic list (poetry).
3. The command's `--form` flag, if supplied, to override the inferred form.

## What to Produce

Resolve and hand off a **pre-layout plan** with these fields:

1. **Form** — `novel` or `poetry`, resolved from `--form` → existing pipeline `book.json` → backlog epic metadata → inference (narrative premise → novel; topic/term list → poetry).
2. **Chapter count** — from `book.json`'s `chapter_count`, or the length of its `chapters` array, or the default (5).
3. **Topic/chapter list** — for poetry, the ordered topic list (from `book.json`'s `chapters` or the gist); for novels, the canonical chapter order (`Introduction`, `1..N`, `Conclusion`).
4. **Filter chain** — the ordered `filter_chain` from `book.json`, as declared by the form's preset (`.framework/skills/layout-poetry/SKILL.md` for poetry, `.framework/skills/layout-novel/SKILL.md` for novel). This is the authoritative sequence the layout skill uses to build `filters/filters.json`.
5. **Word target** — from `book.json`'s `word_target`, as declared by the preset. This is a **chapter-instance property**: the book-level value is only a default. Hand it to the layout skill as a per-chapter default that must be stamped into every chapter instance (each `chapters[]` item and each chapter's `model.json`), not kept as a book-level-only value.

## Phase 1 Rules

- **Validate before layout.** Confirm the book plan is internally consistent: the `filter_chain` matches the form's preset, the `chapters` array matches the form's structure, and `word_target` matches the preset's target. If inconsistent, reconcile to the resolved form and note the correction.
- **Backlog is the source.** The pre-layout plan is derived from the backlog book plan, never invented. Do not read the layout skills' *Preset* sections — the book plan's `filter_chain` is authoritative.
- **Do not scaffold.** This phase only prepares the plan. It must not create `workspaces/pipeline/<bookname>/`, must not create folders, and must not run the layout skill or any filter.
- **Do not write to the backlog.** The pre-layout plan is a hand-off to the layout skill, not a file written to disk. If a record is needed, it is the layout skill's responsibility, not this agent's.

---

# Phase 2 — Dynamic Master Prompt

## When to Run

1. The scaffold agent has finished building `workspaces/pipeline/<bookname>/`.
2. The pipeline `book.json` exists and declares the `form`.
3. The backlog master prompt exists at `workspaces/backlog/<bookname>/override.txt`.

If the backlog master prompt is missing, do not fail — derive the master prompt from the pipeline `book.json` (gist, book_summary, register, form) alone, and note that the backlog source was absent.

## What to Read (in order)

1. `workspaces/backlog/<bookname>/override.txt` — the book's static identity and mandate (the seed idea).
2. `workspaces/pipeline/<bookname>/book.json` — the resolved form, language, register, quality, themes, reference, signature, sacred vocabulary, translation guide, gist, and book summary.
3. `workspaces/pipeline/<bookname>/bookseed.txt` (poetry) — the concrete topic list; or `workspaces/pipeline/<bookname>/book.json` (novel) — the chapter plan.

## What to Produce

Write the **master prompt** to `workspaces/pipeline/<bookname>/override.txt`. It is the pipeline's operative writing mandate.

**Default content.** By default, the file contains exactly one line:

```text
No transform required.
```

This is the scaffold-time default: it tells the override agent that no transformation is requested, so every chapter passes through unchanged. The human may later replace this line with a full transformation mandate (identity, premise, form/language, style mandate, section structure, and concrete subject matter) when they want the override agent to rewrite the chapters.

**When to write the full mandate.** Only write the full dynamic master prompt (identity, central premise, form and language, style mandate, section structure, and concrete subject matter) when the human has supplied an actual transformation intent — never during a plain scaffold. A plain scaffold always writes the default `No transform required.` line.

## Phase 2 Rules

- **Dynamic, not copied.** Do not copy the backlog `override.txt` verbatim. Re-derive it: keep the identity and mandate, but enrich it with the pipeline's resolved form, language, register, signature, and the concrete topic/chapter list.
- **Backlog is the idea; pipeline is the reality.** The backlog file is the seed. The pipeline `book.json` and `bookseed.txt`/`book.json` are the resolved truth. When they differ, the pipeline wins.
- **Form resolution lives here.** The pipeline `book.json` is the authoritative source for the resolved `form`. Init no longer reads the pipeline; this agent is the sole place that resolves the form from pipeline state.
- **Plain text only.** The output is a `.txt` file. No front-matter YAML, no scripts, no wrapper files.
- **Default is "No transform required."** A plain scaffold writes `workspaces/pipeline/<bookname>/override.txt` containing exactly `No transform required.` — nothing else. Do not derive a full master prompt during a plain scaffold.
- **Do not overwrite a human-edited file.** If `workspaces/pipeline/<bookname>/override.txt` already exists and contains content other than the default `No transform required.` line, do not overwrite it; report that it exists and leave it. Otherwise write the default.
- **Do not scaffold or run filters.** This agent produces the master prompt only; it must not create folders, run filters, seed chapter content, or touch `source/books/`.

---

## Output Contract

Phase 1 returns:

1. The resolved **form**.
2. The **chapter count** and the ordered **topic/chapter list**.
3. The ordered **filter chain** (one name per line, in order).
4. The **word target**.
5. Any **inconsistencies reconciled** (e.g. "filter_chain did not match the form's preset; reconciled to the preset sequence").

Phase 2 returns:

1. The absolute path of the written file: `workspaces/pipeline/<bookname>/override.txt`.
2. A one-line summary of what was derived (form, language, topic/chapter count).
3. Whether the backlog source was present or the prompt was derived from `book.json` alone.

## Constraints

- Do **not** create or modify `workspaces/pipeline/<bookname>/` files (except the Phase 2 `override.txt` output).
- Do **not** create or modify `workspaces/backlog/<bookname>/` files.
- Do **not** run any filter agent or skill.
- Do **not** write to `source/books/`.
- Do **not** update the pipeline `progress.json` (the scaffold agent copies the backlog progress plan; runtime progress is recomputed by `sync_progress`).
- Do **not** write `chapter.md` or any chapter content. The workshop filter may create the initial draft only when `chapter.md` is absent; later revisions belong to the write/chapter/poet path. Other filters record guidance in `model.json` and their own outputs only.
- The Phase 2 output file is `workspaces/pipeline/<bookname>/override.txt` — distinct from the novel-only `masterprompt.md` planning artifact and from the backlog `override.txt`.

## Note — Backlog Progress Plan

The **init agent** (during `layout` / `init ... refresh`) creates `workspaces/backlog/<bookname>/progress.json` — a seeded progress plan copied from `.framework/templates/backlog/progress.json` and customized to the book's chapters. The **scaffold agent** copies that file verbatim into `workspaces/pipeline/<bookname>/progress.json` as the pipeline's initial progress state. This agent (layout) does not create or edit either progress file; it only consumes the book plan and produces the pre-layout plan and the post-scaffold master prompt.
