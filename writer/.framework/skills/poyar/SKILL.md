---
name: poyar
description: Dedicated Bengali poyar (পয়ার) skill — two-line couplets (দ্বিপদী), exactly 14 syllables per line in the 4+4+4+2 measure, L1~L2 strong rhyme inside each couplet, no cross-couplet rhyme, daily-used spoken register, couplets bound by continuous meaning. Default style is `poyar`, grounded from `.framework/context/poetry/styles/poyar/` and cached per book as `workspaces/pipeline/<bookname>/style.md`. Owns poyar composition end to end; never delegates to the generic poetry skill. Alias: "payar".
---

# Poyar Skill (পয়ার)

## Audit Metadata

Chapter drafts and their history/version snapshots are exempt. The per-book style
cache `workspaces/pipeline/<bookname>/style.md` is non-exempt: it must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`, stamped
as the invoking `poyar` agent.

Use this skill to compose or recompose a **Bengali poyar** — a run of **two-line
couplets** (দ্বিপদী), each sealed by a **strong rhyme**, each line **exactly 14
syllables**, the whole poem moving as one continuous argument.

## Dedicated-Form Rule (binding)

This skill **owns** the poyar form. It is **not** a variation on the generic
`poetry` skill and must never hand its work back to `poetry`, `srijato`, or any
other form skill.

| Never do this | Do this instead |
|---|---|
| Delegate poyar composition to `.framework/skills/poetry/SKILL.md` | Compose here, under the contract below |
| Ask the `poetry` skill to "add a couplet form" | Apply the couplet contract in this file |
| Emit flat poetic prose because the generic skill writes prose | Emit verse lines — 14 syllables, rhymed pairs |
| Borrow srijato's refrain/stanza shape | Borrow only srijato's **register** |

The generic `poetry` skill writes continuous poetic **prose**. Poyar is **metred,
rhymed verse**. They are incompatible outputs; using the generic skill for a poyar
request is a contract violation, not a shortcut.

## Fundamental Paradigm

> **The agent composes. MCP measures. The agent adjusts.**

MCP (`word.syllable-count`, `word.rhyme-test`, `word.syllable`) is a ruler. It
measures and verifies; it never writes a line. Bengali conjuncts (যুক্তব্যঞ্জন)
make visual counting invalid — trust MCP, never the eye.

## Invocation

```text
/book <bookname> write <n>|all|continue poyar
/book <bookname> poyar <n>|<chapter> [replace]
/book <bookname> payar <n>|<chapter> [replace]   # alias
```

Reached through the **poyar agent** (`.framework/agents/poyar/agent.md`), which is
dispatched by the write agent when the resolved style/form is `poyar`. Never
execute this skill directly from a workflow.

## Form Contract (binding)

| Property | Value |
|---|---|
| Unit | **Two-line couplet** (দ্বিপদী) |
| Line order | Line 1 first; line 2 closes the pair |
| **Meter unit** | **Syllable** — never akshar, never matra |
| **Line length** | **Exactly 14 syllables**, `4 + 4 + 4 + 2` (a `+1` close is legal; 2 preferred) |
| Ruler | `word.syllable-count` **per word, summed** |
| Rhyme | **L1 ~ L2 inside each couplet** — `word.rhyme-test >= 1` **and** identical final rhyme unit |
| Cross-couplet rhyme | **None required and none wanted** — L2~L4 / L1~L4 carry no obligation |
| Distinct ends | L1 end ≠ L2 end (an identical pair is a *redif* and fails) |
| Flow | Every couplet continues the previous thought as a real sentence |
| Register | Daily-used spoken Bengali (srijato's lexicon, not its forms) |
| Language | Resolved from `book.json` → `language` (never from `override.txt`) |

### The meter rule

**A poyar line is exactly 14 syllables.** Not 13, not 15, not "about 14". Sum the
per-word counts:

```python
total = sum(int(extract_text(call_tool("word.syllable-count", {"word": w})))
            for w in line.split())
