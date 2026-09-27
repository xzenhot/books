# Writer Framework — Release Notes

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Created on** | 2026-09-06 |
| **Created by** | pijush |
| **Last release** | 2026-09-27 |
| **Status** | Active |

---

## Overview

The **Writer Framework** is a multi-agent literary engine that turns a seed idea into a finished, versioned book — poetry or novel — in a configured authorial voice. It grounds every chapter in a reference work and a stereotype (signature, reference, theme set, syntax sample), and drives the whole system through a single slash command:

```text
/book <bookname> ...
```

The framework is split into two layers:

- **`.framework/`** — the engine: workflows, role agents, skills, rules, and templates.
- **`.space/`** and **`source/`** — the data: inputs (backlog, pipeline) and outputs (finished, versioned books).

---

## What's Inside

```
.framework/
├── workflows/       # backlog.md + pipeline.md — the orchestration specs for /book
├── agents/          # role agents (init, scaffold, workshop, research, write, publish, …)
├── skills/          # form-specific skills (layout-*, workshop-*, write-*, …)
├── rules/           # shared rules (filters, next-steps, command-boundary)
├── templates/       # stereotypes (novel/, poetry/), styles/, moods/, subjects/, book.json
└── html/            # agent-flow.svg + index.html (the implementation guide)
```

---

## Release Highlights (v1.0.0)

### Two start-point workflows

- **`workflows/backlog.md`** — Phase 0–1: backlog creation (bare bookname, init/backlog/layout).
- **`workflows/pipeline.md`** — Phase 2 onward: scaffold, filters, write, style, translate, publish.

### Agent-first skill invocation

Skills are never executed directly. Every skill-backed operation routes through a role agent in `.framework/agents/<agent>/agent.md`, which then applies the matching skill.

### Form-aware engine

A book is either **novel** (prose) or **poetry** (verse), declared in `book.json`'s `form` field. The form drives source-of-truth files, filter order, chapter structure, word target, and stereotype templates.

### Ordered filter chain

Every chapter passes through an ordered chain of filters before it is finalized:

- **Novel:** `workshop → research → seeds → correctness → theme → syntax → override → quality`
- **Poetry:** `workshop → research → correctness → theme → syntax → override → quality`

`quality` is the final gate; nothing is promoted to `source/books/` until it passes.

---

## Roles & Components

| Component | Path | Role |
|-----------|------|------|
| Workflows | `.framework/workflows/` | The `/book` command surface (backlog + pipeline specs). |
| Agents | `.framework/agents/` | Role actors: `init`, `scaffold`, `workshop`, `research`, `correctness`, `theme`, `syntax`, `override`, `quality`, `enrich`, `write`, `style`, `translate`, `publish`, and more. |
| Skills | `.framework/skills/` | Form-specific craft: `layout-*`, `workshop-*`, `write-*`, `research`, `correctness`, `theme`, `syntax`, `quality`, `translation`, and grounding skills (`history`, `geography`, `mythology`, `philosophy`, `indian`, `contemporary`). |
| Rules | `.framework/rules/` | Shared rules: `filters.md`, `next-steps.md`, `command-boundary.md`. |
| Templates | `.framework/templates/` | Stereotypes (`novel/`, `poetry/`), styles (`pijush`, `poyar`), moods, subjects, and the `book.json` schema. |

---

## Data & Output Paths

| Path | Role |
|------|------|
| `.space/backlog/<book>/` | The backlog epic — `gist.md`, `epic.md`, `book.json` (the book plan). |
| `.space/pipeline/<book>/` | Working state — `model.json`, `bookseed.txt`, `progress.json`, `filters/`, `chapters/`. |
| `source/books/<book>/<version>/` | Finished, versioned reader-facing output. |

---

## See Also

- `AGENTS.md` — runtime steering contract for autonomous coding agents.
- `GUIDE.md` — the implementation guide for the writer agent.
- `.framework/workflows/pipeline.md` — the full `/book` command specification.
- `.framework/what_i_need.md` — plain-English intent behind the system.
