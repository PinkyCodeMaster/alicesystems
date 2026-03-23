Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$hubApiDir = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $hubApiDir)
$pythonPath = Join-Path $hubApiDir ".alice\Scripts\python.exe"
$consoleScript = Join-Path $repoRoot "tools\dev\alice_dev_console.py"

if (-not (Test-Path $pythonPath)) {
    throw "Missing local venv interpreter at $pythonPath"
}

& $pythonPath $consoleScript --serial-port COM5 @args
