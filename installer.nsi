; ============================================================
;  NSIS installer script — TikTok Image Scraper v1.1.0
;  Developer: Hieu Nguyen <hieunv.dev@gmail.com>
;  Website:   behitek.com
; ============================================================

Unicode True
SetCompressor /SOLID lzma

!define APP_NAME      "TikTok Image Scraper"
!ifndef APP_VERSION
!define APP_VERSION   "1.1.0"
!endif
!define APP_PUBLISHER "Hieu Nguyen"
!define APP_URL       "https://behitek.com"
!define APP_EXE       "TikTokImageScraper.exe"
!define BUILD_DIR     "dist\TikTokImageScraper"
!define UNINST_KEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\TikTokImageScraper"

; ---- Modern UI -----------------------------------------------
!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; ---- Installer metadata --------------------------------------
Name          "${APP_NAME} ${APP_VERSION}"
OutFile       "dist\TikTokImageScraper-v${APP_VERSION}-Setup-win64.exe"
InstallDir    "$PROGRAMFILES64\TikTokImageScraper"
InstallDirRegKey HKLM "${UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin

; ---- Install section -----------------------------------------
Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "${BUILD_DIR}\*.*"

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
    CreateShortcut  "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"   "$INSTDIR\Uninstall.exe"

    ; Optional desktop shortcut
    MessageBox MB_YESNO "Create a desktop shortcut?" IDNO skip_desktop
        CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
    skip_desktop:

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Register in Add/Remove Programs
    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"      "${APP_NAME}"
    WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"   "${APP_VERSION}"
    WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"        "${APP_PUBLISHER}"
    WriteRegStr   HKLM "${UNINST_KEY}" "URLInfoAbout"     "${APP_URL}"
    WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation"  "$INSTDIR"
    WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString"  "$INSTDIR\Uninstall.exe"
    WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify"         1
    WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair"         1
SectionEnd

; ---- Uninstall section ---------------------------------------
Section "Uninstall"
    ; Remove installed files
    RMDir /r "$INSTDIR"

    ; Remove Start Menu shortcuts
    RMDir /r "$SMPROGRAMS\${APP_NAME}"

    ; Remove desktop shortcut (if it exists)
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; Remove Playwright browser profile
    RMDir /r "$APPDATA\.tik-scrape-profile"

    ; Remove registry entry
    DeleteRegKey HKLM "${UNINST_KEY}"
SectionEnd
