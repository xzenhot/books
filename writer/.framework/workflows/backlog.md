---
name: backlog
description: Backlog creation and book-plan workflow. Owns the backlog-creation phase of the /book pipeline — the bare bookname command (create/update the backlog epic and its seed gist) and the init/backlog/layout command (configure the backlog book plan and derive the ordered filter chain). Operates only in .space/backlog/<bookname>/; never scaffolds a pipeline or writes finished chapters.
---

# The Backlog Workflow (Backlog Creation)

This workflow owns the **backlog-creation phase** of the `/book` pipeline. It handles the two commands that build and configure the backlog folder before any pipeline exists:

```text
/book <bookname> [<gist>] [form] [refresh]                                          # create/update backlog epic (gist merged; backlog epic only. no pipeline)
/book <bookname> init|backlog|layout [<gist>] [<count>] [form] [refresh]            # configure the backlog book plan
/book <bookname> init idea                                                         # rewrite the gist with AI assistance
```

These are **Phase 0 (Backlog)** and **Phase 1 (Init)** of the overall `/book` workflow. The full `/book` lifecycle lives in `.framework/workflows/pipeline.md`; this file is the authoritative spec for the backlog-creation half of that lifecycle. `scaffold` and everything after it is owned by `pipeline.md`.

## Command Boundary

Every command in this workflow **must pass through** `.framework/rules/command-boundary.md` before executing. That rule is the authoritative boundary contract and applies to all commands, in all workflows, in both forms (novel and poetry).

- Read `.framework/rules/command-boundary.md` first, and treat its backlog/pipeline boundary and sequence rules as binding on every command below.
- This workflow owns **backlog commands only**. It must never cross into `.space/pipeline/<bookname>/` or `source/books/`.
- If a command would violate the boundary, stop and respond with the exact error form defined in that rule.

## Next Steps

After **every** command in this workflow completes — including read-only, no-op, and early-stop results — append a **Next Steps** section to the response, following `.framework/rules/next-steps.md`. That rule is mandatory and unconditional; it maps each completed command to its recommended next action and optional follow-ups. Read it and apply it to every response.

## Scope Boundary

The backlog workflow operates **only inside the backlog**:

```text
.space/backlog/<bookname>/
├── gist.md     # the seed idea — a single-sentence gist plus a short expansion
├── storyline.md     # the full narrative foundation (novel) or thematic grounding (poetry)
└── book.json   # the chapter-layout plan + ordered filter chain (blueprint for scaffold)
```

It must **never** create, read, or modify:

- `.space/pipeline/<bookname>/` (the pipeline is scaffolded later by `pipeline.md`)
- `source/books/` (reader-facing output)
- any filter directory, chapter folder, or `model.json`

The backlog is **metadata**; the pipeline is **execution state**. Commands here produce metadata only.

## Command Reference

| Command | What it does |
|---------|--------------|
| `<bookname>` (bare) | Creates `.space/backlog/<bookname>/storyline.md` if it does not exist, auto-generating the gist from the book name. If the epic already exists, reports that it exists. Does not scaffold a pipeline. |
| `<bookname> [<gist>] [form] [refresh]` | Creates, updates, or rewrites the backlog epic at `.space/backlog/<bookname>/storyline.md` and records the seed idea in `.space/backlog/<bookname>/gist.md`. If `[<gist>]` is omitted, infer a one-line premise from the book name. If the epic already exists, re-groom it into a coherent foundation (preserving the original `Created` timestamp). If `[form]` is supplied, changes the book's form (`novel`/`poetry`) and updates `book.json`. Never creates a pipeline — use `scaffold` for that. If `refresh` is supplied, rebuilds `storyline.md` from scratch and re-initializes the entire backlog folder. |
| init (aliases: backlog, layout) | Creates or selects the backlog book plan, derives the ordered filter chain, and produces the chapter-layout plan. All aliases invoke the same backlog-only init behavior, including incremental count handling. `refresh` re-grooms the backlog artifacts to the resolved form while preserving the chapter count and existing chapters verbatim (re-derivation only on form change or explicit new count). |
| `init idea` | Rewrites the book's gist with AI assistance — reads the existing `gist.md` (or the book name if absent), generates a stronger, more dramatically charged one-line premise, and writes it back to `gist.md` (updating its expansion to match). Never touches `storyline.md`, `book.json`, the pipeline, or `source/books/`. |

