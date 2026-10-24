#!/usr/bin/env python3
"""
mcpclient.py - Interactive MCP (Model Context Protocol) client for the kobi MCP server.

The kobi CLI exposes an MCP server over stdio (JSON-RPC 2.0, newline-delimited
messages). This client:

  1. Launches the published server executable (default: ./mcp/kobi.exe, resolved
     relative to this script) as a child process.
  2. Performs the JSON-RPC "initialize" handshake and sends "notifications/initialized".
  3. Drops into an interactive session where you can list and call tools.

The transport is stdio JSON-RPC - the transport the kobi server actually implements.
There is no gRPC dependency here.

Usage:
    python mcpclient.py                             # interactive session
    python mcpclient.py --server ./mcp/kobi.exe     # explicit server path
    python mcpclient.py --list                      # print the tool catalog and exit
    python mcpclient.py --call workspace.info '{}'  # one-shot tool call and exit

Environment:
    KOBI_MCP_SERVER   override the default server path (same as --server)
"""

import argparse
import json
import os
import subprocess
import sys


# Tool domains exposed as shortcut commands in the interactive REPL.
# `book write {}` -> calls `book.write`, `chapter model {"chapter":1}` -> `chapter.model`, etc.
DOMAINS = ("book", "chapter", "segment", "workspace")


class McpError(Exception):
    """Raised for MCP transport / protocol errors."""


