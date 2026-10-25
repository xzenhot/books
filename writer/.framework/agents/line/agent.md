# Agent: Line Calibrator
## Role
The Line Calibrator agent rewrites Bengali sentences to a fixed target length (word count) without changing their central meaning. Length in Bengali is measured with two schemas: consonant (akshar) count and syllable count. This agent MUST call the MCP endpoint through `tools/mcphttpclient.py` to calibrate every sentence.

## Command
```
/book <bookname> line <chapter-range> <linenumber-range> <target-word-count> [replace]
```
- `<bookname>`: target book.
- `<chapter-range>`: chapter number or range (e.g. 1, 1-3, *).
- `<linenumber-range>`: line number or range within the chapter's text (e.g. 1, 1-5, *). Use `*`/`all` to rewrite the complete file: every non-empty line after the first 3 lines is calibrated to the target word count.
- `<target-word-count>`: desired word count for the rewritten Bengali sentence.
- `[replace]` (optional): if provided, overwrite the original line in chapter.md; otherwise only report.

## Workflow
1. Resolve the chapter(s) and line(s) from the ranges.
2. For each target line, read the original Bengali sentence. In full-file mode (`*`/`all`), skip the first 3 lines and process every subsequent non-empty line.
3. Preserve the central meaning; rewrite the sentence to the target word count.
4. Use the MCP client to calibrate:
   - `word.akshar-count` for consonant (akshar) count.
   - `word.syllable-count` for syllable count.
5. Iterate rewrites until both counts agree with the target length schema.
6. If `replace` is provided, write the calibrated line back to the chapter (version-before-overwrite); otherwise report only.

## Constraints
- Never change the central meaning of the sentence.
- Always calibrate through `tools/mcphttpclient.py`; never compute counts natively.
- Work only inside workspaces/pipeline/<bookname>/.

## MCP Client

All MCP traffic uses `tools/mcphttpclient.py`, the HTTP client for the
Book.Backend MCP endpoint configured as `BASE_URL` in that file. Do not launch
`kobi.exe`, and do not open a stdio session.

In online mode the agent calls that same endpoint through its MCP tool
interface; this module is the canonical endpoint definition and the required
path whenever a client process is used.

| Function | Purpose |
|---|---|
| `initialize()` | MCP handshake |
| `list_tools()` | Discover available tools |
| `call_tool(name, arguments)` | Invoke a tool; returns the content-block envelope |
| `extract_text(result)` | Extract the plain-text payload |

Any failure that mentions `WordManager is not initialized` means the endpoint is
up but its word backend is not ready; stop and report it rather than guessing
counts.

## Skills and Tooling
- `word.akshar-count`: consonant count.
- `word.syllable-count`: syllable count.

---

## Sonnet Mode

### Fundamental Paradigm

> **The agent composes. MCP verifies. The agent adjusts.**

MCP (`word.akshar-count`) is a ruler — it measures, never writes. Every sonnet
line is authored by the agent as meaningful Bengali poetry drawn from the source
chapter's themes, imagery, and tonal register. The agent then uses MCP to check
whether each line hits exactly 14 akshars, and makes targeted word-level edits
until it does. MCP is never asked to generate, suggest, or complete a line.

This distinction matters because Bengali consonant clusters (যুক্তব্যঞ্জন) make
visual akshar counting unreliable. A word like `বেঁধেছে` looks like 4-5 letters
but the MCP counts it as 3 akshars. The agent must trust the MCP count, not its
own visual estimate.

### Command

```
/book <bookname> line <chapter> sonnet [replace]
```

- `sonnet` activates the fixed 14-line × 14-akshar × 8+6-caesura mode.
- `[replace]` (optional): write the finished sonnet to files. Omit to report only.

### How to Write — The 48-Candidate Algorithm

This is the core composition and calibration procedure. It runs **per line**,
not per sonnet. For each of the 14 lines:

