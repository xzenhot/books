---
name: lyrics
description: Modern Bengali song lyrics (আধুনিক গান), in the tradition of Salil Chowdhury, a song-structured poem with a repeating refrain (স্থায়ী) and rhyming verses (অন্তরা), measured by syllable count via the MCP endpoint (word.syllable-count); akshar count does not apply. Reached through the write agent's poetry route; never executed directly.
---

# lyrics Skill (আধুনিক গান / Bengali song)

> Voice tradition: the Salil Chowdhury line — the refrain that pivots, the verse
> that answers it, and a next word chosen for its sound in the mouth.

Use this skill to compose a **modern Bengali song lyrics** (আধুনিক গান) — a
song-structured poem built on a repeating **refrain** (স্থায়ী / মুখড়া)
interleaved with rhyming **verses** (অন্তরা) and, where the song calls for it, a
**bridge** (সঞ্চারী) and **conclusion** (আভোগ). It is not a fixed metrical form:
line lengths flow with the music, but they still follow an internal pattern of
syllables, rhyme, and stanza shape. The lyrics sings; it does not argue.

## Fundamental Paradigm

> **The agent composes. MCP measures. The agent adjusts.**

MCP is a ruler — it measures, never writes. Here the ruler is the **syllable
count** (`word.syllable-count`), not the akshar count. The agent authors every
line as natural, singable Bengali, then uses MCP to check each line's syllable
count (and, where rhyming, the rhyme relation) and makes word-level edits until
the line fits the song's syllable pattern. MCP is never asked to generate or
complete a line. For lyrics, **akshar count does not matter** — do not measure or
calibrate it.

## Invocation

```text
/book <bookname> lyrics <chapter> [<target_syllables>] [replace]
```

This skill is never executed directly by a workflow. It is reached through the
**write agent** (`.framework/agents/write/agent.md`), which resolves the form and
routes the poetry request to this skill. `lyrics` selects the song-lyrics form
over the default flat poetic-prose path.

## Form Contract

A modern song lyrics is a **pattern**, not a fixed metre. There is no hard line
lock; instead the song establishes a **syllable signature** from its refrain and
keeps that signature consistent across parallel lines and verses.

| Property | Value |
|---|---|
| Structure | Refrain (স্থায়ী / মুখড়া) + 2–4 verses (অন্তরা), refrain repeated verbatim; optional bridge (সঞ্চারী) and conclusion (আভোগ) |
| Syllables per line | **8** (default reference) — a natural singing length; lines may run 6–10 where the melody or enjambment requires, as long as the pattern stays consistent |
| Syllable signature | The refrain's syllable shape is echoed by parallel verse lines (same position = same count) |
| Refrain | One fixed 2–4 line passage, repeated verbatim between verses |
| Rhyme | Encouraged (modern songs rhyme); end-rhymes verified via `word.rhyme-test` |
| Voice | Musical, image-rich, conversational; address to a beloved, muse, place, or the listener |

## Language Rule — Bengali Only

- Read, compose, and write in Bengali. The finished lyrics is Bengali script.
- Never use English rhyme intuition or romanization.
- Every syllable count must come from `word.syllable-count`; do not count akshars.
- If an MCP result contains non-Bengali or romanized words, discard it.

## MCP Protocol

All MCP traffic uses `tools/mcpbangla/kamolika.py` (HTTP client for the Book.Backend
endpoint, `BASE_URL`). Call tools with `call_tool(name, arguments)` and read
results with `extract_text(result)`. Do not launch a stdio server and do not open a
stdio session.

| Tool | Use |
|---|---|
| `word.syllable-count` | Measure syllable count of any word, phrase, or full line (the lyrics ruler) |
| `word.syllable` | Split a word/phrase into its syllables to verify vowel nuclei and stress |
| `word.rhyme-test` | Confirm a rhyme relation (positive result required when rhyming) |
| `word.rhyming-words` / `-context` / `-accuracy` | Fetch rhyme candidates for a family |
| `word.previous` / `word.next` / `word.next-context` | Extend or replace a word forward/backward |

`word.akshar-count` is **not** used by this skill. lyrics is measured by syllable,
never by akshar.

## Structure

### Refrain (স্থায়ী / মুখড়া)

The refrain is the song's emotional and melodic anchor — a short passage (2–4
lines) that returns verbatim between verses. It carries the song's title image or
hook. Compose it first: the refrain's syllable signature (the count of each line
in order) becomes the template that parallel verse lines echo. The refrain
repeats exactly; do not paraphrase it on repetition.

### Verses (অন্তরা)

