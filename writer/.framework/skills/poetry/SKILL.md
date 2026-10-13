---
name: poetry
description: Write or rewrite a poetry chapter as flat, continuous poetic prose (no section headings). Driven by the chapter's chapter.json, honoring the assigned signature and theme. Applies the transformer style from `.framework/context/poetry/styles/<style>/style.md` (default `pijush`) and any human override instructions as the final layer. Writes the chapter to chapters/<n>/chapter.md, archiving any prior copy to segments/1/version/.
---

# Poetry Write — Flat Poetic Prose

Use this skill for a poetry pipeline to write (or rewrite) one chapter's core content so it becomes deeper, more finished, and more human — always in the resolved transformer style from `.framework/context/poetry/styles/<style>/style.md` (default `pijush`).

## The Flatten Rule (ESTABLISHED)

The chapter output is **always flat, continuous poetic prose** — never sectioned. Section headings such as `## Question`, `## Oration`, and `## Benediction` are **removed entirely**; only the prose that followed them remains, merged into continuous paragraphs. Do not leave empty headings, stray `#` markers, or orphaned labels. The only heading permitted is the chapter title (`# {chapter_title}`) if the pipeline convention requires a title. This rule is absolute and overrides any other instruction in this skill.

## Scope

This skill works on **one chapter at a time** in an existing pipeline, driven by the chapter's metadata:

- Chapter guidance (authoritative, carries every prior filter's result): `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the authoritative chapter metadata (topic/title, `chapter_summary`, `category`, `subject`, `era`, `place`, `figures`, `events`, `theme`, `theme_essence`, `metaphor_family`, `contemporary_mapping`, `stereotype` including `signature`/`reference`/`syntax_sample`/`theme_set`, and `word_target`). This is the sole per-chapter input; `chapter.md` is not read as a source.
- Human override instructions (always present; seeded at scaffold): `workspaces/pipeline/<bookname>/filters/override/filter.md`
- Output: `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md`

## What to Read

Before writing, read these files in order:

1. `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the chapter model (the only per-chapter input; never `chapter.md`).
2. `workspaces/pipeline/<bookname>/book.json` — the book identity and summary, if you need broader context.
3. `workspaces/pipeline/<bookname>/override.txt` — the **master human override** (the author's craft directives). This is mandatory reading on every write; it takes precedence over every default in this skill, including the flatten/continuous-prose rule. Read it before writing.
4. `workspaces/pipeline/<bookname>/filters/override/filter.md` — the pipeline override command file (always present; created at scaffold). Read its `## Instructions` section for **every** rewrite and apply non-empty instructions to the new version (see *The Override Layer*).
5. `.framework/context/poetry/styles/<style>/style.md` — the transformer style template (resolve `<style>`, default `pijush`, before reading). If the style folder contains `signature.md`, read it as the interpretive authority for resolving ambiguity in `style.md` (see *The Style Layer*).

## Chapter Layout Contract

- `chapters/<n>/chapter.md` is the live working draft, authored by this skill. It is written to the chapter root, not the segment writer folder.
- `chapters/<n>/chapter.json` remains the authoritative runtime metadata file.
- `segments/1/version/` holds archived copies of any prior `chapter.md` before this skill overwrites it.
- `segments/1/editor/` is for editorial notes only, and `segments/1/translator/` is for translated derivatives only.

## Archive Before Overwrite

1. If `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md` does **not** exist, create it — this is a first write; no archive is required.
2. If it **already** exists, copy it to `workspaces/pipeline/<bookname>/chapters/<n>/segments/1/version/` (creating that folder if missing) before overwriting. Name the copy `chapter_v<k>.md`, where `<k>` is one greater than the highest existing `chapter_v*.md` in that version folder (start at `1`).
3. Never overwrite an existing archived copy; always increment.
4. After archiving, overwrite `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md` with the new draft. Do not write the result into `segments/1/writer/`.

## Rewriting Rules

1. **Flatten.** Remove the **Question**, **Oration**, and **Benediction** headings entirely; merge their prose into continuous paragraphs. The output is flat poetic prose, not a three-section frame.
2. **Topic and category.** Ground the prose in the chapter's topic and thematic category from `chapter.json` or `bookseed.txt`.
3. **Verse qualities.** Use compression, image, anaphora, rhythm, and line-break as instruments. Let metaphors carry abstraction rather than explaining it.
4. **Honor the signature.** Write in the chapter's assigned signature voice — its movement, motifs, and diction should carry the theme.
5. **Thread the theme.** Weave the chapter's assigned theme and its essence into the prose's images and turning points.
6. **Length.** Target 500–800 words unless the pipeline specifies otherwise.

## The Style Layer (`<style>`, default `pijush`)

The transformer style always applies. It selects a **transformer style** from
`.framework/context/poetry/styles/<style>/style.md` that reshapes
the written content:

1. **Resolution.** Resolve `<style>` to `.framework/context/poetry/styles/<style>/style.md`, using `pijush` when the invocation omits `<style>`. If the folder or `style.md` does not exist, stop and report, listing the available folders under `.framework/context/poetry/styles/` — never silently write without the resolved style.
2. **Authority.** If the style folder contains `signature.md`, read it and treat it as the interpretive authority for resolving ambiguity or tension within `style.md` (voice, identity, and tonal decisions).
3. **Application.** Apply the style to the rewritten prose. The style governs voice, imagery, and register — it never changes the chapter's metadata-driven content requirements (topic, theme, figures, word target) and never re-introduces section headings.
4. **Layer order.** Transformation layers apply in this order: chapter metadata (base) → style (voice/register) → override instructions (`filters/override/filter.md`, final and binding).

## The Master Override (`override.txt`)

`workspaces/pipeline/<bookname>/override.txt` is the **master human override** — the
author's own craft directives for the book. It is **always authoritative and binding**,
and it overrides any conflicting default in this skill. Read it on **every** write
(before `filters/override/filter.md`) and apply every directive exactly:

- If it says **"লাইন ব্রেক দিন" (give line breaks)**, break the poem into short
  lines — one clause or image per line — **overriding** the flat continuous-prose
  flatten rule below.
- If it gives a **line-count limit** (e.g. "১৬-২২ লাইনের মধ্যে সীমাবদ্ধ রাখুন" —
  keep it strictly within 16–22 lines), honor that exact range. The line-count
  limit is binding and wins over the default word target.
- If it says **"শব্দকে পুন পুন ব্যবহার করবেন না" (do not repeat a word)**, use a
  synonym instead of repeating any word within a line or passage.
- If it says **"কোন একটি নির্দিষ্ট লাইন সংখ্যায় রাখবেন না"** (do not keep any one
  fixed line count — sometimes 2–6, sometimes 7–12, sometimes 13–18), **vary the
  line count and the poem's shape from chapter to chapter**. Do not reuse a fixed
  stanza/line structure across poems.
- If it says **"সব সময় কবিতা ক্লোজ করার দরকার নেই। ওপেন রাখবেন"** (the poem need
  not always close; leave it open), end some poems on an unresolved image or
  question rather than a conclusive turn.
- If it says **"একই প্যাটার্নের কবিতা লিখবেন না" / "প্যাটার্ন রিপিট করবেন না"**
  (do not write the same-pattern poem), never fix a recurring slot for the muse,
  the question, or the closing — vary their position (the muse may appear early,
  mid, or late; the question may or may not close the poem).
- **The muse's position is never fixed.** If the override says the lover (e.g.
  Sagarika) must appear but its line is landing repeatedly at the same spot (e.g.
  a "সাগরিকা, তুমি …" address around line 14–15), **move it** — she may surface in
  the opening, the middle, or the close; as a direct address, a third-person
  image, or a bare name; a fragment, not always a full couplet. Vary the phrasing
  too — do not reuse the same "সাগরিকা, তুমি …" turn in consecutive poems.
