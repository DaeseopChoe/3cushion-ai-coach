<# 
run_mvp_demo.ps1
- Validates samples/anchors/profile
- Runs a few simulator calls (one per track) using the first entries from 7_system_samples.json
Usage:
  pwsh -File .\run_mvp_demo.ps1 [-PythonExe python]
#>

param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# Paths
$paths = @{
  samples = ".\7_system_samples.json"
  anchors = ".\anchors.json"
  profile = ".\profile_7_system.json"
  validator = ".\7_system_validation_loop.py"
  simulator = ".\7_system_simulator.py"
  outdir = ".\out"
  log = ".\out\mvp_demo.log"
}

# Prepare out dir
if (-not (Test-Path $paths.outdir)) { New-Item -ItemType Directory -Path $paths.outdir | Out-Null }
if (Test-Path $paths.log) { Remove-Item $paths.log -Force }

function Write-Log($msg) {
  $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  $line = "[${stamp}] $msg"
  $line | Tee-Object -FilePath $paths.log -Append
}

function Ensure-File($p, $label) {
  if (-not (Test-Path $p)) {
    throw "Missing $label: $p"
  }
}

Ensure-File $paths.samples "samples"
Ensure-File $paths.anchors "anchors"
Ensure-File $paths.profile "profile"
Ensure-File $paths.validator "validator script"
Ensure-File $paths.simulator "simulator script"

# 1) Validation
Write-Log "== Validation: $($paths.validator)"
$valArgs = @(
  $paths.validator, "--samples", $paths.samples, "--anchors", $paths.anchors, "--profile", $paths.profile
)
& $PythonExe @valArgs
if ($LASTEXITCODE -ne 0) {
  Write-Log "Validation FAILED (exit $LASTEXITCODE)"
  exit $LASTEXITCODE
} else {
  Write-Log "Validation OK"
}

# 2) Load a few examples from samples.json (first entry per track)
Write-Log "== Loading examples from $($paths.samples)"
$samplesJson = Get-Content $paths.samples -Raw | ConvertFrom-Json
$tracks = @("B2T_R","B2T_L","T2B_R","T2B_L")
$examples = @()

function To-Token($label, $obj) {
  # build 'CO_(x,y)_sys' like tokens
  $x = [string]::Format("{0}", $obj.x)
  $y = [string]::Format("{0}", $obj.y)
  $s = [string]::Format("{0}", $obj.sys)
  return "{0}_({1},{2})_{3}" -f $label, $x, $y, $s
}

foreach ($t in $tracks) {
  $rows = $samplesJson.tracks.$t
  if ($null -ne $rows -and $rows.Count -gt 0) {
    $coTok = To-Token "CO" $rows[0].CO
    $c3Tok = To-Token "3C" $rows[0]."3C"
    $examples += [pscustomobject]@{ track=$t; CO=$coTok; C3=$c3Tok }
  }
}

# 3) Run simulator for each picked example
foreach ($ex in $examples) {
  Write-Log ("== Simulate: {0} | {1} , {2}" -f $ex.track, $ex.CO, $ex.C3)
  $simArgs = @(
    $paths.simulator, "--track", $ex.track,
    "--CO", $ex.CO, "--C3", $ex.C3,
    "--profile", $paths.profile, "--anchors", $paths.anchors
  )
  & $PythonExe @simArgs 2>&1 | Tee-Object -FilePath $paths.log -Append
  if ($LASTEXITCODE -ne 0) {
    Write-Log ("Simulate FAILED for track {0} (exit {1})" -f $ex.track, $LASTEXITCODE)
    exit $LASTEXITCODE
  } else {
    Write-Log ("Simulate OK for track {0}" -f $ex.track)
  }
}

Write-Log "== MVP demo completed successfully."
Write-Host "MVP demo completed. See log: $($paths.log)"
