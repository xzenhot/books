{style_prompt}

---

Now write segment {segment} of {total} for chapter {number}. Use the complete chapter model context below: its title, summary, word target, references, themes, and any nested enrichment or filter guidance that is present. Metadata describes the chapter; do not reproduce JSON paths, state fields, or context headings in the output. Embody the philosophy, voice, and structure defined above, and match the syntax and rhythm of the sample above. Write in continuous prose ({lang_word}), aiming for roughly {word_target} words, no section headings, no markdown code blocks, no title unless asked.

This segment must flow seamlessly from the prior segments of the same chapter, which are reproduced below. If this is segment 1, open the chapter dramatically and set up the scene, characters, and central tension. If this is the final segment (segment {total}), bring the chapter to a specific, resonant close — an image, turn, question, or silence — not a mere summary. Never restate the chapter title or re-introduce what has already been written.

PRIOR SEGMENTS OF THIS CHAPTER (continue from where this text ends):

{prior_text}

HUMAN OVERRIDE INSTRUCTIONS (bind to these; they take precedence over the style above):

{override}

CHAPTER CONTEXT (complete model.json):

{context}
