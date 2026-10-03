@echo off
if "%~1"=="" (
	echo Usage: write.bat BOOK_NAME [CHAPTER_COUNT] [summary]
	echo Example: write.bat MyNovel 20 "A story about hope."
	echo.
	echo Steps:
	echo   1. Initialize:   write.bat MyNovel 10 "A story about hope."
	echo   2. Layout:       (handled by the script)
	echo   3. Draft:        (handled by the script)
	echo   4. Publish:      (handled by the script)
	echo   5. Read:         (handled by the script)
	exit /b 1
)

set "BOOK_NAME=%~1"
set "CHAPTER_COUNT=%~2"
set "summary=%~3"

if "%CHAPTER_COUNT%"=="" set CHAPTER_COUNT=2
if "%summary%"=="" set summary=A story about a mysterious journey.

echo [1/5] Initializing book: %BOOK_NAME%...
kobi init --book-name "%BOOK_NAME%" --chapter-count %CHAPTER_COUNT% --verbose --debug

echo [2/5] Generating layout with summary: %summary%...
kobi layout --book-name "%BOOK_NAME%" --summary "%summary%" --verbose --debug

echo [3/5] Drafting content...
kobi draft --book-name "%BOOK_NAME%" --verbose --debug

echo [4/5] Publishing book...
kobi publish --book-name "%BOOK_NAME%" --verbose --debug

echo [5/5] Reading final output...
kobi read --book-name "%BOOK_NAME%" --verbose --debug

echo.
echo Done!