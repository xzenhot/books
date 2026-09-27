# layout.ps1
# Scaffold a novel pipeline from the canonical v1 segment-based template.
#
# Usage:
#   .\layout.ps1 -BookName <name> [-ChapterCount <n>] [-Gist <one-line premise>]
#
# Produces:
#   .space/pipeline/book_<name>/   (folder tree + state files + planning artifacts)
#   source/books/book_<name>/      (empty destination for finished chapters)
#
# The layout is static and deterministic: book -> chapters/<n> -> segments/<x>
# -> writer/editor/translator. Planning artifacts (book.json, characters.json,
# masterprompt.md, workshop_metadata.md) are seeded with placeholders that the
# writing agents fill in later.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BookName,

    [Parameter(Position = 1)]
    [int]$ChapterCount = 5,

    [Parameter(Position = 2)]
    [string]$Gist = ""
)

$ErrorActionPreference = "Stop"

# --- Resolve paths relative to this script ---------------------------------
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Framework   = Split-Path -Parent $ScriptDir            # .framework/
$RepoRoot    = Split-Path -Parent $Framework            # novelist/
$Template    = Join-Path $Framework "templates\novel"
$PipelineDir = Join-Path $RepoRoot ".space\pipeline"
$SourceDir   = Join-Path $RepoRoot "source\books"

$BookDir     = Join-Path $PipelineDir "book_$BookName"
$OutDir      = Join-Path $SourceDir   "book_$BookName"

# --- Guards -----------------------------------------------------------------
if (-not (Test-Path $Template)) {
    throw "Canonical template not found: $Template"
}
if (Test-Path $BookDir) {
    Write-Warning "Pipeline already exists: $BookDir (skipping folder creation; state files will be repaired)"
}

# --- Helpers ----------------------------------------------------------------
function New-StateFiles([string]$Path, [hashtable]$Data) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
    $returning = @{ level = $Data.level; state = "returning" }
    foreach ($k in $Data.Keys) {
        if ($k -notin @("level")) {
            $returning[$k] = $Data[$k]
        }
    }
    $returning | ConvertTo-Json | Set-Content -Path (Join-Path $Path "model.json")    -Encoding UTF8
}

function Copy-TemplateDir([string]$Src, [string]$Dst) {
    if (Test-Path $Src) {
        New-Item -ItemType Directory -Force -Path $Dst | Out-Null
        Copy-Item -Path (Join-Path $Src "*") -Destination $Dst -Recurse -Force
    }
}

# --- 1. Book root -----------------------------------------------------------
New-Item -ItemType Directory -Force -Path $BookDir | Out-Null

# Book-level state files
New-StateFiles $BookDir @{ level = "book"; book_name = $BookName; chapter_count = $ChapterCount }

# --- 2. Root planning artifacts --------------------------------------------
$now = Get-Date -Format "yyyy-MM-dd"

# book.json
$chapters = @()
for ($i = 1; $i -le $ChapterCount; $i++) {
    $chapters += @{
        chapter_index   = $i
        name            = "Chapter $i"
        chapter_title   = "Chapter $i title"
        chapter_summary = "Summary of chapter $i."
    }
}
$bookJson = [ordered]@{
    book_name        = $BookName
    book_long_title  = "Provide a long title"
    generic          = "Historical Epic"
    era              = "TBD"
    language         = "en"
    target_audience  = "general public"
    chapter_count    = $ChapterCount
    created_at       = $now
    user_name        = "novelist"
    book_summary     = if ($Gist) { $Gist } else { "Provide a one-line summary of the book." }
    gist             = if ($Gist) { $Gist } else { "Provide a one-line summary of the book." }
    epic_path        = ".space\backlog\epic\$BookName\epic.md"
    chapters         = $chapters
    all_characters   = @()
    history          = @(@{ timestamp = "$now`T00:00:00Z"; action = "Initial scaffold created"; details = "Book pipeline structure established with $ChapterCount chapters" })
}
$bookJson | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $BookDir "book.json") -Encoding UTF8

# characters.json
$charactersJson = [ordered]@{
    version          = "1.0"
    created_at       = $now
    book_name        = $BookName
    characters       = @()
    character_groups = @()
    notes            = "Character roster for '$BookName'."
}
$charactersJson | ConvertTo-Json -Depth 6 | Set-Content -Path (Join-Path $BookDir "characters.json") -Encoding UTF8

