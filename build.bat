@echo off
REM ============================================================
REM  Build script — TikTok Image Scraper v1.0.0
REM  Developer: Hieu Nguyen <hieunv.dev@gmail.com>
REM  Website:   behitek.com
REM ============================================================

setlocal

echo [1/4] Installing PyInstaller ...
uv add --dev pyinstaller --quiet

echo [2/4] Generating icon ...
uv run python assets/create_icon.py

echo [3/4] Building executable ...
uv run pyinstaller build.spec --clean --noconfirm

echo [4/5] Packaging portable zip ...
if exist dist\TikTokImageScraper (
    powershell -Command "Compress-Archive -Path 'dist\TikTokImageScraper\*' -DestinationPath 'dist\TikTokImageScraper-v1.0.0-win64.zip' -Force"
) else (
    echo ERROR: Build failed — dist folder not found.
    exit /b 1
)

echo [5/5] Building installer ...
set MAKENSIS=""
if exist "C:\Program Files (x86)\NSIS\makensis.exe" set MAKENSIS="C:\Program Files (x86)\NSIS\makensis.exe"
if exist "C:\Program Files\NSIS\makensis.exe"       set MAKENSIS="C:\Program Files\NSIS\makensis.exe"

if %MAKENSIS%=="" (
    echo   [SKIP] NSIS not found. Install from https://nsis.sourceforge.io/
    echo          Then re-run this script to also produce an installer.
) else (
    %MAKENSIS% installer.nsi
    if errorlevel 1 (
        echo ERROR: NSIS compilation failed.
        exit /b 1
    )
)

echo.
echo Build complete!
echo   Folder   : dist\TikTokImageScraper\
echo   Portable : dist\TikTokImageScraper-v1.0.0-win64.zip
if not %MAKENSIS%=="" echo   Installer: dist\TikTokImageScraper-v1.0.0-Setup-win64.exe

endlocal
