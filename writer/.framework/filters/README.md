# Filters Index

Classification of every folder under `.framework/filters/`. This is the source of
truth for what is an active chain member versus a reference library versus a
retired/legacy dispatcher. Audits (`eval-judge`, `self-eval`) use this index rather
than guessing.

## Chain members (active)

These are the named filters that appear in a book plan's `filter_chain` and are
routed by `.framework/agents/filter/agent.md`. The **form-divergent** filters
(`workshop`, `research`, `seeds`, `quality`) resolve by the book's form to
`.framework/context/<form>/filters/<name>/SKILL.md`; the **shared** filters resolve
to `.framework/filters/<name>/SKILL.md`.

| Folder | Resolves to | Form-divergent |
|--------|-------------|----------------|
| `workshop/` | `.framework/context/<form>/filters/workshop/SKILL.md` | ✅ |
| `research/` | `.framework/context/<form>/filters/research/SKILL.md` | ✅ |
| `seeds/` | `.framework/context/<form>/filters/seeds/SKILL.md` | ✅ |
| `genre/` | `.framework/filters/genre/SKILL.md` | — |
| `history/` | `.framework/filters/history/SKILL.md` | — |
| `spatality/` | `.framework/filters/spatality/SKILL.md` | — |
| `movement/` | `.framework/filters/movement/SKILL.md` | — |
| `correctness/` | `.framework/filters/correctness/SKILL.md` | — |
| `override/` | `.framework/filters/override/SKILL.md` | — |
| `quality/` | `.framework/context/<form>/filters/quality/SKILL.md` | ✅ |

## Reference libraries (`reference/`)

Subject-domain material, consolidated under `reference/` to flatten the namespace.
Not chain members; consulted by the `research`/`correctness` filters and the
writing agents as grounding material. Never invoked directly by a filter agent.

| Folder | Domain |
|--------|--------|
| `reference/contemporary/` | modern context and mapping |
| `reference/dialogue/` | dialogue technique |
| `reference/geography/` | place and landscape |
| `reference/history/` | historical grounding |
| `reference/indian/` | Indian cultural/religious material |
| `reference/mythology/` | myth and legend |
| `reference/narrative/` | narrative structure |
| `reference/pacing/` | pacing technique |
| `reference/revision/` | revision guidance |
| `reference/translation/` | translation guidance |

## Retired / legacy (`_retired/`)

Moved out of the active tree; no live agent, workflow, or skill may reference them.

| Folder | Former role | Why retired |
|--------|-------------|-------------|
| `layout/` | compatibility dispatcher | superseded by `skills/layout-novel` / `layout-poetry` |
| `enrich/` | legacy enrich engine | superseded by `skills/enrich-novel` / `enrich-poetry` |
| `reference/philosophy/` | philosophical grounding | pointed at the removed `workspaces/context/qualities/` path; seed analysis now lives under `context/<form>/themes/` |
| `reference/poeticprose/` | Gibran-esque prose craft | pointed at the removed `workspaces/context/qualities/` path and a dead `config.json`/`workspaces/context` tree |
| `theme/` | thematic lens filter | moved to the quality chain (`qualities/theme`) |
| `syntax/` | syntax/register filter | moved to the quality chain (`qualities/syntax`) |
| `workshop/` | shared workshop dispatcher | split into `.framework/context/poetry/filters/workshop/` and `.framework/context/novel/filters/workshop/` |
| `research/` | shared research filter | split into `.framework/context/poetry/filters/research/` and `.framework/context/novel/filters/research/` |
| `seeds/` | shared seeds filter | split into `.framework/context/poetry/filters/seeds/` and `.framework/context/novel/filters/seeds/` |
| `quality/` | shared quality dispatcher | split into `.framework/context/poetry/filters/quality/` and `.framework/context/novel/filters/quality/` |
