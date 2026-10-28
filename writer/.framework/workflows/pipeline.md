---
name: pipeline
description: The authoritative Phase 2+ workflow spec for the /book pipeline. Owns scaffold onward — the filter chain, write, style, translate, enrich, form, config, add, review, humanize, and publish — operating only inside workspaces/pipeline/<bookname>/ and workspaces/published/. It routes every command to its owning agent and defers detailed behavior to those agents and their skills; it never executes a skill directly.
---

# The Pipeline Workflow (Phase 2 Onward)

This workflow owns every `/book` command after the backlog phase. It is a **router**: it parses a command, resolves its owning agent (`.framework/agents/<agent>/agent.md`), and delegates — the agent then reads and applies any required skill. This file does not define skill behavior; it defines command surface, phase ordering, boundaries, and the delegation map.

A book is either a **novel** (prose) or **poetry** (verse), declared in the pipeline's `form` field. The pipeline turns filter outputs into finished chapters under versioned folders in `workspaces/published/<bookname>/<version>/`.

## Command Boundary

Every command in this workflow **must pass through** `.framework/rules/command-boundary.md` before executing. That rule is the authoritative boundary contract and applies to all commands, in all workflows, in both forms (novel and poetry).

- Read `.framework/rules/command-boundary.md` first, and treat its backlog/pipeline boundary and sequence rules as binding on every command below.
- This workflow owns **pipeline commands only**. It must never modify `workspaces/backlog/<bookname>/storyline.md` or `book.json`; it may read the backlog read-only.
- If a command would violate the boundary, stop and respond with the exact error form defined in that rule.

## Next Steps

After **every** command in this workflow completes — including read-only, no-op, and early-stop results — append a **Next Steps** section to the response, following `.framework/rules/next-steps.md`. That rule is mandatory and unconditional; it maps each completed command to its recommended next action and optional follow-ups. Read it and apply it to every response.

## Audit Metadata

Every `.md` or `.json` file this workflow's agents create or edit under `workspaces/` must carry `updated_by` and `updated_date`, per `.framework/rules/audit-metadata.md`. Read that rule before the first write.

- **JSON** (`book.json`, `progress.json`, `characters.json`, `filters.json`, filter outputs): root-level `updated_by` and `updated_date`; keep a legacy `updated_at` in sync.
- **Markdown** (`masterprompt.md`, `filters/override/filter.md`, `style.md`, assembled `book.md`, filter outputs): a two-bullet block directly after the H1 (or at the top when no H1) — `- **updated_by:** <agent>` and `- **updated_date:** <ISO-8601-UTC>`.
- **Stamp as:** the acting agent (`scaffold`, `filter:<name>`, `write`, `publish`, `style`, ...). A skill inherits its invoking agent's identity.
- **Exempt:** the entire `workspaces/pipeline/<bookname>/chapters/**` tree and all `_history/`, `history/`, and `version/` archive snapshots. Never stamp immutable copies.
- **Assembled books:** keep one consolidated block after the H1 in `book.md`; strip per-chapter blocks from the concatenated body.
- **Clones:** stamp a copied file after copying; equality checks ignore the audit fields.

## Command Reference

```text

/book <bookname> scaffold count                                                      # 1. scaffold a new book pipeline
/book <bookname> <agentname> <chapter>|<n>|all|continue                              # 2. execute agent on each chapters in the pipeline
/book <bookname> write <n>|range|all|continue [<style>]                               # 3. write finished chapter output (four tasks: enrich -> draft -> transform -> compose)
/book <bookname> chapter <n>|all|continue [<style>]                                    # 3a. alias of write (routed through the write agent)
/book <bookname> story <n>|all|continue [<style>]                                       # 3b. alias of write (routed through the write agent)
/book <bookname> style [<style>]                                                     # 4. transform writer-stage chapters through a style template
/book <bookname> translate <n>|all|continue <language>                               # 5. translate latest writer-stage chapter version
/book <bookname> filter <filter> *|all|<n>                              # 6. run a single filter on a scope
/book <bookname> enrich <count>|range|*                                              # 6a. fuse active filters into one combined agent and enrich chapters in one pass
/book <bookname> eval all|*|<n>|<range>|continue                                     # 6b. evaluate pipeline completeness before write/publish (read-only)
/book <bookname> review *|all|<n>                              # 6c. audit chapters against quality parameters via the review agent (quality gate)
/book <bookname> humanize *|all|<n>                            # 6d. ensure content is in the target language only; remove non-relevant characters
/book <bookname> form <formname>                                                     # 7. set/change the book's form
/book <bookname> config [<key> [<value>]]                                            # 8. get/set the book's model config
/book <bookname> add <chapter-count> filter <filter>                          # 9. add chapters and run a single filter
/book -o | --options | list                                                         # 10. list available books and chapters
/book -h | --help                                                                    # 11. show usage
/book <bookname> publish [<language>]                                                # 12. publish latest writer/translator segments to workspaces/published and assemble book.md
/book <bookname> preview [<language>]                                                # 13. assemble book.md from current drafts without quality review (draft preview)


```


| Command | What it does |
|---------|--------------|
| `scaffold` | Creates or repairs `workspaces/pipeline/<bookname>/` through the scaffold agent, gated by the existence of `book.json`. Never creates or modifies `storyline.md`. |
| `<agentname>` | Runs any registered agent against selected chapters in an existing pipeline. Does not promote output to `workspaces/published/`. |
| `write` | Runs the four-task composition sequence (enrich -> draft -> transform -> compose) and writes the finished chapter to `chapters/<n>/chapter.md`, updating `progress.json`. It does not promote to `workspaces/published/` — that is `publish`. Routes through the **write agent** (`.framework/agents/write/agent.md`), which resolves the form and dispatches to the poetry or novel skill. Ensures the writer-stage segment exists, archiving any prior copy first. Language resolves from `book.json` when not supplied. |
| `chapter` / `story` | Aliases of `write` — write finished chapters through the **write agent** (`.framework/agents/write/agent.md`), routing to the poetry or novel skill by form. |
| `publish [<language>]` | Routes through the publish agent (`.framework/agents/publish/agent.md`) to promote the latest writer-stage segments to a versioned folder `workspaces/published/<bookname>/version<k>/` and assemble `version<k>/book.md`. Without `<language>`, copies the latest segment from `chapters/<n>/segments/1/writer/`. With `<language>`, copies the latest translator segment from `chapters/<n>/segments/1/translator/` (e.g. `en.md`, `bn.md`). Read-only on pipeline content; writes to `workspaces/published/` and updates (and stamps) the pipeline `progress.json`. Each publish creates a new version, so multiple published versions coexist. |
| `preview [<language>]` | Assembles the same output as `publish` — promotes the latest writer-stage (or translator, with `<language>`) segments into a versioned `workspaces/published/<bookname>/version<k>/` folder and assembles `version<k>/book.md` — but **skips the quality gate and review step**. It runs everything `publish` does except validation: no quality pass, no review requirement, no draft-hash check. Useful for inspecting a full draft of the book as it stands without waiting for review to pass. |

