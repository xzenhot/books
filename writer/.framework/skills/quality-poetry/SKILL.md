---
name: quality-poetry
description: Review a poetry chapter against the seed analysis's quality parameters and revise until it passes — the final audit before a chapter is marked complete. Generates (or updates) the human-editable filter.md from the chapter models' context, then applies the human's quality directives to all chapters.
---

# Poetry Quality — Review and Apply Quality Parameters

## Audit Metadata

Chapter models and drafts are exempt. This skill may generate or rewrite
`filters/quality/filter.md` and the pipeline `style.md`; both are non-exempt and
must carry `updated_by` and `updated_date` per
`.framework/rules/audit-metadata.md`, stamped as the invoking `review` agent (or
`filter:quality`). Never stamp history/version snapshots.

Use this skill for a poetry pipeline to audit a finished chapter against the **quality parameters** defined in the seed analysis, and revise it until it passes. This is the final gate before a chapter is marked `completed`.

## Cleanup Before Audit (mandatory)

Before auditing, clean each scoped segment poem (the `latest/` copy, else
`editor/`, else the `writer/` draft):

1. **Remove the `## সারাংশ` section** — the heading (`## সারাংশ`, `## সারাংশঃ`,
   `## Summary`, any heading level) and the prose under it, up to the next
   same-or-higher heading or end of file. Summary is planner metadata, never
   reader-facing text.
2. **Remove the segment title heading** — the leading Markdown heading line
   (e.g. `## প্রাসাদের প্রথম আহ্বান`) and any `## শিরোনামঃ` / `## কবিতাঃ` /
   `## Title` / `## Poem` label (dropping the title line after a bare title
   label). The title already lives in `segment.json` and is emitted by the
   assembled anthology, so leaving it in the poem prints it twice. Never remove
   the poem body: removal must not empty the poem.
3. **Strip non-target-language content** — remove words written in a script other
   than the book's declared language script (from `book.json` → `language`). This
   is removal, not translation: Latin (`Turning Point`), Devanagari, Tamil,
   CJK, Cyrillic, etc. are dropped; target-script words, digits, and punctuation
   are kept. A mixed token keeps only its target-script clusters.

All steps are idempotent. After cleanup, write the poem to the editor stage and
mirror it into `latest/`.

## Current-Draft Requirement

Review the current chapter.md, not metadata alone. Compute its SHA-256 before
review. A pass is valid only for these unchanged bytes. If the poem changes
later, its review is invalid.

## Your Task

1. **Generate the command file** — create (or update) the human-editable `filter.md` from the chapter models' context, so the human has a ready-made, context-aware template to write quality directives into.
2. **Apply the human's directives** — read the human's quality instructions from `filter.md` and apply them to **every chapter**.

## Poetry Length Guidance

The chapter word target is a soft guide for poetry, not a pass-or-fail rule.
Use it only as a minor completeness signal: it contributes at most 15 points
out of 100 to a score. A shorter poem may pass when its imagery, structure,
voice, emotional resonance, and thematic development are strong. Never request
a rewrite solely because it is below the configured target.

## The Quality Parameters

Apply the seed analysis's quality metrics to every chapter:

- **Philosophical depth** — genuine insight, not wordplay.
- **Metaphorical richness** — layered, coherent imagery.
- **Human accessibility** — resonant with a modern reader.
- **Civilizational relevance** — speaks beyond its moment.
- **Literary quality** — the verse is crafted, not merely correct.
- **Ethical framework** — grounded in the epic's values.

### Resolving the seed analysis

The quality metrics come from the book's **seed analysis**, which lives under
`.framework/editor/poetry/themes/<theme-set>/` (each theme set carries its own
quality/seed analysis as the `theme.md`). Resolve it first:

1. Read the chapter model's `stereotype.theme_set` (and its associated
   `reference`) to name the seed analysis; when none is named, fall back to the
   book plan's theme set.
2. Read the resolved seed analysis (e.g.
   `.framework/editor/poetry/themes/aurilus/theme.md`, which is the Meditations
   seed analysis, or a theme set that carries its own seed analysis) for its full
   metrics — philosophical depth, metaphorical richness, accessibility, relevance,
   literary quality, ethical framework — and audit the chapter against those
   specific ratings and metaphor families.

The seed analysis supplies the **content bar and the creative parameters**; the
style supplies only the **structure and register**. Never pull the creative bar
(voice, imagery, emotional depth) from a style file.

## Generating the filter.md (Runtime, Context-Aware)

