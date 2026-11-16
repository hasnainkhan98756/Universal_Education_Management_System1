from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QMessageBox, QHBoxLayout, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from core.security import verify_developer_password

class DeveloperAuthDialog(QDialog):
    """
    A protected pop-up window that asks for the Developer Password.
    Upgraded to match the premium UI theme to fix the "blank" issue.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Developer Authorization Required")
        self.setFixedSize(450, 250)
        self.setModal(True)
        
        # Explicitly set the background to a light color so text is visible
        self.setStyleSheet("QDialog { background-color: #F8F9FA; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Create a styled white card inside the dialog
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: white; border-radius: 12px; border: 1px solid #E5E7EB; }")
        
        # Drop shadow for the card
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)
        card_layout.setContentsMargins(25, 25, 25, 25)

        # Warning Label
        warning_label = QLabel("RESTRICTED ACCESS")
        warning_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        warning_label.setStyleSheet("color: #EF4444; border: none; background: transparent;")
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(warning_label)

        sub_label = QLabel("Please enter the Developer Password to unlock settings.")
        sub_label.setFont(QFont("Segoe UI", 10))
        sub_label.setStyleSheet("color: #6B7280; border: none; background: transparent;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(sub_label)

        # Password Input Field
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter Developer Password...")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit { background-color: #F9FAFB; border: 1px solid #D1D5DB; border-radius: 6px; padding: 10px; color: #111827; }
            QLineEdit:focus { border: 2px solid #1D4ED8; background-color: #FFFFFF; }
        """)
        card_layout.addWidget(self.password_input)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color: white; color: #374151; border: 1px solid #D1D5DB; border-radius: 6px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #F3F4F6; }
        """)

        self.btn_authorize = QPushButton("Authorize")
        self.btn_authorize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_authorize.setStyleSheet("""
            QPushButton { background-color: #1D4ED8; color: white; border-radius: 6px; padding: 8px 15px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #1E40AF; }
        """)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_authorize)
        card_layout.addLayout(btn_layout)

        main_layout.addWidget(card)

        # Connections
        self.btn_authorize.clicked.connect(self.check_authorization)
        self.btn_cancel.clicked.connect(self.reject)
        self.password_input.returnPressed.connect(self.btn_authorize.click)

    def check_authorization(self):
        entered_pass = self.password_input.text()
        if verify_developer_password(entered_pass):
            self.accept()
        else:
            QMessageBox.critical(self, "Authorization Failed", "Invalid Developer Password.\nAccess Denied.")
            self.password_input.clear()