```

Never call `word.syllable-count` on a whole line — it over-counts across conjunct
boundaries and reports 15 for a genuine 14. Never measure by akshar.

### The rhyme rule

`word.rhyme-test >= 1` is **necessary but not sufficient**.

| Value | Meaning | Verdict |
|---|---|---|
| `-1` | different rhyme class | reject |
| `0` | same vowel shape, different class | **reject — not a rhyme** |
| `1` | rhymes (assonantal/consonantal) | check strength |
| `2` | perfect rhyme | accept |

Then apply the **strength test**: the two end words' final syllables, with every
consonant folded to its বর্গ row, must be **identical**.

| Pair | `rhyme-test` | Verdict |
|---|---|---|
| হাত / রাত | `1` | ✓ strong — both `-াত` |
| চোখ / শোক | `1` | ✓ strong — both `-োক` |
| **শব্দ / গন্ধ** | **`1`** | **✗ weak — `-ব্দ` vs `-ন্ধ`; reject** |
| মাটি / বৃষ্টি | `1` | ✗ weak — `-টি` vs `-ষ্টি`; reject |

Verify with the CLI, which exits non-zero on a weak pair:

```bash
python tools/mcpbangla/verse.py rhyme হাত রাত    # exit 0: STRONG
python tools/mcpbangla/verse.py rhyme শব্দ গন্ধ   # exit 1: WEAK
```

**If line 2 cannot make a strong rhyme, rework line 1** — shuffle its words or
replace the line outright. Never accept a weak pair because `rhyme-test` said `1`.

### The flow rule (the one that separates poyar from a rhyme list)

Rhyme binds a *couplet*; **meaning** must bind the *poem*. No cross-couplet rhyme
exists to carry the sound, so the sense has to carry everything.

- Each couplet continues the previous sentence or thought. Not a new topic.
- Each couplet reads as a real sentence, not a decorative fragment.
- Each couplet advances the argument by one step.
- The register and idiom carry forward.

A poyar whose couplets each stand alone is **broken even when all sixteen rhymes
pass**. Before writing, fix the through-line — the single movement the whole poem
makes — and let every couplet take the next step of it.

## Length (derived from `word_target`, not guessed)

Resolve `word_target` from the chapter's `chapter.json`, then the matching
`book.json` `chapters[]` entry, then the book-level value.

A 14-syllable line holds roughly **6–7 words**; a couplet roughly **12–13**.

```text
couplet_count = round(word_target / 12.5)      # 300 words → 24 couplets
```

- Reach the target. Do not stop at 60–70% because the couplets "feel finished".
- Do not pad: never add a couplet that repeats a step already taken.
- To grow, **advance the argument** — a new image, a new turn, a new consequence.
- An explicit line-count directive in `override.txt` or
  `filters/override/filter.md` wins over this target.

## Register — Borrow Srijato's Lexicon, Not Its Form

Take the daily-used spoken word over the literary one.

- **Never inflate a word to reach 14 syllables.** `শুধু` → `শুধুই` to gain a
  syllable is a register break and is forbidden. Add another **everyday clause**
  instead:

  ```text
  short (9):  অপেক্ষা মানে শুধু আশা
  ok   (14):  অপেক্ষা মানে সারাক্ষণ পাহারা আশা     ← added a spoken clause
  ```

- Let idiom and onomatopoeia carry the line (`ঝমঝমিয়ে`, `বড্ড`, `থোড়াই`).
- Ground every elevated turn in a plain, concrete word in the same breath.
- Keep the slight colloquial "incorrectness" (`ততক্ষনে` for `ততক্ষণে`).
- If a line runs long, cut the least essential modifier — never promote a word to
  its tatsama form to save a syllable, and never clip a word to lose one.

## Language Rule

- Read, compose, and write in the resolved `language` (Bengali for Bengali books).
- Never use English rhyme intuition or romanization.
- Discard any MCP candidate containing non-Bengali or romanized text.

## Style Resolution and Caching (default: `poyar`)

Poyar is form-bound. When this skill runs and no other style is named, the style
is **`poyar`** — resolved from `.framework/context/poetry/styles/poyar/`:

| File | Role |
|---|---|
| `sample.txt` | canonical couplet corpus — form, rhyme, and register authority |
| `signature.md` | distilled pattern spec (the *method*, not the subject) |
| `style.md` | full transmuter contract (meter, rhyme, MCP protocol, register) |

The corpus is about **pattern, not subject**. It must therefore be re-grounded to
the book before it can be composed from, and the result is **cached** as the
book's operative style reference.

### Cache location

```text
workspaces/pipeline/<bookname>/style.md
```

This is the same file the style agent writes and the quality/review agents
re-ground — one operative style reference per book, never a second copy.

### Resolution order (every poyar write)

1. **Cache hit** — `workspaces/pipeline/<bookname>/style.md` exists **and** its
   provenance block declares `style: poyar` for this book **and** its form
   contract still states the 14-syllable couplet measure. **Use it. Do not
   regenerate.** Regeneration on every write is a cache miss by construction and
   is forbidden.
2. **Cache miss / wrong style** — the file is absent, or it is grounded to a
   different style (for example a Srijato reference declaring "Refrain + Verses"
   and a 6–12 syllable line). **Synthesize a poyar-grounded reference and write
   it** (below).
3. **Stale** — `book.json` → `updated_at` is newer than the cache's
   `generated_at`, or the cache's `book` field names another book. Re-synthesize.
4. **Human-edited** — a cache carrying `human_edited: true` is authoritative;
   keep it, and report that it was honored rather than rebuilt.

A style grounded to another form is **worse than no style at all** here: a Srijato
reference tells the writer to build refrains and 6–12 syllable lines, which
directly contradicts this form. Never compose poyar against it.

### Precedence over the book's `style` field

`book.json` → `"style"` names the book's **general** transformer style (for
example `srijato`, used by the generic `poetry` skill). It does **not** override
this skill's default: a poyar write is form-bound, so it composes from the
poyar-grounded `style.md` regardless of what `book.json` declares. Only an
**explicit `<style>` argument on the poyar invocation** can override it, and even
then the couplet contract still binds.

### Synthesizing the grounded reference

Read, in order:

1. `.framework/context/poetry/styles/poyar/sample.txt` — extract the **method**:
   couplet pairing, the `4 + 4 + 4 + 2` measure, the daily-used register, the
   plain-concrete anchoring, the oral narrator's address.
2. `.framework/context/poetry/styles/poyar/signature.md` — the distilled pattern.
3. `.framework/context/poetry/styles/poyar/style.md` — the full contract.
4. `workspaces/pipeline/<bookname>/book.json` — `gist`, `book_summary`, `era`,
   `language`, `form`, `chapters[]` titles and summaries.
5. `workspaces/pipeline/<bookname>/storyline.md` — premise, thematic threads,
   voice, imagery.
6. `workspaces/pipeline/<bookname>/override.txt` and
   `filters/override/filter.md` — fold any transformation mandate in.
7. `.framework/context/subjects/registry.md` and the topic files the storyline
   suggests — for the subjects palette.

Then write **one self-contained document** with these sections, in this order:

| Section | Must contain |
|---|---|
| Provenance | the block below — this is what makes caching safe |
| Authority Note | files read, and their precedence on conflict (`sample.txt` first) |
| Form Contract | couplets, **exactly 14 syllables**, `4 + 4 + 4 + 2`, strong L1~L2, **no cross-couplet rhyme** |
| Register | daily-used spoken Bengali; the forbidden literary inflations |
| Persona & Voice | the couplet-maker's stance, grounded in *this* book |
| Book Grounding | premise, setting/era, thematic threads, the book's own vocabulary |
| Imagery Families | the book's motifs re-keyed from the corpus *pattern* |
| Syllable Tension | how to reach 14 by adding an everyday clause, never by inflating a word |
| Rhyme Protocol | `rhyme-test >= 1` **and** identical final rhyme unit; the `শব্দ/গন্ধ` trap |
| Flow Rule | rhyme binds a couplet, meaning binds the poem |
| Transformation Method | the step-by-step procedure this book's couplets follow |
| Subjects Registry | the concrete subject palette chosen from the storyline |
| Good Anchors | living coordinates the writer may draw on |
| Output Rules | verse shape, title, no headings, no annotation |

Never copy the corpus's **subject matter** (the Yamuna, the Pandavas, the village
river) into the reference — carry its **method** onto this book's subject.

### Provenance block (mandatory, first lines of the cached file)

```markdown
<!-- style-provenance
style: poyar
book: <bookname>
form: poetry
meter: syllable-14
grounded_from: .framework/context/poetry/styles/poyar/{sample.txt,signature.md,style.md}
generated_at: <ISO-8601 UTC>
book_updated_at: <book.json updated_at>
human_edited: false
-->
```

Set `human_edited: true` when a human has revised the file — do not revert it.
Resolution step 1 reads this block, so a document without it is treated as a
cache miss.

### After writing the cache

- Report the cache path and whether it was **reused** or **synthesized**.
- Do **not** rewrite it on the next poyar chapter — reuse it.
- If the book's plan changes materially (`updated_at` moves, chapters added),
  re-synthesize once and continue.

## Reading Before Writing (mandatory, every time)

1. `chapters/<n>/chapter.json` — `chapter_title`, `chapter_summary`, `word_target`,
   and `creative_enrichment` (angles, story options, sensory details, structural
   variants, `variety_note`). **The enrichment is the poem's material — use it.**
   A poyar that ignores `creative_enrichment` and re-writes the chapter summary in
   couplets has not been written.
2. `book.json` — `language`, book `gist`, `book_summary`, `era`.
3. `filters/override/filter.md` and `override.txt` — craft directives. Binding.
   Apply silently; never quote them as lines.
4. `storyline.md` — thematic grounding. Invent nothing beyond it.
5. `workspaces/pipeline/<bookname>/style.md` — the **cached, book-grounded poyar
   reference** (resolve it per *Style Resolution and Caching* above; synthesize it
   only on a cache miss).
6. `.framework/context/poetry/styles/poyar/{signature.md,sample.txt}` — form and
   register authority; consult when the cache is ambiguous, never as a substitute
   for the grounded reference.

**Avoid recycled rhymes.** Before writing, read the other poyar chapters in the same
book and do not reuse their rhyme pairs or phrasings. Repetition across chapters
reads as a tic, not a voice. Check:

```bash
python tools/mcpbangla/verse.py audit workspaces/pipeline/<book>/chapters/<other>/chapter.md --form poyar
```

## Composition Workflow

### Phase 0 — Fix the through-line

Write one sentence naming what the poem does from first couplet to last (the
movement, not the topic). Every couplet must take the next step of it. If the
`creative_enrichment` offers several story options, choose one and commit.

### Phase 1 — Fix the rhyme pair before writing either line

A couplet is only as good as its rhyme; a beautiful line 1 cannot rescue a weak
pair.

1. Choose end word **A** that the meaning needs.
2. Fetch partners: `word.rhyming-words` (`sizes` is a hint, not a filter).
3. Confirm `word.rhyme-test(A, B) >= 1` **and** identical final rhyme unit
   (`verse.py rhyme A B`, exit 0).
4. If no **strong** partner exists, **discard A** and choose another end word.

### Phase 2 — Write line 1

A complete, singable statement in the daily register, ending on **A**. Measure it
immediately: exactly 14 syllables. If 13 or 15, rewrite it now — never carry a
wrong-length line forward.

### Phase 3 — Write line 2

Close the pair on **B**, exactly 14 syllables, continuing line 1's sentence.

### Phase 3a — If line 2 will not rhyme well, change line 1

Mandatory, not optional: shuffle line 1's words, swap its final phrase, or replace
it wholesale with a line ending on a word whose strong partners fit the meaning.
Then re-verify the pair and re-measure both lines.

### Phase 4 — Continue without rhyming across

Move to the next couplet. Its rhyme class is free — deliberately do **not** chain
the sound from the previous couplet. Its *meaning* must continue the previous
couplet's thought.

### Phase 5 — Audit, then write

```bash
python tools/mcpbangla/verse.py audit workspaces/pipeline/<book>/chapters/<n>/chapter.md --form poyar
```

The audit must print `=== PASS ===`. Then:

1. Archive any existing `chapter.md` to `chapters/<n>/segments/1/version/chapter_v<k>.md`
   (`<k>` = highest existing + 1; never overwrite an archive).
2. Write `chapters/<n>/chapter.md` as `# {chapter_title}`, a blank line, then
   couplets separated by blank lines (verse, one line per line — never merged
   into paragraphs).
