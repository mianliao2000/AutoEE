param(
    [int]$Port = 5173,
    [int]$ApiPort = 8765
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$WebDir = Join-Path $RepoRoot "web"
$StartedApi = $null

if (-not (Test-Path (Join-Path $WebDir "package.json"))) {
    throw "Cannot find web/package.json. Run this script from the AutoEE repository."
}

function Test-HttpOk($Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/state")) {
    Write-Host "Starting AutoEE API at http://127.0.0.1:$ApiPort ..."
    $StartedApi = Start-Process -FilePath python `
        -ArgumentList @("-m", "uvicorn", "autoee_demo.web_app:create_app", "--factory", "--host", "127.0.0.1", "--port", "$ApiPort", "--log-level", "warning") `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -PassThru

    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpOk "http://127.0.0.1:$ApiPort/api/state") {
            break
        }
        Start-Sleep -Milliseconds 250
    }

    if (-not (Test-HttpOk "http://127.0.0.1:$ApiPort/api/state")) {
        throw "AutoEE API did not start on port $ApiPort."
    }
}
else {
    Write-Host "AutoEE API is already running at http://127.0.0.1:$ApiPort."
}

Push-Location $WebDir
try {
    if (-not (Test-Path "node_modules")) {
        npm install
    }

    Write-Host "Starting AutoEE frontend at http://127.0.0.1:$Port ..."
    npm run dev -- --port $Port
}
finally {
    Pop-Location
    if ($StartedApi -and -not $StartedApi.HasExited) {
        Stop-Process -Id $StartedApi.Id -Force
    }
}
