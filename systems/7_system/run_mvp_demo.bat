@echo off
REM run_mvp_demo.bat : wrapper for PowerShell demo runner
setlocal
set SCRIPT_DIR=%~dp0
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_mvp_demo.ps1"
endlocal
