from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QDoubleSpinBox, QSpinBox,
    QLabel, QScrollArea, QPlainTextEdit,
)

from ui.theme import PALETTE

_DEFAULT_PREFIXES = """\
AMBER01
BLAZE02
CEDAR03
DRIFT04
EMBER05
FLINT06
GROVE07
HAVEN08
IVORY09
JADE10
KARMA11
LUNAR12
MAPLE13
NOBLE14
OPAL15
PEARL16
QUARTZ17
RIVER18
STONE19
THORN20
URBAN21
VELVET22
WILLOW23
XENON24
YACHT25
ZINC26
BOLT27
CORAL28
DUSK29
ECHO30
FERN31
GOLD32
HAZE33
IRIS34
JEST35
KITE36
LOFT37
MINT38
NOVA39
ONYX40
PINE41
QUEST42
REED43
SAGE44
TIDE45
ASHY46
BARK47
CYAN48
DAWN49
EDEN50
FOAM51
GLOW52
HILL53
ICON54
JOLT55
KELP56
LACE57
MOSS58
NEON59
ORCA60
PUFF61
RAIN62
SILK63
TEAL64
UMBER65
VINE66
WAVE67
AXIS68
BONE69
CLAY70
DUNE71
EARL72
FLUX73
GRAY74
HUSK75
IRON76
JURY77
KERN78
LARK79
MUSK80
NAIL81
OAKS82
PLUM83
QUIZ84
RUST85
SLAB86
TUFT87
VOLT88
WREN89
YOLK90
ZEAL91
ARCH92
BUFF93
CHIP94
DALE95
EDGE96
FAWN97
GUST98
HALO99
INKS100"""


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

        layout.addWidget(self._build_prefix_group())
        layout.addWidget(self._build_scraping_group())
        layout.addWidget(self._build_captcha_group())
        layout.addStretch()

        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def _build_prefix_group(self) -> QGroupBox:
        group = QGroupBox("Danh sách tiền tố")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        note = QLabel(
            "Mỗi tiền tố một dòng. URL thứ nhất dùng tiền tố đầu, URL thứ hai dùng tiền tố tiếp theo, v.v. "
            "Nếu số URL nhiều hơn số tiền tố, danh sách sẽ được lặp lại từ đầu."
        )
        note.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.prefix_list_edit = QPlainTextEdit()
        self.prefix_list_edit.setPlainText(_DEFAULT_PREFIXES)
        self.prefix_list_edit.setFixedHeight(180)
        layout.addWidget(self.prefix_list_edit)

        return group

    def _build_scraping_group(self) -> QGroupBox:
        group = QGroupBox("Cài đặt thu thập")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.human_sim_check = QCheckBox("Bật mô phỏng người dùng thật")
        self.human_sim_check.setChecked(True)
        self.human_sim_check.setToolTip(
            "Thêm chuyển động chuột và cuộn trang ngẫu nhiên giữa các yêu cầu\n"
            "để giảm nguy cơ bị phát hiện là bot."
        )
        layout.addWidget(self.human_sim_check)

        note = QLabel(
            "Khi bật, trình thu thập sẽ thực hiện di chuyển chuột ngẫu nhiên và tạm dừng nhỏ\n"
            "trên mỗi trang để mô phỏng hành vi người dùng thật."
        )
        note.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.min_delay_spin = QDoubleSpinBox()
        self.min_delay_spin.setRange(0.0, 60.0)
        self.min_delay_spin.setValue(2.0)
        self.min_delay_spin.setSuffix("  s")
        self.min_delay_spin.setSingleStep(0.5)
        self.min_delay_spin.setFixedWidth(110)
        form.addRow("Thời gian chờ tối thiểu:", self.min_delay_spin)

        self.max_delay_spin = QDoubleSpinBox()
        self.max_delay_spin.setRange(0.0, 120.0)
        self.max_delay_spin.setValue(4.0)
        self.max_delay_spin.setSuffix("  s")
        self.max_delay_spin.setSingleStep(0.5)
        self.max_delay_spin.setFixedWidth(110)
        form.addRow("Thời gian chờ tối đa:", self.max_delay_spin)

        self.page_timeout_spin = QSpinBox()
        self.page_timeout_spin.setRange(5, 120)
        self.page_timeout_spin.setValue(30)
        self.page_timeout_spin.setSuffix("  s")
        self.page_timeout_spin.setFixedWidth(110)
        form.addRow("Thời gian chờ tải trang:", self.page_timeout_spin)

        layout.addLayout(form)
        return group

    def _build_captcha_group(self) -> QGroupBox:
        group = QGroupBox("Xử lý CAPTCHA")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self.sound_notify_check = QCheckBox("Phát âm thanh khi phát hiện CAPTCHA")
        self.sound_notify_check.setChecked(True)
        layout.addWidget(self.sound_notify_check)

        self.tray_notify_check = QCheckBox("Hiện thông báo khi phát hiện CAPTCHA")
        self.tray_notify_check.setChecked(True)
        layout.addWidget(self.tray_notify_check)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.captcha_timeout_spin = QSpinBox()
        self.captcha_timeout_spin.setRange(1, 30)
        self.captcha_timeout_spin.setValue(3)
        self.captcha_timeout_spin.setSuffix("  phút")
        self.captcha_timeout_spin.setFixedWidth(110)
        form.addRow("Thời gian chờ giải CAPTCHA (tối đa):", self.captcha_timeout_spin)

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

    def get_prefix_list(self) -> list[str]:
        lines = self.prefix_list_edit.toPlainText().splitlines()
        return [l.strip() for l in lines if l.strip()]
