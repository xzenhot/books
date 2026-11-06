---
name: amitra
description: Dedicated Bengali অমিত্রাক্ষর ছন্দ (blank-verse) skill — continuous enjambed sentences whose line breaks fall at the 14-akshar (8 + 6) measure with ±10% tolerance (12–16 akshar). Rhyme is optional and scheme-selected: `blank` (chhanda/meter only, no rhyme), `poyar` (L2~L1 strong rhyme per couplet), or `srijato` (L3~L1, L4~L2 per quatrain). Daily-used spoken register, couplets/quatrains bound by continuous meaning. Default style is `amitra`, grounded from `.framework/editor/poetry/styles/amitra/` and cached per book as `workspaces/pipeline/<bookname>/style.md`. Owns amitra composition end to end; never delegates to the generic poetry skill.
---

# Amitra Skill (অমিত্রাক্ষর ছন্দ)

## Audit Metadata

Chapter drafts and their history/version snapshots are exempt. The per-book style
cache `workspaces/pipeline/<bookname>/style.md` is non-exempt: it must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`, stamped
as the invoking `amitra` agent.

Use this skill to compose or recompose a **Bengali অমিত্রাক্ষর ছন্দ** — a run of
**continuous, enjambed sentences** whose **line breaks** fall after **14 akshars**
in the `8 + 6` measure with a **±10 % band (12–16)**. Rhyme is **optional** and
selected by the mode: **`blank`** (no rhyme — the chhanda/metre is the whole
contract), **`poyar`** (L2~L1 strong rhyme per couplet), or **`srijato`** (L3~L1
and L4~L2 per quatrain).

## Dedicated-Form Rule (binding)

This skill **owns** the amitra form. It is **not** a variation on the generic
`poetry` skill and must never hand its work back to `poetry`, `poyar`, or any
other form skill.

| Never do this | Do this instead |
|---|---|
| Delegate amitra composition to `.framework/skills/poetry/SKILL.md` | Compose here, under the contract below |
| Emit flat poetic prose because the generic skill writes prose | Emit verse lines — 14 akshar, continuous sentences |
| Borrow poyar's couplet-only shape in `blank` mode | Use the amitra line-break contract; rhyme only when the mode demands it |
| Treat the line break as a sentence break | Break at the 8 + 6 measure; let sentences run across lines |

The generic `poetry` skill writes continuous poetic **prose**. Amitra is **metred
blank verse** with a hard line-break ruler; even in `blank` mode the line break is
mandatory. They are incompatible outputs.

## Fundamental Paradigm

> **The agent composes and repairs. MCP measures. Python reports. The agent reads
> the report.**

MCP (`word.akshar-count`, `word.rhyme-test`) is a ruler. `tools/mcpbangla/verse.py`
is a **reviewer**, not a writer: it measures and emits a per-line, per-word report.
It never composes, rewrites, replaces, or "fixes" a line — every repair is the
agent's own authored edit. Bengali conjuncts (যুক্তব্যঞ্জন) make visual counting
invalid — trust MCP, never the eye.

The loop is **write → review → repair**, repeated until the exit criteria pass:

```text
1. write  — the agent authors the lines and appends them to chapter.md
2. review — python tools/mcpbangla/verse.py review <file> --form amitra [--scheme <mode>]
3. repair — the agent reads the report and rewrites only the flagged lines
4. repeat until review prints === PASS ===
```

Never script the composition. Never ask Python to generate, complete, or rewrite a
line. Python only measures, describes, and returns a verdict.

## Invocation

```text
/book <bookname> amitra <n>|<chapter> [<scheme>] [replace]
/book <bookname> write <n> amitra [<scheme>]
/book <bookname> chapter <n> amitra [<scheme>]
```

- `<scheme>` (optional): `blank` (default), `poyar`, or `srijato`.
- `[replace]` (optional): write the finished poem to the chapter files; omit to
  report only.

Reached through the **amitra agent** (`.framework/agents/amitra/agent.md`), which
is dispatched by the write agent when the resolved style/form is `amitra`. Never
execute this skill directly from a workflow.

## Form Contract (binding)

| Property | Value |
|---|---|
| Unit | **Continuous enjambed sentence**, not the stanza |
| Line break | Falls after **14 akshars** (target), measured **`8 + 6`** |
| **Meter unit** | **Akshar** (অক্ষর) — the consonant count, never syllables |
| **Line length** | **14 akshar target**, accepted **12–16 akshar** (±10 %) |
| Caesura | A word boundary at **akshar 8** (the 8 falls, then a 4–8 foot) |
| Ruler | `word.akshar-count` |
| Rhyme | **Optional, mode-selected** — see the modes below |
| Flow | Every line continues the previous sentence; enjambment is the rule |
| Register | Daily-used spoken Bengali (srijato's lexicon, not its forms) |
| Language | Resolved from `book.json` → `language` (never from `override.md`) |

### The metre (chhanda) rule — the heart of the form

A line **targets 14 akshar** and is accepted anywhere in **12–16** (±10 % of
14 = ±2). Within that band the line **passes as written** — never burn a revision
chasing 14 when the line already reads well at 13, 15, or 16. Below 12 or above
16 the line is rewritten. The measure is always **akshar**, never syllables.

The caesura does not need to fall mid-word: the first 8 akshar end at a word
boundary, and the remaining 4–8 akshar complete the line. The **`8` side is the
anchor** — keep it at 8 — and let the second foot absorb the tolerance.

### The continuous-sentence rule (enjambment)

The line break is a **metrical** break, not a sentence break. A sentence starts on
one line and finishes one or more lines later; punctuation falls wherever the
syntax puts it, never forced to the line end.

- Every line reads as a continuation of the sentence that preceded it.
- No line is a self-contained slogan; the meaning runs across the breaks.
- The register and idiom carry forward from line to line.

The line contract does **not** relax under enjambment: each physical line still
sits inside 12–16 akshar and splits at the 8-akshar caesura on a word boundary.
The thought crosses the boundary; the boundary is a metrical and (optionally)
sound boundary, never a sentence boundary.

### The rhyme modes

`word.rhyme-test >= 1` is **necessary but not sufficient** for a strong rhyme;
the two end words' final rhyme units (final syllable, every consonant folded to
its বর্গ row) must also be **identical**. `শব্দ / গন্ধ` returns `1` and is
**weak** — reject it.

| Mode | Rhyme contract | Ruler |
|---|---|---|
| **`blank`** (default) | **None.** The chhanda is the entire test. | akshar only |
| **`poyar`** | L2 rhymes L1 inside each couplet (strong, distinct ends). No cross-couplet rhyme. | akshar + `word.rhyme-test` + strength |
| **`srijato`** | L3 rhymes L1 **and** L4 rhymes L2 inside each quatrain. | akshar + `word.rhyme-test` |

In `blank` mode a poem has no rhyme to hide behind: an out-of-band line or a
missing 8-caesura is an outright failure, and there is nothing else to make up for
it.

## Length — default 16 couplets (32 lines)

**The default amitra poem is 32 verse lines** (16 couplets, or 8 quatrains in
`srijato` mode). Use that unless an explicit instruction says otherwise.

Resolution order, highest first:

1. **Explicit line/couplet count** in the invocation, `override.md`, or
   `filters/override/filter.md` (e.g. "20 lines are enough"). Always wins.
2. **`word_target`** from the chapter's `chapter.json`, then the matching
   `book.json` `chapters[]` entry, then the book-level value — but **only when it
   is explicitly marked as binding for this chapter**. When it is the ordinary
   book-wide value, the default shape wins.

   ```text
   couplet_count = round(word_target / 12)
   ```

3. **Default** — **16 couplets / 32 lines** (~195 words).

A 14-**akshar** line holds roughly **6–7 words**; a couplet roughly **12**.

- Do not stop early because the lines "feel finished".
- Do not pad: never add a line that repeats a step already taken.
- To grow, **advance the argument** — a new image, a new turn, a new consequence.
- Report the resolved count and its source, and if a count constraint puts the poem
  under `word_target`, say so plainly rather than silently undershooting.

## Register — Borrow Srijato's Lexicon, Not Its Form

Take the daily-used spoken word over the literary one.

- **Never inflate a word to reach 14 akshar.** `শুধু` → `শুধুই` is a register
  break and is forbidden. Add another **everyday clause** instead.
- The band means an ordinary line usually lands in **12–16** without forcing. If a
  line is inside the band and reads naturally, **keep it** — do not pad it to 14
  and do not trim it to 14.
- Let idiom and onomatopoeia carry the line (`ঝমঝমিয়ে`, `বড্ড`, `থোড়াই`).
- Ground every elevated turn in a plain, concrete word in the same breath.
- Keep the slight colloquial "incorrectness" (`ততক্ষনে` for `ততক্ষণে`).
- If a line runs long, cut the least essential modifier — never promote a word to
  its tatsama form to save an akshar, and never clip a word to lose one. Outside
  the band a line must be repaired; inside it, leave it alone.

## Language Rule

- Read, compose, and write in the resolved `language` (Bengali for Bengali books).
- Never use English rhyme intuition or romanization.
- Discard any MCP candidate containing non-Bengali or romanized text.

## Style Resolution and Caching (default: `amitra`)

Amitra is form-bound. When this skill runs and no other style is named, the style
is **`amitra`** — resolved from `.framework/editor/poetry/styles/amitra/`:

| File | Role |
|---|---|
| `sample.txt` | canonical অমিত্রাক্ষর corpus (Tagore, Madhusudan) — form and register authority |
| `signature.md` | distilled pattern spec (the *method*, not the subject) |
| `style.md` | full transmuter contract (metre, rhyme modes, MCP protocol, register) |

The corpus is about **pattern, not subject**. It must therefore be re-grounded to
the book before it can be composed from, and the result is **cached** as the
book's operative style reference.

### Cache location

```text
workspaces/pipeline/<bookname>/style.md
```

This is the same file the style agent writes and the quality/review agents
re-ground — one operative style reference per book, never a second copy.

### Resolution order (every amitra write)

1. **Cache hit** — `workspaces/pipeline/<bookname>/style.md` exists **and** its
   provenance block declares `style: amitra` for this book **and** its form
   contract still states the 14-akshar target in the `8 + 6` measure (with the
   ±10 % / 12–16 band). **Use it. Do not regenerate.**
2. **Cache miss / wrong style** — the file is absent, or it is grounded to a
   different style (for example a Srijato reference declaring "Refrain + Verses"
   and a 6–12 syllable line). **Synthesize an amitra-grounded reference and write
   it** (below).
3. **Stale** — `book.json` → `updated_at` is newer than the cache's
   `generated_at`, or the cache's `book` field names another book. Re-synthesize.
4. **Human-edited** — a cache carrying `human_edited: true` is authoritative;
   keep it, and report that it was honored rather than rebuilt.

### Synthesizing the grounded reference

Read, in order:

1. `.framework/editor/poetry/styles/amitra/sample.txt` — extract the **method**:
   the 8 + 6 akshar measure, the continuous enjambed sentence, the daily-used
   register, the plain-concrete anchoring, the oral narrator's address.
2. `.framework/editor/poetry/styles/amitra/signature.md` — the distilled pattern
   (create if missing).
3. `.framework/editor/poetry/styles/amitra/style.md` — the full contract (create if
   missing).
4. `workspaces/pipeline/<bookname>/book.json` — `gist`, `book_summary`, `era`,
   `language`, `form`, `chapters[]` titles and summaries.
5. `workspaces/pipeline/<bookname>/storyline.md` — premise, thematic threads,
   voice, imagery.
6. `workspaces/pipeline/<bookname>/override.md` and
   `filters/override/filter.md` — fold any transformation mandate in.
7. `.framework/editor/subjects/registry.md` and the topic files the storyline
   suggests — for the subjects palette.

Then write **one self-contained document** with these sections, in this order:

| Section | Must contain |
|---|---|
| Provenance | the block below — this is what makes caching safe |
| Authority Note | files read, and their precedence on conflict (`sample.txt` first) |
| Form Contract | continuous sentences, **14 akshar target** with **12–16 band** (±10 %), `8 + 6` caesura, optional rhyme modes |
| Register | daily-used spoken Bengali; the forbidden literary inflations |
| Persona & Voice | the blank-verse narrator's stance, grounded in *this* book |
| Book Grounding | premise, setting/era, thematic threads, the book's own vocabulary |
| Imagery Families | the book's motifs re-keyed from the corpus *pattern* |
| Syllable Tension | how to reach 14 by adding an everyday clause, never by inflating a word |
| Rhyme Protocol | per-mode: `blank` = none; `poyar` = L2~L1; `srijato` = L3~L1, L4~L2 |
| Flow Rule | the line break is metrical; meaning binds the whole poem |
| Transformation Method | the step-by-step procedure this book's lines follow |
| Subjects Registry | the concrete subject palette chosen from the storyline |
| Good Anchors | living coordinates the writer may draw on |
| Output Rules | verse shape, title, no headings, no annotation |

Never copy the corpus's **subject matter** (the Pandavas, the Yamuna, the village
river) into the reference — carry its **method** onto this book's subjects.

## Composition Workflow

### Phase 0 — Read and Understand the Source

1. Read the chapter's existing content:
   - `chapters/<n>/chapter.md` is the live poem and the only source.
   - `chapters/<n>/segments/1/writer/chapter.md` is legacy history. Read it only
     when `chapter.md` is missing or empty.
2. Read `book.json` for the chapter `chapter_summary`, and the book
   `book_summary`, `gist`, and `era`.
3. Extract the thematic core: images, emotions, objects, verbs, and the chapter's
   argument. Write this down before composing.
4. Fix the **through-line** — the single movement the whole poem makes — before
   the first line, so every enjambed sentence advances it.

### Phase 1 — Compose the Sentence, Break It at the Metre

Write the poem as **continuous Bengali sentences first**, then break them into
lines at the 8 + 6 measure:

1. Draft a run of plain, spoken Bengali sentences carrying the chapter's argument.
2. For each sentence, split it at word boundaries so each line lands inside
   **12–16 akshar** with a word boundary at **akshar 8**.
3. A sentence longer than one line simply continues onto the next; a sentence
   shorter than one line shares the line with the next sentence (the break is
   metrical, not syntactic).
4. Choose the end word (only when the mode requires rhyme) from the verified rhyme
   bank; in `blank` mode no end word is locked.

### Phase 2 — Optional Rhyme Bank (only for `poyar` / `srijato`)

For a rhyming mode, build the bank before composing:

- `poyar`: for each couplet, choose anchor A (L1 end), find a strong partner B via
  `word.rhyming-words`, verify `word.rhyme-test(A, B) >= 1` **and** identical
  final rhyme unit, then lock both.
- `srijato`: for each quatrain, lock the L1~L3 family and the L2~L4 family the
  same way; the two families must **not** rhyme each other.

Never fetch a rhyme ad hoc and assume it is valid; the bank is the only source of
end words.

### Phase 3 — Calibrate Each Line (akshar + caesura)

For each line:

1. Measure with `word.akshar-count`. Inside **12–16** → pass; keep it.
2. Outside the band → generate meaning-preserving variants (delete / insert /
   replace via `word.next`, `word.previous`, `word.next-context`), test each, and
   select the first candidate that lands in **12–16** on the 8-akshar caesura
   boundary.
3. Never change the central meaning to hit the count; never inflate a word to its
   tatsama form.
4. Iterate up to 3 rounds per line; on exhaustion record `needs_manual_review` and
   continue.

### Phase 4 — Verify and Append (incremental persistence)

Before appending each line (or couplet/quatrain), confirm with MCP:

1. the line is **within 12–16 akshar**, target 14 (`word.akshar-count`);
2. the line reads **`8` + 4–8** — a word boundary at akshar 8;
3. (rhyme modes only) the required end-word pair passes `word.rhyme-test >= 1`
   **and** the identical-final-unit strength test; ends are distinct (no redif),
   and the pair is not already used earlier in this poem.

Then **append immediately** — never hold finished lines in memory. An interrupted
run leaves a valid shorter poem.

## Output Shape

```markdown
# {chapter_title}

