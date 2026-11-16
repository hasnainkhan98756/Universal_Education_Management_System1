"""
ui/components/stitch_widgets.py
===============================
Standardized Google Stitch UI Component Library for School Management System.
All components are theme-aware, 100% vector SVG based (zero emojis), and adhere
strictly to the Stitch design specifications.
"""

from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QHBoxLayout,
    QVBoxLayout, QTableWidget, QTabWidget, QHeaderView, QSizePolicy,
    QAbstractItemView, QMenu
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QIcon, QFont, QColor

from core.icon_manager import IconManager
from core.theme_manager import ThemeManager


class ModernCard(QFrame):
    """Standard Stitch Card container: White surface, 14px radius, 1px subtle border."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("StitchModernCard")
        self.setStyleSheet("""
            QFrame#StitchModernCard {
                background-color: #FFFFFF;
                border-radius: 14px;
                border: 1px solid #E2E8F0;
            }
        """)


class PageHeader(QWidget):
    """
    Standard Stitch Top Header for any Module/Tab.
    Features:
      - Vector icon inside a 42x42 soft-tinted circular capsule
      - Bold 20px title + 12px subtitle
      - Right-aligned action toolbar for primary/secondary buttons
    """
    def __init__(
        self,
        title: str,
        subtitle: str = "",
        icon_name: str = "layout-dashboard",
        icon_color: str = "#2563EB",
        badge_bg: str = "#EFF6FF",
        parent: Optional[QWidget] = None,
        actions: Optional[List[QWidget]] = None
    ):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setStyleSheet("background-color: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(14)

        # Vector Icon in rounded capsule
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(42, 42)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                border-radius: 12px;
                border: 1px solid {icon_color}22;
            }}
        """)
        pixmap = IconManager.get_pixmap(icon_name, color=icon_color, size=22)
        self.icon_badge.setPixmap(pixmap)
        layout.addWidget(self.icon_badge)

        # Title & Subtitle block
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("""
            font-size: 20px;
            font-weight: 800;
            color: #0F172A;
            background: transparent;
        """)
        text_layout.addWidget(self.lbl_title)

        if subtitle:
            self.lbl_subtitle = QLabel(subtitle)
            self.lbl_subtitle.setStyleSheet("""
                font-size: 12px;
                color: #64748B;
                background: transparent;
            """)
            text_layout.addWidget(self.lbl_subtitle)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Right-aligned actions container
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(10)
        layout.addLayout(self.actions_layout)

        if actions:
            for act in actions:
                self.actions_layout.addWidget(act)

    def add_action_button(self, button: QWidget):
        """Add a button or widget to the right side of the header."""
        self.actions_layout.addWidget(button)

    add_action_widget = add_action_button


