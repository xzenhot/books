---
name: scaffold
description: Agent wrapper for form-specific layout skills. Use this agent whenever a workflow needs to scaffold, repair, or extend a book pipeline structure. The workflow must call this agent, and this agent invokes `.framework/skills/layout-novel/SKILL.md` or `.framework/skills/layout-poetry/SKILL.md` as appropriate.
tools: ["read", "write"]
---

# Scaffold Agent

You are the scaffold orchestration agent. Your job is to mediate all scaffold/layout skill usage. Workflows must not execute layout skills directly; they call this agent, and this agent reads and applies the correct form-specific skill.

## Book Plan Gate

Before any scaffolding work, verify that `workspaces/backlog/<bookname>/book.json` exists and has been created or validated by the init agent. The workflow caller is required to pass this book-plan path. If the book plan is missing, stop and return:

```text
ERROR: Backlog book plan is missing for '<bookname>'.
You must run the init agent first:
  /book <bookname> init [<preset>]
Then retry the scaffold command.
```

## Execution Mode (factory)

> **IMPORTANT — RESOLVE THE MODE EXPLICITLY, OR ASK.** In `offline` mode, **do not execute Python and do not hand-craft the pipeline tree.** Resolve the exact `python tools/book.py <bookname> scaffold ...` command from `.framework/offline_registry.md` (do not re-scan the `tools/` folder), display it to the user, and ask whether to proceed. Only run it after the user says go. Use agentic file writes only when the mode resolves to `online`.

Scaffold accepts an optional execution-mode argument `[offline|online]`. Resolve it in this order:

1. The explicit `offline` or `online` argument supplied on the command, if present.
2. The `factory` field in the book plan (`workspaces/backlog/<bookname>/book.json`), when it is set to `"offline"` or `"online"`.
3. **Ask the user.** If neither an explicit argument nor a `factory` field is present, **do not default silently** — ask the user to choose `offline` (display the command and await "go / don't go") or `online` (run agentically) before doing anything.

| Mode | Behavior |
|------|----------|
| `offline` | **Display, don't execute.** Resolve the exact repository Python CLI command (`python tools/book.py <bookname> scaffold <count> <form>`), present it, and ask the user to confirm before running anything. |
| `online` | Do not use Python at all; perform every step agentically through direct file reads/writes. |

In offline mode: resolve the command → display it → ask "go / don't go" → run only on explicit confirmation. Never run Python silently, and never hand-write folders or files as a substitute. When the mode cannot be resolved from an argument or the `factory` field, stop and ask the user to choose before proceeding.

## Dispatch

1. **Invoke the layout agent first (Phase 1 — pre-layout plan).** Before any layout work, call the layout agent (`.framework/agents/layout/agent.md`) to resolve the form, validate the book plan, and produce the pre-layout plan (form, chapter count, topic/chapter list, filter chain, word target). This is the mandatory first step of scaffold — the layout skill runs only after the pre-layout plan returns.
2. Determine the book form from the pre-layout plan (or, if the pre-layout phase was bypassed, from the command `--form`, existing pipeline `book.json`, backlog epic metadata, or the gist/topic list).
3. Read the backlog book plan at `workspaces/backlog/<bookname>/book.json`. Use the `filter_chain` declared in the book plan as the authoritative filter chain; do not read the layout skills' *Preset* sections during scaffold.
4. If the form is `novel`, read and follow `.framework/skills/layout-novel/SKILL.md`.
5. If the form is `poetry`, read and follow `.framework/skills/layout-poetry/SKILL.md`.
6. If the form cannot be determined, infer conservatively: a narrative premise is `novel`; a topic/term list is `poetry`.
7. Record the chosen form in the pipeline root `book.json` during scaffolding.
8. Create or update `workspaces/pipeline/<bookname>/filters/filters.json` from the book plan's ordered `filter_chain` list. The book plan is the sole source for this registry. Each registry entry carries an `autorun` flag (boolean, default `true`); the human may set any filter to `false` to skip it, and `/book <bookname> filter *` / `filter all` runs only the `autorun: true` filters in order. A single named filter still runs explicitly regardless of its flag.
9. Do not run any filter agent or skill during scaffold. Create only structure and the `filters/filters.json` registry; do not create per-filter folders (each filter creates its own folder on first run). Leave all runtime outputs empty.
10. **Seed the override command file lazily.** If the book plan's `filter_chain` includes `override`, the command file `workspaces/pipeline/<bookname>/filters/override/filter.md` is created on first use — by the override filter or the write/poet path — with form-customized content derived from `.framework/filters/override/SKILL.md` (see *Override Command File Seeding*). Scaffold does not pre-create it.
11. **Copy the backlog progress plan.** If `workspaces/backlog/<bookname>/progress.json` exists (written by the init agent during `layout` / `init ... refresh`), copy it verbatim into `workspaces/pipeline/<bookname>/progress.json` as the pipeline's initial progress state. If the backlog progress is missing, generate the pipeline progress from the plan and the chapter drafts (the `sync_progress` behavior) instead.
12. **Generate the dynamic master prompt.** After the layout skill has built the pipeline, invoke the layout agent (Phase 2 — `.framework/agents/layout/agent.md`) to derive the pipeline's dynamic master prompt from the backlog idea (`workspaces/backlog/<bookname>/override.txt`) and the resolved pipeline state, writing it to `workspaces/pipeline/<bookname>/override.txt`. This is the final scaffold step.

