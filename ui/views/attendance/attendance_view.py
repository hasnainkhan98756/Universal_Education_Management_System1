import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QFormLayout, QLineEdit, QComboBox, QTabWidget, 
                               QMessageBox, QFrame, QAbstractItemView, QGridLayout, QDateEdit, QSpinBox, QFileDialog)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from core.academic_service import AcademicService
from core.attendance_service import AttendanceService
from core.state_manager import app_state
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, MetricCard, StatusBadge,
    ModernButton, SearchInput, style_modern_table, style_modern_tabs
)
from datetime import datetime

class AttendanceView(QWidget):
    """
    Phase 12: Complete Student Attendance Management System.
    Added Monthly/Yearly Reporting with Excel Export!
    """
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)
        
        header = PageHeader(
            title="Attendance Management",
            subtitle="Record daily student attendance, track absence rates, and export monthly audit registers",
            icon_name="calendar-check",
        )
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_overview_tab(), "Daily Overview")
        self.tabs.setTabIcon(0, get_icon("bar-chart-2", color="#475569"))
        self.tabs.addTab(self.create_take_attendance_tab(), "Take Attendance")
        self.tabs.setTabIcon(1, get_icon("calendar-check", color="#475569"))
        self.tabs.addTab(self.create_report_tab(), "Monthly / Yearly Reports")
        self.tabs.setTabIcon(2, get_icon("file-spreadsheet", color="#475569"))
        
        main_layout.addWidget(self.tabs)
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        app_state.subscribe_settings_change(self.load_dropdowns)
        app_state.subscribe_data_changed(self.refresh_attendance)
        self.load_dropdowns()
        self.refresh_analytics()
        self.check_date_holiday()

    # --- UI Helpers ---
    def _lbl(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        return lbl

    def _combo(self, items=None):
        cb = QComboBox()
        if items: cb.addItems(items)
        cb.setMinimumHeight(32)
        return cb

    def _date(self):
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setMinimumHeight(32)
        return de

    # ==========================================
    # TAB 1: ATTENDANCE OVERVIEW
    # ==========================================
    def create_overview_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        
        self.lbl_date_header = QLabel("Attendance Overview")
        self.lbl_date_header.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 6px;")
        layout.addWidget(self.lbl_date_header)
        
        grid = QGridLayout()
        grid.setSpacing(14)
        
        self.card_present = self._stat_card("Present", "0", "#10B981")
        self.card_absent = self._stat_card("Absent", "0", "#EF4444")
        self.card_leave = self._stat_card("On Leave", "0", "#F59E0B")
        self.card_late = self._stat_card("Late", "0", "#8B5CF6")
        
        grid.addWidget(self.card_present, 0, 0)
        grid.addWidget(self.card_absent, 0, 1)
        grid.addWidget(self.card_leave, 1, 0)
        grid.addWidget(self.card_late, 1, 1)
        
        layout.addLayout(grid)
        layout.addStretch()
        return page

    def _stat_card(self, title, init_val, color_hex):
        icon_map = {
            "Present": "check-circle-2",
            "Absent": "x-circle",
            "On Leave": "calendar-days",
            "Late": "clock",
        }
        icon_name = icon_map.get(title, "info")
        return MetricCard(title=title, value=init_val, icon_name=icon_name, accent_color=color_hex)

    # ==========================================
    # TAB 2: TAKE ATTENDANCE
    # ==========================================
    def create_take_attendance_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        
        control_lay = QHBoxLayout()
        self.date_picker = self._date()
        self.date_picker.dateChanged.connect(self.refresh_analytics)
        self.date_picker.dateChanged.connect(self.check_date_holiday)
        self.combo_class = self._combo()
        self.combo_class.currentIndexChanged.connect(self.update_sections)
        self.combo_section = self._combo()

        btn_load = ModernButton("Load Students", icon_name="refresh-cw", variant="secondary")
        btn_load.clicked.connect(self.load_attendance_sheet)

        control_lay.addWidget(self._lbl("Date:"))
        control_lay.addWidget(self.date_picker)
        control_lay.addWidget(self._lbl("Class:"))
        control_lay.addWidget(self.combo_class)
        control_lay.addWidget(self._lbl("Section:"))
        control_lay.addWidget(self.combo_section)
        control_lay.addWidget(btn_load)
        control_lay.addStretch()
        layout.addLayout(control_lay)

        # Prominent Academic Calendar Holiday / Vacation Alert Banner
        self.lbl_holiday_banner = QLabel()
        self.lbl_holiday_banner.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1.5px solid #F59E0B; "
            "border-radius: 8px; padding: 10px 14px; font-size: 13px; font-weight: bold;"
        )
        self.lbl_holiday_banner.setVisible(False)
        layout.addWidget(self.lbl_holiday_banner)

        self.lbl_sheet_status = QLabel("Please load a class to take attendance.")
        layout.addWidget(self.lbl_sheet_status)

        bulk_lay = QHBoxLayout()
        btn_all_p = ModernButton("Mark All Present", icon_name="check", variant="success")
        btn_all_p.clicked.connect(lambda: self.mark_all("Present"))

        btn_all_a = ModernButton("Mark All Absent", icon_name="x", variant="danger")
        btn_all_a.clicked.connect(lambda: self.mark_all("Absent"))

        btn_all_h = ModernButton("Mark All as Holiday", icon_name="calendar-days", variant="warning")
        btn_all_h.clicked.connect(lambda: self.mark_all("Holiday"))

        bulk_lay.addWidget(btn_all_p)
        bulk_lay.addWidget(btn_all_a)
        bulk_lay.addWidget(btn_all_h)
        bulk_lay.addStretch()
        layout.addLayout(bulk_lay)

        self.tbl_sheet = QTableWidget()
        self.tbl_sheet.setColumnCount(5)
        self.tbl_sheet.setHorizontalHeaderLabels(["Student ID", "Name", "Father's Name", "Status", "Remarks"])
        self.tbl_sheet.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_sheet.verticalHeader().setDefaultSectionSize(36)
        style_modern_table(self.tbl_sheet)
        layout.addWidget(self.tbl_sheet)

        btn_save = ModernButton("Save Attendance", icon_name="save", variant="primary")
        btn_save.clicked.connect(self.save_attendance)
        layout.addWidget(btn_save)
        
        return page

    # ==========================================
    # TAB 3: MONTHLY/YEARLY REPORTS
    # ==========================================
    def create_report_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)

        # Filters
        filter_lay = QHBoxLayout()
        self.rep_combo_class = self._combo()
        self.rep_combo_class.currentIndexChanged.connect(self.update_rep_sections)
        self.rep_combo_section = self._combo()

        self.rep_spin_year = QSpinBox()
        self.rep_spin_year.setRange(2000, 2100)
        self.rep_spin_year.setValue(datetime.now().year)
        self.rep_spin_year.setMinimumHeight(32)

        self.rep_combo_month = self._combo(["00 - Entire Year", "01 - January", "02 - February", "03 - March", "04 - April", "05 - May", "06 - June", "07 - July", "08 - August", "09 - September", "10 - October", "11 - November", "12 - December"])

        btn_gen = ModernButton("Generate Report", icon_name="bar-chart-2", variant="primary")
        btn_gen.clicked.connect(self.generate_report)

        btn_export = ModernButton("Export to Excel", icon_name="download", variant="secondary")
        btn_export.clicked.connect(self.export_report)

        filter_lay.addWidget(self._lbl("Class:"))
        filter_lay.addWidget(self.rep_combo_class)
        filter_lay.addWidget(self._lbl("Section:"))
        filter_lay.addWidget(self.rep_combo_section)
        filter_lay.addWidget(self._lbl("Year:"))
        filter_lay.addWidget(self.rep_spin_year)
        filter_lay.addWidget(self._lbl("Month:"))
        filter_lay.addWidget(self.rep_combo_month)
        filter_lay.addWidget(btn_gen)
        filter_lay.addWidget(btn_export)
        filter_lay.addStretch()
        
        layout.addLayout(filter_lay)

        # Table
        self.tbl_report = QTableWidget()
        self.tbl_report.setColumnCount(8)
        self.tbl_report.setHorizontalHeaderLabels(["Student ID", "Name", "Total Days", "Present", "Absent", "Leave", "Late", "Percentage"])
        self.tbl_report.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_report.verticalHeader().setDefaultSectionSize(36)
        style_modern_table(self.tbl_report)
        layout.addWidget(self.tbl_report)

        return page

    # ==========================================
    # LOGIC
    # ==========================================
    def refresh_attendance(self):
        """Refreshes analytics, re-evaluates active attendance sheets, and synchronizes live."""
        self.refresh_analytics()
        self.check_date_holiday()
        if hasattr(self, 'combo_class') and hasattr(self, 'combo_section'):
            cid = self.combo_class.currentData()
            sid = self.combo_section.currentData()
            if cid and sid and hasattr(self, 'tbl_sheet') and self.tbl_sheet.rowCount() > 0:
                self.load_attendance_sheet()
        if hasattr(self, 'tabs') and self.tabs.currentIndex() == 2:
            if hasattr(self, 'tbl_report') and self.tbl_report.rowCount() > 0:
                self.generate_report()

    def refresh_data(self):
        self.refresh_attendance()

    def refresh_all(self):
        self.refresh_attendance()

    def showEvent(self, event):
        """Forces immediate live sync upon activating the Attendance tab."""
        self.refresh_attendance()
        super().showEvent(event)

    def on_tab_changed(self, index):
        if index == 0:
            self.refresh_analytics()
        elif index == 1:
            cid = self.combo_class.currentData()
            sid = self.combo_section.currentData()
            if cid and sid and self.tbl_sheet.rowCount() > 0:
                self.load_attendance_sheet()

    def load_dropdowns(self):
        active_session = app_state.get_setting("session", "Default")
        self.classes = AcademicService.get_classes(session_filter=active_session)
        
        self.combo_class.blockSignals(True)
        self.rep_combo_class.blockSignals(True)
        self.combo_class.clear()
        self.rep_combo_class.clear()
        
        for c in self.classes:
            self.combo_class.addItem(c.name, c.id)
            self.rep_combo_class.addItem(c.name, c.id)
            
        self.combo_class.blockSignals(False)
        self.rep_combo_class.blockSignals(False)
        
        self.update_sections()
        self.update_rep_sections()

    def update_sections(self):
        cid = self.combo_class.currentData()
        self.combo_section.clear()
        if cid:
            secs = AcademicService.get_sections(cid)
            for s in secs: self.combo_section.addItem(s.name, s.id)

    def update_rep_sections(self):
        cid = self.rep_combo_class.currentData()
        self.rep_combo_section.clear()
        if cid:
            secs = AcademicService.get_sections(cid)
            for s in secs: self.rep_combo_section.addItem(s.name, s.id)

    def refresh_analytics(self):
        if not hasattr(self, 'date_picker'): return
        d_str = self.date_picker.date().toString("yyyy-MM-dd")
        stats = AttendanceService.get_dashboard_analytics(d_str)
        
        self.card_present.value_label.setText(str(stats["present"]))
        self.card_absent.value_label.setText(str(stats["absent"]))
        self.card_leave.value_label.setText(str(stats["leave"]))
        self.card_late.value_label.setText(str(stats["late"]))
        
        formatted_date = self.date_picker.date().toString("dd MMMM yyyy")
        self.lbl_date_header.setText(f"Attendance Overview ({formatted_date})")

    # --- TAKE ATTENDANCE LOGIC ---
    def load_attendance_sheet(self):
        cid = self.combo_class.currentData()
        sid = self.combo_section.currentData()
        d_str = self.date_picker.date().toString("yyyy-MM-dd")
        
        if not cid or not sid:
            QMessageBox.warning(self, "Validation", "Please select a Class and Section first.")
            return
            
        data = AttendanceService.get_attendance_sheet(cid, sid, d_str)
        self.tbl_sheet.setRowCount(len(data))
        
        existing_count = sum(1 for d in data if d["is_existing"])
        if existing_count > 0:
            self.lbl_sheet_status.setText(f"Loaded {len(data)} students. Attendance is already saved for this date. Saving again will UPDATE the records.")
            self.lbl_sheet_status.setStyleSheet("color: #F59E0B; font-weight: bold;")
        else:
            self.lbl_sheet_status.setText(f"Loaded {len(data)} students. Ready to mark new attendance.")
            self.lbl_sheet_status.setStyleSheet("color: #10B981; font-weight: bold;")
        
        for row, stu in enumerate(data):
            item_id = QTableWidgetItem(stu["student_system_id"])
            item_id.setData(Qt.ItemDataRole.UserRole, stu["student_id"])
            
            self.tbl_sheet.setItem(row, 0, item_id)
            self.tbl_sheet.setItem(row, 1, QTableWidgetItem(stu["name"]))
            self.tbl_sheet.setItem(row, 2, QTableWidgetItem(stu["father_name"]))
            
            cb_status = self._combo(["Present", "Absent", "Leave", "Late", "Holiday"])
            # If today is a holiday and not previously saved, default to Holiday
            holiday_info = AttendanceService.get_holiday_or_event(d_str)
            if holiday_info and not stu["is_existing"]:
                cb_status.setCurrentText("Holiday")
            else:
                cb_status.setCurrentText(stu["status"])

            cb_status.setFixedHeight(32)
            cb_status.setStyleSheet("QComboBox { min-height: 30px; max-height: 32px; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }")
            self.tbl_sheet.setCellWidget(row, 3, cb_status)

            inp_rem = QLineEdit(stu["remarks"])
            if holiday_info and not stu["remarks"] and not stu["is_existing"]:
                inp_rem.setText(holiday_info["title"])
            inp_rem.setFixedHeight(32)
            inp_rem.setStyleSheet("QLineEdit { border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 2px 8px; background: #FFFFFF; color: #111827; }")
            self.tbl_sheet.setCellWidget(row, 4, inp_rem)
            self.tbl_sheet.setRowHeight(row, 44)

    def check_date_holiday(self):
        if not hasattr(self, 'date_picker') or not hasattr(self, 'lbl_holiday_banner'):
            return
        d_str = self.date_picker.date().toString("yyyy-MM-dd")
        holiday = AttendanceService.get_holiday_or_event(d_str)
        if holiday:
            date_range = holiday['start_date'] if holiday['start_date'] == holiday['end_date'] else f"{holiday['start_date']} to {holiday['end_date']}"
            self.lbl_holiday_banner.setText(
                f"<b>{holiday['event_type']} Notice:</b> {holiday['title']} ({date_range}) — "
                f"Official Day Off according to the Academic Calendar. Attendance is defaulted to Holiday, but you can edit and mark Present/Absent if school is open today."
            )
            self.lbl_holiday_banner.setVisible(True)
        else:
            self.lbl_holiday_banner.setVisible(False)

    def mark_all(self, status_val):
        for row in range(self.tbl_sheet.rowCount()):
            cb = self.tbl_sheet.cellWidget(row, 3)
            if cb: cb.setCurrentText(status_val)

    def save_attendance(self):
        cid = self.combo_class.currentData()
        sid = self.combo_section.currentData()
        d_str = self.date_picker.date().toString("yyyy-MM-dd")
        
        rows = self.tbl_sheet.rowCount()
        if rows == 0:
            QMessageBox.warning(self, "Warning", "Please load students before saving.")
            return
            
        attendance_data = []
        for r in range(rows):
            stu_db_id = self.tbl_sheet.item(r, 0).data(Qt.ItemDataRole.UserRole)
            status = self.tbl_sheet.cellWidget(r, 3).currentText()
            remarks = self.tbl_sheet.cellWidget(r, 4).text()
            
            attendance_data.append({
                "student_id": stu_db_id,
                "status": status,
                "remarks": remarks
            })
            
        try:
            success, msg = AttendanceService.save_attendance(cid, sid, d_str, attendance_data)
            if success:
                QMessageBox.information(self, "Success", msg)
                self.load_attendance_sheet()
                self.refresh_analytics()
            else:
                QMessageBox.critical(self, "Error", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save attendance: {str(e)}")

    # --- REPORT LOGIC ---
    def generate_report(self):
        cid = self.rep_combo_class.currentData()
        sid = self.rep_combo_section.currentData()
        year = self.rep_spin_year.value()
        month_idx = self.rep_combo_month.currentIndex() # 0 = All Year, 1 = Jan, 2 = Feb, etc.
        
        if not cid or not sid:
            QMessageBox.warning(self, "Validation", "Please select a Class and Section.")
            return
            
        data = AttendanceService.get_class_attendance_report(cid, sid, year, month_idx)
        
        self.tbl_report.setRowCount(len(data))
        for r, stu in enumerate(data):
            self.tbl_report.setItem(r, 0, QTableWidgetItem(stu["id"]))
            self.tbl_report.setItem(r, 1, QTableWidgetItem(stu["name"]))
            self.tbl_report.setItem(r, 2, QTableWidgetItem(str(stu["total"])))
            
            p_item = QTableWidgetItem(str(stu["present"])); p_item.setForeground(QColor("#10B981"))
            a_item = QTableWidgetItem(str(stu["absent"])); a_item.setForeground(QColor("#EF4444"))
            l_item = QTableWidgetItem(str(stu["leave"])); l_item.setForeground(QColor("#F59E0B"))
            lt_item = QTableWidgetItem(str(stu["late"])); lt_item.setForeground(QColor("#3B82F6"))
            
            self.tbl_report.setItem(r, 3, p_item)
            self.tbl_report.setItem(r, 4, a_item)
            self.tbl_report.setItem(r, 5, l_item)
            self.tbl_report.setItem(r, 6, lt_item)
            
            # Color Code Percentage
            pct = stu["percentage"]
            pct_item = QTableWidgetItem(f"{pct}%")
            pct_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if pct >= 75: pct_item.setForeground(QColor("#10B981"))
            elif pct >= 50: pct_item.setForeground(QColor("#F59E0B"))
            else: pct_item.setForeground(QColor("#EF4444"))
            self.tbl_report.setItem(r, 7, pct_item)
            self.tbl_report.setRowHeight(r, 40)

    def export_report(self):
        if self.tbl_report.rowCount() == 0:
            QMessageBox.warning(self, "Empty Data", "Please generate a report first before exporting.")
            return
            
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill
        except ImportError:
            QMessageBox.critical(self, "Module Missing", "Please run: pip install openpyxl")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Attendance_Report.xlsx", "Excel Files (*.xlsx)")
        if not path: return
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Attendance Report"
        
        headers = ["Student ID", "Name", "Total Tracked Days", "Present", "Absent", "Leave", "Late", "Percentage"]
        ws.append(headers)
        
        # Style Headers
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
            
        # Write Data
        for r in range(self.tbl_report.rowCount()):
            row_data = []
            for c in range(8):
                row_data.append(self.tbl_report.item(r, c).text())
            ws.append(row_data)
            
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 15
        
        wb.save(path)
        QMessageBox.information(self, "Export Successful", f"Attendance Report safely saved to Excel:\n{path}")