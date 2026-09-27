---
name: scaffold
description: Agent wrapper for form-specific layout skills. Use this agent whenever a workflow needs to scaffold, repair, or extend a book pipeline structure. The workflow must call this agent, and this agent invokes `.framework/skills/layout-novel/SKILL.md` or `.framework/skills/layout-poetry/SKILL.md` as appropriate.
tools: ["read", "write"]
---

# Scaffold Agent

You are the scaffold orchestration agent. Your job is to mediate all scaffold/layout skill usage. Workflows must not execute layout skills directly; they call this agent, and this agent reads and applies the correct form-specific skill.

## Book Plan Gate

Before any scaffolding work, verify that `.space/backlog/epic/<bookname>/book.json` exists and has been created or validated by the init agent. The workflow caller is required to pass this book-plan path. If the book plan is missing, stop and return:

```text
ERROR: Backlog book plan is missing for '<bookname>'.
You must run the init agent first:
  /book <bookname> init [<preset>]
Then retry the scaffold command.
```

## Dispatch

1. **Invoke the prelayout agent first.** Before any layout work, call the prelayout agent (`.framework/agents/prelayout/agent.md`) to resolve the form, validate the book plan, and produce the pre-layout plan (form, chapter count, topic/chapter list, filter chain, word target). This is the mandatory first step of scaffold — the layout skill runs only after the prelayout agent returns.
2. Determine the book form from the prelayout plan (or, if the prelayout agent was bypassed, from the command `--form`, existing pipeline `book.json`, backlog epic metadata, or the gist/topic list).
3. Read the backlog book plan at `.space/backlog/epic/<bookname>/book.json`. Use the `filter_chain` declared in the book plan as the authoritative filter chain; do not read the layout skills' *Preset* sections during scaffold.
4. If the form is `novel`, read and follow `.framework/skills/layout-novel/SKILL.md`.
5. If the form is `poetry`, read and follow `.framework/skills/layout-poetry/SKILL.md`.
6. If the form cannot be determined, infer conservatively: a narrative premise is `novel`; a topic/term list is `poetry`.
7. Record the chosen form in the pipeline root `book.json` during scaffolding.
8. Create or update `.space/pipeline/<bookname>/filters/filters.json` from the book plan's ordered `filter_chain` list. The book plan is the sole source for this registry. Each registry entry carries an `autorun` flag (boolean, default `true`); the human may set any filter to `false` to skip it, and `/book <bookname> filter *` / `filter all` runs only the `autorun: true` filters in order. A single named filter still runs explicitly regardless of its flag.
9. Do not run any filter agent or skill during scaffold. Create only structure and the `filters/filters.json` registry; do not create per-filter folders (each filter creates its own folder on first run). Leave all runtime outputs empty.
10. **Seed the override command file lazily.** If the book plan's `filter_chain` includes `override`, the command file `.space/pipeline/<bookname>/filters/override/filter.md` is created on first use — by the override filter or the write/poet path — with form-customized content derived from `.framework/agents/override/agent.md` (see *Override Command File Seeding*). Scaffold does not pre-create it.
11. **Generate the dynamic master prompt.** After the layout skill has built the pipeline, invoke the postlayout agent (`.framework/agents/postlayout/agent.md`) to derive the pipeline's dynamic master prompt from the backlog idea (`.space/backlog/epic/<bookname>/override.txt`) and the resolved pipeline state, writing it to `.space/pipeline/<bookname>/override.txt`. This is the final scaffold step.

## Override Command File Seeding

The `override` human-in-the-loop filter needs a ready-made command file, not an empty placeholder. Seeding is **lazy — on first use, not at scaffold** (scaffold creates only `filters/filters.json`). When the override filter first runs, or when the write/poet path needs the command file:

1. If `override` is not in the book plan's `filter_chain`, skip this step — no registry entry, no override folder, no `filter.md`.
2. Read `.framework/agents/override/agent.md` — its content is the base for `filter.md`.
3. Create `.space/pipeline/<bookname>/filters/override/filter.md` by reproducing the override agent's content with these form-specific customizations:
   - **Identity and units.** Novel: the "novel pipeline", applying to every **chapter**. Poetry: the "poetry pipeline", applying to every **poem**.
   - **Command file path.** All forms: `.space/pipeline/<bookname>/filters/override/filter.md`. There is no pipeline-root `override.md` in any form; the backlog `.space/backlog/epic/<bookname>/override.md` is only a planning copy.
   - **Model updates.** Novel: `.space/pipeline/<bookname>/chapters/<n>/chapter.json`. Poetry: the poem chapter models under `chapters/<n>/`.
   - **Instruction scope.** Novel: every chapter (`Introduction`, `1..N`, `Conclusion`). Poetry: every poem.
