# Audit Metadata (`updated_by` / `updated_date`)

Every framework agent that creates or edits a Markdown (`.md`) or JSON (`.json`)
file under `workspaces/` must stamp it with two audit fields. The fields record
which agent last wrote the file and when, so workspace state can be versioned and
audited.

This rule is additive: it never changes the file's meaning, schema-required
fields, or reader-facing content.

## Scope

Applies to every `.md` and `.json` file an agent writes under:

```text
workspaces/backlog/**
workspaces/pipeline/**        # except chapters, below
workspaces/published/**
workspaces/discovery/**
```

Does **not** apply to:

- `.framework/**` — framework source, not workspace data.
- Non-Markdown, non-JSON files (for example `override.txt`, images, binaries).
- Read-only files. A file the agent only reads is never modified or stamped.

### Exclusions

1. **Pipeline chapters.** Skip the entire chapters tree:

   ```text
   workspaces/pipeline/<bookname>/chapters/**
   ```

   This includes `chapter.md`, `chapter.json`, `mood.json`, segment state,
   translations, and all of their `history/` and `version/` folders.

2. **History and archive snapshots.** Skip every immutable byte-for-byte copy:

   ```text
   **/_history/**
   **/history/**
   **/version/**
   ```

   These snapshots must stay byte-identical to the original for integrity
   checks. Never stamp them.

## The Fields

| Field | Type | Value |
|---|---|---|
| `updated_by` | string | The acting agent name (see the table below). |
| `updated_date` | string | ISO 8601 UTC timestamp with seconds, `YYYY-MM-DDTHH:MM:SSZ` (for example `2026-10-29T09:41:07Z`). |

### Agent Names

| Actor | `updated_by` value |
|---|---|
| Init agent | `init` |
| Scaffold agent | `scaffold` |
| Layout agent | `layout` |
| Filter agent running a filter skill | `filter:<filter>` (for example `filter:research`, `filter:quality`) |
| Enrich, write, style, translate, publish, review, humanize, config | The agent name (for example `enrich`, `publish`) |
| Fixed-form agents | `poyar`, `line`, `rhyme`, `lyrics`, `limerick`, `haiku` |
| Human edit | `human` or `human:<name>` |

A skill inherits the identity of the agent that invoked it. Skills never invent
their own `updated_by`; the owning agent stamps the written files.

## Markdown Format

Add a two-bullet metadata block immediately after the file's first H1 heading. If
the file has no H1, place it at the top. If the file already has a metadata bullet
list directly after the H1 (for example `storyline.md`), place the two bullets
inside that list in its existing order instead of creating a second block. If the
file starts with YAML frontmatter, keep the frontmatter first and place the block
after the H1 that follows it.

```markdown
# <Title>

- **updated_by:** init
- **updated_date:** 2026-10-29T09:41:07Z
```

Rules:

- Use exactly these two bullets with lowercase snake_case keys.
- Legacy `- **Updated:**` and `- **Updated by:**` bullets are the same fields.
  Rename them in place to `updated_date` and `updated_by` on the next write;
  never keep duplicates. Preserve `Created` and every other metadata bullet.
- When the file is a reader-facing assembled book (`book.md`), keep a single
  consolidated audit block after the H1. When assembling from per-chapter files
  that each carry a block, strip the per-chapter blocks from the concatenated
  body so the book contains one audit block only.

## JSON Format

Add the fields at the root of the JSON document:

```json
{
  "updated_by": "init",
  "updated_date": "2026-10-29T09:41:07Z"
}
```

Rules:

- Preserve key order, indentation, encoding, and every existing field. Merge;
  never replace the document.
- If a legacy `updated_at` key exists, set it to the same timestamp as
  `updated_date` so existing consumers stay consistent. If it does not exist,
  do not add it.
- Never change `created_at`, `created_date`, or any creation timestamp.

## When To Stamp

- **On create:** write both fields as part of the initial content.
- **On edit:** update both fields in the same write that changes the content.
  Never backdate.
- **Bulk commands:** use one timestamp for every file written by that command.
- **No-op:** do not rewrite a file just to bump the timestamp. If content did not
  change, leave the file untouched.

## Precedence And Conflicts

1. Content correctness and schema-required fields take priority. Audit fields are
   additive.
2. History and archive snapshots are always exempt; never stamp or rewrite them.
3. **Verbatim clones.** When a workflow copies a source file into a new location
   (for example the scaffold clone of `gist.md`, `storyline.md`, `book.json`, and
   `progress.json` into the pipeline), copy the bytes first, then stamp the copy
   with the copying agent's identity. Any equality check between the source and
   the clone (such as the scaffold book-plan identity check) must ignore
   `updated_by`, `updated_date`, and the synchronized legacy `updated_at`.
4. **CLI-backed writers.** When a command delegates the write to a repository CLI
   (`config`, `publish`, or an offline-mode `scaffold`/`enrich`/`write`), the CLI
   output is bound by this contract. After the CLI completes, the agent verifies
   the written `.md`/`.json` files. If the fields are missing, the agent repairs
   only those fields when it has write access; it must not alter any other
   attribute, and it reports the gap when it cannot write.
5. If a file's schema genuinely cannot accept extra root fields, do not silently
   skip it: report the file and the reason to the caller.
