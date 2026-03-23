Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$hubApiDir = Join-Path $repoRoot "apps\hub-api"
$webDir = Join-Path $repoRoot "apps\web-dashboard"
$infraScriptsDir = Join-Path $repoRoot "infra\scripts"
$pythonPath = Join-Path $hubApiDir ".alice\Scripts\python.exe"
$activateScript = Join-Path $hubApiDir ".alice\Scripts\Activate.ps1"
$envFile = Join-Path $hubApiDir ".env"
$webEnvFile = Join-Path $webDir ".env.local"
$apiHost = if ($env:ALICE_API_HOST) { $env:ALICE_API_HOST } else { "0.0.0.0" }
$apiPort = if ($env:ALICE_API_PORT) { $env:ALICE_API_PORT } else { "8000" }
$apiHealthLocalUrl = "http://127.0.0.1:$apiPort/api/v1/health"
$apiDocsLocalUrl = "http://127.0.0.1:$apiPort/docs"
$apiHealthLanUrl = "http://192.168.0.29:$apiPort/api/v1/health"
$apiDocsLanUrl = "http://192.168.0.29:$apiPort/docs"

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-Command([string]$CommandName, [string]$Message) {
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw $Message
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSeconds = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

if (-not (Test-Path $pythonPath)) {
    throw "Missing hub-api venv at $pythonPath. Build it first in apps\hub-api."
}

if (-not (Test-Path $envFile)) {
    throw "Missing apps\hub-api\.env. Copy .env.example and set MQTT_HOST before starting the stack."
}

if (-not (Test-Path $webEnvFile)) {
    $exampleFile = Join-Path $webDir ".env.local.example"
    if (Test-Path $exampleFile) {
        Copy-Item $exampleFile $webEnvFile
    }
}

Ensure-Command "docker" "Docker Desktop is required to start the local Mosquitto broker."
Ensure-Command "bun" "bun is required to start the web dashboard."

Write-Step "Starting Docker Mosquitto"
& (Join-Path $infraScriptsDir "mqtt-up.ps1")

Write-Step "Running hub-api migrations"
Push-Location $hubApiDir
try {
    & $pythonPath -m alembic upgrade head
} finally {
    Pop-Location
}

$apiCommand = @"
Set-Location '$hubApiDir'
. '$activateScript'
`$env:ALICE_API_HOST='$apiHost'
`$env:ALICE_API_PORT='$apiPort'
python -m uvicorn app.main:app --host $apiHost --port $apiPort
"@

$webCommand = @"
Set-Location '$webDir'
if (-not (Test-Path '.\node_modules')) { bun install }
bun run dev
"@

Write-Step "Starting hub-api in a new PowerShell window"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    $apiCommand
)

Write-Step "Waiting for API readiness"
if (-not (Wait-Http $apiHealthLocalUrl 30)) {
    throw "hub-api did not become ready within 30 seconds."
}

Write-Step "Starting web dashboard in a new PowerShell window"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    $webCommand
)

Write-Step "Stack started"
Write-Host ""
Write-Host "Open these locally:" -ForegroundColor Green
Write-Host "  API docs:    $apiDocsLocalUrl"
Write-Host "  API health:  $apiHealthLocalUrl"
Write-Host "  Dashboard:   http://127.0.0.1:3000"
Write-Host ""
Write-Host "Open these from other devices on your LAN:" -ForegroundColor Green
Write-Host "  API docs:    $apiDocsLanUrl"
Write-Host "  API health:  $apiHealthLanUrl"
Write-Host ""
Write-Host "Power the ESP32 boards. If they are already powered, press EN/RST once on each board so they re-announce cleanly." -ForegroundColor Yellow
Write-Host "Then use the dashboard to confirm both devices appear and the relay responds." -ForegroundColor Yellow
