$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$venvPython = Join-Path $projectRoot ".alice\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
    & $python -m app.scripts.seed_dev
}
finally {
    Pop-Location
}
