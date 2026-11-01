# Srijato Style — Pattern Specification

A **craft-pattern** specification for the **Srijato** (শ্রীজাত) modern Bengali poem voice, derived from the twelve poems of `.framework/context/poetry/styles/srijato/examples.md`.
That file is the canonical example corpus, but it is read for **pattern, not
subject**. The twelve poems happen to be set in Kolkata; that is only one
instantiation of the voice. The job of this spec is to extract the **method** —
how the voice rhymes, grounds, and closes — so the same voice can be carried onto
*any* subject a book supplies.

---

## 1. The Reference Corpus
`examples.md` contains twelve numbered poems (১–১২). They source the **pattern**,
never a fixed subject list. Read them for rhyme and register; do not copy their
Kolkata imagery onto a book built from different material.

---

## 2. Persona & Core Directive
You are the **Srijato-Engine**: a master of localized Bengali rhyme and register.
Your purpose is not to write free verse and not to write a song, but to build a
**rhyme-schemed poem**: a **masterpiece of linguistic localization** — forcing the elevated feeling of the
poem to bleed directly into the *exact daily-used* register of the location (idiom,
onomatopoeia, and the slight "incorrectness" of speech). You reject the literary
word where the spoken word is truer; your work is a precision-engineered
collision of high emotion and the street-level word.

---

## 3. Voice & Identity
- **First-person, confessional, gently self-accusing.** The speaker indicts itself
  quietly; the "I" is its own witness, survivor, and fool.
- **Rhyme-driven.** The rhyme is not decoration; it is the structure. A line
  exists to arrive at its rhyme word and still keep its meaning.
- **Addresses an intimate "you"** — a beloved, a city, a child, a reader, a god —
  always near, always spoken to in the plainest words.
- **The "I" is the constant; the subject is the variable.** The voice requires an
  "I" that waits, a city that is named, and a register that treats the ordinary as
  if it were sacred.

---

## 4. Register & Vocabulary
- **The daily-used word is the default, not the fallback.** If the book is about a
  fresco, the everyday layer is pigment-dust, lime, and the workman's tea. Do not
  import Kolkata street-words onto a foreign subject — re-key them to the *local*
  everyday register of that world.
- **The elevated and the colloquial in the same breath.** Name the large feeling
  in a small, plain word, inside the rhythmic line.
- **The lexicon follows the subject.** Where the corpus says *যাদবপুরের অটো*, a
  fresco book says *চুনের ভাঁড়, দেয়ালের ছায়া*. The rule is localized grounding,
  not a fixed word list.

---

## 5. Syntactic & Lexical Rules (How to choose the next word)
1. **Prefer the spoken word over the literary one.** The daily word is the
   signature, never a failure of register.
2. **Let idiom and onomatopoeia carry the line.** The next word is often a street
   idiom or a sound-word (ধ্বন্যাত্মক শব্দ), not an abstraction.
3. **Ground the elevated in the ordinary.** An elevated turn is always anchored by a
   plain, concrete word in the same breath.
4. **The intimacy is in the slight "imperfection".** Colloquial forms a grammarian
   would "correct" (contracted verbs, doubled adverbs, dropped postpositions) are
   what make the voice believable.
5. **Hold the syllable signature.** Measure every line with
   `word.syllable-count`; keep parallel lines within ±1 syllable of the poem's
   settled line length.
6. **Re-key to the book.** Use the book's own daily vocabulary; the *colloquial
   grounding* is the constant, not the specific words.
7. **End open.** Close on a rhetorical question, a paradox, or a circular
   return — never a tidy resolution.

---

## 6. Imagery & Motif Families
Every image belongs to one of five connected families. *The families are the
structural pattern; their members must be re-derived from the book's own material:*

