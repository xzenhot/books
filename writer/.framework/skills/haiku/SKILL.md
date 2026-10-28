---
name: haiku
description: Fixed-form Bengali haiku (হাইকু) — three lines of 5-7-5 akshars, a season word (kigo) and a pause (kireji), capturing a single moment of perception in nature. No rhyme. Akshar count measured via the MCP endpoint. Reached through the write agent's poetry route.
---

# Haiku Skill (হাইকু)

## Audit Metadata

This skill writes only chapter content and its history/version snapshots, all
inside the exempt `chapters/**` tree, so it stamps no audit fields. If it ever
writes a non-chapter `.md`/`.json`, stamp it as the invoking agent per
`.framework/rules/audit-metadata.md`.

Use this skill to compose a **Bengali haiku** — a three-line poem of **5-7-5
akshars** that captures a single, fleeting moment of perception in nature,
anchored by a **season word** (ঋতুশব্দ) and marked by a **pause** (kireji).

## Fundamental Paradigm

> **The agent composes. MCP measures. The agent adjusts.**

MCP (`word.akshar-count`) is a ruler — it measures, never writes. The agent
authors the haiku's three lines as precise, image-led Bengali, then uses MCP to
confirm the 5-7-5 akshar count and adjusts word choice until it fits. MCP is
never asked to generate or complete a line. Bengali consonant clusters
(যুক্তব্যঞ্জন) make visual counting unreliable; trust MCP, never the eye.

## Invocation

```text
/book <bookname> haiku <chapter> [replace]
```

This skill is never executed directly by a workflow. It is reached through the
**write agent** (`.framework/agents/write/agent.md`), which resolves the form and
routes the poetry request to this skill. `haiku` selects the fixed haiku form.

## Form Contract

| Property | Value |
|---|---|
| Total lines | **3** |
| Akshar pattern | **5 – 7 – 5** |
| Rhyme | **None** |
| Season word (kigo) | One word/phrase naming the season, present in the poem |
| Pause (kireji) | A break or juxtaposition, typically at the end of L1 or L2 |
| Subject | A concrete moment of perception — nature, weather, light, sound |

## Language Rule — Bengali Only

- Read, compose, and write in Bengali. The finished poem is Bengali script.
- Never use English syllable intuition or romanization.
- Every akshar count must come from `word.akshar-count` (the 5-7-5 ruler).
- If an MCP result contains non-Bengali or romanized words, discard it.

## MCP Protocol

All MCP traffic uses `tools/mcpbangla/kamolika.py` (HTTP client for the Book.Backend
endpoint, `BASE_URL`). Call tools with `call_tool(name, arguments)` and read
results with `extract_text(result)`. Do not launch a stdio server and do not open a
stdio session.

| Tool | Use |
|---|---|
| `word.akshar-count` | Measure akshar count of any word, phrase, or full line (the only ruler) |
| `word.syllable-count` | Optional secondary measure; akshar count is the 5-7-5 ruler |
| `word.previous` / `word.next` / `word.next-context` | Extend or replace a word forward/backward |

## Structure

### The 5-7-5 Akshar Pattern

Three lines, exactly 5, 7, and 5 akshars respectively. The pattern is measured
with `word.akshar-count`, never by eye. The middle line (7 akshars) usually
carries the widest image; the shorter outer lines frame it.

### The Season Word (kigo / ঋতুশব্দ)

One word or short phrase in the poem names the season or its concrete sign —
e.g. বর্ষা (monsoon rain), শীতের কুয়াশা (winter fog), বসন্তের ফুল (spring
blossom), শরতের শিউলি (autumn shiuli). The season word anchors the moment in
time without explanation.

### The Pause (kireji)

A break or juxtaposition separates two images, most often at the end of line 1
or line 2. It lets the poem turn from one concrete thing to another rather than
explaining. The pause is structural, not necessarily a written punctuation mark.

## Composition Workflow

### Phase 0 — Read and Understand the Source

1. Read the chapter's content: `chapters/<n>/chapter.md` first, falling back to
   `chapters/<n>/segments/1/writer/chapter.md` when the root draft is empty.
2. Read `book.json` for the chapter `chapter_summary` and the book
   `book_summary`, `gist`, and `era`.
3. Extract the single concrete image and its season before writing a line.

### Phase 1 — Compose the Three Lines

Write three short lines that pair two concrete images across the kireji pause,
each line meaning-first. Do not aim for 5-7-5 yet.

### Phase 2 — Calibrate to 5-7-5

Measure each line with `word.akshar-count` and adjust with
`word.previous` / `word.next` / `word.next-context` until the counts read 5, 7,
and 5. Preserve the image and the season word throughout.

### Phase 3 — Write and Record

Write the finished haiku to `chapters/<n>/chapter.md`, archive the prior draft to
`chapters/<n>/history/`, and record in `chapter.json`:

```json
{
  "form_skill": "haiku",
  "akshar_pattern": "5-7-5",
  "season_word": "<kigo>",
  "calibration_method": "agent_composed_mcp_verified"
}
```

## Constraints

- Never use MCP to generate or complete a line; MCP measures only.
- Never compute akshar counts natively.
- Never alter the image or drop the season word to hit the 5-7-5 target.
- No rhyme — the haiku is image and rhythm only.
- Work only inside `workspaces/pipeline/<bookname>/`.
- Valid only for books with `form: poetry`.

## Audit Tooling

`tools/mcpbangla/verse.py` audits this form mechanically — use it instead of
re-deriving checks inline:

```bash
python tools/mcpbangla/verse.py audit <file> --form haiku
```

It measures every line via MCP and fails the run on any contract violation.

## Report Format

```
Haiku Report
Book    : <bookname>
Chapter : <n>
Mode    : haiku (5-7-5 akshars)

Lines:
  1. [5ak ✓]  <line>
  2. [7ak ✓]  <line>
  3. [5ak ✓]  <line>

Season word : <kigo>

Summary:
  Calibrated : 3/3

Next steps:
  /book <bookname> write <n>      # promote to chapter output
```