class ModernButton(QPushButton):
    """
    Standard Stitch Button with vector SVG icon and consistent padding/colors.
    Variants: 'primary', 'secondary', 'success', 'danger', 'warning'
    """
    def __init__(
        self,
        text: str,
        icon_name: str = "",
        variant: str = "secondary",
        parent: Optional[QWidget] = None
    ):
        super().__init__(text, parent)
        self.variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)

        color_map = {
            "primary": ("#FFFFFF", "#2563EB", "#1D4ED8", "1.5px solid #1D4ED8"),
            "secondary": ("#0F172A", "#F1F5F9", "#E2E8F0", "1.5px solid #94A3B8"),
            "success": ("#FFFFFF", "#10B981", "#059669", "1.5px solid #059669"),
            "danger": ("#FFFFFF", "#EF4444", "#DC2626", "1.5px solid #DC2626"),
            "warning": ("#FFFFFF", "#F59E0B", "#D97706", "1.5px solid #D97706"),
        }

        fg, bg, hover_bg, border = color_map.get(variant, color_map["secondary"])

        if icon_name:
            icon_col = fg if variant != "secondary" else "#0F172A"
            self.setIcon(IconManager.get(icon_name, color=icon_col, size=16))

        pad = "0px" if not text.strip() else "4px 12px"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: {border};
                border-radius: 6px;
                padding: {pad};
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
            QPushButton:pressed {{
                opacity: 0.9;
            }}
            QPushButton:disabled {{
                background-color: #E2E8F0;
                color: #94A3B8;
                border: 1px solid #CBD5E1;
            }}
        """)


class TableActionButton(QPushButton):
    """
    Compact icon button designed specifically for table action columns in Stitch design.
    Zero text clipping, zero vertical overflow.
    Variants: 'edit', 'delete', 'danger', 'view', 'success', 'secondary'
    """
    def __init__(
        self,
        icon_name: str,
        variant: str = "secondary",
        tooltip: str = "",
        size: int = 30,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(size, size)
        if tooltip:
            self.setToolTip(tooltip)

        styles = {
            "edit": {
                "icon": "#2563EB",
                "bg": "#EFF6FF",
                "border": "#93C5FD",
                "hover_bg": "#DBEAFE",
                "hover_border": "#60A5FA",
                "pressed_bg": "#BFDBFE"
            },
            "delete": {
                "icon": "#DC2626",
                "bg": "#FEF2F2",
                "border": "#FCA5A5",
                "hover_bg": "#FEE2E2",
                "hover_border": "#F87171",
                "pressed_bg": "#FECACA"
            },
            "danger": {
                "icon": "#DC2626",
                "bg": "#FEF2F2",
                "border": "#FCA5A5",
                "hover_bg": "#FEE2E2",
                "hover_border": "#F87171",
                "pressed_bg": "#FECACA"
            },
            "view": {
                "icon": "#0D9488",
                "bg": "#F0FDFA",
                "border": "#5EEAD4",
                "hover_bg": "#CCFBF1",
                "hover_border": "#2DD4BF",
                "pressed_bg": "#99F6E4"
            },
            "success": {
                "icon": "#16A34A",
                "bg": "#F0FDF4",
                "border": "#86EFAC",
                "hover_bg": "#DCFCE7",
                "hover_border": "#4ADE80",
                "pressed_bg": "#BBF7D0"
            },
            "secondary": {
                "icon": "#0F172A",
                "bg": "#F1F5F9",
                "border": "#94A3B8",
                "hover_bg": "#E2E8F0",
                "hover_border": "#64748B",
                "pressed_bg": "#CBD5E1"
            }
        }

        conf = styles.get(variant, styles["secondary"])
        icon_size = max(14, size - 16)
        self.setIcon(IconManager.get(icon_name, color=conf["icon"], size=icon_size))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {conf["bg"]};
                border: 1.5px solid {conf["border"]};
                border-radius: 6px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {conf["hover_bg"]};
                border: 1.5px solid {conf["hover_border"]};
            }}
            QPushButton:pressed {{
                background-color: {conf["pressed_bg"]};
            }}
        """)


class TableTextButton(QPushButton):
    """
    Compact text button (with optional icon) designed for table cells.
    Maintains clean 28-30px height with crisp high-contrast border and background.
    """
    def __init__(
        self,
        text: str,
        icon_name: str = "",
        variant: str = "secondary",
        height: int = 30,
        parent: Optional[QWidget] = None
    ):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(height)

        styles = {
            "danger": ("#FFFFFF", "#EF4444", "#DC2626", "#DC2626", "#B91C1C"),
            "delete": ("#FFFFFF", "#EF4444", "#DC2626", "#DC2626", "#B91C1C"),
            "success": ("#FFFFFF", "#10B981", "#059669", "#059669", "#047857"),
            "primary": ("#FFFFFF", "#2563EB", "#1D4ED8", "#1D4ED8", "#1E40AF"),
            "secondary": ("#0F172A", "#F1F5F9", "#94A3B8", "#E2E8F0", "#64748B"),
            "info": ("#1D4ED8", "#EFF6FF", "#93C5FD", "#DBEAFE", "#60A5FA"),
            "edit": ("#1D4ED8", "#EFF6FF", "#93C5FD", "#DBEAFE", "#60A5FA"),
            "warning": ("#FFFFFF", "#F59E0B", "#D97706", "#D97706", "#B45309"),
        }
        fg, bg, border, hover_bg, hover_border = styles.get(variant, styles["secondary"])

        if icon_name:
            self.setIcon(IconManager.get(icon_name, color=fg, size=14))

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: 1.5px solid {border};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11.5px;
                font-weight: 700;
                line-height: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1.5px solid {hover_border};
            }}
            QPushButton:pressed {{
                background-color: {hover_border};
            }}
        """)


class TableDropdownButton(TableTextButton):
    """
    Compact action button with an instant popup menu on click.
    Consolidates multiple actions (such as A4 and Thermal slip/receipt generation)
    under a single, space-saving button to eliminate table column overcrowding.
    """
    def __init__(
        self,
        text: str,
        icon_name: str = "printer",
        variant: str = "secondary",
        height: int = 28,
        parent: Optional[QWidget] = None
    ):
        display_text = f"{text} ▾" if not (text.endswith(" ▾") or text.endswith(" ▼")) else text
        super().__init__(display_text, icon_name=icon_name, variant=variant, height=height, parent=parent)
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px;
                font-size: 12px;
                font-weight: 600;
                color: #1E293B;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #EFF6FF;
                color: #2563EB;
            }
            QMenu::separator {
                height: 1px;
                background: #E2E8F0;
                margin: 4px 8px;
            }
        """)
        self.clicked.connect(self.show_popup_menu)

    def add_menu_action(self, text: str, callback, icon_name: str = "", icon_color: str = "#2563EB"):
        if icon_name:
            icon = IconManager.get(icon_name, color=icon_color, size=14)
            action = self.menu.addAction(icon, text)
        else:
            action = self.menu.addAction(text)
        action.triggered.connect(callback)
        return action

    def show_popup_menu(self):
        self.menu.exec(self.mapToGlobal(QPoint(0, self.height() + 2)))


