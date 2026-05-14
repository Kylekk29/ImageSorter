DARK_THEME = {
    "bg": "#1a1b2e",
    "bg_secondary": "#242538",
    "bg_tertiary": "#2d2e44",
    "surface": "#363850",
    "text": "#cdd6f4",
    "text_secondary": "#a6adc8",
    "text_muted": "#6c7086",
    "border": "#45475a",
    "accent": "#89b4fa",
    "accent_hover": "#b4d0fb",
    "success": "#a6e3a1",
    "warning": "#f9e2af",
    "error": "#f38ba8",
    "star": "#f9e2af",
    "canvas_bg": "#11111b",
}

LIGHT_THEME = {
    "bg": "#f5f5f5",
    "bg_secondary": "#e8e8e8",
    "bg_tertiary": "#dcdcdc",
    "surface": "#ffffff",
    "text": "#1e1e2e",
    "text_secondary": "#585b70",
    "text_muted": "#9ca0b0",
    "border": "#d0d0d0",
    "accent": "#1e66f5",
    "accent_hover": "#2a7aff",
    "success": "#40a02b",
    "warning": "#df8e1d",
    "error": "#d20f39",
    "star": "#df8e1d",
    "canvas_bg": "#e0e0e0",
}

COLOR_LABEL_COLORS = {
    "red": "#e74c3c",
    "yellow": "#f1c40f",
    "green": "#2ecc71",
    "blue": "#3498db",
    "purple": "#9b59b6",
}


def get_theme(dark=True):
    return DARK_THEME if dark else LIGHT_THEME


def make_stylesheet(dark=True):
    t = get_theme(dark)
    return f"""
    /* === Global === */
    QMainWindow, QDialog, QWidget {{
        background-color: {t['bg']};
        color: {t['text']};
        font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
        font-size: 13px;
    }}

    QSplitter::handle {{
        background-color: {t['border']};
        width: 1px;
        height: 1px;
    }}

    /* === Menu Bar === */
    QMenuBar {{
        background-color: {t['bg_secondary']};
        color: {t['text']};
        border-bottom: 1px solid {t['border']};
        padding: 2px 0;
    }}
    QMenuBar::item {{
        padding: 4px 12px;
        border-radius: 4px;
        margin: 2px 2px;
    }}
    QMenuBar::item:selected {{
        background-color: {t['surface']};
    }}
    QMenu {{
        background-color: {t['bg_secondary']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {t['accent']};
        color: {t['bg']};
    }}
    QMenu::separator {{
        height: 1px;
        background: {t['border']};
        margin: 4px 8px;
    }}

    /* === Buttons === */
    QPushButton {{
        background-color: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {t['bg_tertiary']};
        border-color: {t['accent']};
    }}
    QPushButton:pressed {{
        background-color: {t['accent']};
        color: white;
    }}
    QPushButton:disabled {{
        opacity: 0.5;
        color: {t['text_muted']};
    }}

    /* === Sliders === */
    QSlider::groove:horizontal {{
        height: 4px;
        background: {t['bg_tertiary']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {t['accent']};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {t['accent_hover']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{
        background: {t['accent']};
        border-radius: 2px;
    }}

    /* === Text Edit / Text Browser === */
    QTextEdit, QTextBrowser {{
        background-color: {t['bg_secondary']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 8px;
        font-size: 12px;
    }}

    /* === Line Edit === */
    QLineEdit {{
        background-color: {t['bg_secondary']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border-color: {t['accent']};
    }}

    /* === List Widget (Filmstrip) === */
    QListWidget {{
        background-color: {t['bg']};
        border: none;
        border-top: 1px solid {t['border']};
        outline: none;
    }}
    QListWidget::item {{
        border-radius: 4px;
        margin: 2px;
    }}
    QListWidget::item:selected {{
        background-color: {t['accent']};
        border: 2px solid {t['accent']};
    }}

    /* === Scroll Bars === */
    QScrollBar:vertical {{
        background: {t['bg']};
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t['border']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['text_muted']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QScrollBar:horizontal {{
        background: {t['bg']};
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['border']};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {t['text_muted']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* === Group Box === */
    QGroupBox {{
        font-weight: 600;
        border: 1px solid {t['border']};
        border-radius: 8px;
        margin-top: 12px;
        padding: 16px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {t['text_secondary']};
    }}

    /* === Combo Box === */
    QComboBox {{
        background-color: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 6px 10px;
    }}
    QComboBox:hover {{
        border-color: {t['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t['bg_secondary']};
        border: 1px solid {t['border']};
        selection-background-color: {t['accent']};
        selection-color: white;
    }}

    /* === Label === */
    QLabel {{
        color: {t['text']};
    }}

    /* === Check Box === */
    QCheckBox {{
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 3px;
        border: 1px solid {t['border']};
        background-color: {t['bg_secondary']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {t['accent']};
        border-color: {t['accent']};
    }}

    /* === Tab Widget === */
    QTabWidget::pane {{
        border: 1px solid {t['border']};
        border-radius: 6px;
        background-color: {t['bg']};
    }}
    QTabBar::tab {{
        background-color: {t['bg_secondary']};
        color: {t['text_secondary']};
        padding: 8px 16px;
        border: 1px solid {t['border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {t['bg']};
        color: {t['accent']};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        background-color: {t['bg_tertiary']};
    }}

    /* === Tool Tip === */
    QToolTip {{
        background-color: {t['bg_secondary']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 12px;
    }}

    /* === Progress Bar === */
    QProgressBar {{
        background-color: {t['bg_tertiary']};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {t['accent']};
        border-radius: 4px;
    }}

    /* === Spin Box === */
    QSpinBox {{
        background-color: {t['surface']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QSpinBox:focus {{
        border-color: {t['accent']};
    }}

    /* === Status Bar === */
    QStatusBar {{
        background-color: {t['bg_secondary']};
        border-top: 1px solid {t['border']};
        color: {t['text_secondary']};
        font-size: 12px;
    }}
    """
