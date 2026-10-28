---
name: sonnet
description: Fixed-form Bengali sonnet — 14 lines of exactly 14 akshars each, split 8+6 at the caesura, volta at line 9, optional verified rhyme. Routes through the line agent (calibration) and rhyme agent (composition). MCP measures; the agent composes.
---

# Sonnet Skill (বাংলা সনেট)

Use this skill to compose or calibrate a **Bengali sonnet**: exactly **14 lines**,
each **14 akshars** (অক্ষর), split **8 + 6** at the caesura, with a **volta** at
line 9 and an optional verified rhyme scheme.

## Fundamental Paradigm

> **The agent composes. MCP measures. The agent adjusts.**

MCP (`word.akshar-count`) is a ruler — it measures, never writes. Every line is
authored by the agent as meaningful Bengali poetry drawn from the source chapter's
themes, imagery, and tonal register. The agent then uses MCP to check whether each
line hits exactly 14 akshars and makes targeted word-level edits until it does.
MCP is never asked to generate, suggest, or complete a line.

Bengali consonant clusters (যুক্তব্যঞ্জন) make visual akshar counting unreliable;
a word such as `বেঁধেছে` looks like 4–5 letters but the MCP counts it as 3 akshars.
The agent must trust the MCP count, never its own visual estimate.

## Invocation

```text
/book <bookname> line <chapter> sonnet [replace]        # calibration path (line agent)
/book <bookname> rhyme <chapter> sonnet [<scheme>] [replace]  # composition path (rhyme agent)
```

This skill is never executed directly by a workflow. It is reached through the
**line agent** (`.framework/agents/line/agent.md`) for calibration and the
**rhyme agent** (`.framework/agents/rhyme/agent.md`) for composition.

## Form Contract

| Property | Value |
|---|---|
| Total lines | **14** |
| Akshars per line | **14** (consonant count, measured by MCP) |
| Caesura | **8 + 6**, ending on a natural word boundary |
| Volta | Line **9** (thematic turn — noted, not enforced) |
| Octave | Lines 1–8 |
| Sestet | Lines 9–14 |
| Rhyme | Optional; when enabled, verified via `word.rhyme-test` |

## Language Rule — Bengali Only

- Read, compose, and write in Bengali. The finished poem is Bengali script.
- Never use English rhyme intuition, romanization, or transliteration.
- Every akshar count must come from `word.akshar-count`; visual counting is invalid.
- If an MCP result contains non-Bengali or romanized words, discard it.

## MCP Protocol

All MCP traffic uses `tools/mcpbangla/kamolika.py` (HTTP client for the Book.Backend
endpoint, `BASE_URL`). Call tools with `call_tool(name, arguments)` and read
results with `extract_text(result)`. Do not launch a stdio server and do not open a
stdio session.

| Tool | Use |
|---|---|
| `word.akshar-count` | Measure akshar count of any word, phrase, or full line (the only ruler) |
| `word.rhyme-test` | Confirm whether two end words rhyme (positive result required) |
| `word.rhyming-words` / `-context` / `-accuracy` | Fetch rhyme candidates for a family |
| `word.previous` / `word.next` / `word.next-context` | Extend or replace a word forward/backward |
| `poem.sonnet` / `poem.next-sonnet-line` | Draft seeds only — must pass every gate before use |

## Structure

### Volta

Line 9 is the **volta** (বিপর্যয়) — the thematic turn. The agent marks it
`[volta ↻]` in reports and writes `"volta_line": 9` in the chapter model. The
volta is noted, not forced: the agent does not rewrite line 9 to force a theme
change. That is the poet's responsibility.

### Caesura (8 + 6)

Each 14-akshar line splits into two half-lines at a natural word boundary. The
rhyme agent uses the strict `8 + 6` split. The line agent, in its calibration
pass, scans word-by-word via `word.akshar-count` for the best valid boundary,
preferring `4+4|3+3`, `4+4|2+4`, and `4+4|4+2`, and falls back to the word
boundary nearest the midpoint when no preferred pattern fits.

## Composition Workflow

### Phase 0 — Read and Understand the Source

1. Read the chapter's content: `chapters/<n>/chapter.md` first, falling back to
   `chapters/<n>/segments/1/writer/chapter.md` when the root draft is empty.
2. Read `book.json` for the chapter `chapter_summary` and the book
   `book_summary`, `gist`, and `era`.
3. Extract the **thematic core** — images, emotions, objects, verbs, and the
   chapter's argument — and write it down before composing a single line.

### Phase 1 — Compose 14 Seed Lines

Write one seed line per sonnet position as meaningful Bengali poetry. Length does
not matter yet; calibration happens next.

- **Lines 1–8 (Octave)**: establish the central tension from the source.
- **Line 9 (Volta)**: shift perspective, mood, or subject.
- **Lines 10–14 (Sestet)**: resolve, question, or deepen the tension.

### Phase 2 — Calibrate to 14 Akshars (line agent)

For each line, generate meaning-preserving variants (delete / insert / replace
via `word.next`, `word.previous`, `word.next-context`), test each with
`word.akshar-count`, and select the first candidate that reaches exactly 14
akshars on a valid caesura boundary. Iterate up to 3 rounds per line; on
exhaustion record `needs_manual_review` and continue.

### Phase 3 — Compose the Rhyme Bank (rhyme agent, when rhyme is enabled)

Resolve the scheme (`ABAB` default; also `ACBD`, `ABCDEFFEDCBA`), build a rhyme
bank per family via `word.rhyming-words*`, and confirm every end word with
`word.rhyme-test` before it enters a line.

### Phase 4 — Write and Record

Write the finished 14 lines to `chapters/<n>/chapter.md` (clean, no caesura
marks) and `chapters/<n>/segments/1/writer/chapter.md` (with ` | ` caesura
marks), archive the prior draft to `chapters/<n>/history/`, and record in
`chapter.json`:

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

## Constraints

- Never use MCP to generate or complete a line; MCP measures only.
- Never compute akshar counts natively.
- Never alter a line's central meaning to hit an akshar target.
- Never write to `chapter.md` without archiving the prior version to `history/`.
- Work only inside `workspaces/pipeline/<bookname>/`.
- Valid only for books with `form: poetry`.

## Report Format

```
Sonnet Report
Book    : <bookname>
Chapter : <n>
Mode    : sonnet (14 lines × 14 akshars, 8+6 caesura)

Per-line: [14ak ✓] <line>   (line 9 marked [volta ↻])

Summary:
  Calibrated   : 14/14
  Needs review : none

Next steps:
  /book <bookname> write <n>      # promote to chapter output
  /book <bookname> publish         # after write completes
```
