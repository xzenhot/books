---
name: layout-poetry
description: "Use when scaffolding or repairing the structural skeleton of a poetry pipeline. Creates workspaces/pipeline/<bookname>/, book.json, progress.json, override.md, named poetry filter folders, and the configured segment folders for each topic. Does not write poem chapters or runtime filter results."
---

# Layout Poetry - Pipeline Scaffold

## Audit Metadata

Every `.md`/`.json` file this skill creates under `workspaces/` must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`; stamp as
the invoking scaffold/layout agent (`scaffold` or `layout`). Targets include
`book.json`, `progress.json`, `characters.json`, `filters/filters.json`,
`masterprompt.md`, and `workshop_metadata.md`. JSON uses root-level keys;
Markdown uses a two-bullet block after the H1. Chapters and
`_history/`/`history/`/`version/` snapshots are exempt.

You are the structural architect for a poetry pipeline. Create only the scaffold and planning artifacts needed before research, filtering, writing, revision, and final assembly begin.

A scaffolded poetry book lives at:

```text
workspaces/pipeline/<bookname>/
```

Finished content later lives at:

```text
workspaces/published/<bookname>/
```

## Source Of Truth

Use this skill together with `.framework/workflows/pipeline.md`. Do not inspect existing book pipelines to discover or imitate layout conventions; existing books may be legacy, experimental, or partially migrated.

Poetry uses these root files as source of truth:

- `book.json` for how to write: form, language, register, quality, themes, reference, index, vocabulary, and translation guide — and for **what** to write: the `chapters[]` array, one entry per topic (`chapter_title` + `chapter_summary` + `segment_count`).

## Preset (Philosophical Poem)

The poetry form's default preset is the **philosophical poem** preset, now folded into this skill. It declares the book's chapter count, word target, and the ordered filter/agent sequence (the "chapter-curation workflow"):

- **Chapter count:** 10 main poems, one introductory poem, and one conclusion poem.
- **Segments per chapter:** 8 by default, declared explicitly by each chapter's `segment_count`.
- **Development:** new poetic development for each chapter.
- **Word target:** 500 words per segment unless the book pipeline overrides it.
- **Filter sequence** (each step is an agent/filter applied to every selected poem in sequence):

```text
workshop -> research -> genre -> history -> spatality -> movement -> correctness -> override -> quality
```

1. **workshop** — Create the poem as flat, continuous poetic prose, grounded in the topic and chapter plan.
2. **research** — Gather and organize the subject, context, source notes, and usable images for the poem.
3. **genre** — Assign the poem's genre (the literary category shaping its register).
4. **history** — Ground the poem in verified historical/contextual material.
5. **spatality** — Ground the poem in a specific sense of place and space.
6. **movement** — Shape the poem's through-line, pacing, and closing gesture.
7. **correctness** — Verify factual, attributional, religious, philosophical, and cultural claims before poetic rendering.
8. **override** — Apply any human transformation instructions from the override layer, or pass through unchanged when empty.
9. **quality** — Audit the poem against the preset, topic, theme, voice, correctness result, and final quality bar.

## Canonical Folder Shape

```text
workspaces/pipeline/<bookname>/
|-- book.json
|-- progress.json
|-- filters/
|   |-- filters.json
|   `-- (per-filter folders created lazily on first run)
`-- chapters/
    `-- 1/
        |-- model.json
        |-- history/
        `-- segments/
            |-- 1/
            |-- 2/
            `-- <segment_count>/
                |-- model.json
                |-- writer/
                |-- editor/
                |-- latest/
                |-- version/
                `-- translator/
```

Every filter folder uses the same four-file shape as `research/`, with the role file named after the folder.

## Path Invariant

This is mandatory.

- Chapter folders live only under `workspaces/pipeline/<bookname>/chapters/`.
- Segment folders live only under `workspaces/pipeline/<bookname>/chapters/<chapter>/segments/`.
- Each poetry chapter has the positive `segment_count` declared in its plan; legacy plans without it use one segment.
- Each segment gets its own `segment.json`, `writer/`, `editor/`, `latest/`, `translator/`, and `version/` folders under `segments/<n>/`.
- Each chapter has a `history/` folder (`workspaces/pipeline/<bookname>/chapters/<n>/history/`) that holds superseded drafts of `chapter.md`; the live `chapter.md` always holds the current state.
- Do not create `mood.json` for poetry.
- Do not create `book.json`, `characters.json`, `masterprompt.md`, or `workshop_metadata.md` for poetry unless the user explicitly asks for a hybrid project.

## Chapter And Segment State

Create `chapter.json` in every chapter folder and a pending `segment.json` in each configured segment folder.

Layout owns the segment plan: the backlog `book.json` carries each poetry
chapter's `segment_count` **and** its inline `segments[]` array. Scaffold clones
that plan into the pipeline, so `chapter.json` starts with `segment_count` and
the same `segments[]` records (not an empty list). Each record contains
`segment_index`, `name`, `word_target` (the chapter's per-segment target),
`segment_title`, `segment_summary`, and `further_references`; scaffold also
seeds the matching `segments/<n>/segment.json` with the record's title and
summary plus runtime identity/state fields. Enrichment preserves the plan and
only layers the poetic parameters on top.

The scaffold agent's `## Chapter Layout` section is the runtime semantics for these files and folders:

