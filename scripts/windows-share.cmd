@echo off
setlocal
cd /d "%~dp0.."
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  echo Run windows-setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m prototype.share --backend-port 8013
pause
