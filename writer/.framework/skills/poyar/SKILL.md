---
name: poyar
description: Dedicated Bengali poyar (পয়ার) skill — two-line couplets (দ্বিপদী), 14 akshar per line measured 8 + 6 with ±10% tolerance (12–16 akshar), strong L1~L2 rhyme inside each couplet, no cross-couplet rhyme, daily-used spoken register, couplets bound by continuous meaning. Default style is `poyar`, grounded from `.framework/editor/poetry/styles/poyar/` and cached per book as `workspaces/pipeline/<bookname>/style.md`. Owns poyar composition end to end; never delegates to the generic poetry skill. Alias: "payar".
---

# Poyar Skill (পয়ার)

## Audit Metadata

Chapter drafts and their history/version snapshots are exempt. The per-book style
cache `workspaces/pipeline/<bookname>/style.md` is non-exempt: it must carry
`updated_by` and `updated_date` per `.framework/rules/audit-metadata.md`, stamped
as the invoking `poyar` agent.

Use this skill to compose or recompose a **Bengali poyar** — a run of **two-line
couplets** (দ্বিপদী), each sealed by a **strong rhyme**, each line **14 akshar**
in the `8 + 6` measure with a **±10 % band (12–16)**, the whole poem moving as one
continuous argument.

## Dedicated-Form Rule (binding)

This skill **owns** the poyar form. It is **not** a variation on the generic
`poetry` skill and must never hand its work back to `poetry`, `srijato`, or any
other form skill.

| Never do this | Do this instead |
|---|---|
| Delegate poyar composition to `.framework/skills/poetry/SKILL.md` | Compose here, under the contract below |
| Ask the `poetry` skill to "add a couplet form" | Apply the couplet contract in this file |
| Emit flat poetic prose because the generic skill writes prose | Emit verse lines — 14 akshar, rhymed pairs |
| Borrow srijato's stanza/refrain shape | Borrow only srijato's **register** |

