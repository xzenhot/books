#!/usr/bin/env python3
"""
_sonnet_measure.py — Per-line akshar measurement helper for Bengali sonnet calibration.

ROLE IN THE WORKFLOW
--------------------
This script is the agent's ruler, not its writer. The agent (LLM) composes
each sonnet line independently as meaningful Bengali poetry. This script then
measures each line via the kobi MCP server's word.akshar-count tool and reports
the delta from the 14-akshar target so the agent can make targeted word-level
edits in the next iteration.

PARADIGM: Agent composes → MCP verifies → Agent adjusts → MCP verifies → repeat
Never the other way around.

USAGE
-----
1. Agent writes candidate lines into the LINES list below.
2. Run:  python _sonnet_measure.py
3. Read the output: each line shows [count] ✓ or (+n)/(-n).
4. Agent edits only the failing lines, reruns, iterates until all show ✓.

After all 14 lines show ✓, run _sonnet_write.py to split at the caesura and
write the final sonnet to chapter.md and the segment writer folder.

WORD-LEVEL PROBE MODE
---------------------
Add individual words to the PROBE list to understand why a line is over/under.
The script prints each word's akshar count, which tells the agent which exact
word to add, remove, or swap.

    python _sonnet_measure.py --probe

PARAMETERS
----------
TARGET       : 14 (fixed for Bengali sonnet)
VOLTA_LINE   : 9  (thematic turn, annotated in report, not enforced)
"""

import sys
import os
import argparse

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from mcpclient import McpClient, default_server_path

TARGET = 14
VOLTA_LINE = 9

# ---------------------------------------------------------------------------
# EDIT THIS LIST — agent-composed candidate lines, one per sonnet position
# ---------------------------------------------------------------------------
# fresco / chapter 6 — "Abstract, Minimal"
# Theme: blank wall after erasing a great design, one trembling line,
#        charcoal on dry lime, plaster dust taste, the question of a small flaw.
LINES = [
    "বিবর্ণ দেয়ালে শূন্যতায় হাত কাঁপে",        # 1  blank wall, void, trembling hand
    "নকশা মুছে হাত কাঁপে একা রেখায়",            # 2  design erased, hand trembles alone
    "একটি রেখাই চাই স্মৃতির বিরুদ্ধে",            # 3  ✓ one line against memory
    "তুলির শীতল রোধ চুনের ঘর্ষণ",               # 4  cold brush, lime friction
    "কাঠকয়লার শব্দ চাপা দীর্ঘশ্বাস",              # 5  charcoal sound like sigh
    "জিওপ্লাস্টার ধুলো মুখে ধাতব স্বাদ",          # 6  plaster dust metallic taste in mouth
    "একটি নিখুঁত রেখা শূন্যতার সংজ্ঞা",           # 7  one perfect line defines void
    "অতীত হিমায়িত স্থির রেখার থামে",             # 8  past frozen, stilled by the line
    "হাতের কম্পনে একটি বাড়তি দাগ",                # 9  hand tremor — one extra mark [volta]
    "ত্রুটিই মহৎ সৃষ্টির পতন ডাকে",               # 10 this flaw calls down great creation
    "রেখা পাথরের মতো চূড়ান্ত সিদ্ধান্ত",          # 11 line like stone — final decision
    "নির্লিপ্ততা কি ক্ষয় নাকি গোপন প্রেম",        # 12 ✓ detachment — decay or secret love
    "শূন্যতাই রাজকীয় ছায়ায় উত্তর",               # 13 void answers in royal shadow
    "নিরাকারতার গভীরে শুধু স্থিরতা",              # 14 in formlessness — only stillness
]

# ---------------------------------------------------------------------------
# PROBE LIST — individual words to measure when diagnosing a line
# ---------------------------------------------------------------------------
PROBE = [
    "হাতের", "কম্পনে", "কম্পন", "একটি", "ভুল", "দাগ",
    "সহসা", "কাঁপায়", "অকারণ", "হঠাৎ",
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


def measure_words(client, line):
    total = akshar(client, line)
    breakdown = [(w, akshar(client, w)) for w in line.split() if w.strip()]
    return total, breakdown


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
            flag = " ✓"
        else:
            all_ok = False
            needs_work.append(i)
            flag = f" ({delta:+d})"
        volta = "  [volta ↻]" if i == VOLTA_LINE else ""
        print(f"  {i:2d}.{volta} [{count:2d}]{flag}  {line}")

    print()
    if all_ok:
        print("Result  : 14/14 ✓  — ready for _sonnet_write.py")
    else:
        print(f"Result  : {14 - len(needs_work)}/14 calibrated")
        print(f"Fix     : lines {needs_work}")
        print()
        print("Adjustment guide (agent edits, not MCP):")
        print("  Overflow  (+n) : remove n akshar-worth of modifiers")
        print("                   priority: adverbs → adjective compounds")
        print("                             → postpositional particles")
        print("  Underflow (-n) : add n akshar-worth of semantically fitting words")
        print("                   priority: append to end → insert before verb")
        print("  Use --probe to see word-level breakdown of a specific line.")
    print()
    print("Next step: edit LINES above, rerun, repeat until 14/14 ✓")
    print("           then run: python _sonnet_write.py --book fresco --chapter 6")


def run_probe(client):
    if not PROBE:
        print("PROBE list is empty. Add words to the PROBE list in this script.")
        return
    print("Word-level akshar probe:")
    print("-" * 40)
    for w in PROBE:
        count = akshar(client, w)
        print(f"  [{count:2d}ak]  {w}")
    print()
    print("Word breakdown of each LINES entry:")
    print("-" * 40)
    for i, line in enumerate(LINES, 1):
        total, breakdown = measure_words(client, line)
        delta = total - TARGET
        flag = "✓" if delta == 0 else f"{delta:+d}"
        print(f"  {i:2d}. [{total:2d}ak {flag}]  " +
              "  ".join(f"{w}({c})" for w, c in breakdown))


def main():
    parser = argparse.ArgumentParser(
        description="Measure akshar counts of agent-composed Bengali sonnet lines.")
    parser.add_argument("--probe", action="store_true",
                        help="Print word-level breakdown for each line")
    args = parser.parse_args()

    client = McpClient(default_server_path())
    try:
        client.connect()
        client.initialize()
        if args.probe:
            run_probe(client)
        else:
            run_measure(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
