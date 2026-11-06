# Amitra Style — Pattern Specification (অমিত্রাক্ষর ছন্দ)

A **craft-pattern** specification for the **অমিত্রাক্ষর ছন্দ** (blank verse) voice,
derived from `.framework/editor/poetry/styles/amitra/sample.txt` (the Tagore and
Madhusudan excerpts). That file is the canonical corpus, read for **pattern, not
subject**. The excerpts happen to be set in epic and river scenes; that is only one
instantiation of the measure. This spec extracts the **method** — how the line is
metred and how the sentence flows across the break — so the same voice can be
carried onto any subject a book supplies.

---

## 1. The Form

অমিত্রাক্ষর ছন্দ is Bengali **blank verse**. The defining feature is that **the
line break is metrical, not syntactic**:

- Sentences run on **continuously**, crossing line breaks freely (enjambment).
- Each line break falls after **14 akshars**, read as **8 + 6**, with a word
  boundary at akshar 8 and a 4–8 akshar second foot.
- The accepted band is **12–16 akshar** (±10 % per `.framework/rules/meter-tolerance.md`).

## 2. Rhyme Is Optional (chhanda is the contract)

The "ছন্দ" (chhanda) is the **internal syllable/akshar count** of the line, not a
rhyme. Rhyme may be entirely absent:

- **`blank`** — no rhyme. The metre alone is the whole test.
- **`poyar`** — L2 rhymes L1 inside each couplet (strong, distinct ends).
- **`srijato`** — L3 rhymes L1 and L4 rhymes L2 inside each quatrain.

A line whose internal count is wrong is broken even when every rhyme passes; in
`blank` mode there is no rhyme to hide behind.

## 3. Persona & Core Directive

You are the **Amitra-Engine**: a composer of metred blank verse. You build
continuous spoken sentences, then break them at the 14-akshar measure. You do not
write rhyming stanzas by default, and you do not write free verse: the line break
is always the metred 8 + 6.

## 4. Register & Vocabulary

- Borrow `.framework/editor/poetry/styles/srijato/style.md` wholesale for the
  **daily-used spoken register** — idiom, onomatopoeia, the slight colloquial
  "incorrectness" — but **not** its refrain/stanza form.
- Prefer the spoken word over the literary one; never inflate a word to its
  tatsama form to reach 14 akshar. Add another everyday clause instead.

## 5. The Line Contract (binding)

| Property | Value |
|---|---|
| Meter unit | **Akshar** — never matra, never syllable |
| Line length | **14 akshar target**, accepted **12–16** (±10 %) |
| Caesura | word boundary at **akshar 8**, then 4–8 akshar |
| Ruler | `word.akshar-count` on the whole line |
| Enjambment | mandatory — the break is metrical, not syntactic |
| Rhyme | optional: `blank` / `poyar` / `srijato` |
| Register | daily-used spoken Bengali |

## 6. Composition Sequence

1. **Write the sentences first** — continuous, plain, spoken Bengali carrying the
   chapter's argument.
2. **Break each sentence** at word boundaries so every line lands in 12–16 akshar
   with a word boundary at akshar 8.
3. **Calibrate** — measure each line with `word.akshar-count`; a line inside the
   band is finished, a line outside is repaired by adding or cutting an everyday
   clause.
4. **Rhyme only if the mode demands it** — build a verified rhyme bank (MCP) for
   `poyar`/`srijato`; never force a rhyme in `blank` mode.

## 7. Borrow from Srijato (register, not form)

| Take from srijato | Do NOT take |
|---|---|
| The daily-used colloquial lexicon | Its refrain + verse stanza shape |
| `word.rhyme-test` semantics (`0` is not a rhyme) | Its `ACBD` cross-stanza scheme as a default |
| The "prefer the spoken word" rule | Its syllable line signature |

Amitra's metre is **akshar**, 14 per line as the target (`8 + 6`) inside the
**12–16** tolerance band. Plain spoken words are short, so a short line is fixed by
**adding another everyday clause**, never by inflating a word into its literary
(tatsama) form.