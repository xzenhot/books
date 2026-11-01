# Offline Command Registry

The authoritative index of the repository's offline (Python CLI) commands. This
is the reference an agent consults in `offline` mode to resolve the **exact**
command to display to the user before asking for confirmation to run it.

All commands run from the repository root (`d:\lab\github\books\writer`).

---

## Primary CLI — `tools/book.py`

The unified entrypoint. Most structural commands route through it.

```text
python tools/book.py <bookname> <verb> [options...]
```

| Verb | Purpose | Command shape |
|------|---------|---------------|
| `init` | Create backlog artifacts (gist.md, storyline.md, book.json), then layout via Ollama | `python tools/book.py <bookname> init ["seed text"] [novel\|poetry]` |
| `init idea` | Rewrite the gist with AI | `python tools/book.py <bookname> init idea` |
| `build` | Alias for `init` with an optional leading chapter count | `python tools/book.py <bookname> build 20 novel` |
| `layout` | Regenerate book.json from storyline.md (does not touch gist/storyline) | `python tools/book.py <bookname> layout [novel\|poetry]` |
| `scaffold` | Build pipeline folder structure, stage the style signature and bookseed vocabulary, and copy them into the pipeline | `python tools/book.py <bookname> scaffold [count] [novel\|poetry]` |
| `enrich` | Run enrich engine on selected chapters | `python tools/book.py <bookname> enrich [all\|1\|1-5\|continue]` |
| `write` | Run chapter writer on selected chapters | `python tools/book.py <bookname> write [all\|1\|1-5\|continue]` |
| `publish` | Promote pipeline segments to workspaces/published/ | `python tools/book.py <bookname> publish` |
| `preview` | Same as publish but skips quality gate/review (publish --draft) | `python tools/book.py <bookname> preview` |

Common flags: `-t/--type poetry|novel` (form override, default poetry),
`-r/--refresh` (overwrite gist.md on init), `--gist "text"` (explicit seed text),
`--layout`, `--draft`.

---

## Dedicated engine tools

Each is runnable standalone (the `book.py` dispatcher wraps several of these).

| Tool | Purpose | Command shape |
|------|---------|---------------|
| `tools/scaffold.py` | Create/resume/extend a **poetry** pipeline (append-only, no overwrite); reconciles a novel-preset `filter_chain` and stages/copies the style signature and `bookseed.txt` | `python tools/scaffold.py <bookname>` |
| `tools/enrich.py` | Enrich chapter models with variety-driven planning tags | `python tools/enrich.py <bookname> <number\|range\|list\|all\|*>` |
| `tools/write.py` | Write chapter drafts via Ollama from flattened context | `python tools/write.py <bookname> <n\|range\|list\|all\|"*">` |
| `tools/workplan.py` | Shared plan-of-works banner for enrich/write (model, book, count, range, ETA) | imported by `enrich.py` / `write.py`; not run directly |
| `tools/publish.py` | Publish a validated collection from chapter-root drafts | `python tools/publish.py <bookname>` |
| `tools/review.py` | Quality review engine (audits against seed quality parameters) | `python tools/review.py <bookname> [all\|*\|<n>\|<range>\|continue]` |
| `tools/humanize.py` | Polish chapter drafts to target language only | `python tools/humanize.py <bookname> [all\|*\|<n>\|<range>\|continue]` |
| `tools/syntax_filter.py` | Apply the syntax filter (records syntax sample into chapter models) | `python tools/syntax_filter.py <bookname> [all\|1\|1-5\|continue]` |
| `tools/flatten.py` | Flatten a chapter model.json into context.md | `python tools/flatten.py <bookname> <n>` |
| `tools/add_chapters.py` | Append new chapters to a poetry book (inline NEW_CHAPTERS list) | `python tools/add_chapters.py <bookname>` |
| `tools/verify_pipeline.py` | Verify scaffolded pipeline against its backlog book plan | `python tools/verify_pipeline.py <bookname>` |
| `tools/layout.py` | Scaffold a **novel** pipeline from the v1 segment template (PowerShell-free) | `python tools/layout.py <bookname> [--chapter-count N] [--gist "premise"]` |

---

## Search / MCP tools

| Tool | Purpose | Command shape |
|------|---------|---------------|
| `tools/search/cli.py` | Web search via a configured provider adapter | `python tools/search/cli.py "query" [--backend searxng] [--max 5] [--engines wikipedia]` |
| `tools/server.py` | MCP server exposing a `search` tool (SearXNG default) | `python tools/server.py` |
| `tools/book_server.py` | MCP server exposing the Novelist book/publish API | `python tools/book_server.py` |
| `tools/mcpbangla/mcpfacebook/facebook.py` | MCP server exposing Facebook Page publishing/insights/comments | `python tools/mcpbangla/mcpfacebook/facebook.py` |
| `tools/mcp_sync.py` | Regenerate/verify every MCP client config from `.vscode/mcp.json` | `python tools/mcp_sync.py [status\|sync\|check]` |
| `tools/friends_export.py` | List friends from a Facebook data export (no API exists) | `python tools/friends_export.py <export-folder-or-zip> [--format md\|json] [--search TEXT]` |

**`.vscode/mcp.json` is the only MCP configuration in this repository.** Never
add server definitions to `.mcp.json`, `.github/mcp.json`,
`~/.copilot/mcp-config.json`, or the `chat.mcp.servers` user setting by hand.
Edit `.vscode/mcp.json`, then run `python tools/mcp_sync.py sync`; CI and
pre-commit run `python tools/mcp_sync.py check`, which exits non-zero on drift.
Secrets are never stored in any of these files — use `${input:...}` prompts in
`.vscode/mcp.json` and `.env` for the servers themselves.

---

## PowerShell

| Tool | Purpose | Command shape |
|------|---------|---------------|
| `tools/layout.ps1` | Scaffold a **novel** pipeline (PowerShell equivalent of layout.py) | `.\tools\layout.ps1 -BookName <name> [-ChapterCount N] [-Gist "premise"]` |

---

## Utility / diagnostic

| Tool | Purpose | Command shape |
|------|---------|---------------|
| `tools/quality.py` | Shared library (draft identity, atomic metadata, publish eligibility) — not run directly | — |
| `tools/check_publish.py` | One-off diagnostic: compare chapter.md hash vs quality_review hash | `python tools/check_publish.py` |
| `tools/book-test.py` | Unit tests for book.py helpers | `python -m unittest tools.book-test -v` |