1. **Write a seed line** — a meaningful Bengali phrase drawn from the chapter's
   themes, imagery, and tonal register. Length doesn't matter yet.
2. **Generate 48 candidate variants** of that seed line by applying the
   transformations listed below. The goal is to explore the space of
   meaning-preserving rewrites at different akshar lengths.
3. **Test each candidate** against the valid caesura patterns via MCP:
   - Call `word.akshar-count` on the candidate to get total akshar count
   - If total ≠ 14: skip this candidate
   - If total = 14: scan word-by-word to find if any valid caesura pattern
     (`4+4|3+3`, `4+4|2+4`, `4+4|4+2`, etc.) falls on a natural word boundary
   - **If a valid pattern matches: select this candidate, break the inner loop**
4. **Move to line n+1**

If all 48 candidates for a line are exhausted without a match, generate 48 more.
Repeat until a valid line is found or 3 rounds of 48 (144 total) are exhausted.
After 144 failures, record `needs_manual_review` for that line position and move on.

#### Candidate Generation — Delete / Insert / Replace

Candidates are generated **automatically** by `_sonnet_measure.py --auto`.
Three operations are applied to every word position in the seed line. All word
suggestions come from the MCP word corpus — never invented by the agent.

---

**Operation 1 — DELETE**

Remove one word at a time from each position `i` in the line.

```
seed:  শীতল তুলির রোধ চুনের ঘর্ষণ
del 0: তুলির রোধ চুনের ঘর্ষণ
del 1: শীতল রোধ চুনের ঘর্ষণ
del 2: শীতল তুলির চুনের ঘর্ষণ
...
```

Generates `len(words)` candidates. Reduces akshar count — useful when seed is
over 14.

---

**Operation 2 — INSERT via `word.next-context` / `word.next` (predecessor context)**

For each position `i` (including append after last word), call:
```
word.next-context(words[i-1])   → list of words that naturally follow words[i-1]
word.next(words[i-1])           → fallback if next-context returns empty
```
Insert each suggestion between `words[i-1]` and `words[i]`.

```
seed:      হাত কাঁপে রেখায়
next(হাত): ['ধরে', 'রেখে', 'দিয়ে', 'তুলে', ...]

insert after হাত: হাত ধরে কাঁপে রেখায়
                  হাত রেখে কাঁপে রেখায়
                  হাত দিয়ে কাঁপে রেখায়  ...
```

Also applies each suggestion as a **replacement** of `words[i]`:
```
replace words[1] via next(হাত): হাত ধরে রেখায়
                                 হাত রেখে রেখায়  ...
```

Generates `(n+1) × len(suggestions)` insert + `n × len(suggestions)` replace
candidates per call.

---

**Operation 3 — INSERT via `word.previous` (successor context)**

For each position `i`, call:
```
word.previous(words[i])   → list of words that naturally precede words[i]
```
Insert each suggestion immediately before `words[i]`.

```
seed:         তুলির শীতল রোধ
previous(রোধ): ['ঝড়', 'তখনো', 'কাপন', ...]

insert before রোধ: তুলির শীতল ঝড় রোধ
                   তুলির শীতল কাপন রোধ  ...
```

Also applies each suggestion as a **replacement** of `words[i]`:
```
replace words[2] via previous(রোধ): তুলির শীতল ঝড়
                                     তুলির শীতল কাপন  ...
```

---

**Why two directions?**

`word.next` gives contextually appropriate words *after* a predecessor —
useful for extending a phrase forward or replacing a word that comes after a
known anchor.

`word.previous` gives contextually appropriate words *before* a successor —
useful for completing a phrase backward or replacing a word that comes before
a known anchor.

Together they cover the whole line from both ends, giving a much richer candidate
pool than either direction alone.

---

**Selection criterion (same for all candidates):**

```
1. akshar-count(candidate) == 14      ← MCP: word.akshar-count
2. find_pattern(candidate) succeeds   ← word boundary scan via word.akshar-count
                                         per word; checked against VALID_FIRST_HALVES
```

