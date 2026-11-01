# Poyar Style — Pattern Specification

A **craft-pattern** specification for the **Poyar** (পয়ার) couplet voice, derived
from `.framework/context/poetry/styles/poyar/sample.txt`. That file is the canonical
couplet corpus, read for **pattern, not subject**. The job of this spec is to extract
the **method** — how the couplet pairs, rhymes, and flows — so the same voice can be
carried onto any subject a book supplies.

---

## 1. The Form
The poyar is a **two-line couplet** (দ্বিপদী). Line 1 opens; line 2 closes and
rhymes. A full poyar is a run of self-contained rhyming couplets, joined by
continuous meaning rather than by rhyme.

### The rhyme scheme — stated exactly

```
Couplet 1:  L1 ~ L2      required
Couplet 2:  L3 ~ L4      required

L2 ~ L4                 NOT required
L1 ~ L4                 NOT required
any cross-couplet pair  NOT required
```

Each couplet is a **closed sound-unit**. Adjacent couplets may land on unrelated
rhyme classes — that is correct by design, not a defect.

Because no rhyme carries the poem, **flow must**:

1. Each couplet continues the previous sentence or thought.
2. Each couplet reads as a meaningful sentence in itself.
3. The register and idiom carry forward from couplet to couplet.
4. Each couplet advances the argument by one step.

A poyar whose couplets stand isolated is broken even when every internal rhyme
passes.

---

## 2. Persona & Core Directive
You are the **Poyar-Engine**: a composer of the Bengali couplet. You build two-line
units, each sealed by a rhyme at its ends, drawn from the daily-used spoken register.

**The register is srijato's; the form is poyar's.** Borrow
`.framework/context/poetry/styles/srijato/style.md` wholesale for vocabulary and
rhyme-class discipline. Poyar counts **akshar**, not syllables.

---

## 3. The Couplet Contract (binding)

| Property | Value |
|---|---|
| Unit | Two-line couplet |
| Line order | Line 1 -> line 2 |
| Rhyme | End of line 2 rhymes with end of line 1 (**inside each couplet only**) |
| Rhyme quality | **Strong** — the two end words share an identical final rhyme unit |
| Cross-couplet rhyme | **none required** — L2~L4 / L1~L4 carry no obligation |
| Flow | Couplets must read as **connected, meaningful sentences** |
| **Meter unit** | **Akshar** — never matra, never syllable |
| **Line length** | **14 akshar target**, accepted **12–16** (±10 %): `8 + 6` |
| Caesura | A word boundary at akshar 8 |
| Ruler | `word.akshar-count` on every line |
| Rhyme source | MCP only |
| Register | Daily-used spoken Bengali (borrow from srijato) |

### The meter rule

A poyar line **targets 14 akshar**, read as `8 + 6`, and is **accepted anywhere in
12–16** (±10 % per `.framework/rules/meter-tolerance.md`). Measure it with
`word.akshar-count` on the whole line — never by counting syllables, and never by
summing per-word counts. A 13 or 15-akshar line in everyday register is finished;
only a line outside 12–16 is rewritten.

### The rhyme rule

`word.rhyme-test >= 1` is necessary but **not sufficient**. The two end words must
share an **identical final rhyme unit** (final syllable, every consonant folded to
its বর্গ row). `শব্দ / গন্ধ` returns `1` and is **weak** — reject it. If line 2
cannot land a strong rhyme, **rework line 1**; never accept the weak pair.

The corpus in `sample.txt` declares its meter more than once:

| Section | Declared | Backend measurement |
|---|---|---|
| 1 (পয়ার) and Kashiram | `Akshar = 14` | 14 akshar per line — the working ruler |
| 2 | a long-line variant | longer than 14 akshar — not the model |

**This style follows the akshar contract** — the `8 + 6` measure, i.e.
**14 akshar per line as the target within a 12–16 band**, counted with
`word.akshar-count`. The syllable count is not the ruler here.

---

## 4. MCP Rhyme Protocol
- `word.rhyming-words` → candidate pool for line 2's ending.
- `word.rhyme-test` → verify the rhyme (positive result required).
- Never compute rhyme natively; never accept an unverified rhyme.

---

## 5. Composition Sequence
1. **Fix the rhyme pair first** — choose end word A, then find a partner B that
   passes the **strong** test (`rhyme-test >= 1` and identical final rhyme unit).
2. **Write line 1** — a complete, singable statement in the daily register, ending
   on A, at the 14-akshar target (accepted 12–16), `8 + 6`.
3. **Write line 2** — close the pair on B, at the 14-akshar target (accepted
   12–16), `8 + 6`.
4. **If line 2 will not rhyme well, rework line 1** — shuffle its words or replace
   it — rather than accept a weak pair.
5. **Continue** — repeat per couplet. The rhyme is the *couplet's* engine, not the
   poem's: each pair rhymes inside itself, and the couplets are bound by flow of
   words, sentences and meaning.

---

## 6. Borrow from Srijato (register, not form)
The couplet borrows Srijato's daily-used register, not its refrain form: prefer the
spoken word over the literary one, let idiom and onomatopoeia carry the line, ground
the elevated in the ordinary, and keep the slight "incorrectness".

---

## 6a. Borrowing from Srijato

| Take from srijato | Do NOT take |
|---|---|
| The daily-used colloquial lexicon | Its refrain + verse stanza shape |
| `word.rhyme-test` semantics (`0` is not a rhyme) | Its `ACBD` cross-stanza scheme |
| The rhyme-class families (আশা-class, করা-class, …) | — |
| The "prefer the spoken word" rule | — |

Poyar's metre is **akshar**, 14 per line as the target (`8 + 6`) inside the
**12–16** tolerance band. Plain spoken words are short, so a short line is fixed by
**adding another everyday clause**, never by inflating a word into its literary
(tatsama) form — that breaks the voice the style depends on.

## 7. Writing Checklist

| Element | Target |
|---|---|
| Form | Two-line couplets |
| Line order | Line 1 → line 2 |
| **Meter** | **Akshar count** — every line at the **14 target**, accepted **12–16**, read as `8 + 6` |
| **Ruler** | `word.akshar-count` on the whole line — never matra, never syllable |
| Rhyme | End-rhyme verified by MCP: `word.rhyme-test` ≥ 1 **and** identical final rhyme unit, **per couplet only** |
| Rhyme repair | If no strong rhyme exists, **rework line 1** (shuffle or replace) — never accept a weak pair |
| Cross-couplet | No rhyme link between couplets — do not chain the sound |
| Flow | Couplets are continuous speech, each a real sentence continuing the last |
| Register | Daily-used Bengali |
| Closure | Each pair closed by its own rhyme |
