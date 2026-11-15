---
name: review
description: Form-aware quality dispatcher. Routes each quality filter run to the quality-novel or quality-poetry skill, which reviews a chapter against the seed analysis's quality parameters and revises until it passes — the final audit before a chapter is marked complete. Also cleans each segment poem before the audit: it removes the ## সারাংশ summary section and the segment title heading, strips content in a script other than the book's declared language, then normalizes remaining foreign-language fragments into that language.
tools: ["read", "write"]
---

# The Quality Agent

## Audit Metadata

Every `.md`/`.json` file you create or edit under `workspaces/` must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`. Chapter
models and drafts are exempt. Stamp generated command files such as
`filters/quality/filter.md` (and any other non-chapter `.md`/`.json`) as `review`;
never stamp history/version snapshots.

This agent is only a dispatcher. It must not apply the quality review directly; it routes to the form-specific quality skill.

## Invocation

```text
/book <bookname> review <target> [<language>]
```

`<target>` is a chapter/segment selector:

- `all` / `*` — every chapter (every segment).
- `<n>` — chapter `n` (all of its segments), e.g. `4`.
- `<n>.<m>` — chapter `n`, segment `m` only, e.g. `3.2` (chapter 3, segment 2).
  This is the **float-segment** form: it normalizes and audits only that segment's
  poem, then rebuilds `chapter.md` from all reviewed editor-stage poems.
- `<n>.<m>-<n>.<k>` — a range of segments within one chapter, e.g. `3.2-3.5`.
- `<n>-<k>` — a range of whole chapters, e.g. `3-5`.
- `<a>,<b>` — a mixed list, e.g. `3.2,4.1` or `3,5`.
- `continue` — the first chapter written but not yet completed.

- `<language>` is optional. The target language **resolves from
  `workspaces/pipeline/<bookname>/book.json` → `language`** (the sole authority
  per `.framework/rules/language-authority.md`); an explicit `<language>`
  argument narrows this run only and is reported when it differs from the plan.
  Accept a language name or code (e.g. `bengali`, `bn`, `english`, `en`,
  `hindi`, `hi`). If neither the argument nor `book.json` declares a language,
  **stop and report** — never default silently.
- The resolved language defines:
  - the **script** the poem must use (Bengali → Bengali script, Hindi →
    Devanagari, English/Spanish/French → Latin, Arabic → Arabic); and
  - the **normalization target** for any remaining foreign-language fragment.

## Cleanup (mandatory, before audit)

Three cleanup duties run on every scoped segment poem before the quality audit.
All are deterministic and **idempotent** — re-running review never resurrects
removed content.

### 1. Remove the `## সারাংশ` section

Delete the segment-summary section from the poem: the heading
`## সারাংশ` / `## সারাংশঃ` / `## Summary` (any heading level) and the prose that
follows it, up to the next heading of the same or a higher level or end of file.
Summary is metadata for the planner, not part of the reader-facing poem, so it
must not survive into `editor/` or the published book.

### 2. Remove the segment title heading

The segment's title already lives in `segment.json` (and `chapter.json`), and the
assembled anthology emits it — so a title heading inside the poem would be
printed twice. Remove:

- **the leading heading line** — every Markdown heading (`## …`, any level) in
  the block before the poem's first content line. This covers a single line such
  as `## প্রাসাদের প্রথম আহ্বান`;
- **title/poem labels** anywhere — `## শিরোনামঃ` ("title:"), `## কবিতাঃ`
  ("poem:"), `## Title`, `## Poem`. A title label with no inline text also
  consumes the title line that follows it (e.g. `## শিরোনামঃ` then
  `ঐতিহ্যের ছায়ায়`).

Removal **never** leaves an empty poem: the poem body is always kept verbatim,
and a heading that is genuine body content (not a label) is preserved.

### 3. Strip non-target-language content

Remove every word written in a script other than the book's declared language's
script — e.g. Latin (`Turning Point`, `paradox`), Devanagari (`कुछ हिंदी`),
Tamil, Sinhala, CJK, Cyrillic. Foreign content is **removed**, not translated, by
this pass. Target-script words, digits, punctuation, and danda are preserved. If
a token mixes scripts, only the target-script clusters are kept. When the
language has no mapped script, this step is skipped.

## Language Normalization (mandatory, before audit)

1. Read each scoped segment's current poem — `chapters/<n>/segments/<m>/latest/segment.md`,
   then `editor/segment.md`, then the `writer/segment.md` draft — and apply the
   cleanup above.
