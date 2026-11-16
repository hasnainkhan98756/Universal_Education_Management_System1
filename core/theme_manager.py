from PySide6.QtWidgets import QApplication

# ── Color Tokens ────────────────────────────────────────────────────────────
LIGHT = {
    "bg_primary":      "#F3F7FA",   # Stitch page background
    "bg_surface":      "#FFFFFF",   # Clean white surface
    "bg_card":         "#FFFFFF",   # Clean white cards
    "bg_sidebar":      "#FFFFFF",   # Stitch clean white sidebar with right border
    "bg_header":       "#FFFFFF",   # Stitch top header
    "text_primary":    "#0F172A",   # Slate-900
    "text_secondary":  "#64748B",   # Slate-500
    "text_sidebar":    "#475569",   # Slate-600
    "border":          "#E2E8F0",   # Slate-200/80
    "border_light":    "#F1F5F9",   # Slate-100
    "accent":          "#2563EB",   # Blue-600
    "accent_hover":    "#1D4ED8",   # Blue-700
    "accent_light":    "#EFF6FF",   # Blue-50
    "sky":             "#0EA5E9",   # Sky-500
    "success":         "#10B981",   # Emerald-500
    "success_light":   "#ECFDF5",   # Emerald-50
    "danger":          "#EF4444",   # Rose-500
    "danger_light":    "#FFF1F2",   # Rose-50
    "warning":         "#F59E0B",   # Amber-500
    "warning_light":   "#FEF3C7",   # Amber-50
    "purple":          "#9333EA",   # Purple-600
    "purple_light":    "#FAF5FF",   # Purple-50
    "cyan":            "#06B6D4",   # Cyan-500
    "teal":            "#14B8A6",   # Teal-500
    "input_bg":        "#FFFFFF",
    "input_border":    "#CBD5E1",
    "table_hdr":       "#F8FAFC",
    "table_alt":       "#F8FAFC",
    "table_hover":     "#F1F5F9",
    "tab_bg":          "#F1F5F9",
    "tab_sel_bg":      "#FFFFFF",
    "tab_sel_color":   "#2563EB",
    "scroll_bg":       "#F1F5F9",
    "scroll_handle":   "#CBD5E1",
    "list_hover":      "#F8FAFC",
    "list_sel":        "#EFF6FF",
    "dialog_bg":       "#FFFFFF",
    "grp_bg":          "#FFFFFF",
    "shadow":          "rgba(0,0,0,0.04)",
    "border_color":    "#E2E8F0",
    "bg_hover":        "#F1F5F9",
}

DARK = {
    "bg_primary":      "#0B1224",
    "bg_surface":      "#111D35",
    "bg_card":         "#162040",
    "bg_sidebar":      "#0F172A",
    "bg_header":       "#111D35",
    "text_primary":    "#F8FAFC",
    "text_secondary":  "#94A3B8",
    "text_sidebar":    "#94A3B8",
    "border":          "#1E293B",
    "border_light":    "#1E2D4D",
    "accent":          "#3B82F6",
    "accent_hover":    "#2563EB",
    "accent_light":    "#1E3A8A",
    "sky":             "#38BDF8",
    "success":         "#10B981",
    "success_light":   "#064E3B",
    "danger":          "#EF4444",
    "danger_light":    "#7F1D1D",
    "warning":         "#F59E0B",
    "warning_light":   "#78350F",
    "purple":          "#A855F7",
    "purple_light":    "#581C87",
    "cyan":            "#06B6D4",
    "teal":            "#14B8A6",
    "input_bg":        "#1A2744",
    "input_border":    "#2D4070",
    "table_hdr":       "#162040",
    "table_alt":       "#111D35",
    "table_hover":     "#1D2E50",
    "tab_bg":          "#162040",
    "tab_sel_bg":      "#111D35",
    "tab_sel_color":   "#3B82F6",
    "scroll_bg":       "#162040",
    "scroll_handle":   "#2D4070",
    "list_hover":      "#1D2E50",
    "list_sel":        "#1E3A5F",
    "dialog_bg":       "#111D35",
    "grp_bg":          "#162040",
    "shadow":          "rgba(0,0,0,0.35)",
    "border_color":    "#1E293B",
    "bg_hover":        "#1D2E50",
}

