#!/usr/bin/env python3
"""
verse.py — Bengali verse measurement and contract audit CLI.

Replaces the throwaway inline scripts used while composing poetry chapters. Every
measurement and rhyme decision goes through the Book.Backend MCP endpoint via
kamolika.py — nothing is computed natively.

Usage
-----
    # measure every line of a chapter (akshar + syllable)
    python tools/mcpbangla/verse.py measure workspaces/pipeline/durga/chapters/7/chapter.md

    # test a single rhyme pair
    python tools/mcpbangla/verse.py rhyme মাটি বৃষ্টি

    # list verified rhyme-class candidates for a word
    python tools/mcpbangla/verse.py family মাটি

    # audit a chapter against a form contract
    python tools/mcpbangla/verse.py audit workspaces/pipeline/durga/chapters/7/chapter.md --form poyar
    python tools/mcpbangla/verse.py audit <file> --form srijato --scheme ACBD

    # report-only review for the composing agent: per line, per word
    python tools/mcpbangla/verse.py review workspaces/pipeline/durga/chapters/7/chapter.md
    python tools/mcpbangla/verse.py review <file> --target 14 --json

Forms
-----
    poyar    two-line couplets, akshar meter (target 14 per line, band 12-16 by
             the 10% tolerance rule, measured as 8 + 6), L1~L2 strong rhyme
             (identical final rhyme unit), no cross-couplet rhyme.
    srijato  quatrains, syllable meter, scheme ACBD -> L1~L3 and L2~L4 per stanza.
    amitra   Bengali blank verse (অমিত্রাক্ষর ছন্দ): continuous enjambed lines,
             akshar meter (target 14, 8 + 6, band 12-16). Rhyme is optional and
             scheme-selected: `blank` (chhanda/meter only, no rhyme), `poyar`
             (L2~L1 strong rhyme per couplet), or `srijato` (L3~L1, L4~L2 per
             quatrain).

Every metre-based form allows +/-10% drift on its line target
(`.framework/rules/meter-tolerance.md`): a 14-akshar target accepts 12-16, and a
5-7-5 haiku accepts 4-6 / 6-8 / 4-6. Pass `--akshar-tolerance` /
`--syllable-tol` to override the band for a single run.

A "strong" rhyme means the two end words' final rhyme units are identical once
each consonant is folded to its varga row. `word.rhyme-test` alone is too loose:
it accepts `শব্দ/গন্ধ`, which poyar rejects.

Exit codes: 0 = pass, 1 = contract violation, 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import kamolika as mcp  # noqa: E402

# `word.rhyme-test` semantics: positive integer = rhymes (higher = stronger /
# more perfect), `0` = no corpus data / different class, `-1` = no rhyme.
def is_rhyme(r: str) -> bool:
    try:
        return int(r) >= 1
    except (TypeError, ValueError):
        return False

PUNCT = ",.;:!?।॥—–…\"'()[]"
RETRY_DELAY = 1.0  # seconds between MCP retries


def meter_tolerance(target: int, tolerance: int | None = None) -> int:
    """Allowed drift on a metre target: 10% of the target, never below 1.

    Every metre-based form accepts a band around its line target, so a 14-akshar
    line passes at 12-16. See `.framework/rules/meter-tolerance.md`.
    """
    if tolerance is not None and tolerance >= 0:
        return tolerance
    return max(1, math.ceil(target * 0.10))


# Bengali consonant classes (বর্গ). A consonant is folded to its class row so
# that class-mates which poets rhyme freely (ক/খ, ড/ঢ, ...) compare equal, while
# consonants from *different* rows never do. শ/ষ/স/হ share one row.
_VARGAS = ("কখগঘঙ", "চছজঝঞ", "টঠডঢণ", "তথদধন", "পফবভম", "শষসহ")
_VARGA = {ch: row[0] for row in _VARGAS for ch in row}
_VOWELS = set("ািীুূৃেৈোৌ")


# ---------------------------------------------------------------------------
# MCP primitives
# ---------------------------------------------------------------------------

_ready = False
_syllable_cache: dict[str, int] = {}


def _init() -> None:
    global _ready
    if not _ready:
        mcp.initialize()
        _ready = True


def call(name: str, args: dict) -> str:
    _init()
    return mcp.extract_text(mcp.call_tool(name, args)).strip()


def call_with_retry(name: str, args: dict, attempts: int = 3) -> str:
    """Call a tool, retrying transient backend failures (5xx / connection reset).

    The Book.Backend occasionally returns a 500 for a single word while serving the
    rest of a batch; without a retry a whole chapter audit would abort mid-run.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            return call(name, args)
        except Exception as exc:  # requests.HTTPError, ConnectionError, ...
            last = exc
            if i + 1 < attempts:
                time.sleep(RETRY_DELAY * (i + 1))
    raise RuntimeError(f"MCP tool {name!r} failed after {attempts} attempts: {last}")


