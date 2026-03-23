$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")
$venvPython = Join-Path $projectRoot ".alice\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }
$dataDir = Join-Path $projectRoot "data"
$dbFiles = @(
    (Join-Path $dataDir "alice.db"),
    (Join-Path $dataDir "alice.db-shm"),
    (Join-Path $dataDir "alice.db-wal")
)

Push-Location $projectRoot
try {
    foreach ($file in $dbFiles) {
        if (Test-Path $file) {
            try {
                Remove-Item -Force $file -ErrorAction Stop
            }
            catch {
                Write-Error "Could not remove $file. Stop the API or any process using the local SQLite DB, then rerun reset-dev.ps1."
                exit 1
            }
        }
    }

    & $python -m alembic upgrade head
    & $python -m app.scripts.seed_dev
}
finally {
    Pop-Location
}