3. Record the form evidence in `chapter.json`.

## Output Shape

```markdown
# {chapter_title}

<line 1 — 14 syllables>
<line 2 — 14 syllables, rhymes line 1>

<line 3 — 14 syllables>
<line 4 — 14 syllables, rhymes line 3>

...
```

- The chapter title is the only heading.
- Exactly two verse lines per couplet, blank line between couplets.
- No prose paragraphs, no `## সারাংশ` block, no caesura marks, no annotation.

## Record in `chapter.json`

```json
{
  "form_skill": "poyar",
  "form": "couplet_poem",
  "stanza_form": "couplet",
  "stanza_count": 24,
  "line_count": 48,
  "rhyme_scheme": "AA",
  "rhyme_scheme_note": "L1~L2 inside each couplet; no cross-couplet rhyme",
  "meter_unit": "syllable",
  "syllable_target": 14,
  "syllable_measure": "4 + 4 + 4 + (2|1)",
  "syllable_counts": [14, 14, 14, 14],
  "calibration_method": "agent_composed_mcp_verified",
  "state": "written",
  "draft": {"sha256": "<sha256 of chapter.md>", "written_at": "<iso8601 utc>", "origin": "write"},
  "mcp_verification": {
    "syllable_tool": "word.syllable-count (per word, summed)",
    "rhyme_tool": "word.rhyme-test + identical final rhyme unit",
    "all_rhymes_verified": true,
    "all_rhymes_strong": true,
    "syllable_delta": 0,
    "couplets": [
      {"couplet": 1, "L1_end": "…", "L2_end": "…", "rhyme": "1",
       "strength": "STRONG", "rhyme_unit_L1": "…", "rhyme_unit_L2": "…",
       "distinct": true, "L1_syllables": 14, "L2_syllables": 14}
    ]
  }
}
```

