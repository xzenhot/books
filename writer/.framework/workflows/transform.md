# The Transform Workflow (Poetry Fixed-Line Calibration)

> **Audit metadata.** Every `.md`/`.json` file this workflow writes under
> `workspaces/` must carry `updated_by` and `updated_date` per
> `.framework/rules/audit-metadata.md`. The pipeline chapter tree
> (`workspaces/pipeline/<bookname>/chapters/**`) is exempt, so the calibrated
> chapter draft itself is never stamped.

This workflow transforms Bengali poetry chapters to fixed-length lines, where each line has exactly the target number of akshars (consonants). It uses the `line` agent to perform akshar count calibration via the `word.akshar-count` MCP tool.

**Additional Note: Sonnets**
A **sonnet** is a classic poetic form consisting of **14 lines** that follows a specific meter, rhyme scheme, and thematic structure.

Here are the universal rules, the most common styles, and a step-by-step guide to writing your own.

---

### The 4 Core Rules of a Sonnet

### The Two Main Sonnet Types

#### 1. Shakespearean (English) Sonnet — Best for beginners
This is the most common format in English poetry.

#### 2. Petrarchan (Italian) Sonnet
An older, slightly more challenging format because it requires more repeating rhymes.

### Step-by-Step: How to Write a Shakespearean Sonnet

#### Step 1: Pick a Subject with Built-in Tension
Sonnets traditionally deal with intense, conflicting emotions:

#### Step 2: Outline Your 4 Sections
Before rhyming, outline the logic:

#### Step 3: Write in Iambic Pentameter
Count syllables and check stress. Read each line aloud and tap the rhythm on a table:

#### Step 4: Craft the "Volta"
At line 9, change direction:

#### Step 5: Seal it with the Couplet
Lines 13 and 14 must rhyme with each other (**GG**). They should snap the poem shut like a lock:

**Phase**: Poetry line calibration
**Form**: Poetry only
**Primary Tool**: `word.akshar-count` via MCP client
**Agent**: `line` at `.framework/agents/line/agent.md`

## Command Invocation

```
/book <bookname> transform <chapter>|all|continue [<target_akshar>]
```

## Prerequisites

Before running transform, ensure:

