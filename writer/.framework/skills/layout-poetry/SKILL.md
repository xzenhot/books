---
name: layout-poetry
description: "Use when scaffolding or repairing the structural skeleton of a poetry pipeline. Creates .space/pipeline/<bookname>/, book.json, bookseed.txt, progress.json, override.md, named poetry filter folders, one segment per topic, and the empty source/books destination. Does not write poem chapters or runtime filter results."
---

# Layout Poetry - Pipeline Scaffold

You are the structural architect for a poetry pipeline. Create only the scaffold and planning artifacts needed before research, filtering, writing, revision, and final assembly begin.

A scaffolded poetry book lives at:

```text
.space/pipeline/<bookname>/
```

Finished content later lives at:

```text
source/books/<bookname>/
```

## Source Of Truth

Use this skill together with `.framework/workflows/pipeline.md`. Do not inspect existing book pipelines to discover or imitate layout conventions; existing books may be legacy, experimental, or partially migrated.

Poetry uses these root files as source of truth:

- `book.json` for how to write: form, language, register, quality, themes, reference, index, vocabulary, and translation guide.
- `bookseed.txt` for what to write: one topic per line.

## Preset (Philosophical Poem)

The poetry form's default preset is the **philosophical poem** preset, now folded into this skill. It declares the book's chapter count, word target, and the ordered filter/agent sequence (the "chapter-curation workflow"):

- **Chapter count:** 10 main poems, one introductory poem, and one conclusion poem.
- **Development:** new poetic development for each chapter.
- **Word target:** 500 words per poem unless the book pipeline overrides it.
- **Filter sequence** (each step is an agent/filter applied to every selected poem in sequence):

```text
workshop -> research -> correctness -> theme -> syntax -> override -> quality
```

1. **workshop** — Create the poem as flat, continuous poetic prose, grounded in the topic and chapter plan.
2. **research** — Gather and organize the subject, context, source notes, and usable images for the poem.
3. **correctness** — Verify factual, attributional, religious, philosophical, and cultural claims before poetic rendering.
4. **theme** — Assign the poem's philosophical lens, contemporary mapping, and form-consistent poetic stereotype selection.
5. **syntax** — Apply the selected poetic syntax guidance so the language remains current while preserving elevated cadence.
6. **override** — Apply any human transformation instructions from the override layer, or pass through unchanged when empty.
7. **quality** — Audit the poem against the preset, topic, theme, voice, correctness result, and final quality bar.

## Canonical Folder Shape

```text
.space/pipeline/<bookname>/
|-- book.json
|-- bookseed.txt
|-- progress.json
|-- filters/
|   |-- filters.json
|   `-- (per-filter folders created lazily on first run)
`-- chapters/
    `-- 1/
        |-- model.json
        |-- history/
        `-- segments/
            `-- 1/
                |-- model.json
                |-- writer/
                |-- editor/
                |-- version/
                `-- translator/
```

Every filter folder uses the same four-file shape as `research/`, with the role file named after the folder.

## Path Invariant

This is mandatory.

- Chapter folders live only under `.space/pipeline/<bookname>/chapters/`.
- Segment folders live only under `.space/pipeline/<bookname>/chapters/<chapter>/segments/`.
- Poetry chapters always have exactly one segment: `segments/1/`.
- Writer, editor, translator, and version folders live only under `segments/1/`.
- Each chapter has a `history/` folder (`.space/pipeline/<bookname>/chapters/<n>/history/`) that holds superseded drafts of `chapter.md`; the live `chapter.md` always holds the current state.
- Do not create `mood.json` for poetry.
- Do not create `book.json`, `characters.json`, `masterprompt.md`, or `workshop_metadata.md` for poetry unless the user explicitly asks for a hybrid project.

## Chapter And Segment State

Create `chapter.json` in every chapter folder and `model.json` in `segments/1/`.

The scaffold agent's `## Chapter Layout` section is the runtime semantics for these files and folders:

- `chapter.md` is the live poem draft and starts with only the bare minimum content.
- `chapter.json` is the authoritative runtime metadata file for the poem chapter.
- `history/` stores superseded copies of `chapter.md` or writer-stage drafts before overwrite.
- `segments/1/writer/` stores writer-stage poem copies.
- `segments/1/editor/` stores editorial notes and quality feedback.
- `segments/1/version/` stores versioned/promoted snapshots of the segment's published output.
- `segments/1/translator/` stores translated derivatives only.

## Topic And Chapter Set

Each non-empty line in `bookseed.txt` becomes one poetry chapter.

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

### `bookseed.txt`

One topic per line, in the exact writing order.

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

