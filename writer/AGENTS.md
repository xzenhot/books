# AGENTS.md

Universal runtime steering for autonomous coding agents operating in this repository. This document is intentionally self-contained and uses only repository-native markdown instructions. Do not add scripts, wrappers, aliases, shell helpers, or generated command shims to interpret it.

## Runtime Contract

This repository is an autonomous literary workflow system. Agent engines such as Claude Code, GitHub Copilot CLI, Kiro, and Codex must treat this file as the root steering document, then delegate detailed workflow behavior to the framework files under `.framework/`.

The primary command surface is:

```text
/book [args...]
```

When a user invokes `/book`, parse the arguments, inspect the current repository state, then execute the matching workflow defined in one of the two start-point specs under `.framework/workflows/`:

```text
.framework/workflows/backlog.md    # Phase 0–1: backlog creation (bare bookname + init/backlog/layout)
.framework/workflows/pipeline.md   # Phase 2 onward: scaffold, filters, write, style, translate, publish
```

`backlog.md` is the authoritative spec for backlog creation — the bare bookname command (create/update the backlog epic and its seed gist) and the init/backlog/layout command (configure the backlog book plan and derive the ordered filter chain). `pipeline.md` is the authoritative spec for everything after the backlog — command syntax, book lifecycle, filter order, progress tracking, form handling, and output promotion.

## Strict Slash Command Protocol

All `/book` commands must be interpreted from left to right. Preserve user-provided argument text exactly unless the workflow explicitly normalizes it.

Supported command families are defined by the two start-point specs. The backlog-creation families (below) are defined by `.framework/workflows/backlog.md`; the pipeline families are defined by `.framework/workflows/pipeline.md`. At minimum, the runtime must recognize these shapes:

```text
/book <bookname> [<gist>] [form] [refresh]
/book <bookname> init|backlog|layout [<gist>] [<count>] [form] [refresh]
/book <bookname> scaffold <gist> count|chapter-count <number> [--form novel|poetry]
/book <bookname> add <chapter-count> filter <filter>
/book <bookname> filter <filter>
/book <bookname> enrich <count>|range|*
/book <bookname> review *|all|<n>
/book <bookname> humanize *|all|<n>
/book <bookname> write <n>|all|continue [<style>]        # default style: pijush
/book <bookname> style [<style>]
/book <bookname> translate <n>|all|continue <language>
/book <bookname> publish [<language>]
/book <bookname> form <novel|poetry>
/book <bookname> config [<key> [<value>]]

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
.space/backlog/<bookname>/       -> backlog folder
.space/pipeline/<bookname>/ -> pipeline folder
source/books/<bookname>/<version>/ -> final versioned book output folder
```

If the user supplies `book_wife` or a legacy `book_<bookname>` path, treat the canonical `<bookname>` as `wife` (strip the `book_` prefix) unless an existing path proves otherwise. Prefer existing repository paths over inference. The pipeline folder is named directly after the book: `.space/pipeline/<bookname>/`.

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
.space/pipeline/<bookname>/chapters/<chapter>/
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/
```

For poetry, every chapter has exactly one segment:

```text
segments/1
```

Do not create chapter folders outside `chapters/`. Do not create segment folders outside `chapters/<chapter>/segments/`.

### Signature Or Author Persona

A signature/persona argument selects an authorial voice. Resolve it from the form-specific stereotype folders:

```text
.framework/templates/stereotypes/novel/signatures/<signature>/signature.md
.framework/templates/stereotypes/poetry/signatures/<signature>/signature.md
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
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/writer/
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/editor/
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/translator/
```

Filter-stage roles are implemented by agents under:

```text
.framework/agents/<filter>/agent.md
```

Known filter agents:

```text
correctness, enrich, override, quality, research, seeds, syntax,
theme, workshop
```

Known lifecycle agents:

```text
init, scaffold, write, chapter, style, translate, publish, gist, reframe, eval
```

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
.framework/agents/<agent-name>/agent.md
```

