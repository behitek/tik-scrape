import webbrowser
from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QScrollArea, QWidget, QSizePolicy,
)

from ui.image_thumb import ImageThumb
from ui.theme import PALETTE


class UrlRowWidget(QFrame):
    def __init__(self, url: str, index: int, parent=None):
        super().__init__(parent)
        self.url = url
        self.thumbs: list[ImageThumb] = []
        self.product_id = ""
        self.product_title = ""

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background: {PALETTE['bg_card']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
                margin: 2px 4px;
            }}
            QFrame:hover {{
                border-color: {PALETTE['border_lt']};
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        outer.addLayout(self._build_top_bar(index))
        outer.addWidget(self._build_thumb_strip())

    def _build_top_bar(self, index: int) -> QHBoxLayout:
        top = QHBoxLayout()
        top.setSpacing(8)

        idx_label = QLabel(f"{index}.")
        idx_label.setFixedWidth(28)
        idx_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        idx_label.setStyleSheet(f"color: {PALETTE['text_faint']}; font-size: 11px;")
        top.addWidget(idx_label)

        # Clickable URL/title label — text refreshed by _refresh_url_label()
        self._url_label = QLabel()
        self._url_label.setOpenExternalLinks(True)
        self._url_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; }} "
            f"QLabel:hover {{ color: {PALETTE['teal']}; }}"
        )
        self._url_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._refresh_url_label()
        top.addWidget(self._url_label)

        prefix_lbl = QLabel("Tiền tố:")
        prefix_lbl.setStyleSheet(f"color: {PALETTE['text_dim']}; font-size: 11px;")
        top.addWidget(prefix_lbl)

        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("ten_san_pham")
        self.prefix_edit.setFixedWidth(150)
        top.addWidget(self.prefix_edit)

        self.status_label = QLabel("Đang chờ…")
        self.status_label.setFixedWidth(200)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet(f"color: {PALETTE['text_faint']}; font-size: 11px;")
        top.addWidget(self.status_label)

        return top

    def _build_thumb_strip(self) -> QScrollArea:
        self._thumb_container = QWidget()
        self._thumb_layout = QHBoxLayout(self._thumb_container)
        self._thumb_layout.setContentsMargins(0, 0, 0, 0)
        self._thumb_layout.setSpacing(4)
        self._thumb_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._placeholder = QLabel("Chưa có ảnh")
        self._placeholder.setStyleSheet(f"color: {PALETTE['text_faint']}; font-size: 11px;")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_layout.addWidget(self._placeholder)

        scroll = QScrollArea()
        scroll.setWidget(self._thumb_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(140)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        return scroll

    # ── Public API ──────────────────────────────────────────────────────────

    def set_status(self, text: str):
        self.status_label.setText(text)
        if text.startswith("✓"):
            color = PALETTE["success"]
        elif text.startswith("⚠"):
            color = PALETTE["warning"]
        elif "CAPTCHA" in text:
            color = PALETTE["red"]
        else:
            color = PALETTE["text_dim"]
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def set_product_info(self, product_id: str, title: str):
        self.product_id = product_id
        self.product_title = title
        self._refresh_url_label()

    def _refresh_url_label(self):
        text_source = self.product_title or self.url
        display = escape(text_source[:65] + ("…" if len(text_source) > 65 else ""))
        self._url_label.setText(
            f'<a href="{escape(self.url)}" '
            f'style="color:{PALETTE["text_dim"]}; text-decoration:none;">'
            f'{display}</a>'
        )
        tooltip_lines = []
        if self.product_title:
            tooltip_lines.append(self.product_title)
        if self.product_id:
            tooltip_lines.append(f"Product ID: {self.product_id}")
        tooltip_lines.append(self.url)
        self._url_label.setToolTip("\n".join(tooltip_lines))

    def add_images(self, pairs: list[tuple]):
        if self._placeholder:
            self._placeholder.setParent(None)
            self._placeholder = None

        for thumb_px, full_px in pairs:
            thumb = ImageThumb(thumb_px, full_px, self._thumb_container)
            self._thumb_layout.addWidget(thumb)
            self.thumbs.append(thumb)

        self._thumb_container.adjustSize()

    def select_all(self, state: bool):
        for t in self.thumbs:
            t.selected = state
            t.update()
        self.on_selection_changed()

    def on_selection_changed(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, "update_save_button"):
                parent.update_save_button()
                break
            parent = parent.parent()

    def selected_count(self) -> int:
        return sum(1 for t in self.thumbs if t.selected)
