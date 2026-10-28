---
name: backlog
description: Backlog creation and book-plan workflow. Owns the backlog-creation phase of the /book pipeline — the bare bookname command (create/update the backlog epic and its seed gist) and the init/backlog/layout command (configure the backlog book plan and derive the ordered filter chain). Operates only in workspaces/backlog/<bookname>/; never scaffolds a pipeline or writes finished chapters.
---

# The Backlog Workflow (Backlog Creation)

This workflow owns the **backlog-creation phase** of the `/book` pipeline. It handles the commands that build and configure the backlog folder before any pipeline exists:

```text
/book <bookname> init [<gist>] [form] [refresh]          # gist.md only; with refresh: full bootstrap (gist + storyline + book.json)
/book <bookname> layout [<count>] [form]                 # rewrite storyline.md from gist + materials, then derive book.json
/book <bookname> init idea                               # rewrite the gist with AI assistance
```

These are **Phase 0 (Backlog)** and **Phase 1 (Init)** of the overall `/book` workflow. The full `/book` lifecycle lives in `.framework/workflows/pipeline.md`; this file is the authoritative spec for the backlog-creation half of that lifecycle. `scaffold` and everything after it is owned by `pipeline.md`.

## Command Boundary

Every command in this workflow **must pass through** `.framework/rules/command-boundary.md` before executing. That rule is the authoritative boundary contract and applies to all commands, in all workflows, in both forms (novel and poetry).

- Read `.framework/rules/command-boundary.md` first, and treat its backlog/pipeline boundary and sequence rules as binding on every command below.
- This workflow owns **backlog commands only**. It must never cross into `workspaces/pipeline/<bookname>/` or `workspaces/published/`.
- If a command would violate the boundary, stop and respond with the exact error form defined in that rule.

## Next Steps

After **every** command in this workflow completes — including read-only, no-op, and early-stop results — append a **Next Steps** section to the response, following `.framework/rules/next-steps.md`. That rule is mandatory and unconditional; it maps each completed command to its recommended next action and optional follow-ups. Read it and apply it to every response.

## Audit Metadata

Every `.md` or `.json` file this workflow creates or edits under `workspaces/` must carry `updated_by` and `updated_date`, per `.framework/rules/audit-metadata.md`. Read that rule before the first write.

- **Markdown** (`gist.md`, `storyline.md`): a two-bullet block directly after the H1 — `- **updated_by:** <agent>` and `- **updated_date:** <ISO-8601-UTC>` — or inside an existing metadata list after the H1. Migrate legacy `Updated` / `Updated by` bullets to these keys instead of duplicating them.
- **JSON** (`book.json`, `progress.json`): root-level `updated_by` and `updated_date`; keep a legacy `updated_at` in sync.
- **Stamp as:** the owning agent (`init` for backlog files; `layout` for layout-derived files).
- **Exempt:** `_history/` archive snapshots and non-Markdown/non-JSON files.

## Scope Boundary

The backlog workflow operates **only inside the backlog**:

```text
workspaces/backlog/<bookname>/
├── gist.md     # the seed idea — a single-sentence gist plus a short expansion
├── storyline.md     # the full narrative foundation (novel) or thematic grounding (poetry)
├── book.json   # the chapter-layout plan + ordered filter chain (blueprint for scaffold)
└── materials/  # human-authored research materials (created by init; user writes here)
```

It must **never** create, read, or modify:

- `workspaces/pipeline/<bookname>/` (the pipeline is scaffolded later by `pipeline.md`)
- `workspaces/published/` (reader-facing output)
- any filter directory, chapter folder, or `model.json`

The backlog is **metadata**; the pipeline is **execution state**. Commands here produce metadata only.

## Command Reference