<line 1 — 14 akshar target (12–16), 8 + 2nd foot>
<line 2 — 14 akshar target (12–16), 8 + 2nd foot>
<line 3 — 14 akshar target (12–16), 8 + 2nd foot>
...
```

- The chapter title is the only heading.
- One verse line per line; a blank line separates couplets (in `poyar`) or
  quatrains (in `srijato`); in `blank` mode lines may run without stanza gaps.
- No prose paragraphs, no `## সারাংশ` block, no caesura marks, no annotation.

## Record in `chapter.json`

```json
{
  "form_skill": "amitra",
  "form": "blank_verse",
  "stanza_form": "continuous",
  "line_count": 32,
  "rhyme_scheme": "blank",
  "rhyme_scheme_note": "optional: blank | poyar (L2~L1) | srijato (L3~L1, L4~L2)",
  "meter_unit": "akshar",
  "akshar_target": 14,
  "akshar_tolerance": 2,
  "akshar_band": "12-16",
  "caesura": "8 + 2nd foot",
  "akshar_counts": [14, 13, 15, 14],
  "calibration_method": "agent_composed_mcp_verified",
  "state": "written",
  "draft": {"sha256": "<sha256 of chapter.md>", "written_at": "<iso8601 utc>", "origin": "write"},
  "mcp_verification": {
    "akshar_tool": "word.akshar-count",
    "rhyme_tool": "word.rhyme-test + identical final rhyme unit (rhyme modes only)",
    "all_lines_in_band": true,
    "all_caesura_at_8": true,
    "all_rhymes_verified": true,
    "all_rhymes_strong": true
  }
}
```

