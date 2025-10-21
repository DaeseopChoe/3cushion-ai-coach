# simulate_example.ps1
# 예시 입력 몇 개를 돌려보고 결과를 파일로 저장

$ErrorActionPreference = "Stop"
$here  = Split-Path -Parent $MyInvocation.MyCommand.Path
$sysDir = Split-Path -Parent $here

$py = "python"

# 4→3/5→3/6→3 매핑을 필요 시 자동 생성(--auto-maps)
& $py "$sysDir/5_half_system_simulator.py" `
  --co 40 -2.25 `
  --mark 5C `
  --mx 60 --my 42.25 `
  --out "$sysDir/last_run_5C.json" `
  --force

& $py "$sysDir/5_half_system_simulator.py" `
  --co 52 42.25 `
  --mark 4C `
  --mx 62 --my 40 `
  --out "$sysDir/last_run_4C.json" `
  --force
