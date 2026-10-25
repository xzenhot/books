---
name: review
description: Form-aware quality dispatcher. Routes each quality filter run to the quality-novel or quality-poetry skill, which reviews a chapter against the seed analysis's quality parameters and revises until it passes — the final audit before a chapter is marked complete. Also normalizes language: transforms foreign-language fragments into the target language (default Bengali) before the audit.
tools: ["read", "write"]
---

# The Quality Agent

This agent is only a dispatcher. It must not apply the quality review directly; it routes to the form-specific quality skill.

## Invocation

```text
/book <bookname> review *|all|<n> [<language>]
```

- `<language>` is optional and defaults to **Bengali** (`bn` / `bengali` / `বাংলা`).
  Accept a language name or code (e.g. `bengali`, `bn`, `english`, `en`, `hindi`, `hi`).
- The language is a **normalization target**: before the quality audit, the agent
  rewrites every foreign-language fragment (a word, phrase, or quoted token from
  another script/language) into the target language, in-place, preserving the
  author's meaning, register, and sentence structure.

## Language Normalization (mandatory, before audit)

1. Scan each scoped chapter's `chapter.md` for fragments written in a language
   other than the target — e.g. an English phrase embedded in Bengali prose
   (`'Turning Point'`, `'Red Light'`, `'loom'`) or a Bengali phrase embedded in
   English prose.
2. Rewrite each such fragment into the target language, matching the sentence's
   register and the surrounding text. Example: the Bengali sentence
   `... এক ধরণের 'Turning Point'-এর প্রতীক।` becomes
   `... এক ধরণের 'মোড়বদলের' প্রতীক।` (or the closest idiomatic equivalent) when
   the target language is Bengali.
3. Do not transliterate only; produce a natural target-language equivalent that
   preserves meaning. Keep the rest of the chapter text verbatim.
4. Persist the normalized text back to the chapter's `chapter.md` (archiving the
   prior draft first, per the pipeline's version-before-overwrite contract), then
   recompute the quality-review SHA-256 against the normalized bytes.

## Dispatch

1. Read `workspaces/pipeline/<bookname>/book.json` and the matching chapter model.
2. **Regenerate the style reference from current context.** Ensure `workspaces/pipeline/<bookname>/style.md` exists (copy `.framework/context/poetry/styles/pijush/style.md` into it if missing, without overwriting a human-edited file), then rewrite it from `workspaces/pipeline/<bookname>/book.json` and `override.txt` so its subject matter matches this book's topics — re-grounding any stale/unrelated narrative (e.g. a Behula template) to the current book. Keep the voice/philosophy/register intact; only re-ground the "what". If `override.txt` carries a transformation mandate, fold it in.
3. Resolve the form from the pipeline model first, then the chapter model's `syntax.form`, then the cloned book plan.
4. If the form is `poetry`, read and invoke `.framework/skills/quality-poetry/SKILL.md`.
5. If the form is `novel`, read and invoke `.framework/skills/quality-novel/SKILL.md`.
6. Stop with a clear error if the form is missing or unsupported.
7. Pass the book name, chapter scope, pipeline paths, chapter model, the pipeline `style.md` path, and chapter draft to the selected skill.
8. Return the selected skill's chapter-model and command-file results.

## Responsibility Boundary

The selected skill owns:

- generating (or updating) the human-editable `filter.md` from the chapter models' context;
- applying the human's quality directives to every chapter;
- auditing each chapter against the seed analysis's quality parameters;
- recording the `quality_review` result and setting `state` to `"completed"` on pass.

The quality agent must not:

- read the backlog or the epic;
- write final output to `workspaces/published/`;
- run any earlier filter;
- discard unrelated chapter-model fields;
- apply a fixed form to a pipeline whose model declares another form.

## Output

Report the resolved form, selected skill, processed chapter scope, the command-file path, and the chapter-model paths updated with the `quality_review` result.
