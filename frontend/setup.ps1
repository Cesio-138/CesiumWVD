# This script has moved to the project root.
# Please run setup.ps1 from the CesiumWVD/ project root instead:
#
#   cd ..
#   .\setup.ps1
#
# Running it from frontend/ creates the Python environment in the wrong
# location and the Electron build will not find it.

Write-Host ""
Write-Host "  ERROR: Run setup.ps1 from the project root, not from frontend/." -ForegroundColor Red
Write-Host "  cd .."
Write-Host "  .\setup.ps1"
Write-Host ""
exit 1

<# Original script kept below for reference — DO NOT use directly #>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir "venv-wvd"
$PortablePythonDir = Join-Path $ScriptDir ".python"

Write-Host ""
Write-Host "  WVD Extractor — Setup"
Write-Host "  ====================="
Write-Host ""

# ── 1. Find or download Python ───────────────────────────────────────────────

$Python = $null
foreach ($candidate in @("python3", "python", "py")) {
    try {
        $args_ = if ($candidate -eq "py") { @("-3", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") } `
                 else                      { @("-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") }
        $ver = & $candidate @args_ 2>$null
        if ($ver) {
            $parts = $ver.Trim().Split(".")
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 8) {
                $Python = $candidate
                break
            }
        }
    } catch { }
}

function Get-PortablePython {
    Write-Host "  Python >= 3.8 not found. Downloading a portable Python 3.12 (~60 MB)..."
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

    # python-build-standalone Windows zip has files inside a 'python/' subfolder
    $innerDir = Join-Path $PortablePythonDir "python"
    if (Test-Path $innerDir) {
        Get-ChildItem -Path $innerDir | ForEach-Object {
            Move-Item -Path $_.FullName -Destination $PortablePythonDir -Force
        }
        Remove-Item $innerDir -Recurse -Force
    }

    $exe = Join-Path $PortablePythonDir "python.exe"
    if (-not (Test-Path $exe)) {
        Write-Host "  ERROR: Portable Python extraction failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Portable Python ready: $(& $exe --version)" -ForegroundColor Green
    Write-Host ""
    return $exe
}

# Resolve to an actual executable path for venv creation
$PythonExe = $null
if ($Python) {
    try {
        $PythonExe = if ($Python -eq "py") {
            (& py -3 -c "import sys; print(sys.executable)" 2>$null).Trim()
        } else {
            (& $Python -c "import sys; print(sys.executable)" 2>$null).Trim()
        }
    } catch { }
}
if (-not $PythonExe) {
    $PythonExe = Get-PortablePython
}

Write-Host "  Using: $PythonExe ($(& $PythonExe --version 2>&1))"

# ── 2. Create virtual environment ────────────────────────────────────────────

if (Test-Path $VenvDir) {
    Write-Host "  Virtual environment already exists: $VenvDir"
    Write-Host "  To recreate, delete it first: Remove-Item -Recurse $VenvDir"
} else {
    Write-Host "  Creating virtual environment..."
    & $PythonExe -m venv $VenvDir
}

# ── 3. Install dependencies ─────────────────────────────────────────────────

$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
Write-Host "  Installing dependencies..."
& $PipExe install --upgrade pip -q
& $PipExe install -r (Join-Path $ScriptDir "requirements.txt") -q

Write-Host ""
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Next step: .\extract.ps1"
Write-Host ""
