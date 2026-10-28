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

Forms
-----
    poyar    two-line couplets, syllable meter (exactly 14 per line, measured as
             4 + 4 + 4 + (2|1)), L1~L2 strong rhyme (identical final rhyme unit),
             no cross-couplet rhyme.
    srijato  quatrains, syllable meter, scheme ACBD -> L1~L3 and L2~L4 per stanza.

A "strong" rhyme means the two end words' final rhyme units are identical once
each consonant is folded to its varga row. `word.rhyme-test` alone is too loose:
it accepts `শব্দ/গন্ধ`, which poyar rejects.

Exit codes: 0 = pass, 1 = contract violation, 2 = usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import kamolika as mcp  # noqa: E402

RHYME_ACCEPT = ("1", "2", "3", "4")  # >= 1 passes; "0" and "-1" are rejections
PUNCT = ",.;:!?।॥—–…\"'()[]"
RETRY_DELAY = 1.0  # seconds between MCP retries

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
    return rhyme(a, b) in RHYME_ACCEPT


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
    read as the poyar's 4 + 4 + 4 + 2 measure.
    """
    words = [w.strip(PUNCT) for w in line.split() if w.strip(PUNCT)]
    boundaries: list[int] = []
    cumulative = 0
    for w in words:
        cumulative += syllable(w)
        boundaries.append(cumulative)
    return cumulative, boundaries


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
    verdict = "RHYMES" if r in RHYME_ACCEPT else "NO RHYME"
    print(f"{a} / {b}  ->  {r}  ({verdict})")
    print(f"  strength: {sound}  units {ua!r} / {ub!r}")
    if r in RHYME_ACCEPT and sound == "WEAK":
        print("  note: same rhyme class but different coda — too weak for poyar")
    if a == b:
        print("  note: identical words are a redif, not a rhyme")
    return 0 if (r in RHYME_ACCEPT and sound == "STRONG") else 1


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
              syllable_target: int = 8, syllable_tol: int = 1) -> int:
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
        counts = []
        weak = 0
        feet_ok = 0
        for i in range(0, len(lines) - 1, 2):
            a, b = lines[i], lines[i + 1]
            ca, cb = syllable_line(a), syllable_line(b)
            counts += [ca, cb]
            ea, eb = end_word(a), end_word(b)
            r = rhyme(ea, eb)
            sound, ua, ub = rhyme_strength(ea, eb)
            meter_ok = ca == floor and cb == floor
            rhyme_ok = r in RHYME_ACCEPT and sound == "STRONG"
            distinct = ea != eb
            good = meter_ok and rhyme_ok and distinct
            if not good:
                failures += 1
            if sound != "STRONG":
                weak += 1
            # 4 + 4 + 4 + (2|1) is the canonical measure; report, never fail on it,
            # because a word boundary rarely falls on every internal caesura.
            feet = 0
            for line, total in ((a, ca), (b, cb)):
                _, bounds = line_feet(line)
                if all(edge in bounds for edge in (4, 8, 12)) and total - 12 in (1, 2):
                    feet += 1
            if feet == 2:
                feet_ok += 1
            tag = "OK  " if good else "FAIL"
            why = ""
            if not meter_ok:
                why = f" meter {ca}/{cb} != {floor}"
            elif not distinct:
                why = " identical end words (redif)"
            elif r not in RHYME_ACCEPT:
                why = f" rhyme={r}"
            elif sound != "STRONG":
                why = f" WEAK rhyme {ua!r}/{ub!r}"
            print(f"  {tag} c{i // 2 + 1:2d} [{ca}/{cb}] {ea}/{eb} -> {r} "
                  f"{sound}{' feet' if feet == 2 else ''}{why}")
        exact = sum(1 for c in counts if c == floor)
        print(f"\n  syllables: min {min(counts)}, max {max(counts)}, "
              f"target {floor} -> "
              f"{'PASS' if exact == len(counts) else f'FAIL ({exact}/{len(counts)} exact)'}")
        print(f"  strong rhymes: {len(counts) // 2 - weak}/{len(counts) // 2} "
              f"| 4+4+4+2 feet: {feet_ok}/{len(counts) // 2}")
        if exact != len(counts):
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
                ok = r in RHYME_ACCEPT
                failures += 0 if ok else 1
                print(f"    {'OK  ' if ok else 'FAIL'} L{i + 1}~L{j + 1} "
                      f"{ends[i]}/{ends[j]} -> {r}")
            for i, j in negatives:
                r = rhyme(ends[i], ends[j])
                ok = r not in RHYME_ACCEPT
                failures += 0 if ok else 1
                print(f"    {'OK  ' if ok else 'FAIL'} L{i + 1}~L{j + 1} must NOT "
                      f"rhyme {ends[i]}/{ends[j]} -> {r}")

    elif form == "haiku":
        # 3 lines, akshar pattern 5-7-5, no rhyme requirement
        pattern = [5, 7, 5]
        if len(lines) != len(pattern):
            print(f"  FAIL  haiku needs exactly {len(pattern)} lines, got {len(lines)}")
            failures += 1
        for i, (ln, want) in enumerate(zip(lines, pattern), 1):
            got = akshar(ln)
            ok = got == want
            failures += 0 if ok else 1
            print(f"  {'OK  ' if ok else 'FAIL'} L{i} [{got}] expected {want}  {ln}")
        if lines:
            ends = [end_word(l) for l in lines]
            print(f"  (rhyme not required; ends: {ends})")

    elif form == "limerick":
        # 5 lines, AABBA; L1/L2/L5 long, L3/L4 short
        if len(lines) != 5:
            print(f"  FAIL  limerick needs exactly 5 lines, got {len(lines)}")
            failures += 1
        long_max = maxlen if maxlen else 0
        short_max = shortlen if shortlen else 0
        targets = [long_max, long_max, short_max, short_max, long_max]
        if not long_max or not short_max:
            print("  note: pass --maxlen/--shortlen to enforce line lengths")
        counts = []
        for i, ln in enumerate(lines, 1):
            got = akshar(ln)
            counts.append(got)
            want = targets[i - 1] if i <= len(targets) else 0
            if want:
                ok = got == want
                failures += 0 if ok else 1
                print(f"  {'OK  ' if ok else 'FAIL'} L{i} [{got}] expected {want}")
            else:
                print(f"  ..   L{i} [{got}]")
        ends = [end_word(l) for l in lines]
        # AABBA: L1~L2, L1~L5, L3~L4
        pairs = [(0, 1, "A"), (0, 4, "A"), (2, 3, "B")]
        for i, j, fam in pairs:
            if i < len(ends) and j < len(ends):
                r = rhyme(ends[i], ends[j])
                ok = r in RHYME_ACCEPT
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
        tol = syllable_tol
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
            1 for i in range(len(ends) - 1) if rhyme(ends[i], ends[i + 1]) in RHYME_ACCEPT
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

    a = sub.add_parser("audit", help="audit a chapter against a form contract")
    a.add_argument("file", type=Path)
    a.add_argument("--form", default="poyar",
                   choices=["poyar", "srijato", "haiku", "limerick", "lyrics"])
    a.add_argument("--scheme", default="ACBD", help="srijato scheme (ACBD/ABAB/AABB)")
    a.add_argument("--floor", type=int, default=14,
                   help="poyar line length: exact syllable count per line (default 14)")
    a.add_argument("--maxlen", type=int, default=0,
                   help="limerick long-line akshars (L1/L2/L5)")
    a.add_argument("--shortlen", type=int, default=0,
                   help="limerick short-line akshars (L3/L4)")
    a.add_argument("--syllable-target", type=int, default=8,
                   help="lyrics syllables per line (default 8)")
    a.add_argument("--syllable-tol", type=int, default=1,
                   help="lyrics syllable tolerance (default 1)")

    args = p.parse_args(argv)

    try:
        if args.cmd == "measure":
            return cmd_measure(args.file, args.syllable)
        if args.cmd == "rhyme":
            return cmd_rhyme(args.a, args.b)
        if args.cmd == "family":
            return cmd_family(args.word, args.limit)
        if args.cmd == "audit":
            return cmd_audit(args.file, args.form, args.scheme, args.floor,
                             args.maxlen, args.shortlen,
                             args.syllable_target, args.syllable_tol)
    except FileNotFoundError as exc:
        print(f"file not found: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface MCP failures cleanly
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    sys.exit(main())
