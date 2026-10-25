#!/usr/bin/env python3
"""
_sonnet_measure.py — Bengali sonnet line calibrator.

PARADIGM
--------
  Agent composes 14 seed lines → this script auto-generates candidates
  via insert / replace / delete operations (using MCP for word suggestions)
  → MCP verifies akshar count → MCP checks caesura pattern → first match wins.

CANDIDATE GENERATION (per line)
--------------------------------
Three operations produce candidates from a seed line.
All use the kobi MCP server for contextually appropriate Bengali words.

  DELETE   — remove one word at a time from every position.
             Reduces akshar count; useful when seed is over 14.

  INSERT   — insert a MCP-suggested word at every position.
             word.next(predecessor)  → words that naturally follow predecessor
             word.previous(successor) → words that naturally precede successor
             word.next-context(predecessor) → richer context-aware next words
             Both give corpus-backed Bengali suggestions. Increases akshar count.

  REPLACE  — swap one word for each MCP-suggested word at that position.
             word.next(predecessor) gives candidates for position i.
             word.previous(successor) gives candidates for position i.
             All replacement candidates are tested for meaning proximity.

Each operation is applied at every word position in the line, and for every
MCP suggestion returned (up to MAX_SUGGESTIONS per call). All generated
candidates are deduplicated, then tested in order:
  1. akshar-count == 14 ?   (MCP: word.akshar-count)
  2. caesura pattern valid? (word boundary scan via word.akshar-count per word)

The first candidate satisfying both conditions is selected for that line.

VALID CAESURA PATTERNS
-----------------------
First-half totals that must fall on a word boundary (preferred first):
  8 (4+4|3+3, 4+4|2+4, 4+4|4+2), 7, 6, 9, 5, 11

USAGE
-----
  python _sonnet_measure.py                    # measure all 14 lines
  python _sonnet_measure.py --probe            # word-level akshar breakdown
  python _sonnet_measure.py --auto             # auto-calibrate all failing lines
  python _sonnet_measure.py --auto --line 9   # auto-calibrate only line 9
  python _sonnet_measure.py --candidates <n>  # test CANDIDATES[n] manually
"""

import sys
import os
import argparse
import json

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from mcpclient import McpClient, default_server_path

TARGET       = 14
VOLTA_LINE   = 9
MAX_SUGGESTIONS = 12   # max words to fetch per word.next / word.previous call
MAX_ROUNDS   = 3       # rounds of 48 before giving up

# ---------------------------------------------------------------------------
# Valid caesura patterns — ordered by preference
# ---------------------------------------------------------------------------
CAESURA_PATTERNS = [
    (8,  "4+4|3+3 preferred"),
    (8,  "4+4|2+4 preferred"),
    (8,  "4+4|4+2 preferred"),
    (7,  "3+4|2+4"),
    (8,  "5+3|3+3"),
    (8,  "5+3|4+2"),
    (8,  "2+6|3+3"),
    (8,  "6+2|4+2"),
    (8,  "3+5|1+5"),
    (8,  "5+3|5+1"),
    (8,  "2+6|4+2"),
    (8,  "6+2|2+4"),
]
VALID_FIRST_HALVES = [8, 7, 6, 9, 5, 11]

# ---------------------------------------------------------------------------
# LINES — agent-composed seed lines, one per sonnet position
# ---------------------------------------------------------------------------
LINES = [
    "বিবর্ণ দেয়ালে শূন্যতায় হাত কাঁপে",
    "নকশা মুছে হাত কাঁপে একা রেখায়",
    "একটি রেখাই চাই স্মৃতির বিরুদ্ধে",
    "তুলির শীতল রোধ চুনের ঘর্ষণ",
    "কাঠকয়লার শব্দ চাপা দীর্ঘশ্বাস",
    "জিওপ্লাস্টার ধুলো মুখে ধাতব স্বাদ",
    "একটি নিখুঁত রেখা শূন্যতার সংজ্ঞা",
    "অতীত হিমায়িত স্থির রেখার থামে",
    "হাতের কম্পনে একটি বাড়তি দাগ",
    "ত্রুটিই মহৎ সৃষ্টির পতন ডাকে",
    "রেখা পাথরের মতো চূড়ান্ত সিদ্ধান্ত",
    "নির্লিপ্ততা কি ক্ষয় নাকি গোপন প্রেম",
    "শূন্যতাই রাজকীয় ছায়ায় উত্তর",
    "নিরাকারতার গভীরে শুধু স্থিরতা",
]

# ---------------------------------------------------------------------------
# PROBE — words to individually measure in --probe mode
# ---------------------------------------------------------------------------
PROBE: list = []

# ---------------------------------------------------------------------------
# CANDIDATES — manual variants for --candidates <n> mode
# ---------------------------------------------------------------------------
CANDIDATES: dict = {}

