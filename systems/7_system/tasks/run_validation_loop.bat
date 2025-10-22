@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Run validation loop for 7_system
cd /d "%~dp0\.."
python "7_system_validation_loop.py" --samples "7_system_samples.json" --anchors "anchors.json" --profile "profile_7_system.json"
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] validation failed. ExitCode=%ERRORLEVEL%
  exit /b %ERRORLEVEL%
)
echo [OK] validation completed.
