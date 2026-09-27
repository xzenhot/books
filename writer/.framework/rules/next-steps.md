# Next Steps Rule

Every time a `/book` command completes, the runtime must report what changed and then display the most logical next steps for the user. This rule applies to all `/book` subcommands and all forms (novel, poetry).

## What to Show

After finishing the requested work, append a concise **Next Steps** section to the response that contains:

1. **What just happened** — one or two lines summarizing the state change (e.g., "Created backlog epic", "Scaffolded pipeline", "Wrote chapter 3", "Ran syntax filter").
2. **The natural next action** — the single most useful command to run next, based on the command that just completed.
3. **Optional follow-ups** — up to two additional commands that make sense at this point, ordered by usefulness.

## Next-Step Mapping by Command

Use this table to choose the recommended follow-up command. Remember the boundary: backlog commands (1–3) never touch the pipeline, and pipeline commands (4–10) never touch the backlog.

| Completed command | State after completion | Recommended next step | Optional follow-ups |
|---|---|---|---|
| `/book <bookname> [<gist>]` (bare) | Backlog epic created, updated, or rewritten; no pipeline | `/book <bookname> init [preset]` | `/book <bookname> scaffold <gist> count <n>` (after init) |
| `/book <bookname> init [<preset>]` (alias: `backlog`) | Preset selected; filter chain configured; pipeline may or may not exist | If pipeline exists: `/book <bookname> filter all`<br>If pipeline missing: `/book <bookname> scaffold <gist> count <n>` | `/book <bookname> write all` (if pipeline exists and chapters are ready) |
| `/book <bookname> scaffold <gist> count <n>` | Pipeline and chapter structure exist; research not yet run | `/book <bookname> filter all` | `/book <bookname> write all` |
| `/book <bookname> write <target>` | One or more chapters written to `source/books/` or pending | If chapters remain: `/book <bookname> write continue`<br>If all chapters complete: `/book <bookname> filter quality` or final assembly | `/book <bookname> filter <next-filter>` |
| `/book <bookname> write all` | All canonical chapters attempted | `/book <bookname> filter all` | `/book <bookname> filter quality` |
| `/book <bookname> write continue` | Resumed and wrote remaining chapters, or none were pending | If chapters remain pending: `/book <bookname> write continue`<br>If complete: `/book <bookname> filter quality` | `/book <bookname> filter all` |
| `/book <bookname> filter <filter>` | Single filter completed | Next filter in chain: `/book <bookname> filter <next>` | `/book <bookname> filter all` |
| `/book <bookname> filter all` | Full filter chain completed | `/book <bookname> write all` or `/book <bookname> write continue` | `/book <bookname> filter quality` |
| `/book <bookname> filter quality` | Quality gate passed or recorded | `/book <bookname> write all` or final promotion to `source/books/<bookname>/book.md` | Review `source/books/<bookname>/chapters/` |
| `/book <bookname> add <n> filter <filter>` | New chapters added; filter run on new chapters | `/book <bookname> write continue` | `/book <bookname> filter all` |
| `/book <bookname> form <formname>` | Form changed in `model.json` | `/book <bookname> scaffold` (if structure needs rebuilding) | `/book <bookname> config show` |
| `/book <bookname> config [<key> [<value>]]` | Configuration inspected or updated | `/book <bookname> write all` | `/book <bookname> filter all` |
| `/book -o` / `--options` | Read-only list displayed | Choose any book and run its next logical command | `/book <bookname> write continue` |
| `/book -h` / `--help` | Help displayed | Choose a `/book` command to run | — |

## Determining the Next Filter

When recommending a single next filter, look up the current filter chain in `.space/pipeline/<bookname>/filters/filters.json` and suggest the filter with the next higher `order` value after the one just completed. If the completed filter was the last in the chain, recommend the `write all` command instead.

## Format

Present the section as plain Markdown:

```markdown
Next steps:
- Recommended: `/book <bookname> <command>` — short reason
- Optional: `/book <bookname> <command>` — short reason
- Optional: `/book <bookname> <command>` — short reason
```

Keep each reason to one line. Do not invent commands that do not exist in `.framework/workflows/pipeline.md`.