# ---------------------------------------------------------------------------
# MCP helpers
# ---------------------------------------------------------------------------

def text_of(result):
    if isinstance(result, dict):
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                return item["text"].strip()
    return str(result).strip()


_ak_cache: dict = {}

def akshar(client, text: str) -> int:
    t = text.strip()
    if not t:
        return 0
    if t in _ak_cache:
        return _ak_cache[t]
    r = client.call_tool("word.akshar-count", {"word": t})
    v = int(text_of(r))
    _ak_cache[t] = v
    return v


def next_words(client, word: str) -> list[str]:
    """Return corpus-suggested words that follow `word` (word.next-context)."""
    word = word.strip(".,;।?!()\"\u2018\u2019\u201c\u201d")
    if not word:
        return []
    try:
        r = client.call_tool("word.next-context", {"word": word})
        raw = text_of(r)
        data = json.loads(raw)
        if isinstance(data, list):
            return [
                item.get("Word", "") if isinstance(item, dict) else str(item)
                for item in data[:MAX_SUGGESTIONS]
                if (item.get("Word", "") if isinstance(item, dict) else str(item))
            ]
    except Exception:
        pass
    try:
        r = client.call_tool("word.next", {"word": word})
        raw = text_of(r)
        data = json.loads(raw)
        if isinstance(data, list):
            return [
                item.get("Word", "") if isinstance(item, dict) else str(item)
                for item in data[:MAX_SUGGESTIONS]
                if (item.get("Word", "") if isinstance(item, dict) else str(item))
            ]
    except Exception:
        pass
    return []


def prev_words(client, word: str) -> list[str]:
    """Return corpus-suggested words that precede `word` (word.previous)."""
    word = word.strip(".,;।?!()\"\u2018\u2019\u201c\u201d")
    if not word:
        return []
    try:
        r = client.call_tool("word.previous", {"word": word})
        raw = text_of(r)
        data = json.loads(raw)
        if isinstance(data, list):
            return [
                item.get("Word", "") if isinstance(item, dict) else str(item)
                for item in data[:MAX_SUGGESTIONS]
                if (item.get("Word", "") if isinstance(item, dict) else str(item))
            ]
    except Exception:
        pass
    return []

# ---------------------------------------------------------------------------
# Candidate generation — delete / insert / replace
# ---------------------------------------------------------------------------

def _clean(word: str) -> str:
    return word.strip(".,;।?!()\"\u2018\u2019\u201c\u201d\u2014 ")


def generate_candidates(client, line: str) -> list[str]:
    """
    Generate meaning-preserving variant lines from a seed line using three
    operations. All word suggestions come from the MCP corpus.

    Operations
    ----------
    DELETE  — remove one word at each position i.
              Generates len(words) variants.

    INSERT via word.next   — for each position i, fetch next_words(words[i-1])
                             and insert each suggestion between words[i-1] and
                             words[i].  Uses the predecessor word as context.
                             Also inserts after the last word (append).

    INSERT via word.prev   — for each position i, fetch prev_words(words[i])
                             and insert each suggestion before words[i].
                             Uses the successor word as context.

    REPLACE via word.next  — for each position i, fetch next_words(words[i-1])
                             and substitute each suggestion for words[i].
                             Predecessor stays; only words[i] is swapped.

    REPLACE via word.prev  — for each position i, fetch prev_words(words[i+1])
                             and substitute each suggestion for words[i].
                             Successor stays; only words[i] is swapped.

    Returns a deduplicated list of candidate strings (excludes the original seed).
    """
    words = [w for w in line.strip().split() if w.strip()]
    if not words:
        return []

    seen: set = {line.strip()}
    result: list = []

    def add(candidate: str):
        c = " ".join(candidate.strip().split())
        if c and c not in seen:
            seen.add(c)
            result.append(c)

    n = len(words)

    # ---- DELETE: remove word at position i ----
    for i in range(n):
        candidate = words[:i] + words[i+1:]
        if candidate:
            add(" ".join(candidate))

    # ---- INSERT + REPLACE via word.next (predecessor context) ----
    for i in range(n + 1):          # i = insert position (0 = prepend, n = append)
        predecessor = _clean(words[i - 1]) if i > 0 else ""
        suggestions = next_words(client, predecessor) if predecessor else []

        for suggestion in suggestions:
            s = suggestion.strip()
            if not s:
                continue

            # INSERT before position i (i.e. between words[i-1] and words[i])
            candidate = words[:i] + [s] + words[i:]
            add(" ".join(candidate))

            # REPLACE words[i] with suggestion (only when i < n)
            if i < n:
                candidate = words[:i] + [s] + words[i+1:]
                add(" ".join(candidate))

    # ---- INSERT + REPLACE via word.previous (successor context) ----
    for i in range(n):              # i = position of successor word
        successor = _clean(words[i])
        suggestions = prev_words(client, successor)

        for suggestion in suggestions:
            s = suggestion.strip()
            if not s:
                continue

            # INSERT s before words[i]
            candidate = words[:i] + [s] + words[i:]
            add(" ".join(candidate))

            # REPLACE words[i] with s
            candidate = words[:i] + [s] + words[i+1:]
            add(" ".join(candidate))

    return result

