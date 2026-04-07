# WVD Extractor — Run extraction (Windows)
# Activates the venv and runs src/main.py

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $ScriptDir "venv-wvd"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host ""
    Write-Host "  ERROR: Virtual environment not found." -ForegroundColor Red
    Write-Host "  Run setup first:  .\setup.ps1"
    Write-Host ""
    exit 1
}

& $PythonExe (Join-Path $ScriptDir "src\main.py") @args
