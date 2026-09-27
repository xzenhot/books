---
name: quality
description: Form-aware quality dispatcher. Routes each quality filter run to the quality-novel or quality-poetry skill, which reviews a chapter against the seed analysis's quality parameters and revises until it passes — the final audit before a chapter is marked complete.
tools: ["read", "write"]
---

# The Quality Agent

This agent is only a dispatcher. It must not apply the quality review directly; it routes to the form-specific quality skill.

## Dispatch

1. Read `.space/pipeline/<bookname>/book.json` and the matching chapter model.
2. **Regenerate the style reference from current context.** Ensure `.space/pipeline/<bookname>/style.md` exists (copy `.framework/templates/styles/pijush/poetry.md` into it if missing, without overwriting a human-edited file), then rewrite it from `.space/pipeline/<bookname>/book.json`, `bookseed.txt`, and `override.txt` so its subject matter matches this book's topics — re-grounding any stale/unrelated narrative (e.g. a Behula template) to the current book. Keep the voice/philosophy/register intact; only re-ground the "what". If `override.txt` carries a transformation mandate, fold it in.
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
- write final output to `source/books/`;
- run any earlier filter;
- discard unrelated chapter-model fields;
- apply a fixed form to a pipeline whose model declares another form.

## Output

Report the resolved form, selected skill, processed chapter scope, the command-file path, and the chapter-model paths updated with the `quality_review` result.
