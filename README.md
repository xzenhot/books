# books

A multi-agent literary engine for writing **poetry** and **novels** in a configured authorial voice.

The `writer/` directory contains the complete engine — the agents, skills, templates, and data layout that turn a seed idea into finished, versioned books. This repository is the working workspace that hosts that engine plus its output.

## What it does

- **Creates a backlog** from a seed gist — `gist.md`, `storyline.md`, and a chapter-layout `book.json` plan.
- **Scaffolds a pipeline** — the per-book working state where chapters are drafted and refined.
- **Runs a filter chain** (workshop → research → correctness → theme → syntax → … → quality) to ground, style, and validate each chapter.
- **Writes finished chapters** and promotes them to versioned output under `source/books/<book>/<version>/`.

The primary command surface is a single slash command, `/book <bookname> ...`.

## Quick start

```text
/book behula "Bengali mythology of Behula..."   # create the backlog epic
/book behula init poetry                        # configure the book plan
/book behula scaffold                           # build the pipeline
/book behula enrich                             # fuse active filters into one pass
/book behula write                              # write finished chapters
/book behula publish                            # promote to source/books
```

## Workflow commands

The full `/book <bookname> ...` command surface, grouped by phase.

### Backlog (Phase 0–1)

```text
/book <bookname> [<gist>] [form] [refresh]          # create/update the backlog epic + seed gist
/book <bookname> init|backlog [<gist>] [<count>] [form] [refresh]   # configure the book plan
/book <bookname> init idea                           # rewrite the gist with AI
/book <bookname> layout [<count>] [form]             # rewrite storyline.md from gist + materials, then derive book.json
```

### Pipeline (Phase 2 onward)

```text
/book <bookname> scaffold <gist> count|chapter-count <n> [--form novel|poetry]  # build the pipeline tree
/book <bookname> add <chapter-count> filter <filter>   # add chapters + run one filter
/book <bookname> <agentname> <chapter>|<n>|all|continue # run a registered agent
/book <bookname> filter <filter>                       # run a single filter
/book <bookname> enrich <count>|range|*                # fuse active filters into one pass
/book <bookname> review *|all|<n>                      # quality gate (must pass before publish)
/book <bookname> humanize *|all|<n>                    # enforce target language only
/book <bookname> eval all|*|<n>|<range>|continue       # read-only completeness check
/book <bookname> write <n>|all|continue [<style>]      # write finished chapters (default style: pijush)
/book <bookname> style [<style>]                       # transform writer-stage chapters
/book <bookname> translate <n>|all|continue <language> # translate latest writer-stage chapters
/book <bookname> publish [<language>]                  # promote segments to source/books + assemble book.md
/book <bookname> form <novel|poetry>                   # set/change the book's form
/book <bookname> config [<key> [<value>]]              # get/set book config
/book <bookname> poet|poetry|poem                      # produce a single finished poem
```

### Read-only

```text
/book -o | --options | list                           # list books and chapters
/book -h | --help                                     # show usage
```

### Forms and filter chain

A book is either **poetry** (verse) or **novel** (prose), declared in the `form` field.

- **Poetry filter chain:** `workshop → research → correctness → theme → syntax → override → quality`
- **Novel filter chain:** `workshop → research → seeds → correctness → theme → syntax`

Batch helpers live at the repository root:

- `book.bat` — end-to-end run via `writer\.tools\book.py` (`init → layout → write → publish`).

```text
book.bat BOOK_NAME [CHAPTER_COUNT] [summary]
```

Example:

```text
book.bat MyNovel 20 "A story about hope."
```

Steps it runs:

```text
python writer\.tools\book.py "%BOOK_NAME%" init "%summary%" poetry
python writer\.tools\book.py "%BOOK_NAME%" layout %CHAPTER_COUNT%
python writer\.tools\book.py "%BOOK_NAME%" write all
python writer\.tools\book.py "%BOOK_NAME%" publish
```

- `write.bat` — legacy runner targeting `writer\kobi.exe`.

## Details

For the full architecture, command reference, forms, filter chain, role agents, skills, and data layout, see **[`writer/README.md`](writer/README.md)**.

For the runtime steering contract that autonomous coding agents follow, see **[`writer/AGENTS.md`](writer/AGENTS.md)**.
