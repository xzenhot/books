---
name: publish
description: Routes the publish command to the repository CLI (publish.py). Promotes validated chapter drafts to versioned source/books output and assembles book.md. Read-only on the pipeline; writes only to source/books/.
tools: ["read"]
---

# The Publish Agent

This agent is a lightweight dispatcher that routes the publish command to the repository CLI (`publish.py`). It never reads the backlog or the epic.

## Dispatch

1. Read `.space/pipeline/<bookname>/book.json` to confirm the book plan exists.
2. Route the publish work by invoking `python .tools/publish.py <bookname>` — the CLI handles all validation (every poem must have a non-empty registered draft and a passed quality review), version allocation, `source/books/<bookname>/version<k>/` creation, and `progress.json` update.
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
