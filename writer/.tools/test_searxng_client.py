#!/usr/bin/env python3
"""Minimal MCP client test for the novelist search server."""

import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO_ROOT, ".tools", "server.py")


def send(proc, obj):
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def readline(proc, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if line:
            return line.strip()
        time.sleep(0.05)
    raise TimeoutError("No response from server")


def main():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, SERVER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    try:
        print("[1] Sending initialize...")
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "0.1.0"},
                },
            },
        )
        print("INIT RESP:", readline(proc))

        print("[2] Sending notifications/initialized...")
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        print("[3] Sending tools/list...")
        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_line = readline(proc)
        print("TOOLS RESP:", tools_line)
        tools = json.loads(tools_line)
        tool_names = [t["name"] for t in tools.get("result", {}).get("tools", [])]
        print("Tool names:", tool_names)
        assert "search" in tool_names, "search tool not found"

        print("[4] Calling search with default provider...")
        send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "search",
                    "arguments": {
                        "query": "Bengal famine 1943",
                        "max_results": 3,
                    },
                },
            },
        )
        search_line = readline(proc, timeout=60)
        print("SEARCH RESP:", search_line)
        search_result = json.loads(search_line)
        content = search_result["result"]["content"][0]["text"]
        payload = json.loads(content)
        print("Pretty search payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        assert payload["query"] == "Bengal famine 1943"
        assert payload["total"] == len(payload["results"])
        for r in payload["results"]:
            assert "title" in r and "url" in r and "snippet" in r

        print("\nAll checks passed.")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
