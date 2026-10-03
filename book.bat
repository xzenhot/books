@echo off
if "%~1"=="" (
	echo Usage: book.bat BOOK_NAME [CHAPTER_COUNT] [summary]
	echo Example: book.bat MyNovel 20 "A story about hope."
	echo.
	echo Steps:
	echo   1. Init:        book.bat MyNovel 10 "A story about hope."
	echo   2. Layout:      (handled by the script)
	echo   3. Scaffold:    (handled by the script)
	echo   4. Enrich:      (handled by the script)
	echo   5. Write:       (handled by the script)
	echo   6. Review:      (handled by the script)
	echo   7. Publish:     (handled by the script)
	echo   8. Preview:     (handled by the script)
	exit /b 1
)

set "BOOK_NAME=%~1"
set "CHAPTER_COUNT=%~2"
set "summary=%~3"

if "%CHAPTER_COUNT%"=="" set CHAPTER_COUNT=2
if "%summary%"=="" set summary=A story about a mysterious journey.

echo [1/8] Initializing book: %BOOK_NAME%...
python writer\.tools\book.py "%BOOK_NAME%" init "%summary%" poetry

echo [2/8] Generating layout (count: %CHAPTER_COUNT%)...
python writer\.tools\book.py "%BOOK_NAME%" layout %CHAPTER_COUNT%

echo [3/8] Scaffolding pipeline...
python writer\.tools\book.py "%BOOK_NAME%" scaffold %CHAPTER_COUNT% poetry

echo [4/8] Enriching chapters...
python writer\.tools\book.py "%BOOK_NAME%" enrich all

echo [5/8] Writing chapters...
python writer\.tools\book.py "%BOOK_NAME%" write all

echo [6/8] Reviewing quality...
python writer\.tools\book.py "%BOOK_NAME%" review all

echo [7/8] Publishing book...
python writer\.tools\book.py "%BOOK_NAME%" publish

echo [8/8] Previewing draft...
python writer\.tools\book.py "%BOOK_NAME%" preview

echo.
echo Done!