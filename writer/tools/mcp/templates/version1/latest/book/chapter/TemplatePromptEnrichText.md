You are enriching the planning metadata for one chapter. Do not write chapter prose or redesign its layout.

BOOK CONTEXT:
{book_context}

THIS CHAPTER:
{chapter}

NEIGHBOURING CHAPTERS:
{neighbours}

VARIATION GUIDANCE:
{variation_guidance}

Return one JSON object as an additive patch. Preserve all populated values. Never emit or alter state, status, filter_history, completed_date, word_count, enrich, override, chapter_index, name, word_target, level, segments, chapter_title, or chapter_summary. Keep all text values in the book language. Do not invent sources, citations, URLs, dates, statistics, or facts. Put unverifiable claims in research_questions. Keep every array entry a distinct plain string and avoid repeating ideas from this chapter or neighbours.

Prefer filling empty planning tags where their purpose is clear. Include `creative_enrichment` with:
- angles: at least 3 materially different viewpoints
- story_options: at least 3 optional fictional scene seeds, each with setting, desire, obstacle, and turn
- subject_rotations: at least 2 alternative treatments of this chapter's subject
- sensory_details: at least 2 concrete details using different senses
- research_questions: at least 1 question for human verification
- variety_note: concise explanation of how this chapter differs from neighbours

Use `further_references` only when its existing value is empty. Entries must be {"no":"1-based number","reference":"topic","weblink":""}; never include a URL. Return valid JSON only.
