---
name: enrich-novel
description: "Use when enriching a novel's chapters through the fused active filters in a single pass. Fuses the active filters from filters.json into one combined pass over each chapter's chapter.json, recording the fused enrichment guidance so the write agent can compose chapter.md. USE FOR: enriching novel chapters after scaffold, before write. DO NOT USE FOR: poetry (use enrich-poetry), or authoring prose (use novel)."
---

# Enrich Novel — Fuse the Active Filters

You enrich a **novel** pipeline's chapters. You do not apply filters yourself. Instead, you:

1. Read the active filter list from `filters.json`.
2. Fuse the active filter skills into **one combined pass**.
3. Execute that combined pass over each target chapter's metadata.
4. Record the enrichment result — a `chapter.json` annotated `enriched` and ready for the
   write agent to compose `chapter.md`. (You never author prose yourself.)

## Form

This skill applies to the **novel** form only. The novel filter chain is
`workshop → research → seeds → correctness → theme → syntax`, with `Introduction`,
`1..N`, and `Conclusion` chapters, moods per chapter, and a 5,500+ word target.

## Inputs

1. `workspaces/pipeline/<bookname>/filters/filters.json` — the authoritative filter list.
2. `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the chapter's metadata (the only per-chapter input).
3. `workspaces/pipeline/<bookname>/chapters/<n>/mood.json` — the chapter's mood (novel, optional).
4. The active filters' own outputs under `workspaces/pipeline/<bookname>/filters/<filter>/` — the fused guidance's source material.

**Style reference.** Ensure `workspaces/pipeline/<bookname>/style.md` exists (copy
`.framework/templates/stereotypes/poetry/styles/pijush/style.md` into it if missing,
without overwriting a human-edited file), then rewrite it from
`workspaces/pipeline/<bookname>/book.json` and `override.txt` so its subject matter
matches this book's story — re-grounding any stale/unrelated narrative to the current
book. Keep the voice/philosophy/register intact; only re-ground the "what". If
`override.txt` carries a transformation mandate, fold it in.

`chapter.md` is **not** an input here. It is an output file of the writing path; you
never read the chapter's current prose. You do **not** read the backlog or the epic.

## Step 1 — Resolve the Active Filters

Read `filters.json`. A filter is **active** when `autorun` is `true`. Build the active
list in `order` sequence. Treat `workshop` and `override` as always disabled for autorun.

```text
active = [ f for f in filters.json.filters if f.autorun == true ], sorted by f.order
```

For each active filter, note its skill path (e.g. `.framework/filters/workshop/SKILL.md`).
These are the skills you will fuse.

If `filters.json` is missing or has no active filters, stop with a clear error — there
is nothing to combine.

## Step 2 — Fuse the Active Skills

Read each active filter's `SKILL.md`. Extract its **task, method, and rules** — not its
identity prose or its output-file boilerplate. Combine them into a single ordered
instruction set:

- **Order matters.** The combined pass applies the filters in `order` sequence, each feeding the next.
- **One pass.** The combined pass reads the chapter's `chapter.json` once, applies every active filter's guidance in sequence, and writes the result once.
- **No per-filter files.** The combined pass does not write `content-input.md`, `content-output.md`, or per-filter summaries. It writes only the enrichment record in `chapter.json` and never reads or writes `chapter.md`; workshop alone may create that draft when it is absent, and writing agents own later revisions.

The combined pass's contract is:

1. Read `chapter.json` (never `chapter.md` — it is an output file, not a source).
2. Apply each active filter's guidance in `order` sequence to the chapter's metadata and the filters' own outputs.
3. Record the fused enrichment guidance in `chapter.json`.
4. Write nothing to `chapter.md`; the writing path owns that file.
5. Update `chapter.json` with the enrichment result (see Output).

## Step 3 — Execute the Combined Pass

Run the fused instruction set over each target chapter. The end product is a single
enriched `chapter.json`, recording that the chapter has passed through the fused filter
guidance in `order` sequence. The prose authoring is deferred to the write agent, which
reads this enrichment metadata and composes `chapter.md` accordingly.

- **Metadata-only** — the combined pass reads and writes `chapter.json`; it never reads or writes `chapter.md`.
- **Grounded** — every recorded fact and claim is traceable to the chapter's own `chapter.json` sources.
- **Form-correct** — the recorded enrichment states the target form `novel` for the downstream writer.
- **Ready** — no further filter pass is required before write or publish.

## Output

1. **Chapter model** — update `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` without dropping unrelated fields:
   - `state` — set to `"enriched"`.
   - `enrich` — an object recording the result: `{ active_filters: [...], status: "enriched" }`, where `active_filters` lists the fused filter names in order.

`chapter.md` is **not** written here; it is written only later by the writing agent. Do
not write to `workspaces/published/`. Do not create per-filter files. Do not overwrite unrelated
`chapter.json` fields.

## Report

Report the resolved active filters, the fused order, the chapters processed, and the
resulting `state`.
