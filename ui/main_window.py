import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QStackedWidget, QScrollArea, QDialog, QDialogButtonBox,
    QGraphicsDropShadowEffect, QSizePolicy, QComboBox
)
from PySide6.QtCore import (
    Qt, QTimer, QDateTime, Signal, QRect, QRectF, QPoint, QSize,
    QPropertyAnimation, QEasingCurve, QEvent, QRunnable, QThreadPool, QObject
)
from PySide6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QCursor

from core.state_manager import app_state
from core.theme_manager import ThemeManager
from core.notification_service import NotificationService
from core.icon_manager import IconManager, icon_mgr

# Core Views (Dashboard is eager, other views are lazy-loaded via factories)
from ui.views.dashboard import DashboardView
from ui.components.loading_widgets import TabLoadingOverlay, TopProgressBar



class NavButton(QPushButton):
    """Custom sidebar navigation button with active, hover, and pressed states.
    Uses vector Lucide icons directly with zero emojis."""

    def __init__(self, icon_name: str, label_str: str, page_index: int, is_logout: bool = False, icon_color: str = "#64748B"):
        super().__init__()
        self.page_index = page_index
        self.is_logout  = is_logout
        self.icon_name  = icon_name
        self.icon_color = icon_color
        self._active    = False

        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(12)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(20, 20)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet("background:transparent;border:none;")

        self.text_lbl = QLabel(label_str)
        self.text_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.text_lbl.setStyleSheet("background:transparent;border:none;")

        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.text_lbl)
        lay.addStretch()

        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        if self.is_logout:
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none; border-radius: 10px; text-align: left; } "
                "QPushButton:hover { background: #FFF1F2; } "
                "QPushButton:pressed { background: #FFE4E6; }"
            )
            self.text_lbl.setStyleSheet("color: #E11D48; font-weight: 600; background: transparent; border: none;")
            self.icon_lbl.setPixmap(IconManager.get_pixmap("log-out", color="#E11D48", size=18))
            return

        if self._active:
            self.setStyleSheet(
                "QPushButton { background: #EFF6FF; border: none; border-left: 4px solid #2563EB; "
                "border-radius: 10px; text-align: left; }"
            )
            self.text_lbl.setStyleSheet("color: #2563EB; font-weight: 700; background: transparent; border: none;")
            self.icon_lbl.setPixmap(IconManager.get_pixmap(self.icon_name, color="#2563EB", size=18))
        else:
            self.setStyleSheet(
                "QPushButton { background: transparent; border: none; border-radius: 10px; text-align: left; } "
                "QPushButton:hover { background: #F8FAFC; } "
                "QPushButton:pressed { background: #F1F5F9; }"
            )
            self.text_lbl.setStyleSheet("color: #475569; font-weight: 500; background: transparent; border: none;")
            self.icon_lbl.setPixmap(IconManager.get_pixmap(self.icon_name, color=self.icon_color, size=18))


