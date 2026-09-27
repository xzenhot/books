---
name: layout
description: "Compatibility dispatcher for layout scaffolding. Prefer layout-novel for novel pipelines and layout-poetry for poetry pipelines. Use this only when an older workflow still names .framework/skills/layout/SKILL.md."
---

# Layout Dispatcher

This skill is a compatibility shim. The top-level writer agent should orchestrate layout by form and call the specific layout skill directly:

- Novel: `.framework/skills/layout-novel/SKILL.md`
- Poetry: `.framework/skills/layout-poetry/SKILL.md`

## Source Of Truth

This dispatcher must route to the form-specific skill and stop there. Do not inspect existing book pipelines such as `.space/pipeline/book_wife/` to infer scaffold conventions.

## Dispatch Rule

1. Determine the book form from the `/book` command, `--form`, existing pipeline `model.json`, or the backlog epic/config.
2. If the form is `novel`, stop reading this file and follow `.framework/skills/layout-novel/SKILL.md`.
3. If the form is `poetry`, stop reading this file and follow `.framework/skills/layout-poetry/SKILL.md`.
4. If the form cannot be determined, infer conservatively: a narrative premise is `novel`; a topic/term list is `poetry`.
5. Record the chosen form in the pipeline root `model.json` during scaffolding.

Do not implement scaffold details here. This file exists only so older references to `.framework/skills/layout/SKILL.md` still route to the form-specific layout skills.

