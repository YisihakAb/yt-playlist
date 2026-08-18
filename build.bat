@echo off
REM ============================================================
REM Build script - creates a single, size-optimized .exe
REM Run this on Windows, inside the project folder.
REM ============================================================

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Building exe with PyInstaller...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "YouTubePlaylistDownloader" ^
  --optimize 2 ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module PIL ^
  --exclude-module scipy ^
  --exclude-module test ^
  --exclude-module unittest ^
  --exclude-module pydoc_data ^
  --strip ^
  main.py

echo.
echo Done. Find your exe in the "dist" folder.
echo (Optional) Install UPX and add --upx-dir "C:\path\to\upx" to shrink it further.
pause
