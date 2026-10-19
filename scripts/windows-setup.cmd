@echo off
setlocal
cd /d "%~dp0.."
set PYTHONUTF8=1
py -3.11 scripts\setup_windows_demo.py
if errorlevel 1 echo Setup did not finish. See the message above and docs\WINDOWS_DEMO.md.
pause
