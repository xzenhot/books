#!/usr/bin/env python3
"""
_sonnet_write.py — Caesura split and file writer for Bengali sonnet calibration.

ROLE IN THE WORKFLOW
--------------------
Run this script ONLY after _sonnet_measure.py reports 14/14 ✓.
It performs three jobs:

  1. Verifies all 14 lines are still exactly 14 akshars (safety re-check).
  2. Splits each line at the 8-akshar caesura boundary word-by-word via MCP.
  3. Writes the finished sonnet to the pipeline files.

PARADIGM: Agent composes → MCP verifies (_sonnet_measure.py) → Agent adjusts
          → 14/14 ✓ → MCP splits caesura → this script writes files.

The caesura split is also MCP-driven: we call word.akshar-count per word,
accumulate until we reach exactly 8, and split there. This is necessary because
Bengali consonant clusters (যুক্তব্যঞ্জন) make visual counting unreliable.

CAESURA RULES
-------------
A 14-akshar line may be split at any of the following valid first-half sizes.
The split is always on a natural word boundary. All combinations sum to 14.

  Preferred (highly recommended):
    4+4 | 3+3   perfectly balanced
    4+4 | 2+4   excellent flowing rhythm
    4+4 | 4+2   strong start, crisp ending

  Also valid:
    3+5 | 2+4
    5+3 | 3+3
    5+3 | 4+2
    2+6 | 3+3
    6+2 | 4+2
    3+5 | 1+5
    5+3 | 5+1
    2+6 | 4+2
    6+2 | 2+4

The split_caesura() function scans word boundaries and picks the valid
combination whose first-half size falls nearest to a natural break point,
preferring the combinations in the order listed above.

OUTPUT FILES
------------
  chapters/<n>/chapter.md                        ← clean lines, no caesura marks
  chapters/<n>/segments/1/writer/chapter.md      ← lines with " | " caesura marks
  chapters/<n>/chapter.json                      ← sonnet metadata added
  chapters/<n>/history/<timestamp>_pre_sonnet.md ← archived original

USAGE
-----
  python _sonnet_write.py --book fresco --chapter 5
  python _sonnet_write.py --book fresco --chapter 5 --dry-run   # no files written
"""

import sys
import os
import json
import argparse
from datetime import datetime

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(TOOLS_DIR)

if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from mcpclient import McpClient, default_server_path

TARGET = 14
VOLTA_LINE = 9

# ---------------------------------------------------------------------------
# Valid caesura patterns for a 14-akshar Bengali sonnet line.
# Each entry is (first_half, second_half). All sum to 14.
# Ordered by preference — the split finder tries them in this order.
# ---------------------------------------------------------------------------
CAESURA_PATTERNS = [
    # Preferred
    (4, 4, 3, 3),   # 4+4 | 3+3  perfectly balanced
    (4, 4, 2, 4),   # 4+4 | 2+4  excellent flowing rhythm
    (4, 4, 4, 2),   # 4+4 | 4+2  strong start, crisp ending
    # Also valid
    (3, 5, 2, 4),
    (5, 3, 3, 3),
    (5, 3, 4, 2),
    (2, 6, 3, 3),
    (6, 2, 4, 2),
    (3, 5, 1, 5),
    (5, 3, 5, 1),
    (2, 6, 4, 2),
    (6, 2, 2, 4),
]

# Derived: set of valid first-half akshar totals (first two values of each tuple)
VALID_FIRST_HALVES = sorted({a + b for a, b, _, _ in CAESURA_PATTERNS})
# = [5, 6, 7, 8, 9, 11] after dedup — but we evaluate by word-boundary proximity

# ---------------------------------------------------------------------------
# LINES — paste the final 14/14 ✓ lines from _sonnet_measure.py here
# ---------------------------------------------------------------------------
# fresco / chapter 6 — "Abstract, Minimal"
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
# MCP helpers
# ---------------------------------------------------------------------------

def text_of(result):
    if isinstance(result, dict):
        for item in result.get("content", []):
            if isinstance(item, dict) and item.get("type") == "text":
                return item["text"].strip()
    return str(result).strip()


