import logging
import os
import subprocess
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QProgressBar,
    QVBoxLayout, QPushButton, QMessageBox,
)

APP_NAME      = "TikTok Image Scraper"
APP_VERSION   = "1.0.0"
ORG_NAME      = "Hieu Nguyen"
ORG_DOMAIN    = "behitek.com"


def _resource(rel: str) -> str:
    """Return absolute path to a bundled resource (works frozen and unfrozen)."""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, rel)


# ── Playwright first-run installer ──────────────────────────────────────────

class _BrowserInstaller(QThread):
    progress = Signal(str)
    finished_ok = Signal()
    finished_err = Signal(str)

    def run(self):
        try:
            self.progress.emit("Downloading Chromium browser (this may take a few minutes)…")
            # When frozen by PyInstaller, sys.executable is the bundled .exe itself —
            # calling it with "-m playwright install" just relaunches the app and loops.
            # Use playwright's own Node.js driver binary instead.
            if getattr(sys, "frozen", False):
                from playwright._impl._driver import compute_driver_executable
                driver, driver_env = compute_driver_executable()
                result = subprocess.run(
                    [str(driver), "install", "chromium"],
                    capture_output=True, text=True, timeout=600,
                    env={**os.environ, **driver_env},
                )
            else:
                result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True, text=True, timeout=600,
                )
            if result.returncode == 0:
                self.finished_ok.emit()
            else:
                self.finished_err.emit(result.stderr or result.stdout or "Unknown error")
        except Exception as e:
            self.finished_err.emit(str(e))


class _SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First-time Setup")
        self.setFixedSize(420, 160)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self._lbl = QLabel("Setting up Chromium browser for the first time…")
        self._lbl.setWordWrap(True)
        layout.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(0)  # indeterminate
        layout.addWidget(self._bar)

        self._btn = QPushButton("Cancel")
        self._btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._worker = _BrowserInstaller()
        self._worker.progress.connect(self._lbl.setText)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.start()

    def _on_ok(self):
        self._bar.setMaximum(1)
        self._bar.setValue(1)
        self.accept()

    def _on_err(self, msg: str):
        QMessageBox.warning(self, "Setup Error",
            f"Could not install Chromium automatically:\n\n{msg}\n\n"
            "Run  'playwright install chromium'  manually, then restart the app.")
        self.reject()

    def _on_cancel(self):
        self._worker.terminate()
        self.reject()


def _ensure_browser(app: QApplication) -> bool:
    """Return True if Chromium is ready; prompt to install if missing."""
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            info = pw.chromium.launch()
            info.close()
        return True
    except Exception:
        pass  # not installed

    reply = QMessageBox.question(
        None, "Browser Not Found",
        "The Chromium browser required to scrape TikTok is not installed yet.\n\n"
        "Install it now? (requires an internet connection, ~150 MB)",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return False

    dlg = _SetupDialog()
    return dlg.exec() == QDialog.DialogCode.Accepted


# ── Application entry point ──────────────────────────────────────────────────

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORG_NAME)
    app.setOrganizationDomain(ORG_DOMAIN)

    icon_path = _resource(os.path.join("assets", "icon.ico"))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    if not _ensure_browser(app):
        sys.exit(0)

    from ui.main_window import MainWindow  # imported after QApplication exists
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
