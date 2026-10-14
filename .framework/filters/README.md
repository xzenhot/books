# Filters Index

Classification of every folder under `.framework/filters/`. This is the source of
truth for what is an active chain member versus a reference library versus a
retired/legacy dispatcher. Audits (`eval-judge`, `self-eval`) use this index rather
than guessing.

## Chain members (active)

These are the named filters that appear in a book plan's `filter_chain` and are
routed by `.framework/agents/filter/agent.md`. Each dispatches to a form-specific
skill under `.framework/skills/`.

| Folder | Dispatches to |
|--------|---------------|
| `workshop/` | `.framework/skills/workshop-novel/SKILL.md`, `workshop-poetry/SKILL.md` |
| `research/` | (self-contained) |
| `seeds/` | (self-contained) |
| `correctness/` | (self-contained) |
| `theme/` | `.framework/skills/theme-novel/SKILL.md`, `theme-poetry/SKILL.md` |
| `syntax/` | (self-contained) |
| `override/` | (human-in-the-loop command file) |
| `quality/` | `.framework/skills/quality-novel/SKILL.md`, `quality-poetry/SKILL.md` |

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
| `reference/philosophy/` | philosophical grounding |
| `reference/poeticprose/` | poetic-prose craft |
| `reference/revision/` | revision guidance |
| `reference/translation/` | translation guidance |

## Retired / legacy (`_retired/`)

Moved out of the active tree; no live agent, workflow, or skill may reference them.

| Folder | Former role | Why retired |
|--------|-------------|-------------|
| `layout/` | compatibility dispatcher | superseded by `skills/layout-novel` / `layout-poetry` |
| `enrich/` | legacy enrich engine | superseded by `skills/enrich-novel` / `enrich-poetry` |
