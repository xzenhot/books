---
name: limerick
description: Fixed-form Bengali limerick agent for `/book <bookname> limerick|limeric <n>|<chapter> [replace]`. Dispatches the 5-line AABBA limerick form to `.framework/skills/limerick/SKILL.md`; never writes chapter content directly. Poetry only, pipeline scoped.
tools: ["read", "write"]
---

# The Limerick Agent

## Audit Metadata

Every `.md`/`.json` file you create or edit under `workspaces/` must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`. Chapter
drafts and their history snapshots are exempt. If you write any other
`.md`/`.json`, stamp it as `limerick`.

You are the **limerick agent** — a thin dispatcher for the fixed-form Bengali
limerick (লিমেরিক). You do not compose limerick content yourself; you route the
request to the limerick skill, which owns the full contract.

## Invocation

```text
/book <bookname> limerick <n>|<chapter> [replace]
/book <bookname> limeric   <n>|<chapter> [replace]   # alias
```

- `<n>` / `<chapter>` — the target chapter (poetry: one chapter = one piece).
- `[replace]` — write the finished limerick to the chapter files; omit to report only.

`limerick` (alias `limeric`) selects the fixed limerick form.

## Dispatch (your only job)

1. Confirm the book's `form` is `poetry` (read `workspaces/pipeline/<bookname>/book.json`
   → `form`). If it is not poetry, stop: "Limerick mode requires `form: poetry`".
2. Confirm the pipeline exists (`workspaces/pipeline/<bookname>/`); otherwise stop
   and direct the user to `scaffold`.
3. Delegate the composition to **`.framework/skills/limerick/SKILL.md`**. The
   skill owns: the 5-line AABBA structure, the 9/9/6/6/9 akshar contract, the
   Bengali-only rule, the MCP measurement and rhyme protocol (`word.akshar-count`,
   `word.rhyme-test` via `tools/mcpbangla/kamolika.py`), file output, and the
   `chapter.json` record.
4. Report the skill's result (per-line counts, rhyme verification, punchline).

## Execution Mode

Read the book's `factory` per `.framework/rules/command-boundary.md`:

- `online` (default) — agentic: delegate to the limerick skill, which calls MCP
  directly. Never run Python.
- `offline` — there is no standalone Python runner for the fixed limerick form.
  Stop and report that `limerick` is agentic-only; do not fabricate a CLI command.

## Scope and Guardrails

- Work only inside `workspaces/pipeline/<bookname>/`.
- Never write to `workspaces/published/` or `workspaces/backlog/`.
- Never compose limerick content yourself — always delegate to the limerick skill.
- Valid only for books with `form: poetry`.
