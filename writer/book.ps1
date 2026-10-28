<#
.SYNOPSIS
    PowerShell command wrapper for the /book workflow registry.

.DESCRIPTION
    book.ps1 mirrors the command surface defined in .framework/workflows/book.md.
    It parses the same arguments as `/book <bookname> <subcommand> ...` and forwards
    each command to the appropriate Python tool under tools/. It defines no workflow
    behavior of its own - it only routes, exactly like the Markdown registry.

    The command is split into two phases, matching the two workflow specs:

    Backlog creation (Phase 0-1, owned by .framework/workflows/backlog.md):
      - Bare <bookname>            create/update the backlog gist.md only
      - <bookname> init|backlog    create/update gist.md (alias of the bare form)
      - <bookname> layout          rewrite storyline.md from gist + materials,
                                   then derive book.json (the chapter plan)
      - <bookname> init idea       rewrite the gist with AI assistance

    Pipeline (Phase 2 onward, owned by .framework/workflows/pipeline.md):
      - scaffold                   build the pipeline tree from the backlog plan
      - enrich / write / review    produce and refine finished chapters
      - filter / humanize / eval   run a single filter, language cleanup, or check
      - style / translate          apply a style or produce a translation
      - publish / preview          promote to workspaces/published/ (with or
                                   without the quality gate)
      - form / config              inspect or change book-level configuration
      - add ... filter             append chapters and run one filter on them
      - poet|poetry|poem           produce a single finished poem

    Read-only commands:
      - -o | --options | list      list books across backlog/pipeline/published
      - -h | --help                show usage
      - eval-judge                 read-only framework completeness/effectiveness check

    Routing model: each subcommand belongs to a verb group that selects the Python
    entry point. No subcommand keyword is ever treated as a book name, chapter,
    filter, or prose.

    pyinstaller --onefile -w 'filename.py'

.PARAMETER bookname
    The logical book name (the first positional argument). Maps to
    workspaces/backlog/<bookname>/, workspaces/pipeline/<bookname>/, and
    workspaces/published/<bookname>/<version>/.

.PARAMETER subcommand
    The command family: init, backlog, layout, scaffold, add, filter, enrich,
    review, humanize, write, chapter, story, style, translate, publish, form,
    config, poet, poetry, poem, eval, or a read-only flag.

.INPUTS
    None. All arguments are positional strings read from the automatic $args.

.OUTPUTS
    None (this wrapper forwards to Python tools; it writes status to the host).

.EXAMPLE
    .\book.ps1 haveli scaffold 60 poetry
    Scaffold a 60-topic poetry pipeline for 'haveli'.

.EXAMPLE
    .\book.ps1 haveli layout 60 poetry online
    Regenerate the backlog layout (storyline.md + book.json) in online mode.

.EXAMPLE
    .\book.ps1 haveli enrich all
    Fuse the active filters and enrich every chapter in one pass.

.EXAMPLE
    .\book.ps1 haveli write 1
    Write a single finished chapter.

.EXAMPLE
    .\book.ps1 haveli publish
    Promote the latest writer-stage segments to a new versioned output.

.EXAMPLE
    .\book.ps1 -o
    .\book.ps1 --help
    List all books, or show this help.

.NOTES
    - The script intentionally has no param() block and no [CmdletBinding()].
      This prevents PowerShell's common-parameter binder from intercepting flags
      like -o and --help; the raw automatic $args are read instead.
    - Keep this file ASCII-only. Windows PowerShell 5.1 reads BOM-less .ps1 files
      as Windows-1252, so any non-ASCII character (e.g. an em-dash) corrupts
      string parsing. Use plain hyphens and ASCII quotes only.
    - The Python entry point is 'python' on PATH. Override $Python if needed.
    - Exit code 1 is returned when the forwarded Python command fails.

.LINK
    .framework/workflows/book.md
    .framework/workflows/backlog.md
    .framework/workflows/pipeline.md
    .framework/offline_registry.md
#>

