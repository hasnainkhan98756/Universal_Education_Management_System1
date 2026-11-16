import os
import shutil
import csv
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFileDialog, QMessageBox, 
                               QFormLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QListWidget, QStackedWidget, QTabWidget,
                               QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QInputDialog,
                               QCheckBox, QScrollArea, QFrame, QSizePolicy, QDialog)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont, QDesktopServices

from database.connection import get_session, DB_PATH, DB_DIR
from database.models.pdf_templates import PDFTemplateMapping
from core.state_manager import app_state
from core.document_service import DocumentService
from core.backup_service import BackupService
from core.security import verify_developer_password, hash_password
from config import BACKUPS_DIR
from ui.components.stitch_widgets import TableTextButton, TableActionButton, create_table_actions_cell
from ui.views.settings.pdf_mapper_window import VisualPDFMapperWindow
from ui.views.settings.numbering_settings_dialog import NumberingSettingsDialog
from ui.views.settings.countdown_reset_dialog import CountdownResetDialog
from ui.views.analytics.audit_dialog import AuditDiagnosticDialog

def safe_int(val, default=0):
    try: return int(val)
    except: return default

def safe_float(val, default=0.0):
    try: return float(val)
    except: return default

class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        title = QLabel("System Settings & Configuration")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        main_layout.addWidget(title)

        content_layout = QHBoxLayout()

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.sidebar.addItems([
            "1. Academic Defaults",
            "2. Fee & Finance Data",
            "3. Printing & Formats",
            "4. Local Backup & Restore",
            "5. Cloud Drive Sync",
            "6. Data Management",
            "7. Account & Security", 
            "8. Advanced / Developer"
        ])
        self.sidebar.currentRowChanged.connect(self.switch_tab)

        self.stack = QStackedWidget()

        self.stack.addWidget(self.create_academic_tab())      # index 0 -> sidebar item 1
        self.stack.addWidget(self.create_finance_tab())       # index 1 -> sidebar item 2
        self.stack.addWidget(self.create_printing_tab())      # index 2 -> sidebar item 3
        self.stack.addWidget(self.create_backup_tab())        # index 3 -> sidebar item 4
        self.stack.addWidget(self.create_cloud_tab())         # index 4 -> sidebar item 5
        self.stack.addWidget(self.create_data_tab())          # index 5 -> sidebar item 6
        self.stack.addWidget(self.create_security_tab())      # index 6 -> sidebar item 7 Account & Security
        self.stack.addWidget(self.create_developer_tab())     # index 7 -> sidebar item 8

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(self.stack)
        main_layout.addLayout(content_layout)
        
        self.load_public_settings()
        self.load_dev_settings() 

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)

    def _input(self, password=False):
        inp = QLineEdit()
        inp.setMinimumHeight(28)
        if password: inp.setEchoMode(QLineEdit.EchoMode.Password)
        return inp

    def trigger_live_sync(self):
        try:
            top_window = self.window()
            for method in ['sync_ui_with_settings', 'load_settings', 'apply_theme', 'update_ui']:
                if hasattr(top_window, method): getattr(top_window, method)()
            if hasattr(app_state, 'notify_observers'): app_state.notify_observers()
            top_window.update(); top_window.repaint()
        except Exception as e:
            print(f"Live sync error: {e}")

    # ==========================================
    # PUBLIC TABS
    # ==========================================

    def create_academic_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        lay.addWidget(QLabel("<h2>Academic Configuration</h2>"))
        form = QFormLayout(); form.setSpacing(10)

        self.inp_session = self._input()
        self.spin_capacity = QSpinBox(); self.spin_capacity.setRange(10, 200)
        self.spin_pass_pct = QSpinBox(); self.spin_pass_pct.setRange(10, 100); self.spin_pass_pct.setSuffix(" %")
        

        form.addRow(QLabel("<b>Default Academic Session:</b>"), self.inp_session)
        form.addRow(QLabel("<b>Default Section Capacity:</b>"), self.spin_capacity)
        form.addRow(QLabel("<b>Default Passing Percentage:</b>"), self.spin_pass_pct)
        
        btn_save = QPushButton("Save Academic Settings")
        btn_save.setObjectName("btn_success")
        btn_save.setMinimumHeight(30)
        btn_save.clicked.connect(self.save_public_settings)
        
        lay.addLayout(form); lay.addWidget(btn_save); lay.addStretch()
        return page

    def create_finance_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        lay.addWidget(QLabel("<h2>Fee & Finance Defaults</h2>"))
        form = QFormLayout(); form.setSpacing(10)

        self.spin_fine = QDoubleSpinBox(); self.spin_fine.setRange(0, 10000)
        self.spin_discount = QDoubleSpinBox(); self.spin_discount.setRange(0, 100000)
        self.inp_currency = self._input()
        self.inp_bank_details = self._input()
        
        

        form.addRow(QLabel("<b>Default Currency Symbol:</b>"), self.inp_currency)
        form.addRow(QLabel("<b>Default Late Fine:</b>"), self.spin_fine)
        form.addRow(QLabel("<b>Default Discount:</b>"), self.spin_discount)
        form.addRow(QLabel("<b>Bank Account Details (For Receipts):</b>"), self.inp_bank_details)

        btn_save = QPushButton("Save Finance Settings")
        btn_save.setObjectName("btn_success")
        btn_save.setMinimumHeight(30)
        btn_save.clicked.connect(self.save_public_settings)
        
        lay.addLayout(form); lay.addWidget(btn_save); lay.addStretch()
        return page

    def create_printing_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        lay.addWidget(QLabel("<h2>Printing & Receipt Configuration</h2>"))
        form = QFormLayout(); form.setSpacing(10)

        self.combo_paper = QComboBox()
        self.combo_paper.addItems(["A4 Size (Standard)", "Letter Size", "POS Thermal Receipt (80mm)"])
        
        
        self.combo_custom_pdf = QComboBox()
        self.combo_custom_pdf.addItems(["OFF — Clean Built-in Professional A4 PDFs (ReportLab)", "ON — Custom Mapped PDF Templates (PyMuPDF)"])
        
        self.inp_receipt_footer = self._input()
        self.inp_receipt_footer.setPlaceholderText("e.g., Fees once paid are non-refundable.")

        form.addRow(QLabel("<b>Custom PDF Templates:</b>"), self.combo_custom_pdf)
        form.addRow(QLabel("<b>Default Paper Size:</b>"), self.combo_paper)
        form.addRow(QLabel("<b>Receipt Footer Note:</b>"), self.inp_receipt_footer)

        btn_save = QPushButton("Save Printing Settings")
        btn_save.setObjectName("btn_success")
        btn_save.setMinimumHeight(30)
        btn_save.clicked.connect(self.save_public_settings)

        lay.addLayout(form); lay.addWidget(btn_save); lay.addStretch()
        return page

    def create_backup_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(10)
        lay.addWidget(QLabel("<h2>All-in-One Application Backup & Disaster Recovery</h2>"))
        lbl_sub = QLabel(
            "Unified full-app backup: database, PDF templates, field coordinate mappings, branding logos, "
            "student photos, and system settings in a single archive. Creating a new backup directly replaces "
            "the previous backup to permanently eliminate extra storage consumption."
        )
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #64748B; font-size: 12px; margin-bottom: 4px;")
        lay.addWidget(lbl_sub)
        
        form = QFormLayout()
        self.inp_backup_loc = self._input()
        self.inp_backup_loc.setReadOnly(True)
        btn_browse_loc = QPushButton("Browse")
        btn_browse_loc.setObjectName("btn_secondary")
        btn_browse_loc.setMinimumHeight(28)
        btn_browse_loc.clicked.connect(self.browse_backup_folder)
        loc_lay = QHBoxLayout(); loc_lay.addWidget(self.inp_backup_loc); loc_lay.addWidget(btn_browse_loc)
        form.addRow("<b>Default Backup Location:</b>", loc_lay)
        
        self.combo_backup_close = QComboBox()
        self.combo_backup_close.addItems(["Enabled", "Disabled"])
        
        self.combo_backup_auto = QComboBox()
        self.combo_backup_auto.addItems(["Disabled", "Enabled"])
        
        form.addRow("<b>Backup on Application Close:</b>", self.combo_backup_close)
        form.addRow("<b>Auto-Backup After Important Data Entry:</b>", self.combo_backup_auto)

        lay.addLayout(form)
        
        btn_save_config = QPushButton("Save Backup Configuration")
        btn_save_config.setObjectName("btn_success")
        btn_save_config.setMinimumHeight(32)
        btn_save_config.clicked.connect(self.save_public_settings)
        lay.addWidget(btn_save_config)

        lay.addWidget(QLabel("<hr>"))

        btn_backup = QPushButton("Create Full App Backup Now (.zip)")
        btn_backup.setObjectName("btn_primary")
        btn_backup.setMinimumHeight(32)
        btn_backup.clicked.connect(self.run_local_backup)
        lay.addWidget(btn_backup)

        btn_verify = QPushButton("Verify Backup Archive Integrity (.zip or .db)")
        btn_verify.setStyleSheet("background-color: #0891B2; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; min-height: 32px;")
        btn_verify.clicked.connect(self.run_verify_backup)
        lay.addWidget(btn_verify)

        btn_history = QPushButton("View Available Backups & Recovery History")
        btn_history.setStyleSheet("background-color: #4F46E5; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; min-height: 32px;")
        btn_history.clicked.connect(self.show_backup_history)
        lay.addWidget(btn_history)

        btn_restore = QPushButton("Guarded Restore Entire Application (.zip or .db)")
        btn_restore.setObjectName("btn_danger")
        btn_restore.setMinimumHeight(32)
        btn_restore.clicked.connect(self.run_restore)
        lay.addWidget(btn_restore)

        btn_fresh = QPushButton("Restore App to Fresh State (30s Grace Period Factory Reset)")
        btn_fresh.setStyleSheet("background-color: #DC2626; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; min-height: 32px;")
        btn_fresh.clicked.connect(self.trigger_fresh_app_restore)
        lay.addWidget(btn_fresh)
        lay.addStretch()
        return page

    def browse_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if folder: self.inp_backup_loc.setText(folder)

    def create_cloud_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        lay.addWidget(QLabel("<h2>Google Drive / OneDrive Cloud Sync</h2>"))
        
        form = QFormLayout()
        self.inp_cloud_dir = self._input()
        self.inp_cloud_dir.setReadOnly(True)
        btn_browse = QPushButton("Select Cloud Folder")
        btn_browse.setObjectName("btn_secondary")
        btn_browse.setMinimumHeight(28)
        btn_browse.clicked.connect(self.browse_cloud_folder)
        row_lay = QHBoxLayout(); row_lay.addWidget(self.inp_cloud_dir); row_lay.addWidget(btn_browse)
        form.addRow("<b>Cloud Sync Directory:</b>", row_lay)
        lay.addLayout(form)

        btn_sync = QPushButton("Run Cloud Sync Backup Now")
        btn_sync.setObjectName("btn_primary")
        btn_sync.setMinimumHeight(30)
        btn_sync.clicked.connect(self.run_cloud_sync)
        lay.addWidget(btn_sync); lay.addStretch()
        return page

    def create_data_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        lay.addWidget(QLabel("<h2>Data Management & Exports</h2>"))
        
        export_box = QGroupBox("Export Data to Excel (.xlsx)")
        
        exp_lay = QVBoxLayout(export_box)
        
        btn_exp_stu = QPushButton("Export All Students (Excel)")
        btn_exp_stu.setObjectName("btn_primary")
        btn_exp_stu.setMinimumHeight(30)
        btn_exp_stu.clicked.connect(self.export_students_excel)
        
        btn_exp_fee = QPushButton("Export Payment History (Excel)")
        btn_exp_fee.setObjectName("btn_purple")
        btn_exp_fee.setMinimumHeight(30)
        btn_exp_fee.clicked.connect(self.export_fees_excel)
        
        exp_lay.addWidget(btn_exp_stu); exp_lay.addWidget(btn_exp_fee)
        lay.addWidget(export_box)

        maint_box = QGroupBox("Database Maintenance")
        maint_box.setStyleSheet(export_box.styleSheet())
        maint_lay = QVBoxLayout(maint_box)
        
        btn_vacuum = QPushButton("Optimize & Vacuum Database")
        btn_vacuum.setStyleSheet("background-color: #8B5CF6; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; min-height: 30px;")
        btn_vacuum.clicked.connect(self.optimize_database)
        maint_lay.addWidget(btn_vacuum)
        lay.addWidget(maint_box)

        audit_box = QGroupBox("Financial & Data-Integrity Audit")
        audit_box.setStyleSheet(export_box.styleSheet())
        audit_lay = QVBoxLayout(audit_box)

        btn_audit = QPushButton("Run Financial & Data-Integrity Audit Diagnostic")
        btn_audit.setStyleSheet("background-color: #059669; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; min-height: 30px;")
        btn_audit.clicked.connect(self.run_audit_diagnostic)
        audit_lay.addWidget(btn_audit)
        lay.addWidget(audit_box)
        
        lay.addStretch()
        return page

    def run_audit_diagnostic(self):
        diag = AuditDiagnosticDialog(parent=self)
        diag.exec()

    # ==========================================
    # ACCOUNT & SECURITY TAB (index 6)
    # ==========================================

    def create_security_tab(self):
        """Account & Security — wrapped in QScrollArea so it works at ANY window size."""

        # ── Scroll container (outer shell returned to the stack) ──────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        # ── Inner content widget ──────────────────────────────────────────
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(inner)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(10)

        # ── Header ───────────────────────────────────────────────────────
        header_lbl = QLabel("Account & Security")
        header_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_lbl.setStyleSheet("border:none; background:transparent;")
        outer.addWidget(header_lbl)

        sub_lbl = QLabel("Change the password for your currently logged-in account.")
        sub_lbl.setStyleSheet("color:#6B7280; font-size:12px; border:none; background:transparent;")
        outer.addWidget(sub_lbl)

        outer.addWidget(self._divider())

        # ── Logged-in user banner ─────────────────────────────────────────
        self.sec_who_lbl = QLabel()
        self.sec_who_lbl.setMinimumHeight(32)
        outer.addWidget(self.sec_who_lbl)

        # ── Change-Password Card ──────────────────────────────────────────
        card = QFrame()
        card.setObjectName("stat_card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        card_title = QLabel("<b>Change Your Password</b>")
        card_title.setStyleSheet("font-size:13px; border:none; background:transparent;")
        card_lay.addWidget(card_title)

        # ── One labelled password row ─────────────────────────────────────
        def _make_field(label_text, placeholder_text):
            w = QWidget()
            w.setStyleSheet("background:transparent; border:none;")
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(4)

            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                "font-size:12px; font-weight:600; color:#374151;"
                " border:none; background:transparent;"
            )
            v.addWidget(lbl)

            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(6)

            field = QLineEdit()
            field.setPlaceholderText(placeholder_text)
            field.setEchoMode(QLineEdit.EchoMode.Password)
            field.setMinimumHeight(28)
            field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            field.setStyleSheet(
                "QLineEdit { background-color: #FFFFFF; color: #000000; "
                "border: 1.5px solid #94A3B8; border-radius: 6px; "
                "padding: 4px 8px; font-size: 12px; } "
                "QLineEdit:focus { border: 2px solid #2563EB; }"
            )

            eye = QPushButton("Show")
            eye.setFixedSize(28, 28)
            eye.setCheckable(True)
            eye.setToolTip("Show / hide password")
            eye.setStyleSheet(
                "QPushButton { background-color: #F1F5F9; color: #000000; "
                "border: 1.5px solid #CBD5E1; border-radius: 6px; "
                "font-size: 12px; font-weight: bold; } "
                "QPushButton:hover { background-color: #E2E8F0; } "
                "QPushButton:checked { background-color: #E0E7FF; border-color: #6366F1; }"
            )
            
            eye.clicked.connect(lambda _c, f=field, e=eye: self._toggle_echo(f, e))

            h.addWidget(field)
            h.addWidget(eye)
            v.addLayout(h)
            return w, field

        cur_w, self.sec_inp_current = _make_field("Current Password", "Enter your current password")
        card_lay.addWidget(cur_w)

        new_w, self.sec_inp_new = _make_field("New Password", "Minimum 6 characters")
        card_lay.addWidget(new_w)
        self.sec_inp_new.textChanged.connect(self._update_strength)

        self.sec_strength_lbl = QLabel("Password strength:  —")
        self.sec_strength_lbl.setMinimumHeight(18)
        self.sec_strength_lbl.setStyleSheet(
            "font-size:12px; color:#6B7280; border:none; background:transparent;"
        )
        card_lay.addWidget(self.sec_strength_lbl)

        conf_w, self.sec_inp_confirm = _make_field("Confirm New Password", "Re-enter new password")
        card_lay.addWidget(conf_w)

        card_lay.addSpacing(6)

        self.sec_btn_save = QPushButton("Update My Password")
        self.sec_btn_save.setMinimumHeight(32)
        self.sec_btn_save.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.sec_btn_save.setObjectName("btn_primary")
        self.sec_btn_save.setStyleSheet(
            "QPushButton { background-color: #1D4ED8; color: #FFFFFF; font-size: 13px; font-weight: bold; "
            "border: 1.5px solid #1E40AF; border-radius: 6px; min-height: 32px; padding: 4px 14px; } "
            "QPushButton:hover { background-color: #1E40AF; } "
            "QPushButton:pressed { background-color: #172554; }"
        )
        self.sec_btn_save.clicked.connect(self.change_my_password)
        card_lay.addWidget(self.sec_btn_save)

        self.sec_status_lbl = QLabel("")
        self.sec_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sec_status_lbl.setMinimumHeight(26)
        self.sec_status_lbl.setStyleSheet(
            "font-size:13px; border:none; background:transparent;"
        )
        card_lay.addWidget(self.sec_status_lbl)

        outer.addWidget(card)
        outer.addWidget(self._divider())

        # ── Security Tips ─────────────────────────────────────────────────
        tips_box = QGroupBox("Security Tips")
        tips_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        tips_box.setStyleSheet("QGroupBox { font-weight:bold; border:1px solid #D1FAE5; border-radius:8px; margin-top:10px; } QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 6px; color:#065F46; font-size:13px; }")
        tl = QVBoxLayout(tips_box)
        tl.setContentsMargins(16, 14, 16, 14)
        tl.setSpacing(8)
        for tip in [
            "Use at least 8 characters with letters and numbers.",
            "Never share your password with anyone.",
            "Change your password regularly (every 90 days).",
            "Do not use your name, school name, or '12345' as a password.",
        ]:
            t = QLabel(tip)
            t.setStyleSheet(
                "color:#065F46; font-size:12px; background:transparent; border:none;"
            )
            tl.addWidget(t)
        outer.addWidget(tips_box)

        outer.addSpacing(20)          # bottom breathing room — NO addStretch()

        scroll.setWidget(inner)
        scroll.showEvent = lambda e: self._refresh_security_header()
        return scroll

    # ── Security Tab Helpers ─────────────────────────────────────

    def _sec_input(self, placeholder="", password=False):
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(38)
        if password:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
        return inp

    def _eye_btn(self):
        btn = QPushButton("Show")
        btn.setFixedSize(38, 38)
        btn.setCheckable(True)
        btn.setToolTip("Show / Hide password")
        btn.setStyleSheet(
            "QPushButton { background:#F3F4F6; color: #000000; border:1px solid #CBD5E1;"
            " border-radius:6px; font-size:14px; font-weight: bold; }"
            "QPushButton:hover { background: #E2E8F0; }"
            "QPushButton:checked { background:#DBEAFE; border-color:#1D4ED8; }"
        )
        return btn

    def _toggle_echo(self, inp: QLineEdit, btn: QPushButton):
        if btn.isChecked():
            inp.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            inp.setEchoMode(QLineEdit.EchoMode.Password)

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color:#E5E7EB;")
        return line

    def _update_strength(self, text):
        length = len(text)
        has_upper = any(c.isupper() for c in text)
        has_digit = any(c.isdigit() for c in text)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in text)

        score = 0
        if length >= 6:  score += 1
        if length >= 10: score += 1
        if has_upper:    score += 1
        if has_digit:    score += 1
        if has_special:  score += 1

        levels = [
            (0, "—",        "#9CA3AF"),
            (1, "Weak",  "#EF4444"),
            (2, "Fair",  "#F97316"),
            (3, "Good",  "#EAB308"),
            (4, "Strong","#22C55E"),
            (5, "Very Strong", "#16A34A"),
        ]
        label, color = levels[score][1], levels[score][2]
        self.sec_strength_lbl.setText(f"Strength: <b><span style='color:{color}'>{label}</span></b>")

    def _refresh_security_header(self):
        username = getattr(app_state, "current_username", None) or "Unknown"
        role     = getattr(app_state, "current_user_role",  None) or "Unknown"
        self.sec_who_lbl.setText(
            f"Logged in as:  <b>{username.capitalize()}</b>"
            f"  |  Role: <b>{role}</b>"
        )

    # ── Change-Password Logic ────────────────────────────────────

    def change_my_password(self):
        """Validates inputs and changes the password of the currently-logged-in user."""
        current_pwd  = self.sec_inp_current.text()
        new_pwd      = self.sec_inp_new.text()
        confirm_pwd  = self.sec_inp_confirm.text()

        # ── Input Validation ────────────────────────────────────
        if not current_pwd:
            self._sec_error("Please enter your current password.")
            self.sec_inp_current.setFocus()
            return

        if not new_pwd:
            self._sec_error("Please enter a new password.")
            self.sec_inp_new.setFocus()
            return

        if len(new_pwd) < 6:
            self._sec_error("New password must be at least 6 characters.")
            self.sec_inp_new.setFocus()
            return

        if new_pwd != confirm_pwd:
            self._sec_error("Passwords do not match. Please re-enter.")
            self.sec_inp_confirm.clear()
            self.sec_inp_confirm.setFocus()
            return

        if current_pwd == new_pwd:
            self._sec_error("New password must be different from your current password.")
            self.sec_inp_new.setFocus()
            return

        role = getattr(app_state, "current_user_role", None)
        if not role:
            self._sec_error("No user is currently logged in.")
            return

        # ── Call the service (bcrypt verify + bcrypt hash + DB save) ─
        success, message = app_state.change_password(role, current_pwd, new_pwd)

        if success:
            # Clear all fields
            self.sec_inp_current.clear()
            self.sec_inp_new.clear()
            self.sec_inp_confirm.clear()
            self.sec_strength_lbl.setText("Strength: —")
            self._sec_success("Password updated successfully! Use it on your next login.")
            QMessageBox.information(
                self, "Password Changed",
                "Your password has been changed successfully.\n\n"
                "Your new password is active immediately."
            )
        else:
            self._sec_error(f"{message}")

    def _sec_error(self, msg):
        self.sec_status_lbl.setText(msg)
        self.sec_status_lbl.setStyleSheet("color:#DC2626; font-size:13px; font-weight:bold;")

    def _sec_success(self, msg):
        self.sec_status_lbl.setText(msg)
        self.sec_status_lbl.setStyleSheet("color:#16A34A; font-size:13px; font-weight:bold;")

    # ==========================================
    # PROTECTED DEVELOPER TABS 
    # ==========================================

    def create_developer_tab(self):
        page = QWidget(); lay = QVBoxLayout(page)
        self.dev_stack = QStackedWidget()

        # LOCK SCREEN
        lock_page = QWidget(); ll = QVBoxLayout(lock_page); ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inp_dev_pwd = self._input(password=True)
        self.inp_dev_pwd.setMaximumWidth(300)
        
        btn_unlock = QPushButton("Unlock Developer Tools")
        btn_unlock.setStyleSheet("background-color: #111827; color: white; padding: 12px; font-weight: bold; border-radius: 4px; max-width: 300px;")
        btn_unlock.clicked.connect(self.verify_dev)
        
        ll.addWidget(QLabel("<h2 style='color:#DC2626;'>Restricted Area</h2><p>Developer Authorization Required.</p>"), alignment=Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self.inp_dev_pwd, alignment=Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(btn_unlock, alignment=Qt.AlignmentFlag.AlignCenter)

        # UNLOCKED SCREEN
        tools_page = QWidget(); tl = QVBoxLayout(tools_page)
        self.dev_tabs = QTabWidget()
        self.dev_tabs.setStyleSheet("QTabBar::tab { padding: 5px 12px; font-weight: bold; }")
        
        self.dev_tabs.addTab(self.create_dev_institution_tab(), "1. Institution Profile")
        self.dev_tabs.addTab(self.create_dev_branding_tab(), "2. Appearance & Branding")
        self.dev_tabs.addTab(self.create_dev_security_tab(), "3. Force Reset PWD")
        self.dev_tabs.addTab(self.create_dev_pdf_mapping_tab(), "4. PDF Templates & Mapping")
        self.dev_tabs.addTab(self.create_dev_ops_tab(), "5. Developer Operations")

        tl.addWidget(QLabel("<h3>Developer Tools Unlocked</h3>"))
        tl.addWidget(self.dev_tabs)

        self.dev_stack.addWidget(lock_page)
        self.dev_stack.addWidget(tools_page)
        lay.addWidget(self.dev_stack)
        return page

    def create_dev_institution_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        form = QFormLayout(); form.setSpacing(8)

        self.inp_name = self._input()
        self.inp_type = QComboBox()
        self.inp_type.addItems(["School", "College", "School & College", "Academy"])
        self.inp_type.setStyleSheet("padding: 4px 8px; border: 1px solid #D1D5DB; border-radius: 4px; min-height: 28px;")
        
        self.inp_address = self._input()
        self.inp_phone = self._input()
        self.inp_email = self._input()
        self.inp_principal = self._input()
        self.inp_session_main = self._input()
        self.inp_title = self._input()

        form.addRow("<b>Institution Name:</b>", self.inp_name)
        form.addRow("<b>Institution Type:</b>", self.inp_type)
        form.addRow("<b>Address:</b>", self.inp_address)
        form.addRow("<b>Contact Phone:</b>", self.inp_phone)
        form.addRow("<b>Official Email:</b>", self.inp_email)
        form.addRow("<b>Principal / Head Name:</b>", self.inp_principal)
        form.addRow("<b>Active Academic Session:</b>", self.inp_session_main)
        form.addRow("<b>Application Title:</b>", self.inp_title)

        lay.addLayout(form)
        
        btn = QPushButton("Save Profile & Sync UI")
        btn.setStyleSheet("background-color: #10B981; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px; min-height: 30px;")
        btn.clicked.connect(self.save_institution_profile)
        lay.addWidget(btn); lay.addStretch()
        return page

    def create_dev_branding_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        form = QFormLayout(); form.setSpacing(8)

        self.lbl_theme_display = QLabel("Light Theme (Default & Active)")
        self.lbl_theme_display.setStyleSheet("font-weight: bold; font-size: 13px; color: #0F172A; padding: 4px 0;")
        
        self.inp_logo_path = self._input()
        self.inp_logo_path.setReadOnly(True)
        btn_logo = QPushButton("Browse Logo...")
        btn_logo.clicked.connect(self.browse_logo)
        
        logo_lay = QHBoxLayout(); logo_lay.addWidget(self.inp_logo_path); logo_lay.addWidget(btn_logo)

        form.addRow("<b>Application Theme:</b>", self.lbl_theme_display)
        form.addRow("<b>Institution Logo:</b>", logo_lay)

        lay.addLayout(form)
        
        btn = QPushButton("Save Branding & Apply")
        btn.setObjectName("btn_success")
        btn.setMinimumHeight(30)
        btn.clicked.connect(self.save_branding_profile)
        lay.addWidget(btn); lay.addStretch()
        return page

    def create_dev_security_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        form = QFormLayout(); form.setSpacing(8)

        self.inp_admin_pwd = self._input(password=True)
        form.addRow("<b>Force New Admin Password:</b>", self.inp_admin_pwd)

        lay.addLayout(form)
        btn = QPushButton("Force Update Admin Password")
        btn.setStyleSheet("background-color: #DC2626; color: white; padding: 6px 14px; font-weight: bold; border-radius: 4px; min-height: 30px;")
        btn.clicked.connect(self.update_admin_password)
        lay.addWidget(btn); lay.addStretch()
        return page

    def create_dev_pdf_mapping_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(16, 12, 16, 12); layout.setSpacing(8)
        
        self.tbl_templates = QTableWidget()
        self.tbl_templates.setColumnCount(4)
        self.tbl_templates.setHorizontalHeaderLabels(["Document Type", "Template File Status", "Upload / Replace", "Visual Mapper"])
        self.tbl_templates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_templates.verticalHeader().setDefaultSectionSize(28)
        self.tbl_templates.setStyleSheet("QTableWidget { border: none; } QHeaderView::section { background-color: #F9FAFB; font-weight: bold; padding: 6px; }")
        layout.addWidget(self.tbl_templates)
        self.refresh_templates_table()
        return page

    def create_dev_ops_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(8)
        
        num_box = QGroupBox("Document Numbering Engine")
        nl = QVBoxLayout(num_box)
        btn_numbering = QPushButton("Configure Document Numbering")
        btn_numbering.setStyleSheet("background-color: #8B5CF6; color: white; padding: 6px 14px; font-weight: bold; border-radius: 6px; min-height: 30px;")
        btn_numbering.clicked.connect(lambda: NumberingSettingsDialog(self).exec())
        nl.addWidget(btn_numbering)
        lay.addWidget(num_box)
        
        reset_box = QGroupBox("Danger Zone")
        reset_box.setStyleSheet("QGroupBox { border: 2px solid #DC2626; border-radius: 6px; margin-top: 15px; }")
        rl = QVBoxLayout(reset_box)
        btn_reset = QPushButton("Restore App to Fresh State (30s Countdown)")
        btn_reset.setStyleSheet("background-color: #DC2626; color: white; padding: 8px; font-weight: bold; border-radius: 6px; min-height: 32px;")
        btn_reset.clicked.connect(self.trigger_factory_reset)
        rl.addWidget(btn_reset)
        lay.addWidget(reset_box)

        lay.addStretch()
        return page

    # ==========================================
    # LOGIC & FUNCTIONALITY
    # ==========================================

    def load_public_settings(self):
        try:
            self.inp_session.setText(DocumentService.get_setting("session", "2026-2027"))
            self.spin_capacity.setValue(safe_int(DocumentService.get_setting("default_capacity", "40"), 40))
            self.spin_pass_pct.setValue(safe_int(DocumentService.get_setting("default_pass_pct", "33"), 33))
            self.spin_fine.setValue(safe_float(DocumentService.get_setting("default_fine", "0"), 0.0))
            self.spin_discount.setValue(safe_float(DocumentService.get_setting("default_discount", "0"), 0.0))
            self.inp_currency.setText(DocumentService.get_setting("currency_symbol", "Rs."))
            self.inp_bank_details.setText(DocumentService.get_setting("bank_details", ""))
            self.combo_paper.setCurrentText(DocumentService.get_setting("paper_size", "A4 Size (Standard)"))
            self.inp_receipt_footer.setText(DocumentService.get_setting("receipt_footer", ""))
            
            is_custom_pdf = DocumentService.get_setting("custom_pdf_enabled", "0")
            if str(is_custom_pdf).strip() == "1":
                self.combo_custom_pdf.setCurrentIndex(1)
            else:
                self.combo_custom_pdf.setCurrentIndex(0)
            
            default_backup_loc = str(BACKUPS_DIR)
            saved_backup_loc = DocumentService.get_setting("backup_location", default_backup_loc)
            if not saved_backup_loc or "system_backups" in saved_backup_loc or not os.path.exists(saved_backup_loc):
                saved_backup_loc = default_backup_loc
                DocumentService._save_setting_to_db("backup_location", default_backup_loc)
            self.inp_backup_loc.setText(saved_backup_loc)
            self.combo_backup_close.setCurrentText(DocumentService.get_setting("backup_on_close", "Enabled"))
            self.combo_backup_auto.setCurrentText(DocumentService.get_setting("backup_auto", "Disabled"))
            self.inp_cloud_dir.setText(DocumentService.get_setting("cloud_sync_folder", ""))
        except Exception as e:
            print(f"Error loading public settings: {e}")

    def load_dev_settings(self):
        try:
            self.inp_name.setText(DocumentService.get_setting("name", "Institution Name"))
            self.inp_type.setCurrentText(DocumentService.get_setting("inst_type", "School & College"))
            self.inp_address.setText(DocumentService.get_setting("address", ""))
            self.inp_phone.setText(DocumentService.get_setting("phone", ""))
            self.inp_email.setText(DocumentService.get_setting("email", ""))
            self.inp_principal.setText(DocumentService.get_setting("principal", ""))
            self.inp_session_main.setText(DocumentService.get_setting("session", "2026-2027"))
            self.inp_title.setText(DocumentService.get_setting("app_title", "Universal Education Management System"))
            
            self.inp_logo_path.setText(DocumentService.get_setting("institution_logo", ""))
        except Exception as e:
            print(f"Error loading dev settings: {e}")

    def save_public_settings(self):
        try:
            DocumentService._save_setting_to_db("session", self.inp_session.text().strip())
            DocumentService._save_setting_to_db("default_capacity", self.spin_capacity.value())
            DocumentService._save_setting_to_db("default_pass_pct", self.spin_pass_pct.value())
            DocumentService._save_setting_to_db("default_fine", self.spin_fine.value())
            DocumentService._save_setting_to_db("default_discount", self.spin_discount.value())
            DocumentService._save_setting_to_db("currency_symbol", self.inp_currency.text().strip())
            DocumentService._save_setting_to_db("bank_details", self.inp_bank_details.text().strip())
            DocumentService._save_setting_to_db("paper_size", self.combo_paper.currentText())
            DocumentService._save_setting_to_db("receipt_footer", self.inp_receipt_footer.text().strip())
            
            custom_pdf_val = "1" if self.combo_custom_pdf.currentIndex() == 1 else "0"
            DocumentService._save_setting_to_db("custom_pdf_enabled", custom_pdf_val)
            
            DocumentService._save_setting_to_db("backup_location", self.inp_backup_loc.text().strip())
            DocumentService._save_setting_to_db("backup_on_close", self.combo_backup_close.currentText())
            DocumentService._save_setting_to_db("backup_auto", self.combo_backup_auto.currentText())
            
            self.trigger_live_sync() 
            QMessageBox.information(self, "Success", "Public Settings saved permanently.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")

    def save_institution_profile(self):
        try:
            DocumentService._save_setting_to_db("name", self.inp_name.text().strip())
            DocumentService._save_setting_to_db("inst_type", self.inp_type.currentText())
            DocumentService._save_setting_to_db("address", self.inp_address.text().strip())
            DocumentService._save_setting_to_db("phone", self.inp_phone.text().strip())
            DocumentService._save_setting_to_db("email", self.inp_email.text().strip())
            DocumentService._save_setting_to_db("principal", self.inp_principal.text().strip())
            DocumentService._save_setting_to_db("session", self.inp_session_main.text().strip())
            DocumentService._save_setting_to_db("app_title", self.inp_title.text().strip())
            
            self.trigger_live_sync() 
            QMessageBox.information(self, "Success", "Institution Profile saved permanently.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")

    def save_branding_profile(self):
        try:
            logo_path = self.inp_logo_path.text().strip()
            DocumentService._save_setting_to_db("app_theme", "Light Mode")
            DocumentService._save_setting_to_db("theme_mode", "Light")
            DocumentService._save_setting_to_db("institution_logo", logo_path)
            DocumentService._save_setting_to_db("logo_path", logo_path)
            
            from core.theme_manager import ThemeManager
            ThemeManager.apply("Light")
            app_state.load_settings()
            self.trigger_live_sync() 
            QMessageBox.information(self, "Success", "Appearance & Branding saved permanently.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")

    def verify_dev(self):
        try:
            pwd = self.inp_dev_pwd.text()
            if verify_developer_password(pwd):
                self.dev_stack.setCurrentIndex(1)
                self.inp_dev_pwd.clear()
            else:
                QMessageBox.warning(self, "Access Denied", "Developer Authorization Failed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authorization failed:\n{str(e)}")

    def update_admin_password(self):
        try:
            new_pwd = self.inp_admin_pwd.text().strip()
            if not new_pwd: return
            hashed = hash_password(new_pwd)
            DocumentService._save_setting_to_db("admin_password_hash", hashed)
            self.inp_admin_pwd.clear()
            QMessageBox.information(self, "Success", "Admin password successfully updated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update password:\n{str(e)}")

    def browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Logo Image", "", "Images (*.png *.jpg *.jpeg)")
        if path: self.inp_logo_path.setText(path)

    # --- ADVANCED ACTIONS ---
    def run_local_backup(self):
        folder = self.inp_backup_loc.text().strip()
        success, msg = BackupService.create_advanced_backup(folder)
        if success: QMessageBox.information(self, "Success", msg)
        else: QMessageBox.critical(self, "Error", msg)

    def run_verify_backup(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Backup Archive to Verify", "", "Supported Backups (*.zip *.db);;ZIP Archives (*.zip);;Database Files (*.db)")
        if file:
            valid, msg = BackupService.verify_backup_integrity(file)
            if valid:
                QMessageBox.information(self, "Integrity Verification Passed", f"Backup file verified successfully:\n\n{msg}")
            else:
                QMessageBox.critical(self, "Integrity Check Failed", f"Corrupted or invalid backup file:\n\n{msg}")

    def show_backup_history(self):
        history = BackupService.get_backup_history()
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Backup & Recovery History ({len(history)} Available)")
        dlg.setMinimumSize(780, 480)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # Header with Search & Filter
        top_row = QHBoxLayout()
        lbl_info = QLabel(f"<b>Stored Backups:</b> {len(history)} archives detected across local and auto-backup repositories.")
        top_row.addWidget(lbl_info)
        top_row.addStretch()

        txt_filter = QLineEdit()
        txt_filter.setPlaceholderText("Filter backups...")
        txt_filter.setFixedWidth(200)
        txt_filter.setClearButtonEnabled(True)
        top_row.addWidget(txt_filter)
        lay.addLayout(top_row)

        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["Filename", "Type", "Size", "Last Updated", "Actions"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        tbl.setColumnWidth(4, 180)
        tbl.verticalHeader().setDefaultSectionSize(44)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        lay.addWidget(tbl)

        def _populate(filter_str=""):
            filter_lower = filter_str.lower().strip()
            filtered = [b for b in history if filter_lower in b["filename"].lower() or filter_lower in b["type"].lower() or filter_lower in b["date"].lower()]
            tbl.setRowCount(len(filtered))
            for r, b in enumerate(filtered):
                tbl.setItem(r, 0, QTableWidgetItem(b["filename"]))
                tbl.setItem(r, 1, QTableWidgetItem(b["type"]))
                tbl.setItem(r, 2, QTableWidgetItem(f"{b['size_mb']} MB"))
                tbl.setItem(r, 3, QTableWidgetItem(b["date"]))

                btn_v = TableTextButton("Verify", icon_name="check-circle", variant="secondary", height=28)
                btn_v.clicked.connect(lambda _, p=b["path"]: (
                    QMessageBox.information(dlg, "Integrity Check", BackupService.verify_backup_integrity(p)[1])
                ))

                btn_r = TableTextButton("Restore", icon_name="refresh-cw", variant="delete", height=28)
                btn_r.clicked.connect(lambda _, p=b["path"]: (
                    self._restore_from_history(p, dlg)
                ))

                tbl.setCellWidget(r, 4, create_table_actions_cell([btn_v, btn_r]))

        txt_filter.textChanged.connect(_populate)
        _populate()

        # Bottom Bar
        btm_row = QHBoxLayout()
        btn_open_folder = QPushButton("Open Backup Folder in Explorer")
        btn_open_folder.setMinimumHeight(28)
        btn_open_folder.setStyleSheet("font-weight: 600; padding: 4px 12px;")
        def _open_folder():
            bdir = BackupService.get_configured_backup_dir()
            if os.path.exists(bdir):
                QDesktopServices.openUrl(QUrl.fromLocalFile(bdir))
            else:
                QMessageBox.warning(dlg, "Notice", f"Directory does not exist: {bdir}")
        btn_open_folder.clicked.connect(_open_folder)
        btm_row.addWidget(btn_open_folder)

        btm_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setMinimumHeight(28)
        btn_close.setFixedWidth(90)
        btn_close.clicked.connect(dlg.accept)
        btm_row.addWidget(btn_close)
        lay.addLayout(btm_row)

        dlg.exec()

    def _restore_from_history(self, file_path, parent_dlg):
        reply = QMessageBox.question(
            parent_dlg, "Confirm Guarded Restore",
            f"Are you sure you want to restore the system from:\n\n{os.path.basename(file_path)}?\n\n"
            "An emergency pre-restore snapshot will be saved automatically, and an automated rollback will execute if any verification fails.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = BackupService.restore_database_with_safeguards(file_path)
            if success:
                QMessageBox.information(parent_dlg, "Restore Completed", msg)
                parent_dlg.accept()
            else:
                QMessageBox.critical(parent_dlg, "Restore Failed", msg)

    def run_restore(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Select Restore Operation")
        msg_box.setText("<h3>Application Restore Operations</h3>Please select the restore action you wish to perform:")

        btn_fresh = msg_box.addButton("Restore App to Fresh State (30s Grace Period)", QMessageBox.ButtonRole.ActionRole)
        btn_fresh.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold; padding: 8px 14px; border-radius: 4px;")

        btn_file = msg_box.addButton("Restore from Backup File (.zip or .db)", QMessageBox.ButtonRole.ActionRole)
        btn_file.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; padding: 8px 14px; border-radius: 4px;")

        btn_cancel = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked = msg_box.clickedButton()
        if clicked == btn_fresh:
            self.trigger_fresh_app_restore()
        elif clicked == btn_file:
            self.run_restore_from_file()

    def run_restore_from_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Backup File to Restore", "", "Supported Backups (*.zip *.db);;ZIP Archives (*.zip);;Database Files (*.db)")
        if file:
            reply = QMessageBox.question(
                self, "Confirm Guarded Restore",
                "WARNING: Restoring will overwrite the current database.\n\n"
                "A full emergency snapshot will be saved automatically.\n"
                "If the restored database fails integrity verification, an automated rollback will be triggered.\n\n"
                "Do you wish to proceed?"
            )
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = BackupService.restore_database_with_safeguards(file)
                if success:
                    QMessageBox.information(self, "Restore Completed", msg)
                else:
                    QMessageBox.critical(self, "Restore Notice", msg)

    def browse_cloud_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Cloud Sync Folder")
        if folder: 
            self.inp_cloud_dir.setText(folder)
            try:
                DocumentService._save_setting_to_db("cloud_sync_folder", folder)
            except Exception as e:
                print(f"Auto-save cloud folder error: {e}")
            
    def run_cloud_sync(self):
        cloud_folder = self.inp_cloud_dir.text().strip()
        
        if not cloud_folder or not os.path.exists(cloud_folder):
            QMessageBox.warning(self, "Setup Required", "Please select a valid Cloud Folder first.")
            return
            
        success, msg = BackupService.create_advanced_backup(cloud_folder)
        if success: QMessageBox.information(self, "Cloud Sync Successful", f"Backup safely synced to Cloud Folder!\n\n{msg}")
        else: QMessageBox.critical(self, "Error", msg)

    def optimize_database(self):
        reply = QMessageBox.question(self, "Confirm", "Run Database VACUUM?")
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = BackupService.optimize_database()
            if success: QMessageBox.information(self, "Optimized", msg)
            else: QMessageBox.critical(self, "Error", msg)

    def trigger_fresh_app_restore(self):
        dlg = CountdownResetDialog(self)
        res = dlg.exec()
        if res == QDialog.DialogCode.Accepted:
            self.load_public_settings()
            try:
                win = self.window()
                if hasattr(win, 'show_dashboard'):
                    win.show_dashboard()
                if hasattr(win, 'view_dashboard') and hasattr(win.view_dashboard, 'refresh_data'):
                    win.view_dashboard.refresh_data()
            except Exception:
                pass

    def trigger_factory_reset(self):
        self.trigger_fresh_app_restore()

    # --- EXPORTS & PDF LOGIC ---
    def export_students_excel(self):
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        db = get_session()
        try:
            from database.models.student import Student
            students = db.query(Student).all()
            path, _ = QFileDialog.getSaveFileName(self, "Save Export", "Students.xlsx", "Excel (*.xlsx)")
            if not path: return

            wb = openpyxl.Workbook(); ws = wb.active
            headers = ["ID", "Name", "Class", "Fees"]
            ws.append(headers)
            for s in students: ws.append([s.student_id, s.first_name, getattr(s, 'academic_class', 'N/A'), s.monthly_fee])
            wb.save(path)
            QMessageBox.information(self, "Success", "Exported successfully!")
        finally: db.close()

    def export_fees_excel(self):
        import openpyxl
        db = get_session()
        try:
            from database.models.fee import FeePayment
            payments = db.query(FeePayment).all()
            path, _ = QFileDialog.getSaveFileName(self, "Save Export", "Payments.xlsx", "Excel (*.xlsx)")
            if not path: return
            wb = openpyxl.Workbook(); ws = wb.active
            ws.append(["Receipt No", "Amount Paid"])
            for p in payments: ws.append([p.receipt_no, p.amount_paid])
            wb.save(path)
            QMessageBox.information(self, "Success", "Exported successfully!")
        finally: db.close()

    def refresh_templates_table(self):
        doc_types = ["Fee Receipt", "Admission Form", "Student ID Card", "School Leaving Certificate", "Character Certificate", "English Proficiency", "Transcript", "Salary Slip"]
        db = get_session()
        try:
            self.tbl_templates.setRowCount(len(doc_types))
            for row, dt in enumerate(doc_types):
                rec = db.query(PDFTemplateMapping).filter_by(document_type=dt).first()
                if not rec:
                    rec = PDFTemplateMapping(document_type=dt, template_path="", mapping_data="{}")
                    db.add(rec); db.commit()

                self.tbl_templates.setItem(row, 0, QTableWidgetItem(dt))
                has_file = rec.template_path and os.path.exists(rec.template_path)
                status_item = QTableWidgetItem("Configured" if has_file else "Missing")
                status_item.setForeground(Qt.GlobalColor.darkGreen if has_file else Qt.GlobalColor.red)
                self.tbl_templates.setItem(row, 1, status_item)

                btn_upload = QPushButton("Browse PDF...")
                btn_upload.clicked.connect(lambda checked=False, d=dt: self.upload_template(d))
                self.tbl_templates.setCellWidget(row, 2, btn_upload)

                btn_map = QPushButton("Open Visual Mapper")
                btn_map.setEnabled(bool(has_file))
                btn_map.clicked.connect(lambda checked=False, d=dt: self.open_mapper(d))
                self.tbl_templates.setCellWidget(row, 3, btn_map)
        finally: db.close()

    def upload_template(self, doc_type):
        path, _ = QFileDialog.getOpenFileName(self, f"Select PDF Template for {doc_type}", "", "PDF Files (*.pdf)")
        if not path: return
        target_dir = os.path.join(os.path.dirname(DB_DIR), "pdf_templates")
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, f"{doc_type.replace(' ', '_')}_template.pdf")
        shutil.copy2(path, target_file)

        db = get_session()
        try:
            rec = db.query(PDFTemplateMapping).filter_by(document_type=doc_type).first()
            if rec: rec.template_path = target_file; db.commit()
            self.refresh_templates_table()
            QMessageBox.information(self, "Success", f"Template uploaded!")
        finally: db.close()

    def open_mapper(self, doc_type):
        self.mapper_win = VisualPDFMapperWindow(doc_type)
        self.mapper_win.show()