from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QDoubleSpinBox, QSpinBox,
    QLabel, QScrollArea,
)

from ui.theme import PALETTE


class ConfigPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)

        layout.addWidget(self._build_scraping_group())
        layout.addWidget(self._build_captcha_group())
        layout.addStretch()

        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _build_scraping_group(self) -> QGroupBox:
        group = QGroupBox("Scraping Behaviour")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Human simulation toggle
        self.human_sim_check = QCheckBox("Enable human simulation")
        self.human_sim_check.setToolTip(
            "Adds random mouse movements and scrolling between requests\n"
            "to reduce the chance of bot detection."
        )
        layout.addWidget(self.human_sim_check)

        note = QLabel(
            "When enabled, the scraper performs random mouse moves and micro-pauses\n"
            "on each page to better mimic a real browser session."
        )
        note.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Delay settings
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.min_delay_spin = QDoubleSpinBox()
        self.min_delay_spin.setRange(0.0, 60.0)
        self.min_delay_spin.setValue(0.5)
        self.min_delay_spin.setSuffix("  s")
        self.min_delay_spin.setSingleStep(0.5)
        self.min_delay_spin.setFixedWidth(110)
        form.addRow("Min delay between requests:", self.min_delay_spin)

        self.max_delay_spin = QDoubleSpinBox()
        self.max_delay_spin.setRange(0.0, 120.0)
        self.max_delay_spin.setValue(2.0)
        self.max_delay_spin.setSuffix("  s")
        self.max_delay_spin.setSingleStep(0.5)
        self.max_delay_spin.setFixedWidth(110)
        form.addRow("Max delay between requests:", self.max_delay_spin)

        self.page_timeout_spin = QSpinBox()
        self.page_timeout_spin.setRange(5, 120)
        self.page_timeout_spin.setValue(30)
        self.page_timeout_spin.setSuffix("  s")
        self.page_timeout_spin.setFixedWidth(110)
        form.addRow("Page load timeout:", self.page_timeout_spin)

        layout.addLayout(form)
        return group

    def _build_captcha_group(self) -> QGroupBox:
        group = QGroupBox("CAPTCHA Handling")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.sound_notify_check = QCheckBox("Play alert sound when CAPTCHA is detected")
        self.sound_notify_check.setChecked(True)
        layout.addWidget(self.sound_notify_check)

        self.tray_notify_check = QCheckBox("Show desktop notification when CAPTCHA is detected")
        self.tray_notify_check.setChecked(True)
        layout.addWidget(self.tray_notify_check)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.captcha_timeout_spin = QSpinBox()
        self.captcha_timeout_spin.setRange(1, 30)
        self.captcha_timeout_spin.setValue(3)
        self.captcha_timeout_spin.setSuffix("  min")
        self.captcha_timeout_spin.setFixedWidth(110)
        form.addRow("Wait for CAPTCHA solve (max):", self.captcha_timeout_spin)

        layout.addLayout(form)
        return group

    def get_config(self) -> dict:
        return {
            "human_sim": self.human_sim_check.isChecked(),
            "min_delay": self.min_delay_spin.value(),
            "max_delay": self.max_delay_spin.value(),
            "page_timeout": self.page_timeout_spin.value(),
            "sound_notify": self.sound_notify_check.isChecked(),
            "tray_notify": self.tray_notify_check.isChecked(),
            "captcha_timeout_ms": self.captcha_timeout_spin.value() * 60 * 1000,
        }
