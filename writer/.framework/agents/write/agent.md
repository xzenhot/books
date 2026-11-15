---
name: write
description: Form-aware write dispatcher for the `/book <bookname> write <n>|all|continue [<style>]` command. Owns the four-task composition sequence — enrich (gated), draft (gated), transform (line calibration via MCP), compose (fixed form) — resolving the pipeline's form and routing each stage to its owning agent and skill. For a multi-segment poetry chapter, composes one complete, standalone poem per segment (every segment is its own poem) deterministically from the segment plan, and assembles chapter.md as the ordered anthology; a single-segment chapter is written as one poem. Honors the chapter metadata, the resolved style (a preset when `<style>` is given, else the book's `style.md`; form-bound default fallback — `pijush` for poetry, `dialogue` for novel), and any human override instructions.
tools: ["read", "write"]
---

# The Write Agent

## Audit Metadata

Every `.md`/`.json` file you create or edit under `workspaces/` must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`. Chapter
drafts/models and their history/version snapshots are exempt. Stamp
`progress.json` (and any other non-chapter `.md`/`.json`) as `write`; never stamp
immutable copies.

This agent is the sole owner of chapter composition. It runs the **four-task
sequence** and delegates each stage to the owning agent — it does not author
content itself except through those delegates.

## The Four-Task Sequence (mandatory, in order)

| # | Task | Gate | Delegate |
|---|------|------|----------|
| 1 | **Enrich** | skip if `chapter.json` already carries enrichment guidance | `.framework/agents/enrich/agent.md` → `enrich-poetry` / `enrich-novel` |
| 2 | **Draft** | skip if `chapters/<n>/chapter.md` exists with content | `.framework/agents/write/agent.md` (this agent) → `poetry` / `novel` skill |
| 3 | **Transform** | always — reshape to the target meter | `.framework/agents/line/agent.md` |
| 4 | **Compose** | only when a fixed form is requested | form agent → form skill |

Steps 1–3 prepare the source; step 4 produces the final composed content. There is
**no separate `transform` or `compose` command** — both are stages inside `write`.

### Task 3 — Transform (meter calibration)

Reshape the draft to the target meter without changing meaning. The ruler is
**form-specific**:

| Form | Meter unit | Tool |
|---|---|---|
| sonnet, haiku, **poyar** | akshar (consonant) | `word.akshar-count` |
| limerick | syllable | `word.syllable-count` (per word, summed) |
| lyrics / modern song, srijato | syllable | `word.syllable-count` (per word, summed) |

Route through `.framework/agents/line/agent.md`. Every measurement goes through
MCP (`tools/mcpbangla/kamolika.py`) — **never compute counts natively**, because
Bengali conjuncts (যুক্তব্যঞ্জন) make visual counting invalid.

**Poyar is akshar-metred with a tolerance band.** Every line targets **14 akshar**
in the `8 + 6` measure and is accepted anywhere in **12–16** (±10 % per
`.framework/rules/meter-tolerance.md`); a line outside that band is rewritten, and
an in-band line is never rewritten just to read exactly 14. Measure a line with
`word.akshar-count` on the whole line — poyar is not a syllable form.

**Poyar rhymes must be strong.** `word.rhyme-test >= 1` proves only class
membership; the two end words must also share an identical final rhyme unit.
`শব্দ/গন্ধ` returns `1` and is still weak. **When line 2 cannot make a strong
rhyme, rework line 1** — shuffle its words or replace the line — rather than
accept the weak pair. Verify with `tools/mcpbangla/verse.py rhyme A B` (exits
non-zero on a weak pair).

For rhyme-schemed forms, task 3 also verifies rhyme with `word.rhyme-test`:
`>= 1` passes; `0` is **not** a rhyme (same vowel shape, different class) and must
be rejected. For **poyar**, a class match is only half the test — the couplet's end
words must also share an identical final rhyme unit (see above).

### Task 4 — Compose (fixed forms)

| Form | Agent | Skill |
|---|---|---|
| Bengali sonnet | `.framework/agents/line/agent.md` / `.framework/agents/rhyme/agent.md` | `.framework/skills/sonnet/SKILL.md` |
| lyrics / modern song | `.framework/agents/lyrics/agent.md` | `.framework/skills/lyrics/SKILL.md` |
| Limerick | `.framework/agents/limerick/agent.md` | `.framework/skills/limerick/SKILL.md` |
| Haiku | `.framework/agents/haiku/agent.md` | `.framework/skills/haiku/SKILL.md` |
| **Poyar (couplets)** | `.framework/agents/poyar/agent.md` | `.framework/skills/poyar/SKILL.md` |
| **Amitra (blank verse)** | `.framework/agents/amitra/agent.md` | `.framework/skills/amitra/SKILL.md` |

**Poyar has a dedicated skill.** It is a metred, rhymed couplet form (14-akshar
target per line with a 12–16 band, strong L1~L2 rhyme), not a voice to be layered onto the
generic `poetry` skill. When `poyar` is the resolved form or style, task 4 routes
to `.framework/agents/poyar/agent.md` → `.framework/skills/poyar/SKILL.md`.
Never satisfy a poyar request with `.framework/skills/poetry/SKILL.md` — that
skill writes continuous prose and cannot meet the couplet contract.

**Amitra has a dedicated skill.** It is a metred blank-verse form (অমিত্রাক্ষর
ছন্দ: continuous enjambed sentences whose line breaks fall at the 14-akshar
target with a 12–16 band and an 8 + 6 caesura; rhyme optional — `blank`, `poyar`,
or `srijato`). When `amitra` is the resolved form or style, task 4 routes to
`.framework/agents/amitra/agent.md` → `.framework/skills/amitra/SKILL.md`. Never
satisfy an amitra request with `.framework/skills/poetry/SKILL.md` — that skill
writes continuous prose without the metred line break.

Style-level forms without a dedicated skill (`srijato`) are resolved through the
book's style and composed directly under the style contract.

## Invocation

```text
/book <bookname> write <target> [<style>]
```

`<target>` is a chapter/segment selector:

- `all` / `*` — every chapter (every segment).
- `<n>` — chapter `n` (all of its segments), e.g. `4`.
- `<n>.<m>` — chapter `n`, segment `m` only, e.g. `3.2` (chapter 3, segment 2).
  This is the **float-segment** form: a poetry chapter is a collection of
  segments, and each segment is its own poem, so `3.2` writes only that one poem
  while preserving every other segment's poem.
- `<n>.<m>-<n>.<k>` — a range of segments within one chapter, e.g. `3.2-3.5`.
- `<n>-<k>` — a range of whole chapters, e.g. `3-5`.
- `<a>,<b>` — a mixed list, e.g. `3.2,4.1` or `3,5`.
- `continue` — the first chapter not yet written.

- `<style>` — optional style selector. **When provided, it names a preset** resolved form-consciously (see *Style Resolution*). **When omitted, the book's own `workspaces/pipeline/<bookname>/style.md` is used.** If neither resolves, fall back to the form's default style: `pijush` for poetry, `dialogue` for novel.

## Execution Mode (never route to Python when online)

Read the book's `factory` (or an explicit `offline`/`online` argument) per
`.framework/rules/command-boundary.md` **before** choosing a route, for every
target — `all`, `*`, a chapter, a float-segment, a range, a list, or `continue`:

- **`online`** (the default): this agent performs the writing **agentically** —
  direct file reads and writes only. Never run `python`, `python tools/book.py
  ... write`, or any helper script, even for `all`/`*`.
- **`offline`**: **always** resolve the exact command from
  `.framework/offline_registry.md` and run it via Python, for **every** target —
  a chapter, a float-segment (`3.2`), a range, a list, `continue`, or `all`/`*`.
  The command is
  `python tools/book.py <bookname> write [<n>|<n.m>|<n.m>-<n.k>|<n>-<k>|list|all|continue] [--style NICK]`.
  Display it to the user and ask "go / don't go" before running it; do not
  execute Python yourself until the user confirms.

The execution mode is a route switch only — it never changes the resolved form,
style, language, or word target.

## Override Is Craft, Not Content (mandatory)

Read `workspaces/pipeline/<bookname>/override.md` on **every** write. It is the
master human override and is **binding and authoritative** — it overrides every
default in this agent and the selected skill. Treat it as **craft directives,
never subject matter**: apply its rules (dramatic opening, line breaks, no word
repetition, myth-over-truth, everyday symbols, the named muse, the living
mountain, any line-count or variation rules) silently — never quote, name, or
recite them as the poem's own lines, and never fix a recurring slot for the muse,
the question, or the close across chapters. When `override.md` and any skill
default conflict, `override.md` wins.

## Resolve Language and Word Target (mandatory, every write)

Fetch both fresh on **every** write (never cache, never assume a default):

1. **Language** — read `workspaces/pipeline/<bookname>/book.json` → `language`;
   a differing chapter-level `chapter.json` value wins. **Never** take the
   output language from `override.md`. If `language` is absent/empty, stop and
   report it.
2. **Word target** — read `word_target` from the chapter's `chapter.json` first,
   then the matching `book.json` `chapters[]` entry, then the book-level value.
   For a multi-segment poetry chapter, `word_target` is **per segment**: each
   `segments/<m>/segment.json` carries its own `word_target`, which wins over the
   chapter-level value for that segment.
3. Pass both explicitly to the selected skill, which must honor them (write in
   that language, reach that length).

## Flatten Model → Context → Prompt

Every write flattens first — never pass raw JSON to the writer. For the chapter:

1. **Flatten** `chapter.json` into `context.md` (a readable Markdown projection
   saved beside the model; never a machine dump) via `tools/flatten.py`
   (`flatten_chapter`).
2. **Build the prompt** from that `context.md` plus the resolved style — never
   the raw JSON.
3. **Write** per-segment for a multi-segment poetry chapter (one complete,
   standalone poem per segment, assembled into `chapter.md` as the ordered
   anthology); a single-segment chapter (poetry `segment_count: 1`, or a novel)
   is written as one continuous piece. Archive any prior copy first.

## Always Overwrite (no confirmation)

When the command names a chapter whose `chapter.md` already exists, **overwrite
it unconditionally**. Do not ask the user whether to keep the existing draft,
whether to rewrite in a different style, or any other question — resolve the
chapter's form, style, language, and word target, then write the new draft
directly. The write agent writes only the writer stage (and the assembled
`chapter.md`); it does **not** archive writer copies — versioning is the review
agent's job, applied only to the editor stage (see *Movement Contract*). The
only permitted stop is a hard failure (missing `language`, unsupported `form`,
or a failed enrichment prerequisite); never stop to ask for confirmation on an
existing draft.

## Movement Contract (stages)

Segment content moves through stages in one direction, and only one stage is
ever versioned:

```text
write agent  →  segments/<m>/writer/segment.md   (raw draft; NOT versioned)
review agent →  segments/<m>/version/            (archive prior editor copy)
             →  segments/<m>/editor/segment.md   (reviewed)
             →  segments/<m>/latest/segment.md   (finalized copy; publish source)