- `chapter.md` is the live poem draft and starts with only the bare minimum content.
- `chapter.json` is the authoritative runtime metadata file for the poem chapter.
- `history/` stores superseded copies of `chapter.md` or writer-stage drafts before overwrite.
- `segments/<n>/writer/` stores writer-stage poem copies.
- `segments/<n>/editor/` stores editorial notes and quality feedback.
- `segments/<n>/latest/` stores the most recent finalized poem copy (refreshed by review and publish).
- `segments/<n>/version/` stores versioned/promoted snapshots of the segment's published output.
- `segments/<n>/translator/` stores translated derivatives only.

## Topic And Chapter Set

Each entry in `book.json`'s `chapters[]` array becomes one poetry chapter. Its
`segment_count` controls the number of segment records and folders; new poetry
plans default this field to 8, while a legacy plan without it remains one.

If the user supplies topics, preserve their text exactly except for trimming surrounding whitespace. If no topic list is supplied, derive a concise ordered topic list from the gist or book name and the requested chapter count.

The default `chapter_count` is 5 unless the user specifies another count.

## Root Files

Create these at the pipeline root.

### `book.json`

Minimum fields:

- `form`: `poetry`
- `book_name`
- `book_long_title`
- `language`
- `register`
- `quality`
- `themes`
- `reference`
- `index`
- `sacred_vocabulary`
- `translation_guide`
- `chapter_count`
- `source_terms`
- `created_at`

### Topics (in `book.json`)

Each chapter's topic is its `chapters[]` entry: the `chapter_title` (the topic)
and `chapter_summary` (its seed), in the exact writing order. `chapter_title` is
**machine-read**: `tools/verify_pipeline.py` checks progress against the plan's
`chapters[]`, and publish counts `chapters[]` for the chapter total. Keep each
`chapter_title` a single title — never fold summaries, numbering, or commentary
into it.

### `bookseed.md` (book vocabulary seed)

The book's own vocabulary and phrases. **Layout stages it** in the backlog at
`workspaces/backlog/<bookname>/bookseed.md` from
`.framework/templates/backlog/v1/bookseed.md`; the human may fill it. **Scaffold
copies it** verbatim to `workspaces/pipeline/<bookname>/bookseed.md` (plain text,
no audit stamp). Treat each line as a reusable word or phrase for this book.

### `signature.md` (selected style's signature)

The selected style's companion signature. **Scaffold copies it** from
`.framework/editor/<form>/styles/<style>/signature.md` to
`workspaces/pipeline/<bookname>/signature.md` and stamps the copy `scaffold`.
It is never staged in the backlog.

### `progress.json`

Track one entry per topic.

Minimum fields:

- `title`
- `language`
- `source_terms`
- `context`
- `total_chapters`
- `completed_chapters`
- `current_chapter`
- `chapters`

Each progress chapter must include:

- `chapter_number`
- `topic`
- `category`
- `status`
- `file_path`
- `completed_date`

For a new scaffold, set all statuses to `pending`, `completed_chapters` to `0`, `current_chapter` to `1`, and `completed_date` to `null`.

### `filters/override/filter.md` — the override command file

