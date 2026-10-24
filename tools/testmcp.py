#!/usr/bin/env python3
"""
testmcp.py - Automated smoke tests for the kobi MCP client (mcpclient.py).

Exercises the full lifecycle against the published server:
    connect -> initialize -> tools/list -> tools/call -> ping -> close

Run from the tools/ directory (or anywhere; the server path is auto-resolved):

    python testmcp.py              # run all tests
    python testmcp.py --server C:/path/to/kobi.exe

Exit code is 0 on success, 1 on any failure (CI-friendly).
"""

import argparse
import json
import os
import sys

from mcpclient import McpClient, McpError, default_server_path


def check(cond, label):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}")
        raise AssertionError(label)


def extract_text(result):
    """Pull the concatenated text payload out of a tools/call result."""
    text = ""
    for item in result.get("content", []):
        if item.get("type") == "text":
            text += item.get("text", "")
    return text


def show_io(name, arguments, result):
    """Print both the tool invocation (input) and the returned result (output)."""
    print(f"  INPUT   {name} {json.dumps(arguments)}")
    text = extract_text(result)
    if text:
        print(f"  RESULT  {text}")
    else:
        print(f"  RESULT  {json.dumps(result)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Smoke-test the kobi MCP client.")
    parser.add_argument("--server", default=None, help="Path to the kobi MCP server executable.")
    args = parser.parse_args(argv)

    server_path = args.server or os.environ.get("KOBI_MCP_SERVER") or default_server_path()
    print(f"Server: {server_path}")

    client = McpClient(server_path)
    failures = 0

    def run(name, fn):
        nonlocal failures
        print(f"\n[{name}]")
        try:
            fn()
        except (McpError, AssertionError, KeyError, TypeError) as e:
            failures += 1
            print(f"  FAIL  {e}")

    # 1. Server file exists
    run("server exists", lambda: check(os.path.exists(server_path), "server executable present"))

    # 2. Connect + initialize handshake
    def connect_and_init():
        client.connect()
        check(client.proc.poll() is None, "process started")
        result = client.initialize()
        check(isinstance(result, dict), "initialize returned a result")
        check(client.server_info.get("name") == "kobi", "serverInfo.name == 'kobi'")
    run("connect + initialize", connect_and_init)

    # 3. tools/list
    def list_tools():
        tools = client.list_tools()
        names = {t.get("name") for t in tools}
        check(isinstance(tools, list) and len(tools) > 0, "non-empty tool list")
        check("workspace.info" in names, "workspace.info present")
        check("workspace.list" in names, "workspace.list present")
        # New book/chapter/segment tools must be registered.
        for name in (
            "book.version", "book.write", "book.add-chapter",
            "chapter.write", "chapter.add-segment", "chapter.model",
            "segment.write", "segment.model",
        ):
            check(name in names, f"{name} present")
    run("tools/list", list_tools)

    # 4. tools/call workspace.info
    def call_info():
        args = {}
        result = client.call_tool("workspace.info", args)
        show_io("workspace.info", args, result)
        text = extract_text(result)
        check("machine=" in text, "workspace.info reports machine")
        check("user=" in text, "workspace.info reports user")
        check("os=" in text, "workspace.info reports os")
    run("tools/call workspace.info", call_info)

    # 5. tools/call workspace.list
    def call_list():
        args = {}
        result = client.call_tool("workspace.list", args)
        show_io("workspace.list", args, result)
        text = extract_text(result)
        check(text.strip() != "", "workspace.list returned content")
    run("tools/call workspace.list", call_list)

    # 5b. tools/call book.version (read-only, exercises the book tool domain)
    def call_book_version():
        args = {}
        result = client.call_tool("book.version", args)
        show_io("book.version", args, result)
        text = extract_text(result)
        check(text.strip() != "", "book.version returned content")
    run("tools/call book.version", call_book_version)

    # 6. ping
    def do_ping():
        client.ping()
        check(True, "ping round-trip (no exception)")
    run("ping", do_ping)

    # 7. close
    def do_close():
        client.close()
        check(client.proc is None or client.proc.poll() is not None, "process shut down")
    run("close", do_close)

    print("\n" + ("=" * 40))
    if failures == 0:
        print("ALL TESTS PASSED")
        return 0
    print(f"{failures} TEST(S) FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())