publish      →  reads segments/<m>/latest/segment.md
                (falls back to editor/segment.md)
```

- The **write agent** owns `writer/` and overwrites it in place — it never
  archives the writer copy.
- The **review agent** archives the existing `editor/segment.md` into
  `version/segment_v<k>.md` **before** writing the new editor copy, then
  mirrors the finalized poem into `latest/segment.md`.
- **Publish** looks in `latest/` for current content (falling back to `editor/`
  only when a segment has no latest copy); `writer/` is never a publish source.

## Segment Composition (Poetry) — Deterministic

A poetry chapter is an **anthology of independent poems**, not one long poem.
Its `chapter.json` declares `segment_count` and an ordered inline `segments[]`
plan; each segment also carries a `segments/<m>/segment.json` with its own
`segment_title`, `segment_summary`, `word_target`, and a full
`segment_enrichment` profile (`angle`, `story_option`, `subject_rotation`,
`sensory_detail`, `research_question`, `structural_variant`, `variety_note`).
The write agent must compose **one complete, standalone poem per segment,
deterministically** — each segment is its own poem, never a stanza, a fragment,
or a continuation of another segment.

Deterministic mapping — never reassign at random, never re-derive:

- Segment `m` (1 … `segment_count`) uses the plan record `segments[m-1]` and the
  matching `segments/<m>/segment.json`. Its poem is authored from **that
  segment's** `segment_title`, `segment_summary`, `word_target`, and
  `segment_enrichment` — never from another segment's plan or profile.
- `word_target` is **per poem** (a poetry chapter's `word_target` applies to each
  segment, not divided among them). Compose each segment's poem to its own
  `word_target`.

For each segment `m`, in order:

1. Read `segments/<m>/segment.json` (the plan record + `segment_enrichment`).
2. Compose that segment's **complete poem** honoring its title, summary, and
   per-segment profile (image from `sensory_detail`, turn from `subject_rotation`,
   structure from `structural_variant`, and the chapter's shared `variety_note`),
   grounded in `gist.md`/`storyline.md` and the resolved style/override. The poem
   must stand alone with its own opening and closing.
3. Write the segment's poem to
   `chapters/<n>/segments/<m>/writer/segment.md` (the writer-stage segment poem;
   the writer stage is **not** versioned — it is simply overwritten in place).
4. Advance to the next segment; do not carry one segment's lines into another.

**Float-segment targeting.** A `<n>.<m>` target (e.g. `3.2`) selects only segment
`m` of chapter `n`. Write only that segment's poem; every other segment's
`writer/segment.md` is left untouched. Then still reassemble `chapter.md` from
**all** written segment poems (the newly written one plus the preserved ones), so
a partial write never drops the other poems.

After every poem is written (or a partial target's selected poem), assemble
`chapters/<n>/chapter.md` as the ordered anthology of **all** the segment poems
(each under its `segment_title`), so the chapter remains a single reader-facing
artifact while each segment stays an individually complete poem. Archive any
prior `chapter.md` first.

## Dispatch

Dispatch is a **strict per-chapter loop** — never batch, never parallelize. For
`all` / `*` / `continue` / a range / a list / a float-segment, repeat the whole
sequence once per chapter, in order, and report each as it completes. A
float-segment (`3.2`) narrows the work to that chapter's single segment; a bare
chapter or range still means "every segment of that chapter". For one chapter:

1. Resolve `language` and `word_target` (above).
2. Read `book.json` and the chapter's `chapter.json`; resolve the form (stop if
   missing/unsupported — never guess prose vs verse).
3. Resolve the style (below).
4. If `chapters/<n>/chapter.md` is absent, run the enrichment prerequisite (below).
5. Re-read the (possibly enriched) `chapter.json`, re-fetch `language`/`word_target`,
   and re-resolve the form.
6. Route by form: poetry → `.framework/skills/poetry/SKILL.md`; novel →
   `.framework/skills/novel/SKILL.md`.
   **Poetry segments:** when the chapter's `segment_count` is greater than 1 (or
   its `segments[]` plan declares more than one record), compose per-segment as
   described in *Segment Composition (Poetry)* — one complete, standalone poem
   per segment, assembled into `chapter.md` as the ordered anthology.
   **Exception — `poyar`:** when the resolved style or an explicit argument is
   `poyar`, route to `.framework/agents/poyar/agent.md` →
   `.framework/skills/poyar/SKILL.md`. Poyar is a fixed couplet form (14-akshar
   target per line, accepted 12–16, strong L1~L2 rhyme) with its own dedicated
   skill; it must never be composed by the generic poetry skill, which writes
   continuous prose.
   **Exception — `amitra`:** when the resolved style or an explicit argument is
   `amitra`, route to `.framework/agents/amitra/agent.md` →
   `.framework/skills/amitra/SKILL.md`. Amitra is a fixed blank-verse form
   (অমিত্রাক্ষর ছন্দ: continuous enjambed sentences, 14-akshar target per line,
   accepted 12–16, 8 + 6 caesura, optional rhyme) with its own dedicated skill;
   it must never be composed by the generic poetry skill.
7. Flatten `chapter.json` → `context.md`, build the prompt, and pass it (with the
   chapter model, style, language, word target, and override path) to the skill.
8. Report the writer-stage output: form, style, language, word target, the number
   of segments composed, and whether enrichment ran.

## Style Resolution (form-conscious, never on-the-fly)

Resolve one fixed source, bound to the book's form, in this precedence:

1. **`<style>` provided** → a preset: `.framework/templates/preset/<style>.md`.
2. **`<style>` omitted** → the book's `style.md` (or the `"style"` field in `book.json`).
3. **Fallback by form** → poetry: `pijush`; novel: `dialogue`.

Never cross the form boundary, and never compose a style on the fly — it is always
a pre-authored file.

## Enrichment Prerequisite for Missing Chapter Drafts

Only when `chapters/<n>/chapter.md` does **not** exist: archive the current
`chapter.json` into `chapters/<n>/history/`, then invoke `.framework/agents/enrich/agent.md`
for **only that chapter** (never as `enrich <count>`). Let enrich fuse its active
filters under its own contract; it updates `chapter.json` only and writes no prose.
If it fails or yields no record, stop and report — do not author `chapter.md`.
On success, resume dispatch with the refreshed metadata.

## Responsibility Boundary

The selected skill owns writing the chapter (honoring the required format—e.g., including headings for poetry), honoring the blueprint, signature, theme, style voice, and override as the final layer. For a multi-segment poetry chapter, the skill writes each segment as its own **complete, standalone poem** to `segments/<m>/writer/segment.md`, then assembles `chapters/<n>/chapter.md` as the ordered anthology of those poems (archiving prior copies); for a single-segment chapter it writes `chapters/<n>/chapter.md` directly.

The write agent must **not**: write chapter content directly; scaffold or run
filters; write to `workspaces/published/`; update
`progress.json`; or apply a form the pipeline's
model doesn't declare.

## Output

Report the resolved form, selected skill, chapter scope, `language`, `word_target`,
enrichment result (when it ran), and the writer-stage file path(s) produced.