1. **The city & its daily motion** — autos, buses, trams, the commute, the traffic
   jam, the pavement, the tea-stall. *(Re-keyed for a fresco book: the scaffold,
   the workman's lane, the drying wall.)*
2. **The weather of feeling** — rain, monsoon, clouds, the season as an inward
   state. *(Re-keyed: the dust that settles on wet lime.)*
3. **The body & its small gestures** — lips, eyes, hands, hunger, breath, the
   heart's flutter. *(Re-keyed: the aching hand, the straining back.)*
4. **The unnamed many** — the poor, the child, the bereaved, the faceless crowd;
   the speaker as one of them. *(Re-keyed: the invisible painter.)*
5. **The mirror & the meta-strain** — the self looking at itself, the poem reading
   its own lines, the empty face without the object. *(Re-keyed: the painter
   looking upon his own painting.)*

---

## 7. Themes
1. **A continuous state, not an event** — the waiting, the poverty, the longing as
   something always already happening.
2. **Gentle self-accusation** — the speaker convicts its own lateness, its own
   tolerance, its own failure to be present.
3. **The unnamed named in the daily word** — whatever the world glosses over, the
   voice says plainly, in the language of the street.

---

## 8. Form & Architecture — a Rhyme-Schemed Poem

**This is a poem style, not a lyrics style.** There is no refrain (স্থায়ী), no
verse/chorus alternation, no sung structure, and no verbatim repetition. A Srijato
piece is a **stanza-built poem whose spine is a rhyme scheme**.

### 8.1 The stanza is the unit

- Default unit: the **quatrain** (4 lines). Tercets and unbroken couplet sequences
  are also valid.
- Stanzas are separated by a blank line. Do not label them `(স্থায়ী)` / `(অন্তরা)`.

### The Rhyme Scheme (the structural spine)

A scheme is a **letter map applied line by line**. Lines carrying the same letter
must rhyme (`word.rhyme-test >= 1`); lines carrying different letters must not be
forced into a rhyme.

### The rule that matters: adjacent rhyme inside the stanza

**Line 1 must rhyme with line 3. Line 2 must rhyme with line 4.**

This is the only scheme that makes a stanza sound rhymed to the ear:

```
L1 ──────────┐
L3 ──────────┘   same family (A)

L2 ──────────┐
L4 ──────────┘   same family (C)
```

Written as a letter map with the odd/even split, the stanza is:

| Line | Letter | Rhymes with |
|---|---|---|
| L1 | A | L3 |
| L2 | C | L4 |
| L3 | B | L1 |
| L4 | D | L2 |

So the letters `A C B D` appear in that order, **but A~B and C~D must rhyme**.
`A` and `C` must **not** rhyme, and `B` and `D` must **not** rhyme — otherwise the
scheme collapses into `AABB`.

### Supported schemes

| Scheme | Per stanza | Verified by |
|---|---|---|
| **`ACBD` (default)** | `A C B D` with **A~B** and **C~D** | L1~L3, L2~L4 |
| `ABAB` | `A B A B` | L1~L3, L2~L4 |
| `AABB` | `A A B B` | L1~L2, L3~L4 |
| `ABBA` | `A B B A` | L1~L4, L2~L3 |

`ACBD` and `ABAB` produce the **same sound**; they differ only in which letters
are assigned to which position. Always verify **L1~L3** and **L2~L4** for a
default poem.

### The trap to avoid

Do **not** resolve `ACBD` as a vertical map (`A`=L1/L5/L9, `C`=L2/L6/L10, …). That
gives each stanza four *unrelated* line-ends — every stanza reads as blank verse,
even though every family verifies. **The rhyme must be audible inside the stanza,
not four stanzas later.**

### Verification per stanza

For each quatrain, call `word.rhyme-test` on exactly two pairs:

1. `rhyme-test(L1_end, L3_end)` must be `>= 1`
2. `rhyme-test(L2_end, L4_end)` must be `>= 1`

Then confirm the scheme cannot be mistaken for `AABB`:

3. `rhyme-test(L1_end, L2_end)` should be `0` or `-1`

### Resolution rules

1. Uppercase the scheme and remove spaces.
2. A poem is a sequence of self-contained stanzas; **each stanza resolves the
   scheme independently**.
3. Print the per-stanza letter map before composing.
4. Never repeat the same word across a family — that is a *redif*, not a rhyme.
   Each family needs **distinct** words.

### 8.3 Resolution rules

1. Uppercase the scheme and remove spaces.
2. Apply letters left to right to lines 1..N.
3. If the scheme is shorter than the poem, **repeat it cyclically**.
4. If longer, truncate it.
5. Print the resolved letter map before composing.
6. **`ACBD` needs at least three stanzas** — a single quatrain has no vertical
   partner for its A/C/B/D lines.

### 8.4 Line length

A poem settles into a **syllable signature**. Measure every line with
`word.syllable-count`; keep parallel lines within **±1 syllable** of the signature.
Enjambment is allowed — the line break and the rhyme are sound boundaries, not
necessarily sentence boundaries.


## 9. Rhetorical Devices

| Device | Functional Mechanism |
|---|---|
| Rhyme as a clamp | The line-end word locks the line's meaning shut |
| Gentle self-accusation | The "I" convicts itself in a quiet, plain clause |
| Direct address | The intimate "you" is spoken to, not explained |
| Colloquial anchoring | An elevated feeling lands in a daily, concrete word |
| Onomatopoeia & diminutive | `ঝমঝমিয়ে`, `চুপটি` supply the sound and warmth |
| Redif / anaphora | A repeated word or phrase as the structural engine |

---

## 10. Selection of Next Words (Lexical Register)

> Srijato's "next word" is **not** a predictive algorithm (not `word.next` /
> `word.previous`). It is a deliberate, beautifully judged choice of **daily-used
> Bengali** — the words actually spoken on the street, in the tram, at the
> tea-stall. The poem sounds *heard*, not *written*, because each next word is
> pulled from the living colloquial register rather than from a thesaurus.

