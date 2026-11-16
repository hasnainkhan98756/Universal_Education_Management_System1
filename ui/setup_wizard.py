import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QComboBox, 
                               QStackedWidget, QFormLayout, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database.connection import get_session
from database.models.institution import InstitutionSettings
from database.models.users import User
from core.security import hash_password

class SetupWizard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("First Time Setup - Universal Education Management System")
        self.resize(700, 500)
        
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        
        # Header
        self.header_label = QLabel("Institution Setup Wizard")
        self.header_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.header_label)
        
        # Stacked Widget (The "Pages" of our Wizard)
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Navigation Buttons Layout
        self.nav_layout = QHBoxLayout()
        self.btn_back = QPushButton("< Back")
        self.btn_next = QPushButton("Next >")
        self.btn_finish = QPushButton("Finish Setup")
        self.btn_finish.hide() # Hidden until the last step
        
        self.nav_layout.addWidget(self.btn_back)
        self.nav_layout.addStretch() # Pushes next button to the right
        self.nav_layout.addWidget(self.btn_next)
        self.nav_layout.addWidget(self.btn_finish)
        self.main_layout.addLayout(self.nav_layout)
        
        # Connect Buttons
        self.btn_next.clicked.connect(self.next_step)
        self.btn_back.clicked.connect(self.prev_step)
        self.btn_finish.clicked.connect(self.finish_setup)
        
        # Logo path variable
        self.logo_path = ""
        
        # Build the 5 Steps
        self.build_step_1()
        self.build_step_2()
        self.build_step_3()
        self.build_step_4()
        self.build_step_5()
        
        self.update_buttons()

    def build_step_1(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Step 1: Select Institution Type")
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["School", "College", "School + College"])
        layout.addWidget(self.type_combo)
        layout.addStretch()
        
        self.stacked_widget.addWidget(page)

    def build_step_2(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Step 2: Institution Information")
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(label)
        
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.address_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.principal_input = QLineEdit()
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("e.g., 2026-2027")
        
        form.addRow("Institution Name:", self.name_input)
        form.addRow("Address:", self.address_input)
        form.addRow("Phone Number:", self.phone_input)
        form.addRow("Email:", self.email_input)
        form.addRow("Principal Name:", self.principal_input)
        form.addRow("Academic Session:", self.session_input)
        
        layout.addLayout(form)
        layout.addStretch()
        self.stacked_widget.addWidget(page)

    def build_step_3(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Step 3: Branding & Appearance")
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(label)
        
        form = QFormLayout()
        self.app_title_input = QLineEdit()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Ocean Blue", "Emerald Green", "Royal Purple", "Dark Professional"])
        
        self.btn_logo = QPushButton("Browse Logo...")
        self.btn_logo.clicked.connect(self.select_logo)
        self.logo_label = QLabel("No logo selected")
        
        form.addRow("Application Title:", self.app_title_input)
        form.addRow("Color Theme:", self.theme_combo)
        form.addRow("Institution Logo:", self.btn_logo)
        form.addRow("", self.logo_label)
        
        layout.addLayout(form)
        layout.addStretch()
        self.stacked_widget.addWidget(page)
        
    def select_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.logo_path = file_path
            self.logo_label.setText(file_path)

    def build_step_4(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Step 4: Default Templates (Can be changed later)")
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(label)
        
        form = QFormLayout()
        self.id_template = QComboBox()
        self.id_template.addItems(["Modern Portrait", "Classic Landscape"])
        self.receipt_template = QComboBox()
        self.receipt_template.addItems(["Standard Thermal", "A4 Detailed"])
        self.cert_template = QComboBox()
        self.cert_template.addItems(["Formal Standard", "Elegant Script"])
        
        form.addRow("Student ID Card:", self.id_template)
        form.addRow("Fee Receipt:", self.receipt_template)
        form.addRow("Certificates:", self.cert_template)
        
        layout.addLayout(form)
        layout.addStretch()
        self.stacked_widget.addWidget(page)

    def build_step_5(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        label = QLabel("Step 5: Master Accounts Setup")
        label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(label)
        
        form = QFormLayout()
        
        self.prin_user = QLineEdit("principal")
        self.prin_pass = QLineEdit()
        self.prin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.admin_user = QLineEdit("admin")
        self.admin_pass = QLineEdit()
        self.admin_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        form.addRow("<b>Principal Username:</b>", self.prin_user)
        form.addRow("<b>Principal Password:</b>", self.prin_pass)
        form.addRow("---", QLabel("---"))
        form.addRow("<b>Admin Username:</b>", self.admin_user)
        form.addRow("<b>Admin Password:</b>", self.admin_pass)
        
        layout.addLayout(form)
        layout.addStretch()
        self.stacked_widget.addWidget(page)

    def next_step(self):
        current = self.stacked_widget.currentIndex()
        if current < self.stacked_widget.count() - 1:
            self.stacked_widget.setCurrentIndex(current + 1)
        self.update_buttons()

    def prev_step(self):
        current = self.stacked_widget.currentIndex()
        if current > 0:
            self.stacked_widget.setCurrentIndex(current - 1)
        self.update_buttons()

    def update_buttons(self):
        current = self.stacked_widget.currentIndex()
        self.btn_back.setEnabled(current > 0)
        
        if current == self.stacked_widget.count() - 1:
            self.btn_next.hide()
            self.btn_finish.show()
        else:
            self.btn_next.show()
            self.btn_finish.hide()

    def finish_setup(self):
        if not self.prin_pass.text() or not self.admin_pass.text():
            QMessageBox.warning(self, "Error", "Both Principal and Admin passwords are required!")
            return
        if not self.name_input.text():
            QMessageBox.warning(self, "Error", "Institution Name is required!")
            return

        session = get_session()
        try:
            # BUG FIX: Get the existing row instead of creating a new one!
            settings = session.query(InstitutionSettings).first()
            if not settings:
                settings = InstitutionSettings()
                session.add(settings)

            # Update the settings
            settings.is_setup_complete = True
            settings.institution_type = self.type_combo.currentText()
            settings.name = self.name_input.text()
            settings.address = self.address_input.text()
            settings.phone = self.phone_input.text()
            settings.email = self.email_input.text()
            settings.principal_name = self.principal_input.text()
            settings.current_academic_session = self.session_input.text()
            settings.app_title = self.app_title_input.text()
            settings.theme = self.theme_combo.currentText()
            settings.logo_path = self.logo_path

            # Clear old users if they exist (prevents errors during testing)
            session.query(User).delete()

            # Save Principal Account
            principal = User(
                username=self.prin_user.text(),
                password_hash=hash_password(self.prin_pass.text()),
                role="Principal"
            )
            session.add(principal)

            # Save Admin Account
            admin = User(
                username=self.admin_user.text(),
                password_hash=hash_password(self.admin_pass.text()),
                role="Admin"
            )
            session.add(admin)

            session.commit()
            
            QMessageBox.information(self, "Setup Complete", 
                                    "Configuration saved successfully!\n"
                                    "The application will now exit. Please restart it to log in.")
            sys.exit(0)
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Database Error", str(e))
        finally:
            session.close()