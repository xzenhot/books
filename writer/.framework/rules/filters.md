# Pipeline Filters (Shared Rule)

This rule applies to **all workflows** (poetry, novel, reframe, guide). Every book pipeline passes its material through a set of **filters** — stages that shape, correct, or constrain the content before it is finalized.

## What a Filter Is

A filter is a gate that answers one question about the material and transforms it accordingly. Material is not complete until it has passed every filter in the chain.

## Filter Chain Registry

Every pipeline keeps its filter order in a registry file at:

```text
.space/pipeline/<bookname>/filters/filters.json
```

The registry maps numbers to filter names, so the order is explicit and easy to remember without mixing numbers into folder names. The default chain is:

```
workshop → research → seeds → correctness → theme → syntax → override → quality
```

```json
{
  "chain": [
    { "order": 1, "name": "workshop",   "folder": "workshop",    "role_file": "workshop/workshop.md" },
    { "order": 2, "name": "research",   "folder": "research",    "role_file": "research/research.md" },
    { "order": 3, "name": "seeds",      "folder": "seeds",       "role_file": "seeds/seeds.md" },
    { "order": 4, "name": "correctness","folder": "correctness", "role_file": "correctness/correctness.md" },
    { "order": 5, "name": "theme",      "folder": "theme",       "role_file": "theme/theme.md" },
    { "order": 6, "name": "syntax",     "folder": "syntax",      "role_file": "syntax/syntax.md" },
    { "order": 7, "name": "override",   "folder": "override",    "role_file": "override/override.md" },
    { "order": 8, "name": "quality",    "folder": "quality",     "role_file": "quality/quality.md" }
  ]
}
```

## Filter Folder Layout

Each filter folder contains exactly these files:

```text
filters/
|-- workshop/
|   |-- workshop.md        # role definition: purpose, inputs, outputs, rules, hand-off
|   |-- filter.md         # command / human-in-the-loop instructions for this run
|   |-- filter-summary.md # summary of what this filter produced across chapters
|   |-- content-input.md  # input snapshot: what this filter consumed (for undo/rollback)
|   `-- content-output.md # consolidated content output from this filter
|-- research/
|   |-- research.md
|   |-- filter.md
|   |-- filter-summary.md
|   |-- content-input.md
|   `-- content-output.md
...
```

