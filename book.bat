@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
	echo Usage: book.bat BOOK_NAME [VERB] [CHAPTER_COUNT] [summary]
	echo.
	echo How to invoke:
	echo   book.bat MyNovel                                      # full pipeline (all 8 steps)
	echo   book.bat MyNovel write                                # run only the 'write' step
	echo   book.bat MyNovel all 20 "A story about hope."
	echo   book.bat MyNovel publish
	echo.
	echo Arguments:
	echo   BOOK_NAME      Required. Book identifier (folder name under .space/backlog/).
	echo   VERB           Optional. Single step to run (default: all).
	echo                  One of: all, init, layout, scaffold, enrich, write, review, publish, preview.
	echo   CHAPTER_COUNT  Optional. Number of chapters (default: 2).
	echo   summary        Optional. Seed idea for the book (default: a generic story).
	echo.
	echo Steps (run with VERB=all, the default):
	echo   1. Init        -^> book.py init ^<summary^> poetry
	echo   2. Layout      -^> book.py layout ^<count^>
	echo   3. Scaffold    -^> book.py scaffold ^<count^> poetry
	echo   4. Enrich      -^> book.py enrich all
	echo   5. Write       -^> book.py write all
	echo   6. Review      -^> book.py review all
	echo   7. Publish     -^> book.py publish
	echo   8. Preview     -^> book.py preview
	exit /b 1
)

set "BOOK_NAME=%~1"
set "VERB=%~2"
set "CHAPTER_COUNT=%~3"
set "summary=%~4"

if "%VERB%"=="" set VERB=all
if "%CHAPTER_COUNT%"=="" set CHAPTER_COUNT=2
if "%summary%"=="" set summary=A story about a mysterious journey.

rem Determine step count based on verb
set "TOTAL=1"
if /I "%VERB%"=="all" set TOTAL=8

set "i=0"
if /I "%VERB%"=="all"     call :run init     "%summary%" poetry
if /I "%VERB%"=="all"     call :run layout   "%CHAPTER_COUNT%"
if /I "%VERB%"=="all"     call :run scaffold "%CHAPTER_COUNT%" poetry
if /I "%VERB%"=="all"     call :run enrich   all
if /I "%VERB%"=="all"     call :run write    all
if /I "%VERB%"=="all"     call :run review   all
if /I "%VERB%"=="all"     call :run publish
if /I "%VERB%"=="all"     call :run preview
if /I "%VERB%"=="init"     call :run init     "%summary%" poetry
if /I "%VERB%"=="layout"   call :run layout   "%CHAPTER_COUNT%"
if /I "%VERB%"=="scaffold" call :run scaffold "%CHAPTER_COUNT%" poetry
if /I "%VERB%"=="enrich"   call :run enrich   all
if /I "%VERB%"=="write"    call :run write    all
if /I "%VERB%"=="review"   call :run review   all
if /I "%VERB%"=="publish"  call :run publish
if /I "%VERB%"=="preview"  call :run preview

if not defined VERB_MATCHED (
	echo Unknown verb '%VERB%'. Valid: all, init, layout, scaffold, enrich, write, review, publish, preview.
	exit /b 1
)

echo.
echo Done!
exit /b 0

:run
set "VERB_MATCHED=1"
set /a i+=1
set "verbName=%~1"
shift
set "argline="
:buildargs
if not "%~1"=="" (
	set "argline=!argline! %~1"
	shift
	goto buildargs
)
echo [!i!/%TOTAL%] Running '!verbName!'...
python writer\.tools\book.py "%BOOK_NAME%" !verbName!!argline!
if errorlevel 1 (
	echo Step '!verbName!' failed with exit code !errorlevel!. Aborting.
	exit /b !errorlevel!
)
exit /b 0