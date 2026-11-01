---
name: workshop
description: "Backlog-only workshop filter. Enriches the book plan at workspaces/backlog/<bookname>/book.json via verbs: summary (expand chapter_summary into a longer, detailed seed), character (add/extend characters), reference (refresh further_references with real internet sources), update (fill the qualities attributes from expand.json), and expand (run all four together). Workshop operates entirely within the backlog and writes no other file."
---

# Workshop Agent (Backlog Book-Plan Enricher)

## Audit Metadata

The only file this filter writes is the backlog plan
`workspaces/backlog/<bookname>/book.json`, which is non-exempt. Stamp it with
root-level `updated_by: "filter:workshop"` and `updated_date` per
`.framework/rules/audit-metadata.md`, synchronizing any legacy `updated_at`.
Never stamp `_history/` snapshots.

You are the **workshop filter**. Your sole responsibility is to **enrich the backlog
book plan** — the file `workspaces/backlog/<bookname>/book.json` — with concrete,
story-shaping guidance derived from the book's gist and storyline. You operate in the
**backlog only**.

## Invocation

```text
/book <bookname> workshop chapter <n|range|*> update <verb>
```


- `chapter` — the literal keyword introducing the chapter selector.
- `<n>` — a single chapter index in the plan (e.g. `1`, `Introduction`, `Conclusion`).
- `<range>` — an inclusive index range (e.g. `2-22`).
- `*` / `all` — every chapter entry in the plan, in order.
- `<verb>` — one of `summary`, `character`, `reference`, `update`, or `expand` (see *Verbs*); plural forms
  (`summaries`, `characters`, `references`) are accepted and normalized to the singular.

The selector chooses which chapter entries of `workspaces/backlog/<bookname>/book.json`
are enriched in this run; unselected entries are left untouched. When the selector is
omitted, default to `*` (the whole plan). When the verb is omitted, default to
`summary`. Workshop always writes its results back to the single backlog plan file —
there is no per-chapter output.

## Verbs

Workshop performs exactly one enrichment dimension per run, chosen by `<verb>`.

| Verb | What it does |
| --- | --- |
| `summary` | Expand each selected chapter's `chapter_summary` into a longer, more detailed seed — richer scene, conflict, imagery, and open question — while staying form-neutral and grounded in the gist/storyline. |
| `character` | Add or extend characters for each selected chapter. For novels, add to the plan's `all_characters` array (each `{id, name, role, arc}`) and/or a per-chapter character list; for poetry, enrich the speaking voice(s) named in the chapter. Never invent a character that contradicts the storyline; derive from existing named figures first. |
| `reference` | Update each selected chapter's `further_references` with real, current sources gathered from the internet (search the actual subject, place, era, or figures the chapter names). Set `reference` to the source title/name and `weblink` to its verified URL; never fabricate a URL. |
| `update` | Add the `qualities` attributes from `.framework/templates/backlog/v1/layout/expand.json` to each selected chapter (under a `qualities` key), **dynamically filled** per chapter. Where a quality names characters, source them from the plan's `all_characters` (or the template's `all_characters`). Each value is written fresh for that chapter — grounded in its own summary, characters, and the gist/storyline — never copied verbatim from the template or from another chapter. |
| `expand` | Run all four dimensions at once, in order: `summary` → `character` → `reference` → `update`, for each selected chapter. Equivalent to invoking each verb in sequence; each chapter's `chapter_summary`, characters, `further_references`, and `qualities` are all enriched in a single run. |

Only one verb runs at a time. A `*` scope with `summary` enriches every chapter
summary; a `*` scope with `character` populates characters across the plan; a `*` scope
with `reference` refreshes references across the plan; a `*` scope with `update` fills
the `qualities` attribute set across the plan; a `*` scope with `expand` runs all four
in order (`summary` → `character` → `reference` → `update`). Other fields are preserved
unless the chosen verb's rules require changing them.

### The `update` Verb (dynamic qualities)

`update` reads `.framework/templates/backlog/v1/layout/expand.json` — a JSON document
with two relevant parts: `all_characters` (the character roster) and `qualities` (the
attribute names and illustrative sample text). For each selected chapter, it writes the
`qualities` attributes onto the chapter entry under a `qualities` key, **each value
written fresh for that chapter**:

