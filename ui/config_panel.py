from PySide6.QtCore import Qt, QSettings, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QCheckBox, QDoubleSpinBox, QSpinBox,
    QLabel, QScrollArea, QPlainTextEdit, QLineEdit, QPushButton,
)

from scraper.captcha_solver import CaptchaSolver, DEFAULT_BASE_URL
from ui.theme import PALETTE

_SETTING_API_KEY = "captcha/api_key"
_SETTING_AUTO_SOLVE = "captcha/auto_solve"


class _KeyTestWorker(QThread):
    """Checks an API key against the resolver without freezing the UI."""

    result = Signal(bool, str)

    def __init__(self, api_key: str, parent=None):
        super().__init__(parent)
        self._api_key = api_key

    def run(self):
        try:
            balance = CaptchaSolver(self._api_key).get_balance()
            self.result.emit(True, f"✓ Kết nối thành công — số dư: {balance:g}")
        except Exception as e:
            self.result.emit(False, f"✗ {e}")

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
        self._key_test_worker: _KeyTestWorker | None = None
        self._build_ui()
        self._load_settings()

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

        self.auto_solve_check = QCheckBox("Tự động giải CAPTCHA bằng API CaptchaSolve")
        self.auto_solve_check.setChecked(True)
        self.auto_solve_check.setToolTip(
            "Gửi ảnh CAPTCHA lên captcha.kimidev.net để giải tự động.\n"
            "Cần API key bên dưới. Nếu giải không được, app sẽ chờ bạn giải tay."
        )
        self.auto_solve_check.toggled.connect(self._on_settings_changed)
        layout.addWidget(self.auto_solve_check)

        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        key_row.addWidget(QLabel("API key:"))

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("sk_…")
        self.api_key_edit.setClearButtonEnabled(True)
        self.api_key_edit.editingFinished.connect(self._on_settings_changed)
        key_row.addWidget(self.api_key_edit, 1)

        self.show_key_btn = QPushButton("Hiện")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.setFixedWidth(58)
        self.show_key_btn.toggled.connect(self._on_toggle_key_visibility)
        key_row.addWidget(self.show_key_btn)

        self.test_key_btn = QPushButton("Kiểm tra")
        self.test_key_btn.setFixedWidth(80)
        self.test_key_btn.clicked.connect(self._on_test_key)
        key_row.addWidget(self.test_key_btn)

        layout.addLayout(key_row)

        self.key_status_label = QLabel()
        self.key_status_label.setWordWrap(True)
        self.key_status_label.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        layout.addWidget(self.key_status_label)

        note = QLabel(
            'API key lưu trên máy này. Lấy key tại '
            '<a href="https://captcha.kimidev.net/dashboard/services/captcha">'
            'captcha.kimidev.net</a> → mục API Key.'
        )
        note.setOpenExternalLinks(True)
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        layout.addWidget(note)

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

    # ── CAPTCHA API key persistence ─────────────────────────────────────────

    def _load_settings(self):
        settings = QSettings()
        api_key = settings.value(_SETTING_API_KEY, "", type=str)
        auto_solve = settings.value(_SETTING_AUTO_SOLVE, True, type=bool)
        self.api_key_edit.setText(api_key)
        self.auto_solve_check.setChecked(auto_solve)
        self._update_key_status()

    def _on_settings_changed(self):
        self._save_settings()
        self._update_key_status()

    def _save_settings(self):
        settings = QSettings()
        settings.setValue(_SETTING_API_KEY, self.api_key_edit.text().strip())
        settings.setValue(_SETTING_AUTO_SOLVE, self.auto_solve_check.isChecked())
        settings.sync()

    def _update_key_status(self):
        if self._key_test_worker and self._key_test_worker.isRunning():
            return
        if self.api_key_edit.text().strip():
            self.key_status_label.setText(
                "Đã lưu API key — CAPTCHA sẽ được giải tự động khi có thể."
            )
        else:
            self.key_status_label.setText(
                "Chưa có API key — CAPTCHA sẽ phải giải tay trong cửa sổ trình duyệt."
            )

    def _on_toggle_key_visibility(self, shown: bool):
        self.api_key_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
        )
        self.show_key_btn.setText("Ẩn" if shown else "Hiện")

    def _on_test_key(self):
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            self.key_status_label.setText("⚠ Hãy nhập API key trước khi kiểm tra.")
            return
        self._save_settings()
        self.test_key_btn.setEnabled(False)
        self.key_status_label.setText("Đang kiểm tra API key…")

        worker = _KeyTestWorker(api_key, self)
        worker.result.connect(self._on_key_test_result)
        worker.finished.connect(worker.deleteLater)
        self._key_test_worker = worker
        worker.start()

    def _on_key_test_result(self, ok: bool, message: str):
        self.test_key_btn.setEnabled(True)
        color = PALETTE["success"] if ok else PALETTE["error"]
        self.key_status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.key_status_label.setText(message)
        self._key_test_worker = None

    def get_config(self) -> dict:
        self._save_settings()
        return {
            "human_sim": self.human_sim_check.isChecked(),
            "min_delay": self.min_delay_spin.value(),
            "max_delay": self.max_delay_spin.value(),
            "page_timeout": self.page_timeout_spin.value(),
            "sound_notify": self.sound_notify_check.isChecked(),
            "tray_notify": self.tray_notify_check.isChecked(),
            "captcha_timeout_ms": self.captcha_timeout_spin.value() * 60 * 1000,
            "captcha_api_key": self.api_key_edit.text().strip(),
            "captcha_auto_solve": self.auto_solve_check.isChecked(),
            "captcha_base_url": DEFAULT_BASE_URL,
        }

    def get_prefix_list(self) -> list[str]:
        lines = self.prefix_list_edit.toPlainText().splitlines()
        return [l.strip() for l in lines if l.strip()]