The poetry override, like the novel override, is **a filter-file command layer**, not a pipeline-root file. Do **not** create a pipeline-root `override.md`. The `override` filter lives in `filters/override/` and its command file `filters/override/filter.md` is seeded at scaffold from `.framework/agents/override/agent.md` (dynamically customized for the poetry form and the pipeline's actual context), with an empty `## Instructions` section for the human.

## Chapter And Segment State

Create `chapter.json` in every chapter folder and `model.json` in every segment folder.

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

Segment-level `model.json` minimum shape:

```json
{
  "level": "segment",
  "state": "returning",
  "chapter_index": 1,
  "segment_index": 1
}
```

## Filter Registry

Before creating the filter registry, read `.space/backlog/<bookname>/book.json`. Use the ordered `filter_chain` list declared in the book plan as the canonical filter chain. If for any reason the book plan cannot be read, fall back to the default poetry chain declared in this skill's *Preset* section:

```text
workshop -> research -> correctness -> theme -> syntax -> override -> quality
```

Create `.space/pipeline/<bookname>/filters/filters.json` with the selected chain in order.

Each registry entry must include:

- `order`
- `name`
- `folder`
- `role_file`
- `summary_file`
- `input_file`
- `output_file`
- `description`
- `agent`
- `autorun` — a boolean (`true` or `false`). Default `true` for every filter in the chain. The human may set any filter to `false` to skip it; `/book <bookname> filter *` (and `filter all`) runs only the filters whose `autorun` is `true`, in order, skipping disabled ones. A single named filter (`/book <bookname> filter <filter>`) still runs that filter explicitly regardless of its `autorun` flag.

For each named filter folder, scaffold only the registry entry in `filters.json` — **do not pre-create the folder or its files**. The filter creates its own `filters/<filter>/` folder (and its `<filter>.md`, `filter.md`, `filter-summary.md`, `content-input.md`, `content-output.md` files) on first run if missing:

`content-input.md` is the **input snapshot** — when the filter runs, it records the upstream material the filter consumed (previous filter's output, chapter drafts, context). It exists so a filter pass can be undone: restoring the input and the prior state reverses the run. Leave it as an empty placeholder at scaffold time.

Leave runtime content empty unless the active workflow explicitly runs that filter.

**Override command file (poetry customization):** the `override` filter is the one structural exception. Its exact seeding content is **dynamically derived at scaffold time** from `.framework/agents/override/agent.md` plus the poetry stereotype index at `.framework/templates/stereotypes/poetry/readme.md` — do not treat this paragraph as the fixed recipe. Before you create the override file, read both and let them govern the shape:

1. **Read `.framework/agents/override/agent.md`** — the base content for the command file: the override command file is `.space/pipeline/<bookname>/filters/override/filter.md`, and it is generated/refreshed from the chapter (or poem) models' context so the human instructions are grounded in what the poems actually contain.
2. **Read `.framework/templates/stereotypes/poetry/readme.md`** — the master index of the poetry stereotype folder, for the identity wording and conventions of the poetry form.
3. **Seed `.space/pipeline/<bookname>/filters/override/filter.md`** on first use (not at scaffold), customized for poetry: identity "poetry pipeline", applies to every **poem**, model updates on the poem chapter models under `chapters/<n>/`, instruction scope "every poem" (each topic in `bookseed.txt`).
4. **Do not create a pipeline-root `override.md`.** All forms share the single override command file at `filters/override/filter.md`.
5. Align with whatever the readme's sub-indexes declare (singer/signature set, reference texts, syntax samples, theme sets under `signatures/`, `references/`, `syntax/`, `themes/`) — the override layer must not contradict the stereotype set the pipeline will use.
6. Leave the trailing `## Instructions` section empty below the `---` line and never overwrite existing human instructions there.

## Source Destination

Create:

```text
source/books/<bookname>/chapters/
```

Do not write poem chapters or `book.md` during layout.

## Verification

Before reporting completion, verify:

- Root files exist: `book.json`, `bookseed.txt`, and `progress.json`.
- `filters/override/filter.md` exists — the override command file (no pipeline-root `override.md`).
- `filters/filters.json` exists and names all seven poetry filters in order. No per-filter folders are created at scaffold; each filter creates its folder on first run.
- Every topic has one numeric chapter folder.
- Every `segments/1/` has `writer/`, `editor/`, `version/`, and `translator/` folders.
- Every chapter has `model.json`, a `history/` folder, and `segments/1/model.json`.
- No `mood.json` files exist in poetry chapter folders.
- No chapter or segment folders were created outside the canonical paths.
- `source/books/<bookname>/chapters/` exists and contains no unfinished generated prose unless a later workflow created it.

