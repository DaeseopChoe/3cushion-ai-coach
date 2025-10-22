# Run validation loop for 7_system (PowerShell)
Set-Location $PSScriptRoot\..
python ".\7_system_validation_loop.py" --samples ".\7_system_samples.json" --anchors ".\anchors.json" --profile ".\profile_7_system.json"
if ($LASTEXITCODE -ne 0) {
  Write-Error "[ERROR] validation failed. ExitCode=$LASTEXITCODE"
  exit $LASTEXITCODE
}
Write-Host "[OK] validation completed."