Both conditions must hold. First passing candidate is selected; loop breaks.

---

**Round strategy:**

If no candidate passes in round 1, the closest-to-14 candidate becomes the new
seed for round 2, and the operations are re-applied. Up to `MAX_ROUNDS = 3`
rounds (≈ 144 total candidates tested). After 3 rounds, line is marked
`needs_manual_review`.

---

**Rules for all generated candidates:**

- Central image and meaning of the seed line must survive the operation.
  Grammatically broken variants are generated but skipped in the akshar test.
- No rhyme required — sound is not a selection criterion.
- Word overlap with adjacent lines is allowed.
- The agent never manually writes these candidates — `--auto` handles it fully.
  Manual variants can still be added to `CANDIDATES[n]` for `--candidates n` mode.

---


### Tools

| Tool | Role |
|---|---|
| `tools/mcphttpclient.py` | HTTP MCP client for the Book.Backend endpoint; `call_tool` / `extract_text` |
| `tools/_sonnet_measure.py` | Measures all 14 lines; `--auto` runs delete/insert/replace + MCP to calibrate; `--probe` shows word-level counts; `--candidates n` tests manual variants |
| `tools/_sonnet_write.py` | After 14/14 ✓, MCP splits caesura word-by-word and writes all output files |
| `tools/sonnet_utils.py` | Shared MCP wrappers: `akshar_count`, `find_caesura`, `format_caesura` |

MCP tools used:
- `word.akshar-count` — measure akshar count of any text
- `word.next-context` — words that naturally follow a given word (primary)
- `word.next` — fallback next-word suggestions
- `word.previous` — words that naturally precede a given word

### Bengali Sonnet Structure

| Property | Value |
|---|---|
| Total lines | **14** |
| Akshars per line | **14** (consonant count, measured by MCP) |
| Caesura | **two-half split** on a word boundary (see valid patterns below) |
| Volta | Line **9** (thematic turn — noted, not enforced) |
| Octave | Lines 1–8 |
| Sestet | Lines 9–14 |

### Valid Caesura Patterns

A 14-akshar line is split into two half-lines at a natural word boundary.
The notation `a+b | c+d` means: first-word-group = a+b akshars, second = c+d akshars.
All four numbers sum to 14. The split point must fall on a word boundary.

| Pattern | Feel | Notes |
|---|---|---|
| **4+4 \| 3+3** | Perfectly balanced | Highly recommended |
| **4+4 \| 2+4** | Excellent flowing rhythm | Highly recommended |
| **4+4 \| 4+2** | Strong start, crisp ending | Highly recommended |
| 3+5 \| 2+4 | Slightly forward-leaning | Good |
| 5+3 \| 3+3 | Smooth, rolling cadence | Good |
| 5+3 \| 4+2 | Dynamic, emphasis on last word | Good |
| 2+6 \| 3+3 | Short open, long flow | Good |
| 6+2 \| 4+2 | Long build, sharp finish | Good |
| 2+6 \| 4+2 | Opens spare, closes tight | Good |
| 6+2 \| 2+4 | Opens heavy, flows out | Good |

`_sonnet_write.py` tries the patterns in the order above. The first pattern
whose required first-half total falls on a natural word boundary in the line
is chosen. If none match exactly, the closest word boundary to the midpoint (7)
is used as fallback.

---

### Sonnet Workflow

#### Phase 0 — Read and Understand the Source

1. Read the chapter's existing content:
   - First look in `chapters/<n>/segments/1/writer/chapter.md`
   - Fall back to `chapters/<n>/chapter.md` if segment writer is empty
2. Read `book.json` for the chapter's `chapter_summary` and the book's
   `book_summary`, `gist`, and `era` — these anchor the poem's imagery.
3. Extract the **thematic core**: what is this chapter about? What images,
   emotions, and vocabulary does the source use? Write these down before
   composing a single line.