## Constraints

- **Never** route poyar work to the generic `poetry` skill.
- **Never** compose poyar against a style that is not `poyar`-grounded. A Srijato
  or `pijush` reference mandates refrains and 6–12 syllable lines and contradicts
  this form.
- **Never** regenerate `workspaces/pipeline/<bookname>/style.md` when it already
  carries a valid `style: poyar` provenance block for this book — reuse it.
- Never use MCP to generate or complete a line; MCP measures and verifies only.
- Never compute syllable or rhyme facts natively.
- Every line exactly 14 syllables; no exceptions, no "close enough".
- Never accept a weak rhyme; `0` is not a rhyme and `1` alone is not proof.
- Never accept an identical end pair (redif).
- Never rhyme across couplets.
- Never inflate a word to its literary form to make the count.
- Never leave couplets as isolated vignettes — flow is part of the contract.
- Never write `chapter.md` without archiving the prior copy first.
- Never revert a cache marked `human_edited: true`.
- Write only inside `workspaces/pipeline/<bookname>/`. Never promote to
  `workspaces/published/` — that is `publish`.
- Valid only for books with `form: poetry`.

## Audit Tooling

| Script | Use |
|---|---|
| `tools/mcpbangla/verse.py audit <file> --form poyar` | full contract audit; `=== PASS ===` required |
| `tools/mcpbangla/verse.py measure <file> --syllable` | per-line akshar + syllable table |
| `tools/mcpbangla/verse.py rhyme A B` | single pair; exit 1 on weak or non-rhyme |
| `tools/mcpbangla/verse.py family <word>` | verified rhyme-class candidates |
| `tools/mcpbangla/kamolika.py` | MCP HTTP client (`BASE_URL`), imported not run |

`--floor N` on the audit means **exact syllables per line** (default 14), despite
the name. These scripts are permanent — never delete or rewrite them inline.

## Report Format

```
Poyar Report
Book     : <bookname>
Chapter  : <n>
Mode     : poyar (14-syllable couplets, 4+4+4+2)
Style    : poyar (<reused|synthesized> → workspaces/pipeline/<bookname>/style.md)
Target   : <word_target> words → <n> couplets
Language : <language>

Couplets:
  c01 [14/14 ✓] হাত/রাত   rt=1 STRONG
      <line 1>
      <line 2>
  ...

Summary:
  Couplets    : <n>/<n> at exactly 14 syllables
  Strong rhyme: <n>/<n>
  Audit       : PASS
  Flow        : <the through-line the poem follows>
  Reused pairs: none
```
