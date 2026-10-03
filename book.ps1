param(
    [string]$BookName,
    [string]$Verb = "all",
    [int]$ChapterCount = 0,
    [string]$Summary = ""
)

if (-not $BookName) {
    Write-Host "Usage: book.ps1 BOOK_NAME [-Verb <verb>] [-ChapterCount <n>] [-Summary `"text`"]"
    Write-Host ""
    Write-Host "How to invoke:"
    Write-Host "  .\book.ps1 MyNovel                                      # full pipeline (all 8 steps)"
    Write-Host "  .\book.ps1 MyNovel -Verb write                          # run only the 'write' step"
    Write-Host "  .\book.ps1 MyNovel -ChapterCount 20 -Summary `"A story about hope.`""
    Write-Host "  pwsh -File book.ps1 MyNovel -Verb publish"
    Write-Host ""
    Write-Host "Arguments:"
    Write-Host "  BOOK_NAME      Required. Book identifier (folder name under .space/backlog/)."
    Write-Host "  -Verb          Optional. Single step to run (default: all)."
    Write-Host "                 One of: all, init, layout, scaffold, enrich, write, review, publish, preview."
    Write-Host "  -ChapterCount  Optional. Number of chapters (default: 2)."
    Write-Host "  -Summary       Optional. Seed idea for the book (default: a generic story)."
    Write-Host ""
    Write-Host "Steps (run with -Verb all, the default):"
    Write-Host "  1. Init        -> book.py init <summary> poetry"
    Write-Host "  2. Layout      -> book.py layout <count>"
    Write-Host "  3. Scaffold    -> book.py scaffold <count> poetry"
    Write-Host "  4. Enrich      -> book.py enrich all"
    Write-Host "  5. Write       -> book.py write all"
    Write-Host "  6. Review      -> book.py review all"
    Write-Host "  7. Publish     -> book.py publish"
    Write-Host "  8. Preview     -> book.py preview"
    exit 1
}

if ($ChapterCount -le 0) { $ChapterCount = 2 }
if (-not $Summary) { $Summary = "A story about a mysterious journey." }

$bookPy = Join-Path $PSScriptRoot "writer\.tools\book.py"

# Resolve the requested verb into one or more (verb, args) steps.
$verb = $Verb.ToLowerInvariant()
switch ($verb) {
    "all" {
        $steps = @(
            @("init",     $Summary, "poetry"),
            @("layout",   "$ChapterCount"),
            @("scaffold", "$ChapterCount", "poetry"),
            @("enrich",   "all"),
            @("write",    "all"),
            @("review",   "all"),
            @("publish",  ""),
            @("preview",  "")
        )
    }
    "init"     { $steps = @(@("init",     $Summary, "poetry")) }
    "layout"   { $steps = @(@("layout",   "$ChapterCount")) }
    "scaffold" { $steps = @(@("scaffold", "$ChapterCount", "poetry")) }
    "enrich"   { $steps = @(@("enrich",   "all")) }
    "write"    { $steps = @(@("write",    "all")) }
    "review"   { $steps = @(@("review",   "all")) }
    "publish"  { $steps = @(@("publish",  "")) }
    "preview"  { $steps = @(@("preview",  "")) }
    default {
        Write-Host "Unknown verb '$Verb'. Valid: all, init, layout, scaffold, enrich, write, review, publish, preview."
        exit 1
    }
}

$i = 0
$total = $steps.Count
foreach ($step in $steps) {
    $i++
    $verbName = $step[0]
    $args = @($step[1..($step.Count - 1)] | Where-Object { $_ -ne "" })

    Write-Host "[$i/$total] Running '$verbName'..."
    if ($args.Count -eq 0) {
        python $bookPy $BookName $verbName
    } else {
        python $bookPy $BookName $verbName @args
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Step '$verbName' failed with exit code $LASTEXITCODE. Aborting."
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "Done!"