# Meter Tolerance

Every metre-based form — `poyar`, `sonnet`, `haiku`, `limerick`, `srijato`,
`lyrics` — allows **±10 % drift** on its line target. A target is the centre of an
accepted band, not an exact quota.

| Target | Accepted band | Tolerance |
|---|---|---|
| 16 | **14 – 18** | ±2 |
| 14 | **12 – 16** | ±2 |
| 9 | 8 – 10 | ±1 |
| 8 | 7 – 9 | ±1 |
| 7 | 6 – 8 | ±1 |
| 6 | 5 – 7 | ±1 |
| 5 | 4 – 6 | ±1 |

Rule: `tolerance = ceil(target * 0.10)`, with a minimum of **1**.

Meter-unit per form: **akshar** for `poyar` (14), `sonnet` (14), and `haiku`
(5-7-5); **syllable** for `limerick`, `srijato`, and `lyrics`.

### Limerick — a pattern, not a fixed scheme

The limerick has **no single syllable scheme**. The poet picks one pattern at
random and holds it consistently:

| Pattern | Long (L1/L2/L5) | Short (L3/L4) |
|---|---|---|
| compact | 14 | 7 |
| canonical | 16 | 8 |
| long-line | 20 | 10 |
| extended | 22 | 12 |

Each long line sits within **±10 %** of the chosen long value, each short line
within **±10 %** of the chosen short value. `verse.py audit --form limerick`
derives the poem's pattern from its modal line counts and enforces that internal
consistency; `--maxlen`/`--shortlen` pin a specific pattern.

## What the band does and does not relax

- **Relaxed:** the line count. A line anywhere inside the band **passes**; it is
  never rewritten merely to hit the exact number, and a line outside the band is
  rewritten.
- **Not relaxed:** the form's structure. Poyar and sonnet keep the caesura at
  akshar **8**, haiku keeps three lines and its 5-7-5 shape, limerick keeps AABBA
  and its long/short line split, poyar keeps strong L1~L2 rhyme with distinct ends
  and no cross-couplet rhyme.
- **Not relaxed:** the ruler. Akshar (`word.akshar-count`) for akshar metre,
  syllable (`word.syllable-count`, summed per word) for syllable metre.

## Reporting

- The **exact target** is still the preferred line and is reported first.
- Report `exact` and `within band` counts separately, so drift stays visible
  instead of hiding inside a pass.
- `tools/mcpbangla/verse.py audit` applies this band by default; pass
  `--akshar-tolerance N` to tighten or widen it for a single run.

## Write → review → repair loop

Python **never writes verse**. It measures and reports; the composing agent (LLM)
authors and repairs.

```text
1. write  — the agent authors the lines and appends them to the chapter draft
2. review — python tools/mcpbangla/verse.py review <file> --form <form>
3. repair — the agent reads the per-line/per-word report and rewrites only
            the lines and couplets it flags
4. repeat until the review prints === PASS ===
```

`review` is read-only and emits, per line: total akshar, delta vs target, band
verdict, and the exact word-by-word cumulative breakdown; plus, per couplet, the
rhyme test, strength, and both rhyme units. Use `--json` for machine-readable
output.

**Exit criteria** (all must hold) before a chapter is recorded as written:

1. every line is inside its form's band;
2. every required rhyme is `word.rhyme-test >= 1` **and** STRONG;
3. no redif (identical end words), no reused rhyme pair;
4. `review` prints `=== PASS ===` and `audit` prints `=== PASS ===`.
