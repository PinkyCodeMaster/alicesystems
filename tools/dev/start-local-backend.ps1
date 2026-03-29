Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$consoleScript = Join-Path $PSScriptRoot "alice_dev_console.py"
$hubApiDir = Join-Path $repoRoot "apps\hub-api"
$assistantDir = Join-Path $repoRoot "apps\assistant-runtime"
$hubPython = Join-Path $hubApiDir ".alice\Scripts\python.exe"
$assistantPython = Join-Path $assistantDir ".alice\Scripts\python.exe"

function Stop-DockerContainerIfRunning([string]$Name) {
    $id = docker ps -q -f "name=^${Name}$"
    if ($LASTEXITCODE -eq 0 -and $id) {
        Write-Host "Stopping Docker container $Name" -ForegroundColor Yellow
        docker stop $Name | Out-Host
    }
}

Write-Host "Switching to native backend mode" -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Stop-DockerContainerIfRunning "alice-practice-hub-api"
    Stop-DockerContainerIfRunning "alice-practice-dashboard"
    Stop-DockerContainerIfRunning "alice-practice-assistant"
    Stop-DockerContainerIfRunning "alice-practice-mock-sensor"
    Stop-DockerContainerIfRunning "alice-practice-mock-relay"
    Stop-DockerContainerIfRunning "alice-mosquitto"
}

Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "uvicorn app\.main:app") -or
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "uvicorn assistant_runtime\.main:app")
    } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped PID $($_.ProcessId): $($_.Name)" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to stop PID $($_.ProcessId): $($_.Exception.Message)"
        }
    }

if (-not (Test-Path $hubPython)) {
    throw "Missing hub-api venv at $hubPython"
}

if (-not (Test-Path $assistantPython)) {
    throw "Missing assistant-runtime venv at $assistantPython"
}

& $hubPython $consoleScript `
    --native-broker `
    --hub-api-dir $hubApiDir `
    --hub-python $hubPython `
    --assistant-dir $assistantDir `
    --assistant-python $assistantPython
