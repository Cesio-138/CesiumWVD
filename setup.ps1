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
        $apiHeaders = @{ "User-Agent" = "CesiumWVD-setup" }
        $token = if ($env:GH_TOKEN) { $env:GH_TOKEN } elseif ($env:GITHUB_TOKEN) { $env:GITHUB_TOKEN } else { $null }
        if ($token) { $apiHeaders["Authorization"] = "Bearer $token" }
        $release = Invoke-RestMethod `
            -Uri "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest" `
            -Headers $apiHeaders `
            -TimeoutSec 20
        $asset = $release.assets | Where-Object {
            $_.name -like "*install_only*.tar.gz" -and
            $_.name -like "*$arch*"               -and
            $_.name -like "*windows*msvc*"        -and
            $_.name -like "*3.12*"                -and
            $_.name -notlike "*freethreaded*"
        } | Select-Object -First 1
        if ($asset) { $dl_url = $asset.browser_download_url }
    } catch { }

    # Hardcoded fallback (python-build-standalone 20260325, Python 3.12.13)
    if (-not $dl_url) {
        $dl_url = "https://github.com/astral-sh/python-build-standalone/releases/download/20260325/cpython-3.12.13%2B20260325-x86_64-pc-windows-msvc-install_only.tar.gz"
    }

    Write-Host "  Downloading: $dl_url"
    New-Item -ItemType Directory -Force -Path $PortablePythonDir | Out-Null
    $tarFile = Join-Path $PortablePythonDir "python.tar.gz"

    try {
        Invoke-WebRequest -Uri $dl_url -OutFile $tarFile -TimeoutSec 300
    } catch {
        Write-Host "  ERROR: Download failed: $_" -ForegroundColor Red
        Write-Host "  Install Python manually: https://www.python.org/downloads/"
        exit 1
    }

    Write-Host "  Extracting..."
    # python-build-standalone tar has a top-level 'python/' directory; --strip-components=1 removes it
    tar -xzf $tarFile -C $PortablePythonDir --strip-components=1
    Remove-Item $tarFile

    if (-not (Test-Path $PythonExe)) {
        Write-Host "  ERROR: Portable Python extraction failed." -ForegroundColor Red
        exit 1
    }

    Write-Host "  Portable Python ready: $(& $PythonExe --version 2>&1)" -ForegroundColor Green
    Write-Host ""
}

# ── 2. Install dependencies into .python/ ───────────────────────────────────

Write-Host "  Installing dependencies..."
& $PythonExe -m pip install --upgrade pip -q
& $PythonExe -m pip install -r (Join-Path $ScriptDir "requirements.txt") -q

Write-Host ""
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next step: .\extract.ps1"
Write-Host ""
