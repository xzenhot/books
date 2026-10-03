# AGENTS.md

Universal runtime steering for autonomous coding agents operating in this repository. This document is intentionally self-contained and uses only repository-native markdown instructions. Do not add scripts, wrappers, aliases, shell helpers, or generated command shims to interpret it.

## Runtime Contract

This repository is an autonomous literary workflow system. Agent engines such as Claude Code, GitHub Copilot CLI, Kiro, and Codex must treat this file as the root steering document, then delegate detailed workflow behavior to the framework files under `writer/.framework/`.

The primary command surface is:

```text
/book [args...]
```

When a user invokes `/book`, parse the arguments, inspect the current repository state, then execute the matching workflow defined in one of the two start-point specs under `writer/.framework/workflows/`:

```text
writer/.framework/workflows/backlog.md    # Phase 0–1: backlog creation (bare bookname + init/backlog/layout)
writer/.framework/workflows/pipeline.md   # Phase 2 onward: scaffold, filters, write, style, translate, publish
```

`backlog.md` is the authoritative spec for backlog creation — the bare bookname command (create/update the backlog epic and its seed gist) and the init/backlog/layout command (configure the backlog book plan and derive the ordered filter chain). `pipeline.md` is the authoritative spec for everything after the backlog — command syntax, book lifecycle, filter order, progress tracking, form handling, and output promotion.

## Strict Slash Command Protocol

All `/book` commands must be interpreted from left to right. Preserve user-provided argument text exactly unless the workflow explicitly normalizes it.

Supported command families are defined by the two start-point specs. The backlog-creation families (below) are defined by `writer/.framework/workflows/backlog.md`; the pipeline families are defined by `writer/.framework/workflows/pipeline.md`. At minimum, the runtime must recognize these shapes:

```text
/book <bookname> [<gist>] [form] [refresh]
/book <bookname> init|backlog|layout [<gist>] [<count>] [form] [refresh]
/book <bookname> init idea
/book <bookname> scaffold <gist> count|chapter-count <number> [--form novel|poetry]
/book <bookname> add <chapter-count> filter <filter>
/book <bookname> filter <filter>
/book <bookname> <agentname> <chapter>|<n>|all|continue
/book <bookname> enrich <count>|range|*
/book <bookname> review *|all|<n>
/book <bookname> humanize *|all|<n>
/book <bookname> eval all|*|<n>|<range>|continue
/book <bookname> write <n>|all|continue [<style>]        # default style: pijush
/book <bookname> style [<style>]
/book <bookname> translate <n>|all|continue <language>
/book <bookname> publish [<language>]
/book <bookname> form <novel|poetry>
/book <bookname> config [<key> [<value>]]
/book <bookname> poet|poetry|poem

/book -o | --options | list
/book -h | --help
```

Do not invent alternate slash commands. Do not treat subcommand keywords as book names, chapter names, filters, or prose.

## Parameter Parsing

When parsing `/book [args...]`, classify parameters into these slots.

### Target Work Or Book

The first positional argument after `/book` is normally `<bookname>`.

Map it to repository paths as follows:

```text
<bookname>                       -> logical book name, e.g. wife
writer/.space/backlog/<bookname>/       -> backlog folder
writer/.space/pipeline/<bookname>/ -> pipeline folder
writer/source/books/<bookname>/<version>/ -> final versioned book output folder
```

If the user supplies `book_wife` or a legacy `book_<bookname>` path, treat the canonical `<bookname>` as `wife` (strip the `book_` prefix) unless an existing path proves otherwise. Prefer existing repository paths over inference. The pipeline folder is named directly after the book: `writer/.space/pipeline/<bookname>/`.

### Unit, Chapter, And Segment

A chapter/unit argument may be:

```text
Introduction
Conclusion
<n>
all
continue
<topic-name>
```

A segment may be expressed as:

```text
<chapter>/<segment>
1/1
Introduction/1
Conclusion/1
```

Map chapter and segment paths to:

```text
writer/.space/pipeline/<bookname>/chapters/<chapter>/
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/
```

For poetry, every chapter has exactly one segment:

```text
segments/1
```

Do not create chapter folders outside `chapters/`. Do not create segment folders outside `chapters/<chapter>/segments/`.

### Signature Or Author Persona

A signature/persona argument selects an authorial voice. Resolve it from the form-specific stereotype folders:

```text
writer/.framework/templates/stereotypes/novel/signatures/<signature>/signature.md
writer/.framework/templates/stereotypes/poetry/signatures/<signature>/signature.md
```

Known novel signatures include:

```text
aurilus, bankim, bibhutibhushan, dostoevsky, faulkner, gibran, hemingway,
jibanananda, joyce, kafka, mahasweta, manik, marquez, morrison, mujtaba,
proust, rabindrasangeet, sarat, sunil, tarashankar, tolstoy, woolf
```

Known poetry signatures include:

```text
aurilus, blake, dickinson, eliot, gibran, hafez, jibanananda, lorca,
nazrul, neruda, rabindranath, rabindrasangeet, rilke, rumi, shakti,
sukanta, whitman, yeats
```

Read the relevant `registry.md` before using a signature when the workflow requires discovery or validation.

### Stage Or Role

A stage/role argument identifies the pipeline actor responsible for a unit of work:

```text
writer
editor
translator
```

Segment-stage paths are:

```text
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/writer/
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/editor/
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/translator/
```

Filter-stage roles are implemented by agents under:

```text
writer/.framework/agents/<filter>/agent.md
```

Known filter agents:

```text
correctness, enrich, override, quality, research, seeds, syntax,
theme, workshop
```

Known lifecycle agents:

```text
init, scaffold, write (routes to story/poetry), chapter, style, translate,
publish, review, humanize, gist, reframe, eval
```

`write` is not a standalone agent: it dispatches to the form-resolved writing agent (`story` for novels, `poetry` for poetry). `review` and `humanize` are lifecycle agents with their own agents and CLI verbs.

Known post-scaffold agents:

```text
postlayout
```

Known pre-scaffold agents:

```text
prelayout
```

## Agent-First Skill Invocation

Workflows must never execute skills directly.

All skill-backed work must route through an agent:

```text
writer/.framework/agents/<agent-name>/agent.md
```

The agent may then read and apply the corresponding skill:

```text
writer/.framework/skills/<skill-name>/SKILL.md
```

If a required agent is missing, create `writer/.framework/agents/<agent-name>/agent.md` first, then use that agent to invoke the skill. Do not bypass this rule for layout, research, filters, writing, editing, translation, or validation.

Scaffold/layout work is always mediated by:

```text
writer/.framework/agents/scaffold/agent.md
```

The scaffold agent dispatches to:

```text
writer/.framework/skills/layout-novel/SKILL.md
writer/.framework/skills/layout-poetry/SKILL.md
```

## Framework Source Map

Use these framework locations as authoritative inputs.

### Workflow

The `/book` command surface is split across two start-point workflow specs:

```text
writer/.framework/workflows/backlog.md   # backlog creation — bare bookname, init/backlog/layout
writer/.framework/workflows/pipeline.md  # scaffold onward — filters, write, style, translate, publish
```

`backlog.md` owns Phase 0 (Backlog) and Phase 1 (Init): the bare bookname command and the init/backlog/layout command, operating only inside `writer/.space/backlog/<bookname>/`. `pipeline.md` owns Phase 2 onward: scaffold, the filter chain, write, style, translate, enrich, form, config, add, and publish, operating only inside `writer/.space/pipeline/<bookname>/` and `writer/source/books/`.

### Agents