Every subcommand keyword is literal and unambiguous. `backlog` is a synonym of `init`. `idea` is a subcommand of `init`.

## The Bare Bookname Command (gist merged)

For `/book <bookname> [<gist>] [<form>] [refresh]`:

Responsibility: create, update, or rewrite the backlog epic with a detailed narrative foundation, record the seed idea in `gist.md`, and — when a form is supplied — change the book's form and update `book.json`. It does not scaffold or initialize. The former `gist` subcommand is merged into this command: a bare `/book <bookname>` behaves exactly as `/book <bookname> gist` did.

- `<gist>` — optional single-sentence premise. If omitted, infer a one-line premise from the book name.
- `<form>` — optional form selector: `novel` or `poetry`. If supplied, it changes the book's form and updates `book.json` (see step 9).
- `refresh` — optional keyword. When present, **rebuild** the epic and **re-initialize the backlog folder** `.space/backlog/<bookname>/` from scratch (see step 10).

1. This command does NOT scaffold a pipeline, run layout, or run research — it focuses solely on creating and grooming the backlog epic.
2. If `.space/backlog/<bookname>/storyline.md` does not exist, create it; if it exists, develop and refine it.
3. If [<gist>] is omitted, infer a one-line premise from the book name. The gist must be a single sentence.
4. **Write `gist.md`.** Create or update `.space/backlog/<bookname>/gist.md` with the seed idea: a single-sentence **gist** plus a short **expansion** (2–4 sentences) that names the protagonist, the conflict, and the transformation. This file is the source of the book's premise and is read by `init` to derive the chapter-layout plan.
5. **Novel:** Develop a rich, well-groomed epic that includes:
   - A compelling premise and historical grounding
   - Detailed character descriptions, motivations, and arcs
   - Thematic threads that weave through the narrative
   - Chapter-by-chapter outline with key scenes and turning points
   - World-building details (settings, era, cultural context)
   - Emotional and philosophical depth
6. **Poetry:** Create a thoughtful epic with:
   - Thematic grounding and spiritual/philosophical context
   - Topical structure showing the progression of themes
   - Reference to the poetic voice and tradition
