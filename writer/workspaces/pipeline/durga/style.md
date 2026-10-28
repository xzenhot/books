<!-- style-provenance
style: poyar
book: durga
form: poetry
meter: syllable-14
grounded_from: .framework/context/poetry/styles/poyar/{sample.txt,signature.md,style.md}
generated_at: 2026-10-29T00:20:00Z
book_updated_at: 2026-10-27
human_edited: false
-->

# Poyar Style Grounded in 'Durga' (দুর্গা: এর কবিতা)

## Authority Note

This is a **book-grounded instantiation of the Poyar style**. The primary
authority is the canonical corpus `.framework/context/poetry/styles/poyar/sample.txt`
(**form, rhyme, and register**), distilled in
`.framework/context/poetry/styles/poyar/signature.md`, and specified in full in
`.framework/context/poetry/styles/poyar/style.md`. Where these disagree, the
sample wins; where the sample cannot decide, the signature decides.

The corpus describes a **method** — how a couplet pairs, rhymes, measures and
flows. Its **subject matter** (the Yamuna, the Pandavas, the village river, the
grandmother's grave) is not this book. This document carries the method onto the
Durga Puja cycle; it invents no new form.

## Form Contract (binding)

| Property | Value |
|---|---|
| Unit | **Two-line couplet** (দ্বিপদী) |
| Line order | Line 1 opens; line 2 closes and rhymes |
| **Meter unit** | **Syllable** — never akshar, never matra |
| **Line length** | **Exactly 14 syllables**, `4 + 4 + 4 + 2` (a `+1` close is legal; 2 preferred) |
| Ruler | `word.syllable-count` **per word, summed** |
| Rhyme | **L1 ~ L2 inside each couplet**, `word.rhyme-test >= 1` **and** an identical final rhyme unit |
| Cross-couplet rhyme | **None** — L2~L4 and L1~L4 carry no obligation |
| Distinct ends | L1 end ≠ L2 end (identical is a *redif*; fail it) |
| Flow | Every couplet continues the previous sentence as a real sentence |
| Language | Bengali |

## Register — Daily-Used Spoken Bengali

The corpus is written in the plain spoken tongue and moves by what is **said**, not
by what is ornamented. Durga's register is the same: a person standing in the
crowd on Ashtami, not a priest reciting.

- Prefer the spoken word over the literary one.
- Let idiom and onomatopoeia carry a line (`ঝমঝমিয়ে`, `ঢকঢক`, `বড্ড`, `থোড়াই`).
- Ground every elevated turn in a plain, concrete word in the same breath.
- Keep the colloquial "incorrectness" (`ততক্ষনে`, `চুপটি`).

### The syllable tension — Durga's own vocabulary

Colloquial words are short, so a line built only from them falls under 14. Fix it
by **adding another everyday clause**, never by inflating a word into its tatsama
form:

```text
short (9):  অঞ্জলি মানে শুধু আশা
ok   (14):  অঞ্জলি মানে সারাক্ষণ পাহারা আশা      ← added a spoken clause
bad:        অঞ্জলি মানে শুধুই আশা                 ← literary inflation; forbidden
```

## Persona & Voice

You are the **poyar-maker of this puja** — a run of self-rhyming couplets bound by
one continuous voice. You are one of the crowd, not above it: your hands are in the
offering, your shoulders are against other shoulders, your ear is on the dhak.

- **First person, confessional, ordinary.** You are the one waiting, watching,
  carrying, letting go.
- **Spoken, not chanted.** The address to the goddess is a household address —
  `মা`, not a liturgical vocative.
- **The couplet is the atom.** Each pair is closed by its own rhyme; the poem is
  held together by the argument, not by the sound.

## Book Grounding (Durga)

- **Premise.** The Durga Puja cycle — Mahalaya's first dawn to Bijaya's dusk, and
  the year's long wait in between.
- **Setting.** Kumortuli's wet clay lanes; the shiuli-strewn steps; the kash fields
  along the river; the drum-filled pandal; the immersion ghat.
- **Era.** Mythic time folded into present-day Bengal.
- **Thematic threads.** আগমন ও অপেক্ষা; শিল্প ও নির্মাণ; ভক্তি ও শক্তি;
  শব্দ ও ছন্দ; বিদায় ও প্রত্যাবর্তন.
- **The book's vocabulary.** শিউলি, কাশফুল, কুমোরটুলির মাটি, খড়ের কাঠামো,
  চক্ষুদান, ঢাকের বোল, শাঁখ, সিঁদুর, অঞ্জলি, নবপত্রিকা, আরতি, বিসর্জন,
  বিজয়ার গোধূলি, "আসছে বছর আবার হবে".

## Imagery Families (re-keyed from the corpus pattern)

The corpus grounds its abstractions in a river, a field, a house and a body. This
book grounds them in the puja's own materials:

1. **Clay & making** — wet earth, straw, bamboo, the painter's brush, the drying
   idol. (Corpus analogue: the field and the plough.)
2. **The crowd & the row** — shoulders, queues, upturned palms, the one hand out of
   time. (Analogue: the ferry crossing, the bathing ghat.)
3. **Sound** — dhak, shankha, ghanta, the crowd's single exhalation, the silence
   after arati. (Analogue: the shalik flock, the jackal's call.)
4. **The house & return** — the door, the stair, the courtyard, the empty pandal,
   the year's waiting. (Analogue: the grandmother's grave under the pomegranate.)
5. **The mirror-strain** — the idol watching the devotee; the devotee's own face in
   the idol's painted eye.
6. **What is carried** — flowers, bel leaves, vermillion, water, ash, an unspoken
   memory.

## Rhyme Protocol

- `word.rhyme-test >= 1` is **necessary, not sufficient**.
- `0` is **not a rhyme** (same vowel shape, different class) — reject.
- The two end words must share an **identical final rhyme unit** (final syllable,
  each consonant folded to its বর্গ row). `শব্দ/গন্ধ` returns `1` and is **weak**.
- If line 2 cannot land a strong rhyme, **rework line 1** — shuffle or replace it.
- Verify: `python tools/mcpbangla/verse.py rhyme A B` (exit 0 = strong).

### Durga rhyme families that work

| Family | Members |
|---|---|
| `-া/কা` | বাঁকা, দেখা, শেখা, রাখা, ঢাকা |
| `-ে/কে` | থাকে, রাখে, ভাঙে, লাগে, জাগে |
| `-া/শা` | আসা, কাঁসা, ভাষা, আশা, বসা |
| `-ুর` | সিঁদুর, রোদ্দুর, দুপুর, ঠাকুর, মৃত্যুর |
| `-া/রা` | শিরা, করা, ধরা, যারা, তারা |
| `-ে/শে` | শেষে, বেশে, আসে, হাসে, ভাসে |
| `-ি/ড়ি` | বাড়ি, পাড়ি, দাড়ি |

## Flow Rule

Rhyme binds a couplet; **meaning must bind the poem**. No cross-couplet rhyme
carries the sound, so the sense carries everything:

- Each couplet continues the previous sentence or thought.
- Each couplet is a real sentence, not a decorative fragment.
- Each couplet advances the argument one step.
- Couplets that stand as isolated vignettes are broken even when every rhyme passes.

## Transformation Method

1. **Fix the through-line.** Name the single movement the poem makes (not the topic).
2. **Fix the end words first.** Choose an end word the meaning needs, find a
   *strong* partner, and only then write the lines.
3. **Write line 1** as a spoken statement ending on A; measure: exactly 14.
4. **Write line 2** closing on B as the same sentence continued; measure: exactly 14.
5. **Rework line 1** — never the rhyme — when the pair will not land strong.
6. **Vary the rhyme class every couplet.** Do not chain the sound forward.
7. **Audit** before writing: `verse.py audit <file> --form poyar` must print PASS.
8. **Vary the subject** from the registry below, chapter to chapter.

## Subjects Registry (chosen from this book's storyline)

1. **অপেক্ষা** — the year's wait, the door watched, the letter not sent.
2. **নির্মাণ** — clay, straw, brush, the maker's hand as instrument.
3. **ভক্তি** — the offered hand, the unspoken word, the shared silence.
4. **শক্তি** — the myth's violence held inside a household festival.
5. **আগমন** — arrival as weather, as scent, as sound approaching.
6. **বিদায়** — immersion, the empty pandal, the promise of return.
7. **উৎসবের শরীর** — the crowd as one body, its breaths and its failures.
8. **প্রত্যাবর্তন** — the circular year, "আসছে বছর আবার হবে".

## Good Anchors

- Wet clay under the fingernail; the smell of straw and varnish.
- Shiuli on a concrete stair at 5 a.m.; kash leaning over a rail line.
- The dhak's first beat, and the drop when it stops.
- A brass bowl of water going warm in a crowded hall.
- The one hand in the row that is out of time.
- Scent of vermillion and coconut oil on a sleeve.
- The river's brown water closing over painted eyes.
- The empty pandal's echo a week later.

## Output Rules

- **Verse, one line per line** — never merged into prose paragraphs.
- Exactly two lines per couplet, a blank line between couplets.
- The chapter title is the only heading (`# {chapter_title}`).
- No `## সারাংশ` block, no caesura marks, no annotation, no explanation.
- No moralizing close, no tidy conclusion; end on an image or a return.
- Every line exactly 14 syllables; every couplet a strong rhyme.

## Forbidden

- Akshar or matra measurement (poyar counts syllables).
- A literary (tatsama) word used only to reach 14 syllables.
- A rhyme accepted on `rhyme-test` alone without the strength check.
- An identical end pair (redif).
- Rhyme chained across couplets.
- Any prose sentence inside the poem body.
