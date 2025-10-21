# run_validation_loop.ps1
# 샘플 → 앵커 병합 → 백업/적용 → 매핑 생성 → 검증까지 원클릭

param(
  [switch]$Force = $false,
  [switch]$SkipMerge = $false,
  [switch]$SkipApply = $false,
  [switch]$SkipMaps = $false,
  [switch]$SkipValidate = $false
)

$ErrorActionPreference = "Stop"

# repo 루트 기준으로 실행 경로 계산
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$sysDir = Split-Path -Parent $here                   # .../systems/5_half_system
$repo   = Split-Path -Parent (Split-Path -Parent $sysDir)  # .../repo

Write-Host "repo    : $repo"
Write-Host "system  : $sysDir"

# 파이썬 실행
$py = "python"

# 1) 샘플 → 병합/케이스
if (-not $SkipMerge) {
  & $py "$sysDir/5_half_system_validation_loop.py" `
      --template "$sysDir/5_half_system_samples_template.txt" `
      --anchors  "$sysDir/anchors.json" `
      --force:$Force `
      --skip-apply `
      --skip-maps `
      --skip-validate
}

# 2) 병합본 적용 + 백업, 3) 매핑, 4) 검증
& $py "$sysDir/5_half_system_validation_loop.py" `
    --template "$sysDir/5_half_system_samples_template.txt" `
    --anchors  "$sysDir/anchors.json" `
    --force:$Force `
    --skip-merge:$SkipMerge `
    --skip-apply:$SkipApply `
    --skip-maps:$SkipMaps `
    --skip-validate:$SkipValidate