## Review Loop — Python reports, the agent repairs

```bash
python tools/mcpbangla/verse.py review workspaces/pipeline/<book>/chapters/<n>/chapter.md --form amitra --scheme blank
python tools/mcpbangla/verse.py review <file> --form amitra --scheme poyar
python tools/mcpbangla/verse.py review <file> --form amitra --scheme srijato
python tools/mcpbangla/verse.py review <file> --form amitra --json   # machine-readable
```

`review` is **read-only**; it prints a per-line, per-word verdict. Per line it
gives total akshar, delta vs target, band verdict, and the word-by-word cumulative
breakdown with caesura placement; per couplet/quatrain (rhyme modes) it gives the
rhyme test and strength.

Repair rules for the agent:

- Act **only** on the lines the report flags. Do not rewrite a passing line.
- `SHORT` — add an everyday clause; never inflate a word to its tatsama form.
- `LONG` — cut the least essential modifier.
- `off by ±n` on the caesura — move a word across the boundary; the `8` foot is
  the anchor, so prefer adjusting the second foot.
- `WEAK` or `rhyme=0/-1` — rework the line's end word with a verified strong
  partner (rhyme modes only).
- `REDIF` — the two ends are the same word; replace one.

Re-run `review` after every repair batch. The loop exits only on `=== PASS ===`.

