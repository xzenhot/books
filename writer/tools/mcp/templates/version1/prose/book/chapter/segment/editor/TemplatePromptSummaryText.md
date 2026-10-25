Please help me to get running summary for a story.
So far , the running summary is:
{running_summmary}

And newly added text are:
{newly_added_text}

Take both and create running summary in {book_language} and respond with following JSON.

### OUTPUT Format JSON
{
 "text_summary": "here goes the summary"
}


### OUTPUT
- **Generate text in each tag in {book_language} language 
- **Exact JSON shape to return. Do not wrap with "content" wrapper. Only valid tag:  "total_words","segment_content","last_two_sentences"
- **Output Format:** Return ONLY a valid JSON object. 

Now provide the JSON.