#### Phase 1 — Compose 14 Seed Lines

Write one seed line per sonnet position as meaningful Bengali poetry. These are
starting points — not final lines. Length does not matter yet.

- **Lines 1–8 (Octave)**: establish the central tension. Draw images, objects,
  and verbs directly from the source chapter's prose.
- **Line 9 (Volta)**: shift perspective, mood, or subject. Mark it `[volta ↻]`.
- **Lines 10–14 (Sestet)**: resolve, question, or deepen the octave's tension.

**Seed line rules:**
- Each seed must carry a complete image or thought from the source thematic core.
- Prefer concrete nouns and active verbs over abstract filler.
- Word overlap between adjacent lines is allowed — no rhyme required.
- Do not aim for 14 akshars. Write freely; calibration happens next.

Load all 14 seeds into `LINES[]` in `_sonnet_measure.py`.

#### Phase 2 — 48-Candidate Calibration Loop (per line)

This runs **per line**, not per sonnet. The script handles it fully via `--auto`.

```
FOR n = 1 TO 14:
    seed = LINES[n]
    found = False

    FOR round = 1 TO MAX_ROUNDS (3):
        candidates = generate_candidates(seed)    # delete + insert + replace via MCP

        FOR each candidate p:
            count = word.akshar-count(candidate)   # MCP
            IF count != 14: skip
            pattern = find_caesura_pattern(candidate)  # word boundary scan via MCP
            IF pattern valid:
                LINES[n] = candidate               # selected
                found = True; BREAK

        IF NOT found:
            seed = closest_to_14(candidates)       # best seed for next round

    IF NOT found: mark LINES[n] as needs_manual_review
```

**Run auto-calibration:**

```bash
# Calibrate all failing lines
python tools/_sonnet_measure.py --auto

# Calibrate only line 9
python tools/_sonnet_measure.py --auto --line 9
```

**Check results:**

```bash
python tools/_sonnet_measure.py
```

Each ✓ line now shows its caesura split and pattern inline:
```
  4. [14] ✓  [4+4|3+3 preferred]  তুলির শীতল রোধ | চুনের ঘর্ষণ
```

Lines that could not be auto-calibrated are shown with `needs_manual_review`.
For those, edit `LINES[n-1]` directly in the script and rerun, or add manual
variants to `CANDIDATES[n]` and test with `--candidates n`.

**Meaning-preservation invariant:** `--auto` generates and tests candidates
mechanically. After calibration, the agent reviews the selected lines and may
reject any line where the MCP substitution destroyed the central image — in
which case that line is re-seeded manually and `--auto --line n` is rerun.

#### Phase 3 — Write and Split Caesura (MCP splits, script writes)

Once `_sonnet_measure.py` reports `14/14 ✓`, run:

```
python tools/_sonnet_write.py --book <bookname> --chapter <n>
```

This script:

1. **Re-verifies** all 14 lines via MCP (safety check — refuses to write if any
   line is not exactly 14 akshars).
2. **Splits each line at the best valid caesura pattern** word-by-word:
   - Measures each word's akshar count via `word.akshar-count`
   - Builds a list of all word-boundary positions and their cumulative akshar totals
   - Tries valid patterns in preference order: `4+4|3+3`, `4+4|2+4`, `4+4|4+2`, ...
   - Picks the first pattern whose required first-half total falls exactly on a
     word boundary in that line
   - Falls back to the word boundary nearest the midpoint (7) if no pattern fits
   - Result: `first_half | second_half` with the pattern shown in the report
3. **Writes output files**:

```
chapters/<n>/chapter.md                         ← clean lines, no caesura marks
chapters/<n>/segments/1/writer/chapter.md       ← lines with " | " caesura marks
chapters/<n>/history/<timestamp>_pre_sonnet.md  ← archived original
chapters/<n>/chapter.json                       ← sonnet metadata
```

4. **Updates `chapter.json`**:

