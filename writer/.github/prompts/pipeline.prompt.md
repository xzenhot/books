---
description: "Run the pipeline workflow (Phase 2 onward). Reads .framework/workflows/pipeline.md and executes scaffold, filters, write, style, translate, enrich, review, humanize, publish, form, config, add, and poet."
agent: "agent"
argument-hint: "<bookname> <scaffold|write|chapter|story|style|translate|publish|filter|enrich|review|humanize|form|config|add|poet|...>"
---

Read `.framework/workflows/pipeline.md` in full and execute it as the authoritative spec for everything after the backlog (Phase 2 onward).

This workflow owns:

- `scaffold`, `add`, `filter`, `enrich`, `eval`, `review`, `humanize`
- `write`, `chapter`, `story` (aliases routed through the write agent)
- `style`, `translate`, `publish`, `preview`
- `form`, `config`, `poet`/`poetry`/`poem`

Operate only inside `.space/pipeline/<bookname>/` and `source/books/`. Route every skill-backed operation through an agent (`workflow → agent → skill`); never execute a skill directly.

Follow the command-boundary and next-steps rules as that workflow directs, and append the **Next Steps** section after every command.
