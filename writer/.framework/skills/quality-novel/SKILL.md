---
name: quality-novel
description: Review a novel chapter against the seed analysis's quality parameters and revise until it passes — the final audit before a chapter is marked complete. Generates (or updates) the human-editable filter.md from the chapter models' context, then applies the human's quality directives to all chapters.
---

# Novel Quality — Review and Apply Quality Parameters

Use this skill for a novel pipeline to audit a finished chapter against the **quality parameters** defined in the seed analysis, and revise it until it passes. This is the final gate before a chapter is marked `completed`.

## Your Task

1. **Generate the command file** — create (or update) the human-editable `filter.md` from the chapter models' context, so the human has a ready-made, context-aware template to write quality directives into.
2. **Apply the human's directives** — read the human's quality instructions from `filter.md` and apply them to **every chapter**.

## The Quality Parameters

Apply the seed analysis's quality metrics to every chapter:

- **Philosophical depth** — genuine insight, not wordplay.
- **Metaphorical richness** — layered, coherent imagery.
- **Human accessibility** — resonant with a modern reader.
- **Civilizational relevance** — speaks beyond its moment.
- **Literary quality** — the prose is crafted, not merely correct.
- **Ethical framework** — grounded in the epic's values.

## Generating the filter.md (Runtime, Context-Aware)

The `filter.md` is **generated from the chapter models** — it is not a static template. At runtime, read the chapter models and populate the file with the book's actual context, so the human's directives are grounded in what the chapters actually contain.

1. Read the book plan at `.space/pipeline/<bookname>/book.json` (falling back to `model.json`) for the book name and chapter list.
2. Read each chapter model at `.space/pipeline/<bookname>/chapters/<n>/chapter.json` to gather the context:
   - `chapter_index`, `chapter_name`, `chapter_title`
   - `subject`, `era`, `place`, `figures`, `events`
   - `theme`, `contemporary_mapping`
   - `stereotype` (form, signature, reference, theme_set)
   - `syntax` (form, sample)
   - `quality_parameters` (the metrics and their ratings)
   - `state`
3. Write (or update) `.space/pipeline/<bookname>/filters/quality/filter.md` with:
   - A header explaining that directives apply to **all chapters**.
   - A **context summary** — a compact table of each chapter's name, subject, theme, and quality parameters, so the human can see at a glance what they are reviewing.
   - An empty `## Instructions` section below a `---` line, where the human writes their quality directives.
4. **Preserve existing instructions.** If `filter.md` already contains human directives below the `---` line, keep them intact — only refresh the context summary above the line.

## Applying the Directives

1. Read the command file at `.space/pipeline/<bookname>/filters/quality/filter.md`.
2. If the `## Instructions` section is empty, audit the chapter against the seed analysis's quality parameters and pass it if it meets them.
3. If the instructions specify directives, apply them **exactly as written** to **every chapter** (unless a directive is scoped to a specific chapter).
4. Revise any chapter that falls short, looping back to an earlier filter (research, correctness, theme, syntax, override) if the root cause lies there.
5. Record the result in each chapter's model.

## Rules

- **Depth over cleverness** — prioritize genuine insight over wordplay.
- **Consistency** — the voice is maintained throughout.
- **Metaphorical coherence** — a seed metaphor is developed fully, not abandoned.
- **Subject grounding** — the chapter reflects the epic's story, not just style.
- **Emotional resonance** — the chapter moves the reader, not just informs.
- **Timelessness** — written as if it will be read a hundred years from now.
- **The human's word is final.** Apply the directives exactly; do not reinterpret or soften them.
- **Apply to all chapters.** An unscoped directive applies to every chapter (1 through N).

## Chapter Model

For each chapter, update `.space/pipeline/<bookname>/chapters/<n>/chapter.json`. Preserve all existing fields, and add or update:

- `quality_review` — an object recording the result: `{ status, notes }`, where `status` is `"passed"` or `"revised"`, and `notes` is an array of the directives applied or defects fixed.
- `state` — set to `"completed"` once the quality filter passes.

Do not overwrite unrelated fields; merge the quality state into the existing model.

## Guardrails

- Work only in the named pipeline and its chapter models.
- Do not create or modify `source/books/`.
- Do not run research, correctness, theme, syntax, or override.
- The result must remain a novel (prose) chapter; do not apply poetry-only sections or voices.

## Output

- **Command file** — create or update `.space/pipeline/<bookname>/filters/quality/filter.md`, generated from the chapter models' context.
- **Chapter models** — update `.space/pipeline/<bookname>/chapters/<n>/chapter.json` with the `quality_review` result for each chapter. A chapter is `completed` only when this filter passes.