def akshar(text: str) -> int:
    raw = call("word.akshar-count", {"word": text.strip()})
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"ackshar-count returned non-integer for {text!r}: {raw!r}")


def syllable(text: str) -> int:
    """Syllable count of a single word (MCP `word.syllable-count`)."""
    key = text.strip()
    if key in _syllable_cache:
        return _syllable_cache[key]
    raw = call_with_retry("word.syllable-count", {"word": key})
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"syllable-count returned non-integer for {text!r}: {raw!r}")
    _syllable_cache[key] = value
    return value


def syllable_line(line: str) -> int:
    """Syllable count of a whole line, measured word by word.

    `word.syllable-count` is only trustworthy on a single word: applied to a
    multi-word phrase it over-counts across certain conjunct boundaries (it
    reports 15 for a 14-syllable line). Summing the per-word counts, which always
    agrees with `word.syllable`, is the reliable line ruler.
    """
    words = [w.strip(PUNCT) for w in line.split() if w.strip(PUNCT)]
    return sum(syllable(w) for w in words)


def rhyme(a: str, b: str) -> str:
    """Return the raw rhyme-test value ('-1','0','1','2', ...)."""
    return call("word.rhyme-test", {"word": a, "withWord": b})


def rhymes(a: str, b: str) -> bool:
    return is_rhyme(rhyme(a, b))


def family(word: str, sizes=(2, 3, 4), limit: int = 12) -> list[str]:
    """Return verified same-class candidate words for `word`."""
    raw = call("word.rhyming-words", {"word": word, "sizes": list(sizes)})
    try:
        arr = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out: list[str] = []
    seen = {word}
    for item in arr:
        w = item.get("Word")
        if not w or w in seen:
            continue
        seen.add(w)
        if rhymes(word, w):
            out.append(w)
        if len(out) >= limit:
            break
    return out


def syllables_of(word: str) -> list[str]:
    """Return the syllable split of `word` (MCP `word.syllable`)."""
    raw = call("word.syllable", {"word": word})
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def rhyme_unit(word: str) -> str:
    """The sound that must match for a rhyme: the word's final syllable, with the
    consonant cluster folded into its varga row.

    A syllable with no vowel borrows the preceding syllable's vowel, so `শব্দ`
    resolves to the cluster `ব্দ` + `অ`-class vowel, not a bare consonant. Two
    words rhyme *strongly* only when these units are identical.
    """
    parts = syllables_of(word)
    if not parts:
        return ""
    last = parts[-1]
    if not (_VOWELS & set(last)) and len(parts) > 1:
        prev_vowels = [c for c in parts[-2] if c in _VOWELS]
        if prev_vowels:
            last = prev_vowels[-1] + last
    return "".join(_VARGA.get(c, c) for c in last)


def rhyme_strength(a: str, b: str) -> tuple[str, str, str]:
    """Classify a rhyme pair as STRONG or WEAK.

    `word.rhyme-test` answers "do these sit in one rhyme class?" — a loose,
    assonantal judgement that accepts pairs like `শব্দ/গন্ধ` (both end in
    `ন্দ`/`ব্দ` but on different vowels of a long cluster). Poyar needs the
    *coda* to match, so the final rhyme unit must be identical.
    """
    ua, ub = rhyme_unit(a), rhyme_unit(b)
    return ("STRONG" if ua and ua == ub else "WEAK"), ua, ub


def line_feet(line: str, target: int = 14) -> tuple[int, list[int]]:
    """Return the syllable total and the cumulative syllable boundaries of `line`.

    Boundaries are taken where a word ends, so they reveal whether the line can be
    read as an internal syllable measure (used by non-poyar forms).
    """
    words = [w.strip(PUNCT) for w in line.split() if w.strip(PUNCT)]
    boundaries: list[int] = []
    cumulative = 0
    for w in words:
        cumulative += syllable(w)
        boundaries.append(cumulative)
    return cumulative, boundaries


def akshar_feet(line: str, target: int = 14) -> tuple[int, list[int]]:
    """Return the akshar total and cumulative akshar boundaries of `line`.

    Poyar is an **akshar** form measured `8 + 6`, so the boundary that matters is
    the one at akshar 8 — where the word carrying the caesura ends.
    """
    words = [w.strip(PUNCT) for w in line.split() if w.strip(PUNCT)]
    boundaries: list[int] = []
    cumulative = 0
    for w in words:
        cumulative += akshar(w)
        boundaries.append(cumulative)
    return cumulative, boundaries


