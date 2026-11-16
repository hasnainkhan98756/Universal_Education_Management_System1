import os
from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QPushButton, QGridLayout, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, QSize, QRectF, QObject, QEvent, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPalette

from core.state_manager import app_state
from core.theme_manager import ThemeManager
from core.icon_manager import IconManager
from core.document_service import DocumentService
from core.academic_service import AcademicService
from core.student_service import StudentService
from core.fee_service import FeeService
from core.attendance_service import AttendanceService

try:
    from core.analytics_service import AnalyticsService
except ImportError:
    try:
        from core.analytic_service import AnalyticsService
    except ImportError:
        AnalyticsService = None


# ── Fast Donut Chart ──────────────────────────────────────────────────────────
class DonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []   # list of (value, color_str)
        self.center_text = "0%"
        self.center_sub  = "Collected"
        self.setFixedSize(136, 136)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_data(self, segments, center_text="", center_sub=""):
        self.segments = segments
        self.center_text = center_text
        self.center_sub  = center_sub
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(v for v, _ in self.segments) or 1
        W, H = self.width(), self.height()
        margin = 12
        pen_w = 14
        arc_rect = QRectF(margin + pen_w / 2, margin + pen_w / 2,
                          W - 2 * margin - pen_w, H - 2 * margin - pen_w)

        # Background track (Light Slate)
        track_color = QColor("#F1F5F9")
        painter.setPen(QPen(track_color, pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(arc_rect)

        start = -90 * 16
        for val, color in self.segments:
            if val <= 0:
                continue
            span = int(val / total * 360 * 16)
            painter.setPen(QPen(QColor(color), pen_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(arc_rect, start, span)
            start += span

        # Center text (Solid Bold Slate-900)
        painter.setPen(QColor("#0F172A"))
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.drawText(QRectF(0, H / 2 - 16, W, 22), Qt.AlignmentFlag.AlignCenter, self.center_text)

        if self.center_sub:
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#64748B"))
            painter.drawText(QRectF(0, H / 2 + 6, W, 18), Qt.AlignmentFlag.AlignCenter, self.center_sub)

        painter.end()


# ── High-Performance Bar Chart (60 FPS) ───────────────────────────────────────
class BarChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {}       # {"Jan": (income, expenses, profit), ...}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(170)

    def set_data(self, data: dict):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.data:
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No monthly financial data recorded yet")
            painter.end()
            return

        W, H = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 48, 14, 14, 30
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        months = list(self.data.keys())
        n = len(months)
        if n == 0:
            painter.end()
            return

        all_vals = []
        for m in months:
            all_vals.extend(self.data[m][:3])
        max_val = max(all_vals) if all_vals else 1
        if max_val <= 0:
            max_val = 1

        bar_group_w = chart_w / n
        bar_w = max(5.0, (bar_group_w - 12) / 3.0)
        colors = [QColor("#10B981"), QColor("#EF4444"), QColor("#2563EB")]

        # Subtle horizontal grid lines
        painter.setPen(QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.DashLine))
        for frac in [0.25, 0.5, 0.75, 1.0]:
            y_line = pad_t + chart_h * (1.0 - frac)
            painter.drawLine(pad_l, int(y_line), int(pad_l + chart_w), int(y_line))

        # Bottom baseline
        painter.setPen(QPen(QColor("#CBD5E1"), 1.5, Qt.PenStyle.SolidLine))
        painter.drawLine(pad_l, int(pad_t + chart_h), int(pad_l + chart_w), int(pad_t + chart_h))

        # Bars
        painter.setPen(Qt.PenStyle.NoPen)
        for i, month in enumerate(months):
            vals = self.data[month][:3]
            group_x = pad_l + i * bar_group_w + (bar_group_w - (3 * bar_w + 4)) / 2.0
            for j, val in enumerate(vals):
                bh = max(2.0, (val / max_val) * chart_h * 0.9) if val > 0 else 0
                if bh > 0:
                    bx = group_x + j * (bar_w + 2)
                    by = pad_t + chart_h - bh
                    painter.setBrush(QBrush(colors[j]))
                    painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 3.0, 3.0)

            # Month label
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(
                QRectF(pad_l + i * bar_group_w, H - pad_b + 4, bar_group_w, pad_b),
                Qt.AlignmentFlag.AlignCenter, month[:3]
            )

        # Y-axis labels
        painter.setPen(QColor("#64748B"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for frac in [0.0, 0.5, 1.0]:
            y = pad_t + chart_h * (1.0 - frac)
            val_k = int(max_val * frac / 1000)
            painter.drawText(0, int(y) - 7, pad_l - 8, 14,
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{val_k}K" if val_k > 0 else "0")
        painter.end()


# ── KPI Card Builder (100% Vector Lucide Icons, Zero Emojis) ─────────────────
def make_kpi_card(icon_name: str, title: str, value_attr: str, subtitle: str,
                  icon_bg: str, icon_color: str, parent, target_page: int = 0) -> QFrame:
    card = QFrame()
    card.setObjectName("dash_card")
    card.setStyleSheet("""
        QFrame#dash_card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }
        QFrame#dash_card:hover { border-color: #93C5FD; background-color: #F8FAFC; }
    """)
    card.setMinimumHeight(95)
    card.setCursor(Qt.CursorShape.PointingHandCursor)
    card.mousePressEvent = lambda e, p=target_page: parent._nav(p)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(4)

    top = QHBoxLayout()
    icon_lbl = QLabel()
    icon_lbl.setFixedSize(36, 36)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lbl.setStyleSheet(f"background: {icon_bg}; border-radius: 10px; border: none;")
    icon_lbl.setPixmap(IconManager.get_pixmap(icon_name, color=icon_color, size=18))

    title_lbl = QLabel(title)
    title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    title_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")

    top.addWidget(icon_lbl)
    top.addSpacing(8)
    top.addWidget(title_lbl)
    top.addStretch()

    arr = QPushButton()
    arr.setFixedSize(28, 28)
    arr.setCursor(Qt.CursorShape.PointingHandCursor)
    arr.setIcon(IconManager.get_icon("arrow-right", color="#94A3B8", size=14))
    arr.setStyleSheet(
        f"QPushButton {{ background: transparent; border: none; border-radius: 6px; }}"
        f"QPushButton:hover {{ background: #F1F5F9; }}"
    )
    arr.clicked.connect(lambda _, p=target_page: parent._nav(p))
    top.addWidget(arr)
    lay.addLayout(top)

    val_lbl = QLabel("—")
    val_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
    val_lbl.setStyleSheet("color: #0F172A; font-weight: 800; background: transparent; border: none;")
    setattr(parent, value_attr, val_lbl)
    lay.addWidget(val_lbl)

    sub_lbl = QLabel(subtitle)
    sub_lbl.setFont(QFont("Segoe UI", 9))
    sub_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
    lay.addWidget(sub_lbl)

    setattr(parent, f"{value_attr}_arr", arr)
    return card


# ── MAIN DASHBOARD VIEW ───────────────────────────────────────────────────────
class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.finance_hidden = True
        self._finance_labels = {}
        self._raw_finance    = {}
        self._class_att_widgets = []
        self._activity_widgets = []

        # 10-Second Auto-Hide Timer for Financial Data
        self._finance_timer = QTimer(self)
        self._finance_timer.setSingleShot(True)
        self._finance_timer.timeout.connect(self._auto_hide_finance)

        self._build_ui()
        app_state.subscribe(self.refresh_data)
        app_state.subscribe_settings_change(self.refresh_data)
        # Data refresh executes on showEvent to keep MainWindow instantiation instantaneous

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 60 FPS Native Hardware-Blitted Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.scroll_content = QWidget()
        self.content_lay = QVBoxLayout(self.scroll_content)
        self.content_lay.setContentsMargins(18, 14, 18, 18)
        self.content_lay.setSpacing(12)

        # Header
        self._build_header()
        
        # =======================================================
        # SMART ATTENDANCE REMINDER BANNER
        # =======================================================
        self.attendance_banner = QFrame()
        self.attendance_banner.setObjectName("attendance_banner")
        self.attendance_banner.setStyleSheet("""
            QFrame#attendance_banner {
                background-color: #FFFBEB;
                border: 1px solid #FCD34D;
                border-radius: 12px;
            }
        """)
        self.attendance_banner.hide() # Hidden by default
        
        banner_lay = QHBoxLayout(self.attendance_banner)
        banner_lay.setContentsMargins(16, 12, 16, 12)
        
        banner_icn = QLabel()
        banner_icn.setFixedSize(24, 24)
        banner_icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_icn.setPixmap(IconManager.get_pixmap("alert-triangle", color="#D97706", size=16))
        banner_lay.addWidget(banner_icn)
        
        self.lbl_banner_msg = QLabel("Reminder: Today's attendance is pending!")
        self.lbl_banner_msg.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_banner_msg.setStyleSheet("color: #92400E; background: transparent; border: none;")
        banner_lay.addWidget(self.lbl_banner_msg)
        banner_lay.addStretch()
        
        btn_mark_att = QPushButton(" Mark Now")
        btn_mark_att.setIcon(IconManager.get_icon("arrow-right", color="#FFFFFF", size=14))
        btn_mark_att.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_mark_att.setFixedHeight(30)
        btn_mark_att.setStyleSheet("""
            QPushButton {
                background-color: #D97706;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 4px 15px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #B45309; }
        """)
        btn_mark_att.clicked.connect(lambda checked=False: self._nav(5)) # Navigate to Attendance Tab
        banner_lay.addWidget(btn_mark_att)
        
        self.content_lay.addWidget(self.attendance_banner)
        # =======================================================

        # =======================================================
        # SMART MONTHLY FEE REMINDER BANNER
        # =======================================================
        self.fee_banner = QFrame()
        self.fee_banner.setObjectName("fee_banner")
        self.fee_banner.setStyleSheet("""
            QFrame#fee_banner {
                background-color: #EFF6FF;
                border: 1px solid #93C5FD;
                border-radius: 12px;
            }
        """)
        self.fee_banner.hide() # Hidden by default
        
        fee_banner_lay = QHBoxLayout(self.fee_banner)
        fee_banner_lay.setContentsMargins(16, 12, 16, 12)
        
        fee_banner_icn = QLabel()
        fee_banner_icn.setFixedSize(24, 24)
        fee_banner_icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fee_banner_icn.setPixmap(IconManager.get_pixmap("credit-card", color="#2563EB", size=16))
        fee_banner_lay.addWidget(fee_banner_icn)
        
        self.lbl_fee_banner_msg = QLabel("Monthly Fee Reminder: Fee generation pending.")
        self.lbl_fee_banner_msg.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_fee_banner_msg.setStyleSheet("color: #1E40AF; background: transparent; border: none;")
        fee_banner_lay.addWidget(self.lbl_fee_banner_msg)
        fee_banner_lay.addStretch()
        
        btn_open_fees = QPushButton(" Open Fee Register")
        btn_open_fees.setIcon(IconManager.get_icon("arrow-right", color="#FFFFFF", size=14))
        btn_open_fees.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_fees.setFixedHeight(30)
        btn_open_fees.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border-radius: 6px;
                padding: 4px 15px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        btn_open_fees.clicked.connect(lambda checked=False: self._nav(4)) # Navigate to Fees Tab
        fee_banner_lay.addWidget(btn_open_fees)
        
        self.content_lay.addWidget(self.fee_banner)
        # =======================================================

        # Row 1: Financial Record + Monthly Overview Chart
        self._build_row1()
        # Row 2: 4 Metric Cards
        self._build_row2()
        # Row 3: Activities + Fee Donut + Attendance
        self._build_row3()

        self.content_lay.addStretch()
        self.scroll.setWidget(self.scroll_content)
        root.addWidget(self.scroll)

        self.scroll.setStyleSheet("QScrollArea { background-color: #F1F5F9; border: none; }")

        # Native palette-backed background
        pal = self.scroll.viewport().palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#F1F5F9"))
        self.scroll.viewport().setPalette(pal)
        self.scroll.viewport().setAutoFillBackground(True)
        self.scroll_content.setPalette(pal)
        self.scroll_content.setAutoFillBackground(True)

        self.update_theme()

    def update_theme(self):
        t = ThemeManager.tokens()
        bg_col = QColor(t.get("bg_primary", "#F1F5F9"))
        pal = self.scroll.viewport().palette()
        pal.setColor(QPalette.ColorRole.Window, bg_col)
        self.scroll.viewport().setPalette(pal)
        self.scroll_content.setPalette(pal)

        self.lbl_title.setStyleSheet(f"color: {t['text_primary']}; font-weight: bold; background: transparent; border: none;")
        self.lbl_welcome.setStyleSheet(f"color: {t['text_secondary']}; font-weight: 500; background: transparent; border: none;")
        if hasattr(self, "donut"):
            self.donut.update()
        if hasattr(self, "bar_chart"):
            self.bar_chart.update()

    # ── HEADER ────────────────────────────────────────────────────────────────
    def _build_header(self):
        lay = QHBoxLayout()
        lay.setSpacing(12)

        icon_box = QLabel()
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet("background: #DBEAFE; border-radius: 10px; border: none;")
        icon_box.setPixmap(IconManager.get_pixmap("home", color="#2563EB", size=20))
        lay.addWidget(icon_box)

        col = QVBoxLayout()
        col.setSpacing(1)
        self.lbl_title = QLabel("Dashboard")
        self.lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")

        self.lbl_welcome = QLabel("Welcome back!")
        self.lbl_welcome.setFont(QFont("Segoe UI", 11))
        self.lbl_welcome.setStyleSheet("color: #64748B; font-weight: 500; background: transparent; border: none;")

        col.addWidget(self.lbl_title)
        col.addWidget(self.lbl_welcome)
        lay.addLayout(col)
        lay.addStretch()

        self.btn_toggle = QPushButton("  Show Financials")
        self.btn_toggle.setIcon(IconManager.get_icon("eye", color="#2563EB", size=14))
        self.btn_toggle.setIconSize(QSize(14, 14))
        self.btn_toggle.setFixedHeight(32)
        self.btn_toggle.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet(
            "QPushButton { background: #FFFFFF; color: #2563EB; border: 1px solid #DBEAFE; border-radius: 8px; padding: 4px 12px; }"
            "QPushButton:hover { background: #EFF6FF; border-color: #2563EB; }"
            "QPushButton:pressed { background: #DBEAFE; }"
        )
        self.btn_toggle.clicked.connect(self._toggle_finance)

        self.btn_hide = QPushButton("  Hide Financials")
        self.btn_hide.setIcon(IconManager.get_icon("eye-off", color="#64748B", size=14))
        self.btn_hide.setIconSize(QSize(14, 14))
        self.btn_hide.setFixedHeight(32)
        self.btn_hide.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.btn_hide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hide.setStyleSheet(
            "QPushButton { background: #FFFFFF; color: #64748B; border: 1px solid #E2E8F0; border-radius: 8px; padding: 4px 12px; }"
            "QPushButton:hover { background: #F8FAFC; border-color: #94A3B8; }"
            "QPushButton:pressed { background: #E2E8F0; }"
        )
        self.btn_hide.clicked.connect(self._toggle_finance)
        self.btn_hide.hide()

        lay.addWidget(self.btn_toggle)
        lay.addWidget(self.btn_hide)
        self.content_lay.addLayout(lay)

    # ── ROW 1: FINANCIAL RECORD + MONTHLY OVERVIEW ────────────────────────────
    def _build_row1(self):
        row = QHBoxLayout()
        row.setSpacing(18)
        row.addWidget(self._build_financial_card(), stretch=64)
        row.addWidget(self._build_monthly_chart(), stretch=36)
        self.content_lay.addLayout(row)

    def _build_financial_card(self):
        card = QFrame()
        card.setObjectName("dash_card")
        card.setStyleSheet("QFrame#dash_card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        # Title row
        title_row = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(34, 34)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: #ECFDF5; border-radius: 8px; border: none;")
        icon_lbl.setPixmap(IconManager.get_pixmap("wallet", color="#10B981", size=18))

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_lbl = QLabel("Financial Record")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")

        sub_lbl = QLabel("Income, Expenses, Profit/Loss and Dues")
        sub_lbl.setFont(QFont("Segoe UI", 10))
        sub_lbl.setStyleSheet("color: #64748B; font-weight: 500; background: transparent; border: none;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)

        title_row.addWidget(icon_lbl)
        title_row.addSpacing(8)
        title_row.addLayout(title_col)
        title_row.addStretch()
        lay.addLayout(title_row)

        grid = QHBoxLayout()
        grid.setSpacing(10)
        fin_defs = [
            ("arrow-up-right", "Total Profit",   "fin_profit",   "#16A34A", "#F0FDF4", "#DCFCE7", "↑ Real Data"),
            ("shield-alert",   "Total Loss",     "fin_loss",     "#DC2626", "#FEF2F2", "#FEE2E2", "↓ Real Data"),
            ("credit-card",    "Total Expenses", "fin_expenses", "#D97706", "#FFFBEB", "#FEF3C7", "• Outflows"),
            ("receipt",        "Total Dues",     "fin_dues",     "#7C3AED", "#FAF5FF", "#F3E8FF", "• Pending"),
        ]

        for icon_name, title, attr, color, bg_col, bdr_col, badge_txt in fin_defs:
            fc = QFrame()
            fc.setStyleSheet(
                f"QFrame {{ background-color: {bg_col}; border: 1px solid {bdr_col}; border-radius: 10px; }}"
            )
            fc.setMinimumHeight(90)
            fl = QVBoxLayout(fc)
            fl.setContentsMargins(12, 10, 12, 10)
            fl.setSpacing(4)

            il = QLabel()
            il.setFixedSize(26, 26)
            il.setAlignment(Qt.AlignmentFlag.AlignCenter)
            il.setStyleSheet("background: #FFFFFF; border-radius: 6px; border: none;")
            il.setPixmap(IconManager.get_pixmap(icon_name, color=color, size=15))

            tl = QLabel(title)
            tl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

            vl = QLabel("Rs. ******")
            vl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            vl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")

            al = QLabel(badge_txt)
            al.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            al.setStyleSheet(f"color: {color}; background: transparent; border: none;")

            setattr(self, attr, vl)
            self._finance_labels[attr] = vl

            target_map = {
                "fin_profit": 10,
                "fin_loss": 10,
                "fin_expenses": 10,
                "fin_dues": 4,
            }
            target_p = target_map.get(attr, 10)
            fc.setCursor(Qt.CursorShape.PointingHandCursor)
            fc.setToolTip("Click to view details in module")
            fc.mousePressEvent = lambda e, p=target_p: self._nav(p)

            fl.addWidget(il)
            fl.addWidget(tl)
            fl.addWidget(vl)
            fl.addWidget(al)
            fl.addStretch()
            grid.addWidget(fc)

        lay.addLayout(grid)
        return card

    def _build_monthly_chart(self):
        card = QFrame()
        card.setObjectName("dash_card")
        card.setStyleSheet("QFrame#dash_card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        icn = QLabel()
        icn.setFixedSize(32, 32)
        icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icn.setStyleSheet("background: #EFF6FF; border-radius: 8px; border: none;")
        icn.setPixmap(IconManager.get_pixmap("bar-chart-2", color="#2563EB", size=16))
        top.addWidget(icn)
        top.addSpacing(6)

        tl = QLabel("Monthly Overview")
        tl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        tl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        top.addWidget(tl)
        top.addStretch()

        leg = QHBoxLayout()
        leg.setSpacing(10)
        for name, color in [("Income", "#10B981"), ("Expenses", "#EF4444"), ("Profit", "#2563EB")]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent; border: none;")
            lbl = QLabel(name)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
            leg.addWidget(dot)
            leg.addWidget(lbl)
        top.addLayout(leg)
        lay.addLayout(top)

        self.bar_chart = BarChart()
        self.bar_chart.setMinimumHeight(135)
        lay.addWidget(self.bar_chart)
        return card

    # ── ROW 2: 4 METRIC CARDS ─────────────────────────────────────────────────
    def _build_row2(self):
        grid = QHBoxLayout()
        grid.setSpacing(12)
        kpis = [
            ("users-2",        "Active Students", "kpi_students", "Total enrolled students", "#EFF6FF", "#2563EB", 3),
            ("graduation-cap", "Active Teachers", "kpi_teachers", "Total working faculty",   "#F0FDFA", "#0D9488", 7),
            ("user-x",         "Today Absence",  "kpi_absent",   "Students absent today",   "#FEF2F2", "#EF4444", 5),
            ("check-circle",   "Today Present",  "kpi_present",  "Students present today",  "#F0FDF4", "#10B981", 5),
        ]
        for icon_name, title, attr, sub, bg, color, target_page in kpis:
            card = make_kpi_card(icon_name, title, attr, sub, bg, color, self, target_page=target_page)
            btn_arr = getattr(self, f"{attr}_arr")
            btn_arr.clicked.connect(lambda _, p=target_page: self._nav(p))
            grid.addWidget(card)
        self.content_lay.addLayout(grid)

    # ── ROW 3: ACTIVITIES + FEE + ATTENDANCE ──────────────────────────────────
    def _build_row3(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._build_activities_panel(), stretch=33)
        row.addWidget(self._build_fee_panel(),        stretch=34)
        row.addWidget(self._build_attendance_panel(), stretch=33)
        self.content_lay.addLayout(row)

    def _build_activities_panel(self):
        card = QFrame()
        card.setObjectName("dash_card")
        card.setStyleSheet("QFrame#dash_card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        icn = QLabel()
        icn.setFixedSize(28, 28)
        icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icn.setStyleSheet("background: #F1F5F9; border-radius: 7px; border: none;")
        icn.setPixmap(IconManager.get_pixmap("clock", color="#475569", size=15))
        hdr.addWidget(icn)
        hdr.addSpacing(6)

        tl = QLabel("Recent Activities")
        tl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        tl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        hdr.addWidget(tl)
        hdr.addStretch()

        va = QPushButton("View All ")
        va.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        va.setCursor(Qt.CursorShape.PointingHandCursor)
        va.setIcon(IconManager.get_icon("arrow-right", color="#2563EB", size=12))
        va.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        va.setStyleSheet("background: transparent; color: #2563EB; border: none;")
        va.clicked.connect(lambda checked=False: self._nav(10))
        hdr.addWidget(va)
        lay.addLayout(hdr)

        self.activities_lay = QVBoxLayout()
        self.activities_lay.setSpacing(6)
        lay.addLayout(self.activities_lay)
        lay.addStretch()
        return card

    def _build_fee_panel(self):
        card = QFrame()
        card.setObjectName("dash_card")
        card.setStyleSheet("QFrame#dash_card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        icn = QLabel()
        icn.setFixedSize(28, 28)
        icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icn.setStyleSheet("background: #ECFDF5; border-radius: 7px; border: none;")
        icn.setPixmap(IconManager.get_pixmap("pie-chart", color="#10B981", size=15))
        hdr.addWidget(icn)
        hdr.addSpacing(6)

        tl = QLabel("Fee Collection Overview")
        tl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        tl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        hdr.addWidget(tl)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Donut + legend
        mid = QHBoxLayout()
        mid.setSpacing(10)
        self.donut = DonutChart()
        mid.addWidget(self.donut, alignment=Qt.AlignmentFlag.AlignLeft)

        legend_col = QVBoxLayout()
        legend_col.setSpacing(4)
        self.fee_legend_items = {}
        for color, key, label in [
            ("#10B981", "collected", "Collected"),
            ("#2563EB", "due",       "Due"),
            ("#D97706", "overdue",   "Overdue"),
        ]:
            lr = QHBoxLayout()
            lr.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent; border: none;")
            lbl_name = QLabel(label)
            lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: #64748B; background: transparent; border: none;")
            lbl_val = QLabel("Rs. 0")
            lbl_val.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_val.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
            self.fee_legend_items[key] = lbl_val
            lr.addWidget(dot)
            lr.addWidget(lbl_name)
            lr.addStretch()
            lr.addWidget(lbl_val)
            legend_col.addLayout(lr)

        legend_col.addStretch()
        mid.addLayout(legend_col)
        lay.addLayout(mid)

        # Quick Actions
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet("background: #E2E8F0; border: none;")
        lay.addWidget(sep)

        qa_hdr = QHBoxLayout()
        qa_icn = QLabel()
        qa_icn.setFixedSize(24, 24)
        qa_icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qa_icn.setStyleSheet("background: #FEF3C7; border-radius: 6px; border: none;")
        qa_icn.setPixmap(IconManager.get_pixmap("zap", color="#D97706", size=13))
        qa_hdr.addWidget(qa_icn)
        qa_hdr.addSpacing(6)

        qa_lbl = QLabel("Quick Actions")
        qa_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        qa_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        qa_hdr.addWidget(qa_lbl)
        qa_hdr.addStretch()
        lay.addLayout(qa_hdr)

        btn_grid = QGridLayout()
        btn_grid.setSpacing(6)
        qa_btns = [
            ("user-plus",      "Add Student",    "#2563EB", "#EFF6FF", "#DBEAFE", "qa_add_student", 3),
            ("graduation-cap", "Add Teacher",    "#0D9488", "#F0FDFA", "#CCFBF1", "qa_add_teacher", 7),
            ("coins",          "Add Fee Record", "#10B981", "#F0FDF4", "#DCFCE7", "qa_add_fee",     4),
            ("send",           "Send Message",   "#D97706", "#FFFBEB", "#FEF3C7", "qa_send_msg",    9),
            ("package",        "Store / Stock",  "#0891B2", "#ECFEFF", "#CFFAFE", "qa_inventory",   14),
            ("folder",         "Documents",      "#6366F1", "#EEF2FF", "#E0E7FF", "qa_documents",   15),
        ]
        for i, (icon_name, lbl_txt, color, bg_col, bdr_col, attr, page_idx) in enumerate(qa_btns):
            btn = QPushButton(f"  {lbl_txt}")
            btn.setIcon(IconManager.get_icon(icon_name, color=color, size=14))
            btn.setIconSize(QSize(14, 14))
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_col}; color: {color}; border: 1px solid {bdr_col}; "
                f"border-radius: 8px; padding: 6px 6px; text-align: center; }} "
                f"QPushButton:hover {{ background-color: {bdr_col}; }}"
            )
            btn.setMinimumHeight(30)
            btn.clicked.connect(lambda _, p=page_idx: self._nav(p))
            btn_grid.addWidget(btn, i // 2, i % 2)
            setattr(self, attr, btn)

        lay.addLayout(btn_grid)
        lay.addStretch()
        return card

    def _nav(self, page_index: int):
        top = self.window()
        if hasattr(top, "navigate_to_page"):
            top.navigate_to_page(page_index)
        elif hasattr(top, "stack"):
            top.stack.setCurrentIndex(page_index)

    def _build_attendance_panel(self):
        card = QFrame()
        card.setObjectName("dash_card")
        card.setStyleSheet("QFrame#dash_card { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        icn = QLabel()
        icn.setFixedSize(28, 28)
        icn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icn.setStyleSheet("background: #F0FDFA; border-radius: 7px; border: none;")
        icn.setPixmap(IconManager.get_pixmap("calendar-check", color="#0D9488", size=15))
        hdr.addWidget(icn)
        hdr.addSpacing(6)

        tl = QLabel("Today's Attendance")
        tl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        tl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
        hdr.addWidget(tl)
        hdr.addStretch()

        va_att = QPushButton("View All ")
        va_att.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        va_att.setCursor(Qt.CursorShape.PointingHandCursor)
        va_att.setIcon(IconManager.get_icon("arrow-right", color="#2563EB", size=12))
        va_att.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        va_att.setStyleSheet("background: transparent; color: #2563EB; border: none;")
        va_att.clicked.connect(lambda checked=False: self._nav(5))
        hdr.addWidget(va_att)
        lay.addLayout(hdr)

        # Present / Absent / Late row (Pills matching Stitch)
        pal = QHBoxLayout()
        pal.setSpacing(8)
        for icon_name, attr, label, color, bg_col, bdr_col in [
            ("check-circle", "att_present_lbl", "Present", "#10B981", "#F0FDF4", "#DCFCE7"),
            ("user-x",       "att_absent_lbl",  "Absent",  "#EF4444", "#FEF2F2", "#FEE2E2"),
            ("clock",        "att_late_lbl",    "Late",    "#D97706", "#FFFBEB", "#FEF3C7"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            box = QFrame()
            box.setStyleSheet(f"QFrame {{ background: {bg_col}; border: 1px solid {bdr_col}; border-radius: 8px; }} QFrame:hover {{ border-color: {color}; }}")
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            box.setToolTip(f"Click to open {label} attendance register")
            box.mousePressEvent = lambda e: self._nav(5)
            bl = QVBoxLayout(box)
            bl.setContentsMargins(8, 8, 8, 8)
            bl.setSpacing(2)
            bl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            il = QLabel()
            il.setFixedSize(22, 22)
            il.setAlignment(Qt.AlignmentFlag.AlignCenter)
            il.setStyleSheet("background: transparent; border: none;")
            il.setPixmap(IconManager.get_pixmap(icon_name, color=color, size=15))

            vl = QLabel("0%")
            vl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl.setStyleSheet(f"color: {color}; background: transparent; border: none;")

            ll = QLabel(label)
            ll.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ll.setStyleSheet("color: #475569; background: transparent; border: none;")

            setattr(self, attr, vl)
            bl.addWidget(il)
            bl.addWidget(vl)
            bl.addWidget(ll)
            col.addWidget(box)
            pal.addLayout(col)

        lay.addLayout(pal)

        # Class-wise bars
        cw_lbl = QLabel("Class-wise Attendance")
        cw_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        cw_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none; margin-top: 4px;")
        lay.addWidget(cw_lbl)

        self.class_att_lay = QVBoxLayout()
        self.class_att_lay.setSpacing(6)
        lay.addLayout(self.class_att_lay)
        lay.addStretch()
        return card

    # ── DATA REFRESH ──────────────────────────────────────────────────────────
    def refresh_data(self):
        user = getattr(app_state, "current_username", "Admin") or "Admin"
        
        # FIX: Ensure Dashboard correctly reads multi-key aliases for Institution Name
        inst_name = DocumentService.get_setting("name", "UEMS")
        if inst_name and inst_name != "UEMS":
            self.lbl_welcome.setText(f"Welcome back to {inst_name}, {user.capitalize()}!")
        else:
            self.lbl_welcome.setText(f"Welcome back, {user.capitalize()}!")

        # -------------------------------------------------------------
        # NEW SMART ATTENDANCE REMINDER CHECK
        # -------------------------------------------------------------
        try:
            if hasattr(AttendanceService, "get_attendance_reminder_status"):
                rem_status = AttendanceService.get_attendance_reminder_status()
                if not rem_status.get("all_marked", True) and rem_status.get("message"):
                    self.lbl_banner_msg.setText(rem_status["message"])
                    self.attendance_banner.show()
                else:
                    self.attendance_banner.hide()
        except Exception as e:
            print(f"Error loading attendance banner: {e}")
            if hasattr(self, 'attendance_banner'):
                self.attendance_banner.hide()

        # -------------------------------------------------------------
        # SMART MONTHLY FEE REMINDER CHECK
        # -------------------------------------------------------------
        try:
            if hasattr(FeeService, "get_fee_reminder_status"):
                fee_rem = FeeService.get_fee_reminder_status()
                if not fee_rem.get("all_generated", True) and fee_rem.get("message"):
                    self.lbl_fee_banner_msg.setText(fee_rem["message"])
                    self.fee_banner.show()
                else:
                    self.fee_banner.hide()
        except Exception as e:
            print(f"Error loading fee reminder banner: {e}")
            if hasattr(self, 'fee_banner'):
                self.fee_banner.hide()
        # -------------------------------------------------------------

        # 1. Financial metrics (100% Live DB Sync)
        profit = 0.0
        loss = 0.0
        expenses = 0.0
        dues = 0.0

        if AnalyticsService and hasattr(AnalyticsService, "get_executive_kpis"):
            try:
                kpis = AnalyticsService.get_executive_kpis()
                revenue  = float(kpis.get("total_revenue", 0) or 0)
                expenses = float(kpis.get("total_operating_expenses", 0) or kpis.get("total_expenses", 0) or 0)
                store_purchases = float(kpis.get("total_store_purchases", 0) or 0)
                dues     = float(kpis.get("outstanding_fees", 0) or kpis.get("outstanding_dues", 0) or 0)
                net      = float(kpis.get("net_operating_surplus", 0) or (revenue - expenses))
                cash_flow = float(kpis.get("net_cash_surplus", 0) or (revenue - (expenses + store_purchases)))
                if net >= 0:
                    profit = net
                    loss = 0.0
                else:
                    profit = 0.0
                    loss = abs(net)

                if hasattr(self, "fin_expenses"):
                    self.fin_expenses.setToolTip(
                        f"Operational Utility Expenses: Rs. {int(expenses):,}\nStore Capital Purchases: Rs. {int(store_purchases):,}\nTotal Outflows: Rs. {int(expenses + store_purchases):,}"
                    )
                if hasattr(self, "fin_profit"):
                    self.fin_profit.setToolTip(
                        f"Net Operating Surplus: Rs. {int(profit):,}\nNet Cash Flow Surplus: Rs. {int(cash_flow):,}"
                    )
            except Exception as e:
                print(f"Error fetching executive KPIs: {e}")

        self._raw_finance = {
            "fin_profit":   profit,
            "fin_loss":     loss,
            "fin_expenses": expenses,
            "fin_dues":     dues,
        }
        self._render_finance_values()

        # 2. Monthly Trend Chart (100% Live Real DB Data)
        chart_data = {}
        if AnalyticsService and hasattr(AnalyticsService, "get_monthly_revenue_trend"):
            try:
                trend = AnalyticsService.get_monthly_revenue_trend()
                for item in trend:
                    m = item.get("month", "")
                    inc = float(item.get("income", 0))
                    exp = float(item.get("expense", 0))
                    prof = max(0.0, inc - exp)
                    chart_data[m] = (inc, exp, prof)
            except Exception as e:
                print(f"Error loading revenue trend: {e}")

        if not chart_data:
            # Show empty months if no data exists yet
            for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]:
                chart_data[m] = (0.0, 0.0, 0.0)

        self.bar_chart.set_data(chart_data)

        # 3. Row 2 Metrics (100% Live Counts from DB)
        total_students = 0
        total_teachers = 0
        try:
            total_students = StudentService.get_student_count()
        except Exception:
            try:
                total_students = StudentService.count_active_students()
            except Exception:
                total_students = 0

        try:
            from core.hr_service import HRService
            total_teachers = HRService.get_teacher_count()
        except Exception:
            total_teachers = 0

        today_absent = 0
        today_present = 0
        try:
            att = AttendanceService.get_dashboard_analytics() if hasattr(AttendanceService, "get_dashboard_analytics") else {}
            today_present = att.get("present", 0) or att.get("present_today", 0) or 0
            today_absent  = att.get("absent", 0) or att.get("absent_today", 0) or 0
        except Exception:
            pass

        self.kpi_students.setText(str(total_students))
        self.kpi_teachers.setText(str(total_teachers))
        self.kpi_absent.setText(str(today_absent))
        self.kpi_present.setText(str(today_present))

        # 4. Fee Donut Chart (100% Real Live DB Data)
        collected = 0.0
        due = 0.0
        overdue = 0.0
        try:
            stats = FeeService.get_fee_collection_stats()
            collected = float(stats.get("collected", 0) or 0)
            due       = float(stats.get("due", 0) or 0)
            overdue   = float(stats.get("overdue", 0) or 0)
        except Exception as e:
            print(f"Error fetching fee collection stats: {e}")

        tot_fee = collected + due + overdue
        pct = int(collected / tot_fee * 100) if tot_fee > 0 else 0
        self.donut.set_data(
            [(collected, "#10B981"), (due, "#2563EB"), (overdue, "#D97706")],
            f"{pct}%", "Collected"
        )
        if "collected" in self.fee_legend_items:
            self.fee_legend_items["collected"].setText(f"Rs. {int(collected):,}")
        if "due" in self.fee_legend_items:
            self.fee_legend_items["due"].setText(f"Rs. {int(due):,}")
        if "overdue" in self.fee_legend_items:
            self.fee_legend_items["overdue"].setText(f"Rs. {int(overdue):,}")

        # 5. Today Attendance percentages
        tot_att = today_present + today_absent
        p_pct = int(today_present / tot_att * 100) if tot_att > 0 else 0
        a_pct = int(today_absent  / tot_att * 100) if tot_att > 0 else 0
        self.att_present_lbl.setText(f"{p_pct}%")
        self.att_absent_lbl.setText(f"{a_pct}%")
        self.att_late_lbl.setText("0%")

        # 6. Class-Wise Attendance (Real Classes from DB - Reused In-Place)
        try:
            classes = AcademicService.get_classes() if hasattr(AcademicService, "get_classes") else []
        except Exception:
            classes = []

        if not classes:
            # Clear any old class items if empty
            while self.class_att_lay.count():
                item = self.class_att_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self._class_att_widgets.clear()
            no_cls_lbl = QLabel("No classes configured yet.")
            no_cls_lbl.setStyleSheet("color: #334155; font-size: 11px;")
            self.class_att_lay.addWidget(no_cls_lbl)
        else:
            # If a "No classes" label was present, clear it
            if self.class_att_lay.count() == 1 and not self._class_att_widgets:
                item = self.class_att_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            target_classes = classes[:5]
            # Ensure we have enough reusable row widgets
            while len(self._class_att_widgets) < len(target_classes):
                crow = QHBoxLayout()
                crow.setSpacing(8)
                cn_lbl = QLabel("")
                cn_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                cn_lbl.setFixedWidth(90)
                cn_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")

                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(100)
                bar.setFixedHeight(8)
                bar.setTextVisible(False)
                bar.setStyleSheet(
                    "QProgressBar { background: #F1F5F9; border-radius: 4px; border: none; }"
                    "QProgressBar::chunk { background: #0D9488; border-radius: 4px; }"
                )

                cp_lbl = QLabel("100%")
                cp_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                cp_lbl.setFixedWidth(64)
                cp_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                cp_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")

                crow.addWidget(cn_lbl)
                crow.addWidget(bar)
                crow.addWidget(cp_lbl)

                w = QWidget()
                w.setLayout(crow)
                self.class_att_lay.addWidget(w)
                self._class_att_widgets.append((w, cn_lbl, bar, cp_lbl))

            # Hide any excess rows
            for i in range(len(target_classes), len(self._class_att_widgets)):
                self._class_att_widgets[i][0].hide()

            # Calculate real class attendance percentages from DB for today
            from database.connection import get_session
            from database.models.attendance import AttendanceRecord
            from database.models.student import Student
            db_cls = get_session()
            cls_stats = {}
            try:
                today_s = date.today().strftime("%Y-%m-%d")
                for c in target_classes:
                    enrolled = db_cls.query(Student).filter_by(class_id=c.id, status='Active').count()
                    records = db_cls.query(AttendanceRecord).filter_by(class_id=c.id, date=today_s).all()
                    if records:
                        p_count = sum(1 for r in records if r.status in ['Present', 'Late'])
                        pct = int((p_count / len(records)) * 100) if len(records) > 0 else 0
                        cls_stats[c.id] = (pct, f"{pct}%")
                    elif enrolled > 0:
                        cls_stats[c.id] = (0, "Pending")
                    else:
                        cls_stats[c.id] = (100, "100%")
            except Exception as e:
                print(f"Error calculating class attendance: {e}")
            finally:
                db_cls.close()

            # Update rows in-place
            for i, cls_obj in enumerate(target_classes):
                w, cn_lbl, bar, cp_lbl = self._class_att_widgets[i]
                cname = f"Class {cls_obj.name}" if not cls_obj.name.lower().startswith("class") else cls_obj.name
                cpct, cpct_str = cls_stats.get(cls_obj.id, (100, "100%"))
                cn_lbl.setText(cname)
                bar.setValue(cpct)
                cp_lbl.setText(cpct_str)
                if cpct_str == "Pending":
                    cp_lbl.setStyleSheet("color: #D97706; font-weight: bold; background: transparent; border: none;")
                    bar.setStyleSheet(
                        "QProgressBar { background: #F1F5F9; border-radius: 4px; border: none; }"
                        "QProgressBar::chunk { background: #F59E0B; border-radius: 4px; }"
                    )
                else:
                    cp_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")
                    bar.setStyleSheet(
                        "QProgressBar { background: #F1F5F9; border-radius: 4px; border: none; }"
                        "QProgressBar::chunk { background: #0D9488; border-radius: 4px; }"
                    )
                w.setCursor(Qt.CursorShape.PointingHandCursor)
                w.setToolTip(f"Click to open attendance register for {cname}")
                w.mousePressEvent = lambda e: self._nav(5)
                w.show()

        # 7. Recent Activities (Real DB Records - Reused In-Place)
        real_activities = []
        today_s = date.today().strftime("%Y-%m-%d")
        try:
            from database.connection import get_session
            from database.models.fee import FeePayment
            from database.models.student import Student
            from database.models.hr import PayrollRecord
            from database.models.calendar import CalendarEvent
            from database.models.attendance import AttendanceRecord
            from database.models.inventory import StockTransaction
            from database.models.library import BookIssue
            db_act = get_session()
            try:
                # 1. Latest fee payments
                latest_payments = db_act.query(FeePayment).order_by(FeePayment.id.desc()).limit(4).all()
                for p in latest_payments:
                    p_date = p.payment_date or today_s
                    if p_date > today_s:
                        p_date = today_s
                    real_activities.append({
                        "id": p.id,
                        "time_key": p_date,
                        "icon_name": "coins",
                        "title": "Fee Payment Received",
                        "sub": f"Receipt {p.receipt_no} • Rs. {int(p.amount_paid):,} recorded on {p_date}",
                        "color": "#10B981",
                        "bg": "#F0FDF4",
                        "target_page": 4,
                    })

                # 2. Latest students enrolled
                latest_students = db_act.query(Student).order_by(Student.id.desc()).limit(3).all()
                for s in latest_students:
                    s_name = f"{s.first_name} {s.last_name or ''}".strip()
                    cls_name = s.academic_class.name if s.academic_class else "School"
                    adm_date = getattr(s, 'admission_date', '') or today_s
                    if adm_date > today_s:
                        adm_date = today_s
                    real_activities.append({
                        "id": s.id,
                        "time_key": adm_date,
                        "icon_name": "users-2",
                        "title": "Student Enrolled",
                        "sub": f"{s_name} ({s.student_id}) enrolled in Class {cls_name}",
                        "color": "#2563EB",
                        "bg": "#EFF6FF",
                        "target_page": 3,
                    })

                # 3. Latest stock movements / adjustments
                try:
                    latest_tx = db_act.query(StockTransaction).order_by(StockTransaction.id.desc()).limit(3).all()
                    for tx in latest_tx:
                        it_name = tx.item.name if tx.item else "Store Item"
                        tx_t = (tx.transaction_type or "Adjustment").capitalize()
                        tx_d = (tx.transaction_date or today_s)[:10]
                        if tx_d > today_s:
                            tx_d = today_s
                        real_activities.append({
                            "id": tx.id,
                            "time_key": tx_d,
                            "icon_name": "package",
                            "title": f"Stock {tx_t}",
                            "sub": f"{it_name[:24]} ({tx.quantity:+.1f} {tx.item.unit if tx.item else 'units'}) on {tx_d}",
                            "color": "#0891B2",
                            "bg": "#ECFEFF",
                            "target_page": 14,
                        })
                except Exception:
                    pass

                # 4. Latest attendance marked
                latest_att = db_act.query(AttendanceRecord).order_by(AttendanceRecord.id.desc()).limit(1).all()
                for a in latest_att:
                    att_date = str(a.date) if a.date else today_s
                    if att_date > today_s:
                        att_date = today_s
                    real_activities.append({
                        "id": a.id,
                        "time_key": att_date,
                        "icon_name": "user-check",
                        "title": "Attendance Recorded",
                        "sub": f"Daily class attendance logged for {att_date}",
                        "color": "#0D9488",
                        "bg": "#F0FDFA",
                        "target_page": 5,
                    })

                # 5. Latest payroll disbursed
                latest_payroll = db_act.query(PayrollRecord).filter_by(status='Paid').order_by(PayrollRecord.id.desc()).limit(2).all()
                for pr in latest_payroll:
                    pay_date = pr.payment_date or today_s
                    if pay_date > today_s:
                        pay_date = today_s
                    real_activities.append({
                        "id": pr.id,
                        "time_key": pay_date,
                        "icon_name": "receipt",
                        "title": "Salary Disbursed",
                        "sub": f"Payroll {pr.receipt_no} • Rs. {int(pr.net_salary):,} for {pr.pay_month}",
                        "color": "#D97706",
                        "bg": "#FFFBEB",
                        "target_page": 7,
                    })

                # 6. Latest library books issued
                latest_books = db_act.query(BookIssue).filter_by(status='Issued').order_by(BookIssue.id.desc()).limit(2).all()
                for b in latest_books:
                    raw_issue = getattr(b, 'issued_date', getattr(b, 'issue_date', None))
                    issue_d = raw_issue.strftime("%Y-%m-%d") if hasattr(raw_issue, 'strftime') else str(raw_issue or today_s)
                    if issue_d > today_s:
                        issue_d = today_s
                    due_d = b.due_date.strftime("%Y-%m-%d") if hasattr(b.due_date, 'strftime') else str(b.due_date or '')
                    real_activities.append({
                        "id": b.id,
                        "time_key": issue_d,
                        "icon_name": "book-open",
                        "title": "Library Book Issued",
                        "sub": f"Book ID {b.book_id} issued, due on {due_d}",
                        "color": "#3B82F6",
                        "bg": "#EFF6FF",
                        "target_page": 11,
                    })

                # 7. Calendar events ONLY if already started or active today (NOT future months)
                latest_events = db_act.query(CalendarEvent).filter(CalendarEvent.start_date <= today_s).order_by(CalendarEvent.start_date.desc()).limit(2).all()
                for ev in latest_events:
                    real_activities.append({
                        "id": ev.id,
                        "time_key": ev.start_date or today_s,
                        "icon_name": "calendar-days",
                        "title": f"Event: {ev.title}",
                        "sub": f"{ev.event_type or 'School Event'} • Held on {ev.start_date}",
                        "color": "#8B5CF6",
                        "bg": "#FAF5FF",
                        "target_page": 13,
                    })
            finally:
                db_act.close()
        except Exception as e:
            print(f"Error loading recent activities from DB: {e}")

        # Sort by time_key descending, then id descending
        real_activities.sort(key=lambda x: (x.get("time_key") or "", x.get("id", 0)), reverse=True)

        if not real_activities:
            real_activities = [
                {"icon_name": "coins", "title": "Fee Management Active", "sub": "System ready to process voucher payments", "color": "#10B981", "bg": "#F0FDF4", "target_page": 4},
                {"icon_name": "user-check", "title": "Attendance Ready", "sub": "Ready to log daily classroom attendance", "color": "#0D9488", "bg": "#F0FDFA", "target_page": 5},
                {"icon_name": "calendar-days", "title": "School Calendar Live", "sub": "Add events and examinations in Calendar", "color": "#8B5CF6", "bg": "#FAF5FF", "target_page": 13},
            ]

        target_acts = real_activities[:5]
        # Ensure we have enough reusable row widgets
        while len(self._activity_widgets) < len(target_acts):
            arow = QHBoxLayout()
            arow.setSpacing(10)

            dot = QLabel()
            dot.setFixedSize(32, 32)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

            col_a = QVBoxLayout()
            col_a.setSpacing(2)
            t_lbl = QLabel("")
            t_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            t_lbl.setStyleSheet("color: #0F172A; font-weight: bold; background: transparent; border: none;")

            s_lbl = QLabel("")
            s_lbl.setFont(QFont("Segoe UI", 9))
            s_lbl.setStyleSheet("color: #64748B; font-weight: 500; background: transparent; border: none;")
            col_a.addWidget(t_lbl)
            col_a.addWidget(s_lbl)

            arow.addWidget(dot)
            arow.addLayout(col_a)
            arow.addStretch()

            w = QWidget()
            w.setLayout(arow)
            self.activities_lay.addWidget(w)
            self._activity_widgets.append((w, dot, t_lbl, s_lbl))

        # Hide any excess rows
        for i in range(len(target_acts), len(self._activity_widgets)):
            self._activity_widgets[i][0].hide()

        # Update rows in-place
        for i, act in enumerate(target_acts):
            w, dot, t_lbl, s_lbl = self._activity_widgets[i]
            dot.setPixmap(IconManager.get_pixmap(act["icon_name"], color=act["color"], size=16))
            dot.setStyleSheet(f"background: {act.get('bg', '#F1F5F9')}; border-radius: 8px; border: none;")
            t_lbl.setText(act["title"])
            s_lbl.setText(act["sub"])
            target_p = act.get("target_page", 0)
            w.setCursor(Qt.CursorShape.PointingHandCursor)
            w.setToolTip(f"Click to navigate to {act['title']}")
            w.mousePressEvent = lambda e, p=target_p: self._nav(p)
            w.show()

    def _toggle_finance(self):
        if self.finance_hidden:
            # Unhide and start 10-second auto-hide timer
            self.finance_hidden = False
            self.btn_toggle.hide()
            self.btn_hide.show()
            self._render_finance_values()
            self._finance_timer.start(10000)
        else:
            self._auto_hide_finance()

    def _auto_hide_finance(self):
        self.finance_hidden = True
        self.btn_toggle.show()
        self.btn_hide.hide()
        self._finance_timer.stop()
        self._render_finance_values()

    def _render_finance_values(self):
        for attr, lbl in self._finance_labels.items():
            if self.finance_hidden:
                lbl.setText("Rs. ●●●●●●")
            else:
                val = self._raw_finance.get(attr, 0.0)
                lbl.setText(f"Rs. {int(val):,}")