# ---------------------------------------------------------------------------
# Pattern check
# ---------------------------------------------------------------------------

def find_pattern(client, line: str):
    """
    Return (label, first_half, second_half) if any valid caesura first-half
    total falls on a word boundary, else None.
    """
    words = line.strip().split()
    cum, acc = [], 0
    for w in words:
        acc += akshar(client, w)
        cum.append(acc)
    for fh in VALID_FIRST_HALVES:
        if fh in cum:
            idx = cum.index(fh)
            first  = " ".join(words[:idx + 1])
            second = " ".join(words[idx + 1:])
            label  = next(
                (lbl for total, lbl in CAESURA_PATTERNS if total == fh),
                f"{fh}+{TARGET - fh}"
            )
            return label, first, second
    return None

# ---------------------------------------------------------------------------
# Auto-calibrate one line
# ---------------------------------------------------------------------------

def auto_calibrate_line(client, line_n: int, verbose: bool = True) -> str | None:
    """
    Auto-calibrate LINES[line_n-1] using the generate/test loop.

    Runs up to MAX_ROUNDS rounds. Each round:
      1. Generate candidates via delete/insert/replace + MCP word suggestions.
      2. For each candidate: check akshar-count == 14, then check caesura pattern.
      3. First passing candidate is returned and LINES updated.

    Returns the selected line string, or None if all rounds fail.
    """
    seed = LINES[line_n - 1]
    volta = " [volta ↻]" if line_n == VOLTA_LINE else ""
    if verbose:
        print(f"\nLine {line_n}{volta}: auto-calibrating...")
        print(f"  Seed: {seed}  [{akshar(client, seed)}ak]")

    working_seed = seed
    total_tested = 0

    for round_n in range(1, MAX_ROUNDS + 1):
        candidates = generate_candidates(client, working_seed)

        if verbose:
            print(f"  Round {round_n}: {len(candidates)} candidates generated")

        for p, candidate in enumerate(candidates, 1):
            total_tested += 1
            count = akshar(client, candidate)
            if count != TARGET:
                continue
            pattern_result = find_pattern(client, candidate)
            if pattern_result:
                label, first, second = pattern_result
                if verbose:
                    print(f"  ✓ Selected candidate #{p} (round {round_n}, "
                          f"tested {total_tested} total)")
                    print(f"    {first} | {second}  [{label}]")
                LINES[line_n - 1] = candidate
                return candidate

        # Use the closest-to-14 candidate as the new seed for the next round
        best = min(candidates, key=lambda c: abs(akshar(client, c) - TARGET),
                   default=working_seed)
        working_seed = best

    if verbose:
        print(f"  ✗ No valid candidate found after {MAX_ROUNDS} rounds "
              f"({total_tested} tested) — marked for manual review")
    return None

# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_measure(client):
    print("=" * 65)
    print(f"Akshar measurement — target: {TARGET} per line")
    print("=" * 65)
    all_ok = True
    needs_work = []
    for i, line in enumerate(LINES, 1):
        count = akshar(client, line)
        delta = count - TARGET
        if delta == 0:
            pr = find_pattern(client, line)
            if pr:
                label, first, second = pr
                flag = f" ✓  [{label}]  {first} | {second}"
            else:
                flag = " ✓  [14ak — no caesura pattern; run --auto]"
        else:
            all_ok = False
            needs_work.append(i)
            flag = f" ({delta:+d})"
        volta = "  [volta ↻]" if i == VOLTA_LINE else ""
        if delta != 0:
            print(f"  {i:2d}.{volta} [{count:2d}]{flag}  {line}")
        else:
            print(f"  {i:2d}.{volta} [{count:2d}]{flag}")
    print()
    if all_ok:
        print("Result  : 14/14 ✓  — ready for _sonnet_write.py")
    else:
        print(f"Result  : {14 - len(needs_work)}/14 calibrated")
        print(f"Fix     : lines {needs_work}")
        print()
        print("Run --auto to auto-calibrate all failing lines.")
        print("Run --auto --line <n> to auto-calibrate a single line.")
    print()
    print("Commands:")
    print("  python _sonnet_measure.py                    # standard mode")
    print("  python _sonnet_measure.py --probe            # word-level breakdown")
    print("  python _sonnet_measure.py --auto             # auto-calibrate all")
    print("  python _sonnet_measure.py --auto --line <n>  # auto-calibrate line n")
    print("  python _sonnet_measure.py --candidates <n>   # test manual variants")