7. The epic should be polished, coherent, and inspiring — a solid foundation for the full pipeline.
8. **When the epic already exists, re-groom it.** Read the existing epic and extract what is salvageable: the title, book name, language, genre, era, chapter count, and any coherent premise, character, theme, or chapter outline material. Regenerate it into a well-groomed, consistent foundation that remains true to the existing material — do not invent a new story, but reorder, clarify, and deepen what is already present. Update the `Updated` timestamp and `Updated By` field; keep the original `Created` timestamp unchanged.
9. **Change the form when `<form>` is supplied.** If `<form>` differs from the book's current form, change it and update `.space/backlog/<bookname>/book.json`:
   - Set the `filter_chain` to the form's preset chain (see the init agent's *Presets* section: `layout-poetry/SKILL.md` for poetry, `layout-novel/SKILL.md` for novel).
   - Set `word_target` to the form's preset target (500 for poetry, 4500 for novel).
   - Re-derive the `chapters` array for the new form (`Introduction`, `1..N`, `Conclusion` for novels; `1..N` topics for poetry).
   - Re-derive `all_characters` (novels) or drop it (poetry).
   - If `book.json` does not exist yet, create it (delegating to the init agent's book-plan derivation).
10. **When refresh is supplied, compare the canonical gist first.** If the canonical gist is unchanged, do not write gist.md or storyline.md; update only book.json chapter_summary seeds and required count/form metadata. If the gist changed, regenerate the dependent gist.md, storyline.md, and book.json artifacts.
    - Read gist.md and book.json to compare the canonical gist; read storyline.md as source context for chapter summaries.
    - If the canonical gist changed, rebuild storyline.md from the changed premise, preserving Created and updating Updated and Updated By. If the gist is unchanged, do not write storyline.md.
    - If the canonical gist is unchanged, write only book.json with refreshed, varied, form-neutral chapter_summary seeds. If the gist changed, re-derive gist.md, storyline.md, and book.json. Never create override artifacts in the backlog.
    - Never touch `.space/pipeline/<bookname>/` or `source/books/`; the pipeline may be re-scaffolded afterwards by an explicit `scaffold` command.

## The Init Command

For `/book <bookname> init|backlog|layout [<gist>] [<count>] [<form>] [refresh]`:

Responsibility: fully configure the backlog folder — the gist, epic, chapter-layout plan (`book.json`), and master prompt — and derive the ordered filter chain. This phase is mandatory before `scaffold`. Init operates only in the backlog; it must never create or modify pipeline files.

- `<gist>` — optional single-sentence premise. If supplied, it is recorded in `gist.md` (and used to build the epic if missing).
- `<preset>` — optional preset path, named template, or inline Markdown. If omitted, the init agent selects the default preset for the form.
- `<form>` — optional form selector: `novel` or `poetry`. Defaults to `novel`. Used to set or change the book's form.
- `<count>` — optional target chapter count. When the backlog book plan already exists, init is **incremental in count**: only the missing chapters are appended; existing chapters are never rewritten (see *The Incremental Count Rule* below).
- `refresh` — optional keyword. When present, **rebuild** `storyline.md` and **re-initialize the entire backlog folder** `.space/backlog/<bookname>/`: every backlog artifact (`gist.md`, `storyline.md`, `book.json`) is re-derived from the book's identity and reconciled to the resolved form (see step 6). Unlike a normal init (which fills only gaps), `refresh` regenerates the backlog so it is internally consistent — e.g. a poetry book whose `storyline.md` still reads as a novel is rebuilt as a poetry-consistent foundation. It never touches the pipeline or `source/books/`.

1. If `<preset>` is provided, merge its filter chain into `.space/backlog/<bookname>/book.json` as the `filter_chain` field. The content may be a file path, a named preset template, or inline Markdown. If a file path is referenced, read its filter sequence.
2. If `<preset>` is omitted, invoke the init agent (`.framework/agents/init/agent.md`) to select or create the form-specific default filter chain. The form is resolved from the explicit `<form>` argument, backlog epic, or default `novel`. Init never reads the pipeline; the pipeline `book.json` is read only by the postlayout agent after scaffold.
3. The init agent creates or validates the full backlog configuration — `gist.md`, `storyline.md`, and `book.json` — and returns the ordered filter/agent sequence. It does not create or modify any file under `.space/pipeline/<bookname>/`. The `override.md` and `override.txt` files are **pipeline-level** artifacts, not backlog artifacts: they are created by the scaffold step (`.space/pipeline/<bookname>/override.txt` and `.space/pipeline/<bookname>/filters/override/filter.md`), never in the backlog folder.
4. Do not execute filters during init; only prepare the filter chain and the chapter-layout plan.
5. **Change the form when `<form>` is supplied.** If `<form>` differs from the book's current form, change it and update `.space/backlog/<bookname>/book.json`:
   - Set the `filter_chain` to the form's preset chain (see the init agent's *Presets* section: `layout-poetry/SKILL.md` for poetry, `layout-novel/SKILL.md` for novel).
   - Set `word_target` to the form's preset target (500 for poetry, 4500 for novel).
   - Re-derive the `chapters` array for the new form (`Introduction`, `1..N`, `Conclusion` for novels; `1..N` topics for poetry).
   - Re-derive `all_characters` (novels) or drop it (poetry).