The poetry override, like the novel override, is **a filter-file command layer**, not a pipeline-root file. Do **not** create a pipeline-root `override.md`. The `override` filter lives in `filters/override/` and its command file `filters/override/filter.md` is seeded at scaffold from `.framework/editor/poetry/filters/override/SKILL.md` (dynamically customized for the poetry form and the pipeline's actual context), with an empty `## Instructions` section for the human.

## Chapter And Segment State

Create `chapter.json` in every chapter folder and `segment.json` in every segment folder.

Chapter-level `chapter.json` minimum shape:

```json
{
  "level": "chapter",
  "state": "scaffolded",
  "chapter_index": 1,
  "chapter_name": "Topic",
  "topic": "Topic",
  "segments": [1]
}
```

Segment-level `segment.json` minimum shape:

```json
{
  "level": "segment",
  "state": "returning",
  "chapter_index": 1,
  "segment_index": 1
}
```

## Filter Registry

Before creating the filter registry, read `workspaces/backlog/<bookname>/book.json`. Use the ordered `filter_chain` list declared in the book plan as the canonical filter chain. If for any reason the book plan cannot be read, fall back to the default poetry chain declared in this skill's *Preset* section:

```text
workshop -> research -> correctness -> theme -> syntax -> override -> quality
```

**Reconcile a chain inherited from the novel option.** A poetry book that was laid out with the novel option declares the novel chain (`research -> seeds -> correctness -> theme -> syntax -> override -> quality`), which lacks the required `workshop` step. Do not stop: rewrite the plan's `filter_chain` to the poetry chain above, persist that repair to the backlog `book.json`, and report it. A chain that already contains the required steps in order keeps its extra filters.

Create `workspaces/pipeline/<bookname>/filters/filters.json` with the selected chain in order.

Each registry entry must include:

- `order`
- `name`
- `folder`
- `role_file`
- `input_file`
- `output_file`
- `description`
- `agent`
- `autorun` — a boolean (`true` or `false`). Default `true` for every filter in the chain. The human may set any filter to `false` to skip it; `/book <bookname> filter *` (and `filter all`) runs only the filters whose `autorun` is `true`, in order, skipping disabled ones. A single named filter (`/book <bookname> filter <filter>`) still runs that filter explicitly regardless of its `autorun` flag.

For each named filter folder, scaffold only the registry entry in `filters.json` — **do not pre-create the folder or its files**. The filter creates its own `filters/<filter>/` folder (and its `<filter>.md`, `filter.md`, `content-input.md`, `content-output.md` files) on first run if missing:

`content-input.md` is the **input snapshot** — when the filter runs, it records the upstream material the filter consumed (previous filter's output, chapter drafts, context). It exists so a filter pass can be undone: restoring the input and the prior state reverses the run. Leave it as an empty placeholder at scaffold time.

Leave runtime content empty unless the active workflow explicitly runs that filter.

**Override command file (poetry customization):** the `override` filter is the one structural exception. Its exact seeding content is **dynamically derived at scaffold time** from `.framework/editor/poetry/filters/override/SKILL.md` plus the poetry stereotype index at `.framework/editor/poetry/readme.md` — do not treat this paragraph as the fixed recipe. Before you create the override file, read both and let them govern the shape:

1. **Read `.framework/editor/poetry/filters/override/SKILL.md`** — the base content for the command file: the override command file is `workspaces/pipeline/<bookname>/filters/override/filter.md`, and it is generated/refreshed from the chapter (or poem) models' context so the human instructions are grounded in what the poems actually contain.
2. **Read `.framework/editor/poetry/readme.md`** — the master index of the poetry stereotype folder, for the identity wording and conventions of the poetry form.
3. **Seed `workspaces/pipeline/<bookname>/filters/override/filter.md`** on first use (not at scaffold), customized for poetry: identity "poetry pipeline", applies to every **poem**, model updates on the poem chapter models under `chapters/<n>/`, instruction scope "every poem" (each topic in `book.json`'s `chapters[]`).
4. **Keep the two override layers distinct.** All forms share the override command file at `filters/override/filter.md`. The pipeline-root `override.md` is a different file — the master prompt — and both may coexist; never merge them or write one at the other's path.
5. Align with whatever the readme's sub-indexes declare (singer/signature set, reference texts, syntax samples, theme sets under `signatures/`, `references/`, `syntax/`, `themes/`) — the override layer must not contradict the stereotype set the pipeline will use.
6. Leave the trailing `## Instructions` section empty below the `---` line and never overwrite existing human instructions there.

## Source Destination

Create:

```text
workspaces/published/<bookname>/chapters/
```

Do not write poem chapters or `book.md` during layout.

## Verification

Before reporting completion, verify:

- Root files exist: `book.json`, `bookseed.md`, `signature.md`, and `progress.json`.
- `filters/override/filter.md` exists — the override command file. The pipeline-root `override.md` (master prompt) is a separate file and may coexist with it.
- `filters/filters.json` exists and names all seven poetry filters in order. No per-filter folders are created at scaffold; each filter creates its folder on first run.
- Every topic has one numeric chapter folder.
- Every configured `segments/<n>/` has `writer/`, `editor/`, `latest/`, `version/`, `translator/`, and `segment.json`.
- Every chapter has `chapter.json` with `segment_count` and `segments` plus a `history/` folder.
- No `mood.json` files exist in poetry chapter folders.
- No chapter or segment folders were created outside the canonical paths.
- `workspaces/published/<bookname>/chapters/` exists and contains no unfinished generated prose unless a later workflow created it.