def create_table_actions_cell(buttons: list[QWidget]) -> QWidget:
    """
    Returns a transparent table cell container for action buttons,
    ensuring centered alignment, zero margins, and no clipped borders.
    """
    cell_w = QWidget()
    cell_w.setObjectName("table_actions_cell")
    cell_w.setStyleSheet("QWidget#table_actions_cell { background: transparent; border: none; }")
    layout = QHBoxLayout(cell_w)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    for btn in buttons:
        layout.addWidget(btn)
    return cell_w


class MetricCard(ModernCard):
    """
    Standard Stitch KPI / Summary Metric Card.
    Matches the Dashboard Summary Cards layout.
    """
    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        icon_name: str = "bar-chart-2",
        icon_color: str = "#2563EB",
        badge_bg: str = "#EFF6FF",
        parent: Optional[QWidget] = None,
        accent_color: Optional[str] = None
    ):
        super().__init__(parent)
        if accent_color:
            icon_color = accent_color
        self.setFixedHeight(94)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon capsule
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background-color: {badge_bg};
            border-radius: 10px;
            border: 1px solid {icon_color}22;
        """)
        icon_lbl.setPixmap(IconManager.get_pixmap(icon_name, color=icon_color, size=20))
        layout.addWidget(icon_lbl)

        # Content text
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(2)

        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #64748B;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        vbox.addWidget(self.lbl_title)

        self.lbl_val = QLabel(value)
        self.lbl_val.setStyleSheet("""
            font-size: 20px;
            font-weight: 800;
            color: #0F172A;
            background: transparent;
        """)
        vbox.addWidget(self.lbl_val)
        self.value_label = self.lbl_val

        self.lbl_sub = QLabel(subtitle if subtitle else "")
        self.lbl_sub.setStyleSheet("""
            font-size: 11px;
            color: #94A3B8;
            background: transparent;
        """)
        if not subtitle:
            self.lbl_sub.hide()
        vbox.addWidget(self.lbl_sub)
        self.sub_label = self.lbl_sub

        layout.addLayout(vbox)
        layout.addStretch()

    def update_value(self, new_val: str, new_sub: str = ""):
        self.lbl_val.setText(str(new_val))
        if new_sub:
            self.lbl_sub.setText(new_sub)
            self.lbl_sub.show()


class StatusBadge(QLabel):
    """
    Soft pastel pill badge for statuses (Active, Paid, Absent, Present, etc.).
    Zero emojis used.
    """
    def __init__(self, text: str, variant: str = "success", parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(24)

        styles = {
            "success": ("#DCFCE7", "#15803D", "#86EFAC"),  # Paid, Active, Present
            "danger": ("#FEE2E2", "#B91C1C", "#FCA5A5"),   # Unpaid, Inactive, Absent, Suspended
            "warning": ("#FEF3C7", "#B45309", "#FCD34D"),  # Partial, Late, Pending, Migrated
            "info": ("#E0E7FF", "#4338CA", "#A5B4FC"),     # Enrolled, Processing
            "neutral": ("#F1F5F9", "#475569", "#CBD5E1"),  # Excused, Leave, General
            "purple": ("#F3E8FF", "#7E22CE", "#D8B4FE"),   # Graduated Alumni
            "orange": ("#FFEDD5", "#C2410C", "#FDBA74"),   # Dropout
            "sky": ("#E0F2FE", "#0284C7", "#7DD3FC"),      # On Leave
            "secondary": ("#F1F5F9", "#475569", "#CBD5E1"),
        }

        bg, fg, border = styles.get(variant, styles["neutral"])
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)


class SegmentedTabBar(QFrame):
    """
    A modern horizontal segmented pill tab bar for category filtering.
    Emits tab_changed(index, text).
    """
    tab_changed = Signal(int, str)

    def __init__(self, tabs: list, initial_index: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("SegmentedTabBar")
        self.setStyleSheet("""
            QFrame#SegmentedTabBar {
                background-color: #F1F5F9;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
        """)
        self._raw_titles = list(tabs)
        self._buttons: list[QPushButton] = []
        self._current_index = -1

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(4)

        for idx, title in enumerate(tabs):
            display_title = title.replace("&", "&&") if "&&" not in title else title
            btn = QPushButton(display_title)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, i=idx: self.set_current_index(i))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()
        self.set_current_index(initial_index)

    def set_current_index(self, index: int):
        if index < 0 or index >= len(self._buttons):
            return
        if self._current_index == index:
            return
        self._current_index = index
        for i, btn in enumerate(self._buttons):
            is_active = (i == index)
            btn.blockSignals(True)
            btn.setChecked(is_active)
            btn.blockSignals(False)
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #1E293B;
                        font-weight: 700;
                        font-size: 12px;
                        border: 1px solid #CBD5E1;
                        border-radius: 6px;
                        padding: 3px 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #64748B;
                        font-weight: 600;
                        font-size: 12px;
                        border: none;
                        border-radius: 6px;
                        padding: 3px 12px;
                    }
                    QPushButton:hover {
                        background-color: #E2E8F0;
                        color: #1E293B;
                    }
                """)
        self.tab_changed.emit(index, self._raw_titles[index])

    def current_index(self) -> int:
        return self._current_index

    def current_text(self) -> str:
        if 0 <= self._current_index < len(self._raw_titles):
            return self._raw_titles[self._current_index]
        return ""