def word_report(line: str) -> list[dict]:
    """Per-word akshar breakdown of one line, with cumulative boundaries.

    This is the unit the reviewer hands to the composing agent: each word, its
    akshar count, and where the running total stands. No line is ever rewritten
    here — it is measured, described, and returned.
    """
    out: list[dict] = []
    cumulative = 0
    for raw in line.split():
        word = raw.strip(PUNCT)
        if not word:
            continue
        count = akshar(word)
        cumulative += count
        out.append({"word": word, "akshar": count, "cumulative": cumulative})
    return out


def caesura_split(words: list[dict], target_first: int = 8) -> dict:
    """Locate the word boundary nearest `target_first` akshars.

    Reports the split index and both half totals so the reviewer can say whether
    the line reads `8 + n` and how far the caesura is from the target foot.
    """
    boundaries = [w["cumulative"] for w in words]
    if not boundaries:
        return {"at": None, "first": 0, "second": 0, "exact": False, "delta": None}
    idx = min(range(len(boundaries)), key=lambda i: abs(boundaries[i] - target_first))
    first = boundaries[idx]
    second = boundaries[-1] - first
    return {
        "at": idx,
        "first": first,
        "second": second,
        "exact": first == target_first,
        "delta": first - target_first,
    }


# ---------------------------------------------------------------------------
# Line helpers
# ---------------------------------------------------------------------------

def read_lines(path: Path) -> list[str]:
    """Return non-empty content lines with trailing punctuation stripped."""
    raw = path.read_text(encoding="utf-8-sig").splitlines()
    lines = []
    for ln in raw:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):  # skip markdown headings
            continue
        lines.append(s.rstrip(PUNCT).strip())
    return lines


def end_word(line: str) -> str:
    stripped = line.strip().rstrip(PUNCT).strip()
    parts = stripped.split()
    return parts[-1].rstrip(PUNCT) if parts else ""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_measure(path: Path, show_syllable: bool) -> int:
    lines = read_lines(path)
    if not lines:
        print(f"no content lines in {path}", file=sys.stderr)
        return 2
    print(f"{'akshar':>7} {'syll':>5}  line")
    ak_total = 0
    for ln in lines:
        a = akshar(ln)
        ak_total += a
        if show_syllable:
            print(f"{a:>7} {syllable_line(ln):>5}  {ln}")
        else:
            print(f"{a:>7} {'-':>5}  {ln}")
    print(f"\n{len(lines)} lines | akshar total {ak_total} "
          f"| min {min(akshar(l) for l in lines)}")
    return 0


def cmd_rhyme(a: str, b: str) -> int:
    r = rhyme(a, b)
    sound, ua, ub = rhyme_strength(a, b)
    verdict = "RHYMES" if is_rhyme(r) else "NO RHYME"
    print(f"{a} / {b}  ->  {r}  ({verdict})")
    print(f"  strength: {sound}  units {ua!r} / {ub!r}")
    if is_rhyme(r) and sound == "WEAK":
        print("  note: same rhyme class but different coda — too weak for poyar")
    if a == b:
        print("  note: identical words are a redif, not a rhyme")
    return 0 if (is_rhyme(r) and sound == "STRONG") else 1