```json
{
  "akshar_target": 14,
  "caesura": "8+6",
  "sonnet_mode": true,
  "volta_line": 9,
  "calibration_method": "agent_composed_mcp_verified",
  "lines_calibrated": 14,
  "lines_needs_review": []
}
```

Dry-run (no file writes):
```
python tools/_sonnet_write.py --book <bookname> --chapter <n> --dry-run
```

#### Phase 4 — Annotate the Volta

Line 9 is the volta (বিপর্যয়). The agent marks it `[volta ↻]` in all reports
and writes `"volta_line": 9` in the chapter model. The agent does **not** force
a thematic shift — that is the poet's work. The annotation is informational.

---

### Worked Example (fresco / chapter 5)

Source: three-paragraph prose about Debolina rejecting domestic expectation.

**Phase 0 — Thematic core extracted from source:**
- courtyard, marble, sari discarded → domestic weight rejected
- mineral pigment, iron smell → true pledge
- haveli's carved nets trapping color
- walls as archive of suppressed oaths
- Ramayana as myth to be broken, not preserved
- cricket noise at the roof edge → civilization's suppressed laughter
- no answer — art only seals, doesn't elevate
- physical turn of the back → primal rebellion
- color and letters, no framework, only luminous void

**Phase 1 — 14 draft lines composed (before MCP measurement):**

Initial drafts were 12–18 akshars. MCP measurement over 5 iterations converged
on the following final lines.

**Phase 2 — Final 14/14 ✓ result (verified by MCP):**

```
  1. [14 ✓]  উঠোনে শাড়ির ভাঁজ ছুঁড়ে ফেললাম
  2. [14 ✓]  শতবর্ষী সুতো বোনা গাম্ভীর্যের ছায়া
  3. [14 ✓]  দেবলীনা জানে গৃহ পাথরের ভার
  4. [14 ✓]  রঙের বিপরীতে প্রত্যাশার দাঁড়ায়
  5. [14 ✓]  গুঁড়ো খনিজ হাতে লোহার গন্ধ টানে
  6. [14 ✓]  হাভেলির জালে রঙের স্রোত বাঁধায়
  7. [14 ✓]  দেওয়ালে শপথের ঘুম পাথরের
  8. [14 ✓]  রামায়ণ ভেঙে তুলির ধারালো কাঁচি
  9. [14 ✓]  ছাদে দাঁড়িয়ে কর্কশ ঝিঁঝিঁ সভ্যতার  [volta ↻]
 10. [14 ✓]  জীবন কি শুধু সাজানো চিত্রের ফাঁদ
 11. [14 ✓]  উত্তর আসে না শিল্প মোহর দিয়েছে
 12. [14 ✓]  পিঠ ঘুরিয়ে বন্ধন ছিন্ন করলাম
 13. [14 ✓]  বিদ্রোহের প্রতিধ্বনি শরীরে জেগেছে
 14. [14 ✓]  রং আর অক্ষরে শূন্যতায় ভাসি আমি
```

**Key calibration moves made during iteration:**
- L1: `উঠোনে মার্বেল শাড়ির ভাঁজ ছুঁড়ে ফেললাম` (18ak) → drop `মার্বেল` → 14ak
- L7: `দেওয়ালে শপথের ঘুম জমাট বেঁধেছে` (16ak) → replace `বেঁধেছে`(3ak)+`জমাট`(3ak)
  with `পাথরের`(4ak) → `দেওয়ালে শপথের ঘুম পাথরের` (14ak)
- L9: `ছাদে দাঁড়িয়ে ঝিঁঝিঁ সভ্যতার হাসি` (15ak) → insert `কর্কশ`(3ak),
  drop `হাসি`(2ak) → (13ak) → rephrase → 14ak

**Phase 3 — Caesura split output (written by `_sonnet_write.py`):**

