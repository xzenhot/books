---
name: write-poetry
description: Write or rewrite a poetry chapter as flat, continuous poetic prose (no section headings). Driven by the chapter's model.json, honoring the gibran-style signature and assigned theme. Applies an optional transformer style and any human override instructions as the final layer. Writes the chapter to chapters/<n>/chapter.md, archiving any prior copy to segments/1/version/.
---

# Poetry Write — Flat Poetic Prose

Use this skill for a poetry pipeline to write (or rewrite) one chapter's core content so it becomes deeper, more finished, and more human — optionally in a named transformer style.

## The Flatten Rule (ESTABLISHED)

The chapter output is **always flat, continuous poetic prose** — never sectioned. The `## Question`, `## Oration`, and `## Benediction` headings are **removed entirely**; only the prose that followed them remains, merged into continuous paragraphs. Do not leave empty headings, stray `#` markers, or orphaned labels. The only heading permitted is the chapter title (`# {chapter_title}`) if the pipeline convention requires a title. This rule is absolute and overrides any other instruction in this skill.

## Scope

This skill works on **one chapter at a time** in an existing pipeline, driven by the chapter's metadata:

- Chapter guidance (authoritative, carries every prior filter's result): `.space/pipeline/<bookname>/chapters/<n>/chapter.json` — the authoritative chapter metadata (topic/title, `chapter_summary`, `category`, `subject`, `era`, `place`, `figures`, `events`, `theme`, `theme_essence`, `metaphor_family`, `contemporary_mapping`, `stereotype` including `signature`/`reference`/`syntax_sample`/`theme_set`, and `word_target`). This is the sole per-chapter input; `chapter.md` is not read as a source.
- Human override instructions (always present; seeded at scaffold): `.space/pipeline/<bookname>/filters/override/filter.md`
- Output: `.space/pipeline/<bookname>/chapters/<n>/chapter.md`

## What to Read

Before writing, read these files in order:

1. `.space/pipeline/<bookname>/chapters/<n>/chapter.json` — the chapter model (the only per-chapter input; never `chapter.md`).
2. `.space/pipeline/<bookname>/book.json` — the book identity and summary, if you need broader context.
3. `.space/pipeline/<bookname>/filters/override/filter.md` — the pipeline override command file (always present; created at scaffold). Read its `## Instructions` section for **every** rewrite and apply non-empty instructions to the new version (see *The Override Layer*).
4. (When `<style>` is provided) `.framework/templates/styles/<style>/style.md` — the transformer style template. If the style folder contains `signature.md`, read it as the interpretive authority for resolving ambiguity in `style.md` (see *The Style Layer*).

## Chapter Layout Contract

- `chapters/<n>/chapter.md` is the live working draft, authored by this skill. It is written to the chapter root, not the segment writer folder.
- `chapters/<n>/chapter.json` remains the authoritative runtime metadata file.
- `segments/1/version/` holds archived copies of any prior `chapter.md` before this skill overwrites it.
- `segments/1/editor/` is for editorial notes only, and `segments/1/translator/` is for translated derivatives only.

## Archive Before Overwrite

1. If `.space/pipeline/<bookname>/chapters/<n>/chapter.md` does **not** exist, create it — this is a first write; no archive is required.
2. If it **already** exists, copy it to `.space/pipeline/<bookname>/chapters/<n>/segments/1/version/` (creating that folder if missing) before overwriting. Name the copy `chapter_v<k>.md`, where `<k>` is one greater than the highest existing `chapter_v*.md` in that version folder (start at `1`).
3. Never overwrite an existing archived copy; always increment.
4. After archiving, overwrite `.space/pipeline/<bookname>/chapters/<n>/chapter.md` with the new draft. Do not write the result into `segments/1/writer/`.

## Rewriting Rules

1. **Flatten.** Remove the **Question**, **Oration**, and **Benediction** headings entirely; merge their prose into continuous paragraphs. The output is flat poetic prose, not a three-section frame.
2. **Topic and category.** Ground the prose in the chapter's topic and thematic category from `model.json` or `bookseed.txt`.
3. **Verse qualities.** Use compression, image, anaphora, rhythm, and line-break as instruments. Let metaphors carry abstraction rather than explaining it.
4. **Honor the signature.** Write in the chapter's assigned signature voice (e.g. gibran) — its movement, motifs, and diction should carry the theme.
5. **Thread the theme.** Weave the chapter's assigned theme and its essence into the prose's images and turning points.
6. **Length.** Target 500–800 words unless the pipeline specifies otherwise.

## The Style Layer (`<style>`)

When the caller provides a `<style>` argument, it selects a **transformer style** that reshapes the written content:

1. **Resolution.** Look for `.framework/templates/styles/<style>/style.md`. If the folder or `style.md` does not exist, stop and report, listing the available folders under `.framework/templates/styles/` — never silently write without the requested style.
2. **Authority.** If the style folder contains `signature.md`, read it and treat it as the interpretive authority for resolving ambiguity or tension within `style.md` (voice, identity, and tonal decisions).
3. **Application.** Apply the style to the rewritten prose. The style governs voice, imagery, and register — it never changes the chapter's metadata-driven content requirements (topic, theme, figures, word target) and never re-introduces section headings.
4. **Layer order.** Transformation layers apply in this order: chapter metadata (base) → style (voice/register) → override instructions (`filters/override/filter.md`, final and binding).
5. **No style provided.** If `<style>` is omitted, write normally from the chapter metadata and the book's configured stereotype/signature — no transformer style applies.

## The Override Layer (`filters/override/filter.md`)

`.space/pipeline/<bookname>/filters/override/filter.md` is the **pipeline override command file** — a human-authored instruction file created by the scaffold step. It must **always be present** in the pipeline. Apply it to **every** rewrite:

- If the file is somehow missing, recreate its baseline from `.framework/agents/override/agent.md` (form-customized, empty `## Instructions`) before rewriting; if you cannot, rewrite without override and report the missing file.
- If the `## Instructions` section (below the `---` line) is empty, rewrite the chapter normally — no override applies.
- If it holds instructions (bullets or paragraphs), treat **each one as binding** and apply it as the final layer to the chapter written to `chapters/<n>/chapter.md`.
- The human's word is final: apply instructions exactly; do not reinterpret, soften, or skip them.

## Language

Read the `language` field from the pipeline (`book.json` or `model.json`). Use that language for the rewritten content. If the language is `en`, use English. If it is another language code, write in that language. Do not assume a default language.

## Output Format

Write the rewritten chapter to `.space/pipeline/<bookname>/chapters/<n>/chapter.md` as **flat, continuous poetic prose** — no section headings. The only heading permitted is the chapter title (`# {chapter_title}`) if the pipeline convention requires a title. Do not add `## Question`, `## Oration`, `## Benediction`, or any other section labels.

Do not add extra metadata, comments, or explanation outside the chapter text.

## What Not to Do

- Do not scaffold pipelines.
- Do not run filters.
- Do not consult the backlog `.space/backlog/epic/<bookname>/override.md`; apply only the pipeline override command file `.space/pipeline/<bookname>/filters/override/filter.md`.
- Do not write the chapter into `segments/1/writer/` — the output is `chapters/<n>/chapter.md` only. Prior copies are archived to `segments/1/version/`.
- Do not write to `source/books/` — this skill produces the chapter in the pipeline only.
- Do not update `progress.json` — progress tracking is the writer workflow's responsibility.
- Do not merge versions or decide which version is final.
- Do not re-introduce section headings — the flatten rule is absolute.
