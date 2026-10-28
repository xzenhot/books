# Writer

A multi-agent literary engine for writing **poetry** and **novels** in a configured authorial voice, grounded in a reference work and a stereotype (signature, reference, theme set, syntax sample). The whole system is driven by a single slash command:

```text
/book <bookname> ...
```

The system is split into two layers:

- **`.framework/`** — the agents (workflows, role agents, skills) that do the work.
- **`workspaces/`** — the data: inputs (backlog, pipeline) and outputs (finished, versioned books under `workspaces/published/`).

---

## Architecture

```
writer/
├── .framework/              # the engine
│   ├── workflows/           # book.md + backlog.md + pipeline.md — the /book specs
│   ├── agents/              # role agents (scaffold, research, theme, enrich, write, publish, …)
│   ├── skills/              # form-specific skills (layout-poetry, layout-novel, workshop-*, …)
│   ├── rules/               # shared rules
│   └── templates/           # stereotypes (novel/, poetry/), moods/, subjects/, preset/
├── workspaces/                  # inputs & working state
│   ├── backlog/<book>/     # gist.md, storyline.md, book.json (the book plan)
│   └── pipeline/<book>/     # model.json, progress.json, filters/, chapters/
├── workspaces/published/<book>/     # finished, versioned output
├── AGENTS.md                # runtime steering for autonomous coding agents
├── LICENSE
└── README.md
```

---

## The `/book` Command

`/book` is the primary command surface. It is interpreted left-to-right, and its full specification lives in `.framework/workflows/pipeline.md`. The command families are:

```text
/book <bookname> [<gist>] [form] [refresh]                          # create/update the backlog epic
/book <bookname> init|backlog|layout [<gist>] [<count>] [form]      # configure the backlog book plan
/book <bookname> init idea                                          # rewrite the gist with AI assistance
/book <bookname> scaffold <gist> count|chapter-count <n> [--form]   # build the pipeline structure
/book <bookname> <agentname> <chapter>|<n>|all|continue             # run an agent on chapters
/book <bookname> filter <filter> *|all|<n>                        # run a filter on a scope
/book <bookname> enrich <count>|range|*                             # fuse active filters into one pass
/book <bookname> eval all|*|<n>|<range>|continue                    # evaluate pipeline completeness (read-only)
/book <bookname> review *|all|<n>                                  # quality gate before publish
/book <bookname> humanize *|all|<n>                               # target-language-only polish
/book <bookname> write <n>|all|continue [<style>]                   # write finished chapters
/book <bookname> chapter <n>|all|continue [<style>]                 # alias of write
/book <bookname> story <n>|all|continue [<style>]                   # alias of write
/book <bookname> style [<style>]                                    # transform writer-stage chapters
/book <bookname> translate <n>|all|continue <language>              # translate writer-stage chapters
/book <bookname> poet|poetry|poem                                   # produce a single finished poem
/book <bookname> lyrics <n>|<chapter> [<target_syllables>] [replace]    # modern Bengali song lyrics
/book <bookname> limerick|limeric <n>|<chapter> [replace]          # 5-line AABBA limerick
/book <bookname> haiku <n>|<chapter> [replace]                     # 5-7-5 akshar haiku
/book <bookname> line <chapter> sonnet [replace]                   # sonnet calibration (line agent)
/book <bookname> rhyme <chapter> sonnet [<scheme>] [replace]       # sonnet composition (rhyme agent)
/book <bookname> publish [<language>]                               # promote segments to workspaces/published
/book <bookname> preview [<language>]                               # draft preview (skips quality gate)
/book <bookname> form <formname>                                    # set/change the book's form
/book <bookname> config [<key> [<value>]]                           # get/set book config
/book <bookname> add <chapter-count> filter <filter>                # append chapters and run a filter
/book -o | --options | list                                       # list books and chapters
/book -h | --help                                                   # show usage
/book eval-judge [--completeness] [--effectiveness] [--book <n>] [--all]  # framework self-judge
```

### The lifecycle

```text
/book <bookname> <gist>   →  backlog epic (gist.md, storyline.md)
/book <bookname> init     →  book.json (chapter plan + filter chain)
/book <bookname> scaffold →  workspaces/pipeline/<bookname>/ (structure)
/book <bookname> filter * →  run the filter chain (or enrich)
/book <bookname> write    →  workspaces/published/<bookname>/<version>/
/book <bookname> publish  →  workspaces/published/<bookname>/version<k>/
```

---

## Forms

A book is either **poetry** (verse) or **novel** (prose), declared in the pipeline's `form` field.

| Signal | Poetry | Novel |
|--------|--------|-------|
| Source of truth | `model.json` (`chapters[]` holds topics) | `storyline.md` |
| Chapter structure | flat, continuous poetic prose | flat, continuous prose |
| Segments per chapter | exactly one (`segments/1`) | many |
| Word target | 500–800 | 5,500+ |
| Stereotype templates | `.framework/context/poetry/` | `.framework/context/novel/` |

