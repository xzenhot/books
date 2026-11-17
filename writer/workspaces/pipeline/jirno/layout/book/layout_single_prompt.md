Create the complete backlog book plan as valid JSON. Return JSON only — no Markdown fence, no explanation.
Use the exact structural shape and field names of the template below.
Set book_name to {bookname} and form to {form}.
Derive chapter count, titles, summaries, references, book summary, and filter chain from the epic. Preserve every topic or chapter in the epic; do not invent a different premise.
Each chapter must include: chapter_index, name, word_target, chapter_title, chapter_summary, further_references.
For poetry, also set a positive `segment_count` on every chapter (default 8) and populate the `segments` array with exactly that many ordered records (each with `segment_index`, string `name`, the chapter's `word_target`, a distinct `segment_title`, a grounded `segment_summary`, and an empty `further_references` array). For novels, omit `segment_count` and `segments`.
IMPORTANT: every chapter_summary must be 2–4 sentences (150–200 words) describing what the chapter explores — never a one-line placeholder.

TEMPLATE book.json:
{template}

EPIC:
{epic}
