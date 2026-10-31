#!/usr/bin/env python3
"""
mcp_sync.py — keep every MCP client config derived from `.vscode/mcp.json`.

`.vscode/mcp.json` is the single source of truth for MCP servers in this repo.
VS Code reads it directly (with the `server` -> `servers` shape); the Copilot
CLI cannot, because it expects `mcpServers` in `.mcp.json`,
`.github/mcp.json`, or `~/.copilot/mcp-config.json`. This script generates
those files from the canonical one and detects drift, so no client is ever
hand-edited into a divergent state.

Usage
-----
    # show the canonical source, targets, and whether they are in sync
    python tools/mcp_sync.py

    # regenerate every target from the canonical file
    python tools/mcp_sync.py sync

    # exit 1 when a target has drifted (for CI / pre-commit)
    python tools/mcp_sync.py check

Transformations
---------------
    servers            -> mcpServers        (CLI shape)
    type: "stdio"      -> "local"
    ${workspaceFolder:NAME} / ${workspaceFolder}
                       -> absolute path of that workspace folder
    env blocks           -> dropped for stdio servers (they load <writer>/.env
                          through tools/env.py, so no client injects secrets)
    headers with ${input:ID}
                          -> whole server omitted (the CLI cannot prompt)
    builtin servers    -> skipped (the CLI ships its own `github` server)

Secrets live in exactly one place: ``<writer>/.env``, loaded by every Python
entry point through ``tools/env.py``. They are never written into a generated
config.
"""

from __future__ import annotations

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

WRITER_ROOT = Path(__file__).resolve().parent.parent
CANONICAL = WRITER_ROOT / ".vscode" / "mcp.json"

# Servers the Copilot CLI already provides; a user-level duplicate only confuses
# `copilot mcp list`.
BUILTIN_SERVERS = {"github"}


