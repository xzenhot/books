---
name: theme
description: Form-aware theme dispatcher. Routes each theme filter run to the theme-novel or theme-poetry skill, which assigns the chapter its thematic lens and stereotype (signature, reference, theme set) from the chapter's own metadata and prose.
tools: ["read", "write"]
---

# The Theme Agent

This agent is only a dispatcher. It must not apply the theme assignment directly; it routes to the form-specific theme skill.

## Dispatch

1. Read `.space/pipeline/<bookname>/book.json` and the matching chapter model.
2. Resolve the form from the pipeline model first, then the chapter model's `syntax.form`, then the cloned book plan.
3. If the form is `poetry`, read and invoke `.framework/skills/theme-poetry/SKILL.md`.
4. If the form is `novel`, read and invoke `.framework/skills/theme-novel/SKILL.md`.
5. Stop with a clear error if the form is missing or unsupported.
6. Pass the book name, chapter scope, pipeline paths, chapter model, and chapter draft to the selected skill.
7. Return the selected skill's chapter-model result.

## Responsibility Boundary

The selected skill owns:

- reading the chapter's `model.json` (never `chapter.md` — that is an output file owned by the writing path);
- selecting the signature, reference, and theme set from the matching stereotype templates;
- assigning the chapter its theme and mapping it onto a present-day concern;
- recording the `stereotype` object in the chapter's `model.json`.

The theme agent must not:

- read the backlog or the epic;
- write final output to `source/books/`;
- run any later filter;
- discard unrelated chapter-model fields;
- apply a fixed form to a pipeline whose model declares another form.

## Output

Report the resolved form, selected skill, processed chapter scope, and the chapter-model path updated with the `stereotype` object.
