from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)

from ui.theme import PALETTE

APP_NAME    = "TikTok Image Scraper"
APP_VERSION = "1.0.0"
APP_DATE    = "June 5, 2026"
DEV_NAME    = "Hieu Nguyen"
DEV_EMAIL   = "hieunv.dev@gmail.com"
DEV_WEBSITE = "https://behitek.com"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(380, 280)
        self.setStyleSheet(f"""
            QDialog {{
                background: {PALETTE['bg_surface']};
                border: 1px solid {PALETTE['border']};
            }}
            QLabel {{ background: transparent; }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(6)

        # Icon + app name row
        header = QHBoxLayout()
        header.setSpacing(14)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(56, 56)
        px = QPixmap("assets/icon.png")
        if not px.isNull():
            icon_lbl.setPixmap(px.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
        header.addWidget(icon_lbl)

        name_block = QVBoxLayout()
        name_block.setSpacing(2)
        name_lbl = QLabel(APP_NAME)
        name_lbl.setStyleSheet(f"color: {PALETTE['teal']}; font-size: 16px; font-weight: bold;")
        version_lbl = QLabel(f"Version {APP_VERSION}  ·  {APP_DATE}")
        version_lbl.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        name_block.addWidget(name_lbl)
        name_block.addWidget(version_lbl)
        header.addLayout(name_block)
        header.addStretch()
        layout.addLayout(header)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {PALETTE['border']}; min-height: 1px; max-height: 1px;")
        layout.addSpacing(10)
        layout.addWidget(sep)
        layout.addSpacing(10)

        # Developer info
        def info_row(label: str, value: str, link: str = ""):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(80)
            lbl.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 12px;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {PALETTE['text']}; font-size: 12px;")
            if link:
                val.setStyleSheet(
                    f"color: {PALETTE['primary']}; font-size: 12px; text-decoration: underline;"
                )
                val.setCursor(Qt.CursorShape.PointingHandCursor)
                val.mousePressEvent = lambda _e, u=link: QDesktopServices.openUrl(QUrl(u))
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            layout.addLayout(row)

        info_row("Developer:", DEV_NAME)
        info_row("Email:",    DEV_EMAIL,   f"mailto:{DEV_EMAIL}")
        info_row("Website:",  "behitek.com", DEV_WEBSITE)

        layout.addStretch()

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
