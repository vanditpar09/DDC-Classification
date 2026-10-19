@echo off
setlocal
cd /d "%~dp0.."
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Run windows-setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\check_windows_demo.py --quick
if errorlevel 1 (
  pause
  exit /b 1
)
set FIELDNOTE_OCR=portable
set FIELDNOTE_DB=output/fieldnote/windows-demo.sqlite3
set FIELDNOTE_CPU_THREADS=4
echo Open http://127.0.0.1:8013 after the server starts. Keep this window open.
".venv\Scripts\python.exe" -m prototype.run --port 8013 --model native_silver_v2
pause