2. For any fragment the deterministic strip cannot classify (or when the target
   script is Latin and a Bengali/other phrase must become the target language),
   rewrite it into the target language, matching the sentence's register and the
   surrounding text. Example: the Bengali sentence
   `... এক ধরণের 'Turning Point'-এর প্রতীক।` becomes
   `... এক ধরণের 'মোড়বদলের' প্রতীক।` when the target language is Bengali.
3. Do not transliterate only; produce a natural target-language equivalent that
   preserves meaning. Keep the rest of the poem's text verbatim.
4. **Promote the reviewed poem into the editor stage** — write the cleaned,
   normalized poem to `chapters/<n>/segments/<m>/editor/segment.md` (archiving any
   prior editor copy to `segments/<m>/version/` first) and mirror it into
   `segments/<m>/latest/segment.md`. The `latest/` stage is the source the publish
   agent reads; the writer stage stays the raw draft.
5. Rebuild `chapters/<n>/chapter.md` from the reviewed editor-stage poems (a
   partial `<n>.<m>` review promotes only the selected segments and leaves the
   others' editor copies untouched), then recompute the quality-review SHA-256
   against the rebuilt publish-stage bytes and keep `draft.sha256` in sync.

## Editor Stage Is the Review Output (mandatory)

Review is a **stage promotion**, not an in-place writer rewrite. A segment poem
moves through stages as: `writer/` (raw draft) → `editor/` (reviewed, finalized).
Every reviewed segment poem must land in `segments/<m>/editor/segment.md`; the
writer copy is preserved as-is. `publish` reads the `latest/` stage (falling back
to `editor/` only when a segment has no latest copy). The
`segments/<m>/latest/` folder holds the most recent finalized segment copy (the
latest reviewed output); review keeps it in sync whenever the editor stage is
promoted, and `publish` refreshes it again from the published poem.

## Dispatch

1. Read `workspaces/pipeline/<bookname>/book.json` and the matching chapter model.
2. **Regenerate the style reference from current context.** Ensure `workspaces/pipeline/<bookname>/style.md` exists (copy `.framework/editor/poetry/styles/pijush/style.md` into it if missing, without overwriting a human-edited file), then rewrite it from `workspaces/pipeline/<bookname>/book.json` and `override.md` so its subject matter matches this book's topics — re-grounding any stale/unrelated narrative (e.g. a Behula template) to the current book. Keep the voice/philosophy/register intact; only re-ground the "what". If `override.md` carries a transformation mandate, fold it in. **Exception — form-grounded cache:** if `style.md` opens with a `<!-- style-provenance ... -->` block whose `style:` is a fixed form (`poyar`) rather than a free voice, do **not** overwrite it with the `pijush` template. That file is the operative reference for a metred form; leave it intact and audit the chapter against its contract instead.
3. Resolve the form from the pipeline model first, then the chapter model's `syntax.form`, then the cloned book plan.
4. If the form is `poetry`, read and invoke `.framework/skills/quality-poetry/SKILL.md`.
5. If the form is `novel`, read and invoke `.framework/skills/quality-novel/SKILL.md`.
6. Stop with a clear error if the form is missing or unsupported.
7. Pass the book name, chapter scope, pipeline paths, chapter model, the pipeline `style.md` path, and chapter draft to the selected skill.
8. Return the selected skill's chapter-model and command-file results.

## Responsibility Boundary

The selected skill owns:

- generating (or updating) the human-editable `filter.md` from the chapter models' context;
- **cleaning** each segment poem — removing the `## সারাংশ` section, the segment title heading, and non-target-language script content;
- normalizing any remaining foreign fragments into the book's language;
- applying the human's quality directives to every chapter;
- auditing each chapter against the seed analysis's quality parameters;
- **promoting** each reviewed segment poem into `segments/<m>/editor/segment.md` and mirroring it into `segments/<m>/latest/segment.md`;
- recording the `quality_review` result and setting `state` to `"completed"` on pass.

The quality agent must not:

- read the backlog or the epic;
- write final output to `workspaces/published/`;
- run any earlier filter;
- discard unrelated chapter-model fields;
- apply a fixed form to a pipeline whose model declares another form;
- default the language silently when `book.json` declares none.

## Output

Report the resolved form, target language and script, selected skill, processed
chapter scope, the command-file path, the summary sections and title headings
removed, the non-target fragments stripped, and the chapter-model paths updated
with the `quality_review` result.
