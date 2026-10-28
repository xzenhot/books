#!/usr/bin/env python3
"""test.py — Config-driven smoke-test harness for the writer toolkit.

Tests one module at a time: app.py, mcpclient.py, book.py, etc. The harness
reads config.json to instantiate shared dependencies (e.g. the MCP client
needs the kobi server path; book.py/app.py need workspace roots), so no module
is tested in isolation with hard-coded values.

HOW TO RUN A TEST
-----------------
Put exactly ONE test name in `main()` (the `TEST` variable below), then run:

    python test.py

The TEST string selects a single entry from the TESTS registry. To test a
different module, just change that one string — nothing else.

Examples:
    TEST = "app.list-books"       # app.py: scan_books / list_books_text
    TEST = "app.book-details"     # app.py: book_details()
    TEST = "mcp.workspace-info"   # mcpclient.py: connect -> initialize -> call
    TEST = "mcp.list-tools"       # mcpclient.py: tools/list catalog
    TEST = "mcp.word-syllable"    # mcpclient.py: akshar/syllable counts
    TEST = "book.pure-functions"  # book.py: pure helpers (no network)

Exit code is 0 on success, 1 on any failure (CI-friendly).
"""

import json
import sys
from pathlib import Path

# Bengali text in tool results needs a Unicode-capable stdout; Windows consoles
# default to a legacy codepage that cannot encode Devanagari/Bengali glyphs.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Paths & config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = REPO_ROOT / "tools"
CONFIG_PATH = REPO_ROOT / "config.json"

# Make tools/ and tools/mcpbangla/ importable (book.py, notify, kamolika, ...).
MCPBANGLA_DIR = TOOLS_DIR / "mcpbangla"
for _d in (MCPBANGLA_DIR, TOOLS_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))


