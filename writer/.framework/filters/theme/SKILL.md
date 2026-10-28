---
name: theme
description: "Use when defining, assigning, or weaving thematic categories into chapters — the philosophical lens that gives each chapter its spine. USE FOR: building a theme set, cycling themes across chapters, embodying a theme in image and cadence rather than explanation, grounding prose in a reference work's core ideas. DO NOT USE FOR: the voice/style itself (use poeticprose), or factual research (use research)."
---

# The Theme Agent

## Audit Metadata

This filter writes only the chapter model under the exempt `chapters/**` tree, so
it stamps no audit fields. If it ever writes a non-chapter `.md`/`.json`, stamp it
as `filter:theme` per `.framework/rules/audit-metadata.md`.

This agent is only a dispatcher. It must not apply the theme assignment directly; it routes to the form-specific theme skill.

## Dispatch

1. Read `workspaces/pipeline/<bookname>/book.json` and the matching chapter model.
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
- write final output to `workspaces/published/`;
- run any later filter;
- discard unrelated chapter-model fields;
- apply a fixed form to a pipeline whose model declares another form.

## Output

Report the resolved form, selected skill, processed chapter scope, and the chapter-model path updated with the `stereotype` object.
