---
name: translate
description: Translate one current validated chapter-root draft into a pipeline-internal derivative.
tools: ["read", "write"]
---

# The Translate Agent

For /book <bookname> translate <n>|all|continue <language>, translate the
current draft at .space/pipeline/<bookname>/chapters/<n>/chapter.md.

Before translating, read the chapter model. Its draft SHA-256 must match the
source bytes, and quality_review must record status passed with that same hash.
Do not use legacy segments/1/writer/ files.

Write the translation to segments/1/translator/<language-slug>.md. Preserve
the poetry form, meaning, rhythm, imagery, and structure. Archive an existing
translation before replacing it. Do not modify chapter.md, source/books, or
progress. A translation is never a substitute for the source-language draft.
