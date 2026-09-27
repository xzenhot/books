# Command Boundary Rule

The `/book` workflow is strictly divided into **backlog commands** and **pipeline commands**. This boundary must never be crossed.

## Backlog commands (1–3)

These commands operate only inside the backlog folder:

```text
.space/backlog/epic/<bookname>/
```

They are allowed to create, read, or modify only the backlog files:

- `epic.md`
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

- A backlog command must **never** create, read, or modify any file under `.space/pipeline/<bookname>/`.
- A backlog command must **never** create, read, or modify any file under `source/books/<bookname>/`.
- If a pipeline already exists, backlog commands must leave it untouched.
- If `init` produces a filter chain, it must write the result to `.space/backlog/epic/<bookname>/book.json` (the `filter_chain` field), not to `.space/pipeline/<bookname>/filters/filters.json`.

## Pipeline commands (4–10)

These commands operate only on the pipeline and the final output folder:

```text
.space/pipeline/<bookname>/
source/books/<bookname>/
```

The pipeline commands are:

| # | Command | Responsibility |
|---|---|---|
| 4 | `/book <bookname> scaffold count|chapter-count <n> [--form novel|poetry]` | Build pipeline structure only |
| 5 | `/book <bookname> <agentname> <chapter>|<n>|all|continue` | Run a registered agent on pipeline chapters |
| 6 | `/book <bookname> filter <filter>|*|all` | Run one or all filters inside the pipeline |
| 7 | `/book <bookname> form <novel|poetry>` | Change pipeline form |
| 8 | `/book <bookname> config [<key> [<value>]]` | Inspect or modify pipeline configuration |
| 9 | `/book <bookname> add <chapter-count> filter <filter>|*|all` | Add chapters and run filters on them |
| 10 | `/book <bookname> write <n>|all|continue` | Write finished reader-facing chapters |

### Invariants

- A pipeline command must **never** create, modify, or delete `.space/backlog/epic/<bookname>/epic.md` or `.space/backlog/epic/<bookname>/book.json`.
- A pipeline command may read the backlog as read-only input (for example, scaffold reads `epic.md` and `book.json`), but it must never write there.
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
