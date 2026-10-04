# Poetry Lifecycle Contract

Authoritative rules for poetry pipelines. These take precedence over older
conventions and over legacy writer-stage conventions.

1. **Scaffold is resumable.** It adds only plan entries that do not already have
   chapter folders. It never replaces a chapter model, poem, progress record, or
   human override. A changed form, changed existing plan entry, removed poem, or
   changed filter chain requires an explicit migration rather than scaffold.
2. **The current poem is `chapters/<n>/chapter.md`.** The segment version folder
   is immutable history only. `segments/1/writer/` is legacy storage and is never
   a source for style, translation, validation, or publication.
3. **Every write or style replacement archives and verifies the prior root draft,**
   then records `draft.sha256`, `draft.written_at`, and `draft.origin` in the
   chapter model. It removes any old quality review.
4. **Quality reviews the actual current poem.** A passed review records `status`,
   `sha256`, `reviewed_at`, and `reviewer`. Its hash must equal the current draft
   hash.
5. **Write and style never create reader-facing output.** Publish is the only
   operation that creates `source/books/<bookname>/versionN`.
6. **Publish requires every planned poem to have a nonempty registered current
   draft and a matching passed quality review.** It fails before version
   allocation when any poem is missing or stale. It does not create
   introductions, conclusions, or substitute placeholder material for poetry.
7. **Progress keeps written, validated, and published states separately for each
   poem.** A partial write cannot mark the collection complete.
8. **Translation reads only a current, validated chapter-root draft** and writes a
   pipeline derivative. Language-specific publication remains unavailable until
   the Python publisher implements it.