class SearchInput(QLineEdit):
    """Modern Search Input with embedded Lucide search vector icon."""
    def __init__(self, placeholder: str = "Search...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(36)
        
        # Add embedded search icon
        search_icon = IconManager.get("search", color="#94A3B8", size=16)
        self.addAction(search_icon, QLineEdit.ActionPosition.LeadingPosition)

        self.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1.5px solid #CBD5E1;
                border-radius: 8px;
                padding-left: 28px;
                padding-right: 12px;
                padding-top: 3px;
                padding-bottom: 3px;
                font-size: 12px;
                min-height: 32px;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
            }
        """)


def style_modern_table(table: QTableWidget):
    """
    Applies clean Google Stitch styling to a QTableWidget:
    - Soft grey header (#F8FAFC)
    - 40-44px row height
    - Subtle hover (#F8FAFC) and selection (#EFF6FF)
    - Eliminates harsh grid lines
    """
    table.setStyleSheet("""
        QTableWidget {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            gridline-color: #F1F5F9;
            font-size: 12px;
            color: #1E293B;
            selection-background-color: #EFF6FF;
            selection-color: #1E293B;
        }
        QTableWidget::item {
            padding: 4px 6px;
            border-bottom: 1px solid #F1F5F9;
        }
        QTableWidget::item:selected {
            background-color: #EFF6FF;
            color: #1E293B;
        }
        QTableWidget QSpinBox, QTableWidget QDoubleSpinBox, QTableWidget QLineEdit {
            padding: 2px 4px;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid #CBD5E1;
            border-radius: 4px;
            background: #FFFFFF;
            color: #0F172A;
        }
        QTableWidget QSpinBox::up-button, QTableWidget QSpinBox::down-button,
        QTableWidget QDoubleSpinBox::up-button, QTableWidget QDoubleSpinBox::down-button {
            width: 0px;
            height: 0px;
            border: none;
        }
        QHeaderView::section {
            background-color: #F8FAFC;
            color: #64748B;
            font-size: 11px;
            font-weight: 700;
            padding: 6px 4px;
            border: none;
            border-bottom: 2px solid #E2E8F0;
            text-transform: uppercase;
        }
        QScrollBar:vertical {
            border: none;
            background: #F8FAFC;
            width: 8px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #CBD5E1;
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94A3B8;
        }
    """)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(44)
    table.setAlternatingRowColors(False)
    table.setShowGrid(False)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)


def style_modern_tabs(tab_widget: QTabWidget):
    """Applies modern pill-style tab styling to a QTabWidget."""
    tab_widget.setStyleSheet("""
        QTabWidget::pane {
            border: none;
            background: transparent;
        }
        QTabBar::tab {
            background: #F1F5F9;
            color: #64748B;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 6px 14px;
            margin-right: 6px;
            margin-bottom: 10px;
            font-weight: 600;
            font-size: 13px;
        }
        QTabBar::tab:selected {
            background: #2563EB;
            color: #FFFFFF;
            border-color: #2563EB;
        }
        QTabBar::tab:hover:!selected {
            background: #E2E8F0;
            color: #1E293B;
        }
    """)
