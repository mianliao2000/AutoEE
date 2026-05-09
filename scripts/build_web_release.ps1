param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$Workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Workspace

function Assert-InWorkspace {
    param([string]$Path)
    $resolvedParent = Split-Path -Parent $Path
    if (-not (Test-Path $resolvedParent)) {
        New-Item -ItemType Directory -Force -Path $resolvedParent | Out-Null
    }
    $full = [System.IO.Path]::GetFullPath($Path)
    $workspaceFull = [System.IO.Path]::GetFullPath($Workspace)
    if (-not $full.StartsWith($workspaceFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside workspace: $full"
    }
    return $full
}

function Reset-Directory {
    param([string]$Path)
    $full = Assert-InWorkspace $Path
    if (Test-Path $full) {
        Remove-Item -LiteralPath $full -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $full | Out-Null
}

function Assert-LastExit {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

function Stop-OldDistExe {
    $DistExe = [System.IO.Path]::GetFullPath((Join-Path $Workspace "dist\AutoEE\AutoEE.exe"))
    $workspaceFull = [System.IO.Path]::GetFullPath($Workspace)
    if (-not $DistExe.StartsWith($workspaceFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to inspect executable outside workspace: $DistExe"
    }

    $running = Get-CimInstance Win32_Process |
        Where-Object {
            $_.ExecutablePath -and
            ([System.IO.Path]::GetFullPath($_.ExecutablePath) -ieq $DistExe)
        }

    foreach ($process in $running) {
        Write-Host "Stopping old dist AutoEE.exe process $($process.ProcessId) before packaging."
        Stop-Process -Id $process.ProcessId -Force
    }
}

Write-Host "== AutoEE web release build =="
Write-Host "Workspace: $Workspace"

Write-Host "== Installing Python runtime dependencies =="
python -m pip install -r requirements.txt
Assert-LastExit "pip install"

Write-Host "== Installing frontend dependencies =="
npm --prefix web install
Assert-LastExit "npm install"

Write-Host "== Building frontend =="
$WebDistDir = Join-Path $Workspace "web\dist"
if (Test-Path $WebDistDir) {
    $resolvedWebDistDir = Assert-InWorkspace $WebDistDir
    Remove-Item -LiteralPath $resolvedWebDistDir -Recurse -Force
}
npm --prefix web run build
Assert-LastExit "npm build"

Write-Host "== Copying frontend into Python package data =="
$StaticDir = Join-Path $Workspace "autoee_demo\web_static"
Reset-Directory $StaticDir
Copy-Item -Path (Join-Path $Workspace "web\dist\*") -Destination $StaticDir -Recurse -Force

if (-not $SkipTests) {
    Write-Host "== Running Python tests =="
    python -m unittest discover -s tests
    Assert-LastExit "python tests"

    Write-Host "== Running launcher smoke check =="
    python -m autoee_demo.web_launcher --smoke
    Assert-LastExit "launcher smoke"

    Write-Host "== Running compileall =="
    python -m compileall autoee_demo evals tests tools
    Assert-LastExit "compileall"
}

Write-Host "== Building PyInstaller onedir =="
Stop-OldDistExe
python -m PyInstaller --noconfirm packaging/autoee_web.spec
Assert-LastExit "PyInstaller build"

Write-Host "== Preparing portable release folder =="
$ReleaseDir = Join-Path $Workspace "release\AutoEE-Investor-Demo"
Reset-Directory $ReleaseDir
Copy-Item -Path (Join-Path $Workspace "dist\AutoEE\*") -Destination $ReleaseDir -Recurse -Force
Copy-Item -Path (Join-Path $Workspace "README_START_HERE.txt") -Destination (Join-Path $ReleaseDir "README_START_HERE.txt") -Force

Write-Host "== Checking release for accidental OpenAI API key pattern =="
if (Get-Command rg -ErrorAction SilentlyContinue) {
    $SecretPattern = "s" + "k-"
    $matches = rg $SecretPattern $ReleaseDir
    if ($LASTEXITCODE -eq 0) {
        Write-Error "Potential API key pattern found in release folder."
    }
} else {
    Write-Host "ripgrep not found; skipping API key pattern check."
}

Write-Host "Release ready: $ReleaseDir"
