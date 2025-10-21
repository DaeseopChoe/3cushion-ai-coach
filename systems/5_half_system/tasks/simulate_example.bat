@echo off
REM simulate_example.bat

setlocal
set SYS_DIR=%~dp0..
set REPO=%SYS_DIR%\..\..

REM 5C 예시
python "%SYS_DIR%\5_half_system_simulator.py" ^
  --co 40 -2.25 ^
  --mark 5C ^
  --mx 60 --my 42.25 ^
  --out "%SYS_DIR%\last_run_5C.json" ^
  --force

IF ERRORLEVEL 1 GOTO :ERR

REM 4C 예시
python "%SYS_DIR%\5_half_system_simulator.py" ^
  --co 52 42.25 ^
  --mark 4C ^
  --mx 62 --my 40 ^
  --out "%SYS_DIR%\last_run_4C.json" ^
  --force

IF ERRORLEVEL 1 GOTO :ERR

echo.
echo === DONE: simulate examples saved ===
exit /b 0

:ERR
echo [ERROR] simulate failed
exit /b 1
