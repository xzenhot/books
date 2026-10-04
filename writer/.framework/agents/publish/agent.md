---
name: publish
description: Routes the publish command to the repository CLI (publish.py). Promotes validated chapter drafts to versioned source/books output and assembles book.md. Read-only on the pipeline; writes only to source/books/.
tools: ["read"]
---

# The Publish Agent

This agent is a lightweight dispatcher that routes the publish command to the repository CLI (`publish.py`). It never reads the backlog or the epic.

## Execution Mode (factory)

> **IMPORTANT — PUBLISH IS OFFLINE BY DEFAULT. Do not hand-craft the published output. Delegate publish to the repository Python CLI (`python tools/publish.py <bookname>`) unless the book plan's `factory` field is explicitly `"online"` or an explicit `online` argument is supplied.**

Publish accepts an optional execution-mode argument `[offline|online]`. Resolve it in this order:

1. The explicit `offline` or `online` argument supplied on the command, if present.
2. The `factory` field in the book plan (`workspaces/pipeline/<bookname>/book.json`).
3. **Default to `offline`** when neither is provided.

| Mode | Behavior |
|------|----------|
| `offline` (**default**) | Use the repository Python CLI (`python tools/publish.py <bookname>`) for the structural publish operation. |
| `online` | Do not use Python at all; perform every step agentically through direct file reads/writes. |

**The default is `offline`.** When the `[offline|online]` argument is not provided and no `factory` field resolves the mode, run publish through the repository Python CLI.

## Dispatch

1. Read `workspaces/pipeline/<bookname>/book.json` to confirm the book plan exists.
2. Route the publish work by invoking `python tools/publish.py <bookname>` — the CLI handles all validation (every poem must have a non-empty registered draft and a passed quality review), version allocation, `source/books/<bookname>/version<k>/` creation, and `progress.json` update.
3. The CLI exits non-zero if any chapter is missing or stale; report the error to the user.

## Responsibility Boundary

The publish CLI owns:
- Validating every chapter has a non-empty, registered draft matching the model's `draft.sha256`
- Validating every chapter has `quality_review.status: "passed"` with matching `sha256`, `reviewer`, and `reviewed_at`
- Creating the versioned output folder under `source/books/`
- Assembling `version<k>/book.md` from all chapter drafts
- Updating `progress.json` with published hashes and version

The publish agent must not:
- Read the backlog or the epic;
- Run any earlier filter;
- Modify the pipeline working files (except via the CLI's `progress.json` update);
- Write unfinished drafts to `source/books/`.

## Output

Report the version number, the number of chapters published, and the output path `source/books/<bookname>/version<k>/`.
