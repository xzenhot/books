# books

A monorepo for generating complete Bengali **books** — poetry collections and novels — with a
multi-agent literary engine. Books are planned, scaffolded, enriched, written, reviewed,
translated and published from a single command surface:

```text
/book <bookname> <command> [args...]
```

The repository holds three things: the engine (`writer/`), the live workspace where books are
planned and built (`writer/workspaces/`), and exported snapshots of finished books (`storage/`).

---

## Repository layout

| Path | Role |
|------|------|
| [writer/](writer/) | The engine: agent framework, Python tools, workspaces, entry points. See [writer/README.md](writer/README.md). |
| [writer/.framework/](writer/.framework/) | The engine proper — workflows, agents, filters, skills, rules, templates, context. |
| [writer/tools/](writer/tools/) | Python tooling: the `book.py` CLI, enrich/write/publish engines, MCP servers, search layer. |
| [writer/workspaces/](writer/workspaces/) | Live data: `backlog/` (plans), `pipeline/` (work in progress), `published/` (versioned output), `discovery/` (source material). |
| [storage/](storage/) | Exported snapshot of finished books, keyed by book name (`book.md`, `manifest.json`, `chapters/`). |
| [.pkbook/](.pkbook/) | Legacy .NET BookWriter run state (`Init.json`, `Layout.json`, `Draft.json`, `Published.json`). |

---

## The two layers

The system separates **what does the work** from **the data it works on**:

- **`.framework/`** — workflows (`backlog.md`, `pipeline.md`, `book.md`, `eval-judge.md`),
  21 role agents, 8 chain filters, 17 skills, shared rules, and templates.
- **`writer/workspaces/`** — inputs (`backlog/`, `pipeline/`) and outputs
  (`published/<book>/<version>/`).

An agent host (Claude Code, GitHub Copilot CLI, VS Code, Codex, Kiro) reads
[writer/AGENTS.md](writer/AGENTS.md) as root steering, resolves `/book` through
[writer/.framework/workflows/book.md](writer/.framework/workflows/book.md), and delegates to the two
start-point specs: `backlog.md` for Phase 0–1 and `pipeline.md` for everything after.

---

## Lifecycle

```text
/book <book> <gist>           →  backlog epic         (gist.md, storyline.md)
/book <book> init|layout      →  book plan            (book.json: chapters + filter_chain)
/book <book> scaffold         →  pipeline tree        (workspaces/pipeline/<book>/, progress.json)
/book <book> enrich           →  fuse active filters into one guidance pass
/book <book> write            →  finished chapters    (enrich → draft → transform → compose)
/book <book> review           →  quality gate
/book <book> humanize         →  target-language polish
/book <book> translate <lang> →  translator stage
/book <book> publish          →  workspaces/published/<book>/version<N>/
```

`write` (aliases `chapter`, `story`) owns the whole composition path; there is no separate
transform or compose command. Fixed forms are produced by dedicated commands: `poet`, `poyar`,
`lyrics`, `limerick`, `haiku`, `line`/`rhyme` (sonnet).

### Forms

A book is either **poetry** or **novel**, declared in its plan's `form` field.

| Signal | Poetry | Novel |
|--------|--------|-------|
| Source of truth | `book.json` `chapters[]` (topics) | `storyline.md` |
| Segments per chapter | exactly one (`segments/1`) | many |
| Word target | short verse pieces (~200–300 words) | long prose chapters (4,500–5,500 words) |
| Filter chain | `workshop → research → correctness → theme → syntax → override → quality` | `workshop → research → seeds → correctness → theme → syntax` |

### Voice and grounding

Every chapter selects a **signature** (authorial voice), a **reference** (source text), a **theme
set**, and a **syntax sample** from `.framework/context/<form>/`. Poetry ships 18 signatures
(Rabindranath, Jibanananda, Nazrul, Shakti, Sukanta, Rilke, Gibran, Hafez, Whitman, …); novels ship
22 (Bankim, Bibhutibhushan, Sarat, Manik, Tarashankar, Mahasweta, Dostoevsky, Tolstoy, Kafka,
Marquez, Woolf, …). Transformer **styles** live under `context/poetry/styles/` (`pijush`,
`pijushbangali`, `poyar`, `srijato`, `desh`, `lyrical`, …).

---

## Workspace data model

```text
writer/workspaces/
├── backlog/<book>/            gist.md · storyline.md · book.json · progress.json · override.md
├── pipeline/<book>/           book.json · progress.json · filters/filters.json · style.md · chapters/
│   └── chapters/<n>/          chapter.md · chapter.json · context.md · history/ · segments/1/
├── published/<book>/<ver>/    book.md · manifest.json · chapters/<n>/
└── discovery/<book>/          raw source material fed to research/workshop
```

