### TASK
You have to write a chapter of a book. This part will be created entirely based on the 'Segment Summary' given below.

### INPUT DATA
- **Book Context:** {book_summary} | {book_summary}
- **Chapter Summary:** {chapter_summary}
- **Segment Summary (Main Foundation):** {segment_summary}
- **Metaphor/Title (Symbol of Hope):** {segment_title}

### WRITING INSTRUCTIONS
1. **Focus:** Focus only on the events of the 'Segment Summary'. Do not bring in any irrelevant external events.
2. **Metaphor Integration:** Use the metaphor "{segment_title}" 3 to 5 times throughout the writing with great skill. Let it emerge as "Light of Hope" woven into the folds of the narrative, not directly stated. Vary the wording and context each time it is used (Randomized phrasing).
3. **Style & Mood:** Apply deep psychological analysis and accurate application of historical facts in the description. The mood of the writing should align with the 'Segment Summary'.
4. **Length:** Must be at least {number_of_words_per_segment} words or more.
5. **Language:** Use high-quality literary {book_language} language.
6. **Consistency:** Maintain narrative continuity and stay consistent with the 'Chapter Summary' and 'Book Context'.
7. **Avoid Repetition:** Avoid repeating the same information or words. Each sentence should provide new information or perspective.
8. **Engagement:** Make the description lively and engaging to captivate the reader. Each sentence should paint a new picture in the reader's mind.
9. **Emotional Depth:** Strive to evoke deep emotions in the reader's heart. Each event should create a new wave of emotion.
10. **Dialog:** Make dialogue clear and relevant. Dialogue should match the character's personality and the situation.
11. **Character Development:** Emphasize the mental and emotional development of characters. Each character should express a distinct personality and living emotions.
12. **Historical Accuracy:** Apply historical facts accurately. Each event should be correctly presented in its historical context.
13. **Metaphor Usage:** The metaphor "{segment_title}" should emerge in the folds of the writing, as a symbol of new hope and light in the reader's mind. Each time it is used, vary the wording and context so that it blends into the narrative rather than coming directly.
14. **New Character Introduction:** When introducing new characters, clearly present their personality and context. Each new character should blend into the story and paint a new picture in the reader's mind.

Use these characters defined in the 'Book Context' and 'Chapter Summary' to enrich the narrative and ensure consistency throughout the chapter.
{additional_characters_para}

### TECHNICAL CONSTRAINTS (MANDATORY)
- **Format:** Return only a valid JSON object.
- **No Markdown:** Do not write any ```json blocks or any other text.

- **Escaping:** Escape all Newlines with `\n` and double quotes with `\"` within the 'segment_content' field. This is extremely important for C# deserialization.
- **Quotes:** Use only double quotes (") for all keys and values in JSON.

### JSON Shape Structure to return :** 
{segment_template_json} 

### OUTPUT
- **Exact JSON shape to return. Do not wrap with "content" wrapper. Only valid tag:  "total_words","segment_content","last_two_sentences"
Now provide the JSON.