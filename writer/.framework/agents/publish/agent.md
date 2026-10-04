---
name: publish
description: Routes the publish command to the repository CLI (publish.py). Promotes validated chapter drafts to versioned source/books output and assembles book.md. Read-only on the pipeline; writes only to source/books/.
tools: ["read"]
---

# The Publish Agent

This agent is a lightweight dispatcher that routes the publish command to the repository CLI (`publish.py`). It never reads the backlog or the epic.

## Execution Mode (factory)

> **IMPORTANT — PUBLISH IS OFFLINE BY DEFAULT.** In `offline` mode, **do not execute Python and do not hand-craft the published output.** Resolve the exact `python tools/publish.py <bookname>` command from `.framework/offline_registry.md` (do not re-scan the `tools/` folder), display it to the user, and ask whether to proceed. Only run it after the user says go.

Publish accepts an optional execution-mode argument `[offline|online]`. Resolve it in this order:

1. The explicit `offline` or `online` argument supplied on the command, if present.
2. **Default to `offline`** when no explicit argument is provided.

> **NOTE — THE `factory` FIELD DOES NOT APPLY TO PUBLISH.** Publish (like scaffold) is a structural command and is **always offline by default**, regardless of any `factory` value in the book plan (`workspaces/pipeline/<bookname>/book.json`). Do **not** read the `factory` field to resolve publish's execution mode. Publish runs agentically (`online`) only when an explicit `online` argument is supplied on the command; otherwise it must resolve, display, and await confirmation for the exact `python tools/publish.py <bookname>` command.

| Mode | Behavior |
|------|----------|
| `offline` (**default**) | **Display, don't execute.** Resolve the exact repository Python CLI command (`python tools/publish.py <bookname>`), present it, and ask the user to confirm before running anything. |
| `online` | Do not use Python at all; perform every step agentically through direct file reads/writes. |

**The default is `offline`.** In offline mode: resolve the command → display it → ask "go / don't go" → run only on explicit confirmation. Never run Python silently.

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
- The gate never mutates the pipeline or `source/books/`; it only reads.

## Dispatch

1. Read `workspaces/pipeline/<bookname>/book.json` to confirm the book plan exists.
2. Resolve the publish command as `python tools/publish.py <bookname>` (the CLI handles all validation — every poem must have a non-empty registered draft and a passed quality review — version allocation, `source/books/<bookname>/version<k>/` creation, and `progress.json` update).
3. In `offline` mode, display the resolved command and ask the user to confirm; run it only after the user says go. In `online` mode, perform the promotion agentically.
4. The CLI exits non-zero if any chapter is missing or stale; report the error to the user.

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

## Online (Agentic) Publish

In `online` mode, the agent performs the promotion itself (no Python). Version
allocation and assembly follow `.framework/rules/source-versioning.md`. The
agent is read-only on the pipeline and writes only to `source/books/`.

1. **Allocate the version folder.** Inspect `source/books/<bookname>/` for existing
   `version<k>` child folders, take the highest `<k>`, and create
   `source/books/<bookname>/version<k+1>/` (`version1` when none exist), including
   its `chapters/` subfolder. All output of this invocation goes into that folder;
   never overwrite a different version's files.

### Without `<language>` (writer-stage publish)

2. For each target chapter, read the live working draft from
   `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md`. Chapters whose draft
   is missing are skipped and reported.
3. Copy that content into `source/books/<bookname>/version<k>/chapters/<n>/chapter.md`
   (create the folder on first publish; within this new version overwrite freely —
   other versions remain immutable).
4. Copy the chapter metadata alongside as
   `source/books/<bookname>/version<k>/chapters/<n>/chapter.json`.

### With `<language>` (translator-stage publish)

5. For each target chapter, read the latest translator-stage segment from
   `workspaces/pipeline/<bookname>/chapters/<n>/segments/1/translator/` (the file
   matching the requested language, e.g. `en.md`, `bn.md`, `hi.md`; skip and report
   any chapter with no exact match).
6. Copy that translated segment to
   `source/books/<bookname>/version<k>/chapters/<n>/<language>/chapter.md`.

### Assembly

7. Assemble `source/books/<bookname>/version<k>/book.md` (version root) from the
   published chapters in canonical order (`Introduction`, `1..N`, `Conclusion` for
   novels; `bookseed.txt` order for poetry). When a `<language>` was published,
   assemble the translated book at
   `source/books/<bookname>/version<k>/book_<language>.md`.
8. Update `progress.json` (`published`, `published_at`, `published_version`,
   `published_language`) without resetting filter or write state. Return the
   version folder, published/skipped counts, and assembled book paths.
9. Do not run filters, styles, or translations here. Never mutate files under an
   existing `version<k>` folder other than the newly created one.

## Output

Report the version number, the number of chapters published, and the output path `source/books/<bookname>/version<k>/`.