def _qss(t: dict) -> str:
    return f"""
/* ═══ BASE ══════════════════════════════════════════════════ */
QWidget {{
    background-color: {t["bg_primary"]};
    color: {t["text_primary"]};
    font-family: 'Segoe UI', system-ui, -apple-system;
    font-size: 12px;
    selection-background-color: {t["accent"]};
    selection-color: #FFFFFF;
}}
QMainWindow {{ background-color: {t["bg_surface"]}; }}
QFrame {{ background-color: transparent; border: none; }}
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
    background-color: transparent; border: none;
}}
/* ═══ LABELS ════════════════════════════════════════════════ */
QLabel {{ background-color: transparent; color: {t["text_primary"]}; border: none; font-size: 12px; }}
QLabel#lbl_section_title {{
    color: {t["text_primary"]}; font-size: 15px; font-weight: bold; background: transparent;
}}
QLabel#lbl_subtitle {{
    color: {t["text_secondary"]}; font-size: 11px; background: transparent;
}}
/* ═══ INPUTS ════════════════════════════════════════════════ */
QLineEdit {{
    background-color: {t["input_bg"]}; color: {t["text_primary"]};
    border: 1.5px solid {t["input_border"]}; border-radius: 6px;
    padding: 3px 10px; font-size: 12px; min-height: 32px;
    selection-background-color: {t["accent"]}; selection-color: #FFFFFF;
}}
QLineEdit:focus {{ border: 2px solid {t["accent"]}; }}
QLineEdit:disabled {{ background-color: {t["border_light"]}; color: {t["text_secondary"]}; }}
QLineEdit:read-only, QLineEdit[readOnly="true"] {{ background-color: {t["border_light"]}; color: {t["text_primary"]}; }}
QLineEdit::placeholder {{ color: {t["text_secondary"]}; }}
QTextEdit, QPlainTextEdit {{
    background-color: {t["input_bg"]}; color: {t["text_primary"]};
    border: 1.5px solid {t["input_border"]}; border-radius: 6px;
    padding: 6px 10px; font-size: 12px; min-height: 48px;
    selection-background-color: {t["accent"]}; selection-color: #FFFFFF;
}}
QTextEdit:focus, QPlainTextEdit:focus {{ border: 2px solid {t["accent"]}; }}
QTextEdit:disabled, QPlainTextEdit:disabled {{ background-color: {t["border_light"]}; color: {t["text_secondary"]}; }}
QTextEdit:read-only, QTextEdit[readOnly="true"], QPlainTextEdit:read-only, QPlainTextEdit[readOnly="true"] {{ background-color: {t["border_light"]}; color: {t["text_primary"]}; }}
/* ═══ COMBOBOX ══════════════════════════════════════════════ */
QComboBox {{
    background-color: {t["input_bg"]}; color: {t["text_primary"]};
    border: 1.5px solid {t["input_border"]}; border-radius: 6px;
    padding: 3px 26px 3px 10px; min-height: 32px; font-size: 12px;
}}
QComboBox:focus {{ border: 2px solid {t["accent"]}; }}
QComboBox:disabled {{ background-color: {t["border_light"]}; color: {t["text_secondary"]}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ width: 0; height: 0; }}
QComboBox QAbstractItemView {{
    background-color: {t["dialog_bg"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 6px;
    selection-background-color: {t["accent"]}; selection-color: white; padding: 3px;
}}
/* ═══ SPINBOXES / DATE ══════════════════════════════════════ */
QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
    background-color: {t["input_bg"]}; color: {t["text_primary"]};
    border: 1.5px solid {t["input_border"]}; border-radius: 6px;
    padding: 3px 20px 3px 10px; min-height: 32px; font-size: 12px;
    selection-background-color: {t["accent"]}; selection-color: #FFFFFF;
}}
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{ border: 2px solid {t["accent"]}; }}
QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{ background-color: {t["border_light"]}; color: {t["text_secondary"]}; }}
QSpinBox:read-only, QDoubleSpinBox:read-only, QDateEdit:read-only {{ background-color: {t["border_light"]}; color: {t["text_primary"]}; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QDateEdit::up-button, QDateEdit::down-button {{
    background-color: transparent; border: none; width: 16px;
}}
/* Embedded Table Cell Inputs */
QTableWidget QSpinBox, QTableWidget QDoubleSpinBox, QTableWidget QLineEdit {{
    padding: 2px 4px; min-height: 24px; max-height: 28px; font-size: 11px; font-weight: 600;
    border: 1px solid {t["border"]}; border-radius: 4px;
}}
QTableWidget QSpinBox::up-button, QTableWidget QSpinBox::down-button,
QTableWidget QDoubleSpinBox::up-button, QTableWidget QDoubleSpinBox::down-button {{
    width: 0px; height: 0px; border: none;
}}
/* ═══ BUTTONS ═══════════════════════════════════════════════ */
QPushButton {{
    background-color: {t["input_bg"]}; color: {t["text_primary"]};
    border: 1.5px solid {t["input_border"]}; border-radius: 6px;
    padding: 4px 14px; font-weight: 600; min-height: 30px; font-size: 12px;
}}
QPushButton:hover {{
    background-color: {t["accent"]}; color: white; border: 1.5px solid {t["accent"]};
}}
QPushButton:pressed {{ background-color: {t["accent_hover"]}; color: white; }}
QPushButton:disabled {{ background-color: {t["border_light"]}; color: {t["text_secondary"]}; border: 1.5px solid {t["border"]}; }}
QPushButton#btn_primary {{
    background-color: {t["accent"]}; color: #FFFFFF; border: 1.5px solid {t["accent_hover"]}; font-weight: 700;
}}
QPushButton#btn_primary:hover {{ background-color: {t["accent_hover"]}; color: #FFFFFF; border: 1.5px solid {t["accent_hover"]}; }}
QPushButton#btn_secondary {{
    background-color: #F1F5F9; color: #0F172A; border: 1.5px solid #94A3B8; font-weight: 600;
}}
QPushButton#btn_secondary:hover {{
    background-color: #E2E8F0; color: #0F172A; border: 1.5px solid #64748B;
}}
QPushButton#btn_secondary:pressed {{
    background-color: #CBD5E1; color: #0F172A;
}}
QPushButton#btn_success {{
    background-color: {t["success"]}; color: white; border: 1.5px solid #059669; font-weight: 600;
}}
QPushButton#btn_success:hover {{ background-color: #059669; }}
QPushButton#btn_danger {{
    background-color: {t["danger"]}; color: white; border: 1.5px solid #DC2626; font-weight: 600;
}}
QPushButton#btn_danger:hover {{ background-color: #DC2626; }}
QPushButton#btn_warning {{
    background-color: {t["warning"]}; color: white; border: 1.5px solid #D97706; font-weight: 600;
}}
QPushButton#btn_warning:hover {{ background-color: #D97706; }}
QPushButton#btn_purple {{
    background-color: {t["purple"]}; color: white; border: 1.5px solid #7C3AED; font-weight: 600;
}}
QPushButton#btn_purple:hover {{ background-color: #7C3AED; }}
QPushButton#btn_compact {{
    padding: 2px 8px; min-height: 24px; font-size: 11px; border-radius: 4px;
}}
/* ═══ TABLES ════════════════════════════════════════════════ */
QTableWidget {{
    background-color: {t["bg_card"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 8px;
    gridline-color: {t["border"]}; font-size: 12px;
    selection-background-color: {t["accent"]}; selection-color: white;
    alternate-background-color: {t["table_alt"]};
}}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid {t["border"]}; }}
QTableWidget::item:hover {{ background-color: {t["table_hover"]}; color: {t["text_primary"]}; }}
QTableWidget::item:selected {{ background-color: {t["accent"]}; color: white; }}
QHeaderView {{ background-color: transparent; border: none; }}
QHeaderView::section {{
    background-color: {t["table_hdr"]}; color: {t["text_secondary"]};
    font-weight: 700; font-size: 11px; padding: 6px 8px;
    border: none; border-bottom: 1.5px solid {t["border"]};
}}
QHeaderView::section:vertical {{
    min-height: 28px;
}}
/* ═══ TAB WIDGET ════════════════════════════════════════════ */
QTabWidget::pane {{
    background-color: {t["bg_card"]}; border: 1px solid {t["border"]};
    border-radius: 8px; margin-top: -1px;
}}
QTabBar {{ background-color: transparent; }}
QTabBar::tab {{
    background-color: {t["tab_bg"]}; color: {t["text_secondary"]};
    padding: 6px 14px; border-top-left-radius: 6px; border-top-right-radius: 6px;
    margin-right: 2px; font-weight: 600; font-size: 12px; min-height: 28px;
}}
QTabBar::tab:selected {{
    background-color: {t["tab_sel_bg"]}; color: {t["tab_sel_color"]};
    border-bottom: 3px solid {t["accent"]};
}}
QTabBar::tab:hover:!selected {{
    background-color: {t["list_hover"]}; color: {t["text_primary"]};
}}
/* ═══ LIST WIDGET ═══════════════════════════════════════════ */
QListWidget {{
    background-color: {t["bg_card"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 10px; padding: 6px; font-size: 13px;
}}
QListWidget::item {{ padding: 10px 12px; border-radius: 6px; margin-bottom: 2px; }}
QListWidget::item:hover {{ background-color: {t["list_hover"]}; }}
QListWidget::item:selected {{ background-color: {t["list_sel"]}; color: {t["accent"]}; font-weight: bold; }}
/* ═══ TREE WIDGET ═══════════════════════════════════════════ */
QTreeView, QTreeWidget {{
    background-color: {t["bg_card"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 8px;
    alternate-background-color: {t["table_alt"]}; font-size: 13px;
}}
QTreeView::item, QTreeWidget::item {{
    padding: 6px 4px; border-radius: 4px;
}}
QTreeView::item:hover, QTreeWidget::item:hover {{ background-color: {t["list_hover"]}; }}
QTreeView::item:selected, QTreeWidget::item:selected {{
    background-color: {t["accent"]}; color: white;
}}
/* ═══ SCROLLBARS ════════════════════════════════════════════ */
QScrollBar:vertical {{
    background-color: {t["scroll_bg"]}; width: 8px; border-radius: 4px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {t["scroll_handle"]}; border-radius: 4px; min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{ background-color: {t["accent"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; background: none; }}
QScrollBar:horizontal {{
    background-color: {t["scroll_bg"]}; height: 8px; border-radius: 4px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {t["scroll_handle"]}; border-radius: 4px; min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: {t["accent"]}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; background: none; }}
/* ═══ GROUP BOX ═════════════════════════════════════════════ */
QGroupBox {{
    background-color: {t["grp_bg"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 8px;
    margin-top: 12px; padding: 10px; font-weight: bold; font-size: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 2px 8px; color: {t["accent"]}; background-color: {t["grp_bg"]}; border-radius: 4px;
}}
/* ═══ CHECKBOX / RADIO ══════════════════════════════════════ */
QCheckBox {{ color: {t["text_primary"]}; spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 2px solid {t["input_border"]};
    border-radius: 4px; background-color: {t["input_bg"]};
}}
QCheckBox::indicator:checked {{ background-color: {t["accent"]}; border: 2px solid {t["accent"]}; }}
QRadioButton {{ color: {t["text_primary"]}; spacing: 8px; background: transparent; }}
QRadioButton::indicator {{
    width: 16px; height: 16px; border: 2px solid {t["input_border"]};
    border-radius: 8px; background-color: {t["input_bg"]};
}}
QRadioButton::indicator:checked {{ background-color: {t["accent"]}; border: 2px solid {t["accent"]}; }}
/* ═══ PROGRESS BAR ══════════════════════════════════════════ */
QProgressBar {{
    background-color: {t["border"]}; border-radius: 6px; height: 10px;
    text-align: center; color: {t["text_primary"]}; border: none; font-size: 10px;
}}
QProgressBar::chunk {{ background-color: {t["accent"]}; border-radius: 6px; }}
/* ═══ TOOLTIP ════════════════════════════════════════════════ */
QToolTip {{
    background-color: {t["dialog_bg"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 6px;
    padding: 4px 8px; font-size: 11px;
}}
/* ═══ DIALOGS ════════════════════════════════════════════════ */
QDialog {{ background-color: {t["dialog_bg"]}; color: {t["text_primary"]}; }}
QMessageBox {{ background-color: {t["dialog_bg"]}; color: {t["text_primary"]}; }}
QMessageBox QLabel {{ color: {t["text_primary"]}; background: transparent; }}
QDialogButtonBox QPushButton {{ min-width: 75px; padding: 4px 14px; border-radius: 6px; font-weight: 600; font-size: 12px; }}
/* ═══ MENU ══════════════════════════════════════════════════ */
QMenu {{
    background-color: {t["dialog_bg"]}; color: {t["text_primary"]};
    border: 1px solid {t["border"]}; border-radius: 6px; padding: 3px;
}}
QMenu::item {{ padding: 5px 16px; border-radius: 4px; font-size: 12px; }}
QMenu::item:selected {{ background-color: {t["accent"]}; color: white; }}
QMenu::separator {{ height: 1px; background-color: {t["border"]}; margin: 4px 10px; }}
/* ═══ CALENDAR ══════════════════════════════════════════════ */
QCalendarWidget QAbstractItemView {{
    background-color: {t["dialog_bg"]}; color: {t["text_primary"]};
    selection-background-color: {t["accent"]}; selection-color: white;
}}
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {t["bg_card"]}; color: {t["text_primary"]};
    min-height: 42px;
}}
QCalendarWidget QTableView {{
    alternate-background-color: {t["table_alt"]};
    selection-background-color: {t["accent"]};
    selection-color: white;
}}
QCalendarWidget QTableView::item {{
    padding: 6px;
}}
QCalendarWidget QToolButton {{
    background-color: transparent; color: {t["text_primary"]};
    border: none; padding: 6px 10px; border-radius: 6px; font-weight: bold;
}}
QCalendarWidget QToolButton:hover {{ background-color: {t["list_hover"]}; }}
/* ═══ STACKED WIDGET ════════════════════════════════════════ */
QStackedWidget {{ background-color: {t["bg_primary"]}; }}
QStackedWidget > QWidget {{ background-color: {t["bg_primary"]}; }}
QFrame#dash_card, QFrame#stat_card, QFrame[card="true"] {{
    background-color: {t["bg_card"]};
    border: 1px solid {t["border"]};
    border-radius: 16px;
}}
/* ═══ TOOLBAR / STATUS ══════════════════════════════════════ */
QToolBar {{ background-color: {t["bg_surface"]}; border: none; padding: 4px; }}
QStatusBar {{ background-color: {t["bg_surface"]}; color: {t["text_secondary"]}; font-size: 11px; }}
QSplitter::handle {{ background-color: {t["border"]}; }}
"""

class ThemeManager:
    _mode = "Light"

    @classmethod
    def _normalize(cls, mode: str = None) -> str:
        return "Light"

    @classmethod
    def tokens(cls, mode: str = None) -> dict:
        return LIGHT

    @classmethod
    def stylesheet(cls, mode: str = None) -> str:
        return _qss(LIGHT)

    _applied_stylesheet = None

    @classmethod
    def apply(cls, mode: str = "Light"):
        cls._mode = "Light"
        app = QApplication.instance()
        if app:
            sheet = cls.stylesheet("Light")
            if cls._applied_stylesheet != sheet:
                app.setStyleSheet(sheet)
                cls._applied_stylesheet = sheet

    @classmethod
    def current(cls) -> str:
        return "Light"

    @classmethod
    def is_dark(cls) -> bool:
        return False

    @classmethod
    def color(cls, key: str, mode: str = None) -> str:
        """Get a single color token for programmatic use (e.g. chart colors)."""
        return LIGHT.get(key, "#000000")
