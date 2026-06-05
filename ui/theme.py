# TikTok-inspired dark color palette
PALETTE = {
    "bg_deep":    "#0a0a0f",
    "bg_main":    "#111318",
    "bg_surface": "#181b24",
    "bg_card":    "#1d2030",
    "bg_input":   "#13161e",
    "bg_raised":  "#22263a",
    "border_dim": "#1c2038",
    "border":     "#252b42",
    "border_lt":  "#323858",
    "teal":       "#25F4EE",
    "red":        "#FE2C55",
    "primary":    "#4d90f0",
    "success":    "#22c55e",
    "warning":    "#f59e0b",
    "error":      "#ef4444",
    "text":       "#dde1f0",
    "text_dim":   "#6b7794",
    "text_faint": "#2e3450",
}


def stylesheet() -> str:
    c = PALETTE
    return f"""
        QMainWindow, QDialog {{ background: {c['bg_main']}; color: {c['text']}; }}
        QWidget {{ background: {c['bg_main']}; color: {c['text']};
                   font-family: 'Segoe UI', sans-serif; font-size: 12px; }}

        /* ── Tabs ── */
        QTabWidget::pane {{ border: 1px solid {c['border']}; border-top: none; background: {c['bg_main']}; }}
        QTabBar {{ background: {c['bg_surface']}; }}
        QTabBar::tab {{
            background: {c['bg_surface']}; color: {c['text_dim']};
            border: 1px solid {c['border']}; border-bottom: none;
            padding: 7px 24px; margin-right: 2px; font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background: {c['bg_main']}; color: {c['teal']};
            border-bottom: 2px solid {c['teal']};
        }}
        QTabBar::tab:hover:!selected {{ background: {c['bg_card']}; color: {c['text']}; }}

        /* ── Buttons ── */
        QPushButton {{
            background: {c['bg_raised']}; border: 1px solid {c['border_lt']};
            border-radius: 5px; padding: 5px 14px;
            color: {c['text']}; font-size: 12px;
        }}
        QPushButton:hover {{ border-color: {c['teal']}; color: {c['teal']}; }}
        QPushButton:pressed {{ background: {c['bg_surface']}; }}
        QPushButton:disabled {{ color: {c['text_faint']}; border-color: {c['border_dim']};
                                background: {c['bg_surface']}; }}
        QPushButton#primary {{
            background: #1a3f8c; border-color: #2a5ab5; color: #b8d0ff;
        }}
        QPushButton#primary:hover {{ background: #1f4da8; border-color: {c['primary']}; color: #cce0ff; }}
        QPushButton#primary:disabled {{ background: {c['bg_surface']}; border-color: {c['border']};
                                        color: {c['text_faint']}; }}
        QPushButton#danger {{ background: #4a0e1a; border-color: #7a1828; color: #ffb3b3; }}
        QPushButton#danger:hover {{ background: #5e1222; border-color: {c['error']}; }}

        /* ── Progress bar ── */
        QProgressBar {{
            background: {c['bg_surface']}; border: 1px solid {c['border']};
            border-radius: 4px; text-align: center; color: transparent;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['teal']}, stop:1 {c['primary']});
            border-radius: 3px;
        }}

        /* ── Scrollbars ── */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{
            width: 8px; background: {c['bg_deep']}; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c['border_lt']}; border-radius: 4px; min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {c['text_dim']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            height: 6px; background: {c['bg_deep']}; margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {c['border_lt']}; border-radius: 3px; min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {c['text_dim']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

        /* ── Inputs ── */
        QLineEdit {{
            background: {c['bg_input']}; border: 1px solid {c['border']};
            border-radius: 4px; color: {c['text']}; padding: 3px 8px;
        }}
        QLineEdit:focus {{ border-color: {c['teal']}; }}
        QLineEdit:read-only {{ color: {c['text_dim']}; }}

        /* ── Form groups ── */
        QGroupBox {{
            border: 1px solid {c['border']}; border-radius: 6px;
            margin-top: 14px; padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin; left: 10px; padding: 0 4px;
            color: {c['teal']}; font-size: 11px;
        }}
        QCheckBox {{ color: {c['text']}; spacing: 8px; }}
        QCheckBox::indicator {{
            width: 16px; height: 16px;
            background: {c['bg_input']}; border: 1px solid {c['border_lt']};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{ background: {c['teal']}; border-color: {c['teal']}; }}
        QCheckBox::indicator:hover {{ border-color: {c['teal']}; }}

        QDoubleSpinBox, QSpinBox {{
            background: {c['bg_input']}; border: 1px solid {c['border']};
            border-radius: 4px; color: {c['text']}; padding: 3px 6px;
        }}
        QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {c['teal']}; }}
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
        QSpinBox::up-button, QSpinBox::down-button {{
            background: {c['bg_raised']}; border: none; border-radius: 2px; width: 16px;
        }}

        /* ── TextEdit (log panel) ── */
        QTextEdit {{
            background: {c['bg_deep']}; border: none; color: {c['text']};
            selection-background-color: #2a3060;
            font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            font-size: 11px;
        }}

        /* ── Misc ── */
        QLabel#section {{ color: {c['text_dim']}; font-size: 11px; }}
        QFrame[frameShape="4"] {{ color: {c['border']}; }}
        QFrame[frameShape="5"] {{ color: {c['border']}; }}
    """
