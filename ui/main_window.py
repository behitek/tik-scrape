import logging
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog,
    QScrollArea, QLineEdit, QMessageBox, QTabWidget,
    QSystemTrayIcon, QStyle, QPlainTextEdit,
)

from ui.url_row_widget import UrlRowWidget
from ui.config_panel import ConfigPanel
from ui.log_panel import LogPanel, QtLogHandler
from ui.theme import PALETTE, stylesheet
from scraper.worker import CrawlWorker
from scraper.csv_export import write_products_csv


def _resource(rel: str) -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base, rel)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Công cụ tải ảnh TikTok")
        self.setMinimumSize(1000, 700)
        self.resize(1280, 860)
        self._rows: list[UrlRowWidget] = []
        self._worker: CrawlWorker | None = None
        self._dest_folder = os.path.expanduser("~/Desktop/tiktok_images")

        icon_path = _resource(os.path.join("assets", "icon.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(stylesheet())
        self._setup_logging()
        self._setup_tray()
        self._build_ui()
        self._build_menu()

    # ── Menu bar ────────────────────────────────────────────────────────────

    def _build_menu(self):
        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("Trợ giúp")
        about_action = QAction("Giới thiệu", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _on_about(self):
        from ui.about_dialog import AboutDialog
        AboutDialog(self).exec()

    # ── Logging setup ───────────────────────────────────────────────────────

    def _setup_logging(self):
        self._log_handler = QtLogHandler()
        self._log_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self._log_handler)

    # ── System tray ─────────────────────────────────────────────────────────

    def _setup_tray(self):
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Công cụ tải ảnh TikTok")
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(self._build_scraper_tab(), "  Thu thập  ")
        tabs.addTab(self._build_settings_tab(), "  Cài đặt  ")
        root.addWidget(tabs)

        self._log_handler.log_emitted.connect(self._log_panel.append_log)

    def _build_scraper_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 10, 12, 8)
        layout.setSpacing(8)

        layout.addLayout(self._build_url_input())
        layout.addLayout(self._build_action_bar())
        layout.addWidget(self._build_rows_area(), stretch=1)
        layout.addLayout(self._build_save_bar())

        self._log_panel = LogPanel()
        layout.addWidget(self._log_panel)

        return tab

    def _build_settings_tab(self) -> QWidget:
        self._config_panel = ConfigPanel()
        return self._config_panel

    def _build_url_input(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(4)

        lbl = QLabel("Dán danh sách URL (mỗi URL một dòng):")
        lbl.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        box.addWidget(lbl)

        self._url_input = QPlainTextEdit()
        self._url_input.setPlaceholderText(
            "https://vt.tiktok.com/...\nhttps://vt.tiktok.com/...\n..."
        )
        self._url_input.setFixedHeight(110)
        self._url_input.setFont(QFont("Consolas", 10))
        box.addWidget(self._url_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        clear_btn = QPushButton("Xóa danh sách")
        clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(clear_btn)

        self._start_btn = QPushButton("Bắt đầu  ▶")
        self._start_btn.setObjectName("primary")
        self._start_btn.clicked.connect(self._on_start)
        btn_row.addWidget(self._start_btn)

        box.addLayout(btn_row)
        return box

    def _build_action_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self._stop_btn = QPushButton("Dừng")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        bar.addWidget(self._stop_btn)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(16)
        self._progress.setMinimum(0)
        self._progress.setMaximum(1)
        self._progress.setValue(0)
        bar.addWidget(self._progress, stretch=1)

        self._progress_label = QLabel("0 / 0")
        self._progress_label.setFixedWidth(64)
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        bar.addWidget(self._progress_label)

        return bar

    def _build_rows_area(self) -> QScrollArea:
        self._rows_widget = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_widget)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._rows_widget)
        scroll.setWidgetResizable(True)
        return scroll

    def _build_save_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)

        sel_all = QPushButton("Chọn tất cả")
        sel_all.clicked.connect(lambda: self._select_all(True))
        bar.addWidget(sel_all)

        desel_all = QPushButton("Bỏ chọn")
        desel_all.clicked.connect(lambda: self._select_all(False))
        bar.addWidget(desel_all)

        bar.addStretch()

        dest_lbl = QLabel("Lưu vào:")
        dest_lbl.setObjectName("section")
        bar.addWidget(dest_lbl)

        self._dest_edit = QLineEdit(self._dest_folder)
        self._dest_edit.setReadOnly(True)
        self._dest_edit.setMinimumWidth(280)
        bar.addWidget(self._dest_edit)

        browse_btn = QPushButton("Chọn thư mục…")
        browse_btn.clicked.connect(self._on_browse_dest)
        bar.addWidget(browse_btn)

        self._save_btn = QPushButton("Lưu đã chọn (0)")
        self._save_btn.setObjectName("primary")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        bar.addWidget(self._save_btn)

        return bar

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _add_row(self, url: str, index: int, prefix: str = ""):
        row = UrlRowWidget(url, index, self._rows_widget)
        if prefix:
            row.prefix_edit.setText(prefix)
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        self._rows.append(row)

    def _clear_rows(self):
        for row in self._rows:
            row.setParent(None)
        self._rows.clear()

    # ── Slots ────────────────────────────────────────────────────────────────

    def _on_clear(self):
        self._url_input.clear()
        self._clear_rows()
        self._progress.setValue(0)
        self._progress_label.setText("0 / 0")

    def _on_start(self):
        text = self._url_input.toPlainText()
        urls = [l.strip() for l in text.splitlines() if l.strip().startswith("http")]
        if not urls:
            return
        prefixes = self._config_panel.get_prefix_list()
        self._clear_rows()
        for i, url in enumerate(urls, 1):
            prefix = prefixes[(i - 1) % len(prefixes)] if prefixes else ""
            self._add_row(url, i, prefix)
        self._progress.setMaximum(len(urls))
        self._progress.setValue(0)
        self._progress_label.setText(f"0 / {len(urls)}")
        logger.info("Đã tải %d URL", len(urls))
        self._on_crawl()

    def _on_crawl(self):
        if not self._rows:
            return
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress.setValue(0)
        self._progress.setMaximum(len(self._rows))

        for row in self._rows:
            row.set_status("Đang chờ…")

        config = self._config_panel.get_config()
        logger.info(
            "Bắt đầu thu thập: %d URL, human_sim=%s, delay=%.1f–%.1fs",
            len(self._rows), config["human_sim"], config["min_delay"], config["max_delay"],
        )

        urls = [row.url for row in self._rows]
        self._worker = CrawlWorker(urls, config=config)
        self._worker.images_ready.connect(self._on_images_ready)
        self._worker.status_update.connect(self._on_status_update)
        self._worker.progress.connect(self._on_progress)
        self._worker.captcha_detected.connect(self._on_captcha_detected)
        self._worker.product_info.connect(self._on_product_info)
        self._worker.finished.connect(self._on_crawl_finished)
        self._worker.start()

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
        self._stop_btn.setEnabled(False)

    def _on_images_ready(self, url: str, pairs: list):
        for row in self._rows:
            if row.url == url:
                row.add_images(pairs)
                break
        self.update_save_button()

    def _on_status_update(self, url: str, text: str):
        for row in self._rows:
            if row.url == url:
                row.set_status(text)
                break

    def _on_product_info(self, url: str, product_id: str, product_title: str):
        for row in self._rows:
            if row.url == url:
                row.set_product_info(product_id, product_title)
                break

    def _on_progress(self, done: int, total: int):
        self._progress.setValue(done)
        self._progress_label.setText(f"{done} / {total}")

    def _on_captcha_detected(self, url: str):
        config = self._config_panel.get_config()

        if config.get("sound_notify"):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

        if config.get("tray_notify") and QSystemTrayIcon.isSystemTrayAvailable():
            short_url = url[:70] + ("…" if len(url) > 70 else "")
            self._tray.showMessage(
                "Phát hiện CAPTCHA!",
                f"Vui lòng giải CAPTCHA trong cửa sổ trình duyệt.\n{short_url}",
                QSystemTrayIcon.MessageIcon.Warning,
                10_000,
            )

        logger.warning("Phát hiện CAPTCHA — chờ người dùng giải: %s", url)

    def _on_crawl_finished(self):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        total_images = sum(len(row.thumbs) for row in self._rows)
        logger.info("Đã xử lý tất cả URL — tổng %d ảnh", total_images)

        config = self._config_panel.get_config()

        if config.get("sound_notify"):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

        if config.get("tray_notify") and QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.showMessage(
                "Thu thập xong!",
                f"Đã xử lý {len(self._rows)} URL, tìm được {total_images} ảnh.",
                QSystemTrayIcon.MessageIcon.Information,
                8_000,
            )

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu", self._dest_folder)
        if folder:
            self._dest_folder = folder
            self._dest_edit.setText(folder)

    def _select_all(self, state: bool):
        for row in self._rows:
            row.select_all(state)
        self.update_save_button()

    def update_save_button(self):
        total = sum(row.selected_count() for row in self._rows)
        self._save_btn.setText(f"Lưu đã chọn ({total})")
        self._save_btn.setEnabled(total > 0)

    def _on_save(self):
        dest = self._dest_edit.text().strip() or self._dest_folder
        os.makedirs(dest, exist_ok=True)

        saved = 0
        errors = 0
        csv_entries = []
        for row in self._rows:
            selected = [t for t in row.thumbs if t.selected]
            saved_filenames = []
            prefix = row.prefix_edit.text().strip() or "image"
            for i, thumb in enumerate(selected, 1):
                filename = f"{prefix}_{i:03d}.jpg"
                filepath = os.path.join(dest, filename)
                stem, ext = os.path.splitext(filepath)
                counter = 1
                while os.path.exists(filepath):
                    filepath = f"{stem}_{counter}{ext}"
                    counter += 1
                ok = thumb.full_pixmap.save(filepath, "JPEG", 92)
                if ok:
                    saved += 1
                    saved_filenames.append(os.path.basename(filepath))
                else:
                    errors += 1
            csv_entries.append((row.product_id, row.product_title, saved_filenames))

        logger.info("Đã lưu %d ảnh vào %s (%d lỗi)", saved, dest, errors)

        csv_error = ""
        try:
            write_products_csv(dest, csv_entries)
        except Exception as e:
            csv_error = str(e)
            logger.error("Không thể ghi products.csv: %s", e)

        msg = f"Đã lưu {saved} ảnh vào:\n{dest}"
        if errors:
            msg += f"\n\n⚠ {errors} ảnh không thể lưu."
        if csv_error:
            msg += f"\n\n⚠ Không thể ghi products.csv: {csv_error}"

        box = QMessageBox(self)
        box.setWindowTitle("Lưu xong")
        box.setText(msg)
        box.setIcon(QMessageBox.Icon.Information)
        open_btn = box.addButton("Mở thư mục", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() == open_btn:
            os.startfile(dest)
