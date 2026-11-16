from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QTabWidget, QMessageBox, QFrame, QAbstractItemView, QGridLayout,
                               QDialog, QFormLayout, QLineEdit, QSpinBox, QComboBox, QCheckBox, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect
import PySide6.QtWidgets

from core.academic_service import AcademicService
from core.state_manager import app_state
from core.student_service import StudentService
from core.fee_service import FeeService
from core.icon_manager import IconManager
from ui.components.stitch_widgets import (
    PageHeader, MetricCard, ModernCard, ModernButton, TableActionButton, TableTextButton,
    create_table_actions_cell, StatusBadge,
    style_modern_table, style_modern_tabs
)

# ==========================================
# CUSTOM DIALOGS FOR ADDING & EDITING DATA
# ==========================================
class ClassDashboardDialog(QDialog):
    def __init__(self, class_id, class_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Class Dashboard - {class_name}")
        self.setMinimumSize(950, 650)

        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Title
        header = QLabel(f"Dashboard: Class {class_name}")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(header)

        # 3 Live Metric Cards
        stats_lay = QHBoxLayout()
        self.lbl_students = self._stat_card("Total Students", "0", "#3B82F6")
        self.lbl_fees = self._stat_card("Total Pending Fees", "Rs. 0", "#EF4444")
        self.lbl_perf = self._stat_card("Overall Performance", "Live Syncing...", "#10B981")
        stats_lay.addWidget(self.lbl_students)
        stats_lay.addWidget(self.lbl_fees)
        stats_lay.addWidget(self.lbl_perf)
        layout.addLayout(stats_lay)

        # Unified Live Data Table
        layout.addWidget(QLabel("<b>Live Student Roster & Metrics:</b>"))
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(6)
        self.tbl.setHorizontalHeaderLabels(["System ID", "Student Name", "Section", "Pending Fee", "Exam / Academics", "Status"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tbl)
        
        self.load_live_data(class_id)

    def _stat_card(self, title, init_val, color):
        card = QFrame()
        card.setObjectName("stat_card")
        card.setStyleSheet(f"QFrame#stat_card {{ border-left: 5px solid {color}; border-radius: 12px; }}")
        lay = QVBoxLayout(card); lay.setContentsMargins(20, 20, 20, 20)
        t_lbl = QLabel(title); t_lbl.setStyleSheet("background: transparent; border: none;")
        v_lbl = QLabel(init_val); v_lbl.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: bold; margin-top: 5px;")
        lay.addWidget(t_lbl); lay.addWidget(v_lbl)
        card.value_label = v_lbl
        return card

    def load_live_data(self, class_id):
        try:
            students = StudentService.get_students(class_id=class_id, status_filter="Active")
            self.tbl.setRowCount(len(students))
            
            total_pending = 0
            
            for r, stu in enumerate(students):
                self.tbl.setItem(r, 0, QTableWidgetItem(stu.student_id))
                self.tbl.setItem(r, 1, QTableWidgetItem(f"{stu.first_name} {stu.last_name or ''}".strip()))
                
                sec_name = stu.academic_section.name if stu.academic_section else "Unassigned"
                self.tbl.setItem(r, 2, QTableWidgetItem(sec_name))
                
                pending_amt = FeeService.get_student_pending_balance(stu.id)
                total_pending += pending_amt
                fee_item = QTableWidgetItem(f"Rs. {pending_amt:,.0f}")
                if pending_amt > 0:
                    fee_item.setForeground(QColor("#EF4444")); fee_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                else:
                    fee_item.setForeground(QColor("#10B981"))
                self.tbl.setItem(r, 3, fee_item)
                
                exam_item = QTableWidgetItem("Linked to Exam Module")
                exam_item.setForeground(QColor("#8B5CF6"))
                self.tbl.setItem(r, 4, exam_item)
                
                st_item = QTableWidgetItem(stu.status)
                st_item.setForeground(QColor("#10B981"))
                self.tbl.setItem(r, 5, st_item)
            
            self.lbl_students.value_label.setText(str(len(students)))
            self.lbl_fees.value_label.setText(f"Rs. {total_pending:,.0f}")
            self.lbl_perf.value_label.setText("Good / Active")
            
        except Exception as e:
            print(f"Error loading dashboard: {e}")


class AddClassDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Class")
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. 8, 9, 10, Prep")
        form.addRow("<b>Class Name:</b>", self.name_input)
        layout.addLayout(form)
        
        layout.addSpacing(10)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Class")
        self.btn_save.setObjectName("btn_success")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save); btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.name_input.text().strip()


class AddSubjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Subject")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        input_style = ""
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("e.g. Mathematics")
        self.name_input.setStyleSheet(input_style)
        self.code_input = QLineEdit(); self.code_input.setPlaceholderText("e.g. MATH-101 (Optional)")
        self.code_input.setStyleSheet(input_style)
        self.type_input = QComboBox(); self.type_input.addItems(["Compulsory", "Optional", "Practical"])
        self.type_input.setStyleSheet(input_style)
        
        form.addRow("<b>Subject Name:</b>", self.name_input)
        form.addRow("<b>Subject Code:</b>", self.code_input)
        form.addRow("<b>Subject Type:</b>", self.type_input)
        layout.addLayout(form)
        
        layout.addSpacing(10)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Subject")
        self.btn_save.setObjectName("btn_success")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save); btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        return self.name_input.text().strip(), self.code_input.text().strip(), self.type_input.currentText()


class AddGroupedSectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Section")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        input_style = ""
        self.name_input = QLineEdit(); self.name_input.setPlaceholderText("e.g. A, B, Girls Section")
        self.name_input.setStyleSheet(input_style)
        self.capacity_input = QSpinBox(); self.capacity_input.setRange(10, 150); self.capacity_input.setValue(40)
        self.capacity_input.setStyleSheet(input_style)
        
        form.addRow("<b>Section Name:</b>", self.name_input)
        form.addRow("<b>Default Capacity:</b>", self.capacity_input)
        layout.addLayout(form)
        
        layout.addWidget(QLabel("<b>Assign to Classes:</b> (Tick all that apply)"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(150)
        
        check_widget = QWidget()
        self.check_layout = QVBoxLayout(check_widget)
        
        self.checkboxes = {}
        classes = AcademicService.get_classes()
        if not classes:
            self.check_layout.addWidget(QLabel("No classes available. Please add a class first."))
        else:
            for c in classes:
                chk = QCheckBox(c.name)
                chk.setStyleSheet("font-size: 14px; padding: 5px; font-weight: bold;")
                self.check_layout.addWidget(chk)
                self.checkboxes[c.id] = chk
                
        scroll.setWidget(check_widget)
        layout.addWidget(scroll)
        
        layout.addSpacing(10)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Save Section")
        self.btn_save.setObjectName("btn_success")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save); btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        selected_classes = [cid for cid, chk in self.checkboxes.items() if chk.isChecked()]
        return self.name_input.text().strip(), selected_classes, self.capacity_input.value()


class EditGroupedSectionDialog(QDialog):
    def __init__(self, section_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Section")
        self.setMinimumWidth(400)
        self.old_name = section_data["name"]
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        input_style = ""
        self.name_input = QLineEdit(section_data["name"])
        self.name_input.setStyleSheet(input_style)
        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(10, 150)
        self.capacity_input.setValue(section_data["capacity"])
        self.capacity_input.setStyleSheet(input_style)
        
        form.addRow("<b>Section Name:</b>", self.name_input)
        form.addRow("<b>Capacity:</b>", self.capacity_input)
        layout.addLayout(form)
        
        layout.addWidget(QLabel("<b>Assigned Classes:</b> (Tick to add, Untick to remove)"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(150)
        
        check_widget = QWidget()
        self.check_layout = QVBoxLayout(check_widget)
        
        self.checkboxes = {}
        classes = AcademicService.get_classes()
        assigned_ids = section_data.get("class_ids", [])
        
        for c in classes:
            chk = QCheckBox(c.name)
            chk.setStyleSheet("font-size: 14px; padding: 5px; font-weight: bold;")
            if c.id in assigned_ids:
                chk.setChecked(True)
            self.check_layout.addWidget(chk)
            self.checkboxes[c.id] = chk
                
        scroll.setWidget(check_widget)
        layout.addWidget(scroll)
        
        layout.addSpacing(10)
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Update Section")
        self.btn_save.setObjectName("btn_primary")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("btn_secondary")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save); btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def get_data(self):
        selected_classes = [cid for cid, chk in self.checkboxes.items() if chk.isChecked()]
        return self.old_name, self.name_input.text().strip(), selected_classes, self.capacity_input.value()


class SectionStudentsDialog(QDialog):
    """Modal displaying authoritative real-time student enrollment for a section."""
    def __init__(self, section_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Section {section_name} — Enrolled Students")
        self.setMinimumSize(880, 520)
        self.setStyleSheet("""
            QDialog { background-color: #FFFFFF; }
            QLabel { color: #0F172A; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(f"Enrolled Students: Section {section_name}")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        top.addWidget(title)
        top.addStretch()
        layout.addLayout(top)

        tbl = QTableWidget()
        tbl.setColumnCount(6)
        tbl.setHorizontalHeaderLabels(["System ID", "Student Name", "Father Name", "Class", "Contact No.", "Status"])
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        tbl.setColumnWidth(0, 140)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        tbl.setColumnWidth(3, 110)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        tbl.setColumnWidth(4, 130)
        tbl.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        tbl.setColumnWidth(5, 100)
        tbl.verticalHeader().setDefaultSectionSize(40)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        style_modern_table(tbl)
        layout.addWidget(tbl)

        students = AcademicService.get_section_students(section_name)
        tbl.setRowCount(len(students))
        for r, s in enumerate(students):
            id_item = QTableWidgetItem(s["student_id"])
            id_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tbl.setItem(r, 0, id_item)

            name_item = QTableWidgetItem(s["name"])
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tbl.setItem(r, 1, name_item)

            tbl.setItem(r, 2, QTableWidgetItem(s["father_name"]))
            tbl.setItem(r, 3, QTableWidgetItem(s["class_name"]))
            tbl.setItem(r, 4, QTableWidgetItem(s["phone"]))

            st_item = QTableWidgetItem(s["status"])
            st_item.setForeground(QColor("#059669" if s["status"] == "Active" else "#DC2626"))
            st_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tbl.setItem(r, 5, st_item)

        bot = QHBoxLayout()
        count_lbl = QLabel(f"Total Enrolled Students: <b>{len(students)}</b>")
        count_lbl.setStyleSheet("color: #475569; font-size: 13px;")
        bot.addWidget(count_lbl)
        bot.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #0F172A;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 20px;
                border: 1px solid #CBD5E1;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """)
        bot.addWidget(btn_close)
        layout.addLayout(bot)


# ==========================================
# MAIN ACADEMIC VIEW
# ==========================================
class AcademicView(QWidget):
    def __init__(self):
        super().__init__() 
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # Header
        self.header = PageHeader(
            title="Academic Foundation",
            subtitle=f"Active Academic Session: {app_state.get_setting('session', '2026')}",
            icon_name="school",
            icon_color="#2563EB",
            badge_bg="#EFF6FF"
        )
        main_layout.addWidget(self.header)

        # Tabs
        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_overview_tab(), IconManager.get("bar-chart-2", "#2563EB", 16), "Overview")
        self.tabs.addTab(self.create_classes_tab(), IconManager.get("school", "#2563EB", 16), "Classes")
        self.tabs.addTab(self.create_sections_tab(), IconManager.get("list-ordered", "#2563EB", 16), "Sections")
        self.tabs.addTab(self.create_subjects_tab(), IconManager.get("book-open", "#2563EB", 16), "Subjects")
        self.tabs.addTab(self.create_assignments_tab(), IconManager.get("sliders", "#2563EB", 16), "Subject Assignments")

        main_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.refresh_all)
        app_state.subscribe_data_changed(self.refresh_all)
        self.refresh_all()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_all()

    def refresh_data(self):
        self.refresh_all()

    def _btn(self, text, color):
        btn = QPushButton(text)
        color_map = {
            "#10B981": "btn_success",
            "#EF4444": "btn_danger",
            "#3B82F6": "btn_primary",
            "#F59E0B": "btn_warning",
            "#8B5CF6": "btn_purple",
            "#111827": "btn_primary"
        }
        btn.setObjectName(color_map.get(color, "btn_primary"))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _table(self):
        tbl = QTableWidget()
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(tbl)
        return tbl

    def refresh_all(self):
        self.load_overview()
        self.load_classes()
        self.load_sections()
        self.load_subjects()

    # ==========================================
    # OVERVIEW TAB
    # ==========================================
    def create_overview_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        self.lbl_cls = MetricCard("Total Classes", "0", "Configured academic grades", icon_name="school", icon_color="#2563EB", badge_bg="#EFF6FF")
        self.lbl_sec = MetricCard("Unique Sections", "0", "Active class sections", icon_name="list-ordered", icon_color="#10B981", badge_bg="#ECFDF5")
        self.lbl_sub = MetricCard("Total Subjects", "0", "Curriculum subjects", icon_name="book-open", icon_color="#F59E0B", badge_bg="#FFFBEB")
        
        grid.addWidget(self.lbl_cls, 0, 0)
        grid.addWidget(self.lbl_sec, 0, 1)
        grid.addWidget(self.lbl_sub, 0, 2)
        
        lay.addLayout(grid)
        lay.addStretch()
        return page

    def _stat_card(self, title, icon, init_val, color):
        card = QFrame()
        card.setObjectName("stat_card")
        shadow = QGraphicsDropShadowEffect(self); shadow.setBlurRadius(12); shadow.setColor(QColor(0, 0, 0, 12)); shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)
        
        lay = QVBoxLayout(card); lay.setContentsMargins(14, 12, 14, 12)
        
        top = QHBoxLayout()
        ic = QLabel(icon); ic.setStyleSheet(f"font-size: 16px; color: {color}; background-color: {color}20; padding: 6px; border-radius: 6px;")
        t_lbl = QLabel(title); t_lbl.setStyleSheet("background: transparent; border: none; font-size: 11px;")
        top.addWidget(ic); top.addWidget(t_lbl); top.addStretch()
        
        v_lbl = QLabel(init_val); v_lbl.setStyleSheet("font-size: 22px; font-weight: bold; border: none; margin-top: 4px;")
        
        lay.addLayout(top); lay.addWidget(v_lbl)
        card.value_label = v_lbl
        return card

    def load_overview(self):
        metrics = AcademicService.get_dashboard_metrics()
        self.lbl_cls.value_label.setText(str(metrics["classes"]))
        self.lbl_sec.value_label.setText(str(metrics["sections"]))
        self.lbl_sub.value_label.setText(str(metrics["subjects"]))

    # ==========================================
    # CLASSES TAB (UPGRADED WITH DASHBOARD)
    # ==========================================
    def create_classes_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        
        top = QHBoxLayout()
        btn_add = ModernButton("Add New Class", icon_name="plus", variant="primary")
        btn_add.clicked.connect(self.show_add_class)
        top.addWidget(btn_add); top.addStretch()
        lay.addLayout(top)
        
        lay.addSpacing(6)
        self.tbl_cls = self._table()
        
        self.tbl_cls.setColumnCount(4)
        self.tbl_cls.setHorizontalHeaderLabels(["Class Name", "Total Students", "Performance", "Actions"])
        self.tbl_cls.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_cls.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_cls.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tbl_cls.setColumnWidth(2, 130)
        self.tbl_cls.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tbl_cls.setColumnWidth(3, 110)
        self.tbl_cls.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_cls)
        return page

    def show_add_class(self):
        dialog = AddClassDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_data()
            if name:
                success, msg = AcademicService.add_class(name)
                if success: self.refresh_all()
                else: QMessageBox.critical(self, "Error", msg)
            else:
                QMessageBox.warning(self, "Warning", "Class Name cannot be empty.")

    def open_class_dashboard(self, cid, cname):
        dialog = ClassDashboardDialog(cid, cname, self)
        dialog.exec()

    def load_classes(self):
        for child in self.tbl_cls.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_cls.clearContents()

        classes = AcademicService.get_classes_with_stats()
        self.tbl_cls.setRowCount(len(classes))
        
        for r, c in enumerate(classes):
            name_item = QTableWidgetItem(f"Class {c['name']}")
            font = QFont(); font.setBold(True)
            name_item.setFont(font)
            self.tbl_cls.setItem(r, 0, name_item)
            
            count_item = QTableWidgetItem(f"{c['student_count']} Students")
            if c['student_count'] > 0: count_item.setForeground(QColor("#10B981"))
            self.tbl_cls.setItem(r, 1, count_item)
            
            btn_dash = TableTextButton("Dashboard", icon_name="eye", variant="secondary")
            btn_dash.clicked.connect(lambda checked=False, cid=c['id'], cname=c['name']: self.open_class_dashboard(cid, cname))
            self.tbl_cls.setCellWidget(r, 2, create_table_actions_cell([btn_dash]))
            
            btn_del = TableTextButton("Delete", icon_name="trash-2", variant="danger")
            btn_del.clicked.connect(lambda checked=False, cid=c['id']: self.delete_class(cid))
            self.tbl_cls.setCellWidget(r, 3, create_table_actions_cell([btn_del]))
            self.tbl_cls.setRowHeight(r, 48)

    def delete_class(self, cid):
        if QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this class?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            success, msg = AcademicService.delete_class(cid)
            if success: self.refresh_all()
            else: QMessageBox.critical(self, "Error", msg)

    # ==========================================
    # SECTIONS TAB (GROUPED, EDITABLE & LIVE ENROLLMENT)
    # ==========================================
    def create_sections_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        
        top = QHBoxLayout()
        btn_add = ModernButton("Add New Section", icon_name="plus", variant="success")
        btn_add.clicked.connect(self.show_add_section)
        top.addWidget(btn_add); top.addStretch()
        lay.addLayout(top)
        
        lay.addSpacing(6)
        self.tbl_sec = self._table()
        self.tbl_sec.setColumnCount(5)
        self.tbl_sec.setHorizontalHeaderLabels(["Section Name", "Assigned Classes", "Enrolled Students", "Capacity", "Actions"])
        self.tbl_sec.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_sec.setColumnWidth(0, 160)
        self.tbl_sec.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_sec.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_sec.setColumnWidth(2, 220)
        self.tbl_sec.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tbl_sec.setColumnWidth(3, 170)
        self.tbl_sec.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tbl_sec.setColumnWidth(4, 170)
        self.tbl_sec.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_sec)
        return page

    def show_add_section(self):
        dialog = AddGroupedSectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, class_ids, capacity = dialog.get_data()
            if not name or not class_ids:
                QMessageBox.warning(self, "Error", "Name and at least one class are required.")
                return
            
            success, msg = AcademicService.add_grouped_section(name, class_ids, capacity)
            if success: self.refresh_all()
            else: QMessageBox.critical(self, "Error", msg)

    def show_edit_section(self, section_data):
        dialog = EditGroupedSectionDialog(section_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_name, new_name, class_ids, capacity = dialog.get_data()
            if not new_name or not class_ids:
                QMessageBox.warning(self, "Error", "Name and at least one class are required.")
                return
            
            success, msg = AcademicService.update_grouped_section(old_name, new_name, class_ids, capacity)
            if success: self.refresh_all()
            else: QMessageBox.critical(self, "Error", msg)

    def load_sections(self):
        for child in self.tbl_sec.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_sec.clearContents()

        grouped_sections = AcademicService.get_grouped_sections()
        self.tbl_sec.setRowCount(len(grouped_sections))
        
        for r, sec in enumerate(grouped_sections):
            # Col 0: Section Name
            name_item = QTableWidgetItem(f"Section {sec['name']}")
            font = QFont(); font.setBold(True); name_item.setFont(font)
            self.tbl_sec.setItem(r, 0, name_item)
            
            # Col 1: Assigned Classes
            classes_item = QTableWidgetItem(sec["class_string"])
            font2 = QFont(); font2.setBold(True); classes_item.setFont(font2)
            classes_item.setForeground(QColor("#2563EB")) 
            self.tbl_sec.setItem(r, 1, classes_item)
            
            # Col 2: Enrolled Students (Clickable to view full student list)
            enrolled = sec.get("enrolled_count", 0)
            cap = sec.get("capacity", 40)
            btn_stu = QPushButton(f"👤 {enrolled} Enrolled (Click to View)")
            btn_stu.setToolTip(f"View all {enrolled} real enrolled students in Section {sec['name']}")
            btn_stu.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_stu.setFixedHeight(32)
            btn_stu.setStyleSheet("""
                QPushButton {
                    background-color: #EFF6FF;
                    color: #1D4ED8;
                    font-weight: bold;
                    font-size: 12px;
                    border: 1px solid #BFDBFE;
                    border-radius: 6px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background-color: #DBEAFE;
                    border-color: #93C5FD;
                }
            """)
            btn_stu.clicked.connect(lambda checked=False, sname=sec["name"]: SectionStudentsDialog(sname, self).exec())
            self.tbl_sec.setCellWidget(r, 2, btn_stu)

            # Col 3: Capacity (Updatable inline)
            spin_cap = QSpinBox()
            spin_cap.setRange(5, 500)
            spin_cap.setValue(int(sec["capacity"]))
            spin_cap.setSuffix(" Students")
            spin_cap.setFixedHeight(32)
            spin_cap.setStyleSheet("""
                QSpinBox {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    font-weight: bold;
                    font-size: 12px;
                    border: 1.5px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 2px 8px;
                }
                QSpinBox:focus {
                    border: 2px solid #2563EB;
                }
            """)
            def _make_cap_handler(sname):
                def _handler(new_val):
                    AcademicService.update_section_capacity(sname, new_val)
                return _handler
            spin_cap.valueChanged.connect(_make_cap_handler(sec["name"]))
            self.tbl_sec.setCellWidget(r, 3, spin_cap)

            # Col 4: Actions
            btn_edit = TableTextButton("Edit", icon_name="pencil", variant="secondary")
            btn_edit.clicked.connect(lambda checked=False, s=sec: self.show_edit_section(s))
            
            btn_del = TableTextButton("Delete", icon_name="trash-2", variant="danger")
            btn_del.clicked.connect(lambda checked=False, sname=sec["name"]: self.delete_section(sname))
            
            self.tbl_sec.setCellWidget(r, 4, create_table_actions_cell([btn_edit, btn_del]))
            self.tbl_sec.setRowHeight(r, 48)

    def delete_section(self, name):
        if QMessageBox.question(self, "Confirm Deletion", f"Delete the '{name}' section from ALL assigned classes?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            success, msg = AcademicService.delete_grouped_section(name)
            if success: self.refresh_all()
            else: QMessageBox.critical(self, "Error", msg)

    # ==========================================
    # SUBJECTS TAB
    # ==========================================
    def create_subjects_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 8, 0, 0)
        
        top = QHBoxLayout()
        btn_add = ModernButton("Add New Subject", icon_name="plus", variant="warning")
        btn_add.clicked.connect(self.show_add_subject)
        top.addWidget(btn_add); top.addStretch()
        lay.addLayout(top)
        
        lay.addSpacing(6)
        self.tbl_sub = self._table()
        self.tbl_sub.setColumnCount(4)
        self.tbl_sub.setHorizontalHeaderLabels(["Subject Name", "Code", "Type", "Actions"])
        self.tbl_sub.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_sub.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_sub.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_sub.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tbl_sub.setColumnWidth(3, 110)
        self.tbl_sub.verticalHeader().setDefaultSectionSize(48)
        lay.addWidget(self.tbl_sub)
        return page

    def show_add_subject(self):
        dialog = AddSubjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, code, sub_type = dialog.get_data()
            if name:
                success, msg = AcademicService.add_subject(name, code, sub_type)
                if success: self.refresh_all()
                else: QMessageBox.critical(self, "Error", msg)
            else:
                QMessageBox.warning(self, "Warning", "Subject Name cannot be empty.")

    def load_subjects(self):
        for child in self.tbl_sub.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_sub.clearContents()

        subs = AcademicService.get_subjects()
        self.tbl_sub.setRowCount(len(subs))
        for r, s in enumerate(subs):
            name_item = QTableWidgetItem(s.name)
            font = QFont(); font.setBold(True); name_item.setFont(font)
            self.tbl_sub.setItem(r, 0, name_item)
            
            self.tbl_sub.setItem(r, 1, QTableWidgetItem(s.code or "N/A"))
            
            type_item = QTableWidgetItem(s.subject_type)
            if s.subject_type == "Compulsory": type_item.setForeground(QColor("#10B981"))
            elif s.subject_type == "Optional": type_item.setForeground(QColor("#3B82F6"))
            else: type_item.setForeground(QColor("#8B5CF6"))
            self.tbl_sub.setItem(r, 2, type_item)
            
            btn_del = TableTextButton("Delete", icon_name="trash-2", variant="danger")
            btn_del.clicked.connect(lambda checked=False, sid=s.id: self.delete_subject(sid))
            self.tbl_sub.setCellWidget(r, 3, create_table_actions_cell([btn_del]))
            self.tbl_sub.setRowHeight(r, 48)

    def delete_subject(self, sid):
        if QMessageBox.question(self, "Confirm Deletion", "Are you sure you want to delete this subject?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            AcademicService.delete_subject(sid)
            self.refresh_all()

    # ==========================================
    # SUBJECT ASSIGNMENTS 
    # ==========================================
    def create_assignments_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(30, 30, 30, 30)
        
        box = ModernCard()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(40, 40, 40, 40)
        box_lay.setSpacing(14)
        
        icon = QLabel()
        icon.setPixmap(IconManager.get_pixmap("sliders", "#10B981", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("Universal Subject Linkage is Active")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #10B981; border: none; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = QLabel("All subjects are automatically linked and transmitting data to the <b>HR, Timetable, and Examination</b> modules.<br><br>You no longer need to manually link subjects to classes one by one. Teachers can be assigned to any subject globally across the institution.")
        desc.setStyleSheet("color: #475569; font-size: 15px; border: none; background: transparent; line-height: 1.6;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        
        box_lay.addStretch()
        box_lay.addWidget(icon)
        box_lay.addWidget(title)
        box_lay.addWidget(desc)
        box_lay.addStretch()
        
        lay.addWidget(box)
        return page