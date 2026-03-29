param(
  [string]$Payload,
  [string]$InputPath,
  [string]$Output = "output/device-qr.png"
)

$requirements = Join-Path $PSScriptRoot "requirements-qr.txt"
$scriptPath = Join-Path $PSScriptRoot "generate_device_qr.py"

python -m pip install -r $requirements | Out-Host

$pythonArgs = @($scriptPath, "--output", $Output)
if ($Payload) {
  $pythonArgs += @("--payload", $Payload)
}
if ($InputPath) {
  $pythonArgs += @("--input", $InputPath)
}

python @pythonArgs
