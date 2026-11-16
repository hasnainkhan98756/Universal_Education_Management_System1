import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGraphicsDropShadowEffect, QFrame, QApplication, QDialog
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor, QPixmap

from core.state_manager import app_state
from core.theme_manager import ThemeManager
from core.icon_manager import IconManager


class TabLoadingOverlay(QWidget):
    """
    Sleek, non-blocking loading overlay for in-app tab transitions.
    Displays tab icon, tab title, custom institute branding, and animated progress track.
    Appears seamlessly whenever a view takes a moment to build or refresh.
    """
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hide()

        self._anim = None
        self._init_ui()

    def _init_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Centered modern card
        self.card = QFrame()
        self.card.setFixedSize(340, 190)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(24, 20, 24, 20)
        card_lay.setSpacing(10)
        card_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon badge
        self.icon_badge = QLabel()
        self.icon_badge.setFixedSize(48, 48)
        self.icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_badge.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #EFF6FF, stop:1 #DBEAFE);
                border-radius: 12px;
                border: 1.5px solid #BFDBFE;
            }
        """)
        card_lay.addWidget(self.icon_badge, 0, Qt.AlignmentFlag.AlignCenter)

        # Title Label
        self.lbl_title = QLabel("Loading Section...")
        self.lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self.lbl_title)

        # Institute Name Subtitle / Pill
        self.lbl_inst = QLabel()
        self.lbl_inst.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.lbl_inst.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self.lbl_inst)

        # Animated progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate smooth pulse
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border-radius: 2px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #38BDF8);
                border-radius: 2px;
            }
        """)
        card_lay.addWidget(self.progress_bar)

        root_lay.addWidget(self.card)
        self._update_theme()

    def _update_theme(self):
        is_dark = ThemeManager.is_dark()
        inst_name = app_state.get_setting("institution_name", "") or app_state.get_setting("app_title", "Universal Education Management")
        
        if is_dark:
            self.setStyleSheet("TabLoadingOverlay { background-color: rgba(11, 18, 36, 0.75); }")
            self.card.setStyleSheet("""
                QFrame {
                    background-color: #162040;
                    border: 1.5px solid #2D4070;
                    border-radius: 16px;
                }
            """)
            self.lbl_title.setStyleSheet("color: #F8FAFC; background: transparent; border: none;")
            self.lbl_inst.setStyleSheet("color: #38BDF8; background: transparent; border: none;")
            self.progress_bar.setStyleSheet("""
                QProgressBar { background-color: #0F172A; border-radius: 2px; border: none; }
                QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #38BDF8); }
            """)
        else:
            self.setStyleSheet("TabLoadingOverlay { background-color: rgba(243, 247, 250, 0.75); }")
            self.card.setStyleSheet("""
                QFrame {
                    background-color: #FFFFFF;
                    border: 1.5px solid #CBD5E1;
                    border-radius: 16px;
                }
            """)
            self.lbl_title.setStyleSheet("color: #0F172A; background: transparent; border: none;")
            self.lbl_inst.setStyleSheet("color: #2563EB; background: transparent; border: none;")
            self.progress_bar.setStyleSheet("""
                QProgressBar { background-color: #F1F5F9; border-radius: 2px; border: none; }
                QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #0EA5E9); }
            """)

        self.lbl_inst.setText(f"{inst_name} • Live Workspace")

    def show_loading(self, tab_title: str, icon_name: str = "layers"):
        """Displays overlay with specific tab name and vector icon."""
        self._update_theme()
        self.lbl_title.setText(f"Loading {tab_title}...")
        self.icon_badge.setPixmap(IconManager.get_pixmap(icon_name, color="#2563EB", size=24))

        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.show()
        self.raise_()
        QApplication.processEvents()

    def hide_loading(self):
        """Hides the loading overlay."""
        self.hide()


class TopProgressBar(QProgressBar):
    """
    Subtle 3px indeterminate progress bar positioned at the top of the main window or view.
    Provides instant visual feedback during asynchronous data fetching without blocking UI.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self.setTextVisible(False)
        self.setRange(0, 0)  # Indeterminate
        self.setStyleSheet("""
            QProgressBar {
                background-color: transparent;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:0.5 #38BDF8, stop:1 #10B981);
            }
        """)
        self.hide()

    def start(self):
        self.show()
        self.raise_()

    def stop(self):
        self.hide()


class PrintLoadingDialog(QDialog):
    """
    Sleek loading card that appears whenever the user triggers printing or document generation.
    Displays printer animation, disables multiple clicks, and smoothly auto-dismisses upon completion.
    """
    def __init__(self, parent=None, title: str = "Generating & Printing...", subtitle: str = "Formatting high-resolution thermal / A4 document"):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(360, 180)

        # Build card UI
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1.5px solid #CBD5E1;
                border-radius: 16px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 70))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)

        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(20, 16, 20, 16)
        c_lay.setSpacing(8)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Badge
        icon_badge = QLabel()
        icon_badge.setFixedSize(44, 44)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setStyleSheet("""
            QLabel {
                background: #EFF6FF;
                border-radius: 10px;
                border: 1px solid #BFDBFE;
            }
        """)
        icon_badge.setPixmap(IconManager.get_pixmap("printer", color="#2563EB", size=22))
        c_lay.addWidget(icon_badge, 0, Qt.AlignmentFlag.AlignCenter)

        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #0F172A; border: none; background: transparent;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(self.lbl_title)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setFont(QFont("Segoe UI", 9))
        self.lbl_sub.setStyleSheet("color: #64748B; border: none; background: transparent;")
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_lay.addWidget(self.lbl_sub)

        pbar = QProgressBar()
        pbar.setFixedHeight(4)
        pbar.setTextVisible(False)
        pbar.setRange(0, 0)
        pbar.setStyleSheet("""
            QProgressBar { background-color: #F1F5F9; border-radius: 2px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #10B981); }
        """)
        c_lay.addWidget(pbar)

        root_lay.addWidget(card)

    def show_modal(self):
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2
            )
        self.show()
        self.raise_()
        QApplication.processEvents()


class show_print_loading:
    """Context manager to wrap any print/export/PDF generation operation with a loading screen."""
    def __init__(self, parent=None, title="Generating & Printing...", subtitle="Formatting thermal / A4 document"):
        self.dlg = PrintLoadingDialog(parent=parent, title=title, subtitle=subtitle)

    def __enter__(self):
        self.dlg.show_modal()
        return self.dlg

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dlg.close()
        self.dlg.deleteLater()
        QApplication.processEvents()