# No param() block and no [CmdletBinding()]: this script passes its arguments
# straight through, so flags like `-o` and `--help` must not be intercepted by
# PowerShell's common-parameter binder. We read the automatic $args instead.
#
# IMPORTANT: keep this file ASCII-only. Windows PowerShell 5.1 (the default on
# Windows) reads BOM-less .ps1 files as Windows-1252. Any non-ASCII character -
# notably the em-dash (U+2014) - decodes to a stray double-quote and breaks the
# parser ("missing terminator" errors). Use ASCII hyphens and quotes only.
$ErrorActionPreference = 'Stop'
# Repo root = the directory containing this script (parent of tools/).
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# The Python interpreter used to run tools/*.py. Override to a venv path if the
# system 'python' does not have the required dependencies.
$Python = 'python'

# The raw arguments exactly as typed (preserves -o, --help, and other tokens).
# Each is cast to [string] so numeric and wildcard tokens stay verbatim.
$Remaining = @($args | ForEach-Object { [string]$_ })

# --- Verb groups ------------------------------------------------------------
# Each subcommand keyword maps to exactly one group. A group decides which
# Python tool (or which routing note) the command forwards to. The grouping
# mirrors the Command Reference in .framework/workflows/book.md.

# Backlog subcommands owned by backlog.md (Phase 0-1).
$BacklogVerbs = @('init', 'backlog', 'layout')

# Pipeline subcommands owned by pipeline.md that book.py dispatches directly.
# (book.py's argparse 'verb' choices include these.)
$BookPyVerbs = @('scaffold', 'enrich', 'review', 'humanize', 'write', 'publish', 'preview', 'cleanup')

# Pipeline subcommands that are aliases of write.
$WriteAliases = @('chapter', 'story')

# Pipeline subcommands routed to a dedicated tool (not book.py's verb list).
#  - form/config -> tools/config.py
#  - add          -> tools/add_chapters.py
#  - eval         -> tools/verify_pipeline.py (read-only)
$ConfigVerbs = @('form', 'config')

# Agentic-only commands (no standalone Python CLI): filter, style, translate,
# poet/poetry/poem, and the fixed-form poetry verbs (line, rhyme, lyrics, limerick, haiku).
$AgenticVerbs = @('filter', 'style', 'translate', 'poet', 'poetry', 'poem', 'line', 'rhyme', 'lyrics', 'limerick', 'limeric', 'haiku')

# Read-only commands.
$ReadOnlyFlags = @('-o', '--options', 'list', '-h', '--help', 'help')
$EvalJudge = @('eval-judge')

function Write-Usage {
    @"
book.ps1 - PowerShell wrapper for the /book command registry.

Usage:
  .\book.ps1 <bookname> <subcommand> [args...]
  .\book.ps1 -o | --options | list     list books across backlog, pipeline, published
  .\book.ps1 -h | --help               show this usage

Backlog (owned by backlog.md):
  <bookname> init [<gist>] [form] [refresh]
  <bookname> layout [<count>] [form] [offline|online]
  <bookname> init idea

Pipeline (owned by pipeline.md):
  <bookname> scaffold <count> [form] [offline|online]
  <bookname> add <count> filter <filter>
  <bookname> filter <filter> *|all|<n>
  <bookname> enrich <count>|range|*
  <bookname> review *|all|<n>
  <bookname> humanize *|all|<n>
  <bookname> eval all|*|<n>|<range>|continue
  <bookname> write <n>|all|continue [style <nickname>]   (aliases: chapter, story)
  <bookname> cleanup <n>|range|all|*|continue
  <bookname> style [<style>]
  <bookname> translate <n>|all|continue <language>
  <bookname> publish [<language>]
  <bookname> form <novel|poetry>
  <bookname> config [<key> [<value>]]
  <bookname> poet|poetry|poem
  <bookname> lyrics <n>|<chapter> [<target_syllables>] [replace]
  <bookname> limerick|limeric <n>|<chapter> [replace]
  <bookname> haiku <n>|<chapter> [replace]
  <bookname> line <chapter> sonnet [replace]
  <bookname> rhyme <chapter> sonnet [<scheme>] [replace]
  <bookname> workshop chapter <n|range|*> update summary|character|reference|update|expand

Read-only (owned by pipeline.md / eval-judge.md):
  -o | --options | list
  -h | --help
  eval-judge [--completeness] [--effectiveness] [--book <bookname>] [--all]
"@
}

