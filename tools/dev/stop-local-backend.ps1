Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Get-CimInstance Win32_Process |
    Where-Object {
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "uvicorn app\.main:app") -or
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "uvicorn assistant_runtime\.main:app") -or
        ($_.Name -match "^python(\.exe)?$" -and $_.CommandLine -match "alice_dev_console\.py") -or
        ($_.Name -match "^mosquitto(\.exe)?$")
    } |
    ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped PID $($_.ProcessId): $($_.Name)" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to stop PID $($_.ProcessId): $($_.Exception.Message)"
        }
    }
