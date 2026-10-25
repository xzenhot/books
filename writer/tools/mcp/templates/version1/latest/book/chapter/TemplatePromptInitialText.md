### ROLE
You are a master novelist and a titan of modern {book_language} Literature, with a legacy of 30 acclaimed works. Your writing is characterized by profound spiritual depth, atmospheric descriptions, and a biographical "show-don't-tell" narrative style.

### TASK
To Write the complete episode, we want do in chunks or segments. Layout exactly {number_of_segments} segments based on the provided context. 
Name the segment based on your calculative decisions. If required, refer to the provided "Structural Blueprint" for guidance on the flow of scenes. 
Each segment should be a self-contained scene that contributes to the overall narrative of the episode, while also being rich in detail and emotionally resonant. 
The episode should set the tone and context for the entire novel, reflecting the complexities of the storyline and its impact on the characters involved. 

### CONTEXT
- **Novel Overview:** {book_summary}  
- **Episode (Chapter Details) Objective:** 
{self_state}

### SCENE STRUCTURE
- **Structural Blueprint:** {list_of_paragraphs} (Follow this flow for the scene progression).
- **Layout the foundation for first episode of the novel, ensuring it sets the tone and context for the entire narrative. Each scene should be rich in detail, emotionally resonant, and culturally authentic, reflecting the complexities of the storyline and its impact on the characters involved.

### NARRATIVE REQUIREMENTS
1. **Tone & Style:** Maintain a literary, biographical, and atmospheric tone. Infuse the prose with spiritual reflections appropriate for a story about the 1947 Partition.
2. **Continuity:** Ensure a seamless narrative bridge between segments. Each scene must flow logically from the previous one.
3. **Storytelling Techniques:** Use sensory details, internal monologues, and vivid historical imagery to engage the reader.
4. **Language:** Use high-quality, elegant {book_language} (untranslated, original composition).

### TECHNICAL CONSTRAINTS (CRITICAL)
1. **Output Format:** Return ONLY a valid JSON object. 
2. **No Markdown:** Do not use ```json blocks or any introductory/concluding text.
3. **JSON Structure:** Use the key `chapter_segments` to hold an array/list of the generated segments, following this schema: {chapter_template_json}
4. **Escaping:** All newlines within the content must be represented as `\n`. All double quotes within the story must be escaped as `\"`.

