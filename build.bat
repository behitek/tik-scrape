@echo off
REM ============================================================
REM  Build script — TikTok Image Scraper v1.0.0
REM  Developer: Hieu Nguyen <hieunv.dev@gmail.com>
REM  Website:   behitek.com
REM ============================================================

setlocal

echo [1/4] Installing PyInstaller ...
poetry run pip install pyinstaller --quiet

echo [2/4] Generating icon ...
poetry run python assets/create_icon.py

echo [3/4] Building executable ...
poetry run pyinstaller build.spec --clean --noconfirm

echo [4/4] Packaging distribution ...
if exist dist\TikTokImageScraper (
    powershell -Command "Compress-Archive -Path 'dist\TikTokImageScraper\*' -DestinationPath 'dist\TikTokImageScraper-v1.0.0-win64.zip' -Force"
    echo.
    echo Build complete!
    echo   Folder : dist\TikTokImageScraper\
    echo   Archive: dist\TikTokImageScraper-v1.0.0-win64.zip
) else (
    echo ERROR: Build failed — dist folder not found.
    exit /b 1
)

endlocal
