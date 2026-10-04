# Command Boundary Rule

The `/book` workflow is strictly divided into **backlog commands** and **pipeline commands**. This boundary must never be crossed.

## Factory (Execution Mode)

Every command must first read the book plan's `factory` attribute, which is the
**single authoritative execution-mode switch** and overrides every other
instruction in this repository (including anything in `workspaces/start.md`,
the workflows, the agents, and the skills).

Resolve it from the correct `book.json` for the command's phase:

- **Backlog commands** read `workspaces/backlog/<bookname>/book.json`.
- **Pipeline commands** read `workspaces/pipeline/<bookname>/book.json`.

**Search order (pipeline commands).** When resolving `factory` for a pipeline
command, search in this order and stop at the first `book.json` that exists:

1. `workspaces/pipeline/<bookname>/book.json` — the pipeline book plan.
2. `workspaces/backlog/<bookname>/book.json` — fall back to the backlog book plan when the pipeline copy is not yet available (e.g. before scaffold).

Read `factory` from whichever `book.json` is found first. If neither exists,
treat `factory` as `"online"` and report that no book plan was found.

The `factory` value governs how every workflow, agent, and skill must run:

| `factory` | Meaning |
|---|---|
| `"offline"` | Use the repository Python CLI (`.tools/*.py`, e.g. `python .tools/book.py …`) for all structural, repeatable operations, exactly as the workflows currently specify. |
| `"online"` | **Do not use Python at all.** No `python .tools/*.py`, no `run_in_terminal` Python invocation, no Python helper scripts — for any workflow, agent, or skill. Perform every step agentically (direct file reads/writes by the agents/skills themselves). |

- If `factory` is `"online"`, every workflow, agent, and skill must carry out its
  work through direct reasoning and file operations, never by shelling out to
  Python. The existing `> **Delegate to the repository CLI.**` notes are
  **suspended** in online mode.
- If `factory` is absent, treat it as `"online"` (the default).
- Read the `factory` value before executing anything, and never cache it across
  commands — re-read the authoritative `book.json` for the phase on every run.

### Per-Invocation Offline Override

In an **online** book, any agent, workflow, or skill may still be invoked with an
explicit **`offline`** parameter. This is a scoped, per-invocation override:

- Only the **execution of that single invocation** runs offline (using the
  repository Python CLI, `.tools/*.py`, exactly as the workflows specify).
- The override must **not change any configuration** — it must not write or
  persist the `factory` value back to any `book.json`, and must not alter
  `workspaces/start.md` or any other config file.
- The user's most common uses of the offline override are structural commands —
  notably `scaffold` and `publish` — which are safe to run offline even though
  the book's standing mode is `online`.
- After the invocation completes, the book's `factory` remains `"online"`
  unchanged; the override is not sticky.

## User Configurations

Before applying this rule, read `workspaces/start.md` — the user-maintained default configuration. It is the single source of truth for user-specific default values (form, chapter count, style, word targets, presets, filter chains, search provider, and any other user overrides). If `workspaces/start.md` declares a value that differs from a default here or elsewhere, the user configuration wins. If no user-specific value is declared, fall back to the framework defaults.

## Backlog commands (1–3)

These commands operate only inside the backlog folder:

```text
workspaces/backlog/<bookname>/
```

They are allowed to create, read, or modify only the backlog files:

- `storyline.md`
- `book.json`
- `gist.md`
- `override.md`
- `override.txt`

The backlog commands are:

| # | Command | Responsibility |
|---|---|---|
| 1 | `/book <bookname>` | Create backlog epic if missing |
| 2 | `/book <bookname> gist [<gist>]` | Create, update, or rewrite backlog epic |
| 3 | `/book <bookname> init [<preset>] [form]` | Select preset and derive filter chain in backlog |

### Invariants

- A backlog command must **never** create, read, or modify any file under `workspaces/pipeline/<bookname>/`.
- A backlog command must **never** create, read, or modify any file under `source/books/<bookname>/`.
- If a pipeline already exists, backlog commands must leave it untouched.
- If `init` produces a filter chain, it must write the result to `workspaces/backlog/<bookname>/book.json` (the `filter_chain` field), not to `workspaces/pipeline/<bookname>/filters/filters.json`.

## Pipeline commands (4–10)

These commands operate only on the pipeline and the final output folder:

```text
workspaces/pipeline/<bookname>/
source/books/<bookname>/
```

The pipeline commands are:

| # | Command | Responsibility |
|---|---|---|
| 4 | `/book <bookname> scaffold count|chapter-count <n> [--form novel|poetry]` | Build pipeline structure only |
| 5 | `/book <bookname> <agentname> <chapter>|<n>|all|continue` | Run a registered agent on pipeline chapters |
| 6 | `/book <bookname> filter <filter> *\|all\|<n>` | Run one filter on all chapters or one chapter |
| 7 | `/book <bookname> form <novel|poetry>` | Change pipeline form |
| 8 | `/book <bookname> config [<key> [<value>]]` | Inspect or modify pipeline configuration |
| 9 | `/book <bookname> add <chapter-count> filter <filter>|*|all` | Add chapters and run filters on them |
| 10 | `/book <bookname> write <n>|all|continue` | Write finished reader-facing chapters |

### Invariants

- A pipeline command must **never** create, modify, or delete `workspaces/backlog/<bookname>/storyline.md` or `workspaces/backlog/<bookname>/book.json`.
- A pipeline command may read the backlog as read-only input (for example, scaffold reads `storyline.md` and `book.json`), but it must never write there.
- If the required pipeline does not exist, a pipeline command must stop and tell the user to run `scaffold` first.

## Sequence rules

1. `init` must complete before `scaffold`.
2. `scaffold` must complete before any agent, filter, form change, chapter command, or add command.
3. `filter all` or equivalent upstream filters should complete before `chapter` commands.
4. `write all` or `write continue` should complete before final promotion to `source/books/<bookname>/book.md`.

## Error messages

If a command violates a boundary, respond with the exact form:

```text
Backlog command `<command>` must not touch the pipeline. Stop.
```

or

```text
Pipeline command `<command>` must not modify the backlog. Stop.
```

If a required prior phase is missing:

```text
<phase> required first. Run: /book <bookname> <required-command>
```

where `<phase>` is one of `init`, `scaffold`, `filters`.
