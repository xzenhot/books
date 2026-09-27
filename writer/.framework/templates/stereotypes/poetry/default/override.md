# Override - Transformation Layer (Human-in-the-Loop)

This file is the human's review and transformation layer. It is optional. If present, the writer agent reads it before writing each chapter and applies the instructions here to transform the generated text.

Unlike `bookseed.txt`, which lists what to write, `override.md` describes how to reshape the output: voice, local preferences, dialect, cultural texture, and place or era context.

Leave any section empty if you have no instruction for it. The agent applies only what is filled in.

---

## 1. Prompt Transformation

Describe how to transform the base text into a different prompt or voice.

<!-- Example:
- Shift the prophet's voice from formal sermon to intimate whisper.
- Replace "And he answered, saying:" with a direct, unannounced reply.
- End every chapter with a question instead of a statement.
-->

## 2. Local Preferences

Describe stylistic preferences that override the default style rules.

<!-- Example:
- Prefer short sentences; avoid long compound clauses.
- Avoid the word "verily" if it feels too archaic for the target readers.
- Use more river and boat imagery; use less fire imagery.
-->

## 3. Local Dialects

List dialect words, phrases, grammatical forms, or regional speech patterns to weave in.

<!-- Example:
- Use informal second-person address where culturally appropriate.
- Add regional endearment particles sparingly.
- Keep dialect legible to readers outside the region.
-->

## 4. Slug / Location / Era Context

Add contextual anchors that make the text feel place-specific and time-specific.

<!-- Example:
- Location: river towns, coastal markets, mountain villages, city train stations.
- Era: the 2026 monsoon, the digital age, the post-flood village.
- Slugs: "the river boatman", "the market weaver", "the night fisherman".
-->

---

## How the Agent Applies This

1. Read `override.md` before writing, if it exists.
2. Generate the base chapter from quality + theme + reference.
3. Apply each filled section as a transformation pass, in order:
   - Prompt Transformation: reshape the voice or structure.
   - Local Preferences: adjust style to the human's taste.
   - Local Dialects: weave in dialect words and forms.
   - Slug / Location / Era: anchor the text in place and time.
4. Write the transformed chapter to disk.

If `override.md` is empty or absent, the agent writes the base chapter unchanged.
