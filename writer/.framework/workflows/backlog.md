---
name: backlog
description: Backlog creation and book-plan workflow. Owns the backlog-creation phase of the /book pipeline — the bare bookname command (create/update the backlog epic and its seed gist) and the init/backlog/layout command (configure the backlog book plan and derive the ordered filter chain). Operates only in .space/backlog/<bookname>/; never scaffolds a pipeline or writes finished chapters.
---

# The Backlog Workflow (Backlog Creation)

This workflow owns the **backlog-creation phase** of the `/book` pipeline. It handles the commands that build and configure the backlog folder before any pipeline exists:

```text
/book <bookname> init [<gist>] [form] [refresh]          # gist.md only; with refresh: full bootstrap (gist + storyline + book.json)
/book <bookname> layout [<count>] [form]                 # rewrite storyline.md from gist + materials, then derive book.json
/book <bookname> init idea                               # rewrite the gist with AI assistance
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
├── book.json   # the chapter-layout plan + ordered filter chain (blueprint for scaffold)
└── materials/  # human-authored research materials (created by init; user writes here)
```

It must **never** create, read, or modify:

- `.space/pipeline/<bookname>/` (the pipeline is scaffolded later by `pipeline.md`)
- `source/books/` (reader-facing output)
- any filter directory, chapter folder, or `model.json`

The backlog is **metadata**; the pipeline is **execution state**. Commands here produce metadata only.

## Command Reference

| Command | What it does |
|---------|--------------|
| `<bookname> init [<gist>] [form]` | Creates or edits **only `gist.md`** — the seed idea. Does **not** create `storyline.md` or `book.json`. Use `layout` to derive them, or `init ... refresh` to regenerate the full backlog. |
| `<bookname> init ... refresh` | Full bootstrap: regenerates `gist.md`, `storyline.md`, and `book.json` from the premise (grounded in `materials/`). |
| `<bookname> layout [<count>] [form]` | Rewrites `storyline.md` from `gist.md` plus any research materials in `materials/`, then derives `book.json` (the layout). An explicit `<count>` and `form` control the resulting plan. |
| `<bookname> init idea` | Rewrites the book's gist with AI assistance — reads the existing `gist.md` (or the book name if absent), generates a stronger, more dramatically charged one-line premise, and writes it back to `gist.md` (updating its expansion to match). Never touches `storyline.md`, `book.json`, the pipeline, or `source/books/`. |

Every subcommand keyword is literal and unambiguous. `backlog` is a synonym of `init`. `idea` is a subcommand of `init`. `layout` is its own command — not an alias of `init`.

## The Init Command (gist-only by default)

For `/book <bookname> init [<gist>] [<form>] [refresh]`:

Responsibility: create or edit **only `gist.md`** — the seed idea. This is the gist-only boundary. Without `refresh`, init writes `gist.md` and nothing else; it never creates or rewrites `storyline.md` or `book.json`.

- `<gist>` — optional single-sentence premise. If omitted, infer a one-line premise from the book name (or keep the existing gist).
- `<form>` — optional form selector: `novel` or `poetry`. Used only to build a default gist when none exists.
- `refresh` — optional keyword. When present, init switches to **full bootstrap**: regenerate `gist.md`, `storyline.md`, and `book.json` from the premise, grounded in `materials/`.

1. This command does NOT scaffold a pipeline, run layout, or run research.
2. Resolve the gist: `<gist>` argument → existing `gist.md` → inferred from the book name.
3. **Write `gist.md`.** Create or update `.space/backlog/<bookname>/gist.md` with the seed idea: a single-sentence **gist**, a short **expansion** (2–4 sentences) that names the protagonist, the conflict, and the transformation, and an empty `## Author Comment` section the author may fill. Preserve any author-written comment already present.
4. **Without `refresh`, stop here.** Do not create or modify `storyline.md` or `book.json`. Report that the user should run `layout` (or `init ... refresh`) to derive them.
5. **With `refresh`, full bootstrap.** Regenerate `storyline.md` from the premise (grounded in any `materials/` content) and derive `book.json` (the chapter-layout plan + ordered filter chain). This is the only init path that writes `storyline.md`/`book.json`.

## The Layout Command

For `/book <bookname> layout [<count>] [<form>]`:

Responsibility: rewrite `storyline.md` from the gist, then derive `book.json` (the layout). This is the layout boundary.

