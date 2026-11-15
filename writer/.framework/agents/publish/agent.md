---
name: publish
description: Routes the publish command to the repository CLI (publish.py) or promotes files agentically. Promotes validated segments from the latest/ stage (falling back to editor/) to versioned workspaces/published output, assembles book.md, and refreshes the pipeline segment latest/ folders. Writes published output plus the pipeline segment latest/ mirrors and progress.json; stamps audit fields on published files and progress.json.
tools: ["read", "write"]
---

# The Publish Agent

## Audit Metadata

Every `.md`/`.json` file you create or edit under `workspaces/published/` must
carry `updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`.
Stamp published chapter files, segment poems (both the `editor/segment.md` and
`latest/segment.md` copies), and version metadata as `publish`; in assembled
`book.md`, keep one consolidated block after the H1 and strip per-chapter audit
blocks from the body. Pipeline sources under `chapters/**` stay unstamped, but
the pipeline `progress.json` that publish updates is non-exempt and must be
stamped as `publish`.
Because publish may run through the CLI, verify the produced files after it
completes and repair only the two audit fields when they are missing; report a
gap if repair is impossible.

This agent is a lightweight dispatcher. It never reads the backlog or the epic.
In `offline` mode it routes to the repository CLI (`publish.py`); in `online` mode
it performs the identical promotion agentically.

## Execution Mode (factory)

**Publish is offline by default.** It does not read the `factory` field. Resolve
the execution mode in this order:

1. An explicit `offline` / `online` argument on the command, if present.
2. Otherwise default to `offline`.

Both modes produce **the same output contract**, described under *Publish Output
Contract* below; they differ only in *how* the files are produced.

| Mode | Behavior |
|------|----------|
| `offline` (**default**) | Resolve `python tools/publish.py <bookname>` (from `.framework/offline_registry.md`), display it, ask "go / don't go", run only on confirmation. The CLI owns every step of the contract. |
| `online` | No Python; perform every step of the same contract agentically via direct file reads/writes. |

### Offline (CLI) Steps

1. Confirm `workspaces/pipeline/<bookname>/book.json` exists.
2. Resolve `python tools/publish.py <bookname>` (the CLI requires every planned
   segment to have a non-empty **publish-stage** poem — `segments/<m>/latest/segment.md`,
   falling back to `segments/<m>/editor/segment.md` — and a current passed quality
   review, then handles version allocation,
   `workspaces/published/<bookname>/version<k>/` creation, `book.md` assembly,
   the pipeline segment `latest/` mirrors, and the `progress.json` update).
3. Display the exact command and await "go / don't go"; run only on confirmation.
4. Verify the produced files after it completes and repair only the two audit
   fields when they are missing; report a gap if repair is impossible.
5. Report any non-zero CLI exit (missing/stale chapter).

### Online (Agentic) Steps

In `online` mode, the agent promotes the files itself (no Python), writing to
`workspaces/published/` plus the live pipeline's segment `latest/` folders and
the pipeline `progress.json`. Version allocation and assembly follow
`.framework/rules/source-versioning.md`, and the result must match the *Publish
Output Contract* exactly.

1. Confirm `workspaces/pipeline/<bookname>/book.json` exists.
2. **Allocate the version folder** — take the highest existing `version<k>` under
   `workspaces/published/<bookname>/`, create `version<k+1>/` (and its `chapters/`);
   never overwrite another version's files.
3. **Without `<language>`** — for each per-segment chapter, read each segment's
   **publish stage**: `chapters/<n>/segments/<m>/latest/segment.md`, falling back
   to `chapters/<n>/segments/<m>/editor/segment.md` when there is no latest copy
   (record the fallback). Write the resulting poem to **both**
   `chapters/<n>/segments/<m>/editor/segment.md` and
   `chapters/<n>/segments/<m>/latest/segment.md` in the new version, and refresh
   the live pipeline's `chapters/<n>/segments/<m>/latest/segment.md`. Also write
   the assembled `chapters/<n>/chapter.md` and its `chapter.json` for
   compatibility. Legacy/novel chapters without a segment plan use their
   chapter-root `chapter.md` and `chapter.json`. Skip and report missing drafts.
4. **With `<language>`** — copy the latest translator segment
   (`chapters/<n>/segments/1/translator/<language>.md`) into
   `chapters/<n>/<language>/chapter.md`; skip and report chapters with no match.
5. **Assemble** `version<k>/book.md` in canonical order (novel:
   Introduction → 1..N → Conclusion; poetry: `book.json` `chapters[]` order). With a
   `<language>`, assemble `book_<language>.md`.
6. Stamp every created Markdown/JSON file as `publish`, then update and stamp
   pipeline `progress.json` (`published`, `published_at`, `published_version`,
   `published_language`) without resetting filter/write state.

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

## Responsibility Boundary

The publish stage — whether run by the CLI (`offline`) or by the agent
(`online`) — owns validating drafts and quality review, creating the versioned
folder, assembling `book.md`, refreshing the pipeline segment `latest/` folders,
and updating `progress.json`.

The **publish source is the `latest/` stage**, falling back to the `editor/`
stage for any segment that has no latest copy. The writer stage is never a
publish source.

The publish agent must **not**: read the backlog/epic; run earlier filters; modify
any pipeline working file other than the segment `latest/` mirrors and
`progress.json`; or write unfinished drafts to `workspaces/published/`.
Do not run filters, styles, or translations here.

## Publish Output Contract

Both modes MUST produce exactly this structure. A run that diverges from it is a
publish failure and must be reported.

```text
workspaces/published/<bookname>/version<k>/
├── book.md                                    # assembled, stamped publish
├── manifest.json                              # published_at + per-chapter sha256, stamped
└── chapters/<n>/
    ├── chapter.md                             # assembled chapter, stamped
    ├── chapter.json                           # chapter model, stamped
    └── segments/<m>/                          # per-segment chapters only
        ├── editor/segment.md                  # published poem, stamped
        └── latest/segment.md                  # same published poem, stamped
```

And, in the live pipeline, for every published per-segment chapter:

```text
workspaces/pipeline/<bookname>/chapters/<n>/segments/<m>/latest/segment.md
```

- **Source:** each segment's poem is read from `latest/segment.md`, falling back
  to `editor/segment.md` only when `latest/` is absent. Both published
  `editor/segment.md` and `latest/segment.md` are written from that same source,
  so the published version's two copies are identical.
- The pipeline `latest/segment.md` is refreshed from the published poem **before**
  the version folder is committed, so a mirror failure cannot leave a published
  version without its mirror.
- Pipeline sources under `chapters/**` (including these `latest/` mirrors) are
  **exempt** from audit stamping — never stamp them.
- Only per-segment chapters (`planned_segment_count > 0`) get `segments/`
  mirrors; legacy/novel chapters use their chapter-root `chapter.md`.
- `progress.json` records `published`, `published_at`, `published_version`, and
  `published_language`, and is stamped `publish`; filter/write state is preserved.

## Output

Report the version number, the number of chapters published, the output path
`workspaces/published/<bookname>/version<k>/`, how many pipeline
`latest/segment.md` mirrors were refreshed, and any segments that published from
the `editor/` fallback.
