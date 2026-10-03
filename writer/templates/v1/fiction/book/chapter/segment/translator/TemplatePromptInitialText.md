
TASK:
Your task is to translate the content to {book_language} language. 
Target translated text should only contain {book_language} language script only. Remove any other language script if present. 

OUTPUT:
Respond with following JSON format:
{
  "source_language":"detected_language",
  "target_language": "target_language",
  "translation": "translated text."
} 

INPUT: 
Translate this chunk into {book_language}:

{content}
 