def default_server_path():
    """Resolve the kobi MCP server executable.

    Prefers the path relative to this script's directory (./mcp/kobi.exe), since
    the published server lives alongside this client under tools/mcp/. Falls back
    to a working-directory-relative path.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "mcp", "kobi.exe"),
        os.path.join(os.getcwd(), "mcp", "kobi.exe"),
        os.path.join(script_dir, "mcp", "kobi"),
        os.path.join(os.getcwd(), "mcp", "kobi"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]


class McpClient:
    """A minimal stdio JSON-RPC client for the kobi MCP server."""

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(self, server_path):
        self.server_path = server_path
        self.proc = None
        self._next_id = 0
        self.server_info = None
        self.capabilities = None

    # -- lifecycle ---------------------------------------------------------

    def connect(self):
        exe = os.path.abspath(self.server_path)
        if not os.path.exists(exe):
            raise McpError(f"MCP server not found: {exe}")
        try:
            self.proc = subprocess.Popen(
                [exe, "mcp"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
        except OSError as e:
            raise McpError(f"Failed to launch MCP server '{exe}': {e}")

    def close(self):
        if self.proc is None:
            return
        if self.proc.poll() is None:
            try:
                self._send({"jsonrpc": "2.0", "method": "shutdown"})
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
        self.proc = None

    # -- transport ---------------------------------------------------------

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _recv_line(self):
        line = self.proc.stdout.readline()
        if not line:
            raise McpError("MCP server closed stdout unexpectedly (did it crash?).")
        line = line.strip()
        if not line:
            return self._recv_line()
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            raise McpError(
                "Received non-JSON output from the server. "
                "Is the published appSettings.json Environment.Run set to 'Prod'? "
                f"Raw: {line[:200]}"
            )

    def request(self, method, params=None):
        self._next_id += 1
        req_id = self._next_id
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        while True:
            resp = self._recv_line()
            if resp.get("id") == req_id:
                if "error" in resp:
                    err = resp["error"]
                    raise McpError(f"Server error {err.get('code')}: {err.get('message')}")
                return resp.get("result")

    # -- MCP methods -------------------------------------------------------

    def initialize(self):
        result = self.request(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "kobi-mcp-client", "version": "1.0"},
            },
        )
        self.server_info = result.get("serverInfo", {})
        self.capabilities = result.get("capabilities", {})
        # Acknowledge the handshake.
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return result

    def list_tools(self):
        result = self.request("tools/list")
        return result.get("tools", [])

    def call_tool(self, name, arguments=None):
        params = {"name": name, "arguments": arguments if arguments is not None else {}}
        return self.request("tools/call", params)

    def ping(self):
        return self.request("ping")


# -- output helpers ---------------------------------------------------------

def print_tools(tools):
    if not tools:
        print("  (no tools)")
        return
    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "")
        print(f"  {name}")
        if desc:
            print(f"      {desc}")


def print_tool_result(result):
    if isinstance(result, dict) and result.get("isError"):
        print("[error] ", end="")
    content = result.get("content", []) if isinstance(result, dict) else []
    if not content:
        print(json.dumps(result, indent=2))
        return
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            print(item.get("text", ""))
        else:
            print(json.dumps(item, indent=2))


def show_help():
    print(
        "Commands:\n"
        "  list                    List available tools\n"
        "  call <tool> [json]      Call a tool with optional JSON arguments\n"
        "  book <op> [json]        Call book.<op>   (e.g. book write, book version)\n"
        "  chapter <op> [json]     Call chapter.<op> (e.g. chapter model {\"chapter\":1})\n"
        "  segment <op> [json]     Call segment.<op>\n"
        "  workspace <op> [json]   Call workspace.<op> (e.g. workspace info, workspace list)\n"
        "  info                    Show server info from the initialize handshake\n"
        "  ping                    Round-trip ping to the server\n"
        "  help                    Show this help\n"
        "  exit | quit             Close the session"
    )


def parse_arguments(text):
    """Parse a JSON argument literal, tolerating an empty/missing value."""
    text = (text or "{}").strip()
    if text == "":
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid arguments JSON: {e}")


def interactive(client):
    print("kobi MCP client - interactive session")
    print("Type 'help' for commands, 'exit' to quit.")
    while True:
        try:
            raw = input("mcp> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("exit", "quit", "bye"):
            break
        elif cmd in ("help", "?"):
            show_help()
        elif cmd == "list":
            print_tools(client.list_tools())
        elif cmd == "info":
            print(json.dumps(client.server_info or {}, indent=2))
        elif cmd == "ping":
            client.ping()
            print("pong")
        elif cmd == "call":
            if len(parts) < 2:
                print("Usage: call <tool-name> [json-arguments]")
                continue
            name = parts[1]
            args_text = " ".join(parts[2:])
            try:
                arguments = parse_arguments(args_text)
                print_tool_result(client.call_tool(name, arguments))
            except (McpError, ValueError) as e:
                print(f"error: {e}")
        elif cmd in DOMAINS:
            # Shortcut: `book write {}` -> `book.write`, `chapter model {"chapter":1}` -> `chapter.model`.
            if len(parts) < 2:
                print(f"Usage: {cmd} <operation> [json-arguments]")
                continue
            tool_name = f"{cmd}.{parts[1]}"
            args_text = " ".join(parts[2:])
            try:
                arguments = parse_arguments(args_text)
                print_tool_result(client.call_tool(tool_name, arguments))
            except (McpError, ValueError) as e:
                print(f"error: {e}")
        else:
            print(f"Unknown command '{cmd}'. Type 'help'.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Interactive MCP client for the kobi MCP server (stdio JSON-RPC)."
    )
    parser.add_argument(
        "--server",
        default=None,
        help="Path to the kobi MCP server executable (default: ./mcp/kobi.exe relative to this script).",
    )
    parser.add_argument("--list", action="store_true", help="Print the tool catalog and exit.")
    parser.add_argument(
        "--call",
        nargs="+",
        metavar=("TOOL", "ARGS"),
        help="One-shot: call TOOL with optional JSON ARGS and exit.",
    )
    args = parser.parse_args(argv)

    server_path = args.server or os.environ.get("KOBI_MCP_SERVER") or default_server_path()
    client = McpClient(server_path)

    try:
        client.connect()
        client.initialize()
    except McpError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    exit_code = 0
    try:
        if args.list:
            print_tools(client.list_tools())
        elif args.call:
            name = args.call[0]
            args_text = " ".join(args.call[1:])
            try:
                print_tool_result(client.call_tool(name, parse_arguments(args_text)))
            except (McpError, ValueError) as e:
                print(f"error: {e}", file=sys.stderr)
                exit_code = 1
        else:
            interactive(client)
    finally:
        client.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
