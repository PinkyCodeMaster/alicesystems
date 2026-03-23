$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeFile = Resolve-Path (Join-Path $scriptDir "..\docker\docker-compose.yml")
docker compose -f $composeFile up -d mosquitto