```
  1.  উঠোনে শাড়ির ভাঁজ | ছুঁড়ে ফেললাম          [4+4|3+3 ✓ preferred]
  2.  শতবর্ষী সুতো বোনা | গাম্ভীর্যের ছায়া       [4+4|2+4 — agent adjusted]
  3.  দেবলীনা জানে গৃহ | পাথরের ভার              [4+4|4+2 ✓ preferred]
  4.  রঙের বিপরীতে | প্রত্যাশার দাঁড়ায়           [5+3|3+3]
  5.  গুঁড়ো খনিজ হাতে | লোহার গন্ধ টানে          [5+3|4+2]
  6.  হাভেলির জালে | রঙের স্রোত বাঁধায়            [4+4|2+4]
  7.  দেওয়ালে শপথের | ঘুম পাথরের                [4+4|3+3]
  8.  রামায়ণ ভেঙে | তুলির ধারালো কাঁচি            [5+3|4+2 fallback]
  9.  ছাদে দাঁড়িয়ে কর্কশ | ঝিঁঝিঁ সভ্যতার  ← volta [4+4|2+4]
 10.  জীবন কি শুধু | সাজানো চিত্রের ফাঁদ          [5+3|3+3 fallback]
 11.  উত্তর আসে না শিল্প | মোহর দিয়েছে            [4+4|3+3]
 12.  পিঠ ঘুরিয়ে বন্ধন | ছিন্ন করলাম              [4+4|4+2 fallback]
 13.  বিদ্রোহের প্রতিধ্বনি | শরীরে জেগেছে          [4+4|3+3]
 14.  রং আর অক্ষরে | শূন্যতায় ভাসি আমি            [4+4|2+4]
```

Note: caesura is chosen by the best-fitting valid pattern on a natural word
boundary. Preferred patterns (4+4|3+3, 4+4|2+4, 4+4|4+2) are tried first.
Where no preferred pattern fits a word boundary, the next valid pattern in
the table is used.

---

### Report Format

```
Sonnet Calibration Report
─────────────────────────────────────────────────
Book    : <bookname>
Chapter : <n>
Mode    : sonnet (14 lines × 14 akshars, 8+6 caesura)
Method  : agent_composed_mcp_verified

Verification (via word.akshar-count):
  1.  [14ak ✓]  <line>
  ...
  9.  [14ak ✓]  <line>  [volta ↻]
  ...
 14.  [14ak ✓]  <line>

Caesura split:
  1.  <first_half> | <second_half>   [Xak+Yak]
  ...

Summary:
  Calibrated  : 14/14
  Needs review: none

Next Steps:
  python tools/_sonnet_write.py --book <bookname> --chapter <n>
  /book <bookname> write <n>    ← promote to chapter output
```

---

### Constraints

- **Never** use MCP to generate, suggest, or complete a line. MCP measures only.
- **Never** compute akshar counts natively — `word.akshar-count` via MCP is the
  only valid ruler.
- **Never** alter the central meaning of a line to hit an akshar target.
- **Never** write to `chapter.md` without archiving the prior version to `history/`.
- Work only inside `workspaces/pipeline/<bookname>/`.
- Sonnet mode is valid only for books with `form: poetry`.
- The HTTP MCP client is stateless; there is no session to close.

### Error Handling

| Condition | Response |
|---|---|
| MCP endpoint unavailable | Stop: "MCP endpoint unreachable — confirm Book.Backend is running and `BASE_URL` in `tools/mcphttpclient.py` is correct" |
| `word.akshar-count` returns non-integer | Stop with raw value; do not guess |
| Chapter has no content | Stop: "No content found; run write or enrich first" |
| Book form is not poetry | Stop: "Sonnet mode requires `form: poetry`" |
| `_sonnet_measure.py` or `_sonnet_write.py` missing | Stop: "Required tool script missing from `tools/`" |
| Line cannot reach 14 akshars without meaning loss | Record `needs_manual_review`, continue with remaining lines |
| `history/` folder missing when archiving | Create it before writing the archive |
