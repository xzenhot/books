---
name: book
description: The authoritative command registry for the /book surface. Enumerates every command in the /book lifecycle and delegates execution to the two specialized start-point workflows — backlog.md (Phase 0–1) and pipeline.md (Phase 2 onward). Read this file first to resolve which command family a request belongs to and which workflow owns its behavior.
---

# The Book Command Registry

This file is the **single command surface** for `/book`. It lists every supported command, maps each command to its owning workflow, and delegates detailed behavior to the two start-point workflows. It defines **no command behavior of its own** — it only routes.

```text
.framework/workflows/backlog.md   # Phase 0–1: backlog creation (bare bookname, init/backlog/layout)
.framework/workflows/pipeline.md  # Phase 2 onward: scaffold, filters, write, style, translate, publish
```

`backlog.md` is the authoritative spec for backlog creation. `pipeline.md` is the authoritative spec for everything after the backlog. This registry is the index over both.

## How To Resolve A Command

For every `/book [args...]` request, follow this procedure:

1. Parse the arguments left to right, preserving user text exactly unless a workflow normalizes it.
2. Classify the first positional argument:
   - `-o` / `--options` / `list` → **Options** (read-only), delegated to `pipeline.md`.
   - `-h` / `--help` → **Help** (read-only), delegated to `pipeline.md`.
   - A subcommand keyword in the first argument → the matching family below.
   - Otherwise it is `<bookname>`; continue classifying the next argument.
3. Classify the subcommand (second argument when a `<bookname>` leads):
   - `init`, `backlog`, `layout`, `idea`, or a bare `<bookname>` with no subcommand → **backlog.md**.
   - `scaffold`, `add`, `filter`, `enrich`, `eval`, `review`, `write`, `style`, `translate`, `publish`, `form`, `config`, `poet`/`poetry`/`poem`, or a `<filter>`/`<agentname>` → **pipeline.md**.
4. Read the delegated workflow spec and execute its matching section.
5. Append the **Next Steps** section per `.framework/rules/next-steps.md` after **every** command (including read-only, no-op, and error stops).

## Command Families

### Backlog creation — owned by `backlog.md`

```text
/book <bookname> init [<gist>] [form] [refresh]      # gist.md only; refresh → full bootstrap
/book <bookname> layout [<count>] [form]              # rewrite storyline.md from gist + materials, then derive book.json
/book <bookname> init idea
```

### Pipeline — owned by `pipeline.md`

```text
/book <bookname> scaffold <gist> count|chapter-count <number> [--form novel|poetry]
/book <bookname> add <chapter-count> filter <filter>
/book <bookname> filter <filter>
/book <bookname> <agentname> <chapter>|<n>|all|continue
/book <bookname> enrich <count>|range|*
/book <bookname> review *|all|<n>
/book <bookname> eval all|*|<n>|<range>|continue
/book <bookname> write <n>|all|continue [<style>]        # default style: pijush
/book <bookname> style [<style>]
/book <bookname> translate <n>|all|continue <language>
/book <bookname> publish [<language>]
/book <bookname> form <novel|poetry>
/book <bookname> config [<key> [<value>]]
/book <bookname> poet|poetry|poem
```

### Read-only — owned by `pipeline.md`

```text
/book -o | --options | list
/book -h | --help
```

## Command Reference

| Command | Family | Owning workflow | What it does |
|---------|--------|-----------------|--------------|
| `<bookname>` (bare) | Backlog | `backlog.md` | Same as `init` — create/edit `gist.md`. No pipeline. |
| `<bookname> init` / `backlog` | Backlog | `backlog.md` | Create/edit **`gist.md` only** (no `storyline.md`/`book.json`). With `refresh`, full bootstrap: `gist.md` + `storyline.md` + `book.json`, grounded in `materials/`. |
| `<bookname> layout [<count>] [<form>]` | Backlog | `backlog.md` | Rewrite `storyline.md` from `gist.md` + `materials/`, then derive `book.json`. |
| `<bookname> init idea` | Backlog | `backlog.md` | Rewrite the gist with AI assistance. |
| `<bookname> scaffold` | Pipeline | `pipeline.md` | Build/repair the pipeline tree from the backlog book plan. |
| `<bookname> add ... filter` | Pipeline | `pipeline.md` | Add chapters and run one filter on the new chapters. |
| `<bookname> filter` | Pipeline | `pipeline.md` | Run a single named filter in order. |
| `<bookname> <agentname>` | Pipeline | `pipeline.md` | Run a registered agent against selected chapters. |
| `<bookname> enrich` | Pipeline | `pipeline.md` | Fuse active filters into one combined pass. |
| `<bookname> review` | Pipeline | `pipeline.md` | Audit chapters against quality parameters via the review agent; final quality gate before publish. |
| `<bookname> eval` | Pipeline | `pipeline.md` | Evaluate pipeline completeness before write/publish. Read-only. |
| `<bookname> write` | Pipeline | `pipeline.md` | Write finished chapters (story agent for novel, poetry agent for poetry). |
| `<bookname> style` | Pipeline | `pipeline.md` | Transform writer-stage chapters through a style template. |
| `<bookname> translate` | Pipeline | `pipeline.md` | Translate latest writer-stage chapter versions. |
| `<bookname> publish` | Pipeline | `pipeline.md` | Promote segments to `source/books/<bookname>/<version>/` and assemble `book.md`. |
| `<bookname> form` | Pipeline | `pipeline.md` | Set/change the book's form. |
| `<bookname> config` | Pipeline | `pipeline.md` | Get/set book-level config in `model.json`. |
| `<bookname> poet` | Pipeline | `pipeline.md` | Produce a single finished poem (aliases: `poetry`, `poem`). |
| `-o` / `--options` / `list` | Read-only | `pipeline.md` | List books across backlog, pipeline, and `source/books`. |
| `-h` / `--help` | Read-only | `pipeline.md` | Show usage and phase overview. |

## Delegation Rules

- This registry never executes skill-backed work directly. Each owning workflow routes through its agents (`.framework/agents/<agent>/agent.md`), which may then read skills (`.framework/skills/<skill>/SKILL.md`).
- Backlog commands operate only inside `.space/backlog/<bookname>/`. Pipeline commands operate only inside `.space/pipeline/<bookname>/` and `source/books/`.
- Do not invent alternate slash commands. Do not treat subcommand keywords as book names, chapter names, filters, or prose.
- Every command — including read-only ones — must end with the **Next Steps** section per `.framework/rules/next-steps.md`.
