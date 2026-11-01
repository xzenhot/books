---
name: limerick
description: Fixed-form Bengali limerick (লিমেরিক) — five lines, AABBA rhyme scheme, longer opening/closing lines and shorter middle lines, humorous or satirical with a punchline in line 5. The long/short syllable pattern is chosen at random from a menu of valid schemes; rhyme verified via the MCP endpoint. Alias: "limeric".
---

# Limerick Skill (লিমেরিক)

## Audit Metadata

This skill writes only chapter content and its history/version snapshots, all
inside the exempt `chapters/**` tree, so it stamps no audit fields. If it ever
writes a non-chapter `.md`/`.json`, stamp it as the invoking agent per
`.framework/rules/audit-metadata.md`.

Use this skill to compose a **Bengali limerick** — a five-line humorous or
satirical poem with an **AABBA** rhyme scheme: two long lines, two short lines,
and a closing long line that delivers the punchline.

## Fundamental Paradigm

> **The agent composes. MCP measures. The agent adjusts.**

MCP (`word.syllable-count`, `word.rhyme-test`) is a ruler — it measures and
verifies, never writes. The agent authors every line as witty Bengali verse, then
uses MCP to check each line's syllable count and rhyme and adjusts until it fits.
Bengali consonant clusters (যুক্তব্যঞ্জন) make visual counting unreliable; trust
MCP, never the eye.

## Invocation

```text
/book <bookname> limerick <chapter> [replace]
```

This skill is never executed directly by a workflow. It is reached through the
**write agent** (`.framework/agents/write/agent.md`), which resolves the form and
routes the poetry request to this skill. `limerick` (alias `limeric`) selects the
fixed limerick form.

## Form Contract

| Property | Value |
|---|---|
| Total lines | **5** |
| Rhyme scheme | **AABBA** (L1–L2 rhyme A, L3–L4 rhyme B, L5 rhymes A) |
| Long/short pattern | **One scheme, chosen at random** from the menu below — not a single fixed count |
| Ruler | `word.syllable-count` per word, summed (never akshar) |
| Tone | Humorous, satirical, or playful; a punchline or twist in L5 |

### The meter — a pattern is picked, not prescribed

The Bengali limerick is measured in **syllables**, not akshar, but there is **no
single syllable scheme**. The poet selects **one** pattern from the menu below and
then holds it consistently: all three long lines land together, both short lines
land together, each within **±10 %** of the chosen long/short values.

| Pattern | Long lines (L1/L2/L5) | Short lines (L3/L4) | Provenance |
|---|---|---|---|
| **compact** | 14 | 7 | a tight, punchy gallop |
| **canonical** | 16 | 8 | the default corpus shape (example 1) |
| **extended** | 22 | 12 | the stretched register (example 2) |
| **long-line** | 20 | 10 | a mid-extended, declamatory shape |

Pick one at random per composition; never mix two patterns in one poem. The choice
is recorded in `chapter.json` as `syllable_pattern` so the audit can derive and
check it.

Measured from the corpus with MCP:

| Example line | Syllables |
|---|---|
| `কন্‌কনে শীত তাই চাই তার দস্তানা` (L1) | 16 |
| `বাজার ঘুরিয়ে দেখে, জিনিসটা সস্তা না` (L2) | 15 |
| `কম দামে কিনে মোজা` (L3) | 8 |
| `বাড়ি ফিরে গেল সোজা` (L4) | 8 |
| `কিছুতে ঢোকে না হাতে, তাই শেষে পস্তানা` (L5) | 16 |
| `ক্ষান্তবুড়ির দিদিশাশুড়ির পাঁচ বোন থাকে কাল্‌নায়` (L1) | 22 |
| `কোনো দোষ পাছে ধরে নিন্দুকে` (L3) | 12 |

Sum the per-word counts from `word.syllable-count` — never apply it to a whole
phrase, which over-counts across conjunct boundaries. A line inside its pattern's
band is final; never rewrite it to hit the exact number.

## Language Rule — Bengali Only

- Read, compose, and write in Bengali. The finished poem is Bengali script.
- Never use English rhyme intuition or romanization.
- Every syllable count must come from `word.syllable-count` (per word, summed).
- Every rhyme relation must be verified with `word.rhyme-test`.
- If an MCP result contains non-Bengali or romanized words, discard it.

## MCP Protocol

All MCP traffic uses `tools/mcpbangla/kamolika.py` (HTTP client for the Book.Backend
endpoint, `BASE_URL`). Call tools with `call_tool(name, arguments)` and read
results with `extract_text(result)`. Do not launch a stdio server and do not open a
stdio session.

| Tool | Use |
|---|---|
| `word.syllable-count` | Measure syllable count of a word; sum per word for a line (the limerick ruler) |
| `word.rhyme-test` | Confirm a rhyme relation (required for every A and B pair) |
| `word.rhyming-words` / `-context` / `-accuracy` | Fetch rhyme candidates for the A and B families |
| `word.previous` / `word.next` / `word.next-context` | Extend or replace a word forward/backward |

## Structure

### Rhyme Families (AABBA)

Two rhyme families govern the poem:

- **A family** — end words of lines 1, 2, and 5.
- **B family** — end words of lines 3 and 4.

