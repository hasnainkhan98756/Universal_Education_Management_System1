import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QProgressBar, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from core.backup_service import BackupService
from core.icon_manager import get_icon

class CountdownResetDialog(QDialog):
    """
    30-Second Countdown Modal for Restoring App to 100% Fresh State.
    Provides a safety grace period so if triggered by mistake,
    the user can click 'RESTORE DATA / CANCEL' to abort and keep all data safe.
    After 30 seconds pass, all audit data, students, teachers, and files
    are permanently wiped and the fresh app appears.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore App to Fresh State — 30s Grace Period")
        self.setFixedSize(540, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.remaining_seconds = 30
        self.wipe_executed = False

        self._setup_ui()
        self._start_timer()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header with Alert Icon
        hdr_layout = QHBoxLayout()
        hdr_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon = get_icon("alert-triangle", color="#DC2626")
        if icon:
            icon_lbl.setPixmap(icon.pixmap(36, 36))
        hdr_layout.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QLabel("Restore Application to Fresh State")
        lbl_title.setStyleSheet("font-size: 17px; font-weight: bold; color: #1E293B;")
        lbl_sub = QLabel("Permanent Data Wipe & Factory Reset")
        lbl_sub.setStyleSheet("font-size: 12px; color: #DC2626; font-weight: 600;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        hdr_layout.addLayout(title_box)
        hdr_layout.addStretch()
        layout.addLayout(hdr_layout)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(sep)

        # Warning / Details Card
        info_card = QFrame()
        info_card.setStyleSheet("""
            QFrame {
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        info_lay = QVBoxLayout(info_card)
        info_lay.setSpacing(6)

        info_text = QLabel(
            "<b>WARNING:</b> This operation will restore the application to a 100% clean, fresh installation:<br>"
            "• <b>Students & Staff:</b> All students, admissions, teachers, and faculty records deleted.<br>"
            "• <b>Classes & Academics:</b> All classes, sections, subjects, workload, and timetable deleted.<br>"
            "• <b>Inventory, Transport & Library:</b> All inventory items, transport routes, and books deleted.<br>"
            "• <b>Audit & Fees:</b> All fee vouchers, payments, audits, and transactions deleted.<br>"
            "• <b>Files & Photos:</b> All student photos and generated documents permanently removed.<br>"
            "• <b>Preserved:</b> Admin login credentials and school configuration remain intact."
        )
        info_text.setStyleSheet("font-size: 11px; color: #7F1D1D; line-height: 140%;")
        info_text.setWordWrap(True)
        info_lay.addWidget(info_text)
        layout.addWidget(info_card)


        # Countdown Display Container
        cd_container = QFrame()
        cd_container.setStyleSheet("""
            QFrame {
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        cd_lay = QVBoxLayout(cd_container)
        cd_lay.setSpacing(6)
        cd_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_countdown = QLabel("30")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown.setStyleSheet("font-size: 38px; font-weight: 900; color: #DC2626;")
        cd_lay.addWidget(self.lbl_countdown)

        self.lbl_status = QLabel("seconds remaining before permanent fresh app wipe")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        cd_lay.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 30)
        self.progress_bar.setValue(30)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #DC2626;
                border-radius: 4px;
            }
        """)
        cd_lay.addWidget(self.progress_bar)
        layout.addWidget(cd_container)

        # Action Buttons Layout
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        # Big, Prominent Restore / Cancel Button
        self.btn_cancel = QPushButton("RESTORE DATA / CANCEL (Mistake — Keep My Data)")
        cancel_icon = get_icon("shield-check", color="#FFFFFF")
        if cancel_icon:
            self.btn_cancel.setIcon(cancel_icon)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 16px;
                border-radius: 6px;
                min-height: 38px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
        """)
        self.btn_cancel.clicked.connect(self.cancel_and_restore)
        btn_layout.addWidget(self.btn_cancel)

        # Secondary Button: Wipe Now (Skip Countdown)
        self.btn_skip = QPushButton("Wipe Now (Skip 30s Countdown)")
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #DC2626;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #DC2626;
                padding: 6px 12px;
                border-radius: 6px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #FEF2F2;
            }
            QPushButton:pressed {
                background-color: #FEE2E2;
            }
        """)
        self.btn_skip.clicked.connect(self.execute_wipe_immediately)
        btn_layout.addWidget(self.btn_skip)

        layout.addLayout(btn_layout)

    def _start_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    def _on_tick(self):
        self.remaining_seconds -= 1
        if self.remaining_seconds > 0:
            self.lbl_countdown.setText(str(self.remaining_seconds))
            self.progress_bar.setValue(self.remaining_seconds)
            if self.remaining_seconds <= 5:
                self.lbl_countdown.setStyleSheet("font-size: 42px; font-weight: 900; color: #991B1B;")
                self.lbl_status.setText("FINAL CHANCE: Click RESTORE DATA to abort!")
                self.lbl_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #991B1B;")
        else:
            self.timer.stop()
            self.lbl_countdown.setText("0")
            self.progress_bar.setValue(0)
            self._execute_wipe()

    def cancel_and_restore(self):
        """User clicked Restore / Cancel. Aborts reset and guarantees data safety."""
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        QMessageBox.information(
            self,
            "Reset Aborted",
            "Reset cancelled successfully!\n\nAll your students, teachers, audit records, and files are 100% safe and intact."
        )
        self.reject()

    def execute_wipe_immediately(self):
        """User chose to bypass the countdown and execute fresh app wipe immediately."""
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
        self._execute_wipe()

    def _execute_wipe(self):
        if self.wipe_executed:
            return
        self.wipe_executed = True

        self.btn_cancel.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.lbl_countdown.setText("...")
        self.lbl_status.setText("Wiping all audit data, students, teachers, and restoring fresh app...")
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: bold; color: #DC2626;")
        QApplication.processEvents()

        success, msg = BackupService.factory_reset_database()
        if success:
            QMessageBox.information(
                self,
                "Fresh App Ready",
                "Application Restored to 100% Fresh State!\n\n"
                "• All students, teachers, and staff have been wiped.\n"
                "• All classes, sections, subjects, and workload have been wiped.\n"
                "• All inventory, transport, and library records have been wiped.\n"
                "• All audit data, fees, attendance, and transactions have been wiped.\n"
                "• All student photos and documents have been permanently removed.\n\n"
                "The application is now 100% fresh and clean."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Reset Error",
                f"An error occurred while resetting the application:\n{msg}"
            )
            self.reject()

    def closeEvent(self, event):
        """If user closes window with X or Alt+F4 before countdown completes, treat as cancel."""
        if not self.wipe_executed:
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()
            event.accept()
        else:
            event.accept()
