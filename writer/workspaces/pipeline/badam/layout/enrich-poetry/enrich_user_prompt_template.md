=== BOOK CONTEXT (pipeline model.json) ===
{book_context}

=== AUTHOR'S MANDATED VOICE (override.md — governs HOW, not WHAT) ===
{voice}

=== AUTHOR'S DECLARED WORLD (gist.md + storyline.md — the ONLY source of subject matter) ===
{sources}

=== BOOK ARC (every chapter title, in order) ===
{arc}

=== NEIGHBOURING CHAPTERS (subject matter and suggestions already taken) ===
{neighbours}

=== SUGGESTIONS ALREADY USED ELSEWHERE IN THIS BOOK (do not repeat or paraphrase) ===
{pool}

=== THIS CHAPTER (complete model; enrich it) ===
{chapter}

For poetry, split THIS CHAPTER into exactly its declared `segment_count` segments.
Return the ordered `segments` array required by the system contract. Each
segment receives this chapter's `word_target`; derive distinct segment titles
and summaries only from this chapter's title and summary. If a populated
`segments` array already exists, preserve it and do not return a replacement.

=== VARIATION BRIEF ===
seed: {seed}
primary lens ({lens_name}): {lens_guidance}
secondary twist: {twist}
Use the lens and the twist to force a direction this book has not taken yet. They are prompts to your imagination, not text to quote.

=== YOUR TASK ===
Return the single JSON patch described in the system prompt. Fill this chapter's empty tags where the purpose is clear, then add angles, subject rotations, story seeds, sensory detail, and research questions that no neighbouring chapter has already used.
