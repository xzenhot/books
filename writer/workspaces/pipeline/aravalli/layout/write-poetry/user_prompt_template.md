{style_prompt}

---

Now write chapter {number}. Use the complete chapter model context below: its title, summary, word target, references, themes, and any nested enrichment or filter guidance that is present. Metadata describes the chapter; do not reproduce JSON paths, state fields, or context headings in the output. Embody the philosophy, voice, and structure defined above, and match the syntax and rhythm of the sample above. Write in poetic prose ({lang_word}), no headings, no markdown code blocks, no title unless asked.

HUMAN OVERRIDE INSTRUCTIONS (bind to these; they take precedence over the style above):

{override}

Treat the override as craft rules to apply to your writing — do not quote them, name them, or turn their wording into subject matter.

CHAPTER CONTEXT (complete model.json):

{context}
