# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for TikTok Image Scraper v1.0.0
Developer: Hieu Nguyen <hieunv.dev@gmail.com> — behitek.com
Released:  June 5, 2026
"""

import sys
import os as _os
import playwright as _pw
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Playwright JS/JSON data files
playwright_datas = collect_data_files("playwright", includes=["**/*.js", "**/*.json"])

# Playwright driver binaries (node.exe, playwright.cmd, etc.) are not picked up by
# collect_data_files — bundle them explicitly so the frozen app can install browsers.
_pw_dir = _os.path.dirname(_pw.__file__)
_driver_dir = _os.path.join(_pw_dir, "driver")
for _root, _, _files in _os.walk(_driver_dir):
    for _f in _files:
        if not (_f.endswith(".js") or _f.endswith(".json")):
            _src = _os.path.join(_root, _f)
            _dest = _os.path.relpath(_root, _os.path.dirname(_pw_dir))
            playwright_datas.append((_src, _dest))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/icon.ico", "assets"),
        ("assets/icon.png", "assets"),
        *playwright_datas,
    ],
    hiddenimports=[
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtXml",
        # Playwright internals
        "playwright",
        "playwright.sync_api",
        "playwright._impl._browser_type",
        "playwright._impl._playwright",
        *collect_submodules("playwright"),
        # Other deps
        "openpyxl",
        "openpyxl.cell._writer",
        "bs4",
        "PIL",
        "PIL.Image",
        "requests",
        "certifi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "xmlrpc", "pydoc"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TikTokImageScraper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                # no console window — GUI-only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=["qwindows.dll", "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll"],
    name="TikTokImageScraper",
)