# masterprompt.md
$masterprompt = @"
# Master Prompt — $BookName

## Identity
You are a master novelist writing a frame-story novel. The book interleaves a
**modern frame** (a workshop) with a **historical narrative**.

## Central Premise
$($Gist -ne "" ? $Gist : "Provide the central premise of the book.")

## Frame
A modern workshop where characters gather to hear a story.

## Style Mandate
- Serious, descriptive, image-rich literary register.
- Weave the book's subject matter into every chapter.
- Highlight the protagonist's conflict and victory.
- Preserve the contrast between the modern frame and the historical setting.
- End each chapter with a narrative handoff that sustains curiosity.

## Section Structure
1. **Section 1 — Workshop:** the modern frame scene (kept unchanged).
2. **Section 2 — Story:** the narrated historical narrative (rewritten in the selected style).
3. **Section 3 — Discussion:** the characters' response (kept unchanged).
"@
Set-Content -Path (Join-Path $BookDir "masterprompt.md") -Value $masterprompt -Encoding UTF8

# workshop_metadata.md
$workshopMeta = @"
# Workshop Metadata — $BookName

## Workshop Team
| Role | Character | Description |
|------|-----------|-------------|
| Narrator | TBD | Guides the workshop through the story |
| Participant | TBD | A modern participant questioning the story |

## Schedule
| Chapter | Title | Focus |
|---------|-------|-------|
"@
for ($i = 1; $i -le $ChapterCount; $i++) {
    $workshopMeta += "| $i | Chapter $i | TBD |`n"
}
$workshopMeta += @"

## Grounding Notes
- Ground the narrative in accurate detail.
- Weave the book's subject matter into the story.
"@
Set-Content -Path (Join-Path $BookDir "workshop_metadata.md") -Value $workshopMeta -Encoding UTF8

# Filter folders (one per pipeline filter, ordered and prefixed)
foreach ($filterName in @("1_workshop", "2_research", "3_seeds", "4_correctness", "5_theme", "6_syntax", "7_override", "8_quality")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $BookDir "filters\$filterName") | Out-Null
}

# --- 3. Chapters and segments ----------------------------------------------
$templateMoods = Join-Path $Template "moods"
# Select one mood to copy as each chapter's mood.json (default: default.json)
$selectedMood = Join-Path $templateMoods "default.json"
if (-not (Test-Path $selectedMood)) {
    $selectedMood = Get-ChildItem -Path $templateMoods -Filter "*.json" | Select-Object -First 1 -ExpandProperty FullName
}

for ($i = 1; $i -le $ChapterCount; $i++) {
    $chapterDir = Join-Path $BookDir "chapters\$i"
    New-Item -ItemType Directory -Force -Path $chapterDir | Out-Null

    # Copy a single selected mood as mood.json (not the whole moods/ folder)
    if ($selectedMood -and (Test-Path $selectedMood)) {
        Copy-Item -Path $selectedMood -Destination (Join-Path $chapterDir "mood.json") -Force
    }

    # Chapter-level state files
    New-StateFiles $chapterDir @{ level = "chapter"; chapter_index = $i }

    # Segment 1 (canonical single segment)
    $segmentDir = Join-Path $chapterDir "segments\1"
    New-Item -ItemType Directory -Force -Path $segmentDir | Out-Null

    # writer/editor/translator agent folders
    foreach ($agent in @("writer", "editor", "translator")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $segmentDir $agent) | Out-Null
    }

    # Segment-level state files
    New-StateFiles $segmentDir @{ level = "segment"; chapter_index = $i; segment_index = 1 }
}

# --- 4. Output destination --------------------------------------------------
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# --- 5. Report --------------------------------------------------------------
Write-Host ""
Write-Host "Scaffolded book pipeline: $BookDir" -ForegroundColor Green
Write-Host "  chapters: 1..$ChapterCount (each with segments/1 -> writer/editor/translator)"
Write-Host "  planning: book.json, characters.json, masterprompt.md, workshop_metadata.md"
Write-Host "  filters:  1_workshop, 2_research, 3_seeds, 4_correctness, 5_theme, 6_syntax, 7_override, 8_quality"
Write-Host "  output:   $OutDir"
Write-Host ""