def find_repo_root(start: Path) -> Path:
    """Return the closest ancestor that contains a `.git` entry."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return start


REPO_ROOT = find_repo_root(WRITER_ROOT)


def targets() -> dict[str, dict[str, Any]]:
    """Return the client config files derived from the canonical source.

    ``mode`` decides how the file is maintained:

    ``own``     the file belongs to this repository — written in full.
    ``merge``   a shared user-level file — only servers this repo defines are
                rewritten; anything another project added is preserved.
    """
    return {
        "cli-project": {"path": REPO_ROOT / ".mcp.json", "mode": "own"},
        "cli-user": {"path": Path.home() / ".copilot" / "mcp-config.json", "mode": "merge"},
    }


# ---------------------------------------------------------------------------
# Canonical loading
# ---------------------------------------------------------------------------

def load_canonical() -> dict[str, Any]:
    if not CANONICAL.exists():
        raise SystemExit(f"Canonical MCP config not found: {CANONICAL}")
    with CANONICAL.open(encoding="utf-8") as handle:
        data = json.load(handle)
    servers = data.get("servers")
    if not isinstance(servers, dict):
        raise SystemExit(
            f"{CANONICAL} must contain a top-level \"servers\" object "
            "(VS Code's workspace MCP shape)."
        )
    return data


def _input_ids(canonical: dict[str, Any]) -> dict[str, str]:
    return {item["id"]: item.get("description", "") for item in canonical.get("inputs", []) if "id" in item}


# ---------------------------------------------------------------------------
# Value resolution
# ---------------------------------------------------------------------------

def resolve_workspace_vars(value: str) -> str:
    """Resolve `${workspaceFolder}` / `${workspaceFolder:name}` to real paths."""

    def replace(match) -> str:
        name = match.group(1)
        folder = WRITER_ROOT if name in (None, "", "writer") else REPO_ROOT / name.lstrip("\\/")
        return str(folder).replace("\\", "/")

    import re

    return re.sub(r"\$\{workspaceFolder(?::([^}]*))?\}", replace, value)


def _is_input_ref(value: Any) -> bool:
    return isinstance(value, str) and "${input:" in value


def convert_server(name: str, server: dict[str, Any], warnings: list[str]) -> dict[str, Any] | None:
    """Convert one canonical server entry into the Copilot CLI shape."""
    server_type = str(server.get("type", "stdio")).lower()
    converted: dict[str, Any] = dict(server)

    if server_type == "stdio":
        converted["type"] = "local"
    converted.pop("title", None)

    if "command" in converted:
        converted["command"] = resolve_workspace_vars(str(converted["command"]))
    if isinstance(converted.get("args"), list):
        converted["args"] = [resolve_workspace_vars(str(arg)) for arg in converted["args"]]

    # stdio servers load <writer>/.env themselves through tools/env.py, so a
    # client-side env block is redundant and would duplicate secrets.
    if server_type == "stdio":
        converted.pop("env", None)

    if server_type != "stdio" and isinstance(converted.get("headers"), dict):
        if any(_is_input_ref(v) for v in converted["headers"].values()):
            warnings.append(
                f"server '{name}' omitted: its headers need a ${{input:...}} prompt, "
                "which the Copilot CLI cannot ask for"
            )
            return None

    return converted


def build_target(canonical: dict[str, Any], label: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    servers: dict[str, Any] = {}

    for name, server in canonical["servers"].items():
        if name in BUILTIN_SERVERS:
            continue
        converted = convert_server(name, server, warnings)
        if converted is not None:
            servers[name] = converted

    payload: dict[str, Any] = {"mcpServers": servers}
    return payload, warnings


def dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def read_existing(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def merge_servers(expected: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    """Keep servers this repo does not define, and refresh the ones it owns.

    Ordering is deterministic: this repo's servers first (canonical order), then
    any servers another project contributed.
    """
    owned = expected["mcpServers"]
    foreign = {
        name: server
        for name, server in (existing.get("mcpServers") or {}).items()
        if name not in owned
    }
    return {"mcpServers": {**owned, **dict(sorted(foreign.items()))}}


def _display_path(path: Path) -> str:
    """Show a repo-relative path when possible, else the absolute path."""
    try:
        return os.path.relpath(path, REPO_ROOT)
    except ValueError:
        return str(path)


def reconcile(label: str, target: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    """Return the payload that should be written for one target."""
    if target["mode"] != "merge":
        return expected
    return merge_servers(expected, read_existing(target["path"]))


def is_in_sync(target: dict[str, Any], expected: dict[str, Any]) -> bool:
    path = target["path"]
    if not path.exists():
        return False
    actual = read_existing(path)
    wanted = reconcile("", target, expected)
    # Only compare the servers this repo owns; other projects' entries are
    # allowed to differ.
    owned = set(expected["mcpServers"])
    if target["mode"] == "merge":
        return all(actual.get("mcpServers", {}).get(n) == expected["mcpServers"][n] for n in owned)
    return actual == wanted


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def command_status() -> int:
    canonical = load_canonical()
    print(f"canonical  {CANONICAL}")
    print(f"           {len(canonical['servers'])} servers: {', '.join(canonical['servers'])}")
    print(f"           {len(canonical.get('inputs', []))} input prompt(s)")
    print()

    drift = 0
    for label, target in targets().items():
        expected, warnings = build_target(canonical, label)
        synced = is_in_sync(target, expected)
        extra = ""
        if target["mode"] == "merge":
            other = set((read_existing(target["path"]).get("mcpServers") or {})) - set(expected["mcpServers"])
            if other:
                extra = f" (+{len(other)} from other projects: {', '.join(sorted(other))})"
        state = "in sync" if synced else ("missing" if not target["path"].exists() else "DRIFTED")
        if not synced:
            drift += 1
        print(f"{label:12} {target['path']}  [{state}]{extra}")
        for warning in warnings:
            print(f"             ! {warning}")

    print()
    if drift:
        print(f"{drift} target(s) out of sync — run: python tools/mcp_sync.py sync")
        return 1
    print("All targets match the canonical .vscode/mcp.json.")
    return 0


def command_sync() -> int:
    canonical = load_canonical()
    for label, target in targets().items():
        expected, warnings = build_target(canonical, label)
        payload = reconcile(label, target, expected)
        path = target["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(payload), encoding="utf-8")
        note = " (merged, other projects preserved)" if target["mode"] == "merge" else ""
        print(f"wrote {label:12} {path}  ({len(payload['mcpServers'])} servers){note}")
        for warning in warnings:
            print(f"  ! {warning}")
    print("\nRegenerate these files from .vscode/mcp.json before editing them.")
    return 0


def command_check() -> int:
    canonical = load_canonical()
    drift = False
    for label, target in targets().items():
        expected, _ = build_target(canonical, label)
        if not is_in_sync(target, expected):
            print(f"DRIFT: {_display_path(target['path'])} does not match .vscode/mcp.json")
            drift = True
    if drift:
        print("\nRun: python tools/mcp_sync.py sync")
        return 1
    print("MCP configs are in sync with .vscode/mcp.json.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        choices=("status", "sync", "check"),
        help="status (default), sync, or check",
    )
    args = parser.parse_args()
    return {"status": command_status, "sync": command_sync, "check": command_check}[args.command]()


if __name__ == "__main__":
    sys.exit(main())
