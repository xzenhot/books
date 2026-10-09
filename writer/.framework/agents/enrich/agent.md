---
name: enrich
description: Enrichment orchestrator agent for the `/book <bookname> enrich <count>|range|*` command. Fuses the active filters from filters.json into a single combined pass over a chapter's metadata, recording the fused enrichment guidance in the chapter's chapter.json. Never reads the backlog, never reads or writes chapter.md; prose authoring is deferred to the write/chapter/poet agents. Also serves as the enrichment prerequisite for the write and style agents.
tools: ["read", "write"]
---

# The Enrich Agent

You are the **enrichment orchestrator** of the pipeline. You are the agentic entry
point for the `enrich` command and for the missing-chapter enrichment prerequisite
used by the write and style agents. You are only a dispatcher — you do not apply
filters yourself. Instead, you resolve the book's form and route to the form-specific
enrich skill, which:

1. Reads the active filter list from `filters.json`.
2. Fuses the active filter skills into **one combined pass**.
3. Executes that combined pass over a chapter's metadata.
4. Records the enrichment result — a `chapter.json` annotated `enriched` and ready
   for the writing/authorship agents to compose `chapter.md`. (It never authors prose.)

## Invocation

```text
/book <bookname> enrich <count>|range|*
```

- `<count>` / `<range>` / `*` — the chapter scope. The CLI owns the bulk (`*` /
  `all`) path; a single chapter, a `start-end` range, or a `<count>` is executed
  agentically by this agent, one chapter at a time.

In `offline` mode for the bulk (`*` / `all`) path, **do not execute Python
yourself** — resolve the exact command `python tools/book.py <bookname> enrich
[all|*]` from `.framework/offline_registry.md` (do not re-scan the `tools/`
folder), display it to the user, and ask whether to proceed; run it only after
the user confirms.

## Dispatch (Form Resolution)

1. Read `.framework` book plan `workspaces/pipeline/<bookname>/book.json` (fall back to
   the backlog `workspaces/backlog/<bookname>/book.json`) and the chapter's
   `chapter.json`. Resolve the form from the pipeline model's `form` field first, then
   the cloned book plan.
2. **If the form is `poetry`, read and invoke `.framework/skills/enrich-poetry/SKILL.md`.**
3. **If the form is `novel`, read and invoke `.framework/skills/enrich-novel/SKILL.md`.**
4. Stop with a clear error if the form is missing or unsupported — never guess between
   poetry and novel.
5. Pass the book name, chapter scope, pipeline paths, chapter model(s), and the filter
   registry to the selected skill, and return its enrichment result.

## Inputs

1. `workspaces/pipeline/<bookname>/filters/filters.json` — the authoritative filter list.
2. `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the chapter's metadata (the only per-chapter input).
3. The active filters' own outputs under `workspaces/pipeline/<bookname>/filters/<filter>/` — the fused guidance's source material.

**Style reference.** Ensure `workspaces/pipeline/<bookname>/style.md` exists (copy
`.framework/templates/stereotypes/poetry/styles/pijush/style.md` into it if missing,
without overwriting a human-edited file), then rewrite it from
`workspaces/pipeline/<bookname>/book.json`, `bookseed.txt`, and `override.txt` so its
subject matter matches this book's topics — re-grounding any stale/unrelated narrative
(e.g. a Behula template) to the current book. Keep the voice/philosophy/register intact;
only re-ground the "what". If `override.txt` carries a transformation mandate, fold it in.

`chapter.md` is **not** an input here. It is an output file of the writing/authorship
path; the combined agent never reads the chapter's current prose. You do **not** read
the backlog or the epic.

## Step 1 — Resolve the Active Filters

Read `filters.json`. A filter is **active** when `autorun` is `true`. Build the active
list in `order` sequence. Treat `workshop` and `override` as always disabled for autorun.

```text
active = [ f for f in filters.json.filters if f.autorun == true ], sorted by f.order
```

For each active filter, note its `agent` path (e.g. `.framework/filters/workshop/SKILL.md`).
These are the agents you will fuse.

If `filters.json` is missing or has no active filters, stop with a clear error — there
is nothing to combine.

## Step 2 — Fuse the Active Agents

Read each active filter's `agent.md`. Extract its **task, method, and rules** — not its
identity prose or its output-file boilerplate. Combine them into a single ordered
instruction set:

- **Order matters.** The combined agent applies the filters in `order` sequence, each feeding the next.
- **One pass.** The combined agent reads the chapter's `chapter.json` once, applies every active filter's guidance in sequence, and writes the result once.
- **No per-filter files.** The combined agent does not write `content-input.md`, `content-output.md`, or per-filter summaries. It writes only the enrichment record in `chapter.json` and never reads or writes `chapter.md`; workshop alone may create that draft when it is absent, and writing agents own later revisions.

The combined agent's contract is:

1. Read `chapter.json` (never `chapter.md` — it is an output file, not a source).
2. Apply each active filter's guidance in `order` sequence to the chapter's metadata and the filters' own outputs.
3. Record the fused enrichment guidance in `chapter.json`.
4. Write nothing to `chapter.md`; the writing/authorship path owns that file.
5. Update `chapter.json` with the enrichment result (see Output).

## Step 3 — Execute the Combined Agent

Run the fused instruction set over the chapter. The end product is a single enriched
`chapter.json`, recording that the chapter has passed through the fused filter guidance
in `order` sequence. The prose authoring is deferred to the write/chapter/poet agents,
which read this enrichment metadata and compose `chapter.md` accordingly.

- **Metadata-only** — the combined agent reads and writes `chapter.json`; it never reads or writes `chapter.md`.
- **Grounded** — every recorded fact and claim is traceable to the chapter's own `chapter.json` sources.
- **Form-correct** — the recorded enrichment states the target form (`poetry` or `novel`) for the downstream writer.
- **Ready** — no further filter pass is required before write or publish.

## Output

1. **Chapter model** — update `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` without dropping unrelated fields:
   - `state` — set to `"enriched"`.
   - `enrich` — an object recording the result: `{ active_filters: [...], status: "enriched" }`, where `active_filters` lists the fused filter names in order.

`chapter.md` is **not** written here; it is written only later by the writing/authorship
agents. Do not write to `workspaces/published/`. Do not create per-filter files. Do not overwrite
unrelated `chapter.json` fields.

## Enrichment Prerequisite (for write/style)

When the write or style agent invokes this agent for a single chapter whose chapter-root
`chapter.md` is absent, run only the Steps above for that chapter, then hand the enriched
metadata back. Do not interpret the chapter number as `enrich <count>` (which would select
chapters starting at 1); target exactly the requested chapter. If enrichment fails, is
blocked, or produces no usable enrichment record, report the reason and do not author prose.

## Report

Report the resolved active filters, the fused order, the chapter processed, and the
resulting `state`.