| File | Purpose |
|------|---------|
| `<filter>.md` | **Role definition** — purpose, inputs, outputs, rules, and hand-off notes for this filter. |
| `filter.md` | **Run command file** — human instructions or runtime command for this filter pass (especially used by `override`). |
| `filter-summary.md` | **Filter-wide summary** — what was checked, produced, corrected, or decided across all chapters. |
| `content-input.md` | **Input snapshot** — the upstream material this filter consumed (previous filter's output, chapter drafts, context). Written when the filter runs; the record that makes a filter pass undoable. |
| `content-output.md` | **Consolidated output** — the combined content emitted by this filter (e.g., concatenated workshop narratives, merged research notes). |

The exact filters depend on the workflow, but the principle is universal: **each filter owns a named folder in the book's pipeline, and each filter reads from and writes to its own folder.**

## Filter → Folder Mapping

Every filter is backed by a folder in `.space/pipeline/<bookname>/filters/`. The folder is the filter's scratch space — the place where it records what it did, so the pipeline is auditable per filter.

Filter folders are **bare filter names** (no number prefix). The chain order is kept in the registry file, not encoded in folder names. Inside each named folder live the standard files plus the filter-specific role file:

```text
filters/
|-- workshop/
|   |-- workshop.md        # role definition
|   |-- filter.md         # run command / human-in-the-loop file
|   |-- filter-summary.md # summary across chapters
|   |-- content-input.md  # input snapshot (for undo/rollback)
|   `-- content-output.md # consolidated output
|-- research/
|   |-- research.md
|   |-- filter.md
|   |-- filter-summary.md
|   |-- content-input.md
|   `-- content-output.md
...
```

| # | Filter | Folder | Role File | Purpose |
|---|--------|--------|-----------|---------|
| 1 | **Workshop** | `filters/workshop/` | `workshop/workshop.md` | Per-chapter workshop narratives — the flat, continuous prose that becomes the chapter. |
| 2 | **Research** | `filters/research/` | `research/research.md` | Per-chapter research — the subject, era, place, figures, and events the chapter is grounded in. |
| 3 | **Seeds** | `filters/seeds/` | `seeds/seeds.md` | Per-chapter character and quality seeds — who appears and what quality bar to meet. |
| 4 | **Correctness** | `filters/correctness/` | `correctness/correctness.md` | Fact-checking — verify every fact, term, and claim. |
| 5 | **Theme** | `filters/theme/` | `theme/theme.md` | Contemporary theme — map the timeless theme onto a present-day concern. |
| 6 | **Syntax** | `filters/syntax/` | `syntax/syntax.md` | Contemporary syntax — keep the prophetic voice but modernize the sentence structure. |
| 7 | **Override** | `filters/override/` | `override/override.md` | Human-in-the-loop — the human's `filter.md` transformation. |
| 8 | **Quality** | `filters/quality/` | `quality/quality.md` | Quality review — audit against the seed analysis's quality metrics. |

> **Note:** the `filters/<name>/` folders are scaffolded by layout as the filters' scratch space. The content inside them (seeds, research notes, workshop narratives, filter summaries, consolidated outputs) is produced by the later workflow steps that run each filter.

## Filter Role File

Each filter folder contains a markdown file named after the filter it represents (e.g., `workshop.md` inside `workshop/`). This file is the filter's **role definition** and should contain:

1. **Purpose** — what question the filter answers.
2. **Inputs** — which upstream files and folders the filter reads.
3. **Outputs** — what the filter writes into its own folder.
4. **Rules** — constraints, quality bars, and transformation instructions.
5. **Hand-off** — how the next filter should consume this filter's output.

Scaffolding a pipeline creates the folder and the standard files (`filter.md`, `filter-summary.md`, `content-input.md`, `content-output.md`) plus an empty role file. The role file is filled by the filter's agent or skill when the filter runs. When a filter runs, it first writes the upstream material it is about to consume into `content-input.md`, then writes its result to `content-output.md` — so a filter pass can be undone by restoring the input snapshot and the prior chapter state.

> **Convention:** folder names are **bare filter names**. The registry (`filters.json`) records the order; file names inside identify the filter and the standard file type.

## Universal Filter Principles

1. **A filter owns a folder.** Each filter reads from and writes to its own folder in the pipeline.
2. **Snapshot before change.** Before a filter modifies a chapter's working draft (`chapters/<n>/chapter.md`) or any chapter data, it must first copy the current `chapter.md` into its own `content-input.md` (the registry's `input_file`), prepending a header `## <n> <chapter_title> (snapshot before <filter>, <timestamp>)`. No filter may update chapter data before its input snapshot exists — this snapshot is the filter's undo record.
3. **Filters run in order.** The chain is fixed: workshop → research → seeds → correctness → theme → syntax → override → quality (or the workflow's subset).
4. **A filter is a gate.** Material is not complete until it passes every filter.
5. **Filters are auditable.** Each filter records its work in its folder — the input snapshot (`content-input.md`), the result (`content-output.md`), and the summary (`filter-summary.md`) — so the pipeline can be traced and rolled back per filter.
6. **The human-in-the-loop is a filter, not a skill.** The human's `filter.md` inside the `override/` folder is applied as a filter, driven directly by the human-editable file — no skill is created for it.

## Applying the Filters

For each chapter, before marking it complete:

1. **Read the workshop** — the narrated story (or apply the poetry filters).
2. **Read the research** — the grounded subject matter.
3. **Read the seed** — who appears and the quality bar.
4. **Write the chapter** — the finished prose.

A chapter is complete only when every filter in the chain has passed.
