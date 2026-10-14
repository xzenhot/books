@echo off
rem ===========================================================================
rem  backlog.bat — backlog-creation workflow for a /book book.
rem
rem  This file shows the canonical command sequence for the backlog phase
rem  only (Phase 0-1 per .framework/workflows/backlog.md). Each step is the
rem  /book command (or its Python CLI equivalent), in order.
rem
rem  EXAMPLE (the "haveli" book, 60 poems):
rem
rem    /book haveli init                      -> backlog: gist.md (seed idea)
rem    /book haveli layout 60 poetry          -> backlog: storyline.md + book.json
rem
rem  The same commands as the PowerShell wrapper:
rem
rem    .\book.ps1 haveli init
rem    .\book.ps1 haveli layout 60 poetry
rem
rem  For Phase 2 onward (scaffold, enrich, write, review, publish),
rem  see pipeline.bat.
rem
rem  Usage:  backlog.bat <bookname> <count> <form> ["gist"]
rem          e.g.   backlog.bat haveli 60 poetry
rem ===========================================================================

rem Force UTF-8 so Python prints do not crash under
rem the Windows cp1252 console codec.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if "%~1"=="" (
    echo Usage: backlog.bat ^<bookname^> ^<count^> ^<form^> ["gist"]
    echo Example: backlog.bat haveli 60 poetry "one-line premise"
    exit /b 1
)

set BOOK=%~1
set COUNT=%~2
set FORM=%~3
set GIST=%~4

if "%COUNT%"=="" set COUNT=60
if "%FORM%"==""  set FORM=poetry

echo.
echo === 0. init  (gist.md seed idea) ===
python tools/book.py %BOOK% init "%GIST%"

echo.
echo === 1. layout  (storyline.md + book.json) ===
python tools/book.py %BOOK% layout %COUNT% %FORM%

echo.
echo Backlog complete for "%BOOK%". See pipeline.bat for scaffold onward.