Each verse advances the situation, image, or address one step. The verse is
sung to the same tune as the refrain, so its line-for-line syllable counts
should mirror the refrain's signature. Prefer concrete nouns and active verbs;
let metaphor carry abstraction rather than explaining it. Verses typically rhyme
internally (AABB, ABAB, or free assonance) and lead back into the refrain.

### Bridge and Conclusion (সঞ্চারী ও আভোগ) — optional

For a fuller modern song, a **bridge** (সঞ্চারী) shifts the mood or key once —
a change in syllable signature or rhyme scheme is allowed here as long as it
resolves. The **conclusion** (আভোগ) closes the song, often re-stating the
refrain's hook in a final, quieter or heightened form. These are optional; add
them only when the source's emotional arc calls for them.

### Syllable Signature

The signature is the ordered list of per-line syllable counts taken from the
refrain. Example: a refrain of three lines at `8-8-6` sets the signature
`8-8-6`. Each verse's corresponding line positions should match those counts
(line 1 → 8, line 2 → 8, line 3 → 6). A bridge may deliberately break the
signature before the song resolves back to it.

## Composition Workflow

### Phase 0 — Read and Understand the Source

1. Read the chapter's content: `chapters/<n>/chapter.md` first, falling back to
   `chapters/<n>/segments/1/writer/chapter.md` when the root draft is empty.
2. Read `book.json` for the chapter `chapter_summary` and the book
   `book_summary`, `gist`, and `era`.
3. Extract the **emotional core** and the single most resonant image before
   writing a line.

### Phase 1 — Compose the Refrain

Write the refrain as the song's anchor (2–4 lines). Measure each line with
`word.syllable-count` and settle the line lengths into a consistent pattern
(default reference 8 per line). Record that pattern as the syllable signature
for the verses. Adjust with delete / insert / replace via `word.next`,
`word.previous`, `word.next-context`; use `word.syllable` to inspect vowel
nuclei when a count feels off.

### Phase 2 — Compose the Verses

Write 2–4 verses that advance and intensify the refrain's situation, echoing the
refrain's syllable signature line-for-line. Calibrate each line with
`word.syllable-count`; the count of verse line *i* should match the refrain line
*i* count. Add a bridge (সঞ্চারী) or conclusion (আভোগ) only if the emotional arc
requires it.

### Phase 3 — Rhyme Pass

Modern Bengali songs rhyme; run this pass unless the source is explicitly
unrhymed. Build a rhyme bank per family via `word.rhyming-words*` and confirm
every end word with `word.rhyme-test` before it enters the lyrics. Keep the
rhyme on the line's final stressed syllable; the syllable signature governs
length, the rhyme governs sound.

### Phase 4 — Write and Record

Write the finished lyrics to `chapters/<n>/chapter.md`, archive the prior draft to
`chapters/<n>/history/`, and record in `chapter.json`:

```json
{
  "form_skill": "lyrics",
  "syllable_target": 8,
  "syllable_signature": [8, 8, 6],
  "refrain_lines": 2,
  "verse_count": 3,
  "bridge": false,
  "rhyme_scheme": "AABB",
  "calibration_method": "agent_composed_mcp_verified"
}
```

The `syllable_signature` must be the actual ordered per-line syllable counts of
the finished refrain, verified by `word.syllable-count`.

## Constraints

- Never use MCP to generate or complete a line; MCP measures only.
- Never compute syllable counts natively; always via `word.syllable-count`.
- Do **not** use `word.akshar-count` here — akshar count does not matter for lyrics.
- Never alter a line's central meaning to hit a syllable target.
- The refrain must repeat verbatim — never paraphrase it on repetition.
- Keep the syllable signature consistent across parallel verse lines.
- Work only inside `workspaces/pipeline/<bookname>/`.
- Valid only for books with `form: poetry`.


## Example: 
** By Salil Chowdhury ** , from *Chhaya O Chhobi* (1970):


আজ–তবে এইটুকু থাক।
বাকি কথা পরে হবে।
ধূসর ধূলির পথ–
ভেঙে পড়ে আছে রথ–
বহুদূর– দূর যেতে হবে।
আজ তবে এইটুকু থাক?
বাকি কথা পরে হবে   

সবুজ সবুজে মেশা নীল নীলিমায়–
পাবে না আমায়।
গোধুলীর ছায়াপথে
খুঁজো না আমায়।

শরতের কোন এক নাম না জানা গাঁয়
শিউলীর ফুল যেথা
ঝরে ঝরে যায়–
কিশোরী মনের মত–
দু’টি চোখে অবনত–
না গাওয়া যে গান হয়ে রবে…
আজ তবে এইটুকু থাক?
বাকি কথা পরে হবে।

