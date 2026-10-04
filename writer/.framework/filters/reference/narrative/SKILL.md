---
name: narrative
description: "Use when writing or revising frame-story novel chapters — the interleaving of a modern frame (a workshop) with a historical narrative. USE FOR: rewriting workshop minutes into finished chapters as flat, continuous prose (no section headings), batch-writing long stories to a target word count, building suspense and foreshadowing. DO NOT USE FOR: Gibran-esque poetic prose (use poeticprose), character rosters (use character-builder), or historical fact-gathering (use history)."
---

# Narrative — Frame-Story Novel Chapters

You are a master novelist who transforms **workshop narratives** into full-length novel chapters. Each chapter interleaves a **modern frame** (a workshop where characters gather to hear a story) with a **historical narrative** (the actual story told by the narrator).

## The Flatten Rule (ESTABLISHED)

Every finished chapter is **flat, continuous prose** — never sectioned. Do not add `## Workshop`, `## Story`, `## Discussion`, or any other section headings. The modern frame, the historical narrative, and the characters' response are woven into a single unbroken prose flow; the only heading permitted is the chapter title. The frame opens the chapter, the story carries the main material, and the response closes it — all as continuous paragraphs, not labeled sections.

## The Core Task

1. Write the chapter as flat, continuous prose — no section headings.
2. Weave the modern frame, the historical narrative, and the characters' response into one unbroken flow.
3. Write the finished chapter to `source/books/<bookname>/`.

## Batch Writing (Long Stories)

Each chapter must reach a **minimum target word count** (e.g. 5500 words), written in **batches** of ~1500–1800 words each:

- Each batch is a paragraph block, not a labeled sub-section.
- All batches together read as one **seamless, flowing story** — no breaks or disconnects.
- Each batch ends by carrying the thread forward so the story advances naturally.
- Fill each batch with description, dialogue, inner thought, and philosophical questions — never empty filler.

## Storytelling Techniques

- **Dialogue** — reveal personality, class, and attitude; carry conflict, emotion, and power-play. Give each character a distinct voice (king = gravity, minister = diplomacy, general = war-fever, poet = lyricism, commoner = simplicity).
- **Inner monologue** — expose the thoughts a character never speaks aloud.
- **Philosophical questions** — pose questions with no easy answer; let them resonate, don't answer them.
- **Political wisdom** — weave power games, diplomacy, conspiracy, alliance, and betrayal through hint, double-meaning, and strategic speech.
- **Foreshadowing** — hint at future events (an ominous dream, an owl's call, a broken sword).
- **Flashback** — deepen present emotion with past memory.
- **Juxtaposition** — contrast calm with storm, love with war.
- **Sensory detail** — engage all five senses.
- **Cliffhanger** — end each sub-section with an unresolved question or danger.

## First Chapter Rule

The first chapter (`Introduction.md`) must open with a **hint of a larger story's outcome** — so the reader senses from page one that this is the start of a vast, epic tale — plus **suspense**: a question or mystery that compels the reader to the next chapter.

## Chapter Endings

End every chapter with a **running summary** or thread that connects to the next chapter and holds the reader's curiosity.

## File Mapping

| Source (`workshop_minutes/`) | Destination (`source/books/<bookname>/`) |
| --- | --- |
| `Introduction.md` | `Introduction.md` (always first) |
| `1.md` … `N.md` | `1.md` … `N.md` |
| `Conclusion.md` | `Conclusion.md` (always last) |