1. This command does NOT scaffold a pipeline, run filters, or run research.
2. Read the gist from `.space/backlog/<bookname>/gist.md` (a user-supplied `<gist>` overrides it).
3. Read any research materials under `.space/backlog/<bookname>/materials/` and ground the storyline in them (never contradict them).
4. **Rewrite `storyline.md`** from the gist (+ materials), preserving the original `Created` timestamp and updating `Updated`/`Updated By`.
5. **Derive `book.json`** from the (refreshed) `storyline.md`. An explicit `<count>` and `<form>` control the resulting plan — chapter count, titles, summaries, characters, and the ordered `filter_chain`/`word_target`. Without `<count>`, reuse the existing `book.json` chapter count.
6. `layout` is its own command, not an alias of `init`.

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

For `/book <bookname> layout [<count>] [<form>]` (and `init ... refresh [<count>]`):

1. **Resolve the current chapter count** from the existing `book.json` (`chapter_count` and the length of its `chapters` array).
2. **If the requested count is greater than the current chapter count — append, never rewrite.** Derive only the missing chapters from gist.md and storyline.md and append them to the existing chapters array. Each appended chapter_summary must be a simple, form-neutral 1-4 sentence seed built from a varied subject selected from the source material. Vary the opening, syntax, and focus; never reuse a fixed lead-in or sentence pattern such as *This poem* or *Yamuna remembers*. Preserve every existing chapter entry verbatim.
3. **If `<count>` is less than or equal to the current chapter count — change nothing in the chapters.** Report the current count and the requested count, and leave the `chapters` array untouched. Never truncate, renumber, or re-derive existing chapters to shrink the plan.
4. **The rule holds only while the gist is unchanged.** If a `<gist>` is supplied and it differs from the recorded gist in `gist.md`/`book.json`, the premise itself has changed: the standard init path applies (chapters re-derived from the new premise), and the incremental append no longer applies. Without `refresh`, an unchanged gist always means the incremental path above.
5. **`refresh` preserves the chapter count.** The explicit `refresh` keyword re-grooms all backlog artifacts to the resolved form, but it **preserves the existing chapter count and the existing `chapters` array verbatim** — same length, same entries. The `chapters` array is re-derived on refresh only when the form itself changes or the caller explicitly supplies a new `<count>`. Refresh is the only init path that may rewrite backlog artifacts (epic, gist, filter chain); it is not a path that resizes or renumbers the chapter plan.
6. **Report what was done:** the previous count, the new count, the chapters appended (with their indices and titles), and confirmation that existing chapters were preserved verbatim.

The same incremental rule governs `scaffold` and `layout` reconciliation: when a pipeline already exists and the plan only grew, the scaffold/layout agent must not re-scaffold or re-derive existing chapters unless the user explicitly asks (see the safety constraint: *Never re-scaffold an existing pipeline from scratch unless the user explicitly asks*).

## Refresh And Count Contract

`layout` derives `book.json` from `storyline.md`; an explicit larger `<count>`
appends missing entries and a smaller count never removes them (see *The
Incremental Count Rule*). `init ... refresh` regenerates the full backlog from
the premise, grounded in `materials/`. A changed gist or form is an explicit
re-plan: it may rebuild the plan, but does not change an existing pipeline.
Scaffold later reconciles only an append-only plan.

## The Three Backlog Artifacts

A fully configured backlog folder contains exactly three files. Each has one clear role:

| File | Role |
|------|------|
| `gist.md` | The seed idea — a single-sentence gist, a short expansion, and an optional Author Comment. The source of the book's premise. |
| `storyline.md` | The full narrative foundation — premise, setting, characters, themes, chapter outline. The source of truth for a novel's story. |
| `book.json` | The chapter-layout plan and filter chain — chapter count, per-chapter titles and summaries, characters, subject matter, and the ordered filter/agent sequence. The blueprint for `scaffold`. |

### gist.md

The seed idea. Contains a single-sentence **gist** (the high concept), a short **expansion** (2–4 sentences) naming the protagonist, the conflict, and the transformation, and an optional **`## Author Comment`** section for the author's own note on intent, inspiration, or direction. Init creates the Author Comment section as an empty placeholder and never invents the author's words; the author fills it in.

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

- **Gist creation/update** (`init`, `init idea`) is owned by the gist agent (`.framework/agents/gist/agent.md`).
- **Storyline + book-plan derivation** (`layout`, `init ... refresh`) is owned by the init agent (`.framework/agents/init/agent.md`).
- Neither command invokes research, filter, or writing skills. Scaffold and all later phases are owned by `.framework/workflows/pipeline.md`.
