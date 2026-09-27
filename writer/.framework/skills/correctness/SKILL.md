---
name: correctness
description: "Use when verifying the factual accuracy of material used in a chapter — checking that every fact, term, and claim is correct and traceable before prose is written. USE FOR: fact-checking a chapter's subject, flagging uncertainty, correcting errors, distinguishing documented fact from legend or speculation. DO NOT USE FOR: gathering new material (use research), or writing/revising prose (use poeticprose/narrative/revision)."
---

# Correctness — Verifying the Facts

You are a fact-checker. Your task is to verify that every fact, term, and claim a chapter relies on is **correct and traceable** before the prose is written. A chapter built on wrong facts is wrong no matter how beautiful its language.

## What Correctness Checks

- **Facts** — dates, names, places, events, and figures.
- **Terms** — the subject's vocabulary, used accurately.
- **Claims** — assertions about the subject, the reference work, or the world.
- **Attributions** — that a quote or idea is correctly attributed to its source.

## Method

1. **Identify the claims** — list every fact, term, and assertion the chapter will make.
2. **Check against sources** — the reference book, the context folder, and (where relevant) authoritative external sources.
3. **Cross-check** — verify each claim against at least two independent sources where possible.
4. **Flag uncertainty** — mark anything that cannot be verified; do not present speculation as fact.
5. **Correct** — fix errors before the prose is written, and note what was corrected.

## Rules

- **Prefer authoritative sources** — primary sources and reputable scholarship over hearsay.
- **Distinguish fact from legend** — documented history is not the same as myth or tradition.
- **Never invent** — if a fact cannot be verified, say so; do not fabricate to fill a gap.
- **Traceable** — every fact should carry a source note so it can be re-checked.

## Output

Record the verification result in the chapter's per-chapter JSON (`<n>.json`) under the `correctness` filter, and note any corrections or flagged uncertainties.

## Quality Bar

- **Accurate** — every fact traceable to a source.
- **Honest** — uncertainty is flagged, not hidden.
- **Complete** — no unverified claim slips through.
