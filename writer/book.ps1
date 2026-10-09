<#
.SYNOPSIS
PowerShell command wrapper for the /book workflow registry.

.DESCRIPTION
book.ps1 mirrors the command surface defined in .framework/workflows/book.md.
It parses the same arguments as `/book <bookname> <subcommand> ...` and forwards
each command to the appropriate Python tool under tools/. It defines no workflow
behavior of its own — it only routes, exactly like the Markdown registry.

The authoritative specs are:
  .framework/workflows/backlog.md   (bare bookname, init, backlog, layout, init idea)
  .framework/workflows/pipeline.md  (scaffold onward)
  .framework/offline_registry.md    (exact Python command shapes)

.EXAMPLE
  .\book.ps1 haveli scaffold 60 poetry
  .\book.ps1 haveli layout 60 poetry online
  .\book.ps1 haveli enrich all
  .\book.ps1 haveli write 1
  .\book.ps1 haveli publish
  .\book.ps1 -o
  .\book.ps1 --help
#>

# No param() block and no [CmdletBinding()]: this script passes its arguments
# straight through, so flags like `-o` and `--help` must not be intercepted by
# PowerShell's common-parameter binder. We read the automatic $args instead.
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = 'python'

# The raw arguments exactly as typed (preserves -o, --help, and other tokens).
$Remaining = @($args | ForEach-Object { [string]$_ })

# Backlog subcommands owned by backlog.md
$BacklogVerbs = @('init', 'backlog', 'layout')

# Pipeline subcommands owned by pipeline.md that book.py dispatches directly.
$BookPyVerbs = @('scaffold', 'enrich', 'review', 'humanize', 'write', 'publish', 'preview')

# Pipeline subcommands that are aliases of write.
$WriteAliases = @('chapter', 'story')

# Pipeline subcommands routed to a dedicated tool (not book.py's verb list).
#  - form/config -> tools/config.py
#  - add          -> tools/add_chapters.py
#  - eval         -> tools/verify_pipeline.py (read-only)
$ConfigVerbs = @('form', 'config')

# Agentic-only commands (no standalone Python CLI): filter, style, translate, poet/poetry/poem.
$AgenticVerbs = @('filter', 'style', 'translate', 'poet', 'poetry', 'poem')

# Read-only commands.
$ReadOnlyFlags = @('-o', '--options', 'list', '-h', '--help', 'help')
$EvalJudge = @('eval-judge')

function Write-Usage {
    @"
book.ps1 — PowerShell wrapper for the /book command registry.

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
  <bookname> style [<style>]
  <bookname> translate <n>|all|continue <language>
  <bookname> publish [<language>]
  <bookname> form <novel|poetry>
  <bookname> config [<key> [<value>]]
  <bookname> poet|poetry|poem

Read-only (owned by pipeline.md / eval-judge.md):
  -o | --options | list
  -h | --help
  eval-judge [--completeness] [--effectiveness] [--book <bookname>] [--all]
"@
}

function Invoke-Python {
    param([Parameter(Mandatory)][string[]]$Arguments)
    Write-Host "`n> $Python $($Arguments -join ' ')" -ForegroundColor Cyan
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

function Get-BookList {
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
if ($Remaining.Count -eq 0) {
    Write-Usage
    exit 0
}

$first = $Remaining[0]
$rest = $Remaining[1..($Remaining.Count - 1)]

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
$verbRest = $rest[1..($rest.Count - 1)]

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
            Write-Host "Filter '$filterName' runs through the filter agent (.framework/agents/filter/agent.md) — no standalone CLI." -ForegroundColor Yellow
        }
    }
    'eval' {
        # eval (read-only) -> verify_pipeline.py
        Invoke-Python @('tools/verify_pipeline.py', $bookname)
    }
    { $_ -in $AgenticVerbs } {
        $agent = $_
        Write-Host "'$agent' is agent-driven (no standalone Python CLI)." -ForegroundColor Yellow
        Write-Host "  filter    -> .framework/agents/filter/agent.md"
        Write-Host "  style     -> .framework/agents/style/agent.md"
        Write-Host "  translate -> .framework/agents/translate/agent.md"
        Write-Host "  poet      -> .framework/agents/write/agent.md (single finished poem)"
    }
    default {
        Write-Host "Unknown subcommand '$verb'." -ForegroundColor Red
        Write-Usage
        exit 1
    }
}