class NotificationBell(QWidget):
    """Refined notification bell with a crisp top-right red badge count and vibration animation."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._last_count = 0
        self._wiggle_steps = []
        self._wiggle_timer = QTimer(self)
        self._wiggle_timer.setInterval(35)
        self._wiggle_timer.timeout.connect(self._on_wiggle_step)

        self.btn = QPushButton(self)
        self.btn.setGeometry(0, 0, 40, 40)
        self.btn.setIcon(IconManager.get_icon("bell", color="#64748B", size=20))
        self.btn.setIconSize(QSize(20, 20))
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 20px; }"
            "QPushButton:hover { background: rgba(37, 99, 235, 0.08); }"
            "QPushButton:pressed { background: rgba(37, 99, 235, 0.16); }"
        )
        self.btn.clicked.connect(self.clicked.emit)

        self.badge = QLabel(self)
        self.badge.setGeometry(22, 2, 16, 16)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setStyleSheet(
            "QLabel { background: #F43F5E; color: white; font-size: 9px; font-weight: bold; "
            "border-radius: 8px; border: 1.5px solid white; }"
        )
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.badge.hide()

    def wiggle(self):
        """Vibrates/wiggles the bell icon to notify the user of new alerts."""
        self._wiggle_steps = [-5, 5, -4, 4, -3, 3, -2, 2, -1, 1, 0]
        if not self._wiggle_timer.isActive():
            self._wiggle_timer.start()

    def _on_wiggle_step(self):
        if self._wiggle_steps:
            dx = self._wiggle_steps.pop(0)
            self.btn.move(dx, 0)
        else:
            self.btn.move(0, 0)
            self._wiggle_timer.stop()

    def set_count(self, count: int):
        if count > self._last_count and count > 0:
            self.wiggle()
        self._last_count = count

        if count > 0:
            self.badge.setText(str(count) if count < 100 else "99+")
            self.badge.show()
        else:
            self.badge.hide()



class ClickableBackdrop(QWidget):
    """Semi-transparent backdrop that dims the content slightly and closes the sidebar on click."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(15, 23, 42, 0.28); border: none;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class SidebarOverlay(QFrame):
    """
    Modern collapsible sliding drawer overlay sidebar.
    - Width: 260px
    - Positioned as a floating layer over the content area
    - Anti-flicker debounced leave detection (350ms grace period)
    - Full scroll area for navigation buttons ensuring no clipping on 720p/768p/1080p
    """
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setObjectName("sidebar_overlay")
        self.setStyleSheet(
            "QFrame#sidebar_overlay { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }"
        )

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.setInterval(350)
        self._leave_timer.timeout.connect(self._on_leave_timeout)
        self.hamburger_btn = None

        self.nav_buttons = []
        self._build_ui()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(12, 16, 12, 16)
        main_lay.setSpacing(6)

        # ── Top Header Row with Logo, Title, and Close Button ──
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(4, 0, 0, 0)
        hdr_lay.setSpacing(10)

        self.sidebar_logo = QLabel()
        self.sidebar_logo.setFixedSize(36, 36)
        self.sidebar_logo.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563EB, stop:1 #0EA5E9);"
            "border-radius: 9px; border: none;"
        )
        self.sidebar_logo.setPixmap(IconManager.get_pixmap("graduation-cap", color="#FFFFFF", size=20))
        self.sidebar_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr_lay.addWidget(self.sidebar_logo)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        self.lbl_app_name = QLabel("School Management")
        self.lbl_app_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_app_name.setWordWrap(True)
        self.lbl_app_name.setStyleSheet("color: #0F172A; background: transparent; border: none;")

        self.lbl_tagline = QLabel("Learn • Grow • Build")
        self.lbl_tagline.setFont(QFont("Segoe UI", 8))
        self.lbl_tagline.setStyleSheet("color: #2563EB; background: transparent; border: none; font-weight: 600;")
        name_col.addWidget(self.lbl_app_name)
        name_col.addWidget(self.lbl_tagline)
        hdr_lay.addLayout(name_col)
        hdr_lay.addStretch()

        # Close button
        self.btn_close = QPushButton()
        self.btn_close.setIcon(icon_mgr.get_icon("x", color="#64748B", size=14))
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Close Menu (Esc)")
        self.btn_close.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #64748B; "
            "border: 1px solid #E2E8F0; border-radius: 14px; font-size: 12px; font-weight: bold; } "
            "QPushButton:hover { background-color: #FEE2E2; color: #EF4444; border-color: #FCA5A5; } "
            "QPushButton:pressed { background-color: #FECACA; }"
        )
        self.btn_close.clicked.connect(self.close_requested.emit)
        hdr_lay.addWidget(self.btn_close)
        main_lay.addWidget(hdr_frame)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0; margin: 4px 0;")
        main_lay.addWidget(div)

        # ── Scrollable Nav Area (Guarantees responsiveness on 720p/768p) ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QScrollBar:vertical { width: 4px; background: transparent; } "
            "QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 2px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        nav_inner = QWidget()
        nav_inner.setStyleSheet("background: transparent;")
        self.nav_lay = QVBoxLayout(nav_inner)
        self.nav_lay.setContentsMargins(0, 0, 0, 0)
        self.nav_lay.setSpacing(3)

        # All Application Navigation Items (Vector SVG Icons with Zero Emojis)
        nav_items = [
            ("layout-dashboard", "Dashboard",          0, "#2563EB"),
            ("school",           "Classes",            2, "#64748B"),
            ("clock",            "Timetable",          8, "#64748B"),
            ("calendar-days",    "Calendar",           13, "#EF4444"),
            ("graduation-cap",   "Teachers",           7, "#0D9488"),
            ("users-2",          "Students",           3, "#3B82F6"),
            ("coins",            "Fee",                4, "#EAB308"),
            ("user-check",       "Attendance",         5, "#10B981"),
            ("book-open",        "Examinations",       6, "#8B5CF6"),
            ("book-open",        "Library",            11, "#F43F5E"),
            ("bus",              "Transport",          12, "#F59E0B"),
            ("package",          "Inventory",          14, "#06B6D4"),
            ("folder",           "Documents",          15, "#6366F1"),
            ("bar-chart-2",      "Analytics",          10, "#64748B"),
            ("mail",             "Messages",           9, "#64748B"),
            ("settings",         "Settings",           1, "#64748B"),
        ]

        for icon_name, label, idx, icon_col in nav_items:
            btn = NavButton(icon_name, label, idx, icon_color=icon_col)
            if idx == 0:
                btn.set_active(True)
            self.nav_buttons.append(btn)
            self.nav_lay.addWidget(btn)

        self.nav_lay.addStretch()
        scroll.setWidget(nav_inner)
        main_lay.addWidget(scroll)

        # Divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: #E2E8F0; margin: 4px 0;")
        main_lay.addWidget(div2)

        # Version
        ver = QLabel("Version 1.0.0\n© 2026 School Management System")
        ver.setStyleSheet("color: #94A3B8; font-size: 9px; background: transparent; border: none; line-height: 1.3;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_lay.addWidget(ver)
        main_lay.addSpacing(2)

        # Logout
        self.logout_btn = NavButton("log-out", "Logout", -1, is_logout=True, icon_color="#E11D48")
        self.logout_btn.set_active(False)
        main_lay.addWidget(self.logout_btn)

    def enterEvent(self, event):
        self._leave_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        cursor_pos = QCursor.pos()
        global_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
        if global_rect.contains(cursor_pos):
            event.accept()
            return
        self._leave_timer.start()
        super().leaveEvent(event)

    def _on_leave_timeout(self):
        cursor_pos = QCursor.pos()
        global_rect = QRect(self.mapToGlobal(QPoint(0, 0)), self.size())
        if global_rect.contains(cursor_pos):
            return
        if self.hamburger_btn and self.hamburger_btn.isVisible():
            h_rect = QRect(self.hamburger_btn.mapToGlobal(QPoint(0, 0)), self.hamburger_btn.size())
            if h_rect.contains(cursor_pos):
                return
        self.close_requested.emit()


class NotificationSignals(QObject):
    count_ready = Signal(int)

class NotificationWorker(QRunnable):
    def __init__(self, signals: NotificationSignals):
        super().__init__()
        self.signals = signals

    def run(self):
        try:
            count = NotificationService.get_count()
            self.signals.count_ready.emit(count)
        except Exception:
            pass

class MainWindow(QMainWindow):
    """
    Main application shell featuring:
      - Collapsible / auto-hide overlay sidebar with smooth slide animations and anti-flicker detection
      - 100% full-width header bar with Hamburger button, institute branding, live ticking clock, bell widget, and user profile
      - Full-screen QStackedWidget hosting all views (Dashboard, Settings, Academics, Students, Fees,
        Attendance, Exams, HR, Timetable, Communications, Analytics, Library, Transport)
      - Real-time live synchronization with theme switches and settings changes
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Education Management System")
        self.setMinimumSize(1280, 800)

        self.nav_buttons = []
        self._is_sidebar_open = False
        self._anim_sidebar = None
        self._notif_in_progress = False
        self._notif_signals = NotificationSignals()
        self._notif_signals.count_ready.connect(self._on_bell_count_ready)
        self._threadpool = QThreadPool.globalInstance()
        self._navigating = False

        self._nav_meta = {
            0: ("Dashboard", "layout-dashboard"),
            1: ("Settings", "settings"),
            2: ("Classes & Academics", "school"),
            3: ("Students Directory", "users-2"),
            4: ("Fee Management", "coins"),
            5: ("Attendance", "user-check"),
            6: ("Examinations", "book-open"),
            7: ("Teachers & Staff", "graduation-cap"),
            8: ("Timetable", "clock"),
            9: ("Messages & Communications", "mail"),
            10: ("Analytics & Reports", "bar-chart-2"),
            11: ("Library Management", "book-open"),
            12: ("Transport & Fleet", "bus"),
            13: ("Calendar & Events", "calendar-days"),
            14: ("Inventory & Assets", "package"),
            15: ("Documents & Archives", "folder"),
        }

        self._init_ui()

        # Subscribe to settings updates for live sync
        app_state.subscribe_settings_change(self._sync)
        self._sync()

        # Always launch application in maximized screen mode
        self.showMaximized()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # 1. Full-width Top Header
        self._build_header(root_lay)

        # Divider below header
        hdiv = QFrame()
        hdiv.setFixedHeight(1)
        hdiv.setObjectName("header_div")
        hdiv.setStyleSheet("background: #CBD5E1;")
        root_lay.addWidget(hdiv)

        # 2. Main Content Area (Full-width Stack + Backdrop + Overlay Sidebar)
        self._build_content_area(root_lay)

        # Clock timer
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        self._clock.start(1000)
        self._tick()

        # Notification badge timer (every 30s)
        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._refresh_bell)
        self._notif_timer.start(30000)
        self._refresh_bell()

        # Global Search Shortcut (Ctrl+K)
        from PySide6.QtGui import QKeySequence, QShortcut
        self._search_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        self._search_shortcut.activated.connect(self._open_global_search)

        # Reactive Live Synchronization
        app_state.subscribe_data_changed(self._on_global_data_changed)

        # Background idle warmup queue for views (eliminates first-click tab switching lag)
        self._warmup_queue = [3, 4, 5, 7, 2, 1, 6, 8, 9, 10, 11, 12, 13, 14, 15]
        QTimer.singleShot(400, self._prewarm_next_view)

    def _on_global_data_changed(self):
        """Live sync handler: marks views dirty and immediately refreshes the active visible view."""
        self.mark_view_dirty()
        curr_idx = self.stack.currentIndex()
        curr_widget = self.stack.currentWidget()
        if curr_widget:
            for method in ['refresh_attendance', 'refresh_current_view', 'refresh_data', 'refresh_student_list', 'refresh_all']:
                if hasattr(curr_widget, method):
                    try:
                        getattr(curr_widget, method)()
                        self._view_dirty[curr_idx] = False
                    except Exception as e:
                        print(f"Error live-refreshing active view {curr_idx}: {e}")
                    break

    def _open_global_search(self):
        from ui.dialogs.global_search_dialog import GlobalSearchDialog
        dlg = GlobalSearchDialog(self, self)
        dlg.exec()

    def _prewarm_next_view(self):
        if not hasattr(self, "_warmup_queue") or not self._warmup_queue:
            return
        idx = self._warmup_queue.pop(0)
        if idx not in self._cached_views:
            try:
                self.get_or_create_view(idx)
            except Exception as e:
                print(f"Prewarm view {idx} error: {e}")
        if self._warmup_queue:
            QTimer.singleShot(120, self._prewarm_next_view)

    # ── HEADER (100% Full Width) ──────────────────────────────────────────────
    def _build_header(self, root: QVBoxLayout):
        t = ThemeManager.tokens()
        self.header = QFrame()
        self.header.setFixedHeight(64)
        self._style_header()
        hlay = QHBoxLayout(self.header)
        hlay.setContentsMargins(16, 0, 20, 0)
        hlay.setSpacing(14)

        # Hamburger Button
        self.btn_hamburger = QPushButton()
        self.btn_hamburger.setFixedSize(38, 38)
        self.btn_hamburger.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hamburger.setToolTip("Menu")
        self.btn_hamburger.clicked.connect(self.toggle_sidebar)
        self._style_hamburger()
        hlay.addWidget(self.btn_hamburger)
        hlay.addSpacing(4)

        # Institute Logo icon
        self.hdr_logo = QLabel()
        self.hdr_logo.setFixedSize(38, 38)
        self.hdr_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hdr_logo.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563EB, stop:1 #0EA5E9);"
            "border-radius: 10px; border: none;"
        )
        self.hdr_logo.setPixmap(IconManager.get_pixmap("graduation-cap", color="#FFFFFF", size=22))
        hlay.addWidget(self.hdr_logo)
        hlay.addSpacing(2)

        # Institute name + tagline
        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        name_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.hdr_name = QLabel("School Management System")
        self.hdr_name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.hdr_name.setStyleSheet("background: transparent; border: none; color: #0F172A;")

        self.hdr_tagline = QLabel("Learn • Grow • Build a Better Future")
        self.hdr_tagline.setFont(QFont("Segoe UI", 9))
        self.hdr_tagline.setStyleSheet("color: #2563EB; background: transparent; border: none; font-weight: 600;")
        name_col.addWidget(self.hdr_name)
        name_col.addWidget(self.hdr_tagline)
        hlay.addLayout(name_col)
        hlay.addStretch()

        # Global Search Bar Shortcut Button
        self.btn_search = QPushButton("  Search anything... (Ctrl+K)")
        self.btn_search.setIcon(IconManager.get_icon("search", color="#94A3B8", size=14))
        self.btn_search.setIconSize(QSize(14, 14))
        self.btn_search.setFixedHeight(34)
        self.btn_search.setMinimumWidth(240)
        self.btn_search.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search.setStyleSheet(f"""
            QPushButton {{
                background-color: {t['input_bg']};
                color: {t['text_secondary']};
                border: 1.5px solid {t['border']};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 11px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {t['accent']};
                color: {t['text_primary']};
                background-color: #FFFFFF;
            }}
        """)
        self.btn_search.clicked.connect(self._open_global_search)
        hlay.addWidget(self.btn_search)
        hlay.addSpacing(10)

        # Date & Time Frame (Capsules matching Stitch)
        dt_frame = QFrame()
        dt_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        dt_lay = QHBoxLayout(dt_frame)
        dt_lay.setContentsMargins(0, 0, 0, 0)
        dt_lay.setSpacing(10)

        # Date capsule
        date_capsule = QFrame()
        date_capsule.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        dbl = QHBoxLayout(date_capsule)
        dbl.setSpacing(8)
        dbl.setContentsMargins(8, 4, 10, 4)
        date_icon = QLabel()
        date_icon.setPixmap(IconManager.get_pixmap("calendar-days", color="#2563EB", size=16))
        date_icon.setStyleSheet("background: transparent; border: none;")
        date_col = QVBoxLayout()
        date_col.setSpacing(0)
        self.lbl_date = QLabel("--")
        self.lbl_date.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_date.setStyleSheet("background: transparent; border: none; color: #0F172A;")
        self.lbl_day = QLabel("--")
        self.lbl_day.setFont(QFont("Segoe UI", 8))
        self.lbl_day.setStyleSheet("color: #64748B; background: transparent; border: none;")
        date_col.addWidget(self.lbl_date)
        date_col.addWidget(self.lbl_day)
        dbl.addWidget(date_icon)
        dbl.addLayout(date_col)
        dt_lay.addWidget(date_capsule)

        # Time capsule
        time_capsule = QFrame()
        time_capsule.setStyleSheet(
            "QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; }"
        )
        tbl2 = QHBoxLayout(time_capsule)
        tbl2.setSpacing(8)
        tbl2.setContentsMargins(8, 4, 10, 4)
        time_icon = QLabel()
        time_icon.setPixmap(IconManager.get_pixmap("clock", color="#0EA5E9", size=16))
        time_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_time = QLabel("--:--")
        self.lbl_time.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_time.setStyleSheet("background: transparent; border: none; color: #0F172A;")
        tbl2.addWidget(time_icon)
        tbl2.addWidget(self.lbl_time)
        dt_lay.addWidget(time_capsule)

        hlay.addWidget(dt_frame)

        # Notification Bell
        self.bell_widget = NotificationBell()
        self.bell_widget.clicked.connect(self._show_notifications)
        hlay.addWidget(self.bell_widget)

        # User profile
        user_frame = QFrame()
        user_frame.setFixedHeight(44)
        user_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        uf_lay = QHBoxLayout(user_frame)
        uf_lay.setContentsMargins(6, 2, 6, 2)
        uf_lay.setSpacing(10)

        self.avatar = QLabel()
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B82F6, stop:1 #1D4ED8);"
            "border-radius: 18px; border: none;"
        )
        self.avatar.setPixmap(IconManager.get_pixmap("user", color="#FFFFFF", size=18))

        user_col = QVBoxLayout()
        user_col.setSpacing(1)
        user_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.lbl_username = QLabel("Admin")
        self.lbl_username.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_username.setStyleSheet("background: transparent; border: none; color: #0F172A;")

        self.lbl_role = QLabel("Administrator")
        self.lbl_role.setFont(QFont("Segoe UI", 9))
        self.lbl_role.setStyleSheet("color: #64748B; background: transparent; border: none;")
        user_col.addWidget(self.lbl_username)
        user_col.addWidget(self.lbl_role)

        self.lbl_chevron = QLabel()
        self.lbl_chevron.setPixmap(IconManager.get_pixmap("chevron-down", color="#94A3B8", size=14))
        self.lbl_chevron.setStyleSheet("background: transparent; border: none;")

        uf_lay.addWidget(self.avatar)
        uf_lay.addLayout(user_col)
        uf_lay.addWidget(self.lbl_chevron)
        hlay.addWidget(user_frame)

        root.addWidget(self.header)

    # ── FULL-SCREEN CONTENT & OVERLAY SIDEBAR ──────────────────────────────────
    def _build_content_area(self, root: QVBoxLayout):
        self.content_area = QWidget()
        content_lay = QVBoxLayout(self.content_area)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        # Full-Screen Stacked Views (Uses 100% of available screen width and height)
        self.stack = QStackedWidget()

        # View factory mapping for lazy initialization (imports deferred until first access)
        self._view_factories = {
            1: lambda: __import__('ui.views.settings.general_settings', fromlist=['SettingsView']).SettingsView(),
            2: lambda: __import__('ui.views.academics.academic_view', fromlist=['AcademicView']).AcademicView(),
            3: lambda: __import__('ui.views.students.student_view', fromlist=['StudentView']).StudentView(),
            4: lambda: __import__('ui.views.fees.fee_view', fromlist=['FeeView']).FeeView(),
            5: lambda: __import__('ui.views.attendance.attendance_view', fromlist=['AttendanceView']).AttendanceView(),
            6: lambda: __import__('ui.views.examinations.examination_view', fromlist=['ExaminationView']).ExaminationView(),
            7: lambda: __import__('ui.views.hr.hr_view', fromlist=['HRView']).HRView(),
            8: lambda: __import__('ui.views.timetable.timetable_view', fromlist=['TimetableView']).TimetableView(),
            9: lambda: __import__('ui.views.communications.communication_view', fromlist=['CommunicationView']).CommunicationView(),
            10: lambda: __import__('ui.views.analytics.analytics_view', fromlist=['AnalyticsView']).AnalyticsView(),
            11: lambda: __import__('ui.views.library.library_view', fromlist=['LibraryView']).LibraryView(),
            12: lambda: __import__('ui.views.transport.transport_view', fromlist=['TransportView']).TransportView(),
            13: lambda: __import__('ui.views.calendar_view', fromlist=['CalendarView']).CalendarView(),
            14: lambda: __import__('ui.views.inventory.inventory_view', fromlist=['InventoryView']).InventoryView(),
            15: lambda: __import__('ui.views.documents.document_view', fromlist=['DocumentView']).DocumentView(),
        }
        self._cached_views = {}
        self._view_dirty = {}
        self._view_last_refreshed = {}

        # Stack Index 0 (DashboardView) is instantiated immediately on launch
        self.dashboard_view = DashboardView()
        self.stack.addWidget(self.dashboard_view)
        self._cached_views[0] = self.dashboard_view

        # Stack Indices 1 to 15: Lightweight placeholders replaced on-demand
        for i in range(1, 16):
            placeholder = QWidget()
            self.stack.addWidget(placeholder)

        content_lay.addWidget(self.stack)
        root.addWidget(self.content_area)

        # Clickable backdrop overlay
        self.backdrop = ClickableBackdrop(self.content_area)
        self.backdrop.clicked.connect(self.slide_out_sidebar)
        self.backdrop.hide()

        # Sliding drawer sidebar overlay
        self.sidebar = SidebarOverlay(self.content_area)
        self.sidebar.close_requested.connect(self.slide_out_sidebar)
        self.sidebar.logout_btn.clicked.connect(self._logout)
        self.sidebar.hamburger_btn = self.btn_hamburger
        for btn in self.sidebar.nav_buttons:
            btn.clicked.connect(lambda _, b=btn: self._switch(b))
        self.nav_buttons = self.sidebar.nav_buttons
        self.sidebar.hide()

        # In-App Navigation Loading Overlays
        self.tab_loading = TabLoadingOverlay(self.content_area)
        self.top_progress = TopProgressBar(self.content_area)

        # Permanent, single animation object to prevent closure and signal accumulation
        self._anim_sidebar = QPropertyAnimation(self.sidebar, b"pos", self)
        self._anim_sidebar.finished.connect(self._on_sidebar_animation_finished)

    def _style_header(self):
        t = ThemeManager.tokens()
        self.header.setStyleSheet(
            f"QFrame {{ background-color: {t['bg_header']}; border: none; border-bottom: 1px solid {t['border']}; }}"
        )

    def _style_hamburger(self):
        t = ThemeManager.tokens()
        self.btn_hamburger.setIcon(IconManager.get_icon("menu", color=t["text_primary"], size=20))
        self.btn_hamburger.setIconSize(QSize(20, 20))
        self.btn_hamburger.setStyleSheet(
            f"QPushButton {{ background-color: {t['bg_card']}; "
            f"border: 1px solid {t['border']}; border-radius: 8px; padding: 0px; }} "
            f"QPushButton:hover {{ background-color: #EFF6FF; border-color: {t['accent']}; }} "
            f"QPushButton:pressed {{ background-color: #DBEAFE; }}"
        )

    # ── SIDEBAR ANIMATION & GEOMETRY ──────────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        self._update_overlay_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_overlay_geometry()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._is_sidebar_open:
            self.slide_out_sidebar()
            event.accept()
            return
        super().keyPressEvent(event)

    def _update_overlay_geometry(self):
        if hasattr(self, "content_area") and hasattr(self, "sidebar"):
            cw = self.content_area.width()
            ch = self.content_area.height()
            sb_w = self.sidebar.width()
            self.sidebar.setFixedHeight(ch)
            if hasattr(self, "backdrop") and self.backdrop.isVisible():
                self.backdrop.setGeometry(0, 0, cw, ch)
            if hasattr(self, "tab_loading") and self.tab_loading.isVisible():
                self.tab_loading.setGeometry(0, 0, cw, ch)
            if hasattr(self, "top_progress"):
                self.top_progress.setGeometry(0, 0, cw, 3)
            if self._is_sidebar_open:
                self.sidebar.move(0, 0)
            else:
                self.sidebar.move(-sb_w - 20, 0)

    def toggle_sidebar(self):
        if self._is_sidebar_open:
            self.slide_out_sidebar()
        else:
            self.slide_in_sidebar()

    def slide_in_sidebar(self):
        if self._is_sidebar_open:
            return
        self._is_sidebar_open = True
        h = self.content_area.height()
        w = self.sidebar.width()

        self.backdrop.setGeometry(0, 0, self.content_area.width(), h)
        self.backdrop.show()
        self.backdrop.raise_()

        self.sidebar.setGeometry(-w, 0, w, h)
        self.sidebar.show()
        self.sidebar.raise_()

        if self._anim_sidebar.state() == QPropertyAnimation.State.Running:
            self._anim_sidebar.stop()

        self._anim_sidebar.setDuration(220)
        self._anim_sidebar.setStartValue(QPoint(-w, 0))
        self._anim_sidebar.setEndValue(QPoint(0, 0))
        self._anim_sidebar.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_sidebar.start()

    def slide_out_sidebar(self):
        if not self._is_sidebar_open:
            return
        self._is_sidebar_open = False
        w = self.sidebar.width()

        if self._anim_sidebar.state() == QPropertyAnimation.State.Running:
            self._anim_sidebar.stop()

        self._anim_sidebar.setDuration(200)
        self._anim_sidebar.setStartValue(self.sidebar.pos())
        self._anim_sidebar.setEndValue(QPoint(-w, 0))
        self._anim_sidebar.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_sidebar.start()

    def _on_sidebar_animation_finished(self):
        if not self._is_sidebar_open:
            self.sidebar.hide()
            self.backdrop.hide()

    def _sync(self):
        name    = app_state.get_setting("institution_name", "") or app_state.get_setting("name", "School Management System")
        title   = app_state.get_setting("app_title", "School Management System")
        tagline = app_state.get_setting("address", "Learn • Grow • Build a Better Future")
        logo_p  = app_state.get_setting("logo_path", "") or app_state.get_setting("institution_logo", "")
        user    = getattr(app_state, "current_username", "Admin") or "Admin"
        role    = getattr(app_state, "current_user_role", "Administrator") or "Administrator"
        ThemeManager.apply("Light")

        self._style_header()
        self._style_hamburger()

        display_name = name or title
        self.hdr_name.setText(display_name)
        self.hdr_name.setToolTip(display_name)
        if hasattr(self, "sidebar") and hasattr(self.sidebar, "lbl_app_name"):
            self.sidebar.lbl_app_name.setText(display_name)
        if tagline and len(tagline) < 60:
            self.hdr_tagline.setText(tagline)
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "lbl_tagline"):
                self.sidebar.lbl_tagline.setText(tagline)
        self.lbl_username.setText(user.capitalize())
        self.lbl_role.setText(role)

        self.setWindowTitle(f"{title} — {user.capitalize()} ({role})")
        if logo_p and os.path.exists(logo_p):
            self.setWindowIcon(QIcon(logo_p))
            pix = QPixmap(logo_p).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "sidebar_logo"):
                self.sidebar.sidebar_logo.setPixmap(pix)
            self.hdr_logo.setPixmap(pix)

        t = ThemeManager.tokens()
        for lbl in [self.hdr_name, self.lbl_date, self.lbl_time, self.lbl_username]:
            lbl.setStyleSheet(f"background: transparent; border: none; color: {t['text_primary']}; font-weight: bold;")
        for lbl in [self.lbl_day, self.lbl_role]:
            lbl.setStyleSheet(f"background: transparent; border: none; color: {t['text_secondary']}; font-weight: 500;")
        self.hdr_tagline.setStyleSheet(f"color: {t['accent']}; background: transparent; border: none; font-weight: 600;")

        # Update dashboard if available
        if hasattr(self, "dashboard_view") and hasattr(self.dashboard_view, "update_theme"):
            self.dashboard_view.update_theme()
        # Mark cached views dirty so they re-sync on next view
        if hasattr(self, "mark_view_dirty"):
            self.mark_view_dirty()
        if hasattr(self, "_refresh_bell"):
            self._refresh_bell()

    def _tick(self):
        now = QDateTime.currentDateTime()
        self.lbl_date.setText(now.toString("dd MMM yyyy"))
        self.lbl_day.setText(now.toString("dddd"))
        self.lbl_time.setText(now.toString("hh:mm AP"))

    def _on_bell_count_ready(self, count: int):
        self._notif_in_progress = False
        try:
            self.bell_widget.set_count(count)
        except Exception:
            pass

    def _refresh_bell(self):
        if getattr(self, "_notif_in_progress", False):
            return
        self._notif_in_progress = True
        worker = NotificationWorker(self._notif_signals)
        self._threadpool.start(worker)

    def _show_notifications(self):
        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Notifications & System Alerts")
        dlg.setMinimumSize(540, 440)
        dlg.setStyleSheet(f"QDialog {{ background-color: {t['bg_surface']}; color: {t['text_primary']}; }}")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        # Header with total count and category filter
        all_alerts = NotificationService.get_all_notifications()
        hdr_row = QHBoxLayout()
        hdr = QLabel(f"<b>System Alerts & Notifications</b> ({len(all_alerts)})")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {t['text_primary']}; background: transparent; border: none;")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        cmb_cat = QComboBox()
        cmb_cat.setMinimumHeight(26)
        cmb_cat.addItems(["All Categories", "Finance", "Inventory", "HR", "Library", "System", "Events"])
        hdr_row.addWidget(cmb_cat)
        lay.addLayout(hdr_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        iv = QVBoxLayout(inner)
        iv.setContentsMargins(0, 0, 0, 0)
        iv.setSpacing(8)
        scroll.setWidget(inner)
        lay.addWidget(scroll)

        def populate_alerts(selected_cat):
            while iv.count():
                child = iv.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            cat_filter = None if selected_cat == "All Categories" else selected_cat
            alerts = NotificationService.get_all_notifications(category_filter=cat_filter)

            if not alerts:
                empty = QLabel("All clear! No pending alerts for this category.")
                empty.setFont(QFont("Segoe UI", 11))
                empty.setStyleSheet(f"color: {t['text_secondary']}; padding: 30px; background: transparent; border: none;")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                iv.addWidget(empty)
            else:
                for alert in alerts:
                    card = QFrame()
                    card.setStyleSheet(f"QFrame {{ background: {t['bg_card']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}")
                    cl = QHBoxLayout(card)
                    cl.setContentsMargins(10, 8, 10, 8)
                    cl.setSpacing(10)

                    icn = QLabel()
                    icn.setFixedSize(24, 24)
                    icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    icn.setStyleSheet("background: transparent; border: none;")
                    icn.setPixmap(IconManager.get_pixmap("bell", color="#2563EB", size=18))
                    cl.addWidget(icn)

                    text_col = QVBoxLayout()
                    text_col.setSpacing(2)
                    tl = QLabel(f"<b>{alert.get('title', '')}</b> <span style='color: #64748B; font-size: 10px;'>[{alert.get('category', 'System')}]</span>")
                    tl.setStyleSheet(f"color: {t['text_primary']}; font-size: 12px; background: transparent; border: none;")
                    ml = QLabel(alert.get("message", ""))
                    ml.setStyleSheet(f"color: {t['text_secondary']}; font-size: 11px; background: transparent; border: none;")
                    ml.setWordWrap(True)
                    text_col.addWidget(tl)
                    text_col.addWidget(ml)
                    cl.addLayout(text_col, 1)

                    pi = alert.get("page_index")
                    if pi is not None:
                        bg = QPushButton("Action ->")
                        bg.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                        bg.setCursor(Qt.CursorShape.PointingHandCursor)
                        bg.setStyleSheet("background: #1D4ED8; color: white; border: none; border-radius: 6px; padding: 4px 10px; font-size: 11px;")
                        bg.clicked.connect(lambda _, idx=pi, d=dlg: (self.navigate_to_page(idx), d.accept()))
                        cl.addWidget(bg)
                    iv.addWidget(card)
            iv.addStretch()

        cmb_cat.currentTextChanged.connect(populate_alerts)
        populate_alerts("All Categories")

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(dlg.reject)
        bb.setStyleSheet(f"QPushButton {{ background: {t['accent']}; color: white; border: none; border-radius: 6px; padding: 6px 18px; font-size: 12px; }}")
        lay.addWidget(bb)
        self._refresh_bell()
        dlg.exec()

    # ── NAVIGATION ────────────────────────────────────────────────────────────
    def get_or_create_view(self, page_index: int):
        """Lazily instantiate views on first access and cache them permanently."""
        if page_index in self._cached_views:
            return self._cached_views[page_index]

        factory = self._view_factories.get(page_index)
        if factory:
            view_instance = factory()
            self._cached_views[page_index] = view_instance

            # Replace the placeholder widget in the QStackedWidget
            old_widget = self.stack.widget(page_index)
            self.stack.removeWidget(old_widget)
            self.stack.insertWidget(page_index, view_instance)
            if old_widget:
                old_widget.deleteLater()

            # Preserve backward-compatible attribute aliases
            attr_map = {
                1: "settings_view", 2: "academic_view", 3: "student_view",
                4: "fee_view", 5: "attendance_view", 6: "exam_view",
                7: "hr_view", 8: "timetable_view", 9: "comm_view",
                10: "analytics_view", 11: "library_view", 12: "transport_view",
                13: "calendar_view", 14: "inventory_view", 15: "document_view"
            }
            if page_index in attr_map:
                setattr(self, attr_map[page_index], view_instance)

            # Mark view as newly created and needing initial data load
            self._view_dirty[page_index] = True
            return view_instance

        return self.stack.widget(page_index)

    def mark_view_dirty(self, page_index: int = None):
        """Marks a specific view or all views dirty so they refresh upon next navigation."""
        if page_index is None:
            for idx in range(self.stack.count()):
                self._view_dirty[idx] = True
        else:
            self._view_dirty[page_index] = True

    def navigate_to_page(self, page_index: int, payload: dict = None):
        if page_index < 0 or page_index >= self.stack.count():
            return
        if getattr(self, "_navigating", False):
            return
        if page_index == self.stack.currentIndex() and not payload:
            return

        is_dirty = self._view_dirty.get(page_index, True) or (page_index not in self._cached_views)
        needs_loading = (page_index not in self._cached_views) or is_dirty

        if needs_loading:
            meta = self._nav_meta.get(page_index, ("Module", "layers"))
            if hasattr(self, "tab_loading"):
                self.tab_loading.show_loading(meta[0], meta[1])
            self._navigating = True
            # Defer slightly so overlay paints and user cannot multi-click
            QTimer.singleShot(25, lambda: self._do_navigate_page(page_index, payload))
        else:
            self._do_navigate_page(page_index, payload)

    def _do_navigate_page(self, page_index: int, payload: dict = None):
        try:
            widget = self.get_or_create_view(page_index)
            self.stack.setCurrentIndex(page_index)
            for b in self.nav_buttons:
                b.set_active(b.page_index == page_index)

            # Smart refresh: only re-query DB if dirty or first load (Dashboard index 0 always refreshed live)
            is_dirty = self._view_dirty.get(page_index, True) or (page_index == 0)
            if is_dirty:
                for method in ['refresh_data', 'refresh_current_view', 'refresh_student_list', 'refresh_attendance', 'refresh_all']:
                    if hasattr(widget, method):
                        try:
                            if hasattr(self, "top_progress"):
                                self.top_progress.start()
                            getattr(widget, method)()
                            if hasattr(self, "top_progress"):
                                self.top_progress.stop()
                            if page_index != 0:
                                self._view_dirty[page_index] = False
                        except Exception as e:
                            if hasattr(self, "top_progress"):
                                self.top_progress.stop()
                            print(f"Error refreshing view {page_index} ({widget.__class__.__name__}): {e}")
                        break

            # Contextual navigation handling from Global Search or internal links
            if payload and isinstance(payload, dict):
                try:
                    if page_index == 3:  # StudentView
                        stu_id = payload.get("student_id") or payload.get("admission_number")
                        if stu_id and hasattr(widget, "focus_student"):
                            widget.focus_student(stu_id, open_profile=True)
                        elif hasattr(widget, "tabs"):
                            widget.tabs.setCurrentIndex(1)
                    elif page_index == 4:  # FeeView
                        v_no = payload.get("voucher_no")
                        if v_no and hasattr(widget, "search_input"):
                            widget.search_input.setText(str(v_no))
                    elif page_index == 7:  # HRView / Teachers
                        emp_id = payload.get("employee_id")
                        if emp_id and hasattr(widget, "txt_search"):
                            widget.txt_search.setText(str(emp_id))
                            if hasattr(widget, "refresh_employees"):
                                widget.refresh_employees()
                    elif page_index == 14:  # InventoryView
                        if hasattr(widget, "tabs"):
                            widget.tabs.setCurrentIndex(1)
                    elif page_index == 15:  # DocumentView
                        if hasattr(widget, "tabs"):
                            widget.tabs.setCurrentIndex(0)
                except Exception as nav_err:
                    print(f"Error processing navigation payload: {nav_err}")
        finally:
            self._navigating = False
            if hasattr(self, "tab_loading"):
                self.tab_loading.hide_loading()

    def _switch(self, btn: NavButton):
        if btn.page_index < 0:
            return
        self.slide_out_sidebar()
        self.navigate_to_page(btn.page_index)

    def _logout(self):
        if hasattr(self, "_notif_timer"):
            self._notif_timer.stop()
        if hasattr(self, "_clock"):
            self._clock.stop()
        app_state.logout()
        from ui.login_window import LoginWindow
        self._login_win = LoginWindow()
        self._login_win.show()
        self.close()