---

## The Filter Chain

Filters run in a fixed order inside the pipeline. The chain is declared in `book.json`'s `filter_chain` and materialized as `workspaces/pipeline/<bookname>/filters/filters.json`.

**Poetry:** `workshop → research → correctness → theme → syntax → override → quality`

**Novel:** `workshop → research → seeds → correctness → theme → syntax → override → quality`

Each filter is a skill under `.framework/filters/<filter>/SKILL.md`, reached through the filter agent (`.framework/agents/filter/agent.md`). The `enrich` command fuses the active (`autorun: true`) filters into a single combined agent and runs them in one pass.

---

## Role Agents (`.framework/agents/`)

| Agent | Role |
|-------|------|
| `init` | Configure the backlog book plan (`book.json`). |
| `scaffold` | Build the pipeline structure (dispatches to layout skills). |
| `layout` | Pre/post-scaffold preparation and master-prompt seeding. |
| `filter` | Run a named filter skill (`.framework/filters/<filter>/SKILL.md`). |
| `enrich` | Fuse active filters into one combined pass. |
| `write` | Write finished reader-facing chapters (→ poetry/novel skill). |
| `review` | Quality gate — audit chapters against quality parameters. |
| `humanize` | Target-language-only polish (Bengali), post-review. |
| `eval` | Read-only pipeline-completeness evaluator. |
| `style` | Transform writer-stage chapters through a style template. |
| `line` | Calibrate Bengali lines to a fixed akshar count (sonnet calibration; MCP). |
| `rhyme` | Compose rhymed Bengali sonnets (rhyme bank + akshar via MCP). |
| `lyrics` | Dispatch the modern Bengali song lyrics to `skills/lyrics`. |
| `limerick` | Dispatch the 5-line AABBA Bengali limerick to `skills/limerick`. |
| `haiku` | Dispatch the 5-7-5 akshar Bengali haiku to `skills/haiku`. |
| `translate` | Translate writer-stage chapters. |
| `publish` | Promote segments to `workspaces/published/` and assemble the book. |

Filter skills (`.framework/filters/`): `workshop`, `research`, `seeds`, `correctness`, `theme`, `syntax`, `override`, `quality`.

---

## Skills (`.framework/skills/`)

Skills are invoked **only through an agent** — never directly. Form-specific skills include:

- `layout-poetry`, `layout-novel` — pipeline scaffold skeletons.
- `workshop-poetry`, `workshop-novel` — chapter-frame creation.
- `poetry`, `novel` — form-specific chapter writing.
- `quality-poetry`, `quality-novel` — quality audit per form.
- `theme-poetry`, `theme-novel` — thematic lens per form.
- `enrich-poetry`, `enrich-novel` — fused enrichment per form.
- `sonnet`, `limerick`, `haiku` — fixed-form Bengali poems (akshar-count via MCP).
- `lyrics` — modern Bengali song lyrics (syllable-count via MCP; akshar does not apply).

Reference filters live under `.framework/filters/reference/` (`poeticprose`, `narrative`, `dialogue`, `pacing`, `geography`, `history`, `indian`, `mythology`, `philosophy`, `contemporary`, `revision`, `translation`).

---

## Stereotypes & Styles

- **Stereotypes** (`.framework/context/<form>/`) — `signatures/`, `references/`, `themes/`, `syntax/`, `genre/`, `styles/`. Each chapter selects a signature (voice), reference (source text), theme set (philosophical lens), and syntax sample.
- **Styles** (`.framework/context/poetry/styles/<style>/`) — transformer styles (e.g. `pijush`) applied by the `style` command.

---

## Data Layout

| Path | Role |
|------|------|
| `workspaces/backlog/<book>/` | `gist.md`, `storyline.md`, `book.json` (the book plan) |
| `workspaces/pipeline/<book>/` | `model.json`, `progress.json`, `filters/`, `chapters/` |
| `workspaces/pipeline/<book>/chapters/<n>/` | `chapter.md` (live draft), `model.json`, `history/`, `segments/1/{writer,editor,translator}/` |
| `workspaces/published/<book>/<version>/` | finished, versioned reader-facing output |

---

## Quick Start

```text
/book behula "Bengali mythology of Behula..."          # create the backlog epic
/book behula init poetry                               # configure the book plan
/book behula scaffold                                  # build the pipeline
/book behula enrich                                    # fuse active filters into one pass
/book behula write                                     # write finished chapters
/book behula translate bengali                         # translate to Bengali
/book behula publish bengali                           # promote to workspaces/published
```

See `AGENTS.md` for the runtime steering contract, `.framework/workflows/book.md` for the command registry, and `.framework/workflows/pipeline.md` for the full pipeline specification — including *The Write Command*, which owns the four-task compose sequence (enrich → draft → transform → compose).

