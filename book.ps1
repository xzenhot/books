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

$script:i = 0
$script:total = 0

# Per-verb guidance: the correct way to run each step, plus a hint for the
# most common failure cause. Shown when a step fails so the user can self-correct.
$script:examples = @{
    "init"     = @{ Example = ".\book.ps1 $BookName -Verb init -Summary `"A story about hope.`""; Hint = "Init needs the book to exist. Try: .\book.ps1 $BookName (full pipeline)." }
    "layout"   = @{ Example = ".\book.ps1 $BookName -Verb layout -ChapterCount 20"; Hint = "Layout needs a gist. Run init first: .\book.ps1 $BookName -Verb init." }
    "scaffold" = @{ Example = ".\book.ps1 $BookName -Verb scaffold -ChapterCount 20"; Hint = "Scaffold needs init+layout first and a matching chapter count." }
    "enrich"   = @{ Example = ".\book.ps1 $BookName -Verb enrich"; Hint = "Enrich needs a scaffolded pipeline. Run scaffold first." }
    "write"    = @{ Example = ".\book.ps1 $BookName -Verb write"; Hint = "Write needs enriched chapters. Run enrich first." }
    "review"   = @{ Example = ".\book.ps1 $BookName -Verb review"; Hint = "Review needs written chapters. Run write first." }
    "publish"  = @{ Example = ".\book.ps1 $BookName -Verb publish"; Hint = "Publish needs reviewed chapters that passed quality." }
    "preview"  = @{ Example = ".\book.ps1 $BookName -Verb preview"; Hint = "Preview needs written chapters (no quality gate)." }
}

# Run a single step: book.py <bookname> <verb> [args...]
function Invoke-Step {
    param(
        [string]$VerbName,
        [string[]]$Args = @()
    )
    $script:i++
    Write-Host "[$script:i/$script:total] Running '$VerbName'..."

    # Capture the actual command for the error report.
    if ($Args.Count -eq 0) {
        $script:lastCommand = "python writer\.tools\book.py `"$BookName`" $VerbName"
        python $bookPy $BookName $VerbName
    } else {
        $script:lastCommand = "python writer\.tools\book.py `"$BookName`" $VerbName " + ($Args -join " ")
        python $bookPy $BookName $VerbName @Args
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Step '$VerbName' failed (exit code $LASTEXITCODE)." -ForegroundColor Red
        Write-Host "Command tried:" -ForegroundColor Yellow
        Write-Host "  $script:lastCommand"
        Write-Host ""
        Write-Host "Correct usage for this step:" -ForegroundColor Green
        Write-Host "  $($script:examples[$VerbName].Example)"
        Write-Host ""
        Write-Host "Hint: $($script:examples[$VerbName].Hint)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Full pipeline example: .\book.ps1 $BookName -ChapterCount 20 -Summary `"A story about hope.`""
        exit $LASTEXITCODE
    }
}

# Resolve the requested verb into one or more steps.
$verb = $Verb.ToLowerInvariant()
switch ($verb) {
    "all"      { $script:total = 8 }
    "init"     { $script:total = 1 }
    "layout"   { $script:total = 1 }
    "scaffold" { $script:total = 1 }
    "enrich"   { $script:total = 1 }
    "write"    { $script:total = 1 }
    "review"   { $script:total = 1 }
    "publish"  { $script:total = 1 }
    "preview"  { $script:total = 1 }
    default {
        Write-Host "Unknown verb '$Verb'. Valid: all, init, layout, scaffold, enrich, write, review, publish, preview."
        exit 1
    }
}

switch ($verb) {
    "all" {
        Invoke-Step "init"     @($Summary, "poetry")
        Invoke-Step "layout"   @("$ChapterCount")
        Invoke-Step "scaffold" @("$ChapterCount", "poetry")
        Invoke-Step "enrich"   @("all")
        Invoke-Step "write"    @("all")
        Invoke-Step "review"   @("all")
        Invoke-Step "publish"  @()
        Invoke-Step "preview"  @()
    }
    "init"     { Invoke-Step "init"     @($Summary, "poetry") }
    "layout"   { Invoke-Step "layout"   @("$ChapterCount") }
    "scaffold" { Invoke-Step "scaffold" @("$ChapterCount", "poetry") }
    "enrich"   { Invoke-Step "enrich"   @("all") }
    "write"    { Invoke-Step "write"    @("all") }
    "review"   { Invoke-Step "review"   @("all") }
    "publish"  { Invoke-Step "publish"  @() }
    "preview"  { Invoke-Step "preview"  @() }
}

Write-Host ""
Write-Host "Done!"