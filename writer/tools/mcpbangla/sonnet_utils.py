#!/usr/bin/env python3
"""
sonnet_utils.py - Bengali sonnet calibration helpers.

Wraps the Book.Backend HTTP MCP client to provide akshar (consonant) count and
caesura-split utilities required by the line agent's sonnet mode.

A Bengali sonnet has:
  - Exactly 14 lines
  - Exactly 14 akshars per line
  - Each line split 8 + 6 at the caesura

All akshar counts are obtained via the Book.Backend MCP endpoint's
word.akshar-count tool. Native counting is never used — Bengali consonant
clusters (যুক্তব্যঞ্জন) require the engine for accurate results.

Usage (standalone test):
    python tools/mcpbangla/sonnet_utils.py "আমার সোনার বাংলা আমি তোমায় ভালোবাসি"
"""

import os
import sys

# ---------------------------------------------------------------------------
# Import the HTTP MCP client from the same directory
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import kamolika as _mcp  # noqa: E402


class McpError(Exception):
    """Raised when an MCP call fails."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SONNET_LINES: int = 14          # total lines in a Bengali sonnet
SONNET_AKSHARS: int = 14        # akshars per line
CAESURA_FIRST: int = 8          # akshars in the first half
CAESURA_SECOND: int = 6         # akshars in the second half
CAESURA_MARK: str = " | "       # visual caesura separator


# ---------------------------------------------------------------------------
# Session-scoped MCP handshake (lazy, idempotent)
# ---------------------------------------------------------------------------
_initialized: bool = False


def get_client():
    """Return the MCP client module after ensuring the handshake ran."""
    global _initialized
    if not _initialized:
        try:
            _mcp.initialize()
        except Exception as exc:  # requests/connection errors
            raise McpError(f"MCP endpoint unavailable: {exc}") from exc
        _initialized = True
    return _mcp


def close_client() -> None:
    """Reset the handshake flag (the HTTP endpoint is stateless)."""
    global _initialized
    _initialized = False


# ---------------------------------------------------------------------------
# Core MCP helpers
# ---------------------------------------------------------------------------

def call_tool(name: str, arguments: dict | None = None) -> str:
    """Call an MCP tool and return its plain-text payload."""
    client = get_client()
    try:
        result = client.call_tool(name, arguments or {})
    except Exception as exc:
        raise McpError(f"MCP call '{name}' failed: {exc}") from exc
    return client.extract_text(result)


def akshar_count(text: str) -> int:
    """
    Return the total akshar (consonant) count of a Bengali string.

    Calls word.akshar-count on the full text via the MCP endpoint.
    Never computes natively.

    Args:
        text: Any Bengali word, phrase, or line.

    Returns:
        Integer akshar count as reported by the MCP tool.

    Raises:
        McpError: If the MCP call fails.
        ValueError: If the server response cannot be parsed as an integer.
    """
    raw = call_tool("word.akshar-count", {"word": text.strip()}).strip()
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"word.akshar-count returned non-integer for input {text!r}: {raw!r}"
        )


def akshar_count_word(word: str) -> int:
    """
    Return the akshar count of a single Bengali word.

    Thin alias for akshar_count() — kept separate so call sites in
    caesura-splitting loops are clearly operating per-word.

    Args:
        word: A single Bengali word (no spaces).

    Returns:
        Integer akshar count.
    """
    return akshar_count(word)


# ---------------------------------------------------------------------------
# Caesura splitting
# ---------------------------------------------------------------------------

def find_caesura(
    line: str,
    target_first: int = CAESURA_FIRST,
) -> tuple[str, str]:
    """
    Split a calibrated 14-akshar Bengali line into two halves at the caesura.

    The split point is determined word-by-word: we accumulate akshar counts
    (via the MCP tool) until we have consumed exactly `target_first` akshars,
    then everything that follows is the second half.

    If no word boundary falls exactly at `target_first` akshars, the word that
    would push the count over the boundary is assigned to whichever half keeps
    the split closest to the target — first the second half (prefer not to
    over-fill the first half).

    Args:
        line:         A calibrated Bengali line (14 akshars total).
        target_first: Akshar count for the first half (default 8).

    Returns:
        A tuple (first_half, second_half) of stripped strings.
        Neither half contains the caesura mark — callers apply CAESURA_MARK
        when formatting for output.

    Raises:
        McpError:   If any MCP call fails.
        ValueError: If the line is empty or produces zero akshars.
    """
    words = line.strip().split()
    if not words:
        raise ValueError("find_caesura received an empty line.")

    first_words: list[str] = []
    second_words: list[str] = []
    accumulated = 0
    split_done = False

    for word in words:
        if split_done:
            second_words.append(word)
            continue

        word_count = akshar_count_word(word)

        if accumulated + word_count <= target_first:
            # Word fits entirely in the first half
            first_words.append(word)
            accumulated += word_count
            if accumulated == target_first:
                split_done = True
        else:
            # This word would push us over — assign to second half
            # (do not over-fill the first half)
            second_words.append(word)
            split_done = True

    return " ".join(first_words), " ".join(second_words)


def format_caesura(line: str, target_first: int = CAESURA_FIRST) -> str:
    """
    Return a line formatted with the caesura mark.

    Example:
        "আমার সোনার বাংলা আমি তোমায় ভালো" → "আমার সোনার বাংলা | আমি তোমায় ভালো"

    Args:
        line:         Calibrated 14-akshar Bengali line.
        target_first: Akshars in the first half (default 8).

    Returns:
        Formatted string with CAESURA_MARK between the two halves.
    """
    first, second = find_caesura(line, target_first)
    return f"{first}{CAESURA_MARK}{second}"


# ---------------------------------------------------------------------------
# Line-level calibration
# ---------------------------------------------------------------------------

def calibrate_line(line: str, target: int = SONNET_AKSHARS) -> tuple[str, str]:
    """
    Return the akshar count status of a line against the target.

    This function only *reports* the status — it does not rewrite the line.
    Actual rewriting is the responsibility of the line agent, which has access
    to the poem's semantic context and can make meaning-preserving edits.

    Args:
        line:   Bengali line to check.
        target: Target akshar count (default 14).

    Returns:
        A tuple (status, detail) where status is one of:
          "calibrated"  — line already matches target
          "underflow"   — line is below target (needs expansion)
          "overflow"    — line is above target (needs reduction)
        and detail is a human-readable description with actual count.
    """
    count = akshar_count(line)
    if count == target:
        return "calibrated", f"akshar count = {count} ✓"
    elif count < target:
        return "underflow", f"akshar count = {count}, need {target - count} more"
    else:
        return "overflow", f"akshar count = {count}, need to reduce by {count - target}"


def check_sonnet(lines: list[str]) -> dict:
    """
    Run a full sonnet validity check on a list of lines.

    Returns a report dict suitable for agent logging:
      {
        "total_lines": int,
        "line_count_ok": bool,
        "lines": [
          {"n": 1, "text": "...", "akshar_count": int, "status": "calibrated"|..., "detail": "..."},
          ...
        ],
        "all_calibrated": bool,
        "needs_review": [line numbers that are not calibrated]
      }
    """
    report = {
        "total_lines": len(lines),
        "line_count_ok": len(lines) == SONNET_LINES,
        "lines": [],
        "all_calibrated": True,
        "needs_review": [],
    }

    for i, line in enumerate(lines, start=1):
        count = akshar_count(line)
        status, detail = calibrate_line(line, SONNET_AKSHARS)
        entry = {
            "n": i,
            "text": line,
            "akshar_count": count,
            "status": status,
            "detail": detail,
        }
        report["lines"].append(entry)
        if status != "calibrated":
            report["all_calibrated"] = False
            report["needs_review"].append(i)

    return report


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------

def _self_test(text: str) -> None:
    """Quick smoke-test: count akshars and split at caesura."""
    print(f"Input : {text}")
    try:
        count = akshar_count(text)
        print(f"Akshar count : {count}")

        if count > 0:
            formatted = format_caesura(text)
            print(f"Caesura split: {formatted}")

        status, detail = calibrate_line(text)
        print(f"Status       : {status} — {detail}")
    except (McpError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
    finally:
        close_client()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python tools/mcpbangla/sonnet_utils.py \"<bengali line>\"\n"
            "Example: python tools/mcpbangla/sonnet_utils.py \"আমার সোনার বাংলা আমি তোমায় ভালোবাসি\""
        )
        sys.exit(1)

    input_text = " ".join(sys.argv[1:])
    _self_test(input_text)
