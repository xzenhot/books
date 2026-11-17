Generate ONLY these chapters for the book described below: {indices}.
Return a JSON array of chapter objects — one object per index listed. Use this schema for each object:
{schema}

IMPORTANT: chapter_summary must be 2–4 sentences (150–200 words) describing what the chapter explores — its conflict, imagery, and open question. Never write a one-line placeholder.
Derive each chapter's title and summary from the epic. Set chapter_index to the matching index and name to its string form.
For poetry, set `segment_count` to 8 on every chapter unless the epic explicitly requires another count, and populate the `segments` array with exactly that many ordered records (each with `segment_index`, string `name`, the chapter's `word_target`, a distinct `segment_title`, a grounded `segment_summary`, and an empty `further_references` array). For novels, omit `segment_count` and `segments`.

EPIC:
{epic}
