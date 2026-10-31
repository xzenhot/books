#!/usr/bin/env python3
"""env.py — the single `.env` loader for every Python tool in this workspace.

Canonical location: ``<writer>/.env`` (the directory this `tools/` folder lives
in). Every entry point calls :func:`load_env` before reading the environment, so
all tools agree on one file regardless of which script was invoked.

Resolution is anchored to this module's own path, not to the process working
directory, so a tool behaves the same whether it is launched from the writer
root, from `tools/`, or by an MCP client from an arbitrary directory.

Precedence (highest first):

1. Real environment variables (shell, MCP client ``env`` block, CI secrets)
2. ``<writer>/.env``
3. An optional ``.env`` in the current working directory (for one-off overrides)

Existing values are never overwritten unless ``override=True`` is passed.

python-dotenv is used when installed; otherwise a small stdlib parser handles the
same syntax (``KEY=value``, ``#`` comments, optional ``export``, quoted values),
so every tool keeps working in a bare interpreter.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# tools/env.py -> tools -> <writer>
WRITER_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = WRITER_ROOT / ".env"

_loaded: Optional[dict[str, str]] = None


def _parse_fallback(text: str) -> dict[str, str]:
    """Minimal .env parser used when python-dotenv is unavailable."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            # Strip an unquoted inline comment: `KEY=value  # note`
            hash_index = value.find(" #")
            if hash_index != -1:
                value = value[:hash_index].rstrip()
        if key:
            values[key] = value
    return values


def _read(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return {}

    try:
        from dotenv import dotenv_values
    except ImportError:
        return _parse_fallback(text)

    return {k: v for k, v in dotenv_values(path, encoding="utf-8-sig").items() if v is not None}


def load_env(path: Optional[Path] = None, override: bool = False, *, cwd: bool = True) -> dict[str, str]:
    """Load `.env` into ``os.environ`` and return the values that were defined.

    Args:
        path: Explicit file to load. Defaults to ``<writer>/.env``.
        override: When True, ``.env`` values replace existing environment
            variables. Default False — real environment variables win.
        cwd: Also load ``.env`` from the current working directory when it is a
            different file, for one-off overrides.

    Returns:
        The key/value pairs read from the file(s), whether or not they were
        applied (real environment variables take precedence).
    """
    global _loaded

    primary = path or ENV_PATH
    candidates = [primary]
    if cwd:
        local = Path.cwd() / ".env"
        if local.resolve() != primary.resolve():
            candidates.append(local)

    collected: dict[str, str] = {}
    for candidate in candidates:
        if not candidate.exists():
            continue
        for key, value in _read(candidate).items():
            collected.setdefault(key, value)
            if override or key not in os.environ:
                os.environ[key] = value

    _loaded = collected
    return collected


def get(name: str, default: str = "") -> str:
    """Read a variable, loading `.env` first if that has not happened yet."""
    if _loaded is None:
        load_env()
    return os.environ.get(name, default).strip()


def require(name: str, hint: str = "") -> str:
    """Read a required variable, exiting with an actionable message when absent."""
    value = get(name)
    if not value:
        message = f"{name} is not set. Add it to {ENV_PATH}"
        if hint:
            message = f"{message} ({hint})"
        raise SystemExit(message)
    return value


def bootstrap() -> None:
    """Entry-point hook: load `.env` and make the interpreter mode UTF-8 safe.

    Windows consoles default to a legacy code page, which breaks printing
    Bengali. Every tool that prints book text calls this once at startup.
    """
    load_env()
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    loaded = load_env()
    print(f"env file: {ENV_PATH} ({'found' if ENV_PATH.exists() else 'MISSING'})")
    if not loaded:
        print("no values defined")
    for key in sorted(loaded):
        print(f"  {key} = {'<set>' if os.environ.get(key) else '<empty>'}")
