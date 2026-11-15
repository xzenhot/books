# Form Discriminator

The form is declared once, at scaffold time, in the pipeline's `form` field
(`model.json`), and read everywhere else.

| Signal | Novel | Poetry |
|---|---|---|
| **`form` field** | `"novel"` | `"poetry"` |
| **Source of truth** | `storyline.md` (epic-driven) | `model.json` (the `chapters[]` array holds topics) |
| **Chapter structure** | flat, continuous prose | flat, continuous poetic prose |
| **Segments per chapter** | many (`segments/1`, `segments/2`, …) | explicit `segment_count` from the chapter plan; legacy default one |
| **`mood.json`** | present per chapter | absent (no moods) |
| **Filter chain** | preset-defined (`layout-novel/SKILL.md`) | preset-defined (`layout-poetry/SKILL.md`) |
| **Word target** | 5,500+ words | 500–800 words |
| **Stereotype templates** | `.framework/editor/novel/` | `.framework/editor/poetry/` |

The `form` field drives: stereotype template folder, filter chain, chapter
structure and word target, and the source-of-truth file. Poetry segment titles,
summaries, and per-segment word targets are generated during enrichment from the
chapter plan; each chapter's `segment_count` is declared in the backlog plan.
