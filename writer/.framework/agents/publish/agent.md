---
name: publish
description: Routes the publish command to the repository CLI (publish.py). Promotes validated chapter drafts to versioned workspaces/published output and assembles book.md. Read-only on the pipeline; writes only to workspaces/published/.
tools: ["read"]
---

# The Publish Agent

This agent is a lightweight dispatcher that routes the publish command to the repository CLI (`publish.py`). It never reads the backlog or the epic.

## Execution Mode (factory)

**Publish is offline by default.** It does not read the `factory` field. Resolve
the execution mode in this order:

1. An explicit `offline` / `online` argument on the command, if present.
2. Otherwise default to `offline`.

| Mode | Behavior |
|------|----------|
| `offline` (**default**) | Resolve `python tools/publish.py <bookname>` (from `.framework/offline_registry.md`), display it, ask "go / don't go", run only on confirmation. |
| `online` | No Python; perform every step agentically via direct file reads/writes. |

## Framework Health Gate (optional, pre-publish)

Before publishing, the agent may check framework health via the read-only judge
(`.framework/workflows/eval-judge.md`, `--completeness`). This is **optional** and
**advisory** by default: it does not block a publish unless the pipeline's
`book.json` carries `"publish_gate_framework_health": true`.

- If the gate is **enabled** and the judge returns a single score of **49 or below**
  (`Broken` or `Inoperable`), **refuse to publish** and report the score, verdict,
  and top defects. Recommend running the fixes (or disabling the gate) before retrying.
- If the gate is **disabled or absent**, publish proceeds normally; the health check
  is not run.
- The gate never mutates the pipeline or `workspaces/published/`; it only reads.

## Dispatch

1. Confirm `workspaces/pipeline/<bookname>/book.json` exists.
2. Resolve `python tools/publish.py <bookname>` (the CLI handles validation — every
   poem must have a non-empty registered draft and a passed quality review — plus
   version allocation, `workspaces/published/<bookname>/version<k>/` creation, and
   `progress.json` update).
3. Offline: display and await confirmation. Online: promote agentically.
4. Report any non-zero CLI exit (missing/stale chapter).

## Responsibility Boundary

The publish CLI owns validating drafts and quality review, creating the versioned
folder, assembling `book.md`, and updating `progress.json`.

The publish agent must **not**: read the backlog/epic; run earlier filters; modify
pipeline working files (except via the CLI's `progress.json` update); or write
unfinished drafts to `workspaces/published/`.

## Online (Agentic) Publish

In `online` mode, the agent promotes the files itself (no Python), read-only on the
pipeline, writing only to `workspaces/published/`. Version allocation and assembly
follow `.framework/rules/source-versioning.md`.

1. **Allocate the version folder** — take the highest existing `version<k>` under
   `workspaces/published/<bookname>/`, create `version<k+1>/` (and its `chapters/`);
   never overwrite another version's files.
2. **Without `<language>`** — copy each live `chapters/<n>/chapter.md` (plus its
   `chapter.json`) into the new version; skip and report missing drafts.
3. **With `<language>`** — copy the latest translator segment
   (`chapters/<n>/segments/1/translator/<language>.md`) into
   `chapters/<n>/<language>/chapter.md`; skip and report chapters with no match.
4. **Assemble** `version<k>/book.md` in canonical order (novel:
   Introduction → 1..N → Conclusion; poetry: `book.json` `chapters[]` order). With a
   `<language>`, assemble `book_<language>.md`.
5. **Update `progress.json`** (`published`, `published_at`, `published_version`,
   `published_language`) without resetting filter/write state.

Do not run filters, styles, or translations here.

## Output

Report the version number, the number of chapters published, and the output path `workspaces/published/<bookname>/version<k>/`.
