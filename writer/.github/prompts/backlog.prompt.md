---
description: "Run the backlog-creation workflow (Phase 0–1). Reads .framework/workflows/backlog.md and executes the bare bookname command and the init/backlog/layout command inside .space/backlog/<bookname>/."
agent: "agent"
argument-hint: "<bookname> [init|backlog|layout] [<gist>] [<count>] [form] [refresh]"
---

Read `.framework/workflows/backlog.md` in full and execute it as the authoritative spec for backlog creation (Phase 0–1).

This workflow owns:

- The bare `/book <bookname> [<gist>] [form] [refresh]` command — create/update the backlog epic and its seed gist.
- The `/book <bookname> init|backlog|layout [<gist>] [<count>] [form] [refresh]` command — configure the backlog book plan and derive the ordered filter chain.
- `/book <bookname> init idea` — rewrite the gist with AI assistance.

Operate only inside `.space/backlog/<bookname>/`. Never scaffold a pipeline or write finished chapters — those belong to `.framework/workflows/pipeline.md`.

Follow the command-boundary and next-steps rules as that workflow directs, and append the **Next Steps** section after every command.
