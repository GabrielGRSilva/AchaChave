# Build script for AchaChave v1.2
# Bundles the Python app into a single standalone executable.

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$EntryPoint = Join-Path $ScriptDir "achachave.py"

Write-Host "Building AchaChave with PyInstaller..."
python -m PyInstaller --noconfirm --onefile --windowed --name "AchaChave" `
    "$EntryPoint"

Write-Host "Build complete! Check the 'dist/' folder for AchaChave.exe."