def cmd_review(path: Path, form: str, floor: int,
               akshar_tolerance: int | None = None,
               as_json: bool = False, scheme: str = "blank") -> int:
    """Report-only contract review: per line, per word.

    Python never writes or rewrites verse. It measures every line through MCP and
    emits a structured report — line number, total akshar, band verdict, word
    boundaries, caesura placement, and the rhyme verdict for each couplet — that
    the composing agent reads to find and fix its own errors. The loop is
    write → review → repair until the exit criteria pass.
    """
    lines = read_lines(path)
    if not lines:
        print(f"no content lines in {path}", file=sys.stderr)
        return 2

    tol = meter_tolerance(floor, akshar_tolerance)
    low, high = floor - tol, floor + tol
    report: dict = {
        "file": str(path),
        "form": form,
        "target": floor,
        "tolerance": tol,
        "band": [low, high],
        "lines": [],
        "issues": [],
    }

    for i, line in enumerate(lines, 1):
        words = word_report(line)
        total = words[-1]["cumulative"] if words else 0
        split = caesura_split(words, target_first=8)
        in_band = low <= total <= high
        entry = {
            "line": i,
            "text": line,
            "akshar": total,
            "delta": total - floor,
            "in_band": in_band,
            "verdict": "PASS" if in_band else ("SHORT" if total < low else "LONG"),
            "words": words,
            "caesura": split,
            "end_word": end_word(line),
        }
        if not in_band:
            report["issues"].append(
                f"L{i}: {total} akshar, outside {low}-{high} "
                f"({entry['verdict']} by {abs(total - floor)} "
                f"from target {floor})"
            )
        report["lines"].append(entry)

    if form == "poyar":
        if len(lines) % 2:
            report["issues"].append(
                f"odd line count ({len(lines)}) — couplets need pairs")
        report["couplets"] = []
        for i in range(0, len(lines) - 1, 2):
            a, b = report["lines"][i], report["lines"][i + 1]
            ea, eb = a["end_word"], b["end_word"]
            r = rhyme(ea, eb)
            sound, ua, ub = rhyme_strength(ea, eb)
            pair_ok = is_rhyme(r) and sound == "STRONG"
            distinct = ea != eb
            couplet = {
                "couplet": i // 2 + 1,
                "lines": [a["line"], b["line"]],
                "ends": [ea, eb],
                "rhyme_test": r,
                "strength": sound,
                "rhyme_units": [ua, ub],
                "distinct": distinct,
                "verdict": "PASS" if pair_ok and distinct else "FAIL",
            }
            if not pair_ok:
                report["issues"].append(
                    f"c{couplet['couplet']}: {ea}/{eb} rhyme={r} {sound} "
                    f"(units {ua!r}/{ub!r})")
            if not distinct:
                report["issues"].append(
                    f"c{couplet['couplet']}: identical end words {ea} (redif)")
            report["couplets"].append(couplet)

    report["passed"] = not report["issues"]

    if form == "amitra":
        # অমিত্রাক্ষর ছন্দ — blank verse. Meter (akshar + 8 caesura) is mandatory;
        # rhyme is scheme-selected: `blank` = none, `poyar` = couplets,
        # `srijato` = quatrains (L1~L3, L2~L4).
        report["mode"] = scheme
        if scheme == "poyar":
            if len(lines) % 2:
                report["issues"].append(
                    f"odd line count ({len(lines)}) — couplets need pairs")
            report["couplets"] = []
            for i in range(0, len(lines) - 1, 2):
                a, b = report["lines"][i], report["lines"][i + 1]
                ea, eb = a["end_word"], b["end_word"]
                r = rhyme(ea, eb)
                sound, ua, ub = rhyme_strength(ea, eb)
                pair_ok = is_rhyme(r) and sound == "STRONG"
                distinct = ea != eb
                couplet = {
                    "couplet": i // 2 + 1,
                    "lines": [a["line"], b["line"]],
                    "ends": [ea, eb],
                    "rhyme_test": r,
                    "strength": sound,
                    "rhyme_units": [ua, ub],
                    "distinct": distinct,
                    "verdict": "PASS" if pair_ok and distinct else "FAIL",
                }
                if not pair_ok:
                    report["issues"].append(
                        f"c{couplet['couplet']}: {ea}/{eb} rhyme={r} {sound} "
                        f"(units {ua!r}/{ub!r})")
                if not distinct:
                    report["issues"].append(
                        f"c{couplet['couplet']}: identical end words {ea} (redif)")
                report["couplets"].append(couplet)
        elif scheme == "srijato":
            if len(lines) % 4:
                report["issues"].append(
                    f"line count {len(lines)} not a multiple of 4 — "
                    f"quatrains need 4 lines each")
            report["stanzas"] = []
            for s in range(0, len(lines) - 3, 4):
                block = report["lines"][s:s + 4]
                ends = [b["end_word"] for b in block]
                stanza = {
                    "stanza": s // 4 + 1,
                    "ends": ends,
                    "pairs": [],
                    "verdict": "PASS",
                }
                for i, j in ((0, 2), (1, 3)):
                    r = rhyme(ends[i], ends[j])
                    ok = is_rhyme(r)
                    stanza["pairs"].append(
                        {"lines": [s + i + 1, s + j + 1],
                         "ends": [ends[i], ends[j]],
                         "rhyme_test": r,
                         "ok": ok})
                    if not ok:
                        stanza["verdict"] = "FAIL"
                        report["issues"].append(
                            f"stanza {stanza['stanza']}: L{i + 1}~L{j + 1} "
                            f"{ends[i]}/{ends[j]} -> {r}")
                report["stanzas"].append(stanza)
        # blank mode: no rhyme constraints — meter and caesura only.
        report["passed"] = not report["issues"]

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["passed"] else 1

    print(f"=== REVIEW {path.name} — form={form} ===")
    print(f"Target  : {floor} akshar/line, band {low}-{high} (+/-{tol})")
    print(f"Lines   : {len(lines)}")
    print()
    for e in report["lines"]:
        mark = "PASS" if e["in_band"] else "FAIL"
        print(f"L{e['line']:02d} [{e['akshar']:2d} ak] {mark} "
              f"({e['delta']:+d} vs {floor})")
        print(f"     {e['text']}")
        words = "  ".join(
            f"{w['word']}({w['akshar']}→{w['cumulative']})" for w in e["words"])
        print(f"     words: {words}")
        c = e["caesura"]
        if c["at"] is None:
            print("     caesura: none (no words)")
        else:
            exact = "exact" if c["exact"] else f"off by {c['delta']:+d}"
            print(f"     caesura: {c['first']} + {c['second']} "
                  f"at word {c['at'] + 1} ({exact} vs 8)")
        print()

    if form == "poyar":
        print("Couplets:")
        for c in report.get("couplets", []):
            print(f"  c{c['couplet']:02d} {c['ends'][0]}/{c['ends'][1]} "
                  f"rhyme={c['rhyme_test']} {c['strength']} "
                  f"units {c['rhyme_units'][0]!r}/{c['rhyme_units'][1]!r} "
                  f"{c['verdict']}"
                  f"{'' if c['distinct'] else ' REDIF'}")
        print()

    if form == "amitra":
        print(f"Mode: {report.get('mode', 'blank')}")
        if report.get("mode") == "poyar":
            print("Couplets:")
            for c in report.get("couplets", []):
                print(f"  c{c['couplet']:02d} {c['ends'][0]}/{c['ends'][1]} "
                      f"rhyme={c['rhyme_test']} {c['strength']} "
                      f"units {c['rhyme_units'][0]!r}/{c['rhyme_units'][1]!r} "
                      f"{c['verdict']}"
                      f"{'' if c['distinct'] else ' REDIF'}")
        elif report.get("mode") == "srijato":
            print("Stanzas:")
            for s in report.get("stanzas", []):
                print(f"  stanza {s['stanza']}: {s['ends']} {s['verdict']}")
        print()

    print("Issues:")
    if report["issues"]:
        for issue in report["issues"]:
            print(f"  - {issue}")
    else:
        print("  none")
    print()
    print(f"=== {'PASS' if report['passed'] else 'NEEDS REPAIR'} ===")
    return 0 if report["passed"] else 1


