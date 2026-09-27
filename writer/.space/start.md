# Default Configuration

This file is the **user-maintained default configuration**. It is read by all workflows, skills, and agents as the single source of truth for default values. Edit it here to change how the whole system behaves — do not edit `.framework/` directly.

## Workspace Map

| Folder | Role |
|--------|------|
| `.framework/` | The engine (workflows, agents, skills, rules, templates). Read-only; updated from GitHub. **Do not edit.** |
| `.space/` | The workspace. Projects live under `.space/backlog/`; working state under `.space/pipeline/`. |
| `.space/context/` | Additional materials placed here for research and reference. Updated from GitHub. |
| `source/books/` | Build output. All published, finalized work is placed here. |
| `.tools/` | Coding tools available to help you. |

---

## Default Configuration

### Book

| Key | Default | Notes |
|-----|---------|-------|
| `form` | `novel` | `novel` (prose) or `poetry` (verse). |
| `chapter_count` | `5` | Used when no count is supplied. |
| `style` / transformer | `pijush` | Resolved from `.framework/templates/styles/<style>/style.md`. |
| `syntax` | `generic` | The default (Stoic/prophetic) syntax sample. |

### Word Targets

| Form | Default target |
|------|----------------|
| Novel | `5500` words per chapter (war preset: `4500`) |
| Poetry | `500–800` words per piece |

### Default Presets

| Form | Preset |
|------|--------|
| Novel | **simple novel** preset (folded into `layout-novel/SKILL.md`) |
| Poetry | **philosophical poem** preset (folded into `layout-poetry/SKILL.md`) |

### Filter Chain

| Form | Order |
|------|-------|
| Novel | `workshop → research → seeds → correctness → theme → syntax → override → quality` |
| Poetry | `workshop → research → correctness → theme → syntax → override → quality` |

- `quality` is the final gate; nothing is promoted to `source/books/` until it passes.
- Each filter has `autorun: true` by default; set `false` to skip it in `filter *` / `filter all`.

### Override

| Key | Default |
|-----|---------|
| `override.txt` | `No transform required.` — every chapter passes through unchanged until the human writes a transformation mandate. |

### Search

| Key | Default |
|-----|---------|
| Search provider | `searxng` (override with `DEFAULT_SEARCH_PROVIDER` in `.tools/.env` or the `backend` argument) |

---

## Notes for Agents

- **Language is never assumed.** Always read `language` from `book.json` or `model.json`.
- **Defaults live here.** When a workflow, skill, or agent needs a default value, read it from this file first; fall back to `.framework/` only if it is not declared here.
- **This file is user-maintained.** You may change any default above at any time to steer the system.