The agent may then read and apply the corresponding skill:

```text
.framework/skills/<skill-name>/SKILL.md
```

If a required agent is missing, create `.framework/agents/<agent-name>/agent.md` first, then use that agent to invoke the skill. Do not bypass this rule for layout, research, filters, writing, editing, translation, or validation.

Scaffold/layout work is always mediated by:

```text
.framework/agents/scaffold/agent.md
```

The scaffold agent dispatches to:

```text
.framework/skills/layout-novel/SKILL.md
.framework/skills/layout-poetry/SKILL.md
```

## Framework Source Map

Use these framework locations as authoritative inputs.

### Workflow

The `/book` command surface is split across two start-point workflow specs:

```text
.framework/workflows/backlog.md   # backlog creation — bare bookname, init/backlog/layout
.framework/workflows/pipeline.md  # scaffold onward — filters, write, style, translate, publish
```

`backlog.md` owns Phase 0 (Backlog) and Phase 1 (Init): the bare bookname command and the init/backlog/layout command, operating only inside `.space/backlog/<bookname>/`. `pipeline.md` owns Phase 2 onward: scaffold, the filter chain, write, style, translate, enrich, form, config, add, and publish, operating only inside `.space/pipeline/<bookname>/` and `source/books/`.

### Agents

```text
.framework/agents/init/agent.md
.framework/agents/gist/agent.md
.framework/agents/scaffold/agent.md
.framework/agents/prelayout/agent.md
.framework/agents/postlayout/agent.md
.framework/agents/workshop/agent.md
.framework/agents/research/agent.md
.framework/agents/correctness/agent.md
.framework/agents/theme/agent.md
.framework/agents/syntax/agent.md
.framework/agents/override/agent.md
.framework/agents/quality/agent.md
.framework/agents/enrich/agent.md
.framework/agents/humanize/agent.md
.framework/agents/eval/agent.md
.framework/agents/poetry/agent.md
.framework/agents/story/agent.md
.framework/agents/style/agent.md
.framework/agents/translate/agent.md
.framework/agents/publish/agent.md
.framework/agents/reframe/agent.md
.framework/agents/seeds/agent.md
```

Agents are the only valid runtime entry points for skill-backed behavior.

### Skills

```text
.framework/skills/contemporary/SKILL.md
.framework/skills/correctness/SKILL.md
.framework/skills/dialogue/SKILL.md
.framework/skills/geography/SKILL.md
.framework/skills/history/SKILL.md
.framework/skills/indian/SKILL.md
.framework/skills/layout/SKILL.md
.framework/skills/layout-novel/SKILL.md
.framework/skills/layout-poetry/SKILL.md
.framework/skills/mythology/SKILL.md
.framework/skills/narrative/SKILL.md
.framework/skills/pacing/SKILL.md
.framework/skills/philosophy/SKILL.md
.framework/skills/poeticprose/SKILL.md
.framework/skills/workshop-poetry/SKILL.md
.framework/skills/workshop-novel/SKILL.md
.framework/skills/quality/SKILL.md
.framework/skills/research/SKILL.md
.framework/skills/revision/SKILL.md
.framework/skills/syntax/SKILL.md
.framework/skills/theme/SKILL.md
.framework/skills/translation/SKILL.md
```

Read skill files only from inside the responsible agent flow.

### Rules And Templates

```text
.framework/rules/
.framework/templates/moods/
.framework/templates/stereotypes/novel/
.framework/templates/stereotypes/poetry/
.framework/templates/subjects/
```

Use templates as source material; do not copy whole template trees into pipelines unless a scaffold agent explicitly requires it.

## Data And Output Path Map

### Backlog Source

Novel backlog epics live at:

```text
.space/backlog/<bookname>/storyline.md
```

For novels, `storyline.md` is the story source of truth. Do not invent story content beyond it.

### Pipeline Working State

Book pipelines live at:

