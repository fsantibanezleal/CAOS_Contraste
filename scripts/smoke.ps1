# Smoke: validate the CONTRACT 2 artifacts on disk (index -> manifests -> artifacts consistent). The built site is
# measured by `npm run gate` in frontend/, and the deployed one by scripts/check_live.py.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$py = Join-Path ".venv-pipeline" "Scripts\python.exe"
if (-not (Test-Path $py)) { $py = Join-Path ".venv-pipeline" "bin/python" }
if (-not (Test-Path $py)) { $py = if ($env:PYTHON) { $env:PYTHON } else { "python" } }
# Windows PowerShell 5.1 does not carry a native exit code to the script's own: each call is checked.
& $py scripts/check_artifacts.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py scripts/check_units.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py scripts/check_unit_constants.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
