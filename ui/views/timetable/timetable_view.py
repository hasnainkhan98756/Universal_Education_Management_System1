import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QTabWidget, QMessageBox, QFrame, QDialog, 
                               QFormLayout, QLineEdit, QDateEdit, QAbstractItemView, QFileDialog, QSpinBox, QGridLayout)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from core.timetable_service import TimetableService
from core.academic_service import AcademicService
from core.hr_service import HRService
from core.state_manager import app_state
from core.icon_manager import IconManager
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, ModernButton, TableActionButton, TableTextButton,
    create_table_actions_cell, StatusBadge,
    style_modern_table, style_modern_tabs
)

class QuickWorkloadDialog(QDialog):
    def __init__(self, class_id, section_id, parent=None):
        super().__init__(parent)
        self.class_id = class_id; self.section_id = section_id
        self.setWindowTitle("Quick Assign Teacher Workload")
        self.setMinimumWidth(450)
        
        lay = QFormLayout(self)
        self.cb_teacher = QComboBox()
        self.cb_sub = QComboBox()
        self.spin_periods = QSpinBox()
        self.spin_periods.setRange(1, 40)
        self.spin_periods.setValue(5)
        
        for t in HRService.get_employees(status_filter="Active", type_filter="Teacher"):
            self.cb_teacher.addItem(f"{t.first_name} {t.last_name or ''}".strip(), t.id)
            
        subs, _ = AcademicService.get_class_subject_assignment(class_id)
        if not subs:
            lay.addRow(QLabel("No Subjects are assigned to this Class yet!"))
        else:
            for sub in subs: self.cb_sub.addItem(sub.name, sub.id)
            
        lay.addRow("Select Teacher:", self.cb_teacher)
        lay.addRow("Select Subject:", self.cb_sub)
        lay.addRow("Periods per Week Target:", self.spin_periods)
        
        btn_save = ModernButton("Assign Workload", icon_name="save", variant="primary")
        btn_save.clicked.connect(self.save_workload)
        if not subs: btn_save.setEnabled(False)
        lay.addWidget(btn_save)

    def save_workload(self):
        tid = self.cb_teacher.currentData()
        subid = self.cb_sub.currentData()
        if not tid or not subid: return
        success, msg = HRService.assign_teacher(tid, self.class_id, self.section_id, subid, self.spin_periods.value())
        if success: self.accept()
        else: QMessageBox.critical(self, "Error", msg)


class SlotAssignmentDialog(QDialog):
    def __init__(self, class_id, section_id, day, period_id, parent=None):
        super().__init__(parent)
        self.class_id = class_id; self.section_id = section_id
        self.day = day; self.period_id = period_id
        self.setWindowTitle(f"Custom Assign Slot: {day}")
        self.setMinimumWidth(450)

        lay = QFormLayout(self)
        self.cb_sub = QComboBox(); self.cb_teacher = QComboBox(); self.cb_room = QComboBox()

        class_subjects, _ = AcademicService.get_class_subject_assignment(class_id)
        if not class_subjects:
            lay.addRow(QLabel("No Subjects are assigned to this Class in Academics!"))
        else:
            for sub in class_subjects: self.cb_sub.addItem(sub.name, sub.id)

        all_teachers = HRService.get_employees(status_filter="Active", type_filter="Teacher")
        if not all_teachers:
            lay.addRow(QLabel("No Active Teachers found in the HR Module!"))
        else:
            for t in all_teachers: self.cb_teacher.addItem(f"{t.first_name} {t.last_name or ''}".strip(), t.id)

        self.cb_room.addItem("No Specific Room", None)
        for r in TimetableService.get_rooms(): self.cb_room.addItem(f"{r.name} ({r.room_no})", r.id)

        lay.addRow("Select Subject:", self.cb_sub)
        lay.addRow("Select Teacher:", self.cb_teacher)
        lay.addRow("Select Room (Optional):", self.cb_room)

        btn_save = ModernButton("Check Clashes & Schedule", icon_name="check", variant="success")
        btn_save.clicked.connect(self.process_assignment)
        if not class_subjects or not all_teachers: btn_save.setEnabled(False)
        lay.addWidget(btn_save)

    def process_assignment(self):
        if not self.cb_teacher.currentData() or not self.cb_sub.currentData(): return
        success, msg = TimetableService.check_clash_and_save(
            self.class_id, self.section_id, self.day, self.period_id,
            self.cb_sub.currentData(), self.cb_teacher.currentData(), self.cb_room.currentData()
        )
        if success: self.accept()
        else: QMessageBox.critical(self, "Clash Detected", msg)