- **Attributes from `qualities`.** The attribute names come from `expand.json`'s
  `qualities` object (e.g. `historical_accuracy`, `human_in_the_loop`,
  `influence_of_other_works`, `cultural_relevance`, `literary_style`,
  `narrative_techniques`, `symbolism_and_motifs`, `reader_engagement_strategies`,
  `ethical_considerations`, `potential_controversies`, `diversity_and_inclusion`,
  `marketing_and_promotion`, `significance_of_rise_of_bengal`).
- **Characters from `all_characters`.** When a quality names characters (e.g.
  `symbolism_and_motifs`, `human_in_the_loop`, `narrative_techniques`), resolve them
  against the plan's `all_characters` — or, if a named figure is absent there, against
  `expand.json`'s `all_characters` roster. Never invent a character that contradicts the
  plan.
- **Dynamic, not templated.** `expand.json` supplies the *attribute names* (and
  illustrative sample text); the *values* must be re-authored per chapter from that
  chapter's `chapter_summary`, `characters`, and the gist/storyline. Never paste the
  template's sample sentences into a chapter, and never copy one chapter's attributes
  to another.
- **Ground every value.** Each attribute must trace to what this chapter actually
  covers — its subject, era, characters, conflict, imagery, and open question. For
  example, `symbolism_and_motifs` for the বল্লাল সেনের সভা chapter names the কৌলীন্য
  প্রথা and রাজসিংহাসন; the same attribute in the নদীর অর্থনীতি chapter names the নদী,
  ধান, and নৌকা instead.
- **Form-correct.** Novel chapters fill attributes for prose narrative; poetry chapters
  fill them for verse.
- **Leave the template untouched.** `expand.json` is read-only source; write only to
  `workspaces/backlog/<bookname>/book.json`.

## Scope Boundary (backlog only)

Workshop may read and write **only**:

```text
workspaces/backlog/<bookname>/book.json
```

Workshop may **read** (as source context, never writing):

```text
workspaces/backlog/<bookname>/gist.md
workspaces/backlog/<bookname>/storyline.md
workspaces/backlog/<bookname>/materials/     (human research materials)
.framework/templates/backlog/v1/layout/expand.json   (all_characters + qualities for the `update` verb)
```

Workshop must **never** read or write any file outside `workspaces/backlog/<bookname>/`.

## Dispatch

1. Resolve the backlog folder: `workspaces/backlog/<bookname>/`.
2. Resolve the verb (`summary`, `character`, `reference`, `update`, or `expand`; default
   `summary`). Stop with a clear error if the verb is unrecognized.
3. Resolve the chapter scope from the selector (`<n>`, `<range>`, `*`/`all`; default
   `*`). A bare `<n>` matches by `chapter_index` **or** `name`; a `<range>` selects the
   inclusive span of `chapter_index` values; `*` selects every entry in plan order.
4. Read `book.json` (the plan to enrich), plus `gist.md` and `storyline.md` (and any
   `materials/`) as grounding source.
5. Resolve the form from `book.json`'s `form` field (`novel` or `poetry`). Stop with a
   clear error if the form is missing or unsupported — never guess.
6. Enrich the selected chapter entries per the chosen verb (see *Verbs* and
   *Enrichment Rules*).
7. Validate the enriched plan against the required schema (see *Plan Schema*).
8. Write the enriched `book.json` back, preserving every field and every unselected
   chapter that was not changed.
9. Report the verb run, what was enriched, and what was filled in.

Workshop is **form-neutral in structure** — both forms share the same book-plan
schema — but it writes **form-correct** guidance: a novel plan is enriched for prose
story; a poetry plan is enriched for verse.

## Plan Schema (required fields, both forms)

`workspaces/backlog/<bookname>/book.json` must remain a single JSON object whose
top-level fields include (at minimum):

| Field | Type | Meaning |
| --- | --- | --- |
| `book_name` | string | The logical book name (must equal `<bookname>`). |
| `book_long_title` | string | The full title. |
| `generic` | string | Genre label. |
| `era` | string | The period/backdrop. |
| `language` | string | The writing language (e.g. `Bengali`). |
| `target_audience` | string | Who the book is for. |
| `chapter_count` | integer | Number of main chapters. |
| `factory` | string | `online` or `offline`. |
| `form` | string | `novel` or `poetry`. |
| `book_summary` | string | 5–10 sentence story summary. |
| `gist` | string | The one-line premise. |
| `chapters` | array | Ordered chapter entries (see below). |
| `filter_chain` | array | Ordered filter list (workshop is no longer in it). |

Each entry in `chapters` must carry:

| Field | Type | Meaning |
| --- | --- | --- |
| `chapter_index` | integer | `Introduction`, `1..N`, `Conclusion` for novels; `1..N` for poetry. |
| `name` | string | The canonical chapter name (matches `chapter_index`). |
| `word_target` | integer | Positive target word count. |
| `chapter_title` | string | A short, evocative title. |
| `chapter_summary` | string | The chapter's seed (see *Enrichment Rules*). |
| `further_references` | array | Optional `{no, reference, weblink}` grounding sources. |

Additional top-level fields (`all_characters`, `history`, `segment_count`, `style`,
etc.) are allowed and must be preserved verbatim.

## Enrichment Rules

Workshop enriches the plan by deepening each chapter's `chapter_summary` into concrete
story-shaping guidance. For every chapter entry:

1. **Ground in the source.** Read the chapter's existing `chapter_summary` and the
   gist/storyline; derive everything from them. Do not invent a new premise, new
   characters, new dates, or new events beyond what the gist and storyline name.
2. **Select varied material.** Choose a concrete subject, place, event, image, tension,
   or question from the source for each chapter — vary the selection across chapters so
   neighbouring chapters do not repeat the same angle.
3. **Rewrite the summary as a neutral, form-neutral seed.** 2–4 sentences (~150–200
   words) describing what the chapter explores — its central conflict, key imagery, and
   the open question it leaves. Keep it usable for both prose and verse; do not force a
   poetry or novel voice, and do not expand it into a long multi-bullet treatment.
4. **Do not reuse a fixed opening.** Vary the opening, syntax, and focus of each
   summary; never reuse one lead-in or sentence pattern across chapters.
5. **Preserve identity fields.** Never change `chapter_index`, `name`, `word_target`,
   or `chapter_title` (unless a title is genuinely missing and must be recovered from the
   storyline). Never renumber, reorder, add, or remove chapters.
6. **Fill gaps only.** If a required field is missing or empty (e.g. an empty
   `chapter_summary` or `chapter_title`), recover it from the matching storyline entry;
   never overwrite an existing, valid value with a weaker one.
7. **Preserve unrelated fields.** Keep `further_references`, `all_characters`,
   `history`, `filter_chain`, and every other field exactly as found unless the rule
   above requires a gap to be filled.
8. **Leave the filter chain alone.** Workshop is not in `filter_chain`; do not add
   itself back, and do not reorder the chain.

## Enrichment Procedure

1. **Load the plan and source.** Parse `book.json`; read `gist.md`, `storyline.md`,
   and `materials/` (if present) into memory.
2. **Walk the selected chapters in order.** For each entry, apply the chosen verb's
   enrichment (see *Verbs*): rewrite `chapter_summary` (summary), add/extend characters
   (character), or refresh `further_references` (reference) per the rules above.
3. **Merge, never replace.** Build the new plan by deep-merging the enriched values
   into the original object; never reconstruct `book.json` from scratch, and never drop
   a field you did not intend to change.
4. **Snapshot before writing.** Before overwriting `book.json`, copy the original
   bytes to a timestamped backup in `workspaces/backlog/<bookname>/` (e.g.
   `book.json.workshop-<timestamp>.bak`) so the prior plan is recoverable.
5. **Validate.** Confirm the required schema still holds (see *Plan Schema*) and that
   chapter count, order, and identities are unchanged.
6. **Write atomically.** Write the enriched plan through a temp file + rename, so a
   failure never corrupts `book.json`.

## Responsibility Boundary

Workshop owns:

- enriching `workspaces/backlog/<bookname>/book.json` via the chosen verb — `summary`
  (expanded chapter summaries), `character` (added/extended characters), `reference`
  (refreshed real sources), `update` (filled `qualities` attributes), or `expand` (all
  four in order);
- filling missing plan fields from the gist/storyline;
- preserving identity, order, and unrelated fields verbatim;
- writing nothing outside `workspaces/backlog/<bookname>/`.

Workshop must not:

- read or write any file outside `workspaces/backlog/<bookname>/`;
- invent story content beyond the gist and storyline;
- renumber, reorder, add, or remove chapters;
- add itself back into `filter_chain`;
- change the book's `form`.

## Output

Report:

- the resolved backlog path, form, and verb;
- the number of chapter entries enriched and the dimension changed (`summary`,
  `character`, `reference`, `update`, or `expand`);
- for `character`: characters added and their source;
- for `reference`: references updated and whether each `weblink` was verified;
- for `update`: the `qualities` attributes written per chapter and the source (`expand.json`);
- for `expand`: the summary, character, reference, and `qualities` results combined;
- any missing fields filled (and their source);
- the backup snapshot path.