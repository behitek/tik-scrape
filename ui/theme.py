PALETTE = {
    "bg_deep":    "#f0f2f5",
    "bg_main":    "#ffffff",
    "bg_surface": "#f8f9fa",
    "bg_card":    "#f0f2f5",
    "bg_input":   "#ffffff",
    "bg_raised":  "#e8eaed",
    "border_dim": "#e0e3e8",
    "border":     "#d0d4dc",
    "border_lt":  "#b8bdc8",
    "teal":       "#0d9488",
    "red":        "#dc2626",
    "primary":    "#2563eb",
    "success":    "#16a34a",
    "warning":    "#d97706",
    "error":      "#dc2626",
    "text":       "#1a1d2e",
    "text_dim":   "#64748b",
    "text_faint": "#cbd5e1",
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
        QPushButton:pressed {{ background: {c['bg_card']}; }}
        QPushButton:disabled {{ color: {c['text_faint']}; border-color: {c['border_dim']};
                                background: {c['bg_surface']}; }}
        QPushButton#primary {{
            background: {c['primary']}; border-color: #1d4ed8; color: #ffffff;
        }}
        QPushButton#primary:hover {{ background: #1d4ed8; border-color: #1e40af; color: #ffffff; }}
        QPushButton#primary:disabled {{ background: {c['bg_surface']}; border-color: {c['border']};
                                        color: {c['text_faint']}; }}
        QPushButton#danger {{ background: #fee2e2; border-color: #fca5a5; color: #dc2626; }}
        QPushButton#danger:hover {{ background: #fecaca; border-color: {c['error']}; }}
        QPushButton#danger:disabled {{ background: {c['bg_surface']}; border-color: {c['border']};
                                       color: {c['text_faint']}; }}

        /* ── Progress bar ── */
        QProgressBar {{
            background: {c['bg_card']}; border: 1px solid {c['border']};
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
            width: 8px; background: {c['bg_card']}; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {c['border_lt']}; border-radius: 4px; min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {c['text_dim']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            height: 6px; background: {c['bg_card']}; margin: 0;
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
        QLineEdit:read-only {{ color: {c['text_dim']}; background: {c['bg_surface']}; }}

        QPlainTextEdit {{
            background: {c['bg_input']}; border: 1px solid {c['border']};
            border-radius: 4px; color: {c['text']}; padding: 4px 8px;
        }}
        QPlainTextEdit:focus {{ border-color: {c['teal']}; }}

        /* ── Form groups ── */
        QGroupBox {{
            border: 1px solid {c['border']}; border-radius: 6px;
            margin-top: 14px; padding-top: 10px;
            background: {c['bg_surface']};
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
            background: {c['bg_surface']}; border: 1px solid {c['border']}; color: {c['text']};
            selection-background-color: #bfdbfe;
            font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            font-size: 11px;
        }}

        /* ── Misc ── */
        QLabel#section {{ color: {c['text_dim']}; font-size: 11px; }}
        QFrame[frameShape="4"] {{ color: {c['border']}; }}
        QFrame[frameShape="5"] {{ color: {c['border']}; }}
        QMenuBar {{ background: {c['bg_surface']}; color: {c['text']};
                    border-bottom: 1px solid {c['border']}; }}
        QMenuBar::item:selected {{ background: {c['bg_card']}; }}
        QMenu {{ background: {c['bg_main']}; color: {c['text']};
                 border: 1px solid {c['border']}; }}
        QMenu::item:selected {{ background: {c['bg_card']}; }}
    """