class TimetableView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        self.header = PageHeader(
            title="Timetable & Calendar Management",
            subtitle="Manage academic timetables, schedules, events, and room allocations",
            icon_name="timetable",
            icon_color="#2563EB",
            badge_bg="#EFF6FF"
        )

        self.reminder_banner = QLabel("Checking upcoming events...")
        self.reminder_banner.setStyleSheet("""
            background-color: #FEF3C7;
            color: #92400E;
            border: 1px solid #FCD34D;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 600;
        """)
        self.header.add_action_button(self.reminder_banner)
        main_layout.addWidget(self.header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_builder_tab(), IconManager.get("table", "#2563EB", 16), "Timetable Builder")
        self.tabs.addTab(self.create_calendar_tab(), IconManager.get("calendar-days", "#2563EB", 16), "Academic Calendar")
        self.tabs.addTab(self.create_config_tab(), IconManager.get("settings", "#2563EB", 16), "Rooms & Periods Config")

        main_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.refresh_all)
        app_state.subscribe_data_changed(self.refresh_all)
        self.refresh_all() 

    def showEvent(self, event):
        """CRITICAL FIX: Forces a live sync the moment you click the Timetable tab from the Sidebar!"""
        self.refresh_all()
        if self.cb_cls.currentData() and self.cb_sec.currentData():
            self.load_grid()
        super().showEvent(event)

    def _btn(self, text, obj_name="btn_primary"):
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        return btn

    def _table(self):
        tbl = QTableWidget()
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(tbl)
        return tbl

    def refresh_all(self):
        from core.calendar_service import CalendarService
        from datetime import datetime
        today_str = datetime.now().strftime("%Y-%m-%d")
        off_info = CalendarService.get_holiday_or_event(today_str)

        reminders = TimetableService.get_upcoming_reminders()
        msg_parts = []
        if off_info:
            msg_parts.append(f"TODAY: {off_info.get('title')} ({off_info.get('event_type')}) - Classes Suspended / Off Day")
        if reminders:
            msg_parts.append(f"Upcoming: {' | '.join(reminders)}")

        if msg_parts:
            self.reminder_banner.setText("  •  ".join(msg_parts))
            if off_info:
                self.reminder_banner.setStyleSheet("""
                    background-color: #FEE2E2;
                    color: #991B1B;
                    border: 1px solid #FCA5A5;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 600;
                """)
            else:
                self.reminder_banner.setStyleSheet("""
                    background-color: #FEF3C7;
                    color: #92400E;
                    border: 1px solid #FCD34D;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 600;
                """)
            self.reminder_banner.show()
        else:
            self.reminder_banner.hide()
            
        self.load_events()
        self.load_config()

        # Safely preserve class dropdown without crashing
        curr_c = self.cb_cls.currentData()
        active_session = app_state.get_setting("session", "Default")
        self.classes = AcademicService.get_classes(session_filter=active_session)
        self.cb_cls.blockSignals(True); self.cb_cls.clear()
        for c in self.classes: self.cb_cls.addItem(c.name, c.id)
        if curr_c:
            idx = self.cb_cls.findData(curr_c)
            if idx >= 0: self.cb_cls.setCurrentIndex(idx)
        self.cb_cls.blockSignals(False)
        self.sync_sections()

    # ==========================================
    # TAB 1: TIMETABLE BUILDER
    # ==========================================
    def create_builder_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)
        
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)
        self.cb_cls = QComboBox(); self.cb_cls.setMinimumHeight(32); self.cb_cls.currentIndexChanged.connect(self.sync_sections)
        self.cb_sec = QComboBox(); self.cb_sec.setMinimumHeight(32); self.cb_sec.currentIndexChanged.connect(self.load_grid)

        btn_auto = ModernButton("Auto-Generate Timetable", icon_name="rotate-cw", variant="primary")
        btn_auto.setToolTip("Automatically fills the grid based on Teacher Workloads.")
        btn_auto.clicked.connect(self.auto_generate)

        btn_export = ModernButton("Export Excel", icon_name="file-spreadsheet", variant="success")
        btn_export.clicked.connect(self.export_grid_to_excel)

        btn_pdf = ModernButton("Print / PDF", icon_name="printer", variant="secondary")
        btn_pdf.clicked.connect(self.export_grid_to_pdf)

        ctrl.addWidget(QLabel("<b>Class:</b>")); ctrl.addWidget(self.cb_cls)
        ctrl.addWidget(QLabel("<b>Section:</b>")); ctrl.addWidget(self.cb_sec)
        ctrl.addWidget(btn_auto); ctrl.addWidget(btn_export); ctrl.addWidget(btn_pdf); ctrl.addStretch()
        lay.addLayout(ctrl)

        split_lay = QHBoxLayout()
        split_lay.setSpacing(14)

        self.tbl_grid = QTableWidget()
        self.tbl_grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(self.tbl_grid)
        self.tbl_grid.cellDoubleClicked.connect(self.handle_grid_click)
        split_lay.addWidget(self.tbl_grid, stretch=7)

        work_box = ModernCard()
        w_lay = QVBoxLayout(work_box)
        w_lay.setContentsMargins(14, 14, 14, 14)
        w_lay.setSpacing(10)
        
        title_lbl = QLabel("<b>Workload & Assignment Tracker</b><br><small style='color:#64748B;'>Shows official workloads and scheduled slots.</small>")
        w_lay.addWidget(title_lbl)
        
        btn_quick_workload = ModernButton("Add Teacher Workload", icon_name="plus", variant="secondary")
        btn_quick_workload.clicked.connect(self.quick_add_workload)
        w_lay.addWidget(btn_quick_workload)

        self.tbl_workload = QTableWidget()
        self.tbl_workload.setColumnCount(4)
        self.tbl_workload.setHorizontalHeaderLabels(["Subject", "Teacher", "Load", "Del"])
        self.tbl_workload.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_workload.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_workload.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tbl_workload.setColumnWidth(2, 85)
        self.tbl_workload.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tbl_workload.setColumnWidth(3, 54)
        self.tbl_workload.verticalHeader().setDefaultSectionSize(44)
        style_modern_table(self.tbl_workload)
        w_lay.addWidget(self.tbl_workload)
        
        split_lay.addWidget(work_box, stretch=3)
        lay.addLayout(split_lay)
        return page

    def sync_sections(self):
        if self.cb_cls.currentIndex() < 0: return
        curr_s = self.cb_sec.currentData()
        cid = self.cb_cls.currentData()
        self.cb_sec.blockSignals(True); self.cb_sec.clear()
        if cid:
            for s in AcademicService.get_sections(cid): self.cb_sec.addItem(s.name, s.id)
        if curr_s:
            idx = self.cb_sec.findData(curr_s)
            if idx >= 0: self.cb_sec.setCurrentIndex(idx)
        self.cb_sec.blockSignals(False); self.load_grid()

    def load_grid(self):
        cid = self.cb_cls.currentData(); sid = self.cb_sec.currentData()
        if not cid or not sid: return

        self.periods = TimetableService.get_periods()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

        self.tbl_grid.clear()
        self.tbl_grid.setRowCount(len(self.periods))
        self.tbl_grid.setColumnCount(len(days))
        self.tbl_grid.setHorizontalHeaderLabels(days)
        
        if not self.periods:
            self.tbl_grid.setItem(0, 0, QTableWidgetItem("No Periods Configured! Please go to the Config Tab first."))
            return

        p_labels = []
        for p in self.periods:
            if p.start_time and p.end_time:
                p_labels.append(f"{p.name}\n({p.start_time} – {p.end_time})")
            else:
                p_labels.append(p.name)
        self.tbl_grid.setVerticalHeaderLabels(p_labels)
        self.tbl_grid.verticalHeader().setDefaultSectionSize(70)

        for r, p in enumerate(self.periods):
            if p.is_break:
                for c in range(len(days)):
                    item = QTableWidgetItem("BREAK")
                    item.setForeground(QColor("#64748B")); item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tbl_grid.setItem(r, c, item)

        entries = TimetableService.get_class_timetable(cid, sid)
        for e in entries:
            try:
                r = [p.id for p in self.periods].index(e.period_id)
                c = days.index(e.day_of_week)
                
                t_name = f"{e.employee.first_name} {e.employee.last_name or ''}".strip()
                cell_text = f"{e.academic_subject.name}\n{t_name}"
                if e.room: cell_text += f"\nRoom: {e.room.room_no}"
                
                item = QTableWidgetItem(cell_text)
                item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                self.tbl_grid.setItem(r, c, item)
            except Exception as e:
                print(f"Timetable grid load warning: {e}")

        self.refresh_workload_tracker(cid, sid)

    def refresh_workload_tracker(self, cid, sid):
        for child in self.tbl_workload.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_workload.clearContents()

        wl = TimetableService.get_workload_completion(cid, sid)
        self.tbl_workload.setRowCount(len(wl))
        for r, w in enumerate(wl):
            self.tbl_workload.setItem(r, 0, QTableWidgetItem(w["subject"]))
            self.tbl_workload.setItem(r, 1, QTableWidgetItem(w["teacher"]))
            
            l_str = f"{w['scheduled']} / {w['assigned']}"
            item = QTableWidgetItem(l_str)
            item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if w['scheduled'] < w['assigned']: item.setForeground(QColor("#F59E0B"))
            elif w['scheduled'] == w['assigned'] and w['assigned'] > 0: item.setForeground(QColor("#10B981"))
            else: item.setForeground(QColor("#EF4444")) 
            self.tbl_workload.setItem(r, 2, item)

            if w["assign_id"]:
                btn_del = TableActionButton("trash-2", variant="delete", tooltip="Delete Workload", size=28)
                btn_del.clicked.connect(lambda checked=False, aid=w["assign_id"]: self.delete_workload(aid))
                self.tbl_workload.setCellWidget(r, 3, create_table_actions_cell([btn_del]))
            else:
                item_dash = QTableWidgetItem("-")
                item_dash.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl_workload.setItem(r, 3, item_dash)
            self.tbl_workload.setRowHeight(r, 44)

    def quick_add_workload(self):
        cid = self.cb_cls.currentData(); sid = self.cb_sec.currentData()
        if not cid or not sid:
            QMessageBox.warning(self, "Select Class", "Please select a Class and Section first."); return
        diag = QuickWorkloadDialog(cid, sid, self)
        if diag.exec(): self.refresh_workload_tracker(cid, sid)

    def delete_workload(self, aid):
        if QMessageBox.question(self, "Remove", "Delete this workload target?") == QMessageBox.StandardButton.Yes:
            HRService.delete_assignment(aid)
            self.load_grid()

    def handle_grid_click(self, row, col):
        if not self.periods: return
        p = self.periods[row]
        if p.is_break: return

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        day = days[col]
        cid = self.cb_cls.currentData(); sid = self.cb_sec.currentData()
        if not cid or not sid: return

        existing = self.tbl_grid.item(row, col)
        if existing and existing.text().strip() and "BREAK" not in existing.text():
            reply = QMessageBox.question(self, "Clear Slot", f"Clear slot for {day} - {p.name}?")
            if reply == QMessageBox.StandardButton.Yes:
                TimetableService.remove_slot(cid, sid, day, p.id)
                self.load_grid()
        else:
            diag = SlotAssignmentDialog(cid, sid, day, p.id, self)
            if diag.exec(): self.load_grid()

    def auto_generate(self):
        cid = self.cb_cls.currentData(); sid = self.cb_sec.currentData()
        if not cid or not sid: return
        
        reply = QMessageBox.question(self, "Auto-Generate", "This will securely auto-fill the grid based on Teacher Workloads. Continue?")
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = TimetableService.auto_generate_timetable(cid, sid)
            if success:
                QMessageBox.information(self, "Success", msg); self.load_grid()
            else:
                QMessageBox.critical(self, "Error", msg)

    def export_grid_to_excel(self):
        cid = self.cb_cls.currentData(); sid = self.cb_sec.currentData()
        if not cid or not sid: return
        
        c_name = f"{self.cb_cls.currentText()} - {self.cb_sec.currentText()}"
        path, _ = QFileDialog.getSaveFileName(self, "Export Timetable", f"Timetable_{c_name}.xlsx", "Excel Files (*.xlsx)")
        if path:
            success, msg = TimetableService.export_timetable_to_excel(cid, sid, path, c_name)
            if success: QMessageBox.information(self, "Exported", f"Timetable successfully saved to:\n{path}")
            else: QMessageBox.critical(self, "Error", msg)

    def export_grid_to_pdf(self):
        cid = self.cb_cls.currentData(); sid = self.cb_sec.currentData()
        if not cid or not sid: return
        
        c_name = f"{self.cb_cls.currentText()} - {self.cb_sec.currentText()}"
        clean_name = "".join(c for c in c_name if c.isalnum() or c in (' ', '_', '-')).strip()
        path, _ = QFileDialog.getSaveFileName(self, "Export Timetable PDF", f"Timetable_{clean_name}.pdf", "PDF Files (*.pdf)")
        if path:
            success, msg = TimetableService.export_timetable_to_pdf(cid, sid, path, c_name)
            if success:
                QMessageBox.information(self, "Exported", f"Timetable PDF successfully saved to:\n{path}")
            else:
                QMessageBox.critical(self, "Error", msg)

    # ==========================================
    # TAB 2: ACADEMIC CALENDAR
    # ==========================================
    def create_calendar_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(12)
        
        form_card = ModernCard()
        fc_lay = QVBoxLayout(form_card)
        fc_lay.setContentsMargins(16, 16, 16, 16)
        fc_lay.setSpacing(12)
        
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        
        self.ev_title = QLineEdit()
        self.ev_title.setPlaceholderText("e.g. Annual Sports Day / Mid-Term Exams")
        self.ev_type = QComboBox()
        self.ev_type.addItems(["School Holiday", "Exam Week", "Public Event", "Meeting"])
        self.ev_start = QDateEdit(QDate.currentDate())
        self.ev_start.setCalendarPopup(True)
        self.ev_end = QDateEdit(QDate.currentDate())
        self.ev_end.setCalendarPopup(True)
        self.ev_desc = QLineEdit()
        self.ev_desc.setPlaceholderText("Brief event notes or location")

        grid.addWidget(QLabel("<b>Event Title:</b>"), 0, 0)
        grid.addWidget(self.ev_title, 0, 1)
        grid.addWidget(QLabel("<b>Event Type:</b>"), 0, 2)
        grid.addWidget(self.ev_type, 0, 3)

        dates_w = QWidget()
        dates_l = QHBoxLayout(dates_w)
        dates_l.setContentsMargins(0, 0, 0, 0)
        dates_l.setSpacing(8)
        dates_l.addWidget(self.ev_start)
        lbl_to = QLabel("to")
        lbl_to.setStyleSheet("color: #64748B; font-weight: bold;")
        dates_l.addWidget(lbl_to)
        dates_l.addWidget(self.ev_end)

        grid.addWidget(QLabel("<b>Date Range:</b>"), 1, 0)
        grid.addWidget(dates_w, 1, 1)
        grid.addWidget(QLabel("<b>Description:</b>"), 1, 2)
        grid.addWidget(self.ev_desc, 1, 3)

        fc_lay.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = ModernButton("Add to Academic Calendar", icon_name="calendar-days", variant="primary")
        btn_save.clicked.connect(self.save_event)
        btn_row.addWidget(btn_save)
        fc_lay.addLayout(btn_row)

        lay.addWidget(form_card)

        self.tbl_events = self._table()
        self.tbl_events.setColumnCount(5)
        self.tbl_events.setHorizontalHeaderLabels(["Title", "Type", "Start Date", "End Date", "Description"])
        self.tbl_events.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_events.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tbl_events.setColumnWidth(1, 140)
        self.tbl_events.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tbl_events.setColumnWidth(2, 115)
        self.tbl_events.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tbl_events.setColumnWidth(3, 115)
        self.tbl_events.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl_events.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_events, stretch=1)
        self.load_events()
        return page

    def save_event(self):
        success, msg = TimetableService.save_event(self.ev_title.text(), self.ev_type.currentText(), self.ev_start.date().toString("yyyy-MM-dd"), self.ev_end.date().toString("yyyy-MM-dd"), self.ev_desc.text())
        if success: self.load_events(); self.refresh_all(); self.ev_title.clear()

    def load_events(self):
        for child in self.tbl_events.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_events.clearContents()

        evs = TimetableService.get_events()
        self.tbl_events.setRowCount(len(evs))
        for r, e in enumerate(evs):
            t_item = QTableWidgetItem(e.title)
            t_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tbl_events.setItem(r, 0, t_item)

            type_item = QTableWidgetItem(e.event_type)
            if e.event_type == "School Holiday":
                type_item.setForeground(QColor("#10B981"))
            elif e.event_type == "Exam Week":
                type_item.setForeground(QColor("#EF4444"))
            else:
                type_item.setForeground(QColor("#2563EB"))
            self.tbl_events.setItem(r, 1, type_item)

            self.tbl_events.setItem(r, 2, QTableWidgetItem(e.start_date))
            self.tbl_events.setItem(r, 3, QTableWidgetItem(e.end_date))
            self.tbl_events.setItem(r, 4, QTableWidgetItem(e.description or "-"))
            self.tbl_events.setRowHeight(r, 48)

    # ==========================================
    # TAB 3: CONFIG
    # ==========================================
    def create_config_tab(self):
        page = QWidget(); lay = QHBoxLayout(page); lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(14)

        r_box = ModernCard(); rl = QVBoxLayout(r_box)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.addWidget(QLabel("<b>Campus Rooms / Resources</b>"))
        r_form = QFormLayout()
        self.r_no = QLineEdit(); self.r_name = QLineEdit(); self.r_cap = QLineEdit()
        self.r_type = QComboBox(); self.r_type.addItems(["Classroom", "Computer Lab", "Science Lab", "Library"])
        r_form.addRow("Room Number:", self.r_no); r_form.addRow("Room Name:", self.r_name)
        r_form.addRow("Capacity:", self.r_cap); r_form.addRow("Type:", self.r_type)
        btn_r = ModernButton("Save Room", icon_name="save", variant="success"); btn_r.clicked.connect(self.save_room)
        rl.addLayout(r_form); rl.addWidget(btn_r)
        self.tbl_rooms = self._table(); self.tbl_rooms.setColumnCount(4); self.tbl_rooms.setHorizontalHeaderLabels(["No", "Name", "Capacity", "Type"])
        rl.addWidget(self.tbl_rooms); lay.addWidget(r_box)

        p_box = ModernCard(); pl = QVBoxLayout(p_box)
        pl.setContentsMargins(16, 16, 16, 16)
        pl.addWidget(QLabel("<b>Bell Schedule & Periods</b>"))
        p_form = QFormLayout()
        self.p_name = QLineEdit(); self.p_start = QLineEdit(); self.p_end = QLineEdit()
        self.p_break = QComboBox(); self.p_break.addItems(["Teaching Period", "Break / Recess"])
        p_form.addRow("Period Name (e.g. Period 1):", self.p_name); p_form.addRow("Start Time (e.g. 08:00 AM):", self.p_start)
        p_form.addRow("End Time (e.g. 08:40 AM):", self.p_end); p_form.addRow("Type:", self.p_break)
        btn_p = ModernButton("Save Period", icon_name="save", variant="primary"); btn_p.clicked.connect(self.save_period)
        pl.addLayout(p_form); pl.addWidget(btn_p)
        self.tbl_periods = self._table(); self.tbl_periods.setColumnCount(4); self.tbl_periods.setHorizontalHeaderLabels(["Name", "Start", "End", "Type"])
        pl.addWidget(self.tbl_periods); lay.addWidget(p_box)
        return page

    def save_room(self):
        TimetableService.save_room(self.r_no.text(), self.r_name.text(), self.r_cap.text(), self.r_type.currentText())
        self.load_config()

    def save_period(self):
        TimetableService.save_period(self.p_name.text(), self.p_start.text(), self.p_end.text(), True if "Break" in self.p_break.currentText() else False, self.tbl_periods.rowCount() + 1)
        self.load_config()

    def load_config(self):
        rooms = TimetableService.get_rooms()
        self.tbl_rooms.setRowCount(len(rooms))
        for r, rm in enumerate(rooms):
            self.tbl_rooms.setItem(r, 0, QTableWidgetItem(rm.room_no)); self.tbl_rooms.setItem(r, 1, QTableWidgetItem(rm.name))
            self.tbl_rooms.setItem(r, 2, QTableWidgetItem(str(rm.capacity))); self.tbl_rooms.setItem(r, 3, QTableWidgetItem(rm.room_type))
            
        periods = TimetableService.get_periods()
        self.tbl_periods.setRowCount(len(periods))
        for r, p in enumerate(periods):
            self.tbl_periods.setItem(r, 0, QTableWidgetItem(p.name)); self.tbl_periods.setItem(r, 1, QTableWidgetItem(p.start_time))
            self.tbl_periods.setItem(r, 2, QTableWidgetItem(p.end_time)); self.tbl_periods.setItem(r, 3, QTableWidgetItem("Break" if p.is_break else "Class"))