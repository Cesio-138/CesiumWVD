# WVD Extractor — Run extraction (Windows)
# Runs src/main.py using the portable Python from .python/ (preferred)
# or the virtual environment in venv-wvd/ (legacy fallback).

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Prefer portable Python; fall back to venv for backwards compatibility
$PythonExe = Join-Path $ScriptDir ".python\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = Join-Path $ScriptDir "venv-wvd\Scripts\python.exe"
}

if (-not (Test-Path $PythonExe)) {
    Write-Host ""
    Write-Host "  ERROR: Python environment not found." -ForegroundColor Red
    Write-Host "  Run setup first:  .\setup.ps1"
    Write-Host ""
    exit 1
}

& $PythonExe (Join-Path $ScriptDir "src\main.py") @args