The generic `poetry` skill writes continuous poetic **prose**. Poyar is **metred,
rhymed verse**. They are incompatible outputs; using the generic skill for a poyar
request is a contract violation, not a shortcut.

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
1. write  — the agent authors the couplet(s) and appends them to chapter.md
2. review — python tools/mcpbangla/verse.py review <file> --form poyar
3. repair — the agent reads the report and rewrites only the flagged lines
4. repeat until review prints === PASS ===
```

Never script the composition. Never ask Python to generate, complete, or rewrite a
line. Python only measures, describes, and returns a verdict.

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
| **Meter unit** | **Akshar** (অক্ষর) — the consonant count, never syllables |
| **Line length** | **14 akshar target**, accepted **12–16 akshar** (±10 %), measured **`8 + 6`** |
| Caesura | A word boundary at **akshar 8** (the 8 falls, then a 4–8 foot) |
| Ruler | `word.akshar-count` |
| Rhyme | **L1 ~ L2 inside each couplet** — `word.rhyme-test >= 1` **and** identical final rhyme unit |
| Cross-couplet rhyme | **None required and none wanted** — L2~L4 / L1~L4 carry no obligation |
| Distinct ends | L1 end ≠ L2 end (an identical pair is a *redif* and fails) |
| Flow | Every couplet continues the previous thought as a real sentence |
| Register | Daily-used spoken Bengali (srijato's lexicon, not its forms) |
| Language | Resolved from `book.json` → `language` (never from `override.md`) |

### The meter rule

**A poyar line targets 14 akshar** and is accepted anywhere in **12–16**
(±10 % of 14 = ±2). Within that band the line **passes as written** — never burn a
revision chasing 14 when the line already reads well at 13, 15, or 16. Below 12 or
above 16 the line is rewritten. The measure is always **akshar**, never syllables.

```python
total = int(extract_text(call_tool("word.akshar-count", {"word": line})))
in_band = 12 <= total <= 16          # 14 ± 10 %
```

The caesura does not need to fall mid-word: the first 8 akshar end at a word
boundary, and the remaining 4–8 akshar complete the line. The **`8` side is the
anchor** — keep it at 8 — and let the second foot absorb the tolerance.

```text
আমাদের ছোটো নদী চলে | বাঁকে বাঁকে        8 + 6 = 14 akshar   ✓ exact target
আমাদের ছোটো নদী | বাঁকে বাঁকে চলে যায়     8 + 8 = 16 akshar   ✓ upper band
আমাদের ছোটো নদী | বাঁকে বাঁকে              8 + 4 = 12 akshar   ✓ lower band
বৈশাখ মাসে তার হাঁটু | জল                  7 + 3 = 10 akshar   ✗ below band; extend
```

Do not measure syllables. A poyar line and its syllable count are different
numbers, and only the akshar count is the contract.

This ±10 % band is the repository-wide meter rule
(`.framework/rules/meter-tolerance.md`) and applies to every metre-based form —
poyar, sonnet, haiku, limerick, srijato, and lyrics. It relaxes the **line count
only**: the akshar-8 caesura, the rhyme, and the flow rule all still bind.

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

A poyar whose couplets each stand alone is **broken even when every rhyme in the
poem passes**. Before writing, fix the through-line — the single movement the whole
poem makes — and let every couplet take the next step of it.

## Length — default 16 couplets (32 lines)

**The default poyar is 16 couplets = 32 verse lines.** Use that unless an explicit
instruction says otherwise — it is the standard shape this skill composes to.

Measured against real poyar drafts, a couplet runs **~12 words** (2 lines × ~6
words), so the default 32-line poem lands near **195 words**. It is therefore
*shorter* than a typical 300-word `word_target`; that is expected and is not a
defect.

Resolution order, highest first:

1. **Explicit line/couplet count** in the invocation, `override.md`, or
   `filters/override/filter.md` (e.g. "20 lines are enough", "12 couplets").
   Always wins — a directive of "20 lines" means **20 couplets = 40 lines**.
2. **`word_target`** from the chapter's `chapter.json`, then the matching
   `book.json` `chapters[]` entry, then the book-level value — but **only when it
   is explicitly marked as binding for this chapter**. When it is the ordinary
   book-wide value, the default shape wins.

   ```text
   couplet_count = round(word_target / 12)          # 300 words → 25 couplets
   ```

3. **Default** — **16 couplets / 32 lines** (~195 words).

A 14-**akshar** line holds roughly **6–7 words**; a couplet roughly **12**.

- Do not stop early because the couplets "feel finished".
- Do not pad: never add a couplet that repeats a step already taken.
- To grow, **advance the argument** — a new image, a new turn, a new consequence.
- Report the resolved count and its source (directive, `word_target`, or default),
  and if a count constraint puts the poem under `word_target`, say so plainly
  rather than silently undershooting.

## Register — Borrow Srijato's Lexicon, Not Its Form

Take the daily-used spoken word over the literary one.

- **Never inflate a word to reach 14 akshar.** `শুধু` → `শুধুই` is a register
  break and is forbidden. Add another **everyday clause** instead:

  ```text
  short (11 ak):  অপেক্ষা মানে শুধু আশা
  ok   (14 ak):  অপেক্ষা মানে সারাক্ষণ পাহারা আশা     ← added a spoken clause
  ```

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

## Style Resolution and Caching (default: `poyar`)

Poyar is form-bound. When this skill runs and no other style is named, the style
is **`poyar`** — resolved from `.framework/editor/poetry/styles/poyar/`:

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
   contract still states the 14-akshar target in the `8 + 6` couplet measure
   (with the ±10 % / 12–16 band). **Use it. Do not regenerate.** Regeneration on
   every write is a cache miss by construction and is forbidden.
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

1. `.framework/editor/poetry/styles/poyar/sample.txt` — extract the **method**:
   couplet pairing, the `8 + 6` akshar measure, the daily-used register, the
   plain-concrete anchoring, the oral narrator's address.
2. `.framework/editor/poetry/styles/poyar/signature.md` — the distilled pattern.
3. `.framework/editor/poetry/styles/poyar/style.md` — the full contract.
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
| Form Contract | couplets, **14 akshar target** with **12–16 band** (±10 %), `8 + 6` caesura, strong L1~L2, **no cross-couplet rhyme** |
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
meter: akshar-14
grounded_from: .framework/editor/poetry/styles/poyar/{sample.txt,signature.md,style.md}
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
3. `filters/override/filter.md` and `override.md` — craft directives. Binding.
   Apply silently; never quote them as lines.
4. `storyline.md` — thematic grounding. Invent nothing beyond it.
5. `workspaces/pipeline/<bookname>/style.md` — the **cached, book-grounded poyar
   reference** (resolve it per *Style Resolution and Caching* above; synthesize it
   only on a cache miss).
6. `.framework/editor/poetry/styles/poyar/{signature.md,sample.txt}` — form and
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

A couplet must read as a **real sentence**, not a decorative fragment. The poem must
read as one argument, not a list of rhymes.

### Phase 1 — Fix the rhyme pair before writing either line

A couplet is only as good as its rhyme; a beautiful line 1 cannot rescue a weak
pair. Choose the **end words first**, then write the two lines around them.

1. Choose end word **A** that the meaning needs.
2. Find a partner **B** with `word.rhyming-words`, then confirm
   `word.rhyme-test(A, B) >= 1` **and** an identical final rhyme unit
   (`verse.py rhyme A B`, exit 0). Do **not** select on `word.rhyme-rank`: `Rank`
   is the word's position inside its rhyme class, not a quality score.
3. If **A** has no strong partner, **discard A** and choose another end word.
   Never plan a line around an end word with no verified rhymate.

### Phase 2 — Write line 1 at 8 + second foot

Write the opening line as a complete, singable statement in the daily register,
ending on **A**. Then measure it:

```bash
python tools/mcpbangla/verse.py measure <file-or-line>
```

- The line **targets 14 akshar** and passes anywhere in **12–16**. Keep the first
  foot at **8** akshar on a word boundary (the caesura) and let the second foot run
  **4–8**.
- If it is below 12, add an **everyday clause**; if it is above 16, cut the least
  essential modifier. Never inflate a word into its literary form to reach 14.
- Inside the band, **do not adjust** — a 13 or 15 akshar line that reads well is
  correct and final.

Do not carry an out-of-band line forward: fix it before writing line 2.

### Phase 3 — Write line 2 at 8 + second foot

Close the pair on **B** as the continuation of line 1's sentence — one sentence
across the two lines, not two statements. Measure it the same way: **12–16 akshar**
(target 14), first foot **8** on a word boundary, ending on **B**.

### Phase 4 — Verify the couplet, then continue

Before appending, confirm all five gates with MCP:

1. both lines are **within 12–16 akshar**, target 14 (`word.akshar-count`);
2. both lines read **`8` + 4–8** — a word boundary at akshar 8;
3. `word.rhyme-test(A, B) >= 1`;
4. the two ends share an **identical final rhyme unit** (STRONG) — `verse.py rhyme`
   exits non-zero when they do not;
5. the ends are **distinct** (a repeated end word is a redif and fails), and the
   pair is **not already used earlier in this poem**.

If line 2 cannot satisfy the rhyme, **rewrite line 1** — shuffle its words or
replace it — rather than accept a weak pair.

Then move to the next couplet. Its rhyme class is free — deliberately do **not**
chain the sound from the previous couplet. Its *meaning* must continue the previous
couplet's thought, and it must **add a new step** to the argument, not restate the
last one.

**Append each verified couplet to the file immediately** (see *Incremental
Persistence* below). Do not hold finished couplets in memory to write them at the
end.

## Incremental Persistence (write each couplet as it is verified)

The chapter file is the work-in-progress, not a final dump. **Every verified couplet
is written to disk before the next one is composed.**

### Open the draft (once, before the first couplet)

1. **Archive** any existing `chapter.md` to
   `chapters/<n>/segments/1/version/chapter_v<k>.md`
   (`<k>` = highest existing + 1; never overwrite an archive).
2. **Truncate** `chapter.md` to the title and one blank line:

   ```markdown
   # {chapter_title}

   ```

### Append after each couplet passes

A couplet is appended **only** when it satisfies, in this order:

1. both lines measure **within 12–16 akshar** (target 14);
2. `word.rhyme-test(L1_end, L2_end) >= 1`;
3. the two end words share an **identical final rhyme unit** (STRONG);
4. the ends are **distinct** (no redif);
5. the rhyme pair is **not already used earlier in this poem**.

Then append the two lines plus a blank line, in the output shape of the next
section. Never append an unverified pair "to fix later" — a rejected couplet is
reworked in place, never written.

### Resumability (a hard requirement)

Because the file only ever holds verified couplets, an interrupted run leaves a
**valid shorter poem**, not a corrupt draft:

- On start, if `chapter.md` already holds `k` complete couplets (title + 2k verse
  lines), treat them as done and resume at couplet `k + 1`.
- Re-audit the existing lines before continuing; if any line fails, repair that
  couplet before appending anything new.
- Never restart from zero just because the target count was not reached.

### Progress reporting

Report the count after each append (e.g. `7/16 couplets written`), so a long run
shows its state on disk rather than only at the end.

## Review Loop — Python reports, the agent repairs

`review` is the report stage of the write → review → repair loop. It is
**read-only**: it prints a per-line, per-word verdict and never touches the file.

```bash
python tools/mcpbangla/verse.py review workspaces/pipeline/<book>/chapters/<n>/chapter.md --form poyar
python tools/mcpbangla/verse.py review <file> --form poyar --json   # machine-readable
```

The report is what the agent reads to find its own errors. Per line it gives the
total akshar, the delta against the target, the band verdict, and the exact word
breakdown with cumulative counts:

```text
L02 [15 ak] PASS (+1 vs 14)
     বৈশাখ মাসে তার হাঁটু জল থাকে না
     words: বৈশাখ(3→3)  মাসে(2→5)  তার(2→7)  হাঁটু(2→9)  জল(2→11)  থাকে(2→13)  না(1→14)
     caesura: 9 + 5 at word 4 (off by +1 vs 8)
