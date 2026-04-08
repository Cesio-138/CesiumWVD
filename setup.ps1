# WVD Extractor — Setup (Windows)
# Downloads a portable Python 3.12 and installs all dependencies into .python/.
# .python/ is self-contained (all DLLs included) so the Electron build works on
# any Windows machine — no Python installation required on the target.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PortablePythonDir = Join-Path $ScriptDir ".python"
$PythonExe = Join-Path $PortablePythonDir "python.exe"
$PipExe = Join-Path $PortablePythonDir "Scripts\pip.exe"

Write-Host ""
Write-Host "  WVD Extractor — Setup"
Write-Host "  ====================="
Write-Host ""

# ── 1. Ensure portable Python ────────────────────────────────────────────────

if (Test-Path $PythonExe) {
    Write-Host "  Portable Python already installed: $(& $PythonExe --version 2>&1)" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "  Downloading portable Python 3.12 (~60 MB)..."
    Write-Host ""

    $arch = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "i686" }
    $dl_url = $null

    try {
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest" `
            -TimeoutSec 20
        $asset = $release.assets | Where-Object {
            $_.name -like "*install_only.zip" -and
            $_.name -like "*$arch*"           -and
            $_.name -like "*windows*msvc*"    -and
            $_.name -notlike "*freethreaded*"
        } | Select-Object -First 1
        if ($asset) { $dl_url = $asset.browser_download_url }
    } catch { }

    # Hardcoded fallback (python-build-standalone 20260325, Python 3.12.13)
    if (-not $dl_url) {
        $dl_url = "https://github.com/astral-sh/python-build-standalone/releases/download/20260325/cpython-3.12.13%2B20260325-x86_64-pc-windows-msvc-install_only.zip"
    }

    Write-Host "  Downloading: $dl_url"
    New-Item -ItemType Directory -Force -Path $PortablePythonDir | Out-Null
    $zipFile = Join-Path $PortablePythonDir "python.zip"

    try {
        Invoke-WebRequest -Uri $dl_url -OutFile $zipFile -TimeoutSec 300
    } catch {
        Write-Host "  ERROR: Download failed: $_" -ForegroundColor Red
        Write-Host "  Install Python manually: https://www.python.org/downloads/"
        exit 1
    }

    Write-Host "  Extracting..."
    Expand-Archive -Path $zipFile -DestinationPath $PortablePythonDir -Force
    Remove-Item $zipFile

    # python-build-standalone Windows zip extracts into a 'python/' subfolder
    $innerDir = Join-Path $PortablePythonDir "python"
    if (Test-Path $innerDir) {
        Get-ChildItem -Path $innerDir | ForEach-Object {
            Move-Item -Path $_.FullName -Destination $PortablePythonDir -Force
        }
        Remove-Item $innerDir -Recurse -Force
    }

    if (-not (Test-Path $PythonExe)) {
        Write-Host "  ERROR: Portable Python extraction failed." -ForegroundColor Red
        exit 1
    }

    Write-Host "  Portable Python ready: $(& $PythonExe --version 2>&1)" -ForegroundColor Green
    Write-Host ""
}

# ── 2. Install dependencies into .python/ ───────────────────────────────────

Write-Host "  Installing dependencies..."
& $PipExe install --upgrade pip -q
& $PipExe install -r (Join-Path $ScriptDir "requirements.txt") -q

Write-Host ""
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next step: .\extract.ps1"
Write-Host ""