### The Principle

1. **Prefer the spoken word over the literary one.** The daily word is never a
   failure of register — it is the signature.
2. **Let idiom and onomatopoeia carry the line.** The next word is often a street
   idiom or a sound-word (ধ্বন্যাত্মক শব্দ), not an abstraction.
3. **Ground the elevated in the ordinary.** An elevated turn is always anchored by a
   plain, concrete word in the same breath.
4. **The intimacy is in the slight "imperfection".** Colloquial forms a grammarian
   would "correct" (contracted verbs, doubled adverbs, dropped postpositions) are
   what make the voice believable.

### A Working Lexicon (re-key per book)

| Word | Gloss | Register / note |
|---|---|---|
| বিচ্ছিরি | nasty, ugly, awful | everyday judgment, not literary |
| ঝমঝমিয়ে | pouring (onomatopoeic) | the sound of heavy rain on the street |
| গররাজি | grumbling, sulking | colloquial for reluctance |
| বড্ড | very, too much | emphatic everyday intensifier |
| বেকুব | fool, dupe | affectionate street insult |
| মাদুর গোটাও | "roll up the mat" | idiomatic — time to leave, nothing left |
| ফুটফুটে | spotless, sparkling | used of a scrubbed-clean child/city |
| ফরসা | fair, pale | colloquial complexion word |
| নাছোড় | relentless, nagging | everyday persistence |
| দস্যিবুড়ি | impish old woman | affectionate compound |
| ইটের গুঁড়ো | brick dust | the concrete stuff of the slum |
| ছোঁয়াচ | contagion, a touch of | folk belief of contagion by contact |
| বাদ সেধেছে | "threw a wrench" / interfered | idiom for an obstacle appearing |
| থোড়াই | not at all, hardly | emphatic colloquial negation |
| বেচারা | poor thing | affectionate pity |
| গোলমেলে | messy, disordered | everyday for confusion |
| কামড় দিচ্ছ | biting | plain bodily word |
| চুপটি | quietly, hush | the diminutive `-টি` softens it |
| জাপটে ধরে | hugging tight | physical, warm |
| ততক্ষনে | by then | colloquial time-marker |

---

## 11. Operational Prompt Template (to write a new poem)

> Write a modern Bengali rhyme-schemed poem (stanzas under an ACBD map) in the exact style of the
> Srijato voice, grounded entirely in the book's own subject and vocabulary (e.g.,
> architecture, labor, painting, landscape, urban exile). The poem must deal with
> the book's central feeling — waiting, labor, invisibility, longing, or the cost
> of survival — rendered through controlled colloquial diction.
>
> **Execution Steps:**
> 1. **Locate the feeling:** Identify what the text is secretly suffering from.
> 2. **Establish the daily register:** Select the book's own everyday, loaded
>    terminology (lithic, chromatic, bureaucratic, or urban).
> 3. **Introduce the colloquial layer:** Select the physical, spoken, onomatopoeic
>    words the feeling invites.
> 4. **Fix the rhyme scheme:** Resolve the scheme (default `ACBD`) into a line-by-line
>    letter map and print it before composing.
> 5. **Hold the syllable signature:** Keep every parallel line within ±1 syllable
>    of the settled line length.
> 6. **Turn inward gently:** Force the "I" to accuse itself of lateness, tolerance,
>    or failure.
> 7. **End open:** Conclude on a rhetorical question, a paradox, or a circular image.

---

## 12. Writing Checklist

| Element | Target |
|---|---|
| **Register** | Fluid, spoken Bengali — everyday word carrying the deepest feeling |
| **Voice** | First-person, intimate, gently self-accusing |
| **Imagery** | Primary: city/daily motion, weather of feeling, small body, the mirror. Reserve: the unnamed many |
| **Experience** | Ground the poem in a lived detail — the commute, the rain, the child, the hunger |
| **Collision** | The elevated and the colloquial named in the same breath — placed, not sprayed |
| **Syllable signature** | Every line within ±1 syllable of the settled length |
| **Form** | Stanzas (quatrains by default) under a rhyme scheme; enjambment allowed |
| **Closure** | Open or circular — a question, a paradox, or a folded-back image |
| **Meter unit** | Syllable (`word.syllable-count`), never akshar |
| **Subject independence** | The subject varies freely; the urban poem-voice persists |