```text
.space/pipeline/<bookname>/
```

Common pipeline files:

```text
.space/pipeline/<bookname>/book.json          # the book plan (cloned from the backlog)
.space/pipeline/<bookname>/characters.json
.space/pipeline/<bookname>/bookseed.txt
.space/pipeline/<bookname>/progress.json
.space/pipeline/<bookname>/filters/
.space/pipeline/<bookname>/chapters/
```

Novel pipelines use `storyline.md`, `book.json`, `characters.json`, chapter folders, moods, segments, and filters.

Poetry pipelines use `book.json` and `bookseed.txt` as source of truth, one segment per topic, and no `mood.json` unless explicitly configured as a hybrid.

### Segment Drafts

Intermediate segment work stays inside `.space/pipeline/`:

```text
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/writer/
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/editor/
.space/pipeline/<bookname>/chapters/<chapter>/segments/<segment>/translator/
```

Do not write unfinished drafts directly to `source/books/`.

### Chapter Draft Ownership

`chapters/<n>/chapter.md` is the live draft. The workshop filter may create an initial draft only when the file is absent; it never reads or overwrites an existing draft. The write/chapter/poet path may later revise it under the version-before-overwrite contract. All other filters and the enrich fusion agent must not read or write `chapter.md`; they operate on the chapter's `model.json` and their own `filters/<filter>/` outputs. Before a filter modifies a chapter's model, snapshot the prior `model.json` into `chapters/<chapter>/history/` with a timestamped filename. The default transformer style for the write command is `pijush` unless a `<style>` argument is supplied.

### Filter Outputs

Filters write only inside the pipeline filter folders resolved by:

```text
.space/pipeline/<bookname>/filters/filters.json
```

If a registry exists, use it to resolve each filter's `agent` path and `autorun` flag. Each registry entry carries only:

```text
order
name
agent
summary_file
autorun
```

If no registry exists, follow `.framework/workflows/pipeline.md` and the current pipeline layout.

### Final Output

Verified, finalized text is promoted to:

```text
source/books/<bookname>/<version>/chapters/
source/books/<bookname>/<version>/book.md
```

Only promote text after the required validation filters have passed.

## Validation And Promotion Rules

Before writing to `source/books/`, apply the pipeline filters in the order specified by `.framework/workflows/pipeline.md`.

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
- Never create root-level chapter folders under `.space/pipeline/<bookname>/`.
- Never create segment folders outside `chapters/<chapter>/segments/<segment>/`.
- Never move, rename, delete, or overwrite user-authored content without first reading it and confirming the workflow requires the change.
- Never re-scaffold an existing pipeline from scratch unless the user explicitly asks.
- Preserve existing pipeline state and resume from it.
- Maintain the configured authorial tone, signature, language, register, syntax sample, reference, and theme set.
- Prefer existing framework agents, skills, templates, and rules over new abstractions.
- Keep runtime outputs in `.space/pipeline/` until validation permits promotion.
- Keep finished, reader-facing text in versioned folders under `source/books/<bookname>/<version>/` only.

## Operating Procedure

For every `/book` request:

1. Read this `AGENTS.md` file.
2. Read the matching start-point spec — `.framework/workflows/backlog.md` for backlog creation (bare bookname, init/backlog/layout), `.framework/workflows/pipeline.md` for scaffold onward.
3. Parse the target book, unit/chapter/segment, signature/persona, and stage/role from the user arguments.
4. Inspect the relevant `.space/backlog/`, `.space/pipeline/`, and `source/books/` paths before writing.
5. Select the responsible agent from `.framework/agents/`.
6. Let that agent invoke any required skill.
7. Write intermediate outputs only to the pipeline; workshop may create an initial `chapters/<n>/chapter.md` only if absent. Other filters never read or write that file.
8. Run the required filters and validations.
9. Promote final text to `source/books/` only after validation passes.
10. Report what changed, what was validated, and what remains pending.





