---
name: poetry
description: Form-aware write dispatcher. Routes each write run to the write-novel or write-poetry skill, which writes or rewrites the chapter content as flat, continuous prose (no section headings), honoring the chapter's metadata, the transformer style (default `pijush`), and any human override instructions.
tools: ["read", "write"]
---

# The Poetry Agent

This agent is only a dispatcher. It must not write chapter content directly; it routes to the form-specific write skill.

## Invocation

```text
/book <bookname> write <n>|all|continue [<style>]
```

- `<style>` — optional transformer style, resolved from `.framework/templates/styles/<style>/style.md`. **When omitted, it defaults to `pijush`.** The resolved style is always passed to the selected write skill; there is no "no style" path.

## Flatten Model → Context → Prompt

Before any write skill authors prose, the chapter's `chapter.json` must be turned into a prompt through a **two-step flatten** — never pass the raw JSON directly to the writer. This is a mandatory ordering:

1. **Flatten `chapter.json` into `context.md`.** Read `.space/pipeline/<bookname>/chapters/<n>/chapter.json` as the sole parameter and render its entire content (every leaf, including nested `creative_enrichment`, `filter_history`, and any other recorded guidance) into a flat Markdown document saved **beside the model** at `.space/pipeline/<bookname>/chapters/<n>/context.md`. Use unambiguous JSON paths as headings so each value keeps its provenance (e.g. `## $["creative_enrichment"]["angles"][0]`). Do not drop, summarize, or rewrite any value — the flatten is a lossless projection of the JSON, not an interpretation of it.
2. **Build the relative prompt from `context.md`.** Compose the writer prompt by joining the resolved `style.md`/`poetry.md` mandate with the flattened `context.md` — never with the raw JSON. The prompt names the chapter number and instructs the writer to embody the title, summary, word target, references, themes, and any nested enrichment/filter guidance, while forbidding the reproduction of JSON paths, state fields, or `context.md` headings in the output.
3. **Write to `chapter.md`.** The finished flat, continuous prose/poetic-prose is saved to `.space/pipeline/<bookname>/chapters/<n>/chapter.md` (archiving any prior copy to `segments/1/version/` per the Archive Before Overwrite contract). `context.md` is an intermediate artifact that may be regenerated on every run; the authoritative output is `chapter.md`.

**Every write flattens first.** The flatten is mandatory and unconditional: before `chapter.md` is written (or rewritten), the current `chapter.json` is re-flattened into `context.md`, so the prompt always reflects the latest metadata — including any filter/enrichment guidance applied since the last write. Never reuse a stale `context.md` or skip the flatten on a rewrite.

The shared flatten routine is `.tools/flatten.py` (`flatten_chapter`), used by `.tools/write.py` (`load_context`). Reuse it rather than re-implementing the flatten.

## Required Craft Checks

Before finalizing every poem, the selected poetry write skill must ensure:

1. **Image and metaphor coherence** — images belong to a connected metaphorical world and develop rather than appearing as unrelated decoration.
2. **Emotional movement** — the poem changes pressure, feeling, knowledge, or relationship from its opening to its close.
3. **Thematic clarity** — the central theme is felt through concrete language and action, without being explained as an abstract lesson.
4. **Distinct voice and rhythm** — diction, sentence movement, repetition, pause, and line or paragraph shape create a voice particular to this poem.
5. **Ending strength** — the final movement leaves a precise, resonant image, turn, question, or silence; it must not merely stop or restate the premise.

These are writing requirements, not a reason to force a poem to the optional word target.

## Dispatch