## Final Verification

After the last line is appended:

```bash
python tools/mcpbangla/verse.py review workspaces/pipeline/<book>/chapters/<n>/chapter.md --form amitra [--scheme <mode>]
python tools/mcpbangla/verse.py audit  workspaces/pipeline/<book>/chapters/<n>/chapter.md --form amitra --scheme <mode>
```

Both must print `=== PASS ===`. If either fails on a line written earlier, repair
that line in place and re-run both. Then record the form evidence in `chapter.json`.

## Constraints

- **Never** route amitra work to the generic `poetry` skill.
- **Never** compose amitra against a style that is not `amitra`-grounded.
- **Never** regenerate `workspaces/pipeline/<bookname>/style.md` when it already
  carries a valid `style: amitra` provenance block for this book — reuse it.
- Never use MCP or Python to generate, complete, or rewrite a line; MCP measures
  and Python reports only. Every line is authored by the agent.
- Never compute akshar or rhyme facts natively; every count comes from MCP.
- The line break is metrical, never a sentence break; enjambment is the rule.
- In `blank` mode, never force a rhyme to make a line "complete" — the chhanda is
  the whole contract.
- Every line inside the **12–16 akshar** band (±10 % of 14), keeping the first
  foot at 8; a line outside the band is rewritten. Inside the band, never rework a
  line merely to make it read 14.