```text
writer/.framework/agents/init/agent.md
writer/.framework/agents/gist/agent.md
writer/.framework/agents/scaffold/agent.md
writer/.framework/agents/prelayout/agent.md
writer/.framework/agents/postlayout/agent.md
writer/.framework/agents/workshop/agent.md
writer/.framework/agents/research/agent.md
writer/.framework/agents/correctness/agent.md
writer/.framework/agents/theme/agent.md
writer/.framework/agents/syntax/agent.md
writer/.framework/agents/override/agent.md
writer/.framework/agents/quality/agent.md
writer/.framework/agents/enrich/agent.md
writer/.framework/agents/humanize/agent.md
writer/.framework/agents/eval/agent.md
writer/.framework/agents/poetry/agent.md
writer/.framework/agents/story/agent.md
writer/.framework/agents/style/agent.md
writer/.framework/agents/translate/agent.md
writer/.framework/agents/publish/agent.md
writer/.framework/agents/reframe/agent.md
writer/.framework/agents/seeds/agent.md
```

Agents are the only valid runtime entry points for skill-backed behavior.

### Skills

```text
writer/.framework/skills/contemporary/SKILL.md
writer/.framework/skills/correctness/SKILL.md
writer/.framework/skills/dialogue/SKILL.md
writer/.framework/skills/geography/SKILL.md
writer/.framework/skills/history/SKILL.md
writer/.framework/skills/indian/SKILL.md
writer/.framework/skills/layout/SKILL.md
writer/.framework/skills/layout-novel/SKILL.md
writer/.framework/skills/layout-poetry/SKILL.md
writer/.framework/skills/mythology/SKILL.md
writer/.framework/skills/narrative/SKILL.md
writer/.framework/skills/pacing/SKILL.md
writer/.framework/skills/philosophy/SKILL.md
writer/.framework/skills/poeticprose/SKILL.md
writer/.framework/skills/workshop-poetry/SKILL.md
writer/.framework/skills/workshop-novel/SKILL.md
writer/.framework/skills/quality/SKILL.md
writer/.framework/skills/research/SKILL.md
writer/.framework/skills/revision/SKILL.md
writer/.framework/skills/syntax/SKILL.md
writer/.framework/skills/theme/SKILL.md
writer/.framework/skills/translation/SKILL.md
```

Read skill files only from inside the responsible agent flow.

### Rules And Templates

```text
writer/.framework/rules/
writer/.framework/templates/moods/
writer/.framework/templates/stereotypes/novel/
writer/.framework/templates/stereotypes/poetry/
writer/.framework/templates/subjects/
```

Use templates as source material; do not copy whole template trees into pipelines unless a scaffold agent explicitly requires it.

## Python Tool Routing

Every structural, repeatable operation is performed by a Python tool under `writer/.tools/`. Content authoring — the actual prose or verse of a chapter — is never scripted; it always routes through a writing agent (see *Agent-First Skill Invocation*).

Invoke tools from the repository root with the `writer/.tools/` path prefix, e.g. `python writer/.tools/book.py <bookname> <verb>`. From inside the `writer/` folder, drop the `writer/` prefix (`python .tools/book.py <bookname> <verb>`).

### Unified CLI

The single entry point for backlog and pipeline lifecycle commands is:

```text
python writer/.tools/book.py <bookname> <verb> [args...]
```

Verbs: `init`, `backlog` (alias of `init`), `build`, `layout`, `scaffold`, `enrich`, `write`, `publish`, `preview`, `review`, `humanize`. Flags: `-t/--type poetry|novel` (default `poetry`), `-r/--refresh`, `--gist "text"`, `--draft`.

### Command → tool routing