1. **Pipeline exists** — `workspaces/pipeline/<bookname>/` must exist (use `scaffold` first`)
2. **Book form is poetry** — `book.json` must have `form: poetry`
3. **Line agent available** — `.framework/agents/line/agent.md` must exist
4. **Chapters have content** — chapters must have drafts (`chapter.md`) or model data (`chapter.json`)

**Online vs Offline Mode**: Per `.framework/rules/command-boundary.md`, this command uses **online mode** by default — the agent executes agentically via the MCP client. Never route to Python directly in online mode.

## Chapter Scope Resolution

Determine which chapters to transform:

| Scope | Behavior |
|-------|----------|
| `<n>` | Transform single chapter `chapters/<n>/` |
| `all` | Transform all chapters in the pipeline |
| `continue` | Transform only chapters where `state: "needs_calibration"` or no `akshar_target` set |

## Transformation Process

For each chapter in scope, the agent processes every segment's writer-stage text:

### Step 1 — Read Current Line Content

- Read `chapters/<n>/segments/<segment>/writer/chapter.md` (or `chapter.md` if no segments)
- For poetry: every chapter has exactly one segment (`segments/1/`)

### Step 2 — Split Into Lines

- Poetry lines are typically separated by blank lines or specific line breaks
- If no explicit line breaks, use the style's line-breaking rule (pijush style for poetry)

### Step 3 — Calibrate Each Line to Target Akshar Count

For each line, the agent:

1. Calls `word.akshar-count` through the MCP endpoint:
   ```python
   import sys
   sys.path.insert(0, "tools")
   from mcphttpclient import call_tool, extract_text

   result = call_tool("word.akshar-count", {"word": "<bengali-line-text>"})
   current_count = int(extract_text(result))
   ```

2. If `current_count == target_akshars`: line is calibrated, record as `calibrated`

3. If `current_count < target_akshars`: add Bengali consonants to reach target
   - Use known akshar words: "হো" (1 akshar), "ক" (1 akshar), "খ" (1 akshar), etc.
   - Strategy: append consonant-only words until target is reached
   - Example: target 15, current 10 → append "হো ক কृष्ण শ্রী" (5 akshars) → total 15

4. If `current_count > target_akshars`: remove words/constituents until target is reached
   - Priority: remove least essential modifiers first
   - If cannot exactly reduce, record as `underflow` and note the discrepancy

### Step 4 — Write Calibrated Line

- Write the calibrated line back to `chapters/<n>/segments/<segment>/writer/chapter.md`
- Archive prior version to `chapters/<n>/history/` with timestamp
- Record `akshar_calibration` record in chapter model with:
  - `target_akshars`: the target count
  - `actual_akshars`: the calibrated count (should match target)
  - `calibration_method`: "mcp_tool" or "manual_adjustment"
  - `status`: "calibrated" or "adjusted"

## Report Generation

After processing all chapters, the agent reports:

```
Transform Summary:
- Book: <bookname>
- Form: poetry
- Target akshars: <target>
- Chapters processed: <count>
- Chapters calibrated: <count>
- Chapters with discrepancies: <count>
- Chapters needing manual review: <count>

Per-Chapter Details:
Chapter 1:
  - Lines: <total>
  - Calibrated: <count>
  - Underflow: <count>
  - Overflow: <count>
  - Status: <calibrated/partial/needs_review>

Chapter 2:
  ...

Next Steps (per .framework/rules/next-steps.md):
- If all chapters calibrated: Run /book <bookname> write all|continue to write chapters with calibrated lines
- If some chapters need review: Run /book <bookname> review all to audit quality, then write
- If target needs adjustment: Adjust book.json akshar_target field, then re-run transform
- If MCP tool errors: Check MCP client connection, re-run transform after resolving
- General: Run /book <bookname> eval all to check pipeline completeness before write/publish
```

## Error Handling

| Error Condition | Response |
|-----------------|----------|
| Pipeline doesn't exist | Stop: "Use `scaffold` first to create pipeline" |
| Book form is not poetry | Stop: "Book form must be poetry, got: <form>" |
| Line agent doesn't exist | Stop: "Create `.framework/agents/line/agent.md` first" |
| Chapter has no draft content | Stop: "Chapter <n> has no draft; write or enrich first" |
| MCP tool fails | Stop: "word.akshar-count tool error: <error>" |
| Cannot exactly match target | Record as `underflow`/`overflow`, report discrepancy, continue with manual review |
| Language is not Bengali | Stop: "Book language must be Bengali/bng for akshar calibration" |

## Integration with Pipeline

The transform workflow integrates with the pipeline as follows:

1. **Run before `write`** — ensure all lines are calibrated to fixed length before writing chapters
2. **Run before `publish`** — calibrated lines are a prerequisite for promotion to published output
3. **Run after `enrich`** — enrich chapter models first, then calibrate line lengths
4. **Output stays in pipeline** — calibrated drafts stay in `workspaces/pipeline/<bookname>/chapters/` until `write` promotes them

## Next Steps (mandatory, per framework)

After every transform command completes, report next steps following `.framework/rules/next-steps.md`:

- If all chapters calibrated: `Run /book <bookname> write all|continue to write chapters with calibrated lines`
- If some chapters need review: `Run /book <bookname> review all to audit quality, then write`
- If target needs adjustment: `Adjust book.json akshar_target field, then re-run transform`
- If MCP tool errors: `Check MCP client connection, re-run transform after resolving`
- General: `Run /book <bookname> eval all to check pipeline completeness before write/publish`

## Example Usages

### Example 1: Transform all chapters to 15 akshars (default)
```bash
/book mypoetry transform all
```
This calibrates all chapters in `workspaces/pipeline/mypoetry/` to 15 akshars per line using the `word.akshar-count` MCP tool.

### Example 2: Transform single chapter to 21 akshars
```bash
/book mypoetry transform 1 21
```
This calibrates chapter 1 to exactly 21 akshars per line.

### Example 3: Transform with continue scope
```bash
/book mypoetry transform continue
```
This transforms only chapters that haven't been calibrated yet (state: "needs_calibration").

### Example 4: Online mode via agent
The agent routes through `.framework/agents/line/agent.md`, which calls `word.akshar-count` through the MCP endpoint configured in `tools/mcphttpclient.py` for each line calibration.

---

## Sonnet Mode — Bengali Sonnet Calibration

### What Is a Bengali Sonnet

A Bengali sonnet (বাংলা সনেট) differs from its English counterpart in its fundamental
meter unit. English sonnets count **syllables** (iambic pentameter, 10 per line).
Bengali sonnets count **akshars** — consonant letters. Because Bengali consonant
clusters (যুক্তব্যঞ্জন) cannot be counted visually, every akshar count **must** be
obtained via the `word.akshar-count` MCP tool. Native computation is forbidden.

| Property | English Sonnet | Bengali Sonnet |
|---|---|---|
| Meter unit | Syllable | Akshar (consonant) |
| Line length | 10 syllables | **14 akshars** |
| Internal break | None enforced | **8 + 6 caesura** |
| Total lines | 14 | **14** |
| Count tool | Rule-based | `word.akshar-count` via the MCP endpoint |

### Command

```
/book <bookname> transform <chapter>|all|continue sonnet
```

The `sonnet` keyword activates sonnet mode. When present:

- Target akshars is **fixed at 14** — the `<target_akshar>` argument is ignored.
- Total output lines is **fixed at 14** — the poem is trimmed or extended to
  exactly 14 lines before calibration begins.
- Each calibrated line is split **8 + 6** at the caesura.
- The volta (thematic turn) is noted at line 9.

### Prerequisites (in addition to standard transform prerequisites)

- Book form must be `poetry`.
- `tools/sonnet_utils.py` must be present alongside `tools/mcphttpclient.py`.
- The MCP endpoint must be reachable. Its address is `BASE_URL` in
  `tools/mcphttpclient.py`; no stdio server registration is required.

### Sonnet Transformation Process

#### Step 0 — Normalise Line Count to 14

Before any akshar calibration, enforce exactly **14 non-empty lines**:

| Source line count | Action |
|---|---|
| More than 14 | Keep lines 1–8 and the last 6 (preserves the volta at 9 and the closing couplet) |
| Fewer than 14 | Append thematically consistent continuation lines until count = 14; mark each appended line `generated` in the model |
| Exactly 14 | Proceed |

#### Step 1 — Calibrate Each Line to 14 Akshars

For each of the 14 lines, route through the `line` agent which calls
`word.akshar-count` via `tools/sonnet_utils.py`:

```python
from sonnet_utils import akshar_count, calibrate_line

count = akshar_count(line)          # MCP call — never native
status, detail = calibrate_line(line)   # "calibrated" | "underflow" | "overflow"
```

- **`calibrated`** (`count == 14`): no change needed, record status.
- **`underflow`** (`count < 14`): expand — add semantically compatible Bengali words
  or matras until `akshar_count(line) == 14`. Prefer appending to the end; if
  meaning would be distorted, insert before the last word.
- **`overflow`** (`count > 14`): reduce — remove least-essential modifiers (adverbs
  first, then adjectives, then compound verb particles). Retry until count = 14.
  If exact reduction is impossible, record `adjusted` and log the discrepancy.

Iterate the expand/reduce loop until `akshar_count(line) == 14` or the agent
exhausts 5 rewrite attempts, at which point it records `needs_manual_review`.

#### Step 2 — Split Each Line at the Caesura (8 + 6)

After a line reaches 14 akshars, split it using `find_caesura`:

```python
from sonnet_utils import format_caesura, CAESURA_MARK

formatted_line = format_caesura(line)
# example: "আমার সোনার বাংলা আমি | তোমায় ভালোবাসি চির"
```

`find_caesura` scans word-by-word, calling `word.akshar-count` per word, until
the accumulated count reaches 8 — that boundary is the caesura. The remaining
words form the 6-akshar second half.

The caesura mark (`" | "`) is kept in the draft for editorial review and stripped
before final `publish` output unless the book config sets `keep_caesura_mark: true`.

#### Step 3 — Mark the Volta

Line 9 is the **volta** (বিপর্যয়) — the thematic turn. After calibration, the
agent annotates the chapter model:

```json
{
  "volta_line": 9,
  "volta_note": "thematic shift begins at line 9"
}
```

The volta is noted, not enforced — the agent does not rewrite line 9 to force a
theme change. That is the poet's responsibility.

#### Step 4 — Write the Sonnet Draft

Write all 14 formatted lines back to:

```
chapters/<n>/segments/1/writer/chapter.md
```

Archive the prior version:

```
chapters/<n>/history/<timestamp>_pre_sonnet.md
```

Record in the chapter model:

```json
{
  "akshar_target": 14,
  "caesura": "8+6",
  "sonnet_mode": true,
  "volta_line": 9,
  "calibration_method": "mcp_tool",
  "lines_generated": 0,
  "lines_adjusted": 0,
  "lines_needs_review": []
}
```

### Sonnet Report Format

After processing, the agent produces:

```
Sonnet Transform Summary:
- Book      : <bookname>
- Chapter   : <n>
- Mode      : sonnet (14 lines × 14 akshars, 8+6 caesura)
- Lines in  : <original line count>
- Lines out : 14

Per-Line Results:
  1.  [calibrated]  আমার সোনার বাংলা আমি | তোমায় ভালোবাসি চির    (14 akshars: 8+6)
  2.  [calibrated]  ...
  ...
  9.  [volta ↻]     ...
  ...
  14. [calibrated]  ...

Status:
  Calibrated     : <count>/14
  Adjusted       : <count>/14
  Needs review   : <line numbers>

Next Steps:
  - If all calibrated: /book <bookname> write <chapter> to promote the sonnet draft
  - If needs review  : Edit flagged lines manually, then re-run transform <chapter> sonnet
  - To publish       : /book <bookname> publish after write completes
```

### Error Conditions (Sonnet Mode)

| Condition | Response |
|---|---|
| MCP endpoint not reachable | Stop: "MCP endpoint unavailable — confirm Book.Backend is running and `BASE_URL` in tools/mcphttpclient.py is correct" |
| `word.akshar-count` returns non-integer | Stop: "MCP tool returned unexpected value: <raw>" |
| Line cannot reach 14 after 5 attempts | Record `needs_manual_review`, continue with remaining lines |
| Source has 0 non-empty lines | Stop: "Chapter has no content; write or enrich first" |
| Book form is not poetry | Stop: "Sonnet mode requires form: poetry" |
| `sonnet_utils.py` missing | Stop: "tools/sonnet_utils.py not found; ensure it is present alongside mcphttpclient.py" |

### Integration Notes

- Sonnet mode is a **specialisation** of the standard transform workflow. All
  standard prerequisites (pipeline exists, form is poetry, line agent present) still apply.
- Sonnet output stays in `workspaces/pipeline/` until `write` promotes it.
- Sonnet mode does **not** alter `filters/filters.json` or the filter chain.
- The caesura mark is display-only; filters and the publish agent strip it unless
  `keep_caesura_mark: true` is set in `book.json`.

### Example

```bash
# Transform chapter 1 into a 14-line Bengali sonnet (14 akshars × 8+6 caesura)
/book mypoetry transform 1 sonnet

# Transform all chapters into sonnets
/book mypoetry transform all sonnet

# Transform only uncalibrated chapters
/book mypoetry transform continue sonnet
```
