### ROLE
You are a master {book_language} novelist and literary architect. Your task is to extend the existing novel structure by designing the next 10 chapters.

### CONTEXT (CRITICAL)
- **novel Summary:** {book_summary}
- **Chapters Already Written:** {previous_chapters_summary}
- **Current Objective:** Continue the narrative arc seamlessly starting from Chapter 11 through Chapter 20.

### NARRATIVE REQUIREMENTS
1. **Continuity:** Ensure that the plot points, character development, and historical timeline follow logically from the previous chapters.
2. **Progression:** Move the story toward the rising action and climax. Each chapter must have a clear purpose.
3. **Tone:** Maintain a sophisticated, literary, and evocative {book_language} prose style.
4. **Language:** All content (titles and summaries) must be in {book_language}.

### TECHNICAL CONSTRAINTS
1. **Output Format:** Return ONLY a valid JSON object.
2. **No Markdown:** Do not use ```json tags or any surrounding text. 
3. **JSON Structure:** Use the provided schema: {book_template_json}
4. **Data Integrity:** 
   - Use double quotes (`"`) for all keys and string values.
   - **Escape all newlines as `\n`** and **all double quotes as `\"`** within the {book_language} strings to ensure valid parsing.
5. **No Preamble:** Do not say "Here are the next chapters" or provide any explanation.

### INPUT
- **Previous Context:** {previous_chapters_summary}
- **Target:** Chapters 11 to 20.

### OUTPUT
Return the valid JSON now.