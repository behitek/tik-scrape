import logging
from html import escape

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFrame, QApplication,
)

from ui.theme import PALETTE


class QtLogHandler(QObject, logging.Handler):
    """Logging handler that forwards records to Qt via a signal (thread-safe)."""
    log_emitted = Signal(int, str)

    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        fmt = logging.Formatter(
            "%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )
        self.setFormatter(fmt)

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.log_emitted.emit(record.levelno, msg)
        except Exception:
            self.handleError(record)


_LEVEL_COLORS = {
    logging.DEBUG:    PALETTE["text_dim"],
    logging.INFO:     PALETTE["text"],
    logging.WARNING:  PALETTE["warning"],
    logging.ERROR:    PALETTE["error"],
    logging.CRITICAL: PALETTE["red"],
}


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = True
        self._error_count = 0
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header (always visible) ──────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(30)
        header.setStyleSheet(
            f"QFrame {{ background: {PALETTE['bg_surface']}; "
            f"border-top: 1px solid {PALETTE['border']}; border-bottom: none; }}"
        )
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 0, 10, 0)
        h_layout.setSpacing(8)

        self._toggle_btn = QPushButton("▶  Logs")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; "
            f"color: {PALETTE['text_dim']}; font-size: 11px; text-align: left; }}"
            f"QPushButton:hover {{ color: {PALETTE['text']}; }}"
        )
        self._toggle_btn.clicked.connect(self._toggle)
        h_layout.addWidget(self._toggle_btn, stretch=1)

        btn_style = (
            f"QPushButton {{ background: {PALETTE['bg_raised']}; border: 1px solid {PALETTE['border_lt']}; "
            f"border-radius: 3px; padding: 2px 8px; color: {PALETTE['text_dim']}; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {PALETTE['teal']}; border-color: {PALETTE['teal']}; }}"
        )

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedHeight(22)
        copy_btn.setStyleSheet(btn_style)
        copy_btn.clicked.connect(self._copy_logs)
        h_layout.addWidget(copy_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(22)
        clear_btn.setStyleSheet(btn_style)
        clear_btn.clicked.connect(self._clear_logs)
        h_layout.addWidget(clear_btn)

        root.addWidget(header)

        # ── Log text area (collapsed by default) ────────────────────────────
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFixedHeight(180)
        self._text.setVisible(False)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        root.addWidget(self._text)

    # ── Public API ──────────────────────────────────────────────────────────

    def append_log(self, level: int, message: str):
        color = _LEVEL_COLORS.get(level, PALETTE["text"])

        # Bold for WARNING+
        if level >= logging.WARNING:
            html = f'<span style="color:{color}; font-weight:600;">{escape(message)}</span>'
        else:
            html = f'<span style="color:{color};">{escape(message)}</span>'

        self._text.append(html)

        # Track errors and auto-expand on first error
        if level >= logging.ERROR:
            self._error_count += 1
            self._refresh_toggle_label()
            if self._collapsed:
                self._toggle()  # auto-expand so user sees the error
        elif level >= logging.WARNING:
            self._refresh_toggle_label()

    # ── Internals ───────────────────────────────────────────────────────────

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._text.setVisible(not self._collapsed)
        self._refresh_toggle_label()

    def _refresh_toggle_label(self):
        arrow = "▼" if not self._collapsed else "▶"
        if self._error_count > 0:
            label = f"{arrow}  Logs  ·  {self._error_count} error(s)"
            self._toggle_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; "
                f"color: {PALETTE['error']}; font-size: 11px; text-align: left; }}"
                f"QPushButton:hover {{ color: {PALETTE['text']}; }}"
            )
        else:
            label = f"{arrow}  Logs"
            self._toggle_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; "
                f"color: {PALETTE['text_dim']}; font-size: 11px; text-align: left; }}"
                f"QPushButton:hover {{ color: {PALETTE['text']}; }}"
            )
        self._toggle_btn.setText(label)

    def _copy_logs(self):
        QApplication.clipboard().setText(self._text.toPlainText())

    def _clear_logs(self):
        self._text.clear()
        self._error_count = 0
        self._refresh_toggle_label()
