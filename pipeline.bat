@echo off
rem ===========================================================================
rem  pipeline.bat — example end-to-end /book workflow for a poetry book.
rem
rem  This file shows the canonical command sequence for taking a book from
rem  backlog creation through to published output. Each step is the /book
rem  command (or its Python CLI equivalent), in order.
rem
rem  EXAMPLE (the "haveli" book, 60 poems):
rem
rem    /book haveli init                      -> backlog: gist.md (seed idea)
rem    /book haveli layout 60 poetry          -> backlog: storyline.md + book.json
rem    /book haveli scaffold 60 poetry        -> pipeline tree + progress.json
rem    /book haveli enrich *                  -> fuse filters into one pass
rem    /book haveli write all                 -> write every poem
rem    /book haveli review *                  -> quality gate
rem    /book haveli publish                   -> workspaces/published/haveli/versionN/
rem
rem  The same commands as the PowerShell wrapper:
rem
rem    .\book.ps1 haveli init
rem    .\book.ps1 haveli layout 60 poetry
rem    .\book.ps1 haveli scaffold 60 poetry
rem    .\book.ps1 haveli enrich all
rem    .\book.ps1 haveli write all
rem    .\book.ps1 haveli review all
rem    .\book.ps1 haveli publish
rem
rem  Usage:  pipeline.bat <bookname> <form> <count>
rem          e.g.   pipeline.bat matima poetry 5
rem ===========================================================================

rem Force UTF-8 so Python prints (→, Bengali text, etc.) do not crash under
rem the Windows cp1252 console codec.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if "%~1"=="" (
    echo Usage: pipeline.bat ^<bookname^> ^<form^> ^<count^>
    echo Example: pipeline.bat matima poetry 5
    exit /b 1
)

set BOOK=%~1
set FORM=%~2
set COUNT=%~3


if "%COUNT%"=="" set COUNT=60
if "%FORM%"==""  set FORM=poetry

echo.
echo Book   : %BOOK%
echo Form   : %FORM%
echo Count  : %COUNT%


echo.
echo === 1. layout  (storyline.md + book.json) ===
rem python tools/book.py %BOOK% layout %COUNT% %FORM%

echo.
echo === 2. scaffold  (pipeline tree + progress.json) ===
python tools/book.py %BOOK% scaffold %COUNT% %FORM%

echo.
echo === 3. config  (per-chapter word target) ===
python tools/config.py %BOOK% chapter all word_target=110

echo.
echo === 4. enrich  (fuse active filters) ===
python tools/book.py %BOOK% enrich all

echo.
echo === 5. write  (compose chapters) ===
python tools/book.py %BOOK% write all

echo.
echo === 6. review  (quality gate) ===
python tools/book.py %BOOK% review all

echo.
echo === 7. publish  (promote to workspaces/published) ===
python tools/book.py %BOOK% publish

echo.
echo Pipeline complete for "%BOOK%".