```text
/book <bookname> init [<gist>] [novel|poetry] [refresh]  -> python writer/.tools/book.py <bookname> init [<gist>] [novel|poetry] [refresh]
/book <bookname> init idea                                -> python writer/.tools/book.py <bookname> init idea
/book <bookname> layout [<count>] [novel|poetry]          -> python writer/.tools/book.py <bookname> layout [<count>] [novel|poetry]
/book <bookname> scaffold [<count>] [novel|poetry]        -> python writer/.tools/book.py <bookname> scaffold [<count>] [novel|poetry]
/book <bookname> enrich *|all                            -> python writer/.tools/book.py <bookname> enrich [all|*]   # BULK ONLY; single/range/count/continue -> enrich agent directly
/book <bookname> enrich <n>|<range>|<count>|continue      -> agentic: writer/.framework/agents/enrich/agent.md (no Python)
/book <bookname> review [all|*|<n>|<range>|continue]      -> python writer/.tools/book.py <bookname> review [all|*|<n>|<range>|continue]
/book <bookname> humanize [all|*|<n>|<range>|continue]    -> python writer/.tools/book.py <bookname> humanize [all|*|<n>|<range>|continue]
/book <bookname> publish [<language>]                     -> python writer/.tools/book.py <bookname> publish [<language>] [--draft]
/book <bookname> preview                                  -> python writer/.tools/book.py <bookname> preview
/book <bookname> write *|all [<style>]                   -> python writer/.tools/book.py <bookname> write [all|*] [--style <nickname>]   # BULK ONLY; single/range/continue -> writing agent directly
/book <bookname> write <n>|<range>|continue [<style>]      -> agentic: writer/.framework/agents/story/agent.md (novel) | poetry/agent.md (poetry) (no Python)
```

`preview` is `publish --draft`. `book.py review` and `book.py humanize` load and run `writer/.tools/review.py` and `writer/.tools/humanize.py`; `book.py enrich`/`write`/`publish` load `writer/.tools/enrich.py`/`write.py`/`publish.py`.

### Direct tool entry points

```text
python writer/.tools/book.py <bookname> init|build|layout [args]         # backlog create/configure (Ollama)
python writer/.tools/book.py <bookname> scaffold [count] [novel|poetry]  # poetry -> scaffold_poetry.py; novel -> in-process layout
python writer/.tools/book.py <bookname> enrich [all|1|1-5|continue]
python writer/.tools/book.py <bookname> write <chapters> [--style NICK] [--segment N]
python writer/.tools/book.py <bookname> publish [<language>] [--draft]
python writer/.tools/book.py <bookname> review [all|*|<n>|<range>|continue]
python writer/.tools/book.py <bookname> humanize [all|*|<n>|<range>|continue]
python writer/.tools/layout.py <bookname> [--chapter-count N] [--gist "text"]   # novel layout (Python alternative to layout.ps1)
python writer/.tools/scaffold_poetry.py <bookname>                               # poetry scaffold engine
python writer/.tools/enrich.py <bookname> [chapters] [--seed N] [--lens NAME] [--model M] [--temperature T] [--dry-run] [--list-lenses]
python writer/.tools/write.py <bookname> <chapters> [--style NICK] [--segment N]
python writer/.tools/publish.py <bookname> [--draft]
python writer/.tools/review.py <bookname> [all|*|<n>|<range>|continue]
python writer/.tools/humanize.py <bookname> [all|*|<n>|<range>|continue]
python writer/.tools/syntax_filter.py <bookname> [all|1|1-5|continue]            # the syntax filter's runner
python writer/.tools/quality.py <bookname> register-existing                     # register existing drafts (no rewrite)
python writer/.tools/flatten.py <bookname> <chapter>                             # model.json -> context.md
python writer/.tools/add_chapters.py <bookname>                                  # append chapters and reconcile state
python writer/.tools/verify_pipeline.py <bookname>                               # pipeline integrity check
python writer/.tools/server.py                                                   # MCP search server (research)
python writer/.tools/book_server.py                                              # MCP book API server (publish service)
python writer/.tools/search-cli.py "<query>" --backend searxng --max 5 --pretty   # research grounding CLI
```

### Agent → tool routing