| `style` | Applies a transformer style to the latest writer-stage chapter versions, delegating to the enrich agent for the target chapter before falling back to chapter-root `chapter.md` when no writer-stage draft exists. Resolves `<style>` from `.framework/context/poetry/styles/<style>/style.md`, defaults to `pijush`, and writes new writer-stage versions under `segments/1/writer/`. The enrich prerequisite may update the live draft and model after archiving; styling writes only a new writer version and does not promote output. |
| `translate` | Translates the latest writer-stage chapter version from `workspaces/pipeline/<bookname>/chapters/<n>/segments/1/writer/` into the requested language and writes the translated derivative to `workspaces/pipeline/<bookname>/chapters/<n>/segments/1/translator/`. Does not modify the live draft or promote output. |
| `poet` (aliases: `poetry`, `poem`) | Invokes the write agent (`.framework/agents/write/agent.md`) to produce a single finished poem based on the human-authored `override.md` if it exists. |
| `filter` | Runs a single named filter inside an existing pipeline. Never scaffolds or writes finished chapters. The `*` / `all` bulk form is disabled; run each filter separately. |
| `enrich` | Fuses the active (`autorun: true`) filters from `filters.json` into one combined agent and runs it in a single pass over the selected chapters, recording the combined enrichment guidance in each chapter's `model.json` ready for write or publish. Never scaffolds, never reads or writes `chapter.md`, and never writes finished chapters. |
| `review *|all|<n>` | Audit chapters against the seed analysis's quality parameters via the review agent at `.framework/agents/review/agent.md`; the quality gate that must pass before publish. Records `quality_review` result and sets state to `"completed"` on pass. |
| `humanize *|all|<n>` | Ensure content is in the target language only (Bengali). Remove non-relevant characters (Chinese, Urdu, Latin) embedded in Bengali text and replace with Bengali equivalents. |
| `form` | Changes the pipeline's `form` field and reconciles form-driven settings. |
| `config` | Reads or writes book-level configuration values in `model.json` and chapter models. Requires an existing pipeline. |
| `add <chapter-count> filter <filter>` | Adds more main chapters to an existing book pipeline, then runs the requested single filter for the newly added chapters. |
| `options` | Lists book pipelines in `workspaces/pipeline/` and their `workspaces/published/` destinations. Read-only. |
| `help` | Shows usage. |

Every subcommand keyword is literal and unambiguous. The aliases poetry and poem are synonyms of poet; the aliases chapter and story are synonyms of write.

## Command → Agent Routing

This workflow routes every command to exactly one owning agent. The agent owns the
behavior and may invoke a form-specific skill; this file only dispatches. When a
command has an `offline` execution route, the agent resolves the command from
`.framework/offline_registry.md` and asks the user to confirm before running.

| Command | Owning agent | Form-specific skill |
|---------|--------------|---------------------|
| `scaffold` | `.framework/agents/scaffold/agent.md` | `layout-novel` / `layout-poetry` |
| `filter <filter>` | `.framework/agents/filter/agent.md` | `.framework/filters/<filter>/SKILL.md` |
| `<agentname>` | `.framework/agents/<agentname>/agent.md` | (agent-selected) |
| `enrich` | `.framework/agents/enrich/agent.md` | `enrich-novel` / `enrich-poetry` |
| `eval` | `.framework/agents/eval/agent.md` | — (read-only) |
| `review` | `.framework/agents/review/agent.md` | `quality-novel` / `quality-poetry` |
| `humanize` | `.framework/agents/humanize/agent.md` | — |
| `write` / `chapter` / `story` | `.framework/agents/write/agent.md` | `novel` / `poetry`, then `line` (transform), then the form skill (`sonnet` / `lyrics` / `limerick` / `haiku` / `poyar`) |
| `poyar` / `payar` | `.framework/agents/poyar/agent.md` | `.framework/skills/poyar/SKILL.md` |
| `style` | `.framework/agents/style/agent.md` | (style template) |
| `translate` | `.framework/agents/translate/agent.md` | — |
| `publish` | `.framework/agents/publish/agent.md` | — |
| `preview` | `.framework/agents/publish/agent.md` | — |
| `form` | (workflow-level reconcile) | — |
| `config` | (workflow-level, `model.json`) | — |
| `add ... filter` | (workflow-level) + `.framework/agents/filter/agent.md` | — |
| `poet` / `poetry` / `poem` | `.framework/agents/write/agent.md` | `poetry` |
| `options` / `help` | (workflow-level, read-only) | — |

Offline-capable commands (resolve from `.framework/offline_registry.md`): `scaffold`,
`publish`, `enrich`, and `write` — in `offline` mode every scope of these commands
resolves to Python CLI and runs after user confirmation.

## Poetry Lifecycle Contract

The authoritative poetry lifecycle rules live in `.framework/rules/poetry-lifecycle.md`.
They take precedence over legacy writer-stage conventions. Key points: scaffold is
resumable (never replaces chapter models/poems/overrides); the current poem is
`chapters/<n>/chapter.md` (segment `writer/` is legacy, never a source); every
write/style replacement archives and records `draft.sha256`; quality reviews the
actual current poem; only publish creates reader-facing output.

## Rules Index

Cross-cutting rules that every command and agent must honor (read the full rule
before the command that needs it):

| Rule | File | Applies to |
|------|------|------------|
| Command boundary & execution mode (`factory`) | `.framework/rules/command-boundary.md` | every command |
| Next steps (mandatory after every command) | `.framework/rules/next-steps.md` | every command |
| Audit metadata (`updated_by` / `updated_date`) | `.framework/rules/audit-metadata.md` | every workspace write (except chapters and history snapshots) |
| Poetry lifecycle contract | `.framework/rules/poetry-lifecycle.md` | poetry pipelines |
| Mandatory draft version before overwrite | `.framework/rules/draft-versioning.md` | write / style / poet |
| Source versioning (reader-facing output) | `.framework/rules/source-versioning.md` | write / publish |
| Form discriminator | `.framework/rules/form-discriminator.md` | form resolution |
| Chapter layout contract (schema + paths) | `.framework/rules/chapter-layout.md` | scaffold, all filters, write |
| Offline command registry | `.framework/offline_registry.md` | offline-mode commands |

## Workflow Phases and Responsibilities

The `/book` workflow is a linear pipeline of six phases. Each phase has **one trigger command**, **one clear responsibility**, **one primary output**, and **one owning agent or internal process**. No phase may skip an earlier phase.

| Phase | Trigger command | Responsibility | Owner | Primary input | Primary output |
|---|---|---|---|---|---|
| 2 — Scaffold | `/book <bookname> scaffold <gist> count|chapter-count <n> [--form novel|poetry]` | Build the pipeline structure using the preset and form. | Scaffold agent (`.framework/agents/scaffold/agent.md`) | Epic/gist, preset, form | `workspaces/pipeline/<bookname>/` tree |
| 3 — Filter chain | `/book <bookname> filter <filter>`<br>`/book <bookname> <agentname> <chapter>` | Run research/preparatory agents in strict order. No finished chapters. | Named filter/agent | Pipeline context, epic | `workspaces/pipeline/<bookname>/filters/<filter>/` |
| 4 — Write | `/book <bookname> write <n>|range|all|continue <language>` | Turn filter outputs into finished reader-facing chapters. | Write agent (`.framework/agents/write/agent.md`) → poetry/novel skill | Filter outputs | `workspaces/published/<bookname>/<version>/chapters/<n>.md` |
| 4a — Style | `/book <bookname> style [<style>]` | Transform latest writer-stage chapter versions through a named transformer style. | Style agent (`.framework/agents/style/agent.md`) | `.framework/context/poetry/styles/<style>/style.md` + `segments/1/writer/` | next `segments/1/writer/chapter_v*.md` |
| 4b — Translate | `/book <bookname> translate <n>|all|continue <language>` | Translate latest writer-stage chapter versions without changing the live draft. | Translate agent (`.framework/agents/translate/agent.md`) | `segments/1/writer/chapter_v*.md` or `chapter.md` | `segments/1/translator/<language>.md` |
| 5 — Quality & promote | `/book <bookname> filter quality`<br>`/book <bookname> review *|all|<n>` | Final quality gate and assembly into `book.md`. | Review agent (`.framework/agents/review/agent.md`) | Completed chapters | `workspaces/published/<bookname>/<version>/book.md` |
| 5b — Humanize | `/book <bookname> humanize *|all|<n>` | Polish chapter drafts to the target language only; remove non-relevant characters and replace with Bengali equivalents. | Humanize agent (`.framework/agents/humanize/agent.md`) | Reviewed chapters | Humanized `chapters/<n>/chapter.md` |