The A and B families must be distinct; a word may not belong to both. The
punchline (line 5) ends on an A-rhyme word that lands the twist.

### Lengths

Lines 1, 2, and 5 are **long**; lines 3 and 4 are **short**. The actual long/short
counts come from **one randomly chosen pattern** (compact 14/7, canonical 16/8,
extended 22/12, long-line 20/10) and are held consistent across the poem, each
within **±10 %** (`.framework/rules/meter-tolerance.md`). The long/short contrast
and the anapestic long–long–short–short–long shape are what matter — not a single
fixed number.

## Composition Workflow

### Phase 0 — Read and Understand the Source

1. Read the chapter's content: `chapters/<n>/chapter.md` first, falling back to
   `chapters/<n>/segments/1/writer/chapter.md` when the root draft is empty.
2. Read `book.json` for the chapter `chapter_summary` and the book
   `book_summary`, `gist`, and `era`.
3. Identify the single humorous or satirical angle the poem will land.
4. **Pick the syllable pattern at random** from the menu — compact 14/7, canonical
   16/8, extended 22/12, or long-line 20/10. Record it; you will hold it for the
   whole poem.

### Phase 1 — Build the Rhyme Bank

Compose the A-family anchor and B-family anchor end words, then fetch 2–3
verified candidates per family via `word.rhyming-words*` and confirm each with
`word.rhyme-test`. Record the bank:

```text
A: <word>(<syllables>) <word>(<syllables>) ...
B: <word>(<syllables>) <word>(<syllables>) ...
```

### Phase 2 — Compose the Five Lines

Write lines 1 and 2 (long, A-rhyme), lines 3 and 4 (short, B-rhyme), and line 5
(long, A-rhyme, punchline). Hold the chosen pattern: all three long lines sit
together and both short lines sit together, each within **±10 %** of the chosen
long/short values. Calibrate via `word.syllable-count` (summed per word),
adjusting with `word.previous` / `word.next` / `word.next-context` only when a
line breaks the chosen long/short consistency while preserving the joke. An
in-consistency line is final.

### Phase 3 — Verify

Confirm all five end words satisfy AABBA via `word.rhyme-test`, and that the poem
is **internally consistent** — all long lines within ±10 % of each other, all
short lines within ±10 % of each other — via `word.syllable-count`.

### Phase 4 — Write and Record

Write the finished limerick to `chapters/<n>/chapter.md`, archive the prior draft
to `chapters/<n>/history/`, and record in `chapter.json`:

```json
{
  "form_skill": "limerick",
  "rhyme_scheme": "AABBA",
  "syllable_pattern": "canonical",
  "syllable_target": {"long": 16, "short": 8},
  "calibration_method": "agent_composed_mcp_verified"
}
```

## Constraints

- Never use MCP to generate or complete a line; MCP measures and verifies only.
- Never compute syllable counts natively.
- Never alter a line's joke or meaning to hit a syllable or rhyme target.
- **Pick one syllable pattern at random** (compact 14/7, canonical 16/8, extended
  22/12, long-line 20/10) and hold it; never mix patterns in one poem.
- Long lines must sit within ±10 % of one another, and short lines within ±10 % of
  one another; a consistent line is never rewritten to hit the exact number.
- The A and B rhyme families must be distinct.
- Work only inside `workspaces/pipeline/<bookname>/`.
- Valid only for books with `form: poetry`.

## Audit Tooling

`tools/mcpbangla/verse.py` audits this form mechanically — use it instead of
re-deriving checks inline:

```bash
python tools/mcpbangla/verse.py audit <file> --form limerick
```

It derives the poem's chosen long/short pattern from the lines themselves (modal
counts) and fails the run on any consistency or contract violation. Pass
`--maxlen`/`--shortlen` to pin a specific pattern instead.

## Report Format

```
Limerick Report
Book    : <bookname>
Chapter : <n>
Mode    : limerick (5 lines, AABBA, pattern <compact|canonical|extended|long-line>)

Lines:
  1. [16syl ✓] <line>  [A]
  2. [16syl ✓] <line>  [A]
  3. [8syl ✓]  <line>  [B]
  4. [8syl ✓]  <line>  [B]
  5. [16syl ✓] <line>  [A]

Summary:
  Pattern    : <name> (long <n> / short <n>)
  Rhyme      : AABBA verified
  Consistent : 5/5 (longs ±10%, shorts ±10%)

Next steps:
  /book <bookname> write <n>      # promote to chapter output
```
Example: 

1)
কন্‌কনে শীত তাই চাই তার দস্তানা;
বাজার ঘুরিয়ে দেখে, জিনিসটা সস্তা না।
কম দামে কিনে মোজা 
বাড়ি ফিরে গেল সোজা—
কিছুতে ঢোকে না হাতে, তাই শেষে পস্তানা।

2)
ক্ষান্তবুড়ির দিদিশাশুড়ির পাঁচ বোন থাকে কাল্‌নায়,
শাড়িগুলো তারা উনুনে বিছায়, হাঁড়িগুলো রাখে আল্‌নায়।
কোনো দোষ পাছে ধরে নিন্দুকে
নিজে থাকে তারা লোহাসিন্দুকে,
টাকাকড়িগুলো হাওয়া খাবে ব'লে রেখে দেয় খোলা জাল্‌নায় ।

