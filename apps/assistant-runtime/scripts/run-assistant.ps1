$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$venvPython = Join-Path $projectRoot ".alice\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
$hostAddress = if ($env:ALICE_ASSISTANT_HOST) { $env:ALICE_ASSISTANT_HOST } else { "0.0.0.0" }
$port = if ($env:ALICE_ASSISTANT_PORT) { $env:ALICE_ASSISTANT_PORT } else { "8010" }

Push-Location $projectRoot
try {
    & $python -m uvicorn assistant_runtime.main:app --host $hostAddress --port $port --reload
}
finally {
    Pop-Location
}