### Phase gates

- **Phase 3 is gated by Phase 2.** Filters and agents require an existing pipeline. If `workspaces/pipeline/<bookname>/` is missing, stop and require `scaffold`.
- **Phase 4 is gated by Phase 3.** Do not write a chapter until the filters that feed it have produced their outputs.
- **Phase 5 is gated by Phase 4.** Do not assemble `book.md` until all chapters are written.
- **Review is gated by Phase 4 (write).** Do not review a chapter until it has a non-empty `chapter.md` draft. A chapter must be written before it can be reviewed.
- **Humanize is gated by Phase 5 (review).** Do not humanize a chapter until its quality review has passed and it has a valid draft hash. Humanize runs after quality review and before publish.

The workflow orchestrates these phases; it **never** executes layout, research, theme, syntax, or quality skills directly. It routes every skill-backed operation through the agent that owns the current phase. 

## The Agent Command

For `/book <bookname> <agentname> <chapter>|<n>|all|continue`:

Responsibility: run one named agent against selected chapters inside an existing pipeline. Used mainly for ad-hoc filter work. The workflow routes the call to the agent; the agent may invoke its own skill.

1. Stop if `workspaces/pipeline/<bookname>/` does not exist; use `scaffold` first.
2. Resolve the pipeline form from `model.json`. Stop if the form cannot be determined.
3. Resolve `<agentname>` to `.framework/agents/<agentname>/agent.md`. If the agent file does not exist, stop and report the missing agent.
4. Read the agent file. If the agent needs a skill, it may invoke `.framework/skills/<agentname>/SKILL.md` or another skill as directed by its own instructions; this workflow does not execute skills directly.
5. Resolve the target chapter(s):
   - A bare `<n>` targets that numbered chapter.
   - `<chapter>` targets that named chapter (`Introduction`, `Conclusion`, or a topic from `book.json`'s `chapters[].chapter_title`).
   - `all` targets every canonical chapter in order (`Introduction`, `1..N`, `Conclusion` for novels; `book.json` `chapters[]` order for poetry).
   - `continue` targets the first chapter that is pending in `progress.json` or missing the agent's expected upstream input.
6. For each target chapter, collect its current context: `model.json`, `mood.json` (novel), segment state, upstream filter outputs, the epic (novel), or the topic (poetry).
7. Pass that context to the agent and let the agent produce its output. Write the output to the location defined by the agent's contract (typically `workspaces/pipeline/<bookname>/filters/<agentname>/` for filter-like agents, or another agent-specific folder).
8. Do not promote output to `workspaces/published/`; that is the responsibility of the `write` command or final assembly.
9. Update any agent-specific summary or progress files as required by the agent.

The agent command is a generalization of the `filter` command: `filter` runs a named filter agent in the fixed filter chain, while `<agentname>` runs any registered agent against selected chapters and is useful for ad-hoc agent work (e.g. running only `research` on a freshly scaffolded novel, or running `poet` on a specific poetry chapter).

## The Config Command

For `/book <bookname> config [<key> [<value>]]`:

Responsibility: inspect or modify book-level configuration values in `model.json` and chapter models.

1. Stop if the pipeline does not exist.
2. With no argument, print the current `model.json` configuration (stereotype selections, form, word targets, etc.).
3. With `<key>`, print that key's value from `model.json`.
4. With `<key> <value>`, set the key across the root `model.json` and all chapter `model.json` files, where applicable.
5. Do not create chapters, run filters, or write finished output. Configuration changes are preparation only; subsequent `filter` or `chapter` commands apply them.

## The Options Command

For `/book -o` / `/book --options` / `/book list`:

Responsibility: list existing book pipelines and their output destinations. This command is read-only and never modifies any file.

1. Scan `workspaces/pipeline/` for `book_*/book.json` entries (falling back to `model.json` for legacy pipelines).
2. Print each book name, form, chapter count, and `workspaces/published/<bookname>/<version>/` destinations.
3. Report any backlog epics that have no pipeline.

## The Help Command

For `/book -h` / `/book --help`:

Responsibility: display the command reference and phase overview. This command is read-only and never modifies any file.

## Form Discriminator

The form is declared once at scaffold time in the pipeline's `form` field. See
`.framework/rules/form-discriminator.md` for the full novel-vs-poetry table
(source of truth, chapter structure, segments, `mood.json`, filter chain, word
target, stereotype templates). The `form` field drives: stereotype template
folder, filter chain, chapter structure and word target, and source-of-truth file.

## Core Rules

- **Pipeline first.** No chapter may be written until `workspaces/pipeline/<bookname>/` exists and its per-chapter research is produced. Always check whether the pipeline exists; if it does, work with its data — never re-scaffold from scratch.
- **Filters never scaffold.** The `filter` command is read/write on existing pipeline data only: it never creates folders, seeds planning artifacts, or runs layout or research scaffold steps.
- **Archive before replacing drafts.** Every write/chapter/poet agent must copy and verify the existing `chapter.md` as the next `segments/<x>/version/chapter_v<k>.md` before overwriting it; see **Mandatory Draft Version Before Overwrite**.
- **Version, never overwrite.** Every `write` invocation creates a fresh numeric version under `workspaces/published/<bookname>/`; `write continue` chooses the next pending pipeline chapter, then writes it into that new version folder.
- **The epic is the single source of truth for a novel's story.** Chapter narratives are drawn from the epic, never invented from the gist. The gist is indicative only. `model.json` is the source of truth for poetry: it holds *how* to write (language, register, quality, themes, reference, index) and *what* to write (the `chapters[]` array, one entry per topic — its `chapter_title` and `chapter_summary`).
- **Gist vs. summary.** The gist is exactly one sentence (used for `book_long_title`). The book summary is a 5–10 sentence paragraph outlining the complete story, derived from the epic and stored as `book_summary`. When the epic changes, regenerate the gist and update `model.json`.
- **Read before writing.** Before writing any chapter, read its seed/JSON from the pipeline's `filters/`, including `included_characters` and `quality_parameters` (novel) or the topic and category (poetry).
- **Agents invoke skills.** Never execute a skill directly from this workflow. Route every skill-backed operation through an agent in `.framework/agents/<name>/agent.md`; the agent may then read and apply `.framework/skills/<name>/SKILL.md`. If the required agent does not exist, create that agent first, then have the agent invoke the skill.
- **Offline commands resolve from `.framework/offline_registry.md`.** In `offline` mode, do **not** re-read or re-scan the `tools/` folder to discover commands. Consult `.framework/offline_registry.md` — the authoritative index of every offline command — to resolve the exact command, display it to the user, and ask for confirmation before running. If a new helper script is genuinely required, add it to `tools/` (never inside `workspaces/pipeline/<bookname>/`) and record it in `.framework/offline_registry.md`. Prefer reusing an existing registered script over writing a new one. One-off content generation (the actual prose/verse of a chapter) is authored directly, not scripted; only structural, repeatable operations belong in `tools/`.

## Scaffolding

### The scaffold command

For `/book <bookname> scaffold <gist> count|chapter-count <number> [--form novel|poetry]`:

Responsibility: build the pipeline structure from the backlog book plan and form. This phase is gated by configuration.

> **Delegate to the repository CLI (display, don't execute).** Scaffold is a structural, repeatable operation resolved as `python tools/book.py <bookname> scaffold [count] [novel|poetry]`. In `offline` mode, **do not run Python yourself** — resolve the exact command, display it to the user, and ask whether to proceed; run it only after the user confirms. Do not hand-craft the pipeline or create new scripts inside `workspaces/pipeline/<bookname>/`.

1. **Book plan is mandatory.** Before scaffolding, the init agent must have been run and `workspaces/backlog/<bookname>/book.json` must exist. If it does not exist, stop and instruct the user to run `/book <bookname> init ` first. Do not silently fall back to a default template.
2. If the pipeline already exists, skip scaffolding and work with the existing data.
3. Read the form from the backlog book plan. If `--form` is supplied, it must match the plan; otherwise stop and require the backlog plan to be updated through `init` first. Do not infer or replace the cloned plan's form during scaffold.
4. Read the gist and chapter count from `book.json`. Explicit gist/count arguments must agree with the plan; if they differ, stop and require `init` to update the backlog plan first. Do not silently rewrite the plan during scaffold.
5. Stop if the backlog epic is missing for a novel; do not create or rewrite it. The actual story always comes from the existing epic.
6. Invoke the scaffold agent at `.framework/agents/scaffold/agent.md`; do not invoke layout skills directly. Pass the epic (novel) or the gist/topic list (poetry), the chapter count, and **the path to the backlog book plan** `workspaces/backlog/<bookname>/book.json`.
7. The scaffold agent MUST invoke the layout agent (`.framework/agents/layout/agent.md`, Phase 1) as its first step, before any layout work, to resolve the form, validate the book plan, and produce the pre-layout plan. The layout skill runs only after the pre-layout plan returns.
8. **Clone the book plan and seed chapter models (mandatory).** After Phase 1 validation and before layout populates chapter folders, the scaffold agent must copy all three backlog source files — `gist.md`, `storyline.md`, and `book.json` — from `workspaces/backlog/<bookname>/` to `workspaces/pipeline/<bookname>/`. Copy `workspaces/backlog/<bookname>/book.json` to `workspaces/pipeline/<bookname>/book.json` in full, and copy `gist.md` and `storyline.md` verbatim alongside it. For Behula, this is `workspaces/backlog/behula/book.json` → `workspaces/pipeline/behula/book.json`. After copying, stamp each copied `.md`/`.json` with `updated_by: "scaffold"` and the current `updated_date` per `.framework/rules/audit-metadata.md`; the copy stays semantically identical. Preserve every other field, value, and chapter entry; do not substitute a template or a reduced runtime model. Seed each chapter model from its matching `chapters` entry according to the model contract below. Use the cloned plan's declared `filter_chain` sequence to build `filters/filters.json`, never the layout skills' preset chain. Scaffold creates **only** `filters/filters.json` (the registry); it does not create per-filter folders — each filter creates its own `filters/<filter>/` folder when it first runs. These requirements take precedence over conflicting scaffold-agent or layout-skill model templates.
9. Apply form-specific initialization (below).
10. **Seed the override command file lazily.** The override command file `workspaces/pipeline/<bookname>/filters/override/filter.md` is not created at scaffold. It is seeded on first use — by the override filter, the write/poet path, or any step that needs it — with form-customized content derived from `.framework/filters/override/SKILL.md` whenever `override` appears in the book plan's `filter_chain`.
11. **Generate the dynamic master prompt.** After layout, the scaffold agent MUST invoke the layout agent (`.framework/agents/layout/agent.md`, Phase 2) to derive the pipeline's dynamic master prompt from the backlog idea (`workspaces/backlog/<bookname>/override.txt`) and the resolved pipeline state, writing it to `workspaces/pipeline/<bookname>/override.txt`. This is a mandatory final step — a scaffold is not complete until the layout agent has run.
12. **Verify the model contract before completing scaffold.** The root `book.json` must still equal the complete backlog `book.json` as parsed JSON after layout and the master prompt, ignoring `updated_by`, `updated_date`, and the synchronized legacy `updated_at` per `.framework/rules/audit-metadata.md`. Each chapter model must contain all fields from its matching plan entry with identical values and types. Missing, duplicated, or mismatched chapter identities fail validation; do not report scaffold complete until resolved. Run only the scaffold and layout agents and delegated layout work here, not filter or writing agents. After scaffold, the user must run `/book <bookname> filter <filter>` for each filter, in order, to populate filter outputs.
13. Write chapters only after all filter outputs have been produced.

Scaffold execution goes through `.framework/agents/scaffold/agent.md`, and that agent invokes the selected form-specific layout skill. The authoritative scaffold rules live in `.framework/skills/layout-novel/SKILL.md` for novels and `.framework/skills/layout-poetry/SKILL.md` for poetry; the scaffold agent selects the correct one by form.

The current scaffold invariants are:

- New book pipelines live under `workspaces/pipeline/<bookname>/`.
- Finished book output lives under `workspaces/published/<bookname>/`.
- Chapter folders use numeric level names: `chapters/<n>/`.
- Segment folders use numeric level names: `chapters/<n>/segments/<x>/`.
- Do not create chapter number folders directly under `<bookname>/`.
- Do not create segment number folders outside `chapters/<n>/segments/`.
- Do not scaffold `Template*.json`, `TemplatePrompt*.txt`, or `TemplateSystemPromptText.txt` into a book pipeline.
- Include `book.json`/`chapter.json` at book/chapter levels and `segment.json` at segment level; each is a level state file, not a template file.
- Create root planning artifacts: `book.json`, `characters.json`, `masterprompt.md`, `workshop_metadata.md`, and `filters/`.

### Form-specific initialization (after layout)

**Both forms:** preserve the cloned root `model.json` unchanged during scaffold, including form-specific initialization and the master-prompt phase. Read book settings from it; do not regenerate titles, summaries, chapter plans, or add template defaults to the root model. Any required missing book configuration must be resolved through backlog `init` before scaffold. Later explicit `config` or runtime operations may update the pipeline independently.

**Novel:** use the cloned `gist`, `form`, `book_long_title`, and `book_summary`. Resolve the epic at `workspaces/backlog/<bookname>/storyline.md` without injecting an `epic_path` field into the cloned model.

**Poetry:**
1. Do not create any `workspaces/published/` destination during scaffold; reader-facing version folders are created only by the `write` command.
2. Read poetry settings from the cloned `model.json`; do not replace it with a poetry template or inject extra root fields during scaffold.
3. The chapter topics live in `book.json`'s `chapters[]` array (each entry's `chapter_title`/`chapter_summary`); there is no separate topic list. The override command file is `filters/override/filter.md`, seeded by scaffold step 9 from `.framework/filters/override/SKILL.md` (dynamically customized for the poetry form and pipeline context). Do **not** create a pipeline-root `override.md`.
4. Initialize `progress.json` with all topics pending if it does not already exist, using `.framework/templates/backlog/progress.json` as the template shape.

### Progress tracking (both forms)

For **poetry**, scaffold `progress.json` at the book pipeline root. The file tracks the writing state of each topic declared in `book.json`'s `chapters[]` array: total chapters, completed chapters, current chapter, and a per-topic array of `{chapter_number, topic, category, status, file_path, completed_date}`. Use `.framework/templates/backlog/progress.json` as the template shape, but re-seed it with the actual topics and categories from the current pipeline.

For **novels**, also scaffold `progress.json` at the book pipeline root. Use the same template shape, but populate it with the novel's canonical chapter order: `Introduction`, `1..N`, `Conclusion`. Set all chapters to `status: "pending"` and `completed_date: null` until written. Update the file after each chapter is written (mark status `completed` and set `completed_date` to the current ISO 8601 timestamp). Before `write continue` or `write all`, read `progress.json` to determine which chapters remain.

### Chapter layout contract

The chapter model schema and chapter paths are defined in
`.framework/rules/chapter-layout.md` — read it for the full contract. Key points:
the required chapter fields are `chapter_index`, `name`, `word_target`,
`chapter_title`, `chapter_summary`, `further_references` (never renamed to
`topic`/`title`/`summary`); `chapter.md` is the live draft owned by workshop
(create-only) and the write path; filters operate only on `chapter.json` and their
own `filters/<filter>/` outputs; versioned/translated derivatives belong in segment
`version/`, `writer/`, `editor/`, or `translator/` folders.


## The Epic (Novel only)

The epic is the single source of truth for a novel's story, at `workspaces/backlog/<bookname>/storyline.md`.

Every epic embeds a **Metadata** block near the top, right after the title and subtitle, recording the project's provenance and identity:

| Field | Meaning |
|-------|---------|
| Title / Book name / Storyline path | The book's long title; the `<bookname>`; `workspaces/backlog/<bookname>/storyline.md` |
| Created / `updated_date` / `updated_by` | ISO 8601 timestamps and the agent that last updated (see `.framework/rules/audit-metadata.md`) |
| User / Author / Machine | The invoking user; the authoring engine; the producing model/agent |
| Language / Genre / Era | The epic's language code, genre, and historical era |
| Chapter count / Gist | The number of chapters; the single-sentence gist |

When creating an epic, always write this block; when the epic changes, keep it current. The flow into the pipeline is:

```
gist → create epic (if absent)
epic → summarize → gist (indicative, saved to model.json)
epic → layout → chapter plan (chapters, titles, summaries, characters)
chapter plan → research → workshop → chapters
```

## The Add Command

For `/book <bookname> add <chapter-count> filter <filter>`:

Responsibility: extend an existing pipeline with additional main chapters and run a single named filter for only those new chapters.

1. Stop if `workspaces/pipeline/<bookname>/` does not exist; use `scaffold` first.
2. Read `model.json`, `book.json`, and the existing chapter folders to determine the current main chapter count.
3. Treat `<chapter-count>` as the number of additional main chapters to append, not the new total.
4. Update the backlog epic and book plan with new chapter entries that continue the existing narrative arc.
5. Update `chapter_count` in `model.json`, `book.json`, and epic metadata to the new total.
6. Create only the new chapter folders under `workspaces/pipeline/<bookname>/chapters/<n>/`, with `model.json`, form-appropriate `mood.json` handling, and canonical `segments/1/` state files following the path invariant enforced by the scaffold agent and its selected layout skill.
7. Leave existing chapters, filters, source output, and human override files unchanged unless the user explicitly asks to regenerate them.
8. Run the requested single `<filter>` only for the newly added chapters. The `*` / `all` bulk form is not accepted — report an error and instruct the user to run each filter separately by name. Do not refresh existing chapters unless the user explicitly asks to refresh the whole book.

## The Form Command

For `/book <bookname> form <formname>`:

Responsibility: change the form of an existing pipeline and reconcile all form-driven settings.

1. Stop if the pipeline does not exist.
2. If `<formname>` matches the current form, report no change needed.
3. Otherwise update the `form` field and re-select everything the form drives: filter chain (8 vs 6), chapter structure (flat prose vs flat poetic prose), word target (5,500+ vs 500–800), stereotype template folder, and source of truth.
4. Re-run the form-dependent selections: **Theme** (re-assign each chapter's theme from `.framework/context/<form>/themes/`), **Syntax** (update each chapter's `syntax` object from `.framework/context/<form>/syntax/`), **Quality** (re-audit against the new form's quality parameters).
5. **Re-seed the override command file for the new form.** The `override` filter is in both chains, so `workspaces/pipeline/<bookname>/filters/override/filter.md` is updated when the form flips. Apply the same rules as the scaffold step (*Override Command File Seeding* in `.framework/agents/scaffold/agent.md`): read `.framework/filters/override/SKILL.md` and reproduce its content customized to the new form — identity and units ("novel pipeline" / every chapter, or "poetry pipeline" / every poem), command-file paths, model-update paths, and instruction scope. Preserve any human-authored `## Instructions` that remain applicable; carry them to the new form's operative instruction file so nothing human-authored is silently dropped:
   - **All forms:** the override command file stays at `workspaces/pipeline/<bookname>/filters/override/filter.md`. There is no pipeline-root `override.md` in any form. Re-render the role/context portion above the `---` line for the new form (identity, units, model-update paths, instruction scope) and preserve any human-authored `## Instructions` in place.
6. Report the change and its consequences.

## The Filter Command

For `/book <bookname> filter <filter> *|all|<n>`:

Responsibility: run exactly one named preparatory filter inside an existing pipeline, against the selected scope — `*`/`all` (every canonical chapter in order) or a single chapter `<n>`. No chapter writing happens here. Each filter must be run separately, by its own name, in chain order.

The filter chain depends on the form. Each filter owns a folder in the pipeline's `filters/` and consumes the output of the filters before it — run them strictly in order, never skipping or reordering.

**Novel (preset: `layout-novel/SKILL.md`)** — routed through the filter agent (`.framework/agents/filter/agent.md`), which invokes each filter's skill under `.framework/filters/`:

| # | Filter | Agent | Produces |
|---|---|---|---|
| 1 | workshop | `.framework/filters/workshop/SKILL.md` | The flat, continuous prose (no section headings) |
| 2 | research | `.framework/filters/research/SKILL.md` | The refined chapter at the target mastery level |
| 3 | seeds | `.framework/filters/seeds/SKILL.md` | `included_characters` and `quality_parameters` |
| 4 | correctness | `.framework/filters/correctness/SKILL.md` | Fact-check results |
| 5 | theme | `.framework/filters/theme/SKILL.md` | Thematic lens and contemporary mapping |
| 6 | syntax | `.framework/filters/syntax/SKILL.md` | Modernized sentence structure |

**Poetry (preset: `layout-poetry/SKILL.md`)** — routed through the filter agent (`.framework/agents/filter/agent.md`), which invokes each filter's skill under `.framework/filters/`:

| Filter | Agent | Produces |
|---|---|---|
| workshop | `.framework/filters/workshop/SKILL.md` | The flat, continuous poem prose (no section headings) |
| research | `.framework/filters/research/SKILL.md` | Research subject |
| correctness | `.framework/filters/correctness/SKILL.md` | Correctness of information |
| theme | `.framework/filters/theme/SKILL.md` | Contemporary theme |
| syntax | `.framework/filters/syntax/SKILL.md` | Contemporary language syntax |
| override | `.framework/filters/override/SKILL.md` | Custom human-authored override instructions |
| quality | `.framework/filters/quality/SKILL.md` | Quality review |

Running a filter (`/book <bookname> filter <filter> *|all|<n>`):

1. Stop if the pipeline does not exist; the user must run `scaffold` first.
2. Route the work through the filter agent at `.framework/agents/filter/agent.md`. The
   agent loads the filter skill from `.framework/filters/<filter>/SKILL.md`, snapshots
   the chapter model into `history/` before any update, runs the named filter, and
   records `state` + a `filter_history` entry in `chapter.json`. Only workshop may
   create `chapters/<n>/chapter.md`, and only when absent; no filter reads or
   overwrites it.
3. Each filter is run separately, by name, in chain order; there is no combined
   full-chain `filter` pass.

## The Enrich Command

For `/book <bookname> enrich <count>|range|*`:

Responsibility: fuse the active filters into one combined agent and run it in a single pass over the selected chapters, recording the fused enrichment guidance in each chapter's `model.json`, ready for write or publish. This work is performed by the enrich agent at `.framework/agents/enrich/agent.md`, but **how it is executed depends on the target scope** (narrow = agentic, bulk = delegated):

- `<count>` — a bare number targets that many chapters starting from chapter 1 (e.g. `enrich 5` → chapters 1–5).
- `range` — a `start-end` range targets those chapters inclusive (e.g. `enrich 3-7` → chapters 3,4,5,6,7).
- `*` (or `all`) — targets every canonical chapter in order.

**Execution route (mode-dependent).** Read the book's `factory` (or an explicit
`offline`/`online` argument) per `.framework/rules/command-boundary.md` before
choosing a route:

- **`online`** (the default): execute **agentically via the enrich agent** for
  **every** target — including `all` and `*`. Never route to Python.
- **`offline`**: **always** resolve the exact command from
  `.framework/offline_registry.md` and run it via Python — for **every** target,
  not just `all`/`*`. The command is
  `python tools/book.py <bookname> enrich [<n>|range|all|continue]`. Display it and
  ask the user to confirm before running it; do not execute Python yourself.

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route the work through the enrich agent at `.framework/agents/enrich/agent.md`. The
   agent reads the active (`autorun: true`) filters from `filters/filters.json`, fuses
   them into one ordered pass over each chapter's `chapter.json` (never `chapter.md`),
   and records `state: "enriched"` + an `enrich` record of the fused filter names.

The enrich command is a single-pass fusion of the active filter chain, not a replacement for the individual `filter` command. It never reads the backlog or the epic.

## The Eval Command

For `/book <bookname> eval all|*|<n>|<range>|continue`:

Responsibility: evaluate whether the pipeline is complete enough to `write` and
`publish`, and report exactly what is missing. This command is **read-only**.

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route the work through the eval agent at `.framework/agents/eval/agent.md`. The
   agent reads the book plan, `progress.json`, `filters/filters.json`, chapter
   models/drafts, and filter outputs, then reports per-chapter write-readiness,
   validation, and publish-readiness. It never mutates anything.
3. Report the readiness table and blockers. Do not run `write` or `publish` from
   this command.

## The Review Command

For `/book <bookname> review *|all|<n>`:

Responsibility: audit chapters against the seed analysis's quality parameters — the
**quality gate** before publish.

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route the work through the review agent at `.framework/agents/review/agent.md`,
   which resolves the form and dispatches to `quality-poetry` or `quality-novel`.
   On pass it records `quality_review` (`status: "passed"`, `sha256`,
   `reviewed_at`, `reviewer`) and sets `state: "completed"`; on fail it reports
   the violations and leaves the chapter unchanged.
3. Report the resolved form, selected skill, scope, and updated chapter models.

## The Humanize Command

For `/book <bookname> humanize *|all|<n>`:

Responsibility: ensure the chapter draft is entirely in the target language
(Bengali), replacing any foreign-language characters with Bengali equivalents. Runs
after quality review and before publish.

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route the work through the humanize agent at `.framework/agents/humanize/agent.md`,
   which verifies a passed `quality_review`, archives the prior draft to
   `history/humanize_<timestamp>.md`, rewrites `chapter.md`, and records
   `humanized: true` + a new `draft.sha256` in the chapter model.
3. Report the chapters processed and the number of foreign characters replaced.

### The human-in-the-loop override filter

`override` is a **custom filter created by the human**, present in both the novel
and poetry chains. The workflow does not generate its instructions; it applies a
human-edited command file.

| Form | Override file | Mediated by |
|---|---|---|
| Novel | `workspaces/pipeline/<bookname>/filters/override/filter.md` | `.framework/filters/override/SKILL.md` |
| Poetry | `workspaces/pipeline/<bookname>/filters/override/filter.md` | `.framework/filters/override/SKILL.md` |

Key points: the override filter runs as a normal chain step; the agent reads the
human-edited `filter.md` (passes through unchanged when missing/empty); scaffold
pre-seeds it from `.framework/filters/override/SKILL.md`; the chapter and poet
agents read the same file and apply its `## Instructions` as the final layer. The
command file must always be present — if missing, re-seed its baseline. The
`quality` filter is also human-in-the-loop, but its role is audit/gatekeeping.

## The Stereotype Selection

Every chapter is rendered in its form's voice. The theme and syntax filters select
from the stereotype templates:

- **Signature** — `.framework/context/<form>/signatures/`
- **Reference** — `.framework/context/<form>/references/`
- **Theme set** — `.framework/context/<form>/themes/`
- **Syntax sample** — `.framework/context/<form>/syntax/`

Read the `registry.md` in each folder to discover options, then the chosen file for
the full definition. Selections must be mutually consistent.

## The Poet Command

For `/book <bookname> poet` (aliases: `poetry`, `poem`):

1. Stop if the pipeline does not exist; use `scaffold` first. Stop if the form is
   not `poetry`.
2. Route through the write agent (`.framework/agents/write/agent.md`) to produce a
   single finished poem from the override command file, in the configured voice and
   language. Write the result to `workspaces/published/<bookname>/<version>/poem.md` (or
   `poems/override.md` if present); do not overwrite a human-edited poem.

## The Poyar Command

For `/book <bookname> poyar <n>|<chapter> [replace]` (alias: `payar`):

1. Stop if the pipeline does not exist; use `scaffold` first. Stop if the form is
   not `poetry`.
2. Resolve the **poyar style cache** at `workspaces/pipeline/<bookname>/style.md`.
   Poyar's default style is `poyar`, grounded from
   `.framework/context/poetry/styles/poyar/{sample.txt,signature.md,style.md}`:
   - **Reuse** when the file's `<!-- style-provenance -->` block declares
     `style: poyar` for this book — never regenerate per chapter.
   - **Synthesize** when it is missing, grounded to another style (e.g. a Srijato
     "Refrain + Verses" reference at 6–12 syllables), stale against
     `book.json` → `updated_at`, or names another book.
   - **Honor** `human_edited: true`; never revert it.
   A style grounded to a different form contradicts the couplet contract and must
   not be composed against.
3. Route through the poyar agent (`.framework/agents/poyar/agent.md`) →
   `.framework/skills/poyar/SKILL.md`. That skill owns the couplet contract:
   exactly 14 syllables per line in the `4 + 4 + 4 + 2` measure, strong L1~L2
   rhyme inside each couplet, no cross-couplet rhyme, daily-used spoken register,
   and continuous flow between couplets. The couplet count derives from the
   chapter's `word_target`.
4. **Never** satisfy a poyar request with `.framework/skills/poetry/SKILL.md`. That
   skill writes continuous poetic prose and cannot meet the couplet contract.
5. The agent writes `chapters/<n>/chapter.md` (archiving the prior copy to
   `segments/1/version/`), records the form evidence in `chapter.json`, and must
   report `=== PASS ===` from
   `python tools/mcpbangla/verse.py audit <file> --form poyar`.

## The Style Command

For `/book <bookname> style [<style>]`:

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route through the style agent (`.framework/agents/style/agent.md`), which
   resolves `<style>` (default `pijush`) from
   `.framework/context/poetry/styles/<style>/style.md`, transforms
   the current draft (delegating to the enrich agent when no writer-stage draft
   exists), and writes a new writer-stage version. It never modifies chapter-root
   `chapter.md`, writes to `workspaces/published/`, or updates `progress.json`.
3. Report the selected style, chapters transformed, and output version paths.

## The Translate Command

For `/book <bookname> translate <n>|all|continue <language>`:

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route through the translate agent (`.framework/agents/translate/agent.md`), which
   reads the validated current draft at `chapters/<n>/chapter.md` and writes the
   derivative to `segments/1/translator/<language>.md` (archiving any prior
   translation). It never modifies `chapter.md`, `workspaces/published/`, or `progress.json`.
3. Report the translated chapter(s) and output paths.
## Mandatory Draft Version Before Overwrite

See `.framework/rules/draft-versioning.md` for the full contract. Every write agent,
poet agent, and any delegated skill or helper that replaces an existing `chapter.md`
must archive the prior bytes to `segments/<x>/version/chapter_v<k>.md` and verify
byte-for-byte equality **before** overwriting the live draft. These are pipeline
draft versions, separate from reader-facing `workspaces/published/` versions.

## Source Versioning

See `.framework/rules/source-versioning.md` for the full contract. Reader-facing
output is always versioned under `workspaces/published/<bookname>/<version>/`; the next
version is one greater than the highest existing numeric folder (`1` when none).
Existing versions are immutable snapshots.
## The Write Command

For `/book <bookname> write <n>|range|all|continue [<style>]` (aliases: `chapter`,
`story`):

Responsibility: turn the chapter model and filter outputs into a finished,
reader-facing chapter, and update progress.

Execution route (mode-dependent). Read the book's `factory` (or an explicit
`offline`/`online` argument) per `.framework/rules/command-boundary.md` before
choosing a route:

- **`online`** (the default): execute **agentically via the write agent** for
  **every** target — including `all` and `*`. Never route to Python, never run
  `python tools/book.py ... write`.
- **`offline`**: **always** resolve the exact command from
  `.framework/offline_registry.md` and run it via Python — for **every** target,
  not just `all`/`*`. The command is
  `python tools/book.py <bookname> write [<n>|range|all|continue] [--style NICK]`.
  Display it and ask the user to confirm before running it; do not execute
  Python yourself until the user confirms.

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Run the **four-task sequence** below. Each task is gated: it runs only when its
   precondition is not already satisfied.
3. Update `progress.json` after each completed chapter. Do not run filter agents
   here.

### The Four-Task Sequence

`write` owns the whole composition path. There is no separate `transform` or
`compose` command — both are stages **inside** `write`.

| # | Task | Gate | Owning agent / skill |
|---|------|------|----------------------|
| 1 | **Enrich** | only if the chapter is not yet enriched | `.framework/agents/enrich/agent.md` → `enrich-poetry` |
| 2 | **Draft** | only if `chapter.md` is absent or empty | `.framework/agents/write/agent.md` → `poetry` / `novel` |
| 3 | **Transform** | always — reshape the draft to the target meter | `.framework/agents/line/agent.md` |
| 4 | **Compose** | only for a requested fixed form | the form agent → its form skill |