def cmd_family(word: str, limit: int) -> int:
    members = family(word, limit=limit)
    if not members:
        print(f"no verified rhymes found for {word}")
        return 0
    print(f"rhyme class of {word} ({len(members)} verified):")
    for w in members:
        print(f"  {akshar(w):>3} ak  {w}")
    return 0


def _find_refrain(lines: list[str], min_block: int = 2) -> tuple[int, int] | None:
    """Detect a verbatim repeated block. Returns (block_size, repetitions) or None."""
    n = len(lines)
    for size in range(min_block, n // 2 + 1):
        block = [l.strip() for l in lines[:size]]
        reps = 1
        idx = size
        while idx + size <= n and [l.strip() for l in lines[idx:idx + size]] == block:
            reps += 1
            idx += size
        if reps >= 2:
            return (size, reps)
        # also scan for a later verbatim repeat of the opening block
        for start in range(size, n - size + 1):
            if [l.strip() for l in lines[start:start + size]] == block:
                return (size, 2)
    return None


def cmd_audit(path: Path, form: str, scheme: str, floor: int,
              maxlen: int = 0, shortlen: int = 0,
              syllable_target: int = 8, syllable_tol: int | None = None,
              akshar_tolerance: int | None = None) -> int:
    lines = read_lines(path)
    if not lines:
        print(f"no content lines in {path}", file=sys.stderr)
        return 2

    print(f"=== AUDIT {path.name} — form={form} ===")
    failures = 0

    if form == "poyar":
        if len(lines) % 2:
            print(f"  FAIL  odd line count ({len(lines)}) — couplets need pairs")
            failures += 1
        tol = meter_tolerance(floor, akshar_tolerance)
        print(f"  line ruler: akshar (target {floor} +/- {tol} = "
              f"{floor - tol}-{floor + tol})")
        counts = []
        weak = 0
        feet_ok = 0
        for i in range(0, len(lines) - 1, 2):
            a, b = lines[i], lines[i + 1]
            ca, cb = akshar(a), akshar(b)
            counts += [ca, cb]
            ea, eb = end_word(a), end_word(b)
            r = rhyme(ea, eb)
            sound, ua, ub = rhyme_strength(ea, eb)
            meter_ok = abs(ca - floor) <= tol and abs(cb - floor) <= tol
            rhyme_ok = is_rhyme(r) and sound == "STRONG"
            distinct = ea != eb
            good = meter_ok and rhyme_ok and distinct
            if not good:
                failures += 1
            if sound != "STRONG":
                weak += 1
            # The canonical measure is 8 + 6 akshar: a word boundary must fall on
            # akshar 8 of each line. Reported, never failed — a line can be metrically
            # in-band and still lack the caesura at a convenient word edge.
            feet = 0
            for line in (a, b):
                _, bounds = akshar_feet(line)
                if 8 in bounds:
                    feet += 1
            if feet == 2:
                feet_ok += 1
            tag = "OK  " if good else "FAIL"
            why = ""
            if not meter_ok:
                why = (f" akshar {ca}/{cb} outside {floor - tol}-{floor + tol}"
                       f" (target {floor})")
            elif not distinct:
                why = " identical end words (redif)"
            elif not is_rhyme(r):
                why = f" rhyme={r}"
            elif sound != "STRONG":
                why = f" WEAK rhyme {ua!r}/{ub!r}"
            print(f"  {tag} c{i // 2 + 1:2d} [{ca}/{cb} ak] {ea}/{eb} -> {r} "
                  f"{sound}{' 8-caesura' if feet == 2 else ''}{why}")
        exact = sum(1 for c in counts if c == floor)
        in_band = sum(1 for c in counts if abs(c - floor) <= tol)
        band_ok = in_band == len(counts)
        print(f"\n  akshar: min {min(counts)}, max {max(counts)}, "
              f"target {floor} (band {floor - tol}-{floor + tol}) -> "
              f"{'PASS' if band_ok else f'FAIL ({in_band}/{len(counts)} in band)'}")
        print(f"  exact {floor}: {exact}/{len(counts)} lines")
        print(f"  strong rhymes: {len(counts) // 2 - weak}/{len(counts) // 2} "
              f"| 8 caesura: {feet_ok}/{len(counts) // 2}")
        if not band_ok:
            failures += 1

    elif form == "srijato":
        letters = scheme.upper()
        stanza = len(letters)
        if len(lines) % stanza:
            print(f"  FAIL  line count {len(lines)} not a multiple of {stanza}",
                  file=sys.stderr)
            failures += 1
        for s in range(len(lines) // stanza):
            block = lines[s * stanza:(s + 1) * stanza]
            ends = [end_word(l) for l in block]
            print(f"  stanza {s + 1}: {ends}")
            # ACBD resolves to L1~L3, L2~L4
            if letters == "ACBD":
                pairs = [(0, 2), (1, 3)]
                negatives = [(0, 1)]
            elif letters == "ABAB":
                pairs = [(0, 2), (1, 3)]
                negatives = []
            elif letters == "AABB":
                pairs = [(0, 1), (2, 3)]
                negatives = []
            else:
                print(f"  unsupported scheme {letters}", file=sys.stderr)
                return 2
            for i, j in pairs:
                r = rhyme(ends[i], ends[j])
                ok = is_rhyme(r)
                failures += 0 if ok else 1
                print(f"    {'OK  ' if ok else 'FAIL'} L{i + 1}~L{j + 1} "
                      f"{ends[i]}/{ends[j]} -> {r}")
            for i, j in negatives:
                r = rhyme(ends[i], ends[j])
                ok = not is_rhyme(r)
                failures += 0 if ok else 1
                print(f"    {'OK  ' if ok else 'FAIL'} L{i + 1}~L{j + 1} must NOT "
                      f"rhyme {ends[i]}/{ends[j]} -> {r}")

    elif form == "amitra":
        # অমিত্রাক্ষর ছন্দ — blank verse. Meter (akshar + 8 caesura) is mandatory;
        # rhyme is scheme-selected: `blank` = none, `poyar` = couplets,
        # `srijato` = quatrains (L1~L3, L2~L4).
        tol = meter_tolerance(floor, akshar_tolerance)
        print(f"  line ruler: akshar (target {floor} +/- {tol} = "
              f"{floor - tol}-{floor + tol}); mode={scheme}")
        counts = []
        feet_ok = 0
        for line in lines:
            counts.append(akshar(line))
            _, bounds = akshar_feet(line)
            if 8 in bounds:
                feet_ok += 1
        in_band = sum(1 for c in counts if abs(c - floor) <= tol)
        band_ok = in_band == len(counts)
        if not band_ok:
            failures += 1
        print(f"  akshar: min {min(counts)}, max {max(counts)}, "
              f"target {floor} (band {floor - tol}-{floor + tol}) -> "
              f"{'PASS' if band_ok else f'FAIL ({in_band}/{len(counts)} in band)'}")
        print(f"  exact {floor}: {sum(1 for c in counts if c == floor)}/{len(counts)} "
              f"| 8 caesura: {feet_ok}/{len(counts)}")
        if scheme == "poyar":
            if len(lines) % 2:
                print(f"  FAIL  odd line count ({len(lines)}) — couplets need pairs",
                      file=sys.stderr)
                failures += 1
            for i in range(0, len(lines) - 1, 2):
                ea, eb = end_word(lines[i]), end_word(lines[i + 1])
                r = rhyme(ea, eb)
                sound, ua, ub = rhyme_strength(ea, eb)
                ok = is_rhyme(r) and sound == "STRONG" and ea != eb
                failures += 0 if ok else 1
                print(f"    {'OK  ' if ok else 'FAIL'} c{i // 2 + 1} "
                      f"{ea}/{eb} -> {r} {sound}")
        elif scheme == "srijato":
            if len(lines) % 4:
                print(f"  FAIL  line count {len(lines)} not a multiple of 4",
                      file=sys.stderr)
                failures += 1
            for s in range(0, len(lines) - 3, 4):
                ends = [end_word(lines[s + k]) for k in range(4)]
                for i, j in ((0, 2), (1, 3)):
                    r = rhyme(ends[i], ends[j])
                    ok = is_rhyme(r)
                    failures += 0 if ok else 1
                    print(f"    {'OK  ' if ok else 'FAIL'} "
                          f"stanza {s // 4 + 1} L{i + 1}~L{j + 1} "
                          f"{ends[i]}/{ends[j]} -> {r}")

    elif form == "haiku":
        # 3 lines, akshar pattern 5-7-5 (+/-10%), no rhyme requirement
        pattern = [5, 7, 5]
        if len(lines) != len(pattern):
            print(f"  FAIL  haiku needs exactly {len(pattern)} lines, got {len(lines)}")
            failures += 1
        print("  line ruler: akshar (targets 5-7-5, +/-10%)")
        for i, (ln, want) in enumerate(zip(lines, pattern), 1):
            got = akshar(ln)
            tol = meter_tolerance(want, akshar_tolerance)
            ok = abs(got - want) <= tol
            failures += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FAIL'} L{i} [{got}] expected {want} "
                  f"(band {want - tol}-{want + tol})  {ln}")
        if lines:
            ends = [end_word(l) for l in lines]
            print(f"  (rhyme not required; ends: {ends})")

    elif form == "limerick":
        # 5 lines, AABBA; L1/L2/L5 long, L3/L4 short.
        # The long/short lengths are NOT a single fixed scheme: the poet selects
        # one pattern from a menu (e.g. 16/8, 22/12, 14/7 ...). The audit derives
        # the chosen long and short targets from the poem itself and enforces
        # *internal consistency* (all long lines match, all short lines match),
        # each within +/-10%. Explicit --maxlen/--shortlen overrides derivation.
        if len(lines) != 5:
            print(f"  FAIL  limerick needs exactly 5 lines, got {len(lines)}")
            failures += 1
        counts = [syllable_line(ln) for ln in lines]
        long_vals = [counts[i] for i in (0, 1, 4)]
        short_vals = [counts[i] for i in (2, 3)]
        if maxlen:
            long_target = maxlen
        else:
            long_target = max(set(long_vals), key=long_vals.count)  # modal long
        if shortlen:
            short_target = shortlen
        else:
            short_target = max(set(short_vals), key=short_vals.count)  # modal short
        targets = [long_target, long_target, short_target, short_target, long_target]
        print(f"  line ruler: syllable — derived pattern "
              f"long {long_target} / short {short_target} (+/-10%)"
              + (" (--maxlen/--shortlen override)" if (maxlen or shortlen) else ""))
        for i, ln in enumerate(lines, 1):
            got = counts[i - 1]
            want = targets[i - 1]
            tol = meter_tolerance(want, syllable_tol)
            ok = abs(got - want) <= tol
            failures += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FAIL'} L{i} [{got}] expected {want} "
                  f"(band {want - tol}-{want + tol})  {ln}")
        ends = [end_word(l) for l in lines]
        # AABBA: L1~L2, L1~L5, L3~L4
        pairs = [(0, 1, "A"), (0, 4, "A"), (2, 3, "B")]
        for i, j, fam in pairs:
            if i < len(ends) and j < len(ends):
                r = rhyme(ends[i], ends[j])
                ok = is_rhyme(r)
                failures += 0 if ok else 1
                distinct = ends[i] != ends[j]
                if not distinct:
                    ok = False
                    failures += 1
                print(f"  {'OK  ' if ok else 'FAIL'} L{i + 1}~L{j + 1} ({fam}) "
                      f"{ends[i]}/{ends[j]} -> {r}"
                      f"{' (redif)' if not distinct else ''}")

    elif form == "lyrics":
        # refrain + verses, syllable meter. Contract: refrain repeats verbatim,
        # and parallel lines share a syllable signature.
        target = syllable_target if syllable_target else 8
        tol = meter_tolerance(target, syllable_tol)
        counts = []
        print(f"  line ruler: syllable (target {target} +/- {tol})")
        for i, ln in enumerate(lines, 1):
            got = syllable_line(ln)
            counts.append(got)
            ok = abs(got - target) <= tol
            failures += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FAIL'} L{i:2d} [{got}] {ln}")

        # detect a verbatim repeated block = the refrain
        refrain = _find_refrain(lines)
        if refrain:
            blocks, reps = refrain
            print(f"\n  refrain detected: {reps} lines repeated {blocks} times")
            if blocks < 2:
                print("  note: a refrain should repeat at least twice")
        else:
            print("\n  warning: no verbatim repeated block found — lyrics expects a refrain")

        # rhyme is encouraged, not mandatory: report only
        ends = [end_word(l) for l in lines]
        hits = sum(
            1 for i in range(len(ends) - 1) if is_rhyme(rhyme(ends[i], ends[i + 1]))
        )
        print(f"  adjacent end-rhymes: {hits}/{max(len(ends) - 1, 0)} (encouraged, not required)")

    else:
        print(f"unknown form {form!r} (use poyar|srijato|haiku|limerick|lyrics)",
              file=sys.stderr)
        return 2

    print(f"\n=== {'PASS' if failures == 0 else f'{failures} FAILURE(S)'} ===")
    return 0 if failures == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="verse.py",
        description="Bengali verse measurement and contract audit (MCP-backed).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("measure", help="measure akshar/syllable per line")
    m.add_argument("file", type=Path)
    m.add_argument("--syllable", action="store_true", help="also show syllable count")

    r = sub.add_parser("rhyme", help="test whether two words rhyme")
    r.add_argument("a")
    r.add_argument("b")

    f = sub.add_parser("family", help="list verified rhyme-class candidates")
    f.add_argument("word")
    f.add_argument("--limit", type=int, default=12)

    rv = sub.add_parser(
        "review",
        help="report-only contract review: per line, per word (for the composing agent)")
    rv.add_argument("file", type=Path)
    rv.add_argument("--form", default="poyar", choices=["poyar", "amitra", "free"],
                    help="contract to review against (default: poyar)")
    rv.add_argument("--target", type=int, default=14,
                    help="akshar target per line (default 14)")
    rv.add_argument("--akshar-tolerance", type=int, default=None,
                    help="akshar tolerance (default: 10%% of target, min 1 -> 14 gives 12-16)")
    rv.add_argument("--scheme", default="blank",
                    choices=["blank", "poyar", "srijato"],
                    help="amitra rhyme mode (blank=no rhyme, poyar=couplets, srijato=quatrains)")
    rv.add_argument("--json", action="store_true",
                    help="emit the report as JSON (machine-readable for the agent)")

    a = sub.add_parser("audit", help="audit a chapter against a form contract")
    a.add_argument("file", type=Path)
    a.add_argument("--form", default="poyar",
                   choices=["poyar", "srijato", "haiku", "limerick", "lyrics", "amitra"])
    a.add_argument("--scheme", default="ACBD",
                   help="srijato scheme (ACBD/ABAB/AABB); amitra mode (blank/poyar/srijato)")
    a.add_argument("--floor", type=int, default=14,
                   help="poyar line length: akshar target per line (default 14)")
    a.add_argument("--maxlen", type=int, default=0,
                   help="limerick long-line syllables (L1/L2/L5); "
                        "0 = derive from the poem (self-consistent pattern)")
    a.add_argument("--shortlen", type=int, default=0,
                   help="limerick short-line syllables (L3/L4); "
                        "0 = derive from the poem (self-consistent pattern)")
    a.add_argument("--syllable-target", type=int, default=8,
                   help="lyrics syllables per line (default 8)")
    a.add_argument("--syllable-tol", type=int, default=None,
                   help="lyrics syllable tolerance (default: 10%% of target, min 1)")
    a.add_argument("--akshar-tolerance", type=int, default=None,
                   help="akshar tolerance for poyar/haiku "
                        "(default: 10%% of target, min 1 -> 14 gives 12-16)")

    args = p.parse_args(argv)

    try:
        if args.cmd == "measure":
            return cmd_measure(args.file, args.syllable)
        if args.cmd == "rhyme":
            return cmd_rhyme(args.a, args.b)
        if args.cmd == "family":
            return cmd_family(args.word, args.limit)
        if args.cmd == "review":
            return cmd_review(args.file, args.form, args.target,
                              args.akshar_tolerance, args.json, args.scheme)
        if args.cmd == "audit":
            return cmd_audit(args.file, args.form, args.scheme, args.floor,
                             args.maxlen, args.shortlen,
                             args.syllable_target, args.syllable_tol,
                             args.akshar_tolerance)
    except FileNotFoundError as exc:
        print(f"file not found: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface MCP failures cleanly
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    sys.exit(main())
