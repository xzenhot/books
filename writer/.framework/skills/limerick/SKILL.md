---
name: limerick
description: Fixed-form Bengali limerick (লিমেরিক) — five lines, AABBA rhyme scheme, longer opening/closing lines and shorter middle lines, humorous or satirical with a punchline in line 5. Akshar count and rhyme verified via the MCP endpoint. Alias: "limeric".
---

# Limerick Skill (লিমেরিক)

Use this skill to compose a **Bengali limerick** — a five-line humorous or
satirical poem with an **AABBA** rhyme scheme: two long lines, two short lines,
and a closing long line that delivers the punchline.

## Fundamental Paradigm

> **The agent composes. MCP measures. The agent adjusts.**

MCP (`word.akshar-count`, `word.rhyme-test`) is a ruler — it measures and
verifies, never writes. The agent authors every line as witty Bengali verse, then
uses MCP to check each line's akshar count and rhyme and adjusts until it fits.
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
| Akshars: L1, L2, L5 | **9** (long lines) |
| Akshars: L3, L4 | **6** (short lines) |
| Tone | Humorous, satirical, or playful; a punchline or twist in L5 |

## Language Rule — Bengali Only

- Read, compose, and write in Bengali. The finished poem is Bengali script.
- Never use English rhyme intuition or romanization.
- Every akshar count must come from `word.akshar-count`.
- Every rhyme relation must be verified with `word.rhyme-test`.
- If an MCP result contains non-Bengali or romanized words, discard it.

## MCP Protocol

All MCP traffic uses `tools/mcpbangla/kamolika.py` (HTTP client for the Book.Backend
endpoint, `BASE_URL`). Call tools with `call_tool(name, arguments)` and read
results with `extract_text(result)`. Do not launch a stdio server and do not open a
stdio session.

| Tool | Use |
|---|---|
| `word.akshar-count` | Measure akshar count of any word, phrase, or full line |
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

Lines 1, 2, and 5 are long (9 akshars); lines 3 and 4 are short (6 akshars).
This long–long–short–short–long shape approximates the anapestic gallop of the
English limerick while keeping the akshar as the Bengali meter unit.

## Composition Workflow

### Phase 0 — Read and Understand the Source

1. Read the chapter's content: `chapters/<n>/chapter.md` first, falling back to
   `chapters/<n>/segments/1/writer/chapter.md` when the root draft is empty.
2. Read `book.json` for the chapter `chapter_summary` and the book
   `book_summary`, `gist`, and `era`.
3. Identify the single humorous or satirical angle the poem will land.

### Phase 1 — Build the Rhyme Bank

Compose the A-family anchor and B-family anchor end words, then fetch 2–3
verified candidates per family via `word.rhyming-words*` and confirm each with
`word.rhyme-test`. Record the bank:

```text
A: <word>(<akshar>) <word>(<akshar>) ...
B: <word>(<akshar>) <word>(<akshar>) ...
```

### Phase 2 — Compose the Five Lines

Write lines 1 and 2 (long, A-rhyme), lines 3 and 4 (short, B-rhyme), and line 5
(long, A-rhyme, punchline). Calibrate every line to its akshar target via
`word.akshar-count`, adjusting with `word.previous` / `word.next` /
`word.next-context` while preserving the joke.

### Phase 3 — Verify

Confirm all five end words satisfy AABBA via `word.rhyme-test`, and that every
line hits its akshar target via `word.akshar-count`.

### Phase 4 — Write and Record

Write the finished limerick to `chapters/<n>/chapter.md`, archive the prior draft
to `chapters/<n>/history/`, and record in `chapter.json`:

```json
{
  "form_skill": "limerick",
  "rhyme_scheme": "AABBA",
  "akshar_target": {"long": 9, "short": 6},
  "calibration_method": "agent_composed_mcp_verified"
}
```

## Constraints

- Never use MCP to generate or complete a line; MCP measures and verifies only.
- Never compute akshar counts natively.
- Never alter a line's joke or meaning to hit an akshar or rhyme target.
- The A and B rhyme families must be distinct.
- Work only inside `workspaces/pipeline/<bookname>/`.
- Valid only for books with `form: poetry`.

## Audit Tooling

`tools/mcpbangla/verse.py` audits this form mechanically — use it instead of
re-deriving checks inline:

```bash
python tools/mcpbangla/verse.py audit <file> --form limerick
```

It measures every line via MCP and fails the run on any contract violation.

## Report Format

```
Limerick Report
Book    : <bookname>
Chapter : <n>
Mode    : limerick (5 lines, AABBA, 9/9/6/6/9 akshars)

Lines:
  1. [9ak ✓] <line>  [A]
  2. [9ak ✓] <line>  [A]
  3. [6ak ✓] <line>  [B]
  4. [6ak ✓] <line>  [B]
  5. [9ak ✓] <line>  [A]

Summary:
  Rhyme    : AABBA verified
  Calibrated: 5/5

Next steps:
  /book <bookname> write <n>      # promote to chapter output
```
