Generate exactly ONE chapter for the book below: chapter_index {index}.
Return a single JSON object matching this schema — no array, no prose, no markdown fence:
{schema}

IMPORTANT: chapter_summary must be 2–4 sentences describing what the chapter explores — its conflict, imagery, and open question. Derive chapter_title and chapter_summary from the epic. Set chapter_index to {index} and name to "{index}". For poetry, set segment_count to 8 unless the epic explicitly requires another count, and populate the `segments` array with exactly that many ordered records (each with segment_index, name, word_target, a distinct segment_title, a grounded segment_summary, and an empty further_references array); for novels, omit segment_count and segments.

EPIC:
{epic}