def akshar(client, text):
    r = client.call_tool("word.akshar-count", {"word": text.strip()})
    return int(text_of(r))


def split_caesura(client, line):
    """
    Split a 14-akshar line at the best natural word boundary using valid
    caesura patterns.

    Algorithm:
    1. Measure each word's akshar count via MCP.
    2. Build a list of all word-boundary positions with their accumulated
       akshar count (possible split points).
    3. For each valid caesura pattern (in preference order), check whether
       the required first-half total (a+b) falls on a word boundary.
    4. Return the first pattern that matches a word boundary exactly.
    5. If no pattern matches exactly, fall back to the closest valid
       first-half total that has a word boundary.

    Returns (first_half: str, second_half: str, first_count: int, second_count: int,
             pattern_label: str).
    """
    words = line.strip().split()
    # Build cumulative akshar counts at each word boundary
    cumulative = []
    acc = 0
    for w in words:
        wc = akshar(client, w)
        acc += wc
        cumulative.append((acc, w))

    # cumulative[i] = (total akshars after words[0..i], words[i])
    boundary_totals = [c for c, _ in cumulative]  # list of ints

    # Try each pattern in preference order
    for a, b, c, d in CAESURA_PATTERNS:
        first_total = a + b
        second_total = c + d
        if first_total + second_total != TARGET:
            continue
        if first_total in boundary_totals:
            # Found a clean word-boundary split
            split_idx = boundary_totals.index(first_total)
            first_words = [w for _, w in cumulative[:split_idx + 1]]
            second_words = [w for _, w in cumulative[split_idx + 1:]]
            f_text = " ".join(first_words)
            s_text = " ".join(second_words)
            f_count = akshar(client, f_text) if f_text else 0
            s_count = akshar(client, s_text) if s_text else 0
            pattern_label = f"{a}+{b}|{c}+{d}"
            return f_text, s_text, f_count, s_count, pattern_label

    # Fallback: split at the word boundary closest to TARGET//2 = 7
    target_first = TARGET // 2
    best_idx = min(range(len(boundary_totals)),
                   key=lambda i: abs(boundary_totals[i] - target_first))
    first_words = [w for _, w in cumulative[:best_idx + 1]]
    second_words = [w for _, w in cumulative[best_idx + 1:]]
    f_text = " ".join(first_words)
    s_text = " ".join(second_words)
    f_count = akshar(client, f_text) if f_text else 0
    s_count = akshar(client, s_text) if s_text else 0
    return f_text, s_text, f_count, s_count, f"{f_count}+{s_count}(fallback)"

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_paths(book, chapter):
    base = os.path.join(WORKSPACE_ROOT, "workspaces", "pipeline", book,
                        "chapters", str(chapter))
    return {
        "chapter_md":  os.path.join(base, "chapter.md"),
        "chapter_json": os.path.join(base, "chapter.json"),
        "history_dir":  os.path.join(base, "history"),
        "writer_dir":   os.path.join(base, "segments", "1", "writer"),
        "writer_md":    os.path.join(base, "segments", "1", "writer", "chapter.md"),
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(book, chapter, dry_run=False):
    paths = resolve_paths(book, chapter)
    client = McpClient(default_server_path())

    try:
        client.connect()
        client.initialize()

        print("=" * 65)
        print(f"SONNET WRITE — {book} / chapter {chapter}")
        print("=" * 65)
        print(f"Target  : {TARGET} lines × {TARGET} akshars (valid caesura patterns: 4+4|3+3, 4+4|2+4, ...)")
        print()

        # --- Safety re-verify all 14 lines ---
        print("Step 1 — Safety verification (14 akshars per line):")
        print("-" * 65)
        all_ok = True
        counts = []
        for i, line in enumerate(LINES, 1):
            count = akshar(client, line)
            counts.append(count)
            flag = "✓" if count == TARGET else f"FAIL ({count-TARGET:+d})"
            if count != TARGET:
                all_ok = False
            volta = "  [volta ↻]" if i == VOLTA_LINE else ""
            print(f"  {i:2d}.{volta} [{count:2d}] {flag}  {line}")

        if not all_ok:
            print()
            print("ERROR: Not all lines are 14 akshars.")
            print("Fix failing lines in _sonnet_measure.py first, then rerun.")
            return

        print()
        print("All 14 lines verified ✓")

        # --- Caesura split ---
        print()
        print("Step 2 — Caesura split (best valid pattern via MCP):")
        print("-" * 65)
        formatted = []
        for i, line in enumerate(LINES, 1):
            f, s, fc, sc, pattern = split_caesura(client, line)
            full = f"{f} | {s}" if s else f
            volta = "  ← volta" if i == VOLTA_LINE else ""
            print(f"  {i:2d}.  {full}{volta}")
            print(f"       [{fc}+{sc}={fc+sc}ak  pattern:{pattern}]")
            formatted.append(full)

        # --- Report ---
        print()
        print("=" * 65)
        print("SONNET")
        print("=" * 65)
        for i, f in enumerate(formatted, 1):
            vm = "  ← volta" if i == VOLTA_LINE else ""
            print(f"  {i:2d}.  {f}{vm}")

        if dry_run:
            print()
            print("(dry-run — no files written)")
            return

        # --- Write files ---
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Archive original chapter.md
        os.makedirs(paths["history_dir"], exist_ok=True)
        if os.path.exists(paths["chapter_md"]):
            with open(paths["chapter_md"], encoding="utf-8") as f:
                original = f.read()
            archive = os.path.join(paths["history_dir"],
                                   f"{ts}_pre_sonnet.md")
            with open(archive, "w", encoding="utf-8") as f:
                f.write(original)
            print(f"\nArchived  → {os.path.relpath(archive, WORKSPACE_ROOT)}")

        # Write clean lines (no caesura marks) to chapter.md
        clean = "\n".join(LINES) + "\n"
        with open(paths["chapter_md"], "w", encoding="utf-8") as f:
            f.write(clean)
        print(f"Written   → {os.path.relpath(paths['chapter_md'], WORKSPACE_ROOT)}")

        # Write caesura-marked lines to segment writer folder
        os.makedirs(paths["writer_dir"], exist_ok=True)
        caesura_text = "\n".join(formatted) + "\n"
        with open(paths["writer_md"], "w", encoding="utf-8") as f:
            f.write(caesura_text)
        print(f"Written   → {os.path.relpath(paths['writer_md'], WORKSPACE_ROOT)}")

        # Update chapter.json
        model = {}
        if os.path.exists(paths["chapter_json"]):
            with open(paths["chapter_json"], encoding="utf-8") as f:
                try:
                    model = json.load(f)
                except json.JSONDecodeError:
                    model = {}
        model.update({
            "akshar_target": TARGET,
            "caesura": "multi-pattern (4+4|3+3 preferred)",
            "sonnet_mode": True,
            "volta_line": VOLTA_LINE,
            "calibration_method": "agent_composed_mcp_verified",
            "lines_calibrated": len(LINES),
            "lines_needs_review": [],
            "sonnet_calibrated_at": ts,
        })
        with open(paths["chapter_json"], "w", encoding="utf-8") as f:
            json.dump(model, f, ensure_ascii=False, indent=2)
        print(f"Updated   → {os.path.relpath(paths['chapter_json'], WORKSPACE_ROOT)}")

        print()
        print("Done.")
        print()
        print("Next steps:")
        print(f"  /book {book} write {chapter}    ← promote sonnet to chapter output")
        print(f"  /book {book} eval all           ← check pipeline completeness")

    finally:
        client.close()

def build_line(previous):
    return previous

def main():
    parser = argparse.ArgumentParser(
        description="Caesura-split and write a verified Bengali sonnet to pipeline files.")
    parser.add_argument("--book", default="fresco",
                        help="Book name (default: fresco)")
    parser.add_argument("--chapter", default="5",
                        help="Chapter number (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print result but do not write any files")
    args = parser.parse_args()
    run(book=args.book, chapter=args.chapter, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