The `filter.md` is **generated from the chapter models** — it is not a static template. At runtime, read the chapter models and populate the file with the book's actual context, so the human's directives are grounded in what the chapters actually contain.

1. Read the book plan at `workspaces/pipeline/<bookname>/book.json` (falling back to `model.json`) for the book name and chapter list.
2. Read each chapter model at `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` to gather the context:
   - `chapter_index`, `chapter_name`, `chapter_title`
   - `topic`, `subject`, `era`, `place`, `figures`, `events`
   - `theme`, `contemporary_mapping`
   - `stereotype` (form, signature, reference, theme_set)
   - `syntax` (form, sample)
   - `quality_parameters` (the metrics and their ratings)
   - `state`
3. Write (or update) `workspaces/pipeline/<bookname>/filters/quality/filter.md` with:
   - A header explaining that directives apply to **all chapters**.
   - A **context summary** — a compact table of each chapter's name, topic, theme, and quality parameters, so the human can see at a glance what they are reviewing.
   - An empty `## Instructions` section below a `---` line, where the human writes their quality directives.
4. **Preserve existing instructions.** If `filter.md` already contains human directives below the `---` line, keep them intact — only refresh the context summary above the line.

## Applying the Directives

1. Read the command file at `workspaces/pipeline/<bookname>/filters/quality/filter.md`.
2. If the `## Instructions` section is empty, audit the chapter against the seed analysis's quality parameters and pass it if it meets them.
3. If the instructions specify directives, apply them **exactly as written** to **every chapter** (unless a directive is scoped to a specific chapter).
4. Revise any chapter that falls short, looping back to an earlier filter (research, correctness, theme, syntax, override) if the root cause lies there.
5. **Promote the reviewed poem into the editor stage** — write the normalized,
   finalized poem to `chapters/<n>/segments/<m>/editor/segment.md` (archiving any
   prior editor copy) and mirror it into `chapters/<n>/segments/<m>/latest/segment.md`,
   then rebuild `chapters/<n>/chapter.md` from the editor poems.
6. Record the result in each chapter's model.

## Rules

- **Depth over cleverness** — prioritize genuine insight over wordplay.
- **Consistency** — the voice is maintained throughout.
- **Metaphorical coherence** — a seed metaphor is developed fully, not abandoned.
- **Subject grounding** — the chapter reflects the epic's story, not just style.
- **Emotional resonance** — the chapter moves the reader, not just informs.
- **Timelessness** — written as if it will be read a hundred years from now.
- **The human's word is final.** Apply the directives exactly; do not reinterpret or soften them.
- **Apply to all chapters.** An unscoped directive applies to every chapter (1 through N).
- **Float-segment scope.** A `<n>.<m>` target (e.g. `3.2`) audits and normalizes only
  segment `m` of chapter `n` (a `3.2-3.5` range selects several); the other segments'
  poems are preserved, and `chapter.md` is rebuilt from all reviewed editor-stage poems.
  A bare `<n>` or `all`/`*` still audits every segment of the scoped chapter(s).

## Editor Stage (review output)

Review **promotes** content into the editor stage — it never rewrites the writer
stage in place. Each reviewed segment poem is written to
`chapters/<n>/segments/<m>/editor/segment.md` (archiving the prior editor copy
first) and mirrored into `chapters/<n>/segments/<m>/latest/segment.md`. The writer
copy stays the raw draft. `publish` reads **only** the
`editor/` stage (and refreshes `latest/` from it); an un-reviewed segment has no
editor copy and is skipped by publish.

## Chapter Model

For each chapter, update `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json`. Preserve all existing fields, and add or update:

- `quality_review` — an object recording the result: `{ status, notes }`, where `status` is `"passed"` or `"revised"`, and `notes` is an array of the directives applied or defects fixed.
- `state` — set to `"completed"` once the quality filter passes.

Do not overwrite unrelated fields; merge the quality state into the existing model.

## Guardrails

- Work only in the named pipeline and its chapter models.
- Do not create or modify `workspaces/published/`.
- Do not run research, correctness, theme, syntax, or override.
- The result must remain a poetry chapter; do not apply novel-only sections or voices.

## Output

- **Command file** — create or update `workspaces/pipeline/<bookname>/filters/quality/filter.md`, generated from the chapter models' context.
- **Editor stage** — promote each reviewed segment poem to `chapters/<n>/segments/<m>/editor/segment.md` (archiving the prior copy), and rebuild `chapters/<n>/chapter.md` from the editor poems.
- **Chapter models** — update `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` with the `quality_review` result for each chapter. A chapter is `completed` only when this filter passes.
