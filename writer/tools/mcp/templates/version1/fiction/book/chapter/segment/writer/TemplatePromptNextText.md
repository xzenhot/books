CONTINUE TO WRITE FOR NEXT SEGMENT.

### OBJECTIVE
You have to write a specific part of chapter number {chapter_index} of the book. 
- **Current Part:** Section {segment_index} of {segment_count}.
- **Goal:** This segment will be created based on {segment_summary}.
- **Here is what happened previously: {last_two_sentences}

### TECHNICAL CONSTRAINTS (FOR AGENTIC PARSING)
1. **Output Format:** Return ONLY a valid JSON object. 
2. **No Markdown:** Do not use ```json blocks or any introductory text.
3. **JSON Schema:** Follow this shape: {segment_template_json}
4. **Data Integrity:** 
   - Escape all Newlines with `\n` and double quotes with `\"` within the 'segment_content' field.
   - This is extremely important for C# deserialization. Use double quotes (") for all keys and values.
5. **No Preamble:** Do not say "Here is the JSON" or "Sure" etc.

### JSON Shape Structure to return :** 
{segment_template_json} 

### OUTPUT
- **Exact JSON shape to return. Do not wrap with "content" wrapper. Only valid tag:  "total_words","segment_content","last_two_sentences"
Now provide the JSON.