# Deployment Guide — TikTok Image Scraper v1.0.0

Developer: Hieu Nguyen <hieunv.dev@gmail.com> · behitek.com

---

## Prerequisites

Run these once on the build machine (Windows):

```bat
# 1. Install Poetry (if not already installed)
pip install poetry

# 2. Install project dependencies
poetry install

# 3. Install Playwright browser (needed at runtime, not bundled)
poetry run playwright install chromium

# 4. Install PyInstaller
poetry run pip install pyinstaller
```

---

## Build the executable

```bat
build.bat
```

This runs four steps automatically:

1. Regenerates `assets/icon.ico`
2. Runs `pyinstaller build.spec --clean`
3. Zips the output folder

**Output files:**

```
dist\
  TikTokImageScraper\          ← runnable folder (all files needed)
    TikTokImageScraper.exe     ← main executable
    ...
  TikTokImageScraper-v1.0.0-win64.zip   ← share this to the client
```

---

## What to send the client

Send the file:
```
dist\TikTokImageScraper-v1.0.0-win64.zip
```

**Client install steps (no Python needed):**

1. Extract the ZIP to any folder (e.g. `C:\Tools\TikTokImageScraper\`)
2. Double-click `TikTokImageScraper.exe`
3. On first launch, the app will offer to install Chromium automatically (~150 MB, one-time)
4. Done — ready to use

---

## Manual build (step-by-step)

If `build.bat` fails, run each step manually:

```bat
# Generate icon
poetry run python assets/create_icon.py

# Build
poetry run pyinstaller build.spec --clean --noconfirm

# Package (PowerShell)
Compress-Archive -Path dist\TikTokImageScraper\* `
                 -DestinationPath dist\TikTokImageScraper-v1.0.0-win64.zip `
                 -Force
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pyinstaller: command not found` | Run `poetry run pip install pyinstaller` first |
| Missing Qt platform DLL on client | Ensure `platforms\qwindows.dll` is inside the dist folder |
| Chromium fails to install on client | Client runs `"%LOCALAPPDATA%\Programs\Python\...\playwright" install chromium` or contacts developer |
| App opens then immediately closes | Re-build without `console=False` in `build.spec` to see error output |
| UPX not found (warning) | Ignorable warning — install [UPX](https://github.com/upx/upx/releases) and add to PATH to compress the exe |

---

## Version info embedded in the EXE

Right-click `TikTokImageScraper.exe` → Properties → Details to see:

| Field | Value |
|---|---|
| Product name | TikTok Image Scraper |
| Product version | 1.0.0 |
| Company name | Hieu Nguyen — behitek.com |
| Copyright | © 2026 Hieu Nguyen |
| Contact | hieunv.dev@gmail.com |
