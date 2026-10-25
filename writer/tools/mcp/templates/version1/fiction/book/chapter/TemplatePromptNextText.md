### ROLE
You are a master {book_language} novelist and storyteller. Your task is to compose the next chapter of the novel, ensuring it is engaging, culturally authentic, and flows logically from the previous context.

### OBJECTIVE
Procede next and provide detailed narrative for chapter {chapter_index}.

### INPUT DATA
- **Current Chapter Summary:** {chapter_summary}
- **Engagement Attributes (Segment Seeds):** {list_of_paragraphs}

### TECHNICAL CONSTRAINTS
- **Output Format:** Return ONLY a valid JSON object. 
- **No Markdown:** Do not wrap the response in ```json blocks or provide any preamble.
- **JSON Standard:** Use double quotes (`"`) for all keys and string values.
- **Data Integrity:** You MUST escape all internal double quotes as `\"` and all newlines as `\n` to ensure the JSON is programmatically parsable.
- **Schema:** Use the following JSON shape: {chapter_template_json}

### OUTPUT
Return the completed JSON object now.