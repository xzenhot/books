Create the complete backlog book plan as valid JSON. Return JSON only — no Markdown fence, no explanation.
Use the exact structural shape and field names of the template below.
Set book_name to {bookname} and form to {form}.
Derive chapter count, titles, summaries, references, book summary, and filter chain from the epic. Preserve every topic or chapter in the epic; do not invent a different premise.
Each chapter must include: chapter_index, name, word_target, chapter_title, chapter_summary, further_references.
IMPORTANT: every chapter_summary must be 2–4 sentences (150–200 words) describing what the chapter explores — never a one-line placeholder.

TEMPLATE book.json:
{template}

EPIC:
{epic}