- Never accept a weak rhyme in a rhyme mode; `0` is not a rhyme and `1` alone is
  not proof.
- Never leave lines as isolated vignettes — flow is part of the contract.
- **Never hold verified lines in memory** — append each one to `chapter.md` as
  soon as it passes.
- Never append an unverified line "to fix later"; rework it in place instead.
- Never restart a partially written chapter from zero — resume after the lines
  already on disk.
- Never write `chapter.md` without archiving the prior copy first.
- Never revert a cache marked `human_edited: true`.
- Write only inside `workspaces/pipeline/<bookname>/`. Never promote to
  `workspaces/published/` — that is `publish`.
- Valid only for books with `form: poetry`.

## Audit Tooling

| Script | Use |
|---|---|
| `tools/mcpbangla/verse.py review <file> --form amitra [--scheme <mode>]` | report-only per-line review; `=== PASS ===` required |
| `tools/mcpbangla/verse.py audit <file> --form amitra --scheme <mode>` | full contract audit; `=== PASS ===` required |
| `tools/mcpbangla/verse.py measure <file> --syllable` | per-line akshar (and syllable, for reference) |
| `tools/mcpbangla/verse.py rhyme A B` | single pair; exit 1 on weak or non-rhyme |
| `tools/mcpbangla/verse.py family <word>` | verified rhyme-class candidates |
| `tools/mcpbangla/kamolika.py` | MCP HTTP client (`BASE_URL`), imported not run |

## Report Format

```
Amitra Report
Book     : <bookname>
Chapter  : <n>
Mode     : amitra (অমিত্রাক্ষর ছন্দ — 14-akshar lines, 8 + 6, band 12–16)
Scheme   : blank (no rhyme) | poyar (L2~L1) | srijato (L3~L1, L4~L2)
Style    : amitra (<reused|synthesized> → workspaces/pipeline/<bookname>/style.md)
Target   : 32 lines (default) | <count directive> | <word_target> words
Language : <language>

Lines:
  L01 [14 ✓] [8+6 ✓]  <line>
  ...

Summary:
  Lines in band : <n>/<n> (12–16 akshar, 8 + 2nd foot)
  Exact 14      : <n>/<n>
  8 caesura     : <n>/<n>
  Rhyme audit   : n/a (blank) | passed (poyar/srijato)
  Needs review  : none
  Written       : incremental (last append at line <n>)
  Flow          : <the through-line the poem follows>

Next:
  /book <bookname> amitra <n> <scheme> replace   ← persist after review
  /book <bookname> write <n>                      ← promote to chapter output
```