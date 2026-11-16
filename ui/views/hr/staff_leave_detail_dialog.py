import os
from datetime import datetime, date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QMessageBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from core.leave_service import LeaveService
from core.hr_service import HRService
from core.icon_manager import IconManager
from ui.components.stitch_widgets import (
    ModernCard, ModernButton, StatusBadge
)

class StaffLeaveDetailDialog(QDialog):
    """
    Modern modal dialog displaying complete staff leave details:
    - Duration, start date, end date, total days
    - Reason why the leave was taken
    - Leave type and annual quota balance
    - Direct 'Mark Arrived / Remove from Leave' action
    """

    def __init__(self, employee_id: int, date_str: str = None, parent=None):
        super().__init__(parent)
        self.employee_id = employee_id
        self.date_str = date_str or datetime.now().strftime("%Y-%m-%d")

        self.setWindowTitle("Staff Leave & Absence Details")
        self.setMinimumWidth(540)
        self.resize(560, 560)
        self.setStyleSheet("background-color: #F8FAFC;")

        # Fetch leave details
        self.leave_data = LeaveService.get_active_leave_for_employee(self.employee_id, self.date_str)
        self.balances = LeaveService.get_employee_balance(self.employee_id)

        self._build_ui()

    def _build_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(20, 20, 20, 20)
        main_lay.setSpacing(14)

        if not self.leave_data:
            lbl_err = QLabel("No active leave record found for this staff member.")
            lbl_err.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 13px;")
            main_lay.addWidget(lbl_err)
            btn_close = ModernButton("Close", icon_name="x", variant="secondary")
            btn_close.clicked.connect(self.reject)
            main_lay.addWidget(btn_close)
            return

        # ── 1. Header Profile Card ──
        header_card = ModernCard()
        h_lay = QHBoxLayout(header_card)
        h_lay.setContentsMargins(16, 14, 16, 14)
        h_lay.setSpacing(14)

        # Avatar Icon
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(48, 48)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet("background-color: #FEF3C7; border: 1px solid #FCD34D; border-radius: 24px;")
        avatar_lbl.setPixmap(IconManager.get_pixmap("calendar-days", color="#D97706", size=24))
        h_lay.addWidget(avatar_lbl)

        # Info Column
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        name_lbl = QLabel(self.leave_data["employee_name"])
        name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #0F172A; background: transparent; border: none;")

        sub_lbl = QLabel(f"ID: <b>{self.leave_data['emp_id']}</b> &nbsp;•&nbsp; {self.leave_data['designation']} ({self.leave_data['department']})")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")

        info_col.addWidget(name_lbl)
        info_col.addWidget(sub_lbl)
        h_lay.addLayout(info_col)
        h_lay.addStretch()

        # Status Badge
        badge = StatusBadge("On Leave", variant="warning")
        h_lay.addWidget(badge)
        main_lay.addWidget(header_card)

        # ── 2. Leave Specification Card ──
        leave_card = ModernCard()
        l_lay = QVBoxLayout(leave_card)
        l_lay.setContentsMargins(16, 14, 16, 14)
        l_lay.setSpacing(12)

        card_title = QLabel("Leave Information & Duration")
        card_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        card_title.setStyleSheet("color: #1E293B; background: transparent;")
        l_lay.addWidget(card_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)

        # Row 0: Leave Type & Total Days
        grid.addWidget(QLabel("<span style='color:#64748B; font-size:11px;'>Leave Type:</span>"), 0, 0)
        lbl_type = QLabel(f"<b>{self.leave_data['leave_type_name']}</b>")
        lbl_type.setStyleSheet("color: #1E3A8A; font-size: 12px;")
        grid.addWidget(lbl_type, 0, 1)

        grid.addWidget(QLabel("<span style='color:#64748B; font-size:11px;'>Total Duration:</span>"), 0, 2)
        days_cnt = self.leave_data["total_days"]
        lbl_days = QLabel(f"<b style='color:#D97706;'>{days_cnt} Day{'s' if days_cnt != 1 else ''}</b>")
        lbl_days.setStyleSheet("font-size: 12px;")
        grid.addWidget(lbl_days, 0, 3)

        # Row 1: Date Range
        grid.addWidget(QLabel("<span style='color:#64748B; font-size:11px;'>From Date:</span>"), 1, 0)
        lbl_from = QLabel(f"<b>{self.leave_data['from_date']}</b>")
        lbl_from.setStyleSheet("color: #334155; font-size: 11px;")
        grid.addWidget(lbl_from, 1, 1)

        grid.addWidget(QLabel("<span style='color:#64748B; font-size:11px;'>To Date:</span>"), 1, 2)
        lbl_to = QLabel(f"<b>{self.leave_data['to_date']}</b>")
        lbl_to.setStyleSheet("color: #334155; font-size: 11px;")
        grid.addWidget(lbl_to, 1, 3)

        # Row 2: Applied / Approval Info
        grid.addWidget(QLabel("<span style='color:#64748B; font-size:11px;'>Applied On:</span>"), 2, 0)
        lbl_app = QLabel(self.leave_data.get("applied_on", "-"))
        lbl_app.setStyleSheet("color: #64748B; font-size: 11px;")
        grid.addWidget(lbl_app, 2, 1)

        grid.addWidget(QLabel("<span style='color:#64748B; font-size:11px;'>Authority Remarks:</span>"), 2, 2)
        lbl_rem = QLabel(self.leave_data.get("admin_remarks", "Approved"))
        lbl_rem.setStyleSheet("color: #16A34A; font-weight: 600; font-size: 11px;")
        grid.addWidget(lbl_rem, 2, 3)

        l_lay.addLayout(grid)

        # Reason Why Block
        l_lay.addSpacing(4)
        l_lay.addWidget(QLabel("<span style='color:#1E293B; font-weight:bold; font-size:11px;'>Reason for Leave (Why):</span>"))
        
        reason_frame = QFrame()
        reason_frame.setStyleSheet("""
            QFrame {
                background-color: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-left: 4px solid #3B82F6;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        rf_lay = QVBoxLayout(reason_frame)
        rf_lay.setContentsMargins(10, 8, 10, 8)
        lbl_reason = QLabel(self.leave_data["reason"])
        lbl_reason.setWordWrap(True)
        lbl_reason.setStyleSheet("color: #334155; font-size: 11px; line-height: 1.4; background: transparent; border: none;")
        rf_lay.addWidget(lbl_reason)
        l_lay.addWidget(reason_frame)

        main_lay.addWidget(leave_card)

        # ── 3. Remaining Annual Quotas ──
        if self.balances:
            bal_card = ModernCard()
            b_lay = QVBoxLayout(bal_card)
            b_lay.setContentsMargins(16, 12, 16, 12)
            b_lay.setSpacing(8)

            b_lay.addWidget(QLabel("<span style='color:#1E293B; font-weight:bold; font-size:11px;'>Annual Leave Balance & Quotas:</span>"))
            b_chips = QHBoxLayout()
            b_chips.setSpacing(10)

            for name, q in self.balances.items():
                chip = QFrame()
                chip.setStyleSheet("""
                    QFrame {
                        background-color: #FFFFFF;
                        border: 1px solid #E2E8F0;
                        border-radius: 6px;
                        padding: 4px 8px;
                    }
                """)
                c_lay = QVBoxLayout(chip)
                c_lay.setContentsMargins(6, 4, 6, 4)
                c_lay.setSpacing(1)
                t_lbl = QLabel(name)
                t_lbl.setStyleSheet("color: #64748B; font-size: 9px; font-weight: bold; background:transparent;")
                v_lbl = QLabel(f"<b>{q['remaining']}</b> / {q['max']} left")
                v_lbl.setStyleSheet("color: #2563EB; font-size: 11px; background:transparent;")
                c_lay.addWidget(t_lbl)
                c_lay.addWidget(v_lbl)
                b_chips.addWidget(chip)

            b_chips.addStretch()
            b_lay.addLayout(b_chips)
            main_lay.addWidget(bal_card)

        main_lay.addStretch()

        # ── 4. Action Buttons Bar ──
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        # Arrived / Return from leave button
        self.btn_arrived = ModernButton("Mark Arrived / Remove from Leave", icon_name="user-check", variant="success")
        self.btn_arrived.setFixedHeight(38)
        self.btn_arrived.clicked.connect(self._mark_arrived)
        btn_bar.addWidget(self.btn_arrived)

        btn_bar.addStretch()

        # Close button
        btn_close = ModernButton("Close", icon_name="x", variant="secondary")
        btn_close.setFixedHeight(38)
        btn_close.clicked.connect(self.reject)
        btn_bar.addWidget(btn_close)

        main_lay.addLayout(btn_bar)

    def _mark_arrived(self):
        emp_name = self.leave_data["employee_name"]
        reply = QMessageBox.question(
            self,
            "Confirm Teacher Arrival",
            f"Are you sure you want to mark <b>{emp_name}</b> as Arrived today ({self.date_str})?<br><br>"
            f"• Employee status will be restored to <b>Active</b>.<br>"
            f"• Their active leave will be concluded.<br>"
            f"• Today's attendance will be marked as <b>Present</b>.<br>"
            f"• They will be removed from Today's Exceptions list.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            success, msg = HRService.mark_employee_arrived(self.employee_id, self.date_str)
            if success:
                QMessageBox.information(self, "Teacher Arrived", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)