#### Task 1 — Enrich (gated)

Read `chapters/<n>/chapter.json`. If it already carries enrichment guidance (the
enrich agent's fused-filter record), skip. Otherwise route through
`.framework/agents/enrich/agent.md`, which applies
`.framework/skills/enrich-poetry/SKILL.md` to fuse the active
`filters/filters.json` filters into one pass and records the guidance in the
chapter model. Enrich writes guidance only — never `chapter.md`.

#### Task 2 — Draft (gated)

Check `chapters/<n>/chapter.md`. If it exists with content, skip. Otherwise route
through `.framework/agents/write/agent.md`, which resolves the form and dispatches
to `.framework/skills/poetry/SKILL.md` (or `novel`), producing the flat
poetic-prose draft. This draft is the **source content** that tasks 3–4 reshape —
it is not the final composed form.

#### Task 3 — Transform (always)

Reshape the draft to the target meter, preserving meaning. The meter unit and
target are **form-specific**:

| Form | Meter unit | Target | Ruler |
|---|---|---|---|
| sonnet | akshar (consonant) | 14/line, 8+6 caesura | `word.akshar-count` |
| limerick, haiku | akshar (consonant) | form pattern (haiku 5-7-5) | `word.akshar-count` |
| **poyar** | **syllable** | **exactly 14/line**, `4 + 4 + 4 + 2` | `word.syllable-count` (summed per word) |
| lyrics / modern song, srijato | syllable | syllable signature | `word.syllable-count` |

**Poyar is a syllable form** — every line holds exactly 14 syllables in the
`4 + 4 + 4 + 2` measure (a `+1` close is legal, 2 preferred). A 13- or
15-syllable line must be rewritten. Never measure poyar by akshar, and never call
`word.syllable-count` on a whole line (it over-counts phrases) — sum the words.

**Poyar also demands a strong rhyme.** `word.rhyme-test >= 1` only proves the two
end words sit in one rhyme class; the pair is still weak when the codas differ
(`শব্দ/গন্ধ` returns `1` and is weak). Require an identical final rhyme unit, and
when line 2 cannot reach one, rework line 1 — shuffle or replace it — rather than
accept the weak pair. `tools/mcpbangla/verse.py rhyme A B` exits non-zero for a
weak pair.

**Poyar composition is owned by its own skill.** Task 3 only calibrates an existing
draft to the meter; the poyar form itself is authored under
`.framework/skills/poyar/SKILL.md` (dispatched via `.framework/agents/poyar/agent.md`),
which owns the couplet contract, the strong-rhyme protocol, the flow rule, and the
`word_target`-derived couplet count. Do not use the generic `poetry` skill to
produce poyar content.

Route through `.framework/agents/line/agent.md`. For each line:

1. Measure with the form's ruler via MCP (`tools/mcpbangla/kamolika.py`).
2. If the count matches the target, record `calibrated`.
3. If under, expand with semantically compatible words until it matches.
4. If over, remove the least essential modifiers until it matches.
5. If no exact match is reachable, record `underflow`/`overflow` and flag for
   review.

**Never compute akshar or syllable counts natively.** Bengali consonant clusters
(যুক্তব্যঞ্জন) make visual counting invalid; every count must come from MCP.

For rhyme-schemed forms (srijato, poyar, lyrics, sonnet), task 3 also verifies the rhyme:
`word.rhyme-test` must return `>= 1` for every required pair. A `0` is **not** a
rhyme (same vowel shape, different class) and must be rejected.

#### Task 4 — Compose (fixed forms only)

When a fixed form is requested, author the finished content in that form — not
merely a reshaped copy of the draft, but new poetry written to the form's contract
from the enriched model and the chapter's thematic core. Route through the
form-specific agent and skill:

| Desired form | Command | Agent | Skill |
|---|---|---|---|
| Bengali sonnet (14 lines, 8+6 caesura, volta at 9) | `line` / `rhyme` | `.framework/agents/line/agent.md`, `.framework/agents/rhyme/agent.md` | `.framework/skills/sonnet/SKILL.md` |
| lyrics / modern song (refrain + verses, syllable signature) | `lyrics` | `.framework/agents/lyrics/agent.md` | `.framework/skills/lyrics/SKILL.md` |
| Limerick (5-line AABBA) | `limerick` | `.framework/agents/limerick/agent.md` | `.framework/skills/limerick/SKILL.md` |
| Haiku (5-7-5 akshars) | `haiku` | `.framework/agents/haiku/agent.md` | `.framework/skills/haiku/SKILL.md` |
| **Poyar (14-syllable couplets)** | `poyar` / `payar` | `.framework/agents/poyar/agent.md` | `.framework/skills/poyar/SKILL.md` |

**Poyar is a fixed form with a dedicated skill.** Never compose it through
`.framework/skills/poetry/SKILL.md` — that skill writes continuous poetic prose
and cannot satisfy the couplet contract (exactly 14 syllables per line, strong
L1~L2 rhyme, no cross-couplet rhyme). `poyar` is also a style-directory name under
`.framework/context/poetry/styles/poyar/`; when that name is invoked, treat it as
this form and route here. Its default style is `poyar`, grounded from
`.framework/context/poetry/styles/poyar/` and **cached per book** at
`workspaces/pipeline/<bookname>/style.md` with a `<!-- style-provenance -->` block:
reuse that cache, synthesize it only on a miss, and never compose against a
reference grounded to another form.

Rhyme schemes are style-level. The default scheme is `ACBD`, resolved per stanza
as **L1 rhymes L3, L2 rhymes L4** — not a vertical map across stanzas. Verify each
stanza with two `word.rhyme-test` calls plus one negative check (`L1` must *not*
rhyme `L2`, or the scheme has collapsed into `AABB`).

#### Output and Record

Every task writes to `chapters/<n>/chapter.md` only, archiving any prior copy to
`chapters/<n>/history/` per `.framework/rules/draft-versioning.md`. The chapter
model records:

```json
{
  "form_skill": "<sonnet|lyrics|limerick|haiku|poyar|srijato>",
  "form": "poem",
  "rhyme_scheme": "ACBD",
  "syllable_counts": [7, 7, 7, 7],
  "calibration_method": "agent_composed_mcp_verified",
  "mcp_verification": { "all_rhymes_verified": true, "syllable_delta": 0 }
}
```

Reader-facing output is versioned per `.framework/rules/source-versioning.md`.
Nothing is promoted to `workspaces/published/` by `write` alone.

### Sonnet Mode

The `sonnet` form is a specialisation of task 3 + task 4 and is fixed at:

- exactly **14 lines**
- exactly **14 akshars** per line
- each line split **8 + 6** at a word boundary (caesura)
- the thematic turn (volta) at line 9

A Bengali sonnet counts **akshars**, not syllables:

| Property | English sonnet | Bengali sonnet |
|---|---|---|
| Meter unit | syllable | akshar (consonant) |
| Line length | 10 syllables | **14 akshars** |
| Internal break | none enforced | **8 + 6 caesura** |
| Total lines | 14 | **14** |

Line-count normalisation comes first: if the source has more than 14 lines keep
lines 1–8 plus the last 6 (preserving the volta and closing couplet); if fewer,
append thematically consistent lines marked `generated`.

Calibration uses the shared wrappers in `tools/mcpbangla/sonnet_utils.py`:

```python
import sys; sys.path.insert(0, "tools/mcpbangla")
from sonnet_utils import akshar_count, calibrate_line

count = akshar_count(line)              # MCP call — never native
status, detail = calibrate_line(line)   # calibrated | underflow | overflow
```

The full 48-candidate delete/insert/replace algorithm, caesura pattern table, and
volta handling live in `.framework/agents/line/agent.md` (**Sonnet Mode**) and
`.framework/skills/sonnet/SKILL.md`. Rhyme selection for a sonnet is owned by
`.framework/agents/rhyme/agent.md`.

### Write Error Handling

| Condition | Response |
|---|---|
| Pipeline doesn't exist | stop: use `scaffold` first |
| Book form is not poetry for a fixed form | stop: "`<form>` requires `form: poetry`" |
| Chapter has no draft and cannot be drafted | stop: chapter `<n>` has no source; run `enrich`/`write` first |
| MCP endpoint unreachable | stop: confirm Book.Backend is running and `BASE_URL` in `tools/mcpbangla/kamolika.py` is correct |
| Count cannot reach target | record `underflow`/`overflow`, report the delta, continue |
| Rhyme test returns `0` or `-1` | rewrite the line — `0` is not a rhyme |
| `sonnet_utils.py` missing | stop: ensure `tools/mcpbangla/sonnet_utils.py` is present |

### Write Next Steps

After every `write` run, report next steps per `.framework/rules/next-steps.md`:

- all chapters composed → `/book <bookname> review all`, then `publish`
- some chapters need review → `/book <bookname> review all`, then re-`write`
- meter target needs adjustment → adjust the book/chapter target, then re-`write`
- MCP errors → resolve the endpoint, then re-`write`
- general → `/book <bookname> eval all` to check completeness before publish

### Write Examples

```bash
/book durga write 1                    # default style, four-task sequence
/book durga write all online           # every chapter, agentic
/book durga write 6 poyar              # fixed-form compose (couplets)
/book durga write 4 srijato            # rhyme-schemed poem
/book wife write 5 --style desh        # explicit style
```

## The Publish Command

For `/book <bookname> publish [<language>]`:

> **Delegate to the repository CLI (display, don't execute).** Publish is a
> structural, repeatable operation resolved as `python tools/book.py <bookname>
> publish [language]`. In `offline` mode, **do not run Python yourself** — resolve
> the exact command, display it to the user, and ask whether to proceed; run it only
> after the user confirms.

1. Stop if the pipeline does not exist; use `scaffold` first.
2. Route through the publish agent (`.framework/agents/publish/agent.md`), passing
   the book name and optional `<language>`. The agent owns version allocation,
   writer-stage or translator-stage promotion, `book.md` assembly, and the
   `progress.json` update — see its `## Online (Agentic) Publish` section for the
   full step contract. It is read-only on pipeline content; it writes only to
   `workspaces/published/` and to the pipeline `progress.json` (including its audit
   fields).
3. The agent may apply the optional **framework health gate** — when
   `publish_gate_framework_health: true` is set in `book.json`, a judge score of
   49 or below (`Broken`/`Inoperable`) refuses the publish. Disabled by default.

## Writing the Chapters

Chapter writing is owned by the write agent (`.framework/agents/write/agent.md`),
which dispatches to the novel/poetry skill. The shared writing bar — form shape,
file mapping, writing rules, language and style — lives in the write agent's
**Writing Guidance** section; the novel skill (`.framework/skills/novel/SKILL.md`)
owns the novel-specific storytelling techniques, the first-chapter rule, and the
book-assembly contract (assembly itself is the publish agent's job).

## Workspace References

| Art | Path |
|---|---|
| Storyline (novel source of truth) | `workspaces/backlog/<bookname>/storyline.md` |
| Book plan & gist (`gist`, `epic_path`, `form` fields) | `workspaces/pipeline/<bookname>/book.json` |
| Poetry topic index | `workspaces/pipeline/<bookname>/book.json` (`chapters[].chapter_title`) |
| Workshop narratives (novel source) | `workspaces/pipeline/<bookname>/filters/workshop/` |
| Chapter seeds (novel characters & quality) | `workspaces/pipeline/<bookname>/filters/seeds/` |
| Per-chapter research | `workspaces/pipeline/<bookname>/filters/research/` (novel), `filters/research/` (poetry) |
| Character list (novel) | `workspaces/pipeline/<bookname>/characters.json` |
| Finished chapters | `workspaces/published/<bookname>/<version>/chapters/` |
| Consolidated book | `workspaces/published/<bookname>/<version>/book.md` |