```text
init       -> python writer/.tools/book.py <bookname> init|build|layout [args]
gist       -> python writer/.tools/book.py <bookname> init idea
scaffold   -> python writer/.tools/book.py <bookname> scaffold [count] [novel|poetry]
enrich     -> BULK (*|all): python writer/.tools/book.py <bookname> enrich [all|*]  (writer/.tools/enrich.py)
              narrow (<n>|<range>|<count>|continue): writer/.framework/agents/enrich/agent.md directly (no Python)
publish    -> python writer/.tools/book.py <bookname> publish [lang]       (writer/.tools/publish.py)
review     -> python writer/.tools/book.py <bookname> review [target]      (writer/.tools/review.py)
humanize   -> python writer/.tools/book.py <bookname> humanize [target]    (writer/.tools/humanize.py)
write      -> BULK (*|all): python writer/.tools/book.py <bookname> write [all|*] [--style NICK]   (bulk runner; authored content still comes from the writing agent)
              narrow (<n>|<range>|continue): agentic: writer/.framework/agents/story/agent.md (novel) | poetry/agent.md (poetry) (no Python)
research   -> python writer/.tools/server.py | python writer/.tools/search-cli.py "<query>" --backend searxng --max 5 --pretty
syntax     -> python writer/.tools/syntax_filter.py <bookname> [target]
quality    -> python writer/.tools/quality.py <bookname> register-existing  (the review itself is agentic)
```

### Rules

- `filter` has **no** standalone CLI runner (`book.py ... filter` errors). Route it to the registered filter agent at `writer/.framework/agents/<filter>/agent.md`; `syntax` is the only filter with a direct script (`writer/.tools/syntax_filter.py`).
- `enrich` and `write` are **scope-dependent**: `*`/`all` delegate to the CLI bulk runner (`book.py enrich [all|*]` → `writer/.tools/enrich.py`; `book.py write [all|*]` → `writer/.tools/write.py`); any narrow target (`<n>`, `<range>`, `<count>`, `continue`) is executed **agentically with no Python** — enrich via `writer/.framework/agents/enrich/agent.md`, write via the form-resolved writing agent (`writer/.framework/agents/story/agent.md` for novels, `writer/.framework/agents/poetry/agent.md` for poetry). The `book.py enrich`/`write` verbs are bulk-only structural wrappers; they do not replace agentic execution.
- Agents are agentic, not Python: `workshop`, `correctness`, `seeds`, `theme`, `override`, `quality`, `style`, `translate`, `gist`, `reframe`, `eval`, `prelayout`, `postlayout`, `story`, `poetry`, `enrich` (on narrow targets), and every filter agent write only Markdown/JSON under `writer/.space/pipeline/` or the backlog. They must not invent, invoke, or shell out to any Python tool other than the routed ones above.
- Run from the repository root and prefix with `writer/.tools/`. The research commands quoted in `writer/.framework/agents/research/agent.md` are written relative to `writer/`; from the repository root they must be prefixed with `writer/`.

## Data And Output Path Map

### Backlog Source

Novel backlog epics live at:

```text
writer/.space/backlog/<bookname>/storyline.md
```

For novels, `storyline.md` is the story source of truth. Do not invent story content beyond it.

### Pipeline Working State

Book pipelines live at:

```text
writer/.space/pipeline/<bookname>/
```

Common pipeline files:

```text
writer/.space/pipeline/<bookname>/book.json          # the book plan (cloned from the backlog)
writer/.space/pipeline/<bookname>/characters.json
writer/.space/pipeline/<bookname>/bookseed.txt
writer/.space/pipeline/<bookname>/progress.json
writer/.space/pipeline/<bookname>/filters/
writer/.space/pipeline/<bookname>/chapters/
```

Novel pipelines use `storyline.md`, `book.json`, `characters.json`, chapter folders, moods, segments, and filters.

Poetry pipelines use `book.json` and `bookseed.txt` as source of truth, one segment per topic, and no `mood.json` unless explicitly configured as a hybrid.

### Segment Drafts

Intermediate segment work stays inside `writer/.space/pipeline/`:

```text
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/writer/
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/editor/
writer/.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/translator/
```

Do not write unfinished drafts directly to `writer/source/books/`.

### Chapter Draft Ownership

