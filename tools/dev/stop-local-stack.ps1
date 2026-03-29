Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$infraScriptsDir = Join-Path $repoRoot "infra\scripts"

Write-Host "Stopping local Mosquitto" -ForegroundColor Cyan
& (Join-Path $infraScriptsDir "mqtt-down.ps1")

Write-Host "Stopping uvicorn and Next.js node processes" -ForegroundColor Cyan
Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "uvicorn app\.main:app") -or
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "uvicorn assistant_runtime\.main:app") -or
        ($_.Name -match "^node(\.exe)?$" -and $_.CommandLine -match "next dev") -or
        ($_.Name -match "^node(\.exe)?$" -and $_.CommandLine -match "expo start")
    } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped PID $($_.ProcessId): $($_.Name)" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to stop PID $($_.ProcessId): $($_.Exception.Message)"
        }
    }
