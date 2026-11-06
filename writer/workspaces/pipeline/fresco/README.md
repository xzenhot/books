# Pipeline — fresco

- **updated_by:** scaffold
- **updated_date:** 2026-11-06T12:25:58Z

This folder is the live **poetry pipeline** for `fresco`. It is a self-contained snapshot: after scaffold, every later command (`enrich`, `filter`, `write`, `style`, `translate`, `publish`) reads and writes here and never falls back to `workspaces/backlog/fresco/`. If a file listed below is missing, the fix is a re-scaffold — not reading the backlog.

## Book facts

| Key | Value |
|---|---|
| Book | `fresco` |
| Form | `poetry` |
| Poems scaffolded | 32 |
| Word target per poem | 500 |
| Style | `pijush` |
| Execution mode (`factory`) | `online` |

## Root files

| File | Significance |
|---|---|
| `book.json` | The authoritative plan for this pipeline: identity, `form`, `factory`, `chapter_count`, the `chapters[]` plan, `word_target`, `filter_chain`, and `quality_chain`. Cloned from the backlog and stamped `scaffold`. |
| `progress.json` | Progress ledger: one entry per chapter with `status`, topic, and draft path. Updated by `write` and `publish`. |
| `gist.md` | The seed premise: one-sentence gist, short expansion, author comment. |
| `storyline.md` | The full narrative foundation (novel) or thematic grounding (poetry) — the source for chapter intent. |
| `override.md` | The author's master prompt: mandated voice, diction rules, and craft directives. Exempt from audit stamping. |
| `bookseed.md` | The book's vocabulary and phrase seed. `enrich` appends a derived lexicon block. Plain text; exempt from audit stamping. |
| `signature.md` | The selected style's authorial signature, copied from `.framework/editor/<form>/styles/<style>/` and stamped `scaffold`. |
| `README.md` | This map. Refreshed by scaffold while the generator marker is present. |

## Folders

| Folder | Significance |
|---|---|
| `chapters/` | One folder per poem, named by chapter index (`1` … `32`). Holds the live draft and its runtime state. |
| `filters/` | Filter registry plus per-filter output folders. Scaffold creates only `filters/filters.json`; each filter creates `filters/<name>/` on its first run. |
| `qualities/` | Quality-dimension registry plus per-dimension folders. Scaffold creates only `qualities/qualities.json`; each dimension creates `qualities/<name>/` on first use. |
| `layout/` | The form-tool templates cloned from `.framework/templates/backlog/v1/layout/` — prompts, lenses, twists, and schemas that `enrich` and `write` consume. Keeps the pipeline self-contained. |

## Chapter layout (`chapters/<n>/`)

| Path | Significance |
|---|---|
| `chapter.json` | Runtime state for this chapter: identity, `chapter_title`, `chapter_summary`, `word_target`, `state`, and the live `segments` list. |
| `chapter.md` | The live working draft. Created and revised by the write/chapter/poet path (workshop may seed it when absent). Filters never read it. |
| `history/` | Superseded `chapter.md` and model snapshots, written before anything overwrites the live draft. Immutable; never audit-stamped. |
| `model.json` | Legacy chapter-model name. Still read when `chapter.json` is absent; scaffold does not create it for new pipelines. |

### Segment layout (`chapters/<n>/segments/1/`)

Every chapter owns at least one segment folder. Poetry always has exactly one (`1`).

| Path | Significance |
|---|---|
| `segment.json` | Runtime state for this segment (level, state, chapter/segment index). |
| `writer/` | Writer-stage output: the finished copy of the draft for this segment. |
| `editor/` | Editor and review commentary, including content quality scores. |
| `translator/` | Translated derivatives of the latest draft, named by language (`en.md`, `bn.md`, …). |
| `version/` | Promoted snapshots of the segment's published output (`chapter_v<k>.md`). |

## Runtime registries

`filters/filters.json` declares the ordered filter chain; `qualities/qualities.json` declares the quality dimensions for this form. Each entry carries `order`, `name`, and `autorun` (filters also carry the `agent` skill path). Setting `autorun: false` skips an entry in `filter *` / `filter all`; naming it explicitly still runs it.

- **Filter chain:** `workshop` → `research` → `genre` → `history` → `spatality` → `movement` → `correctness` → `override` → `quality`
- **Quality chain:** `subject` → `genre` → `theme` → `syntax` → `signature`

## Read/write ownership

| Actor | May write | Must not touch |
|---|---|---|
| `scaffold` | Pipeline structure, root planning files, the two registries, this README | Filter output, finished drafts, `workspaces/published/` |
| `filter:<name>` | Its own `filters/<name>/` folder and chapter **models** | `chapter.md`, another filter's folder, `workspaces/published/` |
| `enrich` | Chapter models and the derived lexicon block in `bookseed.md` | `chapter.md` |
| `write` / `chapter` / `poet` | `chapter.md`, `segments/1/writer/`, `history/`, `progress.json` | `workspaces/backlog/` |
| `review` / `humanize` | Editor commentary and language corrections | `workspaces/published/` |
| `publish` | `workspaces/published/<bookname>/<version>/` and `progress.json` | Pipeline drafts |

## Command surface for this pipeline

```text
/book fresco enrich *            # fuse active filters into one guidance pass
/book fresco filter <name> all|*|<n>
/book fresco write <n>|all|continue [<style>]
/book fresco review *|all|<n>
/book fresco humanize *|all|<n>
/book fresco translate <n>|all|continue <language>
/book fresco publish [<language>]
```

Outputs never become reader-facing here: finished text is promoted only into `workspaces/published/fresco/<version>/` by `publish`, after the quality gate passes.

<!-- generated-by: scaffold; remove this line to keep a hand-written README -->