function Invoke-Python {
    <#
    .SYNOPSIS
        Run a Python tool and fail the script on a non-zero exit code.

    .DESCRIPTION
        Echoes the resolved command (cyan), runs `python <arguments>`, then throws
        if the process exits non-zero. Because $ErrorActionPreference is 'Stop',
        a thrown error halts the wrapper, mirroring the Python tool's own failure.
    #>
    param([Parameter(Mandatory)][string[]]$Arguments)
    Write-Host "`n> $Python $($Arguments -join ' ')" -ForegroundColor Cyan
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

function Get-BookList {
    <#
    .SYNOPSIS
        List every book folder across the three workspace roots.

    .DESCRIPTION
        Scans workspaces/backlog/, workspaces/pipeline/, and workspaces/published/
        and prints each book folder name, grouped by root. This backs the read-only
        `-o` / `--options` / `list` command. It writes nothing and changes nothing.
    #>
    $roots = @(
        (Join-Path $RepoRoot 'workspaces\backlog'),
        (Join-Path $RepoRoot 'workspaces\pipeline'),
        (Join-Path $RepoRoot 'workspaces\published')
    )
    foreach ($root in $roots) {
        if (Test-Path $root) {
            Write-Host "`n== $root ==" -ForegroundColor Yellow
            Get-ChildItem $root -Directory | Sort-Object Name | ForEach-Object { Write-Host "  $($_.Name)" }
        }
    }
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------
# The remainder of this script is a single left-to-right parser:
#   first arg  -> book name (or a read-only flag / eval-judge)
#   second arg -> the subcommand verb, routed through a switch to its tool group
#   remaining  -> verb-specific arguments, forwarded verbatim to the Python tool.
# No subcommand keyword is reinterpreted as a book name, chapter, filter, or prose.
if ($Remaining.Count -eq 0) {
    Write-Usage
    exit 0
}

$first = $Remaining[0]
# Slice safely: `1..0` is `@(1,0)` in PowerShell, so a single remaining argument
# must be guarded to avoid a phantom $null (and a duplicated token) in $rest.
# Use Select-Object -Skip, which is safe for both single and multiple elements.
$rest = @($Remaining | Select-Object -Skip 1)

# Read-only flags.
if ($first -in $ReadOnlyFlags) {
    if ($first -in @('-h', '--help', 'help')) {
        Write-Usage
        exit 0
    }
    # -o | --options | list
    Get-BookList
    exit 0
}

# eval-judge (read-only, agentic).
if ($first -eq 'eval-judge') {
    Write-Host "eval-judge is a read-only agentic check (no Python CLI)." -ForegroundColor Yellow
    Write-Host "See .framework/workflows/eval-judge.md and .framework/rules/self-eval.md."
    exit 0
}

$bookname = $first
if ($rest.Count -eq 0) {
    # Bare bookname -> same as init (gist-only).
    Invoke-Python @('tools/book.py', $bookname, 'init')
    exit 0
}

$verb = $rest[0]
# Same safe slice for the verb's trailing arguments.
$verbRest = @($rest | Select-Object -Skip 1)

switch ($verb) {
    { $_ -in $BacklogVerbs } {
        # init [gist] [form] [refresh]; init idea; layout [count] [form] [offline|online]
        if ($verb -eq 'init' -and $verbRest.Count -gt 0 -and $verbRest[0] -eq 'idea') {
            Invoke-Python @('tools/book.py', $bookname, 'init', 'idea')
        }
        else {
            $pyArgs = @('tools/book.py', $bookname, $verb) + $verbRest
            Invoke-Python $pyArgs
        }
    }
    { $_ -in $BookPyVerbs } {
        # scaffold/enrich/review/humanize/write/publish/preview -> book.py
        $pyArgs = @('tools/book.py', $bookname, $verb) + $verbRest
        Invoke-Python $pyArgs
    }
    { $_ -in $WriteAliases } {
        # chapter/story are aliases of write.
        $pyArgs = @('tools/book.py', $bookname, 'write') + $verbRest
        Invoke-Python $pyArgs
    }
    { $_ -in $ConfigVerbs } {
        # form <novel|poetry> | config [key [value]]
        if ($verb -eq 'form') {
            if ($verbRest.Count -eq 0) {
                throw "form requires a value: novel or poetry"
            }
            $formValue = $verbRest[0]
            Invoke-Python @('tools/config.py', $bookname, 'book', "form=$formValue")
        }
        else {
            # config [key [value]] -> pass through to config.py
            if ($verbRest.Count -eq 0) {
                Invoke-Python @('tools/config.py', $bookname)
            }
            else {
                $pyArgs = @('tools/config.py', $bookname) + $verbRest
                Invoke-Python $pyArgs
            }
        }
    }
    'add' {
        # add <count> filter <filter> -> append chapters (add_chapters.py), then run the filter agent.
        if ($verbRest.Count -eq 0) {
            throw "add requires a chapter count: add <count> filter <filter>"
        }
        Write-Host "Appending chapters via tools/add_chapters.py" -ForegroundColor Yellow
        Invoke-Python @('tools/add_chapters.py', $bookname)
        $filterIdx = [Array]::IndexOf($verbRest, 'filter')
        if ($filterIdx -ge 0 -and $filterIdx + 1 -lt $verbRest.Count) {
            $filterName = $verbRest[$filterIdx + 1]
            Write-Host "Filter '$filterName' runs through the filter agent (.framework/agents/filter/agent.md) - no standalone CLI." -ForegroundColor Yellow
        }
    }
    'eval' {
        # eval (read-only) -> verify_pipeline.py
        Invoke-Python @('tools/verify_pipeline.py', $bookname)
    }
    'workshop' {
        # workshop chapter <n|range|*> update <verb> -> tools/expand.py
        # Syntax: <bookname> workshop chapter <scope> update summary|character|reference|update|expand
        $scope = 'all'
        $verb = 'expand'
        # Find the scope token after the literal 'chapter' keyword.
        $chapterIdx = [Array]::IndexOf($verbRest, 'chapter')
        if ($chapterIdx -ge 0 -and $chapterIdx + 1 -lt $verbRest.Count) {
            $scope = $verbRest[$chapterIdx + 1]
        }
        # Find the verb token after the literal 'update' keyword.
        $updateIdx = [Array]::IndexOf($verbRest, 'update')
        if ($updateIdx -ge 0 -and $updateIdx + 1 -lt $verbRest.Count) {
            $verb = $verbRest[$updateIdx + 1]
        }
        Invoke-Python @('tools/expand.py', $bookname, $scope, '--verb', $verb)
    }
    { $_ -in $AgenticVerbs } {
        $agent = $_
        Write-Host "'$agent' is agent-driven (no standalone Python CLI)." -ForegroundColor Yellow
        Write-Host "  filter    -> .framework/agents/filter/agent.md"
        Write-Host "  style     -> .framework/agents/style/agent.md"
        Write-Host "  translate -> .framework/agents/translate/agent.md"
        Write-Host "  poet      -> .framework/agents/write/agent.md (single finished poem)"
        switch ($agent) {
            'line'      { Write-Host "  line      -> .framework/agents/line/agent.md -> .framework/skills/sonnet/SKILL.md (calibration)" -ForegroundColor Cyan }
            'rhyme'     { Write-Host "  rhyme     -> .framework/agents/rhyme/agent.md -> .framework/skills/sonnet/SKILL.md (composition)" -ForegroundColor Cyan }
            'lyrics'     { Write-Host "  lyrics     -> .framework/agents/lyrics/agent.md -> .framework/skills/lyrics/SKILL.md" -ForegroundColor Cyan }
            'limerick'  { Write-Host "  limerick  -> .framework/agents/limerick/agent.md -> .framework/skills/limerick/SKILL.md" -ForegroundColor Cyan }
            'limeric'   { Write-Host "  limeric   -> alias of limerick" -ForegroundColor Cyan }
            'haiku'     { Write-Host "  haiku     -> .framework/agents/haiku/agent.md -> .framework/skills/haiku/SKILL.md" -ForegroundColor Cyan }
        }
    }
    default {
        Write-Host "Unknown subcommand '$verb'." -ForegroundColor Red
        Write-Usage
        exit 1
    }
}