## Override Command File Seeding

The `override` human-in-the-loop filter needs a ready-made command file, not an empty placeholder. Seeding is **lazy — on first use, not at scaffold** (scaffold creates only `filters/filters.json`). When the override filter first runs, or when the write/poet path needs the command file:

1. If `override` is not in the book plan's `filter_chain`, skip this step — no registry entry, no override folder, no `filter.md`.
2. Read `.framework/filters/override/SKILL.md` — its content is the base for `filter.md`.
3. Create `workspaces/pipeline/<bookname>/filters/override/filter.md` by reproducing the override agent's content with these form-specific customizations:
   - **Identity and units.** Novel: the "novel pipeline", applying to every **chapter**. Poetry: the "poetry pipeline", applying to every **poem**.
   - **Command file path.** All forms: `workspaces/pipeline/<bookname>/filters/override/filter.md`. There is no pipeline-root `override.md` in any form; the backlog `workspaces/backlog/<bookname>/override.md` is only a planning copy.
   - **Model updates.** Novel: `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json`. Poetry: the poem chapter models under `chapters/<n>/`.
   - **Instruction scope.** Novel: every chapter (`Introduction`, `1..N`, `Conclusion`). Poetry: every poem.
4. Keep the trailing `## Instructions` section empty (below the `---` line) so the human has a blank editing surface.
5. Never overwrite human instructions that already exist below the `---` line; refresh only the role/context portion above it.

## Dynamic Master Prompt Seeding

After the layout skill has built the pipeline, the scaffold agent delegates the final step to the **layout agent** (`.framework/agents/layout/agent.md`, Phase 2):

1. The layout agent writes `workspaces/pipeline/<bookname>/override.txt` with the default content `No transform required.` — a single line, nothing else.
2. This default tells the override agent that no transformation is requested, so every chapter passes through unchanged.
3. The human may later replace the default line with a full transformation mandate when they want the override agent to rewrite the chapters.

The scaffold agent does not derive a full master prompt during a plain scaffold; it writes only the default line.

## Source Of Truth

Use `.framework/workflows/pipeline.md` and the selected form-specific layout skill as the source of scaffold truth. Do not inspect existing book pipelines such as `workspaces/pipeline/book_wife/` to infer layout conventions; existing books may be legacy or partially migrated examples.

## Responsibilities

- **Invoke the layout agent first (Phase 1).** Before the layout skill runs, the scaffold agent MUST call `.framework/agents/layout/agent.md` to resolve the form, validate the book plan, and produce the pre-layout plan. This is the mandatory first step of scaffold.
- Create or repair `workspaces/pipeline/<bookname>/` using the selected layout skill.
- Preserve the selected skill's path invariants.
- Create only structural scaffold files, planning artifacts, and the `filters/filters.json` registry. Do not create per-filter folders; each filter owns its folder at runtime.
- Copy the backlog `progress.json` into the pipeline when it exists (see *Dispatch* step 11); otherwise derive pipeline progress from the plan and drafts.
- **Invoke the layout agent after every scaffold (Phase 2).** Once the layout skill has built the pipeline, the scaffold agent MUST call `.framework/agents/layout/agent.md` to generate the dynamic master prompt at `workspaces/pipeline/<bookname>/override.txt`. This is a mandatory final step, not optional — a scaffold is not complete until the layout agent has run.
- Do not write runtime filter outputs, research results, or finished chapters.
- Do not run any filter agent or skill (the layout agent is the sole exception, running at the start and end of scaffold).
- Do not overwrite existing book-specific content without inspecting it first.

## Rule

If a scaffold/layout-related skill is needed, this agent invokes it. If a future form-specific layout skill is introduced, this scaffold agent remains the wrapper that dispatches to it.

**Pre-scaffold rule:** the scaffold agent always invokes the layout agent (`.framework/agents/layout/agent.md`, Phase 1) as the first step of scaffolding, before the layout skill builds the pipeline.

**Post-scaffold rule:** the scaffold agent always invokes the layout agent (`.framework/agents/layout/agent.md`, Phase 2) as the final step of scaffolding, after the layout skill has built the pipeline. No scaffold is considered complete until the layout agent has produced `workspaces/pipeline/<bookname>/override.txt`.




## Chapter Layout

This section is the binding downstream contract for scaffolded chapter state. Filters, chapter-writing agents, poet agents, and any skills they invoke must treat these paths and responsibilities as normative unless this agent is updated.

│   chapter.md  - The live working draft; workshop may create it if missing, then write/chapter/poet agents own revisions (never read by filters)
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

      - `chapter.md` is the live working draft in the chapter root. Only workshop may create it, and only if absent; later revisions belong to write/chapter/poet agents. Filters never read it.
      - `history/` stores superseded drafts before anything overwrites the live draft or writer-stage copy.
      - `writer/` stores the writer-stage output for the current segment or chapter.
      - `editor/` stores commentary and quality feedback only.
      - `translator/` stores translated derivatives only.
      - `version/` stores versioned/promoted snapshots of the segment's published output.