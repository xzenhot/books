{style_prompt}

---

Now write chapter {number}. Use the complete chapter model context below: its title, summary, word target, references, themes, and any nested enrichment or filter guidance that is present. Metadata describes the chapter; do not reproduce JSON paths, state fields, or context headings in the output. Embody the philosophy, voice, and structure defined above, and match the syntax and rhythm of the sample above. Write in poetic prose ({lang_word}).

OUTPUT FORMAT (MANDATORY — follow exactly, no markdown code fences):
# শিরোনামঃ 
{title}

# কবিতাঃ
[the poetry body — written in flowing poetic prose]

# সারাংশঃ
[the chapter summary]

Use exactly these three Bengali headings, in this order, on their own lines.

CHAPTER TITLE: {title}

WORD TARGET: {word_target} words (the poetry body alone — between "# কবিতাঃ" and "# সারাংশঃ"). This is a HARD requirement, not a suggestion. You MUST write a body of at least {word_target} words, and not more than 125% of it. If you stop early, the chapter is incomplete. Keep writing and deepening the imagery, the riverine detail, the body and the myth, until the body reaches this length. Do not pad with filler — expand with genuine sensory and spiritual depth.

HUMAN OVERRIDE INSTRUCTIONS (bind to these; they take precedence over the style above):

{override}

Treat the override as craft rules to apply to your writing — do not quote them, name them, or turn their wording into subject matter.

{gist_guardrail}

{theme_grounding}

CHAPTER CONTEXT (complete model.json):

{context}
