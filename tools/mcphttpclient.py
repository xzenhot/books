"""
mcp.py — Python MCP client for Book.Backend
============================================
Talks to the three HTTP endpoints exposed by McpHttpHandler:

    POST /mcp/initialize
    GET  /mcp/tools
    POST /mcp/call/{toolName}

Usage
-----
    # interactive REPL
    python mcp.py

    # one-shot commands
    python mcp.py init
    python mcp.py tools
    python mcp.py call write_book '{"bookName":"MyBook"}'
    python mcp.py call get_dashboard '{}'
    python mcp.py call expand_idea '{"seed":"A story about time travel"}'

Dependencies
------------
    pip install requests
"""

from __future__ import annotations

import json
import sys
import textwrap
import urllib3
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("requests is not installed. Run:  pip install requests")

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL    = "https://localhost:64485"  # TLS endpoint; http://localhost:64486 is the non-TLS bind
VERIFY_TLS  = False                       # set True in production with a real cert
TIMEOUT     = 30                          # seconds

# Suppress the "InsecureRequestWarning" when VERIFY_TLS is False
if not VERIFY_TLS:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Low-level HTTP helpers ─────────────────────────────────────────────────────

def _get(path: str) -> Any:
    url = BASE_URL.rstrip("/") + path
    r = requests.get(url, verify=VERIFY_TLS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict | None = None) -> Any:
    url = BASE_URL.rstrip("/") + path
    r = requests.post(
        url,
        json=body or {},
        headers={"Content-Type": "application/json"},
        verify=VERIFY_TLS,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


# ── Public client API ──────────────────────────────────────────────────────────

def initialize() -> dict:
    """Send the MCP handshake and return the server info payload."""
    return _post("/mcp/initialize")


def list_tools() -> list[dict]:
    """Return the list of available tool descriptors."""
    data = _get("/mcp/tools")
    return data.get("tools", data)


def call_tool(tool_name: str, arguments: dict | None = None) -> dict:
    """
    Invoke a named tool with optional arguments dict.
    Returns the MCP content-block envelope:
        { "content": [{"type": "text", "text": "..."}], "isError": false }
    """
    return _post(f"/mcp/call/{tool_name}", arguments or {})


def extract_text(result: dict) -> str:
    """Pull the plain text out of an MCP content-block envelope."""
    blocks = result.get("content", [])
    return "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text")


# ── Pretty-print helpers ───────────────────────────────────────────────────────

def _banner(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2))


def _print_tools(tools: list[dict]) -> None:
    if not tools:
        print("  (no tools returned)")
        return
    for t in tools:
        name  = t.get("name", "?")
        desc  = t.get("description", "")
        schema = t.get("inputSchema", {})
        props  = schema.get("properties", {})
        params = ", ".join(props.keys()) if props else "—"
        print(f"  • {name}")
        print(f"      {desc}")
        print(f"      params: {params}")


# ── CLI commands ───────────────────────────────────────────────────────────────

def cmd_init() -> None:
    _banner("MCP Initialize")
    result = initialize()
    _print_json(result)


def cmd_tools() -> None:
    _banner("Available Tools")
    tools = list_tools()
    _print_tools(tools)
    print(f"\n  Total: {len(tools)} tool(s)")


def cmd_call(tool_name: str, args_json: str = "{}") -> None:
    _banner(f"Call → {tool_name}")
    try:
        args = json.loads(args_json)
    except json.JSONDecodeError as e:
        sys.exit(f"Invalid JSON for arguments: {e}")

    result = call_tool(tool_name, args)
    text   = extract_text(result)
    is_err = result.get("isError", False)

    if is_err:
        print(f"  ERROR: {text}")
    else:
        print(f"  {text}")


# ── Interactive REPL ───────────────────────────────────────────────────────────

HELP_TEXT = textwrap.dedent("""
    Commands:
      init                          — MCP handshake
      tools                         — list available tools
      call <toolName> [argsJson]    — invoke a tool
      help                          — show this help
      quit / exit                   — exit

    Examples:
      call write_book {"bookName":"MyBook"}
      call get_dashboard {}
      call expand_idea {"seed":"robots fall in love"}
      call suggest_book_name {"gist":"A love story between robots"}
      call get_book {"bookName":"MyBook"}
""")


def repl() -> None:
    print("Book.Backend MCP Client")
    print(f"Connected to: {BASE_URL}")
    print('Type "help" for commands, "quit" to exit.\n')

    while True:
        try:
            line = input("mcp> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split(None, 2)   # split into at most 3 parts
        cmd   = parts[0].lower()

        if cmd in ("quit", "exit"):
            break
        elif cmd == "help":
            print(HELP_TEXT)
        elif cmd == "init":
            cmd_init()
        elif cmd == "tools":
            cmd_tools()
        elif cmd == "call":
            if len(parts) < 2:
                print("  Usage: call <toolName> [argsJson]")
                continue
            tool_name = parts[1]
            args_json = parts[2] if len(parts) > 2 else "{}"
            try:
                cmd_call(tool_name, args_json)
            except requests.HTTPError as e:
                print(f"  HTTP error: {e}")
            except requests.ConnectionError:
                print(f"  Could not connect to {BASE_URL}. Is Book.Backend running?")
        else:
            print(f"  Unknown command '{cmd}'. Type 'help'.")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]

    try:
        if not args:
            repl()
        elif args[0] == "init":
            cmd_init()
        elif args[0] == "tools":
            cmd_tools()
        elif args[0] == "call":
            if len(args) < 2:
                sys.exit("Usage: python mcp.py call <toolName> [argsJson]")
            tool_name = args[1]
            args_json = args[2] if len(args) > 2 else "{}"
            cmd_call(tool_name, args_json)
        else:
            sys.exit(f"Unknown command '{args[0]}'. Use: init | tools | call")
    except requests.ConnectionError:
        sys.exit(f"Cannot connect to {BASE_URL}. Start Book.Backend first.")
    except requests.HTTPError as e:
        sys.exit(f"HTTP error: {e}")


if __name__ == "__main__":
    main()