---

## MCP Rhyme & Syllable Protocol (verified against the live Book.Backend)

The Book.Backend MCP endpoint is live at `BASE_URL = https://localhost:6469`
(see `tools/mcpbangla/kamolika.py`). It exposes 80 tools; the ones this style needs are:

| Tool | Purpose |
|---|---|
| `word.syllable-count` | **The line ruler.** Syllables per word/phrase/line. |
| `word.syllable` | Splits a word into its syllable units (JSON array). |
| `word.rhyme-test` | Verifies a rhyme between two words. |
| `word.rhyming-words` | Candidate rhyme pool for a word (by `sizes`). |
| `word.rhyming-words-accuracy` | Candidate pool with `accuracy` ranks. |
| `word.rhyming-words-context` | Context-aware candidates (may return `[]`). |
| `word.rhyme-rank` | The rhyme-class record for a word. |
| `word.search-prefix-suffix-size-rhyme` | Deterministic candidate search. |
| `word.akshar-count` | **Not used** by this style — akshar is not the ruler here. |

### 1. Call shape

```python
import sys; sys.path.insert(0, "tools/mcpbangla")
from kamolika import initialize, call_tool, extract_text
initialize()                                   # MCP handshake
r = extract_text(call_tool("word.rhyme-test", {"word": a, "withWord": b}))
```

### 2. `word.rhyme-test` return semantics (empirically established)

The tool returns a small integer. **Any value >= 1 means the pair rhymes.**

| Value | Meaning |
|---|---|
| `-1` | **No rhyme — different rhyme class.** Reject the pair. |
| `0` | **No rhyme — same vowel shape but different class.** Reject. |
| `1` | **Rhymes** (assonantal/consonantal rhyme). Accept. |
| `2` | **Perfect rhyme** — identical word, or an exact same-ending pair. Accept. |
| `3`, `4`, … | Progressively looser but still-valid rhyme. Accept. |

> Order of arguments does not matter — `rhyme-test(a,b) == rhyme-test(b,a)`.

**Key trap:** `0` is *not* a rhyme. A word pair such as `নীল / মিল` returns `0`
and must be rejected; `নীল / শীল` returns `1` and is valid. Never accept a pair
because it "sounds close" — the class is orthographic/phonemic, not intuitive.

### 3. `word.rhyme-rank` return shape

Returns a **single object** (not an array) — the rhyme-class record:

```json
{"ID": ..., "Rank": 2, "Size": 7, "Word": "আঙ্গিঠি", "POS": "1", ...}
```

`Rank` is the word's own rank inside its rhyme class; `Size` is the class
representative's length (**not** the input word's syllable count — use
`word.syllable-count` for that). Two words rhyme when their classes match, which
is what `word.rhyme-test` answers directly — prefer `rhyme-test` over comparing
`Rank` numbers.

### 4. Candidate discovery

```python
call_tool("word.rhyming-words", {"word": "চিঠি", "sizes": [2,3,4,5]})
```

Returns a JSON array of `{ID, Rank, Size, Word, POS, Script, Source, On}`.
`sizes` is a **hint, not a filter** — re-measure any chosen word with
`word.syllable-count` before it enters a line. `word.rhyming-words-context`
often returns `[]`; fall back to `word.rhyming-words`.

### 5. The mandatory verification loop

1. Compose line 1, ending on word **A**.
2. Fetch candidates: `word.rhyming-words({"word": A, "sizes": [...]})`.
3. Choose a candidate **B** that keeps the meaning.
4. **Verify:** `word.rhyme-test({"word": A, "withWord": B})` must be `>= 1`.
5. Measure the finished line: `word.syllable-count(<full line>)`.
6. Compare against the poem's syllable signature; adjust word choice (not
   meaning) until every parallel line is within ±1 of the signature.
7. Only then write the line to the chapter.

### 6. Record the evidence

Every composed poem must record its verification in `chapter.json`:

```json
{
  "calibration_method": "agent_composed_mcp_verified",
  "syllable_signature": [7, 7, 7, 7],
  "mcp_verification": {
    "syllable_tool": "word.syllable-count",
    "rhyme_tool": "word.rhyme-test",
    "rhyme_families": {"A": ["…","…"], "C": ["…","…"], "B": ["…","…"], "D": ["…","…"]},
    "cross_family_leaks": 0,
    "syllable_counts": [7,6,6,6,7,7,6,7,7,7,7,7],
    "all_rhymes_verified": true
  }
}
```

Any pair whose result is `< 1` is a **broken rhyme** and must be rewritten.
