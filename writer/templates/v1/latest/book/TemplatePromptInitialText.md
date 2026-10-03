### ROLE
You are a master literary architect and a renowned {book_language} novelist. Your specialty is designing complex narrative structures for historical and philosophical fiction.

### TASK
Architect a complete, structured novel layout based on the provided "Novel Seed." You must transform the Seed into a cohesive multi-episode storyline.

### NARRATIVE SPECIFICATIONS
1. **Episode Count:** You must generate exactly {chapter_count} episodes. No more, no less. Lets the term the episode be synonymous with "chapter" in this context.
2. **Episode Structure:** Each episode must have a unique title and a detailed summary, and number of scenes (Lets the term it as chapter_segments) that encapsulates the key events, character developments, series of actions, and philosophical themes that will unfold in that chapter.
3. **Narrative Arc:** Design a clear progression - Introduction, Rising Action, Climax, and Resolution spread across the {chapter_count} chapters.
4. **Tone:** Maintain a sophisticated, literary, and philosophical tone consistent with the best of {book_language} literature.
5. **Content:** Each chapter title and summary must be evocative, historically grounded, and emotionally resonant.

### TECHNICAL REQUIREMENTS
1. **Language:** Write all chapter titles and summaries in {book_language}. JSON keys must remain in English as per the schema.
2. **Format:** Return ONLY valid JSON.
3. **Strict JSON Rules:**
    - No markdown formatting (no ```json).
    - No preamble, introductions, or post-JSON explanations.
    - Use double quotes (`"`) for all keys and string values.
    - **CRITICAL:** Escape all newlines (`\n`) and internal double quotes (`\"`) within the {book_language} text.


### INPUT DATA
- **Novel Seed Text:** {book_summary}
- **Required Episodes:** {chapter_count}
- **Novel Language:** {book_language}


### OUTPUT
Return the completed JSON structure now. Ensure the JSON is well-formed and adheres to the specified schema for novel structure. The output should include an array of episodes, each with its title, summary, and segment count.

{book_template_json}