`chapters/<n>/chapter.md` is the live draft. The workshop filter may create an initial draft only when the file is absent; it never reads or overwrites an existing draft. The write/chapter/poet path may later revise it under the version-before-overwrite contract. All other filters and the enrich fusion agent must not read or write `chapter.md`; they operate on the chapter's `model.json` and their own `filters/<filter>/` outputs. Before a filter modifies a chapter's model, snapshot the prior `model.json` into `chapters/<chapter>/history/` with a timestamped filename. The default transformer style for the write command is `pijush` unless a `<style>` argument is supplied.

### Filter Outputs

Filters write only inside the pipeline filter folders resolved by:

```text
writer/.space/pipeline/<bookname>/filters/filters.json
```

If a registry exists, use it to resolve each filter's `agent` path and `autorun` flag. Each registry entry carries only:

```text
order
name
agent
summary_file
autorun
```

If no registry exists, follow `writer/.framework/workflows/pipeline.md` and the current pipeline layout.

### Final Output

Verified, finalized text is promoted to:

```text
writer/source/books/<bookname>/<version>/chapters/
writer/source/books/<bookname>/<version>/book.md
```

Only promote text after the required validation filters have passed.

## Validation And Promotion Rules

Before writing to `writer/source/books/`, apply the pipeline filters in the order specified by `writer/.framework/workflows/pipeline.md`.

For novels, the full validation chain is:

```text
workshop -> research -> seeds -> correctness -> theme -> syntax -> override -> quality
```

For poetry, the full validation chain is:

```text
workshop -> research -> correctness -> theme -> syntax -> override -> quality
```

`quality` is the final gate. Do not mark a chapter complete or promote it to final output until quality has passed or the workflow explicitly records an accepted human override.

## Safety And Structure Constraints

- Never alter the repository directory structure unless the active workflow explicitly requires it.
- Never create root-level chapter folders under `writer/.space/pipeline/<bookname>/`.
- Never create segment folders outside `chapters/<chapter>/segments/<segment>/`.
- Never move, rename, delete, or overwrite user-authored content without first reading it and confirming the workflow requires the change.
- Never re-scaffold an existing pipeline from scratch unless the user explicitly asks.
- Preserve existing pipeline state and resume from it.
- Maintain the configured authorial tone, signature, language, register, syntax sample, reference, and theme set.
- Prefer existing framework agents, skills, templates, and rules over new abstractions.
- Keep runtime outputs in `writer/.space/pipeline/` until validation permits promotion.
- Keep finished, reader-facing text in versioned folders under `writer/source/books/<bookname>/<version>/` only.

## Operating Procedure

For every `/book` request:

1. Read this `AGENTS.md` file.
2. Read the matching start-point spec — `writer/.framework/workflows/backlog.md` for backlog creation (bare bookname, init/backlog/layout), `writer/.framework/workflows/pipeline.md` for scaffold onward.
3. Parse the target book, unit/chapter/segment, signature/persona, and stage/role from the user arguments.
4. Inspect the relevant `writer/.space/backlog/`, `writer/.space/pipeline/`, and `writer/source/books/` paths before writing.
5. Select the responsible agent from `writer/.framework/agents/`.
6. Route the work using the *Python Tool Routing* section: send structural, repeatable operations (`init`/`layout`/`scaffold`/`publish`/`review`/`humanize` and helper scripts) to the matching `python writer/.tools/...` tool with the documented parameters; send content authoring (`style`/`translate`) to the responsible agent. For `enrich` and `write`, apply the scope rule: `*`/`all` delegate to the CLI bulk runner, while any narrow target (`<n>`, `<range>`, `<count>`, `continue`) is executed agentically with no Python (enrich agent, or story/poetry writing agent).
7. Let that agent invoke any required skill.
8. Write intermediate outputs only to the pipeline; workshop may create an initial `chapters/<n>/chapter.md` only if absent. Other filters never read or write that file.
9. Run the required filters and validations.
10. Promote final text to `writer/source/books/` only after validation passes.
11. Report what changed, what was validated, and what remains pending.





