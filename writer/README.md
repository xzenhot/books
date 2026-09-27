# Writer

A multi-agent literary engine for writing **poetry** and **novels** in a configured authorial voice, grounded in a reference work and a stereotype (signature, reference, theme set, syntax sample). The whole system is driven by a single slash command:

```text
/book <bookname> ...
```

The system is split into two layers:

- **`.framework/`** — the agents (workflows, role agents, skills) that do the work.
- **`.space/`** and **`source/`** — the data: inputs (backlog, pipeline) and outputs (finished, versioned books).

---

## Architecture

```
writer/
├── .framework/              # the engine
│   ├── workflows/           # pipeline.md — the single orchestration spec for /book
│   ├── agents/              # role agents (scaffold, research, theme, enrich, write, publish, …)
│   ├── skills/              # form-specific skills (layout-poetry, layout-novel, workshop-*, …)
│   ├── rules/               # shared rules
│   └── templates/           # stereotypes (novel/, poetry/), styles/, moods/, subjects/
├── .space/                  # inputs & working state
│   ├── backlog/epic/<book>/ # gist.md, epic.md, book.json (the book plan)
│   └── pipeline/<book>/     # model.json, bookseed.txt, progress.json, filters/, chapters/
├── source/books/<book>/     # finished, versioned output
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
/book <bookname> scaffold <gist> count|chapter-count <n> [--form]   # build the pipeline structure
/book <bookname> <agentname> <chapter>|<n>|all|continue             # run an agent on chapters
/book <bookname> filter <filter>|*|all                              # run a filter (or the chain)
/book <bookname> enrich <count>|range|*                             # fuse active filters into one pass
/book <bookname> write <n>|all|continue                             # write finished chapters
/book <bookname> style [<style>]                                    # transform writer-stage chapters
/book <bookname> translate <n>|all|continue <language>              # translate writer-stage chapters
/book <bookname> publish [<language>]                               # promote segments to source/books
/book <bookname> form <formname>                                    # set/change the book's form
/book <bookname> config [<key> [<value>]]                           # get/set book config
/book -o | --options                                                # list books and chapters
/book -h | --help                                                   # show usage
```

### The lifecycle

```text
/book <bookname> <gist>   →  backlog epic (gist.md, epic.md)
/book <bookname> init     →  book.json (chapter plan + filter chain)
/book <bookname> scaffold →  .space/pipeline/<bookname>/ (structure)
/book <bookname> filter * →  run the filter chain (or enrich)
/book <bookname> write    →  source/books/<bookname>/<version>/
/book <bookname> publish  →  source/books/<bookname>/version<k>/
```

---

## Forms

A book is either **poetry** (verse) or **novel** (prose), declared in the pipeline's `form` field.

| Signal | Poetry | Novel |
|--------|--------|-------|
| Source of truth | `model.json` + `bookseed.txt` | `epic.md` |
| Chapter structure | flat, continuous poetic prose | flat, continuous prose |
| Segments per chapter | exactly one (`segments/1`) | many |
| Word target | 500–800 | 5,500+ |
| Stereotype templates | `stereotypes/poetry/` | `stereotypes/novel/` |

---

## The Filter Chain

Filters run in a fixed order inside the pipeline. The chain is declared in `book.json`'s `filter_chain` and materialized as `.space/pipeline/<bookname>/filters/filters.json`.

**Poetry:** `workshop → research → correctness → theme → syntax → override → quality`

**Novel:** `workshop → research → seeds → correctness → theme → syntax`

Each filter is backed by a role agent in `.framework/agents/<filter>/agent.md`. The `enrich` command fuses the active (`autorun: true`) filters into a single combined agent and runs them in one pass.

---

## Role Agents (`.framework/agents/`)

| Agent | Role |
|-------|------|
| `init` | Configure the backlog book plan (`book.json`). |
| `scaffold` | Build the pipeline structure (dispatches to layout skills). |
| `prelayout` / `postlayout` | Pre/post-scaffold preparation and master-prompt seeding. |
| `workshop` | Create the initial chapter frame. |
| `research` | Ground and enrich the chapter. |
| `correctness` | Verify factual and cultural claims. |
| `theme` | Assign the philosophical lens and stereotype. |
| `syntax` | Modernize sentence structure while keeping the register. |
| `override` | Apply the human-in-the-loop transformation (`override.txt`). |
| `quality` | Final quality audit. |
| `enrich` | Fuse active filters into one combined pass. |
| `write` / `chapter` | Write finished reader-facing chapters. |
| `style` | Transform writer-stage chapters through a style template. |
| `translate` | Translate writer-stage chapters. |
| `publish` | Promote segments to `source/books/` and assemble the book. |
| `gist`, `seeds`, `reframe` | Supporting roles. |

---

## Skills (`.framework/skills/`)

Skills are invoked **only through an agent** — never directly. Form-specific layout and workshop skills include:

- `layout-poetry`, `layout-novel` — pipeline scaffold skeletons.
- `workshop-poetry`, `workshop-novel` — chapter-frame creation.
- `poeticprose`, `narrative`, `dialogue`, `pacing` — prose craft.
- `research`, `correctness`, `theme`, `syntax`, `quality`, `revision` — filter backing.
- `translation` — cross-language rendering.
- `geography`, `history`, `indian`, `mythology`, `philosophy`, `contemporary` — grounding.

---

## Stereotypes & Styles

- **Stereotypes** (`.framework/templates/stereotypes/<form>/`) — `signatures/`, `references/`, `themes/`, `syntax/`. Each chapter selects a signature (voice), reference (source text), theme set (philosophical lens), and syntax sample.
- **Styles** (`.framework/templates/styles/<style>/`) — transformer styles (e.g. `pijush`) applied by the `style` command.

---

## Data Layout

| Path | Role |
|------|------|
| `.space/backlog/epic/<book>/` | `gist.md`, `epic.md`, `book.json` (the book plan) |
| `.space/pipeline/<book>/` | `model.json`, `bookseed.txt`, `progress.json`, `filters/`, `chapters/` |
| `.space/pipeline/<book>/chapters/<n>/` | `chapter.md` (live draft), `model.json`, `history/`, `segments/1/{writer,editor,translator}/` |
| `source/books/<book>/<version>/` | finished, versioned reader-facing output |

---

## Quick Start

```text
/book behula "Bengali mythology of Behula..."          # create the backlog epic
/book behula init poetry                               # configure the book plan
/book behula scaffold                                  # build the pipeline
/book behula enrich                                    # fuse active filters into one pass
/book behula write                                     # write finished chapters
/book behula translate bengali                         # translate to Bengali
/book behula publish bengali                           # promote to source/books
```

See `AGENTS.md` for the runtime steering contract and `.framework/workflows/pipeline.md` for the full command specification.

