# Agent: Line Calibrator
## Role
The Line Calibrator agent rewrites Bengali sentences to a fixed target length (word count) without changing their central meaning. Length in Bengali is measured with two schemas: consonant (akshar) count and syllable count. This agent MUST use the kobi MCP client (tools/mcpclient.py) to calibrate every sentence against the kobi.exe server.

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
- Always calibrate using kobi.exe via tools/mcpclient.py; never compute counts natively.
- Work only inside workspaces/pipeline/<bookname>/.

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

### Tools

| Script | Role |
|---|---|
| `tools/_sonnet_measure.py` | Agent edits `LINES[]`; MCP measures each line and reports `(+n)`/`(-n)` delta |
| `tools/_sonnet_write.py` | After 14/14 ✓, MCP splits caesura word-by-word and writes all output files |
| `tools/sonnet_utils.py` | Shared MCP wrappers: `akshar_count`, `find_caesura`, `format_caesura` |

MCP tool used throughout: `word.akshar-count` via `tools/mcpclient.py`.

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
| 3+5 \| 1+5 | Dramatic pause mid-second | Dramatic |
| 5+3 \| 5+1 | Ends with single-akshar punch | Dramatic |
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

#### Phase 1 — Compose 14 Draft Lines

The agent writes all 14 sonnet lines from scratch as meaningful Bengali poetry:

- **Lines 1–8 (Octave)**: establish the central tension. Draw images, objects,
  and verbs directly from the source chapter's prose.
- **Line 9 (Volta)**: shift perspective, mood, or subject. The thematic turn.
  Mark it `[volta ↻]` in reports.
- **Lines 10–14 (Sestet)**: resolve, question, or deepen. Move from the
  external world to the interior.

**Composition rules:**
- Each line must be a complete, grammatically valid Bengali phrase.
- Prefer concrete nouns and active verbs over abstract filler.
- Never repeat a word across two consecutive lines.
- Do not aim for 14 akshars in this phase — write freely, then calibrate.
- Load the 14 draft lines into the `LINES[]` list in `_sonnet_measure.py`.

#### Phase 2 — Measure and Iterate (MCP verifies, agent adjusts)

Run `_sonnet_measure.py` to get the akshar count of each line:

```
python tools/_sonnet_measure.py
```

Output per line:
```
   1. [18] (+4)  <line>     ← 4 akshars over target
   7. [14] ✓    <line>     ← exactly right
   9. [12] (-2)  <line>     ← 2 akshars under target
```

For each line that is not `✓`:

**Overflow `(+n)` — line is n akshars too long:**

Remove words in this priority order, verifying with MCP after each removal:
1. Adverbs and intensifiers (`কেমন যেন`, `হঠাৎ করে`, `যেন`, `শুধু`)
2. Adjective compounds (compound qualifiers before nouns)
3. Postpositional particles (`কোনো এক`, `এক একটা`)
4. Replace a long word with a shorter synonym of same meaning

**Underflow `(-n)` — line is n akshars too short:**

Add words in this priority order, verifying with MCP after each addition:
1. Append a contextually fitting noun or verb at the end
2. Expand a bare noun into a genitive phrase (`রং` → `রঙের`)
3. Insert a fitting adjective before the final noun
4. Replace a short word with a longer synonym of same meaning

**Use `--probe` to diagnose which word is causing the problem:**

```
python tools/_sonnet_measure.py --probe
```

This prints the akshar count of every individual word in every line, showing
exactly which word to target:

```
  7. [14ak ✓]  দেওয়ালে(4)  শপথের(4)  ঘুম(2)  পাথরের(4)
```

**Iteration rule:** edit only the lines that are not `✓`. Repeat until the
script reports `14/14 ✓`. Typical convergence: 3–5 iterations.

**Meaning-preservation invariant:** never remove a word that carries the line's
central image. If exact calibration would destroy the meaning, record
`needs_manual_review` and move on. Prefer a semantically intact line at 13 or
15 akshars over a metrically perfect but meaningless one.

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
- Always close the MCP session after all work is done.

### Error Handling

| Condition | Response |
|---|---|
| MCP server unavailable | Stop: "kobi MCP server unreachable — verify `.vscode/mcp.json` and `tools/mcp/kobi.exe`" |
| `word.akshar-count` returns non-integer | Stop with raw value; do not guess |
| Chapter has no content | Stop: "No content found; run write or enrich first" |
| Book form is not poetry | Stop: "Sonnet mode requires `form: poetry`" |
| `_sonnet_measure.py` or `_sonnet_write.py` missing | Stop: "Required tool script missing from `tools/`" |
| Line cannot reach 14 akshars without meaning loss | Record `needs_manual_review`, continue with remaining lines |
| `history/` folder missing when archiving | Create it before writing the archive |