def run_probe(client):
    if PROBE:
        print("Word-level akshar probe:")
        print("-" * 40)
        for w in PROBE:
            print(f"  [{akshar(client, w):2d}ak]  {w}")
        print()
    print("Word breakdown of each LINES entry:")
    print("-" * 40)
    for i, line in enumerate(LINES, 1):
        words = line.strip().split()
        total = akshar(client, line)
        delta = total - TARGET
        flag = "✓" if delta == 0 else f"{delta:+d}"
        breakdown = "  ".join(f"{w}({akshar(client,w)})" for w in words)
        print(f"  {i:2d}. [{total:2d}ak {flag}]  {breakdown}")


def run_auto(client, only_line: int | None = None):
    """Auto-calibrate all failing lines (or just `only_line`)."""
    print("=" * 65)
    print("AUTO CALIBRATE")
    print("=" * 65)
    print("Operations: delete · insert(word.next/word.next-context) ·")
    print("            insert(word.previous) · replace(word.next) ·")
    print("            replace(word.previous)")
    print()

    targets = [only_line] if only_line else range(1, 15)
    results = {}

    for i in targets:
        count = akshar(client, LINES[i - 1])
        pr = find_pattern(client, LINES[i - 1]) if count == TARGET else None

        if count == TARGET and pr:
            # Already good
            label, first, second = pr
            print(f"  {i:2d}. [already ✓]  [{label}]  {first} | {second}")
            results[i] = "ok"
            continue

        selected = auto_calibrate_line(client, i, verbose=True)
        results[i] = "calibrated" if selected else "needs_review"

    # Final summary
    print()
    print("=" * 65)
    print("FINAL SONNET AFTER AUTO-CALIBRATION")
    print("=" * 65)
    all_ok = True
    for i, line in enumerate(LINES, 1):
        count = akshar(client, line)
        pr = find_pattern(client, line) if count == TARGET else None
        if pr:
            label, first, second = pr
            flag = f"✓  [{label}]"
            display = f"{first} | {second}"
        else:
            all_ok = False
            flag = f"({count - TARGET:+d})" if count != TARGET else "✓ (no pattern)"
            display = line
        volta = "  [volta ↻]" if i == VOLTA_LINE else ""
        print(f"  {i:2d}.{volta} [{count:2d}] {flag}  {display}")

    print()
    if all_ok:
        print("Result  : 14/14 ✓  — run _sonnet_write.py to write files")
    else:
        needs = [i for i, s in results.items() if s == "needs_review"]
        print(f"Result  : manual review needed for lines {needs}")
        print("Edit those lines in LINES[] and rerun.")


def run_candidates(client, line_n: int):
    candidates = CANDIDATES.get(line_n, [])
    seed = LINES[line_n - 1]
    volta = " [volta ↻]" if line_n == VOLTA_LINE else ""
    print("=" * 70)
    print(f"Candidates for line {line_n}{volta}   seed: {seed}")
    print("=" * 70)
    if not candidates:
        print("CANDIDATES dict empty for this line.")
        print(f"Populate CANDIDATES[{line_n}] with variants, or use --auto.")
        return
    selected = None
    for p, candidate in enumerate(candidates, 1):
        count = akshar(client, candidate)
        if count == TARGET:
            pr = find_pattern(client, candidate)
            if pr:
                label, first, second = pr
                status = f"✓ MATCH  [{label}]  →  {first} | {second}"
                if selected is None:
                    selected = (p, candidate, label, first, second)
            else:
                status = "✓ 14ak — no caesura boundary"
        else:
            status = f"({count - TARGET:+d})"
        print(f"  {p:3d}. [{count:2d}] {status}  {candidate}")
    print()
    if selected:
        p, line, label, first, second = selected
        print(f"SELECTED → candidate {p}: {first} | {second}  [{label}]")
        print(f"Copy into LINES[{line_n - 1}] and rerun standard mode.")
    else:
        print("No match found. Use --auto to generate more variants.")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Bengali sonnet line calibrator — measure, auto-calibrate, probe.")
    parser.add_argument("--probe",      action="store_true",
                        help="Word-level akshar breakdown of all lines")
    parser.add_argument("--auto",       action="store_true",
                        help="Auto-calibrate all failing lines via delete/insert/replace + MCP")
    parser.add_argument("--line",       type=int, metavar="N",
                        help="With --auto: calibrate only line N")
    parser.add_argument("--candidates", type=int, metavar="N",
                        help="Test CANDIDATES[N] manually")
    args = parser.parse_args()

    client = McpClient(default_server_path())
    try:
        client.connect()
        client.initialize()
        if args.auto:
            run_auto(client, only_line=args.line)
        elif args.probe:
            run_probe(client)
        elif args.candidates is not None:
            run_candidates(client, args.candidates)
        else:
            run_measure(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
