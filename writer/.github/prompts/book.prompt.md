---
description: Interpret and execute a /book literary workflow command
---

You are the runtime for the `/book` literary workflow in this repository.

## Steer from the root contract first

1. Read `#file:AGENTS.md` — the root steering document. It defines the command
   surface, parameter parsing, data/output path map, and operating procedure.
2. Then read the matching start-point spec:
   - `.framework/workflows/backlog.md` for backlog creation (bare bookname, `init|backlog|layout`)
   - `.framework/workflows/pipeline.md` for scaffold onward (filters, write, style, translate, publish)

## Interpret the arguments

Treat `$ARGUMENTS` (everything the user typed after `/book`) as a command parsed
left-to-right. Classify into: target book, unit/chapter/segment, signature/persona,
stage/role, and flags (gist, count, form, refresh, language, style).

Do not invent alternate slash commands. Do not treat subcommand keywords as book
names, chapter names, filters, or prose.

## Execute

For executable lifecycle verbs (`init`, `scaffold`, `enrich`, `write`, `publish`),
you may delegate to the repository CLI rather than re-implementing it:

```text
python .tools/book.py <bookname> <verb> [options...]
```

`book.py` already implements init/build/layout, scaffold, enrich, write, and publish.
For anything structural or repeatable, reuse an existing `.tools/` script; do not
create new scripts inside `.space/pipeline/<bookname>/`.

## Report

After executing, report what changed, what was validated, and what remains pending,
following the `next-steps` rule in `.framework/rules/next-steps.md`.
