@echo off
REM run_validation_loop.bat
REM 샘플 → 병합 → 백업/적용 → 매핑 → 검증

setlocal
set SYS_DIR=%~dp0..
set REPO=%SYS_DIR%\..\..

echo repo    : %REPO%
echo system  : %SYS_DIR%

REM 1) 샘플 → 병합/케이스 생성 (병합만)
python "%SYS_DIR%\5_half_system_validation_loop.py" ^
  --template "%SYS_DIR%\5_half_system_samples_template.txt" ^
  --anchors  "%SYS_DIR%\anchors.json" ^
  --force ^
  --skip-apply --skip-maps --skip-validate

IF ERRORLEVEL 1 GOTO :ERR

REM 2~4) 적용 + 매핑 + 검증
python "%SYS_DIR%\5_half_system_validation_loop.py" ^
  --template "%SYS_DIR%\5_half_system_samples_template.txt" ^
  --anchors  "%SYS_DIR%\anchors.json" ^
  --force

IF ERRORLEVEL 1 GOTO :ERR
echo.
echo === DONE: Validation loop OK ===
exit /b 0

:ERR
echo [ERROR] validation loop failed
exit /b 1
