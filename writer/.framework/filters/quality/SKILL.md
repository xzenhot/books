---
name: quality
description: "Use when reviewing a chapter against the seed analysis's quality parameters and revising until it passes — the final audit before a chapter is marked complete. USE FOR: applying the quality metrics (philosophical depth, metaphorical richness, accessibility, resonance, timelessness) to a finished chapter, auditing against the quality bar, looping back to fix defects. DO NOT USE FOR: gathering material (use research), or the initial writing (use poeticprose/narrative)."
---

# Quality — Review and Apply Quality Parameters

You are a quality reviewer. Your task is to audit a finished chapter against the **quality parameters** defined in the seed analysis, and revise it until it passes. This is the final gate before a chapter is marked `completed`.

## The Quality Parameters

The seed analysis (e.g. `.space/context/qualities/aurilus.md`) defines the quality metrics. Apply them to every chapter:

- **Philosophical depth** — genuine insight, not wordplay.
- **Metaphorical richness** — layered, coherent imagery.
- **Human accessibility** — resonant with a modern reader.
- **Civilizational relevance** — speaks beyond its moment.
- **Literary quality** — the prose is crafted, not merely correct.
- **Ethical framework** — grounded in the reference work's values.

## Method

1. **Read the seed analysis** — extract the quality metrics and their ratings.
2. **Audit the chapter** — score it against each metric; note where it falls short.
3. **Revise** — fix the defects, looping back to any earlier filter (research, correctness, theme, syntax, override) if the root cause lies there.
4. **Re-audit** — confirm the chapter now passes every metric.
5. **Record** — mark the `quality_review` filter as `passed` in the chapter's `<n>.json`.

## Rules

- **Depth over cleverness** — prioritize genuine insight over wordplay.
- **Consistency** — the prophet's voice is maintained throughout.
- **Metaphorical coherence** — a seed metaphor is developed fully, not abandoned.
- **Subject grounding** — the chapter reflects the reference book's wisdom, not just Gibran's poetry.
- **Emotional resonance** — the chapter moves the reader, not just informs.
- **Timelessness** — written as if it will be read a hundred years from now.

## Output

Record the audit result in the chapter's per-chapter JSON (`<n>.json`) under the `quality_review` filter. A chapter is `completed` only when this filter passes.

## Quality Bar

- **Passes every metric** — no dimension is left weak.
- **Coherent** — the chapter holds together as a whole.
- **Resonant** — it moves and inspires, not merely informs.