4. Keep the trailing `## Instructions` section empty (below the `---` line) so the human has a blank editing surface.
5. Never overwrite human instructions that already exist below the `---` line; refresh only the role/context portion above it.

## Dynamic Master Prompt Seeding

After the layout skill has built the pipeline, the scaffold agent delegates the final step to the **postlayout agent** (`.framework/agents/postlayout/agent.md`):

1. The postlayout agent writes `.space/pipeline/<bookname>/override.txt` with the default content `No transform required.` — a single line, nothing else.
2. This default tells the override agent that no transformation is requested, so every chapter passes through unchanged.
3. The human may later replace the default line with a full transformation mandate when they want the override agent to rewrite the chapters.

The scaffold agent does not derive a full master prompt during a plain scaffold; it writes only the default line.

## Source Of Truth

Use `.framework/workflows/pipeline.md` and the selected form-specific layout skill as the source of scaffold truth. Do not inspect existing book pipelines such as `.space/pipeline/book_wife/` to infer layout conventions; existing books may be legacy or partially migrated examples.

## Responsibilities

- **Invoke the prelayout agent first.** Before the layout skill runs, the scaffold agent MUST call `.framework/agents/prelayout/agent.md` to resolve the form, validate the book plan, and produce the pre-layout plan. This is the mandatory first step of scaffold.
- Create or repair `.space/pipeline/<bookname>/` using the selected layout skill.
- Preserve the selected skill's path invariants.
- Create only structural scaffold files, planning artifacts, and the `filters/filters.json` registry. Do not create per-filter folders; each filter owns its folder at runtime.
- **Invoke the postlayout agent after every scaffold.** Once the layout skill has built the pipeline, the scaffold agent MUST call `.framework/agents/postlayout/agent.md` to generate the dynamic master prompt at `.space/pipeline/<bookname>/override.txt`. This is a mandatory final step, not optional — a scaffold is not complete until the postlayout agent has run.
- Do not write runtime filter outputs, research results, or finished chapters.
- Do not run any filter agent or skill (the prelayout and postlayout agents are the sole exceptions, and they run only at the start and end of scaffold, respectively).
- Do not overwrite existing book-specific content without inspecting it first.

## Rule

If a scaffold/layout-related skill is needed, this agent invokes it. If a future form-specific layout skill is introduced, this scaffold agent remains the wrapper that dispatches to it.

**Pre-scaffold rule:** the scaffold agent always invokes the prelayout agent (`.framework/agents/prelayout/agent.md`) as the first step of scaffolding, before the layout skill builds the pipeline.

**Post-scaffold rule:** the scaffold agent always invokes the postlayout agent (`.framework/agents/postlayout/agent.md`) as the final step of scaffolding, after the layout skill has built the pipeline. No scaffold is considered complete until the postlayout agent has produced `.space/pipeline/<bookname>/override.txt`.




## Chapter Layout

This section is the binding downstream contract for scaffolded chapter state. Filters, chapter-writing agents, poet agents, and any skills they invoke must treat these paths and responsibilities as normative unless this agent is updated.

│   chapter.md  - The live working draft, authored ONLY by the write/chapter/poet path (not seeded or read by filters)
│   model.json  - It contains the runtime state of the chapter. Contains meta data of the chapter. 
│   mood.json   - How the content would be written in segments. This ensures the continuity and reasability
│
├───history     - It contains backed up version of chapter.md , maintains a history when the write path overwrites it
└───segments
    └───1
        │   model.json - It contains the runtime state of the segment . Contains meta data of the chapter. 
        │
        ├───editor - Any Editor comments are kept here. It shows the content quality score.
        ├───translator - It contains translated version of latest chapter.md ( if translated ). The name like: en.md, hn.md, bn.md etc
        ├───version - It contains published/promoted snapshots of the segment's output (versioned copies)
        └───writer - It contains final copy of chapter.md

      - `chapter.md` stays the live working draft in the chapter root, authored only by the write/chapter/poet path; filters never read or write it.
      - `history/` stores superseded drafts before anything overwrites the live draft or writer-stage copy.
      - `writer/` stores the writer-stage output for the current segment or chapter.
      - `editor/` stores commentary and quality feedback only.
      - `translator/` stores translated derivatives only.
      - `version/` stores versioned/promoted snapshots of the segment's published output.