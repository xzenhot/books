# Next Steps Rule

Every time a `/book` command completes, the runtime must report what changed and then display the most logical next steps for the user. This rule applies to all `/book` subcommands and all forms (novel, poetry).

This rule is **mandatory and unconditional**: after **every** workflow command in both `.framework/workflows/backlog.md` and `.framework/workflows/pipeline.md`, a **Next Steps** section must be appended to the response. It is not optional, and it is not skipped for read-only commands (`options`/`list`), error stops, or no-op completions.

## What to Show

After finishing the requested work, append a concise **Next Steps** section to the response that contains:

1. **What just happened** — one or two lines summarizing the state change (e.g., "Created backlog epic", "Scaffolded pipeline", "Wrote chapter 3", "Ran syntax filter").
2. **The natural next action** — the single most useful command to run next, based on the command that just completed.
3. **Optional follow-ups** — up to two additional commands that make sense at this point, ordered by usefulness.

If a command stopped early (missing prerequisite, boundary violation, no-op), still show **Next Steps** — the recommended step is the command that resolves the blocker (e.g. `init` before `scaffold`).

## Next-Step Mapping by Command

Use this table to choose the recommended follow-up command. Remember the boundary: backlog commands never touch the pipeline, and pipeline commands never touch the backlog. Commands are listed for both workflows.

### Backlog commands (`.framework/workflows/backlog.md`)

| Completed command | State after completion | Recommended next step | Optional follow-ups |
|---|---|---|---|
| `/book <bookname>` (bare) | Backlog epic created or reported existing; no pipeline | `/book <bookname> init [<preset>] [<count>]` | `/book <bookname> scaffold <gist> count <n>` (after init) |
| `/book <bookname> [<gist>] [form] [refresh]` | Backlog epic + `gist.md` created/updated/rewritten; no pipeline | `/book <bookname> init [<preset>] [<count>]` | `/book <bookname> scaffold <gist> count <n>` (after init) |
| `/book <bookname> init\|backlog\|layout [<gist>] [<count>] [form] [refresh]` | Backlog book plan (`book.json`) + filter chain configured; pipeline may or may not exist | If pipeline exists: `/book <bookname> filter <filter>` or `enrich`<br>If pipeline missing: `/book <bookname> scaffold <gist> count <n>` | `/book <bookname> write all` (if pipeline exists and chapters are ready) |
| `/book <bookname> init idea` | `gist.md` rewritten with AI assistance; epic/plan untouched | `/book <bookname> init [<preset>] [<count>]` | `/book <bookname> scaffold <gist> count <n>` (after init) |

### Pipeline commands (`.framework/workflows/pipeline.md`)

| Completed command | State after completion | Recommended next step | Optional follow-ups |
|---|---|---|---|
| `/book <bookname> scaffold <gist> count\|chapter-count <n> [--form]` | Pipeline + chapter structure exist; filters not yet run | `/book <bookname> enrich *` (or `filter <filter>`) | `/book <bookname> write all` |
| `/book <bookname> <agentname> <chapter>\|<n>\|all\|continue` | One agent ran on selected chapters; no promotion | Next filter/agent in chain, or `/book <bookname> enrich *` | `/book <bookname> write all` |
| `/book <bookname> enrich <count>\|range\|*` | Active filters fused into one pass; guidance recorded in `model.json` | `/book <bookname> write <n>\|all\|continue` | `/book <bookname> filter quality` |
| `/book <bookname> filter <filter>` | Single filter completed | Next filter in chain: `/book <bookname> filter <next>` | `/book <bookname> enrich *` |
| `/book <bookname> write <n>\|range\|all\|continue [<language>]` | One or more finished chapters written | If chapters remain: `/book <bookname> write continue`<br>If all complete: `/book <bookname> filter quality` | `/book <bookname> publish [<language>]` |
| `/book <bookname> style [<style>]` | New writer-stage version created under `segments/1/writer/` | `/book <bookname> write <n>\|all` (to promote) or `/book <bookname> publish` | `/book <bookname> translate <n> <language>` |
| `/book <bookname> translate <n>\|all\|continue <language>` | Translated derivative written to `segments/1/translator/` | `/book <bookname> publish <language>` | `/book <bookname> write continue` |
| `/book <bookname> poet\|poetry\|poem` | A single finished poem produced | `/book <bookname> filter quality` | `/book <bookname> publish` |
| `/book <bookname> filter quality` | Quality gate passed or recorded | `/book <bookname> publish [<language>]` | Review `source/books/<bookname>/chapters/` |
| `/book <bookname> review *|all|<n>` | Quality audit passed; all chapter models have `quality_review` and `state: "completed"` | `/book <bookname> humanize *|all|<n>` | Review `source/books/<bookname>/chapters/` |
| `/book <bookname> humanize *|all|<n>` | Chapter drafts humanized to target language only; all foreign characters replaced | `/book <bookname> publish [<language>]` | Review `source/books/<bookname>/version<k>/` |
| `/book <bookname> add <chapter-count> filter <filter>` | New chapters added; filter run on new chapters | `/book <bookname> write continue` | `/book <bookname> enrich *` |
| `/book <bookname> form <formname>` | Form changed in `model.json` | `/book <bookname> scaffold` (if structure needs rebuilding) | `/book <bookname> config` |
| `/book <bookname> config [<key> [<value>]]` | Configuration inspected or updated | `/book <bookname> write all` | `/book <bookname> enrich *` |
| `/book <bookname> publish [<language>]` | Versioned output promoted to `source/books/<bookname>/version<k>/` | Review `source/books/<bookname>/version<k>/book.md` | Start a new book: `/book <bookname>` |
| `/book -o` / `--options` / `list` | Read-only list displayed | Choose any book and run its next logical command | `/book <bookname> write continue` |
| `/book -h` / `--help` | Help displayed | Choose a `/book` command to run | — |

## Determining the Next Filter

When recommending a single next filter, look up the current filter chain in `.space/pipeline/<bookname>/filters/filters.json` and suggest the filter with the next higher `order` value after the one just completed. If the completed filter was the last in the chain, recommend `write all` (or `publish` if chapters are already written) instead.

## Format

Present the section as plain Markdown:

```markdown
Next steps:
- Recommended: `/book <bookname> <command>` — short reason
- Optional: `/book <bookname> <command>` — short reason
- Optional: `/book <bookname> <command>` — short reason
```

Keep each reason to one line. Do not invent commands that do not exist in `.framework/workflows/backlog.md` or `.framework/workflows/pipeline.md`.
