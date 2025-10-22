# Simulate one example using 7_system_simulator.py (PowerShell)
Set-Location $PSScriptRoot\..
# Example: B2T_R, CO=(40,-2.25)_3, 3C=(82.25,20)_7
python ".\7_system_simulator.py" --track B2T_R --CO "CO_(40,-2.25)_3" --C3 "3C_(82.25,20)_7" --profile ".\profile_7_system.json" --anchors ".\anchors.json"
if ($LASTEXITCODE -ne 0) {
  Write-Error "[ERROR] simulate failed. ExitCode=$LASTEXITCODE"
  exit $LASTEXITCODE
}
Write-Host "[OK] simulate completed."
