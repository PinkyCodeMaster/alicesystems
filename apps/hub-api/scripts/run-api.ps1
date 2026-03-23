$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$venvPython = Join-Path $projectRoot ".alice\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

Push-Location $projectRoot
try {
    $hostAddress = if ($env:ALICE_API_HOST) { $env:ALICE_API_HOST } else { "0.0.0.0" }
    $port = if ($env:ALICE_API_PORT) { $env:ALICE_API_PORT } else { "8000" }
    & $python -m uvicorn app.main:app --host $hostAddress --port $port --reload
}
finally {
    Pop-Location
}