```

Per couplet it gives the rhyme test, strength, and both rhyme units:

```text
c02 হাত/রাত rhyme=2 STRONG units 'াত'/'াত' PASS
```

Repair rules for the agent:

- Act **only** on the lines and couplets the report flags. Do not rewrite a
  passing line.
- `SHORT` — add an everyday clause; never inflate a word to its tatsama form.
- `LONG` — cut the least essential modifier.
- `off by ±n` on the caesura — move a word across the boundary; the `8` foot is
  the anchor, so prefer adjusting the second foot.
- `WEAK` or `rhyme=0/-1` — rework line 1 and choose a new end word with a verified
  strong partner.
- `REDIF` — the two ends are the same word; replace one.

Re-run `review` after every repair batch. The loop exits only on `=== PASS ===`.

## Final Verification

After the last couplet is appended:

```bash
python tools/mcpbangla/verse.py review workspaces/pipeline/<book>/chapters/<n>/chapter.md --form poyar
python tools/mcpbangla/verse.py audit  workspaces/pipeline/<book>/chapters/<n>/chapter.md --form poyar
```

`review` must print `=== PASS ===` and the audit must print `=== PASS ===`. If
either fails on a couplet written earlier, repair that couplet in place and re-run
both. Then record the form evidence in `chapter.json` (`stanza_count`,
`line_count`, `akshar_counts`, and the per-couplet `mcp_verification` block).

## Output Shape

```markdown
# {chapter_title}

