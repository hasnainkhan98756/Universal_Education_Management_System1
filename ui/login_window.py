import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QMessageBox, QFrame, 
                               QGraphicsDropShadowEffect, QHBoxLayout)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QColor
from core.state_manager import app_state
from core.theme_manager import ThemeManager

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Login")
        self.setFixedSize(450, 500)
        self.setWindowOpacity(0.0)

        t = ThemeManager.tokens()
        is_dark = ThemeManager.is_dark()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        if is_dark:
            central_widget.setStyleSheet(
                "QWidget { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0B1224, stop:1 #111D35); }"
            )
        else:
            central_widget.setStyleSheet(
                "QWidget { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E3C72, stop:1 #2A5298); }"
            )
        main_layout = QVBoxLayout(central_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.login_card = QFrame()
        self.login_card.setFixedSize(350, 400)
        self.login_card.setStyleSheet(f"""
            QFrame {{ background-color: {t['bg_card']}; border-radius: 16px; border: 1px solid {t['border']}; }}
            QLabel {{ background-color: transparent; color: {t['text_primary']}; }}
            QLineEdit {{ background-color: {t['input_bg']}; border: 1.5px solid {t['input_border']}; border-radius: 8px; padding: 10px; font-size: 14px; color: {t['text_primary']}; }}
            QLineEdit:focus {{ border: 2px solid {t['accent']}; }}
            QPushButton {{ background-color: {t['accent']}; color: white; border-radius: 8px; padding: 12px; font-size: 14px; font-weight: bold; border: none; }}
            QPushButton:hover {{ background-color: {t['accent_hover']}; }}
            QPushButton:pressed {{ background-color: #1E40AF; }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 120 if is_dark else 70))
        shadow.setOffset(0, 6)
        self.login_card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.login_card)
        card_layout.setContentsMargins(30, 40, 30, 40)
        card_layout.setSpacing(18)
        
        inst_name = app_state.get_setting("institution_name", "") or app_state.get_setting("name", "") or "Universal Education Management"
        logo_path = app_state.get_setting("logo_path", "") or app_state.get_setting("institution_logo", "")

        # Optional Logo Icon or Badge
        if logo_path and os.path.exists(logo_path):
            try:
                pix = QPixmap(logo_path).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_lbl = QLabel()
                logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                logo_lbl.setPixmap(pix)
                logo_lbl.setStyleSheet("background: transparent; border: none;")
                card_layout.addWidget(logo_lbl)
            except Exception:
                pass

        self.title_label = QLabel(inst_name)
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"color: {t['text_primary']}; background: transparent; border: none;")
        self.title_label.setWordWrap(True)
        card_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Sign in to access institutional workspace")
        self.subtitle_label.setFont(QFont("Segoe UI", 10))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet(f"color: {t['text_secondary']}; background: transparent; border: none;")
        card_layout.addWidget(self.subtitle_label)
        card_layout.addSpacing(6)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        card_layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.password_input)
        
        # Smooth progress indicator for login transition
        from PySide6.QtWidgets import QProgressBar
        self.login_progress = QProgressBar()
        self.login_progress.setFixedHeight(4)
        self.login_progress.setTextVisible(False)
        self.login_progress.setRange(0, 0)
        self.login_progress.setStyleSheet("""
            QProgressBar { background-color: #E2E8F0; border-radius: 2px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #38BDF8); }
        """)
        self.login_progress.hide()
        card_layout.addWidget(self.login_progress)

        card_layout.addSpacing(4)
        
        self.btn_login = QPushButton("Login to Dashboard")
        self.btn_login.clicked.connect(self.attempt_login)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        card_layout.addWidget(self.btn_login)

        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.btn_login.click)
        
        main_layout.addWidget(self.login_card)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()

        # Non-blocking pre-warm of MainWindow modules in background after login window is rendered
        QTimer.singleShot(300, self._prewarm_main_window)

    def _prewarm_main_window(self):
        try:
            import ui.main_window  # Preloads module into memory without blocking UI startup
        except Exception:
            pass

    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both username and password.")
            return
            
        success, message = app_state.login(username, password)
        
        if success:
            inst_name = app_state.get_setting("institution_name", "") or "Workspace"
            self.btn_login.setEnabled(False)
            self.btn_login.setText(f"Opening {inst_name}...")
            self.subtitle_label.setText("Credentials verified! Loading workspace...")
            self.subtitle_label.setStyleSheet("color: #2563EB; font-weight: bold; background: transparent;")
            self.login_progress.show()
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            QTimer.singleShot(50, self._do_launch_main_window)
        else:
            QMessageBox.critical(self, "Login Failed", message)
            self.password_input.clear()
            self.password_input.setFocus()

    def _do_launch_main_window(self):
        from ui.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.showMaximized()
        self.close()