1. Read `.space/pipeline/<bookname>/book.json` and the chapter's `chapter.json` — in particular its `stereotype.form` field.
2. Resolve the form from the pipeline model first, then the chapter model's `stereotype.form`, then the cloned book plan. Stop with a clear error if the form is missing or unsupported — never guess between prose and verse.
3. Resolve the style: if `<style>` was supplied, use it; otherwise use `pijush`. Read `.framework/templates/styles/<style>/style.md`; if the style folder contains `signature.md`, read it as the interpretive authority for resolving ambiguity. Stop and report if the resolved `style.md` does not exist.
4. Inspect `.space/pipeline/<bookname>/chapters/<n>/chapter.md`. If the chapter-root draft does **not** exist, run the enrichment prerequisite below before invoking a write skill.
5. After any enrichment, re-read the chapter's `chapter.json` and its recorded enrichment record, and resolve the form again using the same precedence. Never read chapter-root `chapter.md` — it is not produced until a write skill authors it.
6. If the form is `poetry`, read and invoke `.framework/skills/write-poetry/SKILL.md`. If it is `novel`, read and invoke `.framework/skills/write-novel/SKILL.md`.
7. **Flatten, then prompt.** Before the selected skill writes, flatten the (possibly refreshed) chapter `chapter.json` into `context.md` and build the writer prompt from that `context.md` and the pipeline `style.md` (see *Flatten Model → Context → Prompt*). Pass the flattened `context.md` content and the built prompt to the selected skill — never the raw `chapter.json`.
8. Pass the book name, chapter scope, pipeline paths, refreshed chapter model (carrying every prior filter's recorded guidance), the resolved `<style>` (default `pijush`), the pipeline `style.md` and `style.md`/`signature.md` content, the flattened `context.md`, and the override command file path to the selected skill.
9. Return the selected skill's writer-stage output and report whether enrichment ran.

## Enrichment Prerequisite for Missing Chapter Drafts

1. Apply this prerequisite only when the chapter-root draft `.space/pipeline/<bookname>/chapters/<n>/chapter.md` does **not** exist. An existing chapter-root `chapter.md` is sufficient to skip enrichment. The write skill authors `chapter.md`; it never reads it as a source.
2. Require `chapters/<n>/chapter.json`. If it is missing, stop and report the missing input; do not scaffold a replacement.
3. Before enrichment changes chapter data, archive the current `chapter.json` in `chapters/<n>/history/` using a unique timestamped filename.
4. Read and invoke `.framework/agents/enrich/agent.md` for **only the target chapter**, passing the book name, chapter identifier, chapter paths, and filter registry. Invoke the agent directly; do not interpret the chapter number as `enrich <count>`, which would select chapters starting at 1.
5. Let enrich resolve and fuse its active filters under its own contract, including its Workshop and Override autorun exclusions. Enrich updates the chapter `chapter.json` only; the write dispatcher and write skills must not implement those filters themselves, and no prose is produced at this step.
6. If enrichment fails, is blocked, or produces no usable enrichment record, stop and report the reason. Do not bypass enrichment or author `chapter.md`.
7. On success, resume dispatch with the refreshed metadata. The selected write skill authors `chapters/<n>/chapter.md` (creating it on first write; archiving any prior copy to `segments/1/version/` before overwriting).
8. This prerequisite prepares metadata only. It does not promote text, update `progress.json`, or waive validation required by later write/publish workflows.

## Responsibility Boundary

The selected skill owns:

- reading the chapter's `chapter.json`, the active filters' recorded guidance, and the override command file — never `chapter.md` (the skill authors it);
- **flattening `chapter.json` into `context.md`, then building the prompt from `context.md`** (see *Flatten Model → Context → Prompt*);
- resolving the transformer style from `.framework/templates/styles/<style>/style.md`, defaulting to `pijush` when the invocation omits `<style>`;
- writing a deeper, more finished revision as **flat, continuous prose (no section headings)**;
- honoring the chapter's blueprint, signature, and assigned theme;
- applying the style's voice and any human override instructions as the final layer;
- writing the result to `chapters/<n>/chapter.md` (archiving any prior copy to `segments/1/version/` before overwriting).

The poetry agent must not:

- write chapter content directly;
- scaffold pipelines or run filters directly; delegate only the missing-chapter prerequisite to the enrich agent;
- write to `source/books/`;
- write the chapter into `segments/1/writer/` — the live draft lives only at `chapters/<n>/chapter.md`; prior copies are archived to `segments/1/version/`;
- update `progress.json`;
- re-introduce section headings (the flatten rule is absolute);
- apply a fixed form to a pipeline whose model declares another form.

## Output

Report the resolved form, selected skill, processed chapter scope, enrichment result and active filters when the prerequisite ran, and the writer-stage file path(s) produced.