- If it asks for **~5% Hindi-Urdu flavor** (e.g. সन्नाटा, হাওয়া, মিত্তি, দর্দ),
  weave one or two such common words in where they fit, not in every poem.
- Every directive (dramatic opening, philosophical questions, myth-over-truth,
  everyday symbols, a named muse, the living mountain) must **shape** the prose
  silently — never be quoted, named, or recited as the poem's own content.

When `override.txt` and this skill's defaults conflict, **`override.txt` wins.**

## The Override Layer (`filters/override/filter.md`)

`workspaces/pipeline/<bookname>/filters/override/filter.md` is the **pipeline override command file** — a human-authored instruction file created by the scaffold step. It must **always be present** in the pipeline. Apply it to **every** rewrite:

- If the file is somehow missing, recreate its baseline from `.framework/filters/override/SKILL.md` (form-customized, empty `## Instructions`) before rewriting; if you cannot, rewrite without override and report the missing file.
- If the `## Instructions` section (below the `---` line) is empty, rewrite the chapter normally — no override applies.
- If it holds instructions (bullets or paragraphs), treat **each one as binding** and apply it as the final layer to the chapter written to `chapters/<n>/chapter.md`.
- The human's word is final: apply instructions exactly; do not reinterpret, soften, or skip them.

## Language

Read the `language` field from the pipeline (`book.json` first, then
`chapter.json`). Use that language for the rewritten content. If the language is
`en`, use English. If it is another language code, write in that language. Do not
assume a default language.

**The language is read from `book.json` — never from `override.txt`.** The master
override (`override.txt`) is a *craft* directive (voice, line breaks, repetition,
symbol, muse, length) and may itself be written in any language; its language is
never the output language. Even if `override.txt` is worded in English (or
mentions "translated to English"), the poem's language is determined solely by
`book.json` → `language`. Read that field on every write and write the poem in it.

## Override Is Craft, Not Content

The pipeline override command file (`filters/override/filter.md`) and the master
prompt (`override.txt`) hold **craft directives**, never subject matter. Rules
such as "start dramatically", "break lines", "do not repeat a word — use a
synonym", "establish myth, wrap truth in symbol", "draw symbols from everyday
life", "keep the muse present", and "make the mountain live" must shape the
prose silently — they must never be quoted, named, or recited as the poem's own
lines. Avoid repeating a word within a line or passage; reach for a synonym.

## Output Format

Write the rewritten chapter to `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md` as **flat, continuous poetic prose** — no section headings — **unless the master `override.txt` instructs otherwise** (e.g. line breaks), in which case the override wins and the output follows it. The only heading permitted is the chapter title (`# {chapter_title}`) if the pipeline convention requires a title. Do not add `## Question`, `## Oration`, `## Benediction`, or any other section labels.

Do not add extra metadata, comments, or explanation outside the chapter text.

## What Not to Do

- Do not scaffold pipelines.
- Do not run filters.
- Do not consult the backlog `workspaces/backlog/<bookname>/override.md`; apply the pipeline override command file `workspaces/pipeline/<bookname>/filters/override/filter.md` and the master `workspaces/pipeline/<bookname>/override.txt`.
- Do not write the chapter into `segments/1/writer/` — the output is `chapters/<n>/chapter.md` only. Prior copies are archived to `segments/1/version/`.
- Do not write to `workspaces/published/` — this skill produces the chapter in the pipeline only.
- Do not update `progress.json` — progress tracking is the writer workflow's responsibility.
- Do not merge versions or decide which version is final.
- Do not re-introduce section headings — the flatten rule is absolute.
