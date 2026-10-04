---
description: "Run the /book command registry. Reads .framework/workflows/book.md and resolves the /book command surface, routing each command to its owning workflow (backlog.md or pipeline.md)."
agent: "agent"
argument-hint: "/book [args...]"
---

Read `.framework/workflows/book.md` in full and execute it as the authoritative `/book` command registry.

This file is the single command surface for `/book`. Follow its "How To Resolve A Command" procedure exactly:

1. Parse the `/book [args...]` arguments left to right, preserving user text unless a workflow normalizes it.
2. Classify the command into its family and owning workflow:
   - Backlog creation (`<bookname>` bare, `init`, `backlog`, `layout`, `init idea`) → `.framework/workflows/backlog.md`
   - Pipeline (`scaffold`, `add`, `filter`, `enrich`, `eval`, `review`, `write`, `chapter`, `story`, `style`, `translate`, `publish`, `form`, `config`, `poet`/`poetry`/`poem`, or a `<filter>`/`<agentname>`) → `.framework/workflows/pipeline.md`
   - Read-only (`-o`/`--options`/`list`, `-h`/`--help`) → `.framework/workflows/pipeline.md`
3. Read the delegated workflow spec and execute its matching section.
4. Append the **Next Steps** section per `.framework/rules/next-steps.md` after every command.

Do not define command behavior of your own — this registry only routes to the two start-point workflows.
