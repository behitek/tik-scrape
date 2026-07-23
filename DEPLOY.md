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

# 5. Install NSIS (for the installer — one-time, system-wide)
#    Download from https://nsis.sourceforge.io/ and install to the default location:
#    C:\Program Files (x86)\NSIS\
```

---

## Build the executable

Run each step from a PowerShell terminal in the project root:

```powershell
# Step 1 — install/update PyInstaller
poetry run pip install pyinstaller --quiet

# Step 2 — regenerate icons
poetry run python assets/create_icon.py

# Step 3 — build the app
poetry run pyinstaller build.spec --clean --noconfirm

# Step 4 — package portable zip
Compress-Archive -Path dist\TikTokImageScraper\* `
                 -DestinationPath dist\TikTokImageScraper-v1.0.0-win64.zip `
                 -Force

# Step 5 — build installer (requires NSIS installed)
& "C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

> **Note:** `build.bat` exists but must be run from a plain `cmd.exe` terminal
> (not PowerShell) due to Unicode characters in the script.

**Output files:**

```
dist\
  TikTokImageScraper\                          <- runnable folder (all files needed)
    TikTokImageScraper.exe                     <- main executable
    ...
  TikTokImageScraper-v1.0.0-win64.zip         <- portable distribution
  TikTokImageScraper-v1.0.0-Setup-win64.exe   <- Windows installer
```

---

## What to send the client

Preferred (installer):
```
dist\TikTokImageScraper-v1.0.0-Setup-win64.exe
```

Alternative (portable):
```
dist\TikTokImageScraper-v1.0.0-win64.zip
```

**Installer — client steps (no Python needed):**

1. Run `TikTokImageScraper-v1.0.0-Setup-win64.exe`
2. Follow the wizard — installs to `Program Files`, creates Start Menu shortcut
3. On first launch, the app will offer to install Chromium automatically (~150 MB, one-time)
4. Done — app appears in Start Menu and Add/Remove Programs

**Portable ZIP — client steps:**

1. Extract the ZIP to any folder (e.g. `C:\Tools\TikTokImageScraper\`)
2. Double-click `TikTokImageScraper.exe`
3. On first launch, the app will offer to install Chromium automatically (~150 MB, one-time)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pyinstaller: command not found` | Run `poetry run pip install pyinstaller` first |
| Missing Qt platform DLL on client | Ensure `platforms\qwindows.dll` is inside the dist folder |
| Chromium fails to install on client | Client runs `"%LOCALAPPDATA%\Programs\Python\...\playwright" install chromium` or contacts developer |
| App opens then immediately closes | Re-build without `console=False` in `build.spec` to see error output |
| UPX not found (warning) | Ignorable warning — install [UPX](https://github.com/upx/upx/releases) and add to PATH to compress the exe |
| NSIS `can't change compressor` error | `SetCompressor` must be the first line in `installer.nsi` (before any `!include`) |
| `build.bat` fails in PowerShell | Run it from `cmd.exe` instead, or run each step directly in PowerShell |

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