| Command | What it does |
|---------|--------------|
| `<bookname> init [<gist>] [form]` | Creates or edits **only `gist.md`** — the seed idea. Does **not** create `storyline.md` or `book.json`. Use `layout` to derive them, or `init ... refresh` to regenerate the full backlog. |
| `<bookname> init ... refresh` | Full bootstrap: regenerates `gist.md`, `storyline.md`, and `book.json` from the premise (grounded in `materials/`). |
| `<bookname> layout [<count>] [form]` | Rewrites `storyline.md` from `gist.md` plus any research materials in `materials/`, then derives `book.json` (the layout). An explicit `<count>` and `form` control the resulting plan. |
| `<bookname> init idea` | Rewrites the book's gist with AI assistance — reads the existing `gist.md` (or the book name if absent), generates a stronger, more dramatically charged one-line premise, and writes it back to `gist.md` (updating its expansion to match). Never touches `storyline.md`, `book.json`, the pipeline, or `workspaces/published/`. |

Every subcommand keyword is literal and unambiguous. `backlog` is a synonym of `init`. `idea` is a subcommand of `init`. `layout` is its own command — not an alias of `init`.

## The Init Command (gist-only by default)

For `/book <bookname> init [<gist>] [<form>] [refresh]`:

Responsibility: create or edit **only `gist.md`** — the seed idea. This is the
gist-only boundary. Without `refresh`, init writes `gist.md` and nothing else; it
never creates or rewrites `storyline.md` or `book.json`. With `refresh`, init
switches to **full bootstrap** (gist + storyline + book.json, grounded in
`materials/`).

1. Route the work through the init agent (`.framework/agents/init/agent.md`), which
   owns the gist-only and refresh paths: resolving the gist, writing `gist.md`
   (single-sentence gist + 2–4 sentence expansion + empty `## Author Comment`), and
   — only with `refresh` — regenerating `storyline.md` and `book.json`.
2. Without `refresh`, report that the user should run `layout` (or `init ... refresh`)
   to derive `storyline.md`/`book.json`.

## The Layout Command

For `/book <bookname> layout [<count>] [<form>]`:

Responsibility: rewrite `storyline.md` from the gist (grounded in `materials/`),
then derive `book.json`. `layout` is its own command, not an alias of `init`.

1. Route the work through the init agent (`.framework/agents/init/agent.md`), which
   owns storyline generation and book-plan derivation, including the
   **Incremental Count Rule** (append-only, never truncate) and the
   **Refresh And Count Contract**. It preserves the original `Created` timestamp
   and updates `updated_by`/`updated_date`.

## The Idea Command

For `/book <bookname> init idea`:

Responsibility: rewrite the book's **gist** with AI assistance — a stronger,
dramatically charged one-line premise (plus matching expansion). Operates only on
`gist.md`.

1. Route the work through the init agent (`.framework/agents/init/agent.md`), which
   owns the **Great Idea** method. It never rewrites `storyline.md` or `book.json`;
   those need re-derivation via a later `init`/`refresh`.
2. Report the old gist, the new gist, and note that `storyline.md`/`book.json` are
   unchanged and will need re-derivation.

## The Three Backlog Artifacts

A fully configured backlog folder contains exactly three files; the init agent owns
their full schemas:

| File | Role |
|------|------|
| `gist.md` | The seed idea — single-sentence gist, short expansion, optional Author Comment. |
| `storyline.md` | The full narrative foundation (novel) or thematic grounding (poetry). |
| `book.json` | The chapter-layout plan + ordered filter chain — blueprint for `scaffold`. |

## Routing and Ownership

- **Gist creation/update** (`init`, `init idea`) and **storyline generation** are
  owned by the init agent (`.framework/agents/init/agent.md`) — see its
  *Gist-Only Path*, *Full Path*, *Refresh Mode*, *The Great Idea*, *Storyline
  Generation*, *Incremental Count Rule*, and *Seeding Research Materials* sections.
- **Storyline + book-plan derivation** (`layout`, `init ... refresh`) is owned by
  the init agent.
- Neither command invokes research, filter, or writing skills. Scaffold and all
  later phases are owned by `.framework/workflows/pipeline.md`.