6. **Refresh when refresh is supplied.** Compare the canonical one-line gist in gist.md with book.json.gist first. If unchanged, write only book.json chapter_summary seeds and required count/form metadata; do not write gist.md or storyline.md. If changed, regenerate the dependent gist.md, storyline.md, and book.json artifacts. Never touch the pipeline or source/books.
7. **Output contract:** after init, book.json must exist and contain the complete chapter-layout plan (chapter count, per-chapter titles, and simple form-neutral chapter_summary seeds) plus characters, subject matter, and the authoritative filter_chain sequence that scaffold will use to build the pipeline. Each summary must be contextual to gist.md and storyline.md only, usable for poetry, prose, or any other literary form, and must not prescribe a literary form. Init uses simple, form-neutral chapter_summary seeds; there is no separate layout summary mode.

## The Idea Command

For `/book <bookname> init idea`:

Responsibility: rewrite the book's **gist** with AI assistance — the single-sentence premise that seeds the whole book. This command operates only on the gist; it does not touch the epic, the book plan, the pipeline, or `source/books/`.

- The command reads the existing `.space/backlog/<bookname>/gist.md` (its one-line **gist**) as the source material. If `gist.md` does not exist, use the book name as the seed.
- It asks the AI to generate a **stronger, more dramatically charged one-line premise** — a specific, concrete situation that names a person, a place, a problem, and a consequence (see the gist agent's *The Great Idea* method). It must remain a single sentence.
- It writes the improved one-liner back to `gist.md` as the **gist**, and regenerates the **expansion** (2–4 sentences) to match — naming the protagonist, the conflict, and the transformation. This is the only artifact `init idea` writes.

1. Do **not** scaffold a pipeline, run layout, or run research.
2. Do **not** rewrite `storyline.md` or `book.json`. Those are downstream artifacts: the user must run a later `init`/`refresh` (or re-run the bare bookname command) to re-derive the epic and book plan from the rewritten gist.
3. Preserve the original `Created` timestamp if one exists; update `Updated` and `Updated By`.
4. The gist must remain a **single sentence**; the expansion stays short (2–4 sentences) and names protagonist, conflict, and transformation.
5. Report the old gist, the new gist, and note that `storyline.md`/`book.json` are unchanged and will need re-derivation.

### The Incremental Count Rule

For `/book <bookname> init|backlog|layout [<gist>] [<count>] [<form>] [refresh]`:

1. **Resolve the current chapter count** from the existing `book.json` (`chapter_count` and the length of its `chapters` array).
2. **If the requested count is greater than the current chapter count — append, never rewrite.** Derive only the missing chapters from gist.md and storyline.md and append them to the existing chapters array. Each appended chapter_summary must be a simple, form-neutral 1-4 sentence seed built from a varied subject selected from the source material. Vary the opening, syntax, and focus; never reuse a fixed lead-in or sentence pattern such as *This poem* or *Yamuna remembers*. Preserve every existing chapter entry verbatim.
3. **If `<count>` is less than or equal to the current chapter count — change nothing in the chapters.** Report the current count and the requested count, and leave the `chapters` array untouched. Never truncate, renumber, or re-derive existing chapters to shrink the plan.
4. **The rule holds only while the gist is unchanged.** If a `<gist>` is supplied and it differs from the recorded gist in `gist.md`/`book.json`, the premise itself has changed: the standard init path applies (chapters re-derived from the new premise), and the incremental append no longer applies. Without `refresh`, an unchanged gist always means the incremental path above.
5. **`refresh` preserves the chapter count.** The explicit `refresh` keyword re-grooms all backlog artifacts to the resolved form, but it **preserves the existing chapter count and the existing `chapters` array verbatim** — same length, same entries. The `chapters` array is re-derived on refresh only when the form itself changes or the caller explicitly supplies a new `<count>`. Refresh is the only init path that may rewrite backlog artifacts (epic, gist, filter chain); it is not a path that resizes or renumbers the chapter plan.
6. **Report what was done:** the previous count, the new count, the chapters appended (with their indices and titles), and confirmation that existing chapters were preserved verbatim.

The same incremental rule governs `scaffold` and `layout` reconciliation: when a pipeline already exists and the plan only grew, the scaffold/layout agent must not re-scaffold or re-derive existing chapters unless the user explicitly asks (see the safety constraint: *Never re-scaffold an existing pipeline from scratch unless the user explicitly asks*).

## Refresh And Count Contract

For poetry backlog plans, a normal unchanged-gist init may append missing poem
entries when an explicit count is larger. It preserves every existing chapter
entry byte-for-byte. A smaller count never removes poems. Refresh without a
changed gist preserves gist.md, storyline.md, the chapter count, and every chapter
entry; it may only repair missing required metadata. A changed gist or form is
an explicit re-plan: it may rebuild the plan, but does not change an existing
pipeline. Scaffold later reconciles only an append-only plan.

## The Three Backlog Artifacts

A fully configured backlog folder contains exactly three files. Each has one clear role:

| File | Role |
|------|------|
| `gist.md` | The seed idea — a single-sentence gist plus a short expansion. The source of the book's premise. |
| `storyline.md` | The full narrative foundation — premise, setting, characters, themes, chapter outline. The source of truth for a novel's story. |
| `book.json` | The chapter-layout plan and filter chain — chapter count, per-chapter titles and summaries, characters, subject matter, and the ordered filter/agent sequence. The blueprint for `scaffold`. |

### gist.md

The seed idea. Contains a single-sentence **gist** (the high concept) plus a short **expansion** (2–4 sentences) naming the protagonist, the conflict, and the transformation.

### storyline.md

The full narrative foundation. For novels: premise, setting & era, characters, thematic threads, chapter-by-chapter outline, world-building, and conclusion. For poetry: thematic grounding, topical structure, and reference to the poetic voice and tradition.

### book.json

The chapter-layout plan. This is the blueprint that tells `scaffold` exactly how many chapters to build and how each chapter is laid out. If there are more than 10 chapters, derive it in batches of 10 to minimize token context. It must contain:

- **Identity fields** — `book_name`, `book_long_title`, `generic` (genre), `era`, `language`, `target_audience`, `chapter_count`, `created_at`, `user_name`, `gist`, and `form`.
- **`book_summary`** — a 5–10 sentence paragraph outlining the complete story, derived from the epic.
- **`chapters`** — an ordered array, one entry per chapter. Each entry carries `chapter_index`, `name`, `chapter_title`, `chapter_summary`, `word_target`, and `further_references`.
- **`all_characters`** — array for novels; omitted or empty for poetry.
- **`filter_chain`** — the ordered array of filter/agent names, taken from the form's preset.
- **`word_target`** — the default target word count per chapter/poem (4500 for novels, 500 for poetry). Every chapter item carries its own `word_target` field.

**Chapter count and layout.** The chapter count comes from the epic's declared chapter count (or its chapter outline length). The layout follows the form:

- **Novel:** `Introduction`, `1..N`, `Conclusion` (N = the epic's main chapter count).
- **Poetry:** `1..N` (N = the number of topics in the epic's topical structure).

The sample schema is `.framework/templates/book.json`.

## Routing and Ownership

- **Epic creation/update** (bare bookname command) is owned by the gist agent (`.framework/agents/gist/agent.md`).
- **Book-plan derivation** (init command) is owned by the init agent (`.framework/agents/init/agent.md`).
- Neither command invokes layout, research, filter, or writing skills. Scaffold and all later phases are owned by `.framework/workflows/pipeline.md`.
