
TASK:
Your task is to translate the content to {book_language} language. 
Target translated text should only contain {book_language} language script only. Remove any other language script if present. 

OUTPUT:
Respond with following JSON format:
{
  "source_language": "English",
  "target_language": "Bengali",
  "chunk_index": 1,
  "translation": "..."
}

INPUT: 
Translate this chunk #{chunk_index} into {book_language}:

{content}
 


