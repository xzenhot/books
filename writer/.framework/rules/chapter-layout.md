# Chapter Layout Contract

The scaffold agent's `## Chapter Layout` section defines the downstream paths for
all filters, chapter-writing agents, poet agents, and any skills they invoke. This
contract is mandatory and takes precedence over conflicting model templates in
that agent or its layout skills.

## Chapter model schema (both forms)

For every entry in the cloned root model's `chapters` array, create
`chapters/<name>/chapter.json` as a single JSON object copied from that entry, not
an array or a book-level configuration object. Match by the entry's `name` and
verify its `chapter_index`; never select an entry by an unrelated example or by
array position alone. Preserve all source fields, including any additional fields
present in the plan.

The required base fields are `chapter_index` (integer), `name` (string),
`word_target` (integer), `chapter_title` (string), `chapter_summary` (string), and
`further_references` (array). Do not rename or replace them with `chapter_name`,
`topic`, `title`, or `summary`. Runtime metadata such as `segments`, `level`,
`state`, `syntax`, and filter history may be added without dropping or overwriting
the copied source fields.

For poetry, each plan chapter may declare a positive integer `segment_count`
(new plans default to 8; legacy plans without it default to one) and an inline
`segments[]` plan (ordered titles and summaries) authored by layout. Scaffold
copies the count and the plan into `chapter.json` and creates the corresponding
segment folders, seeding each `segments/<n>/segment.json` from its matching plan
record with pending runtime state. Enrichment layers poetic parameters on top of
the preserved plan and, for legacy chapters whose plan is still empty, fills the
`segments` array with exactly that many ordered records and mirrors each record
into its matching `segments/<n>/segment.json`. The poetry `word_target` is per
segment, not divided among the segment count.

Named novel units such as `Introduction` and `Conclusion` likewise use their plan
entry's `name` as the folder name and preserve its declared index.

On an existing pipeline, preserve the incremental rule: do not re-clone over an
edited root model or replace existing chapter state merely to enforce this schema.
During explicitly requested repair, read existing models and fill missing source
fields from the matching plan entries; preserve runtime metadata and report
conflicting existing values. A full replacement requires an explicit re-scaffold
request.

## Chapter paths

- `chapters/<n>/chapter.md` is the live working draft. The workshop filter may
  create an initial draft only when the file is absent and must never read or
  overwrite an existing draft. Later revisions belong to the writing stage
  (chapter/write agents). All other filters, including enrich, must not read or
  modify it; they operate on `chapter.json` and their own `filters/<filter>/`
  inputs/outputs.
- `chapters/<n>/chapter.json` is the runtime state for the chapter. Filters, write
  agents, poet agents, and supporting skills must merge their metadata here rather
  than inventing parallel state files.
- `chapters/<n>/mood.json` describes how the chapter is shaped across segments and
  must remain the continuity/readability guide for downstream writing.
- `chapters/<n>/segments/<x>/version/` stores verified copies of the prior
  `chapter.md` and writer-stage drafts before replacement, following **Mandatory
  Draft Version Before Overwrite**. Other metadata snapshots may remain directly
  under `history/`.
- `chapters/<n>/segments/<x>/segment.json` is the runtime state for that segment.
- `chapters/<n>/segments/<x>/writer/` stores the writer-stage copy of the current
  chapter or segment draft.
- `chapters/<n>/segments/<x>/editor/` stores editor comments, assessments, and
  quality notes.
- `chapters/<n>/segments/<x>/latest/` stores the most recent finalized copy of
  the chapter or segment draft (the latest reviewed output, refreshed by review
  and publish).
- `chapters/<n>/segments/<x>/translator/` stores translated outputs of the latest
  chapter or segment draft, named by language such as `en.md`, `hn.md`, or `bn.md`.

No downstream step may create alternate chapter-version files in the chapter root
unless the scaffold agent's contract is updated to allow them. The chapter root
holds the live `chapter.md`; workshop may create it only when absent, while later
writers archive before replacing it. Versioned or translated derivatives belong in
segment `version/`, `writer/`, `editor/`, `latest/`, or `translator/` folders (legacy archives
remain in `history/`).
