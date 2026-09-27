---
name: theme-poetry
description: Assign a poetry chapter its thematic lens and stereotype (signature, reference, theme set) from the chapter's own metadata, using the poetry stereotype templates. Reads only the chapter's model.json — never the backlog, never chapter.md.
---

# Poetry Theme — The Philosophical Lens

Use this skill for a poetry pipeline to assign one chapter its **theme** (the philosophical lens) and one **stereotype** (signature, reference, theme set). Work only from the chapter's own metadata.

## Inputs (only these)

1. `.space/pipeline/<bookname>/chapters/<n>/chapter.json` — the chapter's metadata. This is the only per-chapter input; `chapter.md` is an output file owned by the write path and is never read.

Everything you need is in the chapter model.

## What a Theme Is

A theme is not a topic or a plot point. It is a **lens** — a recurring idea that shapes how the subject is rendered. Each chapter gets one theme, embodied through image and cadence, never stated outright.

## Method

1. Read the chapter's `model.json`.
2. Confirm the form is `poetry` (from `model.json` → `syntax.form` or the pipeline model).
3. Select the **signature**, **reference**, and **theme set** from the poetry stereotype templates:
   - `.framework/templates/stereotypes/poetry/signatures/`
   - `.framework/templates/stereotypes/poetry/references/`
   - `.framework/templates/stereotypes/poetry/themes/`
   - Read the `registry.md` in each folder to discover what is available, then read the chosen files.
4. Assign the chapter its theme, and map it onto a present-day concern.
5. Record the stereotype in `model.json` (see Output).

The three selections must be **mutually consistent** — all from the poetry form, and where possible the same author or tradition.

## Weaving a Theme (Not Stating It)

- **Embody, don't explain.** Show the theme through image and cadence.
- **Return to the metaphor family** throughout the chapter.
- **Let the theme shape the opening question and the closing benediction.**
- **Honor the signature** — the chosen voice's movement, motifs, and diction should carry the theme.

## Output

Update the chapter's `model.json` by adding (or updating) a `stereotype` object:

```json
{
  "stereotype": {
    "form": "poetry",
    "signature": "gibran",
    "reference": "aurilus.txt",
    "theme_set": "generic.md"
  }
}
```

- **`form`** — `"poetry"`, matching the template directory used.
- **`signature`** — the folder name under `stereotypes/poetry/signatures/`.
- **`reference`** — the file name under `stereotypes/poetry/references/`.
- **`theme_set`** — the file name under `stereotypes/poetry/themes/`.

If `model.json` already has a `stereotype` object, update it in place; otherwise add it as a new top-level key. Do not overwrite the other fields in `model.json`.

## Guardrails

- Work only in the named pipeline and its chapter model.
- Do not read the backlog or the epic.
- Do not create or modify `source/books/`.
- Do not run research, correctness, syntax, override, or quality.
- The result must remain a poetry chapter; do not apply novel-only sections or voices.