def load_config():
    """Load config.json (the application configuration) as a dict."""
    with CONFIG_PATH.open("r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def mcp_endpoint(config=None):
    """Return the MCP HTTP endpoint URL.

    The backend is reached over HTTP (Book.Backend). The legacy stdio
    ``mcp.server`` entry in config.json describes a `the kobi engine` executable that
    no longer ships, so it is deliberately ignored.
    """
    import kamolika

    return kamolika.BASE_URL


# ---------------------------------------------------------------------------
# Dependency factories — everything is instantiated from config.json.
# ---------------------------------------------------------------------------

def make_mcp_client(config=None):
    """Return the HTTP MCP client after completing the handshake."""
    import kamolika

    kamolika.initialize()
    return kamolika


def make_app_module(config=None):
    """Import app.py so its pure helpers (scan_books, book_details, ...) are
    callable without launching the tkinter GUI."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("writer_app", REPO_ROOT / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_book_module(config=None):
    """Import tools/book.py so its pure helpers are callable directly."""
    import book

    return book


# ---------------------------------------------------------------------------
# Assertion / output helpers
# ---------------------------------------------------------------------------

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
    print(f"  RESULT  {text if text else json.dumps(result)}")


# ---------------------------------------------------------------------------
# Tests — one function per module/concern.
# ---------------------------------------------------------------------------

def test_app_list_books(config):
    """app.py — verify book scanning / listing helpers work."""
    app = make_app_module(config)

    books = app.scan_books()
    check(isinstance(books, list), "scan_books() returns a list")

    text = app.list_books_text()
    check(isinstance(text, str) and text.strip() != "", "list_books_text() returns content")
    print(text)


def test_app_book_details(config):
    """app.py — verify book_details() resolves states/form for a known book."""
    app = make_app_module(config)
    books = app.scan_books()
    check(len(books) > 0, "at least one book exists to inspect")
    name = books[0]
    states, form, chapter_count = app.book_details(name)
    print(f"  book={name} states={states} form={form} chapters={chapter_count}")
    check(isinstance(states, list), "book_details() returns a states list")


def test_mcp_workspace_info(config):
    """mcpclient.py — full handshake + workspace.info tool call."""
    client = make_mcp_client(config)
    try:
        client.connect()
        check(client.proc.poll() is None, "process started")
        result = client.initialize()
        check(isinstance(result, dict), "initialize returned a result")
        check(client.server_info.get("name") == "kobi", "serverInfo.name == 'kobi'")

        args = {}
        result = client.call_tool("workspace.info", args)
        show_io("workspace.info", args, result)
        text = extract_text(result)
        check("machine=" in text, "workspace.info reports machine")
        check("user=" in text, "workspace.info reports user")
    finally:
        client.close()


def test_mcp_list_tools(config):
    """mcpclient.py — tools/list returns the registered tool catalog."""
    client = make_mcp_client(config)
    try:
        client.connect()
        client.initialize()
        tools = client.list_tools()
        names = {t.get("name") for t in tools}
        check(isinstance(tools, list) and len(tools) > 0, "non-empty tool list")
        for name in (
            "workspace.info", "workspace.list",
            "book.version", "book.write", "book.add-chapter",
            "chapter.write", "chapter.add-segment", "chapter.model",
            "segment.write", "segment.model",
            "word.akshar-count", "word.syllable-count", "word.syllable",
        ):
            check(name in names, f"{name} present")
    finally:
        client.close()


def test_mcp_word_syllable(config):
    """mcpclient.py — akshar (letter) vs syllable counts for Bengali words."""
    client = make_mcp_client(config)
    words = ["যমুনার", "পাড়ে", "মেঘের", "শ্রাবণ"]
    try:
        client.connect()
        client.initialize()
        for word in words:
            args = {"word": word}
            akshar = client.call_tool("word.akshar-count", args)
            syll = client.call_tool("word.syllable-count", args)
            split = client.call_tool("word.syllable", args)
            a = extract_text(akshar).strip()
            s = extract_text(syll).strip()
            sp = extract_text(split).strip()
            print(f"  {word}: akshar={a} syllable={s} split={sp}")
            check(a != "", f"{word} has an akshar count")
            check(s != "", f"{word} has a syllable count")
    finally:
        client.close()


def _tokenize_line(line):
    """Split a Bengali line into words, stripping sentence punctuation."""
    import re

    tokens = re.split(r"\s+", line.strip())
    words = []
    for t in tokens:
        # Drop leading/trailing punctuation (danda, comma, dash, etc.).
        cleaned = re.sub(r"^[।,;:!?।॥\-—–…\u0964\u0965]+|[।,;:!?।॥\-—–…\u0964\u0965]+$", "", t)
        if cleaned:
            words.append(cleaned)
    return words


def test_mcp_file_counts(config, file_path):
    """mcpclient.py — per-line letter (akshar) and syllable counts from a text file.

    Takes a text file path, reads it line by line, and for each line sums the
    akshar (letter) and syllable counts of its words using the kobi word tools.
    """
    import re

    path = Path(file_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"text file not found: {path}")

    client = make_mcp_client(config)
    try:
        client.connect()
        client.initialize()

        lines = path.read_text(encoding="utf-8-sig").splitlines()
        check(len(lines) > 0, f"file {path} has at least one line")

        for idx, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            words = _tokenize_line(line)
            line_akshar = 0
            line_syllable = 0
            per_word = []
            for word in words:
                args = {"word": word}
                a = extract_text(client.call_tool("word.akshar-count", args)).strip()
                s = extract_text(client.call_tool("word.syllable-count", args)).strip()
                try:
                    av = int(a)
                except ValueError:
                    av = 0
                try:
                    sv = int(s)
                except ValueError:
                    sv = 0
                line_akshar += av
                line_syllable += sv
                per_word.append(f"{word}({av},{sv})")

            print(f"  L{idx}: letters={line_akshar} syllables={line_syllable}  |  {' '.join(per_word)}")
            check(line_akshar > 0, f"line {idx} has a letter count")
            check(line_syllable > 0, f"line {idx} has a syllable count")
    finally:
        client.close()


def test_book_pure_functions(config):
    """book.py — exercise pure helpers that need no network/Ollama."""
    book = make_book_module(config)

    check(book.validate_bookname("cosmos") == "cosmos", "validate_bookname passes a clean name")
    check(book.resolve_form(["poetry"]) == "poetry", "resolve_form('poetry')")
    check(book.resolve_form([None], fallback="novel") == "novel", "resolve_form fallback")
    check(book.resolve_count(["20"]) == 20, "resolve_count('20') -> 20")
    check(book.resolve_count([None]) is None, "resolve_count(None) -> None")
    title = book.make_title("cosmos", "poetry")
    check(isinstance(title, str) and title != "", "make_title returns a title")
    gist = book.default_gist("cosmos", "poetry")
    check(isinstance(gist, str) and gist != "", "default_gist returns text")

    # extract_json should tolerate a fenced JSON block.
    sample = '```json\n{"form": "poetry", "chapter_count": 4}\n```'
    data = book.extract_json(sample)
    check(isinstance(data, dict) and data.get("form") == "poetry", "extract_json parses a fenced block")


# ---------------------------------------------------------------------------
# Registry — map a TEST name to a single test function.
# ---------------------------------------------------------------------------

TESTS = {
    "app.list-books": test_app_list_books,
    "app.book-details": test_app_book_details,
    "mcp.workspace-info": test_mcp_workspace_info,
    "mcp.list-tools": test_mcp_list_tools,
    "mcp.word-syllable": test_mcp_word_syllable,
    "mcp.file-counts": test_mcp_file_counts,
    "book.pure-functions": test_book_pure_functions,
}


# ---------------------------------------------------------------------------
# main — put exactly ONE test item here.
# ---------------------------------------------------------------------------

def main():
    # ========================================================================
    # EDIT THESE LINES to run one test at a time (see TESTS registry above).
    TEST = "mcp.file-counts"
    test_bengali_file = r"D:\lab\rd\music\voba\নদী ভরা ঢেউ বোঝ নাতো কেউ.txt"
    # ========================================================================

    config = load_config()
    print(f"config.json: {CONFIG_PATH}")
    print(f"server: {mcp_server_path(config)}")
    print(f"\n[{TEST}]")

    try:
        if TEST == "mcp.file-counts":
            TESTS[TEST](config, test_bengali_file)
        else:
            TESTS[TEST](config)
    except Exception as e:  # noqa: BLE001 — report any failure clearly
        print(f"  FAIL  {e}")
        return 1

    print("\n" + "=" * 40)
    print("TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
