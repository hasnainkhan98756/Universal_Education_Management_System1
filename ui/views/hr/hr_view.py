import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, 
                               QTabWidget, QMessageBox, QFrame, QAbstractItemView, 
                               QGridLayout, QDateEdit, QDialog, QFileDialog, QSpinBox,
                               QTextEdit, QDialogButtonBox, QScrollArea, QCheckBox, QAbstractSpinBox)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from core.hr_service import HRService
from core.academic_service import AcademicService
from core.pdf_service import PDFGenerationService
from core.document_service import DocumentService
from core.leave_service import LeaveService
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, MetricCard, StatusBadge,
    ModernButton, TableActionButton, TableTextButton, TableDropdownButton, create_table_actions_cell,
    SearchInput, style_modern_table, style_modern_tabs, SegmentedTabBar
)
from ui.components.loading_widgets import show_print_loading
from database.connection import DB_DIR
from core.state_manager import app_state
from ui.views.hr.employee_profile_dialog import EmployeeProfileDialog
from ui.views.hr.staff_leave_detail_dialog import StaffLeaveDetailDialog
from datetime import datetime, date

class HRView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        header = PageHeader(
            title="Teachers & Staff Management (HR)",
            subtitle="Manage employees, faculty workload, attendance registers, payroll processing, and leave requests",
            icon_name="users-2",
        )
        btn_refresh = ModernButton("Refresh All Data", icon_name="refresh-cw", variant="secondary")
        btn_refresh.clicked.connect(self.refresh_current_view)
        header.add_action_widget(btn_refresh)
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_dashboard_tab(), "HR Analytics")
        self.tabs.setTabIcon(0, get_icon("bar-chart-2", color="#475569"))
        self.tabs.addTab(self.create_directory_tab(), "Staff Directory")
        self.tabs.setTabIcon(1, get_icon("users-2", color="#475569"))
        self.tabs.addTab(self.create_assignment_tab(), "Teaching Workload")
        self.tabs.setTabIcon(2, get_icon("book-open", color="#475569"))
        self.tabs.addTab(self.create_attendance_tab(), "Staff Attendance")
        self.tabs.setTabIcon(3, get_icon("calendar-check", color="#475569"))
        self.tabs.addTab(self.create_payroll_tab(), "Payroll & Salary Slips")
        self.tabs.setTabIcon(4, get_icon("receipt", color="#475569"))
        self.tabs.addTab(self.create_leave_tab(), "Leave Management")
        self.tabs.setTabIcon(5, get_icon("calendar-days", color="#475569"))

        main_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        app_state.subscribe_data_changed(self.refresh_current_view)
        self.refresh_current_view()

    def refresh_all(self):
        self.refresh_current_view()

    def on_tab_changed(self, index):
        self.refresh_current_view()

    def showEvent(self, event):
        """CRITICAL FIX: Forces a live sync the moment you click the HR tab from the Sidebar!"""
        self.refresh_current_view()
        super().showEvent(event)

    def _btn(self, text, color):
        btn = QPushButton(text)
        if color == "#10B981":
            btn.setObjectName("btn_success")
        elif color == "#EF4444":
            btn.setObjectName("btn_danger")
        elif color == "#8B5CF6":
            btn.setObjectName("btn_purple")
        elif color == "#F59E0B":
            btn.setObjectName("btn_warning")
        else:
            btn.setObjectName("btn_primary")
        return btn

    def _table(self):
        tbl = QTableWidget()
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(36)
        style_modern_table(tbl)
        return tbl

    def _stat_card(self, title, init_val, color_hex):
        icon_map = {
            "Active Staff / Teachers": "users-2",
            "Present Today": "check-circle-2",
            "Absent / Leave Today": "alert-circle",
            "Salary Paid (This Month)": "wallet",
            "Salary Pending (This Month)": "clock",
            "Total Committed Payroll": "credit-card",
            "Pending Applications": "clock",
            "Approved (This Year)": "check-circle-2",
            "Staff On Leave Today": "calendar-days",
        }
        icon_name = icon_map.get(title, "info")
        return MetricCard(title=title, value=init_val, icon_name=icon_name, accent_color=color_hex)

    # ==========================================
    # TAB 0: HR DASHBOARD ANALYTICS
    # ==========================================
    def create_dashboard_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)

        top_bar = QHBoxLayout()
        self.dash_date = QDateEdit(QDate.currentDate())
        self.dash_date.setCalendarPopup(True)
        self.dash_date.dateChanged.connect(self.refresh_dashboard_analytics)

        self.dash_month = QComboBox()
        self.dash_month.addItems([
            "January 2026", "February 2026", "March 2026", "April 2026", "May 2026", "June 2026",
            "July 2026", "August 2026", "September 2026", "October 2026", "November 2026", "December 2026"
        ])
        curr_m_str = datetime.now().strftime("%B %Y")
        idx = self.dash_month.findText(curr_m_str)
        if idx >= 0:
            self.dash_month.setCurrentIndex(idx)
        self.dash_month.currentIndexChanged.connect(self.refresh_dashboard_analytics)

        top_bar.addWidget(QLabel("<b>Attendance Date:</b>"))
        top_bar.addWidget(self.dash_date)
        top_bar.addSpacing(20)
        top_bar.addWidget(QLabel("<b>Payroll Month:</b>"))
        top_bar.addWidget(self.dash_month)
        top_bar.addStretch()
        lay.addLayout(top_bar)

        grid = QGridLayout()
        grid.setSpacing(15)

        self.card_total_staff = self._stat_card("Active Staff / Teachers", "0 / 0", "#1E3A8A")
        self.card_today_present = self._stat_card("Present Today", "0 (0%)", "#10B981")
        self.card_today_absent = self._stat_card("Absent / Leave Today", "0 / 0", "#EF4444")
        self.card_month_paid = self._stat_card("Salary Paid (This Month)", "Rs. 0", "#059669")
        self.card_month_pending = self._stat_card("Salary Pending (This Month)", "Rs. 0", "#F59E0B")
        self.card_total_payroll = self._stat_card("Total Committed Payroll", "Rs. 0", "#8B5CF6")

        grid.addWidget(self.card_total_staff, 0, 0)
        grid.addWidget(self.card_today_present, 0, 1)
        grid.addWidget(self.card_today_absent, 0, 2)
        grid.addWidget(self.card_month_paid, 1, 0)
        grid.addWidget(self.card_month_pending, 1, 1)
        grid.addWidget(self.card_total_payroll, 1, 2)

        lay.addLayout(grid)

        lay.addWidget(QLabel("<b>Today's Staff Exceptions (Absent / On Leave / Late):</b>"))
        self.tbl_dash_exceptions = self._table()
        self.tbl_dash_exceptions.setColumnCount(6)
        self.tbl_dash_exceptions.setHorizontalHeaderLabels(["Emp ID", "Staff Name", "Department", "Status", "Remarks", "Action"])
        self.tbl_dash_exceptions.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tbl_dash_exceptions.setColumnWidth(5, 135)
        self.tbl_dash_exceptions.setMinimumHeight(280)
        self.tbl_dash_exceptions.cellClicked.connect(self._on_dash_exception_clicked)
        lay.addWidget(self.tbl_dash_exceptions)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def refresh_dashboard_analytics(self):
        d_str = self.dash_date.date().toString("yyyy-MM-dd")
        m_str = self.dash_month.currentText()
        stats = HRService.get_hr_dashboard_stats(d_str, m_str)

        self.card_total_staff.value_label.setText(f"{stats['active_staff']} Active ({stats['teachers_count']} Teachers)")
        self.card_today_present.value_label.setText(f"{stats['att_present']} ({stats['att_rate']}%)")
        self.card_today_absent.value_label.setText(f"{stats['att_absent']} Absent | {stats['att_leave']} Leave")
        self.card_month_paid.value_label.setText(f"Rs. {stats['total_paid']:,.0f} ({stats['paid_count']} Paid)")
        self.card_month_pending.value_label.setText(f"Rs. {stats['total_pending']:,.0f} ({stats['pending_count']} Due)")
        self.card_total_payroll.value_label.setText(f"Rs. {stats['total_expense_budget']:,.0f}")

        sheet = HRService.get_staff_attendance_sheet(d_str)
        exceptions = [s for s in sheet if s["status"] in ["Absent", "Leave", "Late", "Half Day"]]

        for child in self.tbl_dash_exceptions.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_dash_exceptions.clearContents()
        self.tbl_dash_exceptions.clearSpans()

        if not exceptions:
            self.tbl_dash_exceptions.setRowCount(1)
            self.tbl_dash_exceptions.setRowHeight(0, 44)
            item = QTableWidgetItem("All staff members are present today - no attendance exceptions.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#10B981"))
            font = QFont("Segoe UI", 10)
            font.setItalic(True)
            item.setFont(font)
            self.tbl_dash_exceptions.setItem(0, 0, item)
            self.tbl_dash_exceptions.setSpan(0, 0, 1, 6)
        else:
            self.tbl_dash_exceptions.setRowCount(len(exceptions))
            for r, exc in enumerate(exceptions):
                self.tbl_dash_exceptions.setRowHeight(r, 44)
                
                id_item = QTableWidgetItem(exc["emp_id"])
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setData(Qt.ItemDataRole.UserRole, exc["id"])
                self.tbl_dash_exceptions.setItem(r, 0, id_item)
                
                name_item = QTableWidgetItem(exc["name"])
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                name_item.setData(Qt.ItemDataRole.UserRole, exc["id"])
                name_item.setToolTip("Click to view full leave details or mark teacher arrived")
                self.tbl_dash_exceptions.setItem(r, 1, name_item)
                
                dept_item = QTableWidgetItem(exc["department"])
                dept_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tbl_dash_exceptions.setItem(r, 2, dept_item)
                
                st_item = QTableWidgetItem(exc["status"])
                st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if exc["status"] == "Absent": st_item.setForeground(QColor("#EF4444"))
                elif exc["status"] == "Leave": st_item.setForeground(QColor("#F59E0B"))
                elif exc["status"] == "Late": st_item.setForeground(QColor("#8B5CF6"))
                else: st_item.setForeground(QColor("#3B82F6"))
                st_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                self.tbl_dash_exceptions.setItem(r, 3, st_item)
                
                rem_item = QTableWidgetItem(exc["remarks"] or "-")
                rem_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tbl_dash_exceptions.setItem(r, 4, rem_item)

                if exc["status"] == "Leave":
                    btn_leave = TableTextButton("Leave Details", icon_name="calendar-days", variant="secondary")
                    btn_leave.setToolTip("View leave duration, reason, and mark teacher arrived")
                    btn_leave.clicked.connect(lambda _, eid=exc["id"]: self._open_leave_detail(eid))
                    self.tbl_dash_exceptions.setCellWidget(r, 5, create_table_actions_cell([btn_leave]))
                else:
                    item_dash = QTableWidgetItem("-")
                    item_dash.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tbl_dash_exceptions.setItem(r, 5, item_dash)

    def _on_dash_exception_clicked(self, row, col):
        if col == 5:
            return
        id_item = self.tbl_dash_exceptions.item(row, 0)
        st_item = self.tbl_dash_exceptions.item(row, 3)
        if not id_item:
            return
        eid = id_item.data(Qt.ItemDataRole.UserRole)
        if eid and st_item and st_item.text() == "Leave":
            self._open_leave_detail(eid)

    def _open_leave_detail(self, employee_id):
        d_str = self.dash_date.date().toString("yyyy-MM-dd")
        dlg = StaffLeaveDetailDialog(employee_id, d_str, self)
        if dlg.exec():
            self.refresh_current_view()

    # ==========================================
    # TAB 1: STAFF DIRECTORY
    # ==========================================
    def create_directory_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        
        self.subtab_bar = SegmentedTabBar([
            "All Personnel",
            "Active Faculty & Staff",
            "On Leave",
            "Retired Veterans",
            "Resigned & Terminated",
            "Suspended Under Inquiry"
        ], initial_index=1)
        self.subtab_bar.tab_changed.connect(self._on_subtab_changed)
        lay.addWidget(self.subtab_bar)

        filter_lay = QHBoxLayout()
        self.inp_search_emp = SearchInput(placeholder="Search by Name, ID, CNIC, Phone...")
        
        # Debounce staff search by 250ms
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_directory)
        self.inp_search_emp.textChanged.connect(lambda _: self._search_timer.start())
        
        self.filter_status = QComboBox()
        self.filter_status.addItems(["All", "Active", "On Leave", "Retired", "Suspended", "Resigned", "Terminated", "Inactive"])
        self.filter_status.currentIndexChanged.connect(self._on_combo_status_changed)
        
        self.filter_type = QComboBox()
        self.filter_type.addItems(["All", "Teacher", "Principal", "Admin", "Clerk", "Support Staff"])
        self.filter_type.currentIndexChanged.connect(self.refresh_directory)

        btn_add = ModernButton("Register New Staff", icon_name="plus", variant="primary")
        btn_add.clicked.connect(lambda: self.open_employee_form(None))

        btn_export = ModernButton("Export Excel", icon_name="download", variant="secondary")
        btn_export.clicked.connect(self.export_employees)

        filter_lay.addWidget(self.inp_search_emp, stretch=2)
        filter_lay.addWidget(QLabel("Status:"))
        filter_lay.addWidget(self.filter_status)
        filter_lay.addWidget(QLabel("Type:"))
        filter_lay.addWidget(self.filter_type)
        filter_lay.addWidget(btn_add)
        filter_lay.addWidget(btn_export)
        lay.addLayout(filter_lay)

        self.tbl_dir = self._table()
        self.tbl_dir.setColumnCount(8)
        self.tbl_dir.setHorizontalHeaderLabels(["Emp ID", "Name", "Designation", "Department", "Phone", "Status", "Actions", "DB_ID"])
        self.tbl_dir.setColumnHidden(7, True)
        self.tbl_dir.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_dir.setColumnWidth(6, 170)
        self.tbl_dir.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_dir)
        return page

    def _on_subtab_changed(self, idx: int, text: str):
        if not hasattr(self, 'filter_status'): return
        self.filter_status.blockSignals(True)
        if text == "All Personnel":
            self.filter_status.setCurrentText("All")
        elif text == "Active Faculty & Staff":
            self.filter_status.setCurrentText("Active")
        elif text == "On Leave":
            self.filter_status.setCurrentText("On Leave")
        elif text == "Retired Veterans":
            self.filter_status.setCurrentText("Retired")
        elif text == "Resigned & Terminated":
            self.filter_status.setCurrentText("Resigned")
        elif text == "Suspended Under Inquiry":
            self.filter_status.setCurrentText("Suspended")
        self.filter_status.blockSignals(False)
        self.refresh_directory()

    def _on_combo_status_changed(self):
        if hasattr(self, 'subtab_bar') and hasattr(self, 'filter_status'):
            st = self.filter_status.currentText()
            self.subtab_bar.blockSignals(True)
            if st in ["All", "All Status"]:
                self.subtab_bar.set_current_index(0)
            elif st == "Active":
                self.subtab_bar.set_current_index(1)
            elif st == "On Leave":
                self.subtab_bar.set_current_index(2)
            elif st == "Retired":
                self.subtab_bar.set_current_index(3)
            elif st in ["Resigned", "Terminated"]:
                self.subtab_bar.set_current_index(4)
            elif st == "Suspended":
                self.subtab_bar.set_current_index(5)
            self.subtab_bar.blockSignals(False)
        self.refresh_directory()

    def open_employee_form(self, emp_db_id=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Employee Master Record" if not emp_db_id else "Edit Employee Record")
        dialog.setMinimumWidth(550)
        lay = QFormLayout(dialog)

        fname = QLineEdit(); lname = QLineEdit()
        gen = QComboBox(); gen.addItems(["Male", "Female"])
        cnic = QLineEdit(); phone = QLineEdit(); email = QLineEdit()
        etype = QComboBox(); etype.addItems(["Teacher", "Principal", "Admin", "Clerk", "Support Staff", "Security", "Driver"])
        desig = QLineEdit(); dept = QLineEdit()
        salary = QDoubleSpinBox(); salary.setRange(0, 1000000); salary.setValue(35000.0)
        qual = QLineEdit(); exp = QLineEdit(); addr = QLineEdit()
        stat = QComboBox(); stat.addItems(["Active", "On Leave", "Retired", "Suspended", "Resigned", "Terminated", "Inactive"])

        if emp_db_id:
            emp = HRService.get_employee_by_id(emp_db_id)
            if emp:
                fname.setText(emp.first_name); lname.setText(emp.last_name or "")
                gen.setCurrentText(emp.gender or "Male")
                cnic.setText(emp.cnic or ""); phone.setText(emp.phone or ""); email.setText(emp.email or "")
                etype.setCurrentText(emp.emp_type or "Teacher")
                desig.setText(emp.designation or ""); dept.setText(emp.department or "")
                salary.setValue(emp.basic_salary or 0.0)
                qual.setText(getattr(emp, 'qualification', '') or ""); exp.setText(emp.experience or ""); addr.setText(emp.address or "")
                if emp.status: stat.setCurrentText(emp.status)

        lay.addRow("First Name *:", fname); lay.addRow("Last Name:", lname)
        lay.addRow("Gender:", gen); lay.addRow("CNIC / ID Card:", cnic)
        lay.addRow("Phone Number:", phone); lay.addRow("Email:", email)
        lay.addRow("Employee Type:", etype); lay.addRow("Designation:", desig)
        lay.addRow("Department:", dept); lay.addRow("Basic Salary (Rs.):", salary)
        lay.addRow("Employment Status:", stat)
        lay.addRow("Qualification:", qual); lay.addRow("Experience:", exp)
        lay.addRow("Residential Address:", addr)

        btn_save = ModernButton("Save Employee", icon_name="save", variant="primary")
        btn_save.clicked.connect(dialog.accept)
        lay.addWidget(btn_save)

        if dialog.exec():
            data = {
                "first_name": fname.text().strip(), "last_name": lname.text().strip(),
                "gender": gen.currentText(), "cnic": cnic.text().strip(),
                "phone": phone.text().strip(), "email": email.text().strip(),
                "emp_type": etype.currentText(), "designation": desig.text().strip(),
                "department": dept.text().strip(), "basic_salary": salary.value(),
                "qualification": qual.text().strip(), "experience": exp.text().strip(),
                "address": addr.text().strip(), "status": stat.currentText()
            }
            if not data["first_name"]:
                QMessageBox.warning(self, "Validation", "First Name is strictly required."); return
            
            if emp_db_id:
                success, msg = HRService.update_employee(emp_db_id, data)
            else:
                success, msg = HRService.add_employee(data)
            
            if success:
                QMessageBox.information(self, "Success", msg)
                self.refresh_directory()
                self.refresh_dashboard_analytics()
            else:
                QMessageBox.critical(self, "Error", msg)

    def refresh_directory(self):
        s_term = self.inp_search_emp.text().strip()
        st_filter = self.filter_status.currentText()
        if hasattr(self, 'subtab_bar') and self.subtab_bar.current_index() > 0:
            subtab_text = self.subtab_bar.current_text()
            if subtab_text != "All Personnel":
                st_filter = subtab_text
        tp_filter = self.filter_type.currentText()

        for child in self.tbl_dir.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_dir.clearContents()

        staff = HRService.get_employees(status_filter=st_filter, type_filter=tp_filter, search_query=s_term)
        total_matched = len(staff)
        DISPLAY_LIMIT = 300
        display_staff = staff[:DISPLAY_LIMIT] if total_matched > DISPLAY_LIMIT else staff

        self.tbl_dir.setRowCount(len(display_staff))
        for r, s in enumerate(display_staff):
            self.tbl_dir.setItem(r, 0, QTableWidgetItem(s.emp_id))
            self.tbl_dir.setItem(r, 1, QTableWidgetItem(f"{s.first_name} {s.last_name or ''}".strip()))
            self.tbl_dir.setItem(r, 2, QTableWidgetItem(s.designation or "-"))
            self.tbl_dir.setItem(r, 3, QTableWidgetItem(s.department or "-"))
            self.tbl_dir.setItem(r, 4, QTableWidgetItem(s.phone or "-"))
            
            st_item = QTableWidgetItem(s.status)
            if s.status == "Active":
                st_item.setForeground(QColor("#10B981"))
            elif s.status == "Retired":
                st_item.setForeground(QColor("#8B5CF6"))
            elif s.status in ["On Leave", "Leave"]:
                st_item.setForeground(QColor("#0EA5E9"))
            elif s.status == "Suspended":
                st_item.setForeground(QColor("#F59E0B"))
            else:
                st_item.setForeground(QColor("#EF4444"))
            self.tbl_dir.setItem(r, 5, st_item)

            btn_view = TableTextButton("Profile", icon_name="eye", variant="secondary")
            btn_view.clicked.connect(lambda checked=False, sid=s.id: EmployeeProfileDialog(sid, self).exec())
            
            btn_edit = TableTextButton("Edit", icon_name="pencil", variant="secondary")
            btn_edit.clicked.connect(lambda checked=False, sid=s.id: self.open_employee_form(sid))

            self.tbl_dir.setCellWidget(r, 6, create_table_actions_cell([btn_view, btn_edit]))
            self.tbl_dir.setItem(r, 7, QTableWidgetItem(str(s.id)))
            self.tbl_dir.setRowHeight(r, 48)

    def export_employees(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Staff Directory", "Staff_Directory.xlsx", "Excel Files (*.xlsx)")
        if path:
            HRService.export_employees_to_excel(path)
            QMessageBox.information(self, "Exported", f"Staff directory exported:\n{path}")

    # ==========================================
    # TAB 2: TEACHING WORKLOAD
    # ==========================================
    def create_assignment_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        
        form_lay = QHBoxLayout()
        self.combo_teacher = QComboBox()
        self.combo_cls = QComboBox()
        self.combo_cls.currentIndexChanged.connect(self.sync_assignment_dropdowns)
        self.combo_sec = QComboBox()
        self.combo_sub = QComboBox()
        self.spin_periods = QSpinBox()
        self.spin_periods.setRange(1, 40)
        self.spin_periods.setValue(5)
        
        btn_assign = ModernButton("Assign Workload", icon_name="plus", variant="primary")
        btn_assign.clicked.connect(self.add_assignment)

        btn_exp_load = ModernButton("Export Excel", icon_name="download", variant="secondary")
        btn_exp_load.clicked.connect(self.export_workload)

        form_lay.addWidget(QLabel("Teacher:"))
        form_lay.addWidget(self.combo_teacher)
        form_lay.addWidget(QLabel("Class:"))
        form_lay.addWidget(self.combo_cls)
        form_lay.addWidget(QLabel("Section:"))
        form_lay.addWidget(self.combo_sec)
        form_lay.addWidget(QLabel("Subject:"))
        form_lay.addWidget(self.combo_sub)
        form_lay.addWidget(QLabel("Periods/Wk:"))
        form_lay.addWidget(self.spin_periods)
        form_lay.addWidget(btn_assign)
        form_lay.addWidget(btn_exp_load)
        lay.addLayout(form_lay)

        self.tbl_assign = self._table()
        self.tbl_assign.setColumnCount(7)
        self.tbl_assign.setHorizontalHeaderLabels(["Teacher", "Emp ID", "Class", "Section", "Subject", "Periods", "Action"])
        self.tbl_assign.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_assign.setColumnWidth(6, 110)
        self.tbl_assign.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_assign)
        return page

    def sync_assignment_dropdowns(self):
        cid = self.combo_cls.currentData()
        self.combo_sec.clear()
        self.combo_sub.clear()
        if cid:
            for sec in AcademicService.get_sections(cid):
                self.combo_sec.addItem(sec.name, sec.id)
            subs, _ = AcademicService.get_class_subject_assignment(cid)
            for sub in subs:
                self.combo_sub.addItem(sub.name, sub.id)

    def refresh_assignments(self):
        self.combo_teacher.clear()
        self.combo_cls.clear()
        for t in HRService.get_employees("Active"):
            if t.emp_type == "Teacher":
                self.combo_teacher.addItem(f"{t.first_name} {t.last_name or ''}", t.id)
        for c in AcademicService.get_classes():
            self.combo_cls.addItem(c.name, c.id)

        for child in self.tbl_assign.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_assign.clearContents()

        assigns = HRService.get_assignments()
        self.tbl_assign.setRowCount(len(assigns))
        for r, a in enumerate(assigns):
            self.tbl_assign.setItem(r, 0, QTableWidgetItem(f"{a.employee.first_name} {a.employee.last_name or ''}"))
            self.tbl_assign.setItem(r, 1, QTableWidgetItem(a.employee.emp_id))
            self.tbl_assign.setItem(r, 2, QTableWidgetItem(a.academic_class.name))
            self.tbl_assign.setItem(r, 3, QTableWidgetItem(a.academic_section.name))
            self.tbl_assign.setItem(r, 4, QTableWidgetItem(a.academic_subject.name))
            self.tbl_assign.setItem(r, 5, QTableWidgetItem(str(a.periods_per_week)))
            
            btn_del = TableTextButton("Remove", icon_name="trash-2", variant="danger")
            btn_del.clicked.connect(lambda checked=False, aid=a.id: self.delete_assignment(aid))
            self.tbl_assign.setCellWidget(r, 6, create_table_actions_cell([btn_del]))
            self.tbl_assign.setRowHeight(r, 48)

    def add_assignment(self):
        tid = self.combo_teacher.currentData()
        cid = self.combo_cls.currentData()
        secid = self.combo_sec.currentData()
        subid = self.combo_sub.currentData()
        if not tid or not cid or not secid or not subid:
            QMessageBox.warning(self, "Validation", "Select teacher, class, section, and subject.")
            return
        
        success, msg = HRService.assign_teacher(tid, cid, secid, subid, self.spin_periods.value())
        if success:
            QMessageBox.information(self, "Assigned", msg)
            self.refresh_assignments()
        else:
            QMessageBox.warning(self, "Duplicate Protection", msg)

    def delete_assignment(self, aid):
        if QMessageBox.question(self, "Confirm", "Remove this workload assignment?") == QMessageBox.StandardButton.Yes:
            HRService.delete_assignment(aid)
            self.refresh_assignments()

    def export_workload(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Workload", "Teaching_Workload.xlsx", "Excel Files (*.xlsx)")
        if path:
            HRService.export_workload_to_excel(path)
            QMessageBox.information(self, "Exported", f"Workload exported:\n{path}")

    # ==========================================
    # TAB 3: STAFF ATTENDANCE
    # ==========================================
    def create_attendance_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)

        self.att_sub_tabs = QTabWidget()
        style_modern_tabs(self.att_sub_tabs)

        daily_widget = QWidget()
        d_lay = QVBoxLayout(daily_widget)
        ctrl = QHBoxLayout()
        self.att_date = QDateEdit(QDate.currentDate())
        self.att_date.setCalendarPopup(True)
        self.att_date.dateChanged.connect(self.load_attendance)
        btn_load = ModernButton("Load Register", icon_name="refresh-cw", variant="secondary")
        btn_load.clicked.connect(self.load_attendance)
        
        btn_all_p = ModernButton("All Present", icon_name="check", variant="success")
        btn_all_p.clicked.connect(lambda: self.mark_all_att("Present"))
        btn_all_a = ModernButton("All Absent", icon_name="x", variant="danger")
        btn_all_a.clicked.connect(lambda: self.mark_all_att("Absent"))
        btn_all_h = ModernButton("All Holiday", icon_name="calendar-days", variant="warning")
        btn_all_h.clicked.connect(lambda: self.mark_all_att("Holiday"))

        ctrl.addWidget(QLabel("Date:"))
        ctrl.addWidget(self.att_date)
        ctrl.addWidget(btn_load)
        ctrl.addStretch()
        ctrl.addWidget(btn_all_p)
        ctrl.addWidget(btn_all_a)
        ctrl.addWidget(btn_all_h)
        d_lay.addLayout(ctrl)

        self.lbl_staff_holiday_banner = QLabel()
        self.lbl_staff_holiday_banner.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1.5px solid #F59E0B; "
            "border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold;"
        )
        self.lbl_staff_holiday_banner.setVisible(False)
        d_lay.addWidget(self.lbl_staff_holiday_banner)

        self.tbl_att = self._table()
        self.tbl_att.setColumnCount(6)
        self.tbl_att.setHorizontalHeaderLabels(["Emp ID", "Name", "Department", "Designation", "Status", "Remarks"])
        d_lay.addWidget(self.tbl_att)

        btn_save = ModernButton("Save Staff Attendance", icon_name="save", variant="primary")
        btn_save.clicked.connect(self.save_attendance)
        d_lay.addWidget(btn_save)

        monthly_widget = QWidget()
        m_lay = QVBoxLayout(monthly_widget)
        m_ctrl = QHBoxLayout()
        self.att_rep_year = QSpinBox()
        self.att_rep_year.setRange(2000, 2100)
        self.att_rep_year.setValue(datetime.now().year)

        self.att_rep_month = QComboBox()
        self.att_rep_month.addItems([
            "00 - Full Year", "01 - January", "02 - February", "03 - March", "04 - April",
            "05 - May", "06 - June", "07 - July", "08 - August", "09 - September",
            "10 - October", "11 - November", "12 - December"
        ])
        self.att_rep_month.setCurrentIndex(datetime.now().month)

        btn_gen_rep = ModernButton("View Attendance Report", icon_name="bar-chart-2", variant="primary")
        btn_gen_rep.clicked.connect(self.load_monthly_attendance_report)

        btn_exp_rep = ModernButton("Export Attendance to Excel", icon_name="download", variant="secondary")
        btn_exp_rep.clicked.connect(self.export_monthly_attendance)

        m_ctrl.addWidget(QLabel("Year:"))
        m_ctrl.addWidget(self.att_rep_year)
        m_ctrl.addWidget(QLabel("Month:"))
        m_ctrl.addWidget(self.att_rep_month)
        m_ctrl.addWidget(btn_gen_rep)
        m_ctrl.addWidget(btn_exp_rep)
        m_ctrl.addStretch()
        m_lay.addLayout(m_ctrl)

        self.tbl_monthly_att = self._table()
        self.tbl_monthly_att.setColumnCount(9)
        self.tbl_monthly_att.setHorizontalHeaderLabels([
            "Emp ID", "Name", "Department", "Total Days", "Present", "Absent", "Leave", "Late", "Attendance %"
        ])
        m_lay.addWidget(self.tbl_monthly_att)

        self.att_sub_tabs.addTab(daily_widget, "Daily Attendance Register")
        self.att_sub_tabs.setTabIcon(0, get_icon("calendar-check", color="#475569"))
        self.att_sub_tabs.addTab(monthly_widget, "Monthly Attendance Report")
        self.att_sub_tabs.setTabIcon(1, get_icon("bar-chart-2", color="#475569"))
        lay.addWidget(self.att_sub_tabs)
        return page

    def load_attendance(self):
        d_str = self.att_date.date().toString("yyyy-MM-dd")
        from core.calendar_service import CalendarService
        holiday_info = CalendarService.get_holiday_or_event(d_str)
        if hasattr(self, 'lbl_staff_holiday_banner'):
            if holiday_info:
                date_range = holiday_info['start_date'] if holiday_info['start_date'] == holiday_info['end_date'] else f"{holiday_info['start_date']} to {holiday_info['end_date']}"
                self.lbl_staff_holiday_banner.setText(
                    f"<b>{holiday_info['event_type']} Notice:</b> {holiday_info['title']} ({date_range}) — "
                    f"Institution is officially closed on this date according to the Academic Calendar. Attendance is not required. "
                    f"(If staff worked or school was open today, you can adjust status to Present/Absent and save)."
                )
                self.lbl_staff_holiday_banner.setVisible(True)
            else:
                self.lbl_staff_holiday_banner.setVisible(False)

        data = HRService.get_staff_attendance_sheet(d_str)
        self.tbl_att.setRowCount(len(data))
        for r, s in enumerate(data):
            self.tbl_att.setRowHeight(r, 44)
            id_item = QTableWidgetItem(s["emp_id"])
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_att.setItem(r, 0, id_item)
            
            name_item = QTableWidgetItem(s["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.tbl_att.setItem(r, 1, name_item)
            
            dept_item = QTableWidgetItem(s["department"])
            dept_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.tbl_att.setItem(r, 2, dept_item)
            
            desig_item = QTableWidgetItem(s["designation"])
            desig_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.tbl_att.setItem(r, 3, desig_item)
            
            cb = QComboBox()
            cb.addItems(["Present", "Absent", "Late", "Half Day", "Leave", "Holiday"])
            cb.setCurrentText(s["status"])
            self.tbl_att.setCellWidget(r, 4, cb)
            
            rem = QLineEdit(s["remarks"])
            rem.setStyleSheet("padding: 4px 8px; border: 1px solid #D1D5DB; border-radius: 6px;")
            self.tbl_att.setCellWidget(r, 5, rem)
            self.tbl_att.item(r, 0).setData(Qt.ItemDataRole.UserRole, s["id"])

            # Auto-clear leave remarks if status changed to Present/Late/Half Day
            cb.currentTextChanged.connect(lambda txt, line_edit=rem: (
                line_edit.setText("") if txt in ["Present", "Late", "Half Day"] and ("Leave" in line_edit.text() or "Sanctioned" in line_edit.text()) else None
            ))

    def mark_all_att(self, st):
        for r in range(self.tbl_att.rowCount()):
            cb = self.tbl_att.cellWidget(r, 4)
            rem = self.tbl_att.cellWidget(r, 5)
            if cb:
                cb.setCurrentText(st)
                if st in ["Present", "Late", "Half Day"] and rem and ("Leave" in rem.text() or "Sanctioned" in rem.text()):
                    rem.setText("")

    def save_attendance(self):
        d_str = self.att_date.date().toString("yyyy-MM-dd")
        rows = self.tbl_att.rowCount()
        data = []
        for r in range(rows):
            data.append({
                "id": self.tbl_att.item(r, 0).data(Qt.ItemDataRole.UserRole),
                "status": self.tbl_att.cellWidget(r, 4).currentText(),
                "remarks": self.tbl_att.cellWidget(r, 5).text()
            })
        success, msg = HRService.save_staff_attendance(d_str, data)
        if success:
            QMessageBox.information(self, "Saved", msg)
            self.refresh_current_view()
        else:
            QMessageBox.critical(self, "Error", msg)

    def load_monthly_attendance_report(self):
        y = self.att_rep_year.value()
        m = self.att_rep_month.currentIndex()
        data = HRService.get_monthly_staff_attendance_report(y, m)
        self.tbl_monthly_att.setRowCount(len(data))
        for r, s in enumerate(data):
            self.tbl_monthly_att.setRowHeight(r, 44)
            
            id_item = QTableWidgetItem(s["emp_id"])
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_monthly_att.setItem(r, 0, id_item)
            
            name_item = QTableWidgetItem(s["name"])
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.tbl_monthly_att.setItem(r, 1, name_item)
            
            dept_item = QTableWidgetItem(s["department"])
            dept_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.tbl_monthly_att.setItem(r, 2, dept_item)
            
            tot_item = QTableWidgetItem(str(s["total_days"]))
            tot_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_monthly_att.setItem(r, 3, tot_item)
            
            p_item = QTableWidgetItem(str(s["present"]))
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            p_item.setForeground(QColor("#10B981"))
            
            a_item = QTableWidgetItem(str(s["absent"]))
            a_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            a_item.setForeground(QColor("#EF4444"))
            
            l_item = QTableWidgetItem(str(s["leave"]))
            l_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            l_item.setForeground(QColor("#F59E0B"))
            
            lt_item = QTableWidgetItem(str(s["late"]))
            lt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            lt_item.setForeground(QColor("#3B82F6"))

            self.tbl_monthly_att.setItem(r, 4, p_item)
            self.tbl_monthly_att.setItem(r, 5, a_item)
            self.tbl_monthly_att.setItem(r, 6, l_item)
            self.tbl_monthly_att.setItem(r, 7, lt_item)

            pct_item = QTableWidgetItem(f"{s['percentage']}%")
            pct_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            pct_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if s["percentage"] >= 80: pct_item.setForeground(QColor("#10B981"))
            elif s["percentage"] >= 60: pct_item.setForeground(QColor("#F59E0B"))
            else: pct_item.setForeground(QColor("#EF4444"))
            self.tbl_monthly_att.setItem(r, 8, pct_item)

    def export_monthly_attendance(self):
        y = self.att_rep_year.value()
        m = self.att_rep_month.currentIndex()
        path, _ = QFileDialog.getSaveFileName(self, "Export Attendance Report", f"Staff_Attendance_{y}_{m}.xlsx", "Excel Files (*.xlsx)")
        if path:
            HRService.export_monthly_attendance_to_excel(y, m, path)
            QMessageBox.information(self, "Exported", f"Attendance report exported:\n{path}")

    # ==========================================
    # TAB 4: PAYROLL
    # ==========================================
    def create_payroll_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(20, 20, 20, 20)
        
        ctrl = QHBoxLayout()
        self.pay_month = QComboBox()
        self.pay_month.addItems([
            "January 2026", "February 2026", "March 2026", "April 2026", "May 2026", "June 2026",
            "July 2026", "August 2026", "September 2026", "October 2026", "November 2026", "December 2026"
        ])
        curr_m_str = datetime.now().strftime("%B %Y")
        p_idx = self.pay_month.findText(curr_m_str)
        if p_idx >= 0:
            self.pay_month.setCurrentIndex(p_idx)

        self.filter_pay_status = QComboBox()
        self.filter_pay_status.addItems(["All Statuses", "Paid", "Pending"])
        self.filter_pay_status.currentIndexChanged.connect(self.load_payroll)

        btn_gen = ModernButton("Generate Monthly Payroll", icon_name="file-spreadsheet", variant="primary")
        btn_gen.clicked.connect(self.generate_payroll)
        
        btn_load = ModernButton("Load Register", icon_name="refresh-cw", variant="secondary")
        btn_load.clicked.connect(self.load_payroll)
        
        btn_exp_pay = ModernButton("Export Expense Register", icon_name="download", variant="secondary")
        btn_exp_pay.clicked.connect(self.export_payroll)

        ctrl.addWidget(QLabel("Month:"))
        ctrl.addWidget(self.pay_month)
        ctrl.addWidget(QLabel("Show:"))
        ctrl.addWidget(self.filter_pay_status)
        ctrl.addWidget(btn_gen)
        ctrl.addWidget(btn_load)
        ctrl.addWidget(btn_exp_pay)
        ctrl.addStretch()
        lay.addLayout(ctrl)

        self.lbl_pay_summary = QLabel("Loading payroll summary...")
        lay.addWidget(self.lbl_pay_summary)

        self.tbl_pay = self._table()
        self.tbl_pay.setColumnCount(13)
        self.tbl_pay.setHorizontalHeaderLabels([
            "Receipt No", "Name", "Basic", "Allowances", "Bonus", "Overtime", 
            "Deductions", "Advance", "Tax", "Net Salary", "Status", "Payment Date", "Action"
        ])
        col_widths = {
            0: 110,  # Receipt No
            1: 140,  # Name
            2: 75,   # Basic
            3: 82,   # Allowances
            4: 70,   # Bonus
            5: 70,   # Overtime
            6: 82,   # Deductions
            7: 72,   # Advance
            8: 68,   # Tax
            9: 90,   # Net Salary
            10: 75,  # Status
            11: 90,  # Payment Date
            12: 125  # Action (Unified TableDropdownButton)
        }
        for c, w in col_widths.items():
            if c == 1:
                self.tbl_pay.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
            else:
                self.tbl_pay.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
                self.tbl_pay.setColumnWidth(c, w)
        self.tbl_pay.horizontalHeader().setMinimumSectionSize(60)
        self.tbl_pay.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tbl_pay.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_pay)
        return page

    def generate_payroll(self):
        m = self.pay_month.currentText()
        success, msg = HRService.generate_payroll(m)
        QMessageBox.information(self, "Result", msg)
        self.load_payroll()
        self.refresh_dashboard_analytics()

    def load_payroll(self):
        m = self.pay_month.currentText()
        st_filter = self.filter_pay_status.currentText()
        if st_filter == "All Statuses":
            st_filter = "All"

        for child in self.tbl_pay.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_pay.clearContents()

        recs = HRService.get_payroll(m, status_filter=st_filter)
        
        total_payout = sum((p.net_salary or 0.0) for p in recs)
        paid_payout = sum((p.net_salary or 0.0) for p in recs if p.status == "Paid")
        pending_payout = sum((p.net_salary or 0.0) for p in recs if p.status != "Paid")
        paid_ppl = sum(1 for p in recs if p.status == "Paid")
        pending_ppl = sum(1 for p in recs if p.status != "Paid")

        self.lbl_pay_summary.setText(
            f"<b>Payroll Summary ({m}):</b> "
            f"Total: <b>Rs. {total_payout:,.0f}</b> ({len(recs)} staff)  |  "
            f"Paid: <b style='color:#10B981;'>Rs. {paid_payout:,.0f}</b> ({paid_ppl})  |  "
            f"Pending: <b style='color:#EF4444;'>Rs. {pending_payout:,.0f}</b> ({pending_ppl})"
        )

        self.tbl_pay.setRowCount(len(recs))
        for r, p in enumerate(recs):
            self.tbl_pay.setItem(r, 0, QTableWidgetItem(p.receipt_no or "-"))
            emp_name = f"{p.employee.first_name} {p.employee.last_name or ''}".strip()
            self.tbl_pay.setItem(r, 1, QTableWidgetItem(emp_name))
            
            basic = p.basic_salary or 0.0
            self.tbl_pay.setItem(r, 2, QTableWidgetItem(f"{basic:,.0f}"))

            def _create_pay_spin(val, is_paid_flag, row_idx, base_sal):
                sb = QDoubleSpinBox()
                sb.setRange(0, 10000000)
                sb.setDecimals(0)
                sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                sb.setAlignment(Qt.AlignmentFlag.AlignRight)
                sb.setValue(float(val or 0.0))
                if is_paid_flag:
                    sb.setEnabled(False)
                else:
                    sb.valueChanged.connect(lambda _: self._recalc_payroll_row(row_idx, base_sal))
                return sb

            is_paid = (p.status == "Paid")
            alw = _create_pay_spin(p.allowances, is_paid, r, basic)
            bon = _create_pay_spin(p.bonus, is_paid, r, basic)
            ot = _create_pay_spin(p.overtime, is_paid, r, basic)
            ded = _create_pay_spin(p.deductions, is_paid, r, basic)
            adv = _create_pay_spin(p.advance, is_paid, r, basic)
            tax = _create_pay_spin(p.tax, is_paid, r, basic)

            self.tbl_pay.setCellWidget(r, 3, alw); self.tbl_pay.setCellWidget(r, 4, bon)
            self.tbl_pay.setCellWidget(r, 5, ot); self.tbl_pay.setCellWidget(r, 6, ded)
            self.tbl_pay.setCellWidget(r, 7, adv); self.tbl_pay.setCellWidget(r, 8, tax)

            net_item = QTableWidgetItem(f"{p.net_salary:,.0f}")
            net_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if is_paid: net_item.setForeground(QColor("#10B981"))
            else: net_item.setForeground(QColor("#EF4444"))
            self.tbl_pay.setItem(r, 9, net_item)

            st_item = QTableWidgetItem(p.status)
            if is_paid: st_item.setForeground(QColor("#10B981"))
            else: st_item.setForeground(QColor("#F59E0B"))
            self.tbl_pay.setItem(r, 10, st_item)
            self.tbl_pay.setItem(r, 11, QTableWidgetItem(p.payment_date or "-"))

            if not is_paid:
                btn_act = TableDropdownButton("Pay", icon_name="credit-card", variant="primary", height=28)
                btn_act.add_menu_action(
                    "Pay & A4 Slip",
                    lambda checked=False, pid=p.id, rw=r: self.process_salary(pid, rw, force_thermal=False),
                    icon_name="file-text", icon_color="#2563EB"
                )
                btn_act.add_menu_action(
                    "Pay & Thermal (80mm)",
                    lambda checked=False, pid=p.id, rw=r: self.process_salary(pid, rw, force_thermal=True),
                    icon_name="printer", icon_color="#059669"
                )
                self.tbl_pay.setCellWidget(r, 12, create_table_actions_cell([btn_act]))
            else:
                btn_slip = TableDropdownButton("Slip", icon_name="printer", variant="secondary", height=28)
                btn_slip.add_menu_action(
                    "A4 Detailed Slip",
                    lambda checked=False, p_obj=p: self.reprint_salary_slip(p_obj, force_thermal=False),
                    icon_name="file-text", icon_color="#1E293B"
                )
                btn_slip.add_menu_action(
                    "Thermal Slip (80mm)",
                    lambda checked=False, p_obj=p: self.reprint_salary_slip(p_obj, force_thermal=True),
                    icon_name="printer", icon_color="#059669"
                )
                self.tbl_pay.setCellWidget(r, 12, create_table_actions_cell([btn_slip]))
            self.tbl_pay.setRowHeight(r, 48)

    def _recalc_payroll_row(self, row, basic):
        try:
            alw = self.tbl_pay.cellWidget(row, 3).value()
            bon = self.tbl_pay.cellWidget(row, 4).value()
            ot = self.tbl_pay.cellWidget(row, 5).value()
            ded = self.tbl_pay.cellWidget(row, 6).value()
            adv = self.tbl_pay.cellWidget(row, 7).value()
            tax = self.tbl_pay.cellWidget(row, 8).value()
            gross = basic + alw + bon + ot
            net = max(0.0, gross - (ded + adv + tax))
            item = self.tbl_pay.item(row, 9)
            if item:
                item.setText(f"{net:,.0f}")
        except Exception:
            pass

    def reprint_salary_slip(self, rec, force_thermal=False):
        doc_type = "Thermal Salary Slip" if force_thermal else "Salary Slip"
        out_dir = os.path.join(os.path.dirname(DB_DIR), "generated_docs", "Salary_Slips")
        os.makedirs(out_dir, exist_ok=True)
        file_name = f"Thermal_{rec.receipt_no}.pdf" if force_thermal else f"{rec.receipt_no}.pdf"
        out_path = os.path.join(out_dir, file_name)

        with show_print_loading(self, title=f"Loading {'Thermal' if force_thermal else 'A4'} Salary Slip...", subtitle=f"Slip #{rec.receipt_no}"):
            if not os.path.exists(out_path):
                data_dict = {
                    "employee.name": f"{rec.employee.first_name} {rec.employee.last_name or ''}".strip() if rec.employee else "Employee",
                    "employee.emp_id": rec.employee.emp_id if rec.employee else "",
                    "employee.designation": rec.employee.designation or "-" if rec.employee else "-",
                    "employee.department": rec.employee.department or "-" if rec.employee else "-",
                    "payroll.receipt_no": rec.receipt_no, "payroll.month": rec.pay_month,
                    "payroll.basic": f"{rec.basic_salary:,.2f}", "payroll.allowances": f"{rec.allowances:,.2f}",
                    "payroll.bonus": f"{rec.bonus:,.2f}", "payroll.overtime": f"{rec.overtime:,.2f}",
                    "payroll.gross": f"{rec.gross_salary:,.2f}", "payroll.deductions": f"{rec.deductions:,.2f}",
                    "payroll.advance": f"{rec.advance:,.2f}", "payroll.tax": f"{rec.tax:,.2f}",
                    "payroll.net_salary": f"{rec.net_salary:,.2f}", "payroll.payment_date": rec.payment_date or datetime.now().strftime("%Y-%m-%d"),
                    "payroll.method": rec.payment_method or "Bank Transfer",
                    "employee_id": rec.employee_id, "employee.id": rec.employee_id
                }
                PDFGenerationService.generate_document(doc_type, data_dict, out_path)

            if os.path.exists(out_path):
                try:
                    os.startfile(out_path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not open Salary Slip PDF: {e}")
            else:
                QMessageBox.information(self, "Info", f"Salary Slip file not found at:\n{out_path}")

    def process_salary(self, pid, row, force_thermal=False):
        alw = self.tbl_pay.cellWidget(row, 3).value(); bon = self.tbl_pay.cellWidget(row, 4).value()
        ot = self.tbl_pay.cellWidget(row, 5).value(); ded = self.tbl_pay.cellWidget(row, 6).value()
        adv = self.tbl_pay.cellWidget(row, 7).value(); tax = self.tbl_pay.cellWidget(row, 8).value()

        success, msg, data = HRService.process_payroll_payment(pid, alw, bon, ot, ded, adv, tax, "Bank Transfer")
        if success:
            doc_type = "Thermal Salary Slip" if force_thermal else "Salary Slip"
            out_dir = os.path.join(os.path.dirname(DB_DIR), "generated_docs", "Salary_Slips")
            os.makedirs(out_dir, exist_ok=True)
            file_name = f"Thermal_{data['payroll.receipt_no']}.pdf" if force_thermal else f"{data['payroll.receipt_no']}.pdf"
            out_path = os.path.join(out_dir, file_name)
            
            with show_print_loading(self, title="Printing Salary Slip...", subtitle=f"Slip #{data['payroll.receipt_no']}"):
                pdf_ok, p_msg = PDFGenerationService.generate_document(doc_type, data, out_path)
                if pdf_ok:
                    try:
                        emp_db_id = data.get("employee_id") or data.get("employee.id")
                        DocumentService.log_document(None, doc_type, data['payroll.receipt_no'], out_path, employee_id=emp_db_id)
                    except Exception:
                        pass
                    try: os.startfile(out_path)
                    except Exception: pass
            
            info = "Salary payment recorded successfully."
            if pdf_ok:
                info += f"\n\nSalary Slip ({'80mm Thermal' if force_thermal else 'A4 Detailed'}) generated & saved:\n{out_path}"
            else:
                info += f"\n\n(PDF Generator Note: {p_msg})"
            QMessageBox.information(self, "Payment Complete", info)
            self.load_payroll()
            self.refresh_dashboard_analytics()

    def export_payroll(self):
        m = self.pay_month.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "Export Payroll Expense Register", f"Payroll_Expense_{m}.xlsx", "Excel Files (*.xlsx)")
        if path:
            HRService.export_payroll_to_excel(m, path)
            QMessageBox.information(self, "Exported", f"Payroll register successfully exported:\n{path}")

    # ==========================================
    # NAVIGATION & GENERAL REFRESH
    # ==========================================
    def refresh_current_view(self):
        self.refresh_dashboard_analytics()
        self.refresh_directory()
        self.refresh_assignments()
        self.load_attendance()
        self.load_payroll()
        self.refresh_leave()

    def on_tab_changed(self, idx):
        if idx == 0:   self.refresh_dashboard_analytics()
        elif idx == 1: self.refresh_directory()
        elif idx == 2: self.refresh_assignments()
        elif idx == 3: self.load_attendance()
        elif idx == 4: self.load_payroll()
        elif idx == 5: self.refresh_leave()

    # ==========================================
    # LEAVE MANAGEMENT TAB
    # ==========================================
    def create_leave_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(18)

        # Top Stat Cards
        cards_lay = QHBoxLayout()
        cards_lay.setSpacing(15)
        self.card_leave_pending = self._stat_card("Pending Applications", "0 Applications", "#F59E0B")
        self.card_leave_approved = self._stat_card("Approved (This Year)", "0 Days", "#10B981")
        self.card_leave_today = self._stat_card("Staff On Leave Today", "0 Staff", "#3B82F6")
        cards_lay.addWidget(self.card_leave_pending)
        cards_lay.addWidget(self.card_leave_approved)
        cards_lay.addWidget(self.card_leave_today)
        lay.addLayout(cards_lay)

        # Filter and Action Bar
        bar = QHBoxLayout()
        lbl = QLabel("Staff Leave Applications")
        lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        
        self.combo_leave_filter = QComboBox()
        self.combo_leave_filter.addItems(["All", "Pending", "Approved", "Rejected"])
        self.combo_leave_filter.currentIndexChanged.connect(self.refresh_leave)
        
        btn_apply = ModernButton("Apply Leave", icon_name="plus", variant="primary")
        btn_apply.clicked.connect(self.apply_leave_dialog)
        
        btn_refresh_leave = ModernButton("Refresh", icon_name="refresh-cw", variant="secondary")
        btn_refresh_leave.clicked.connect(self.refresh_leave)

        bar.addWidget(lbl)
        bar.addStretch()
        bar.addWidget(QLabel("<b>Filter Status:</b>"))
        bar.addWidget(self.combo_leave_filter)
        bar.addWidget(btn_refresh_leave)
        bar.addWidget(btn_apply)
        lay.addLayout(bar)

        # Table
        self.tbl_leave = self._table()
        self.tbl_leave.setColumnCount(9)
        self.tbl_leave.setHorizontalHeaderLabels([
            "ID", "Staff Member", "Leave Type", "From Date", "To Date", "Days", "Reason", "Status", "Actions"
        ])
        self.tbl_leave.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.tbl_leave.setColumnWidth(8, 200)
        self.tbl_leave.verticalHeader().setDefaultSectionSize(48)
        self.tbl_leave.setMinimumHeight(280)
        lay.addWidget(self.tbl_leave)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(w)
        return scroll

    def refresh_leave(self):
        if not hasattr(self, 'tbl_leave'): return
        status = self.combo_leave_filter.currentText() if hasattr(self, 'combo_leave_filter') else "All"
        apps   = LeaveService.get_all_applications(status)
        all_apps = LeaveService.get_all_applications("All")

        pending_cnt = sum(1 for a in all_apps if a.status == "Pending")
        approved_days = sum(a.total_days for a in all_apps if a.status == "Approved")
        t_d = date.today()
        today_on_leave = sum(1 for a in all_apps if a.status == "Approved" and a.from_date <= t_d <= a.to_date)

        if hasattr(self, 'card_leave_pending'):
            self.card_leave_pending.value_label.setText(f"{pending_cnt} Pending")
        if hasattr(self, 'card_leave_approved'):
            self.card_leave_approved.value_label.setText(f"{approved_days} Days")
        if hasattr(self, 'card_leave_today'):
            self.card_leave_today.value_label.setText(f"{today_on_leave} On Leave")

        for child in self.tbl_leave.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_leave.clearContents()
        self.tbl_leave.clearSpans()

        if not apps:
            self.tbl_leave.setRowCount(1)
            self.tbl_leave.setRowHeight(0, 48)
            item = QTableWidgetItem("No leave applications found matching filter.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#6B7280"))
            font = QFont("Segoe UI", 10)
            font.setItalic(True)
            item.setFont(font)
            self.tbl_leave.setItem(0, 0, item)
            self.tbl_leave.setSpan(0, 0, 1, 9)
        else:
            self.tbl_leave.setRowCount(len(apps))
            status_colors = {"Approved": "#16A34A", "Rejected": "#DC2626", "Pending": "#D97706"}
            for r, app in enumerate(apps):
                id_item = QTableWidgetItem(str(app.id))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_leave.setItem(r, 0, id_item)

                name_item = QTableWidgetItem(app.employee_name)
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tbl_leave.setItem(r, 1, name_item)

                type_item = QTableWidgetItem(app.leave_type_name)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tbl_leave.setItem(r, 2, type_item)

                f_item = QTableWidgetItem(str(app.from_date))
                f_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_leave.setItem(r, 3, f_item)

                t_item = QTableWidgetItem(str(app.to_date))
                t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_leave.setItem(r, 4, t_item)

                d_item = QTableWidgetItem(f"{app.total_days} d")
                d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_leave.setItem(r, 5, d_item)

                r_item = QTableWidgetItem(app.reason or "-")
                r_item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.tbl_leave.setItem(r, 6, r_item)

                st_item = QTableWidgetItem(app.status)
                st_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                st_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                st_item.setForeground(QColor(status_colors.get(app.status, "#6B7280")))
                self.tbl_leave.setItem(r, 7, st_item)

                buttons = []
                if app.status == "Pending":
                    b_ok = TableTextButton("Approve", icon_name="check", variant="success")
                    b_ok.clicked.connect(lambda _, aid=app.id: self._approve_leave(aid))
                    buttons.append(b_ok)

                    b_rej = TableTextButton("Reject", icon_name="x", variant="danger")
                    b_rej.clicked.connect(lambda _, aid=app.id: self._reject_leave(aid))
                    buttons.append(b_rej)

                b_del = TableActionButton("trash-2", variant="delete", tooltip="Delete Application", size=28)
                b_del.clicked.connect(lambda _, aid=app.id: self._delete_leave(aid))
                buttons.append(b_del)

                self.tbl_leave.setCellWidget(r, 8, create_table_actions_cell(buttons))
                self.tbl_leave.setRowHeight(r, 48)

    def apply_leave_dialog(self):
        employees = [e for e in HRService.get_all_employees() if e.status in ["Active", "On Leave"]]
        if not employees:
            QMessageBox.warning(self, "No Staff Found", "No active or on-leave staff members found in the directory.")
            return
        leave_types = LeaveService.get_leave_types()
        if not leave_types:
            QMessageBox.warning(self, "No Leave Types", "No leave types configured.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Apply Staff Leave")
        dlg.setMinimumWidth(500)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)

        combo_emp = QComboBox()
        for emp in employees:
            name = f"{emp.first_name} {emp.last_name or ''}".strip()
            combo_emp.addItem(f"{name} ({emp.emp_id}) - {emp.status}", (emp.id, name))

        combo_lt = QComboBox()
        for lt in leave_types:
            combo_lt.addItem(f"{lt.name} (Quota: {lt.max_days_per_year} days/yr)", lt.id)

        lbl_balance = QLabel("")
        lbl_balance.setStyleSheet("color: #2563EB; font-weight: bold;")

        today = QDate.currentDate()
        de_from = QDateEdit(today)
        de_from.setCalendarPopup(True)
        de_to = QDateEdit(today)
        de_to.setCalendarPopup(True)

        lbl_duration = QLabel("Duration: 1 day(s)")
        lbl_duration.setStyleSheet("font-weight: bold; color: #059669;")

        def update_balance():
            emp_data = combo_emp.currentData()
            if not emp_data:
                lbl_balance.setText("")
                lbl_duration.setText("")
                return
            emp_id, _ = emp_data
            balances = LeaveService.get_employee_balance(emp_id)
            selected_lt_id = combo_lt.currentData()
            selected_lt = next((lt for lt in leave_types if lt.id == selected_lt_id), None)
            
            f_q = de_from.date()
            t_q = de_to.date()
            days = f_q.daysTo(t_q) + 1 if t_q >= f_q else 0
            
            if selected_lt and selected_lt.name in balances:
                b = balances[selected_lt.name]
                lbl_balance.setText(f"Remaining {selected_lt.name} balance: {b['remaining']} of {b['max']} days (Used: {b['used']} days)")
                if days > 0:
                    if days > b['remaining']:
                        excess_days = days - b['remaining']
                        lbl_duration.setText(f"Selected: {days} day(s) (Exceeds remaining quota by {excess_days} d - Admin sanctioned)")
                        lbl_duration.setStyleSheet("font-weight: bold; color: #DC2626;")
                    else:
                        lbl_duration.setText(f"Selected: {days} day(s) (Within annual quota)")
                        lbl_duration.setStyleSheet("font-weight: bold; color: #059669;")
                else:
                    lbl_duration.setText("Invalid date range (To Date is before From Date)")
                    lbl_duration.setStyleSheet("font-weight: bold; color: #DC2626;")
            else:
                lbl_balance.setText("")

        combo_emp.currentIndexChanged.connect(update_balance)
        combo_lt.currentIndexChanged.connect(update_balance)
        de_from.dateChanged.connect(update_balance)
        de_to.dateChanged.connect(update_balance)
        update_balance()

        inp_reason = QTextEdit()
        inp_reason.setMaximumHeight(80)
        inp_reason.setPlaceholderText("Enter reason for leave...")

        chk_auto_approve = QCheckBox("Approve immediately & update attendance register")
        chk_auto_approve.setChecked(True)
        chk_auto_approve.setStyleSheet("font-weight: bold; color: #1E293B;")

        form.addRow("<b>Employee:</b>", combo_emp)
        form.addRow("<b>Leave Type:</b>", combo_lt)
        form.addRow("<b>Leave Balance:</b>", lbl_balance)
        form.addRow("<b>From Date:</b>", de_from)
        form.addRow("<b>To Date:</b>", de_to)
        form.addRow("<b>Duration:</b>", lbl_duration)
        form.addRow("<b>Reason:</b>", inp_reason)
        form.addRow("<b>Approval:</b>", chk_auto_approve)
        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            emp_data = combo_emp.currentData()
            if not emp_data:
                return
            emp_id, emp_name = emp_data
            lt_id = combo_lt.currentData()
            f_qdate = de_from.date()
            t_qdate = de_to.date()
            if t_qdate < f_qdate:
                QMessageBox.warning(self, "Invalid Dates", "To Date cannot be earlier than From Date.")
                return
            f_date = date(f_qdate.year(), f_qdate.month(), f_qdate.day())
            t_date = date(t_qdate.year(), t_qdate.month(), t_qdate.day())
            reason = inp_reason.toPlainText().strip()
            auto_app = chk_auto_approve.isChecked()

            ok, msg = LeaveService.apply_leave(emp_id, emp_name, lt_id, f_date, t_date, reason, allow_excess=False, auto_approve=auto_app)
            if not ok and "EXCEEDS_QUOTA:" in msg:
                prompt_text = (
                    f"{msg.replace('EXCEEDS_QUOTA:', '').strip()}\n\n"
                    "Do you want to grant and approve this as administrative sanctioned excess leave?"
                )
                reply = QMessageBox.question(
                    self, "Leave Quota Exceeded", prompt_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    ok, msg = LeaveService.apply_leave(emp_id, emp_name, lt_id, f_date, t_date, reason, allow_excess=True, auto_approve=auto_app)

            if ok:
                QMessageBox.information(self, "Success", msg)
                self.refresh_leave()
                self.refresh_directory()
                if hasattr(self, 'load_attendance'):
                    self.load_attendance()
                self.refresh_dashboard_analytics()
            else:
                QMessageBox.critical(self, "Error", msg)

    def _approve_leave(self, app_id):
        ok, msg = LeaveService.approve_leave(app_id)
        if ok:
            QMessageBox.information(self, "Approved", msg)
            self.refresh_leave()
            self.refresh_directory()
            if hasattr(self, 'load_attendance'):
                self.load_attendance()
            self.refresh_dashboard_analytics()
        else:
            QMessageBox.critical(self, "Error", msg)

    def _reject_leave(self, app_id):
        ok, msg = LeaveService.reject_leave(app_id)
        if ok:
            QMessageBox.information(self, "Rejected", msg)
            self.refresh_leave()
            self.refresh_directory()
            if hasattr(self, 'load_attendance'):
                self.load_attendance()
            self.refresh_dashboard_analytics()
        else:
            QMessageBox.critical(self, "Error", msg)

    def _delete_leave(self, app_id):
        if QMessageBox.question(self, "Confirm", "Delete this leave application?") == QMessageBox.StandardButton.Yes:
            ok, msg = LeaveService.delete_leave(app_id)
            if ok:
                QMessageBox.information(self, "Deleted", msg)
                self.refresh_leave()
                self.refresh_directory()
                if hasattr(self, 'load_attendance'):
                    self.load_attendance()
                self.refresh_dashboard_analytics()
            else:
                QMessageBox.critical(self, "Error", msg)