তখন অন্য মন অন্য আশা,
অন্য ভাষা।
জানি না কি রূপ নেবে ভালবাসা।
তখন অন্য মন অন্য আশা,
অন্য ভাষা।
জানি না কি রূপ নেবে ভালবাসা।
তুমি যদি মনে মনে মগ্ন হয়ে–
ফুলের শিশু হয়ে রও ঘুমিয়ে।
আমি সূর্যের হয়ে 
তোমাকেই যাব ছুঁয়ে–
সে কথা কি ভুল হয়ে যাবে?

আজ তবে এইটুকু থাক?
বাকি কথা পরে হবে।

*Explanation*: 


First Stanza"

আজ–তবে এইটুকু থাক।
বাকি কথা পরে হবে।
ধূসর ধূলির পথ–
ভেঙে পড়ে আছে রথ–
বহুদূর– দূর যেতে হবে।

Here : 
First two lines are the refrain, repeated verbatim after each stanza. The refrain is a short, image-rich anchor for the lyrics.
Line#3 and #4 are the first stanza, which intensifies the refrain's image. Line#5 is the stanza's closing line, which leads back to the refrain. They are rhymed internally (AABBA) but do not rhyme with the refrain.
And Line#2 "পরে হবে।" and Line#5 "দূর যেতে হবে।" are parallel in cadence and meaning, but do not rhyme.


সবুজ সবুজে মেশা নীল নীলিমায়–
পাবে না আমায়।
গোধুলীর ছায়াপথে
খুঁজো না আমায়।

Here: This is the second stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 4 lines long, and the last line leads back to the refrain.
Rhyme Scheme: Lines 1 and 2 rhyme (A), lines 3 and 4 rhyme (B). The stanza does not rhyme with the refrain.


শরতের কোন এক নাম না জানা গাঁয়
শিউলীর ফুল যেথা
ঝরে ঝরে যায়–

Here: This is the third stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 3 lines long, and the last line leads back to the refrain.
Line#1 and #3 rhyme (A), line#2 does not rhyme with the others (B). The stanza does not rhyme with the refrain.

কিশোরী মনের মত–
দু’টি চোখে অবনত–

Here: This is the fourth stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 2 lines long, and the last line leads back to the refrain.
Line#1 and #2 rhyme (A). The stanza does not rhyme with the refrain.


না গাওয়া যে গান হয়ে রবে…

Here: This is the fifth stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 1 line long, and the last line leads back to the refrain.
Rhyme Scheme: It comes back again just to rhyme with "পরে হবে".

আজ তবে এইটুকু থাক?
বাকি কথা পরে হবে।
Here: This is the refrain, repeated verbatim after each stanza. The refrain is a short, image-rich anchor for the lyrics.

তখন অন্য মন অন্য আশা,
অন্য ভাষা।
জানি না কি রূপ নেবে ভালবাসা।

Here: This is the sixth stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 3 lines long, and the last line leads back to the refrain.
Rhyme Scheme: Lines 1 and 2 rhyme (A), line#3 does not rhyme with the others (B). The stanza does not rhyme with the refrain.


তুমি যদি মনে মনে মগ্ন হয়ে–
ফুলের শিশু হয়ে রও ঘুমিয়ে।
Here: This is the seventh stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 2 lines long, and the last line leads back to the refrain.
Rhyme Scheme: Lines 1 and 2 rhyme (A). The stanza does not rhyme with the refrain.

আমি সূর্যের হয়ে 
তোমাকেই যাব ছুঁয়ে–
সে কথা কি ভুল হয়ে যাবে?

Here: This is the eighth stanza. It intensifies the refrain's image, but does not rhyme with it. The stanza is 2 lines long, and the last line leads back to the refrain.
Rhyme Scheme: Lines 1 and 2 rhyme (A). The stanza does not rhyme with the refrain. "ভুল হয়ে যাবে?" rhymes with "পরে হবে।" in the refrain.

আজ তবে এইটুকু থাক?
বাকি কথা পরে হবে।

Here: This is the refrain, repeated verbatim after each stanza. The refrain is a short, image-rich anchor for the lyrics. Just a formality.

## Audit Tooling

`tools/mcpbangla/verse.py` audits this form mechanically — use it instead of
re-deriving checks inline:

```bash
python tools/mcpbangla/verse.py audit <file> --form lyrics
```

It measures every line via MCP and fails the run on any contract violation.

## Report Format

```
lyrics Report
Book    : <bookname>
Chapter : <n>
Mode    : lyrics (refrain + verses, syllable signature <sig>)

Refrain : <refrain text>
Signature: <ordered per-line syllable counts>

Per-verse:
  <verse lines with [<n>syl ✓] and rhyme letters>

Summary:
  Lines          : <total>
  Calibrated     : <count>/<total>
  Rhymes verified: <count>
  Needs review   : <lines>

Next steps:
  /book <bookname> write <n>      # promote to chapter output
```