`manifest.json` records each published chapter's SHA-256 and the publish timestamp. Published
versions are immutable: the next publish writes `version<N+1>` where `N` is the highest existing
number.

---

## Entry points

| Entry point | Purpose |
|-------------|---------|
| `/book …` | The agent command surface (VS Code prompts in [writer/.github/prompts/](writer/.github/prompts/), steering in [writer/AGENTS.md](writer/AGENTS.md)). |
| `writer/book.ps1` | PowerShell wrapper — routes the same command shape to the Python tools; defines no behavior of its own. |
| `python tools/book.py <book> <verb>` | Unified CLI: `init`, `backlog`, `layout`, `scaffold`, `enrich`, `filter`, `write`, `review`, `humanize`, `style`, `publish`, `preview`, `cleanup`, `poet`, `lyrics`, `limerick`, `haiku`, `line`, `rhyme`. |
| `python app.py` | Tkinter desktop front-end that lists books and streams engine output. `--list` prints books and exits. |
| `python tools/verify_pipeline.py <book>` | Verifies a scaffolded pipeline against its backlog plan; exits non-zero on contract errors. |
| `writer/pipeline.bat` | Worked example of a full poetry run (init → layout → scaffold → enrich → write → review → publish). |

### Execution modes

Each book plan carries a `factory` switch that overrides every other instruction:

- `online` (default) — the work is done **agentically by the agents/skills**; no Python is invoked.
- `offline` — the agent resolves the exact command from
  [writer/.framework/offline_registry.md](writer/.framework/offline_registry.md), displays it, and waits for
  the user's confirmation before running it.

---

## Setup

Requires Python 3.10+ (developed against 3.12) and, for the GUI, Tk. The `/book` engine itself uses
only the standard library; the optional packages cover the search layer, the FastAPI publish
service and the MCP servers:

```powershell
cd writer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then fill in provider keys
```

`.env` is the single credential location (git-ignored); every Python entry point loads it through
`tools/env.py`, and real environment variables win over the file. `python tools/env.py` shows what
was resolved.

### MCP servers

[writer/.vscode/mcp.json](writer/.vscode/mcp.json) is the single source of truth. VS Code reads it
directly; CLI clients need generated files instead, so never hand-edit those:

```powershell
python tools/mcp_sync.py          # report canonical source, targets, and drift
python tools/mcp_sync.py sync     # regenerate .mcp.json + ~/.copilot/mcp-config.json
python tools/mcp_sync.py check    # exit 1 on drift (for CI or a pre-commit hook)
```

Configured servers: `novelist-search` (SearXNG/Brave/Tavily adapter), `novelist-book` (book HTTP
API client), `novelist-facebook` (Pages publishing), `stitch` (remote HTTP), plus the host's
built-in GitHub server.

---

## Native components

Part of the toolchain is .NET, shipped prebuilt:

- **[writer/tools/mcp/](writer/tools/mcp/)** — a prebuilt .NET deployment (`Book.Backend.exe`) for
  Bengali word processing: akshar (consonant) and syllable counting, rhythmic measurement, and
  OpenXML/MagNET/Lipika document output. Its tools are reached over MCP — over HTTP
  (`POST /mcp/call/{tool}`) by `mcphttpclient.py`, or over stdio through a `kobi.exe` server
  configured in `writer/config.json` (git-ignored; the executable must be supplied locally).
  Every metrical decision in the fixed-form tools (`sonnet_utils.py`, `verse.py`,
  `_sonnet_measure.py`) goes through it.
- **[.pkbook/](.pkbook/)** — state written by the legacy .NET `BookWriter` engine
  (`Init.json`, `Layout.json`, `Draft.json`, `Published.json`, `BookPublished.html`), retained for
  reference. The current engine keeps its state under `writer/workspaces/` instead.

---

## Example: `behula`

The flagship book is an 81-poem Bengali collection (`form: poetry`, `style: pijush`,
`word_target: 280`) built through the full chain. Its live output is
[writer/workspaces/published/behula/](writer/workspaces/published/behula/) (versions 1–4, each with
an assembled `book.md`, `manifest.json` and 81 chapters), and the exported snapshot —
`book.md`, `manifest.json`, all 81 chapters — is [storage/Behula/](storage/Behula/).

---

## License

MIT — see [writer/LICENSE](writer/LICENSE). Copyright (c) 2026 Pijush Biswas.