$ErrorActionPreference = "Stop"

$BASE = Split-Path -Parent $PSCommandPath
$DIST = Join-Path $BASE "dist"
$VERSION = "1.0.0"
$OUTPUT = Join-Path $DIST "SafeNet.exe"

Write-Host "SafeNet Packaging Script v$VERSION"
Write-Host "================================="
Write-Host ""

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: PyInstaller not found. Install it: pip install pyinstaller"
    exit 1
}

if (Test-Path $DIST) { Remove-Item -Recurse -Force $DIST }
New-Item -ItemType Directory -Path $DIST -Force | Out-Null

Write-Host "[1/3] Building executable with PyInstaller..."
pyinstaller --onefile --windowed `
    --name "SafeNet" `
    --distpath $DIST `
    --specpath (Join-Path $BASE "build") `
    --workpath (Join-Path $BASE "build") `
    --add-data "webapp/templates;webapp/templates" `
    --add-data "webapp/static;webapp/static" `
    --add-data "webapp/data;webapp/data" `
    --add-data "webapp/__init__.py;webapp" `
    --add-data "version.json;." `
    --add-data "requirements.txt;." `
    --hidden-import "waitress" `
    --hidden-import "psutil" `
    --hidden-import "sqlite3" `
    --hidden-import "werkzeug" `
    --hidden-import "flask" `
    --hidden-import "fpdf" `
    --icon NONE `
    (Join-Path $BASE "run.py") 2>&1

if (-not (Test-Path $OUTPUT)) {
    Write-Host "ERROR: Build failed - output not found at $OUTPUT"
    exit 1
}

Write-Host ""
Write-Host "[2/3] Creating distribution archive..."
$ZIP_PATH = Join-Path $BASE "SafeNet-v$VERSION.zip"
if (Test-Path $ZIP_PATH) { Remove-Item -Force $ZIP_PATH }

$items = @($OUTPUT, (Join-Path $BASE "version.json"), (Join-Path $BASE "README.md"))
$existing = $items | Where-Object { Test-Path $_ }
Compress-Archive -Path $existing -DestinationPath $ZIP_PATH -Force

Write-Host ""
Write-Host "[3/3] Build complete!"
Write-Host "  Executable: $OUTPUT"
Write-Host "  Archive:    $ZIP_PATH"
Write-Host "  Size:       $((Get-Item $OUTPUT).Length / 1MB -as [int]) MB"
Write-Host ""
Write-Host "Done!"