<line 1 — 14 akshar target (12–16), 8 + 2nd foot>
<line 2 — 14 akshar target (12–16), 8 + 2nd foot, rhymes line 1>

<line 3 — 14 akshar target (12–16), 8 + 2nd foot>
<line 4 — 14 akshar target (12–16), 8 + 2nd foot, rhymes line 3>

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
  "stanza_count": 16,
  "line_count": 32,
  "rhyme_scheme": "AA",
  "rhyme_scheme_note": "L1~L2 inside each couplet; no cross-couplet rhyme",
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
    "rhyme_tool": "word.rhyme-test + identical final rhyme unit",
    "all_rhymes_verified": true,
    "all_rhymes_strong": true,
    "all_lines_in_band": true,
    "akshar_delta": 0,
    "couplets": [
      {"couplet": 1, "L1_end": "…", "L2_end": "…", "rhyme": "1",
       "strength": "STRONG", "rhyme_unit_L1": "…", "rhyme_unit_L2": "…",
       "distinct": true, "L1_akshar": 14, "L2_akshar": 13,
       "L1_in_band": true, "L2_in_band": true}
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
- Never use MCP or Python to generate, complete, or rewrite a line; MCP measures
  and Python reports only. Every line is authored by the agent.
- Never compute akshar or rhyme facts natively; every count comes from MCP.
- Never plan a couplet around an end word with no verified strong partner.
- Never accept an unverified rhyme; `word.rhyme-test` **and** the strength test must
  both pass.
- Never measure poyar by syllables — it is an akshar form.
- Every line inside the **12–16 akshar** band (±10 % of 14), keeping the first
  foot at 8; a line outside the band is rewritten. Inside the band, never rewrite
  a line merely to make it read 14.
- Never accept a weak rhyme; `0` is not a rhyme and `1` alone is not proof.
- Never accept an identical end pair (redif).
- Never rhyme across couplets.
- Never inflate a word to its literary form to make the count.
- Never leave couplets as isolated vignettes — flow is part of the contract.
- **Never hold verified couplets in memory** — append each one to `chapter.md` as
  soon as it passes, so an interrupted run leaves a valid shorter poem.
- Never append an unverified couplet "to fix later"; rework it in place instead.
- Never restart a partially written chapter from zero — resume after the couplets
  already on disk.
- Never write `chapter.md` without archiving the prior copy first.
- Never revert a cache marked `human_edited: true`.
- Write only inside `workspaces/pipeline/<bookname>/`. Never promote to
  `workspaces/published/` — that is `publish`.
- Valid only for books with `form: poetry`.

## Audit Tooling

| Script | Use |
|---|---|
| `tools/mcpbangla/verse.py review <file> --form poyar` | **report-only** per-line, per-word review for the repair loop; `=== PASS ===` required |
| `tools/mcpbangla/verse.py audit <file> --form poyar` | full contract audit; `=== PASS ===` required (target 14, band 12–16) |
| `tools/mcpbangla/verse.py measure <file> --syllable` | per-line akshar (and syllable, for reference) |
| `tools/mcpbangla/verse.py rhyme A B` | single pair; exit 1 on weak or non-rhyme |
| `tools/mcpbangla/verse.py family <word>` | verified rhyme-class candidates |
| `tools/mcpbangla/kamolika.py` | MCP HTTP client (`BASE_URL`), imported not run |

`--floor N` on the audit sets the **akshar target** per line (default 14), and
`--akshar-tolerance N` sets the allowed drift (default `ceil(N × 10%)`, so 2 for a
target of 14 → band **12–16**). The name `--floor` is legacy: it is a target, not a
minimum. These scripts are permanent — never delete or rewrite them inline.

## Report Format

```
Poyar Report
Book     : <bookname>
Chapter  : <n>
Mode     : poyar (14-akshar couplets, 8 + 6, band 12–16)
Style    : poyar (<reused|synthesized> → workspaces/pipeline/<bookname>/style.md)
Target   : 16 couplets / 32 lines (default) | <count directive> | <word_target> words
Language : <language>

Couplets:
  c01 [14/13 ✓] হাত/রাত   rt=1 STRONG
      <line 1>
      <line 2>
  ...

Summary:
  Couplets    : <n>/<n> within band 12–16 akshar (8 + 2nd foot)
  Line length : <exact-n>/<total> at exactly 14 | band <total>/<total> pass
  Strong rhyme: <n>/<n>
  Review      : PASS (per-line/per-word report attached on failure)
  Audit       : PASS
  Written     : incremental (last append at couplet <n>)
  Flow        : <the through-line the poem follows>
  Reused pairs: none
```
