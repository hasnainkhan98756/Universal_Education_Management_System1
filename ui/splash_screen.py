import os
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGraphicsDropShadowEffect, QFrame, QApplication
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QRect
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter, QPainterPath

from core.state_manager import app_state
from core.icon_manager import IconManager
from config import initialize_directories
from database.connection import init_db
from core.theme_manager import ThemeManager


class AppSplashScreen(QWidget):
    """
    High-Performance, Stitch-Styled Frameless Application Startup Screen.
    Displays dynamic institute branding, animated progress, and initializes
    core application services smoothly without freezing the UI.
    """
    initialization_complete = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(580, 360)

        # Center on primary screen
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

        self._current_step = 0
        self._target_progress = 0
        self._init_ui()

    def _init_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(15, 15, 15, 15)

        # Card container with deep luxury gradient and subtle glow border
        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B1224, stop:0.5 #111D35, stop:1 #162040);
                border-radius: 20px;
                border: 1.5px solid rgba(59, 130, 246, 0.35);
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(28, 24, 28, 24)
        card_lay.setSpacing(14)

        # ── Top Badge Row ──────────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.pill_badge = QLabel("●  UNIVERSAL EDUCATION MANAGEMENT SYSTEM (UEMS)")
        self.pill_badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.pill_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(37, 99, 235, 0.22);
                color: #60A5FA;
                border: 1px solid rgba(96, 165, 250, 0.45);
                border-radius: 12px;
                padding: 4px 12px;
            }
        """)
        top_row.addWidget(self.pill_badge)
        top_row.addStretch()

        self.lbl_ver = QLabel("v1.0.0 Enterprise")
        self.lbl_ver.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        self.lbl_ver.setStyleSheet("color: #64748B; background: transparent; border: none;")
        top_row.addWidget(self.lbl_ver)
        card_lay.addLayout(top_row)

        card_lay.addSpacing(6)

        # ── Center Brand Row (Logo + Institute Name) ───────────────────────────
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(0, 0, 0, 0)
        brand_row.setSpacing(18)

        # Logo Widget (Circular or rounded square)
        self.logo_lbl = QLabel()
        self.logo_lbl.setFixedSize(68, 68)
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_lbl.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563EB, stop:1 #0EA5E9);
                border-radius: 16px;
                border: 2px solid rgba(255, 255, 255, 0.2);
            }
        """)
        self._load_logo()
        brand_row.addWidget(self.logo_lbl)

        # Text Column
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(3)

        inst_name = self._get_institute_name()
        self.lbl_inst_name = QLabel(inst_name)
        self.lbl_inst_name.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_inst_name.setStyleSheet("color: #F8FAFC; background: transparent; border: none;")
        self.lbl_inst_name.setWordWrap(True)
        text_col.addWidget(self.lbl_inst_name)

        tagline = app_state.get_setting("address", "") or "Empowering Educational Excellence & Student Success"
        self.lbl_tagline = QLabel(tagline)
        self.lbl_tagline.setFont(QFont("Segoe UI", 10))
        self.lbl_tagline.setStyleSheet("color: #38BDF8; background: transparent; border: none; font-weight: 500;")
        self.lbl_tagline.setWordWrap(True)
        text_col.addWidget(self.lbl_tagline)

        brand_row.addLayout(text_col, stretch=1)
        card_lay.addLayout(brand_row)

        card_lay.addStretch()

        # ── Status and Percentage Row ──────────────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel("Starting system core...")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.lbl_status.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()

        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_percent.setStyleSheet("color: #38BDF8; background: transparent; border: none;")
        status_row.addWidget(self.lbl_percent)
        card_lay.addLayout(status_row)

        # ── Glowing Modern Progress Bar ────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0F172A;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:0.5 #3B82F6, stop:1 #38BDF8);
                border-radius: 4px;
            }
        """)
        card_lay.addWidget(self.progress_bar)

        # ── Footer Row ─────────────────────────────────────────────────────────
        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 2, 0, 0)

        inst_short = inst_name.split()[0] if inst_name else "Institute"
        self.lbl_foot_left = QLabel(f"Licensed to {inst_short} • High Performance Enterprise Core")
        self.lbl_foot_left.setFont(QFont("Segoe UI", 8))
        self.lbl_foot_left.setStyleSheet("color: #475569; background: transparent; border: none;")
        foot_row.addWidget(self.lbl_foot_left)
        foot_row.addStretch()

        lbl_foot_right = QLabel("Secure & Audited")
        lbl_foot_right.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        lbl_foot_right.setStyleSheet("color: #10B981; background: transparent; border: none;")
        foot_row.addWidget(lbl_foot_right)
        card_lay.addLayout(foot_row)

        root_lay.addWidget(self.card)

    def _get_institute_name(self) -> str:
        name = app_state.get_setting("institution_name", "") or app_state.get_setting("name", "") or app_state.get_setting("app_title", "")
        if not name or name.strip() == "":
            name = "Universal Education Management System"
        return name

    def _load_logo(self):
        logo_path = app_state.get_setting("logo_path", "") or app_state.get_setting("institution_logo", "")
        if logo_path and os.path.exists(logo_path):
            try:
                pix = QPixmap(logo_path)
                if not pix.isNull():
                    scaled = pix.scaled(
                        60, 60,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    # Create rounded mask for clean appearance
                    rounded = QPixmap(60, 60)
                    rounded.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(rounded)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    path = QPainterPath()
                    path.addRoundedRect(0, 0, 60, 60, 14, 14)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled)
                    painter.end()

                    self.logo_lbl.setPixmap(rounded)
                    return
            except Exception:
                pass

        # Fallback vector icon
        self.logo_lbl.setPixmap(IconManager.get_pixmap("graduation-cap", color="#FFFFFF", size=36))

    def update_branding(self):
        """Refreshes institute name and logo if changed during load."""
        inst_name = self._get_institute_name()
        self.lbl_inst_name.setText(inst_name)
        self._load_logo()
        inst_short = inst_name.split()[0] if inst_name else "Institute"
        self.lbl_foot_left.setText(f"Licensed to {inst_short} • High Performance Enterprise Core")

    def start_initialization(self, finish_callback):
        """
        Executes startup steps sequentially with smooth progress feedback.
        """
        self._finish_callback = finish_callback
        self._steps = [
            (15, "Initializing system directories & user data storage...", self._step_init_dirs),
            (35, "Connecting institutional database & caching tables...", self._step_init_db),
            (55, "Verifying schema migrations & system integrity...", self._step_upgrade_db),
            (75, "Loading institutional profiles, settings & credentials...", self._step_load_settings),
            (90, "Applying theme & design system...", self._step_apply_theme),
            (100, "Ready! Launching Universal Education Management System...", self._step_complete),
        ]
        self._current_step_idx = 0
        QTimer.singleShot(50, self._run_next_step)

    def _step_init_dirs(self):
        initialize_directories()

    def _step_init_db(self):
        init_db()

    def _step_upgrade_db(self):
        from main import safe_db_upgrade
        safe_db_upgrade()

    def _step_load_settings(self):
        app_state.load_settings()
        self.update_branding()

    def _step_apply_theme(self):
        saved_theme = app_state.get_setting("theme_mode", "Light")
        ThemeManager.apply(saved_theme)

    def _step_complete(self):
        pass

    def _run_next_step(self):
        if self._current_step_idx < len(self._steps):
            percent, msg, action = self._steps[self._current_step_idx]
            self.lbl_status.setText(msg)
            self.lbl_percent.setText(f"{percent}%")
            self.progress_bar.setValue(percent)
            QApplication.processEvents()

            try:
                action()
            except Exception as e:
                print(f"Startup warning on step {self._current_step_idx}: {e}")

            self._current_step_idx += 1
            # Very snappy 80ms interval between steps for fluid, brisk startup
            QTimer.singleShot(80, self._run_next_step)
        else:
            # Done! Smooth fade out
            QTimer.singleShot(100, self._fade_out_and_finish)

    def _fade_out_and_finish(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(220)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.finished.connect(self._on_fade_finished)
        self.anim.start()

    def _on_fade_finished(self):
        self.close()
        if hasattr(self, "_finish_callback") and self._finish_callback:
            self._finish_callback()
