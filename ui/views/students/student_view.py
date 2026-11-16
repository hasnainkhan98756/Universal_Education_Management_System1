import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, 
                               QTabWidget, QFileDialog, QMessageBox, QAbstractItemView, QMenu, QTextEdit, QDateEdit, QScrollArea,
                               QCheckBox, QSpinBox, QFrame)
from PySide6.QtCore import Qt, QDate, QTimer
from PySide6.QtGui import QFont, QPixmap, QColor, QAction

from core.academic_service import AcademicService
from core.student_service import StudentService
from core.fee_service import FeeService 
from core.state_manager import app_state
from core.pdf_service import PDFGenerationService
from core.document_service import DocumentService
from core.promotion_service import PromotionService

from ui.views.students.student_profile_dialog import StudentProfileDialog
from ui.views.settings.numbering_settings_dialog import NumberingSettingsDialog
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, ModernButton, TableActionButton, TableTextButton,
    create_table_actions_cell, StatusBadge, SearchInput,
    style_modern_table, style_modern_tabs, SegmentedTabBar
)
from core.icon_manager import IconManager

class StudentView(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)
        
        self.header = PageHeader(
            title="Admissions & Students",
            subtitle="Student enrolment, directory, verification, and promotion",
            icon_name="users-2",
            icon_color="#2563EB",
            badge_bg="#EFF6FF"
        )
        
        btn_dev_settings = ModernButton("Numbering Formats", icon_name="settings", variant="secondary")
        btn_dev_settings.clicked.connect(self.open_numbering_settings)
        self.header.add_action_button(btn_dev_settings)
        
        main_layout.addWidget(self.header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_admission_tab(), IconManager.get("user-plus", "#2563EB", 16), "Admission Wizard")
        self.tabs.addTab(self.create_student_list_tab(), IconManager.get("users-2", "#2563EB", 16), "Student Directory")
        self.tabs.addTab(self.create_promotion_tab(), IconManager.get("graduation-cap", "#2563EB", 16), "Student Promotion")
        
        main_layout.addWidget(self.tabs)
        
        # UI Sync Triggers
        self.tabs.currentChanged.connect(self.on_tab_changed)
        app_state.subscribe_settings_change(self.load_academic_dropdowns)
        app_state.subscribe_data_changed(self.refresh_data)
        self.load_academic_dropdowns()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_data()

    def on_tab_changed(self, index):
        if index == 0:
            self.load_academic_dropdowns()
        elif index == 1: 
            self.load_academic_dropdowns()
            self.refresh_student_list()
        elif index == 2:
            self._promo_load_classes()

    def refresh_data(self):
        self.load_academic_dropdowns()
        curr = self.tabs.currentIndex()
        if curr == 0:
            pass
        elif curr == 1:
            self.refresh_student_list()
        elif curr == 2:
            self._promo_load_classes()
        if hasattr(self, 'tbl_students') and curr != 1:
            self.refresh_student_list()

    def refresh_all(self):
        self.refresh_data()

    def open_numbering_settings(self):
        dlg = NumberingSettingsDialog(self)
        dlg.exec()

    def _lbl(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #000000; font-weight: bold; background: transparent; border: none;")
        return lbl

    def _input(self):
        inp = QLineEdit()
        inp.setMinimumHeight(32)
        return inp

    def _combo(self, items):
        cb = QComboBox()
        cb.addItems(items)
        cb.setMinimumHeight(32)
        return cb

    def _spinbox(self):
        sb = QDoubleSpinBox()
        sb.setRange(0, 1000000)
        sb.setMinimumHeight(32)
        return sb

    def _date(self):
        de = QDateEdit(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setMinimumHeight(32)
        return de

    def _scrollable_tab(self, widget):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.setWidget(widget)
        return scroll

    def create_admission_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 10)
        
        self.wizard = QTabWidget()
        self.wizard.setStyleSheet("QTabBar::tab { padding: 4px 10px; font-weight: bold; font-size: 11px; }")
        self.wizard.currentChanged.connect(self.on_wizard_tab_changed)
        
        w1 = QWidget(); l1 = QFormLayout(w1)
        l1.setContentsMargins(14, 10, 14, 12); l1.setVerticalSpacing(8); l1.setHorizontalSpacing(14)
        self.adm_fname = self._input(); self.adm_lname = self._input(); self.adm_gender = self._combo(["Male", "Female", "Other"])
        self.adm_dob = self._date(); self.adm_bform = self._input(); self.adm_nat = self._input(); self.adm_rel = self._input()
        self.adm_bg = self._combo(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"])
        self.adm_pob = self._input()
        
        photo_row = QHBoxLayout()
        self.adm_photo_path = ""
        self.lbl_photo_name = QLabel("No photo selected")
        self.lbl_photo_name.setStyleSheet("color: #6B7280; font-size: 11px; border: none;")
        btn_photo = QPushButton("Browse Image")
        btn_photo.setObjectName("btn_secondary")
        btn_photo.setMinimumHeight(28)
        btn_photo.clicked.connect(self.browse_photo)
        photo_row.addWidget(btn_photo); photo_row.addWidget(self.lbl_photo_name); photo_row.addStretch()

        l1.addRow(self._lbl("First Name *"), self.adm_fname); l1.addRow(self._lbl("Last Name"), self.adm_lname)
        l1.addRow(self._lbl("Gender *"), self.adm_gender); l1.addRow(self._lbl("Date of Birth *"), self.adm_dob)
        l1.addRow(self._lbl("B-Form / CRC No."), self.adm_bform); l1.addRow(self._lbl("Nationality"), self.adm_nat)
        l1.addRow(self._lbl("Religion"), self.adm_rel); l1.addRow(self._lbl("Blood Group"), self.adm_bg)
        l1.addRow(self._lbl("Place of Birth"), self.adm_pob); l1.addRow(self._lbl("Student Photo"), photo_row)
        
        w2 = QWidget(); l2 = QFormLayout(w2)
        l2.setContentsMargins(14, 10, 14, 12); l2.setVerticalSpacing(8); l2.setHorizontalSpacing(14)
        self.adm_father = self._input(); self.adm_fcnic = self._input(); self.adm_focc = self._input(); self.adm_fphone = self._input()
        self.adm_mother = self._input(); self.adm_mcnic = self._input()
        self.adm_guard = self._input(); self.adm_grel = self._input(); self.adm_gcnic = self._input(); self.adm_inc = self._input()
        l2.addRow(self._lbl("Father's Name *"), self.adm_father); l2.addRow(self._lbl("Father's CNIC"), self.adm_fcnic)
        l2.addRow(self._lbl("Father's Occupation"), self.adm_focc); l2.addRow(self._lbl("Father's Mobile"), self.adm_fphone)
        l2.addRow(self._lbl("Mother's Name"), self.adm_mother); l2.addRow(self._lbl("Mother's CNIC"), self.adm_mcnic)
        l2.addRow(self._lbl("Guardian Name (if not Father)"), self.adm_guard); l2.addRow(self._lbl("Guardian Relationship"), self.adm_grel)
        l2.addRow(self._lbl("Guardian CNIC"), self.adm_gcnic); l2.addRow(self._lbl("Monthly Family Income"), self.adm_inc)

        # ── SIBLING INFORMATION ──
        self.adm_has_sibling = self._combo(["No", "Yes"])
        self.adm_sib_name = self._input()
        self.adm_sib_name.setPlaceholderText("Sibling Full Name")
        self.adm_sib_class = self._input()
        self.adm_sib_class.setPlaceholderText("e.g. Grade 7 - Section A")
        self.adm_sib_roll = self._input()
        self.adm_sib_roll.setPlaceholderText("Sibling Roll / System ID")

        def _toggle_sib(idx):
            is_y = (idx == 1)
            self.adm_sib_name.setEnabled(is_y)
            self.adm_sib_class.setEnabled(is_y)
            self.adm_sib_roll.setEnabled(is_y)
            if not is_y:
                self.adm_sib_name.clear()
                self.adm_sib_class.clear()
                self.adm_sib_roll.clear()
        self.adm_has_sibling.currentIndexChanged.connect(_toggle_sib)
        _toggle_sib(0)

        l2.addRow(self._lbl("Any Sibling in this School?"), self.adm_has_sibling)
        l2.addRow(self._lbl("Sibling's Full Name"), self.adm_sib_name)
        l2.addRow(self._lbl("Sibling's Class & Section"), self.adm_sib_class)
        l2.addRow(self._lbl("Sibling's Roll / Student ID"), self.adm_sib_roll)

        w3 = QWidget(); l3 = QFormLayout(w3)
        l3.setContentsMargins(14, 10, 14, 12); l3.setVerticalSpacing(8); l3.setHorizontalSpacing(14)
        self.adm_pschool = self._input(); self.adm_pclass = self._input(); self.adm_pexam = self._input()
        self.adm_psession = self._input(); self.adm_pgrade = self._input(); self.adm_tc = self._input(); self.adm_tcdate = self._date()
        l3.addRow(self._lbl("Previous School Name"), self.adm_pschool); l3.addRow(self._lbl("Previous Class"), self.adm_pclass)
        l3.addRow(self._lbl("Previous Examination"), self.adm_pexam); l3.addRow(self._lbl("Previous Session"), self.adm_psession)
        l3.addRow(self._lbl("Result / Grade"), self.adm_pgrade); l3.addRow(self._lbl("Transfer Certificate No."), self.adm_tc)
        l3.addRow(self._lbl("TC Issue Date"), self.adm_tcdate)

        w4 = QWidget(); l4 = QFormLayout(w4)
        l4.setContentsMargins(14, 10, 14, 12); l4.setVerticalSpacing(8); l4.setHorizontalSpacing(14)
        self.adm_address = self._input(); self.adm_city = self._input(); self.adm_dist = self._input()
        self.adm_phone = self._input(); self.adm_email = self._input()
        self.adm_em_name = self._input(); self.adm_em_rel = self._input(); self.adm_em_num = self._input()
        l4.addRow(self._lbl("Residential Address *"), self.adm_address); l4.addRow(self._lbl("City"), self.adm_city); l4.addRow(self._lbl("District"), self.adm_dist)
        l4.addRow(self._lbl("Primary Mobile No."), self.adm_phone); l4.addRow(self._lbl("Email Address"), self.adm_email)
        l4.addRow(self._lbl("Emergency Contact Person"), self.adm_em_name); l4.addRow(self._lbl("Emergency Relationship"), self.adm_em_rel)
        l4.addRow(self._lbl("Emergency Contact No."), self.adm_em_num)

        w5 = QWidget(); l5 = QFormLayout(w5)
        l5.setContentsMargins(14, 10, 14, 12); l5.setVerticalSpacing(8); l5.setHorizontalSpacing(14)
        self.adm_type = self._combo(["New Admission", "Transfer", "Re-Admission"]); self.adm_date = self._date()
        self.adm_class = self._combo([]); self.adm_class.currentIndexChanged.connect(self.update_sections_dropdown); self.adm_section = self._combo([])
        self.adm_number = self._input()
        
        # Fee Plan / Billing Cycle Selector
        self.adm_billing_cycle = self._combo(["Monthly Fee", "6-Month Package", "Annual Package"])
        self.adm_fee = self._spinbox(); self.adm_fee_6m = self._spinbox(); self.adm_fee_annual = self._spinbox(); self.adm_disc = self._spinbox()
        self.adm_billing_cycle.currentIndexChanged.connect(self._on_billing_cycle_changed)
        
        # Admission Fee & Payment Status
        self.adm_admission_fee = self._spinbox()
        self.adm_admission_fee_paid = QCheckBox("Admission Fee Paid at Admission Time")
        self.adm_admission_fee_paid.setStyleSheet("QCheckBox { font-weight: bold; color: #059669; font-size: 12px; }")

        l5.addRow(self._lbl("Admission Type"), self.adm_type); l5.addRow(self._lbl("Admission Date *"), self.adm_date)
        l5.addRow(self._lbl("Select Class *"), self.adm_class); l5.addRow(self._lbl("Select Section *"), self.adm_section)
        l5.addRow(self._lbl("Custom Admission No. (Optional)"), self.adm_number)
        l5.addRow(self._lbl("Billing Cycle / Fee Plan *"), self.adm_billing_cycle)
        l5.addRow(self._lbl("Base Monthly Fee (Rs)"), self.adm_fee)
        l5.addRow(self._lbl("6-Month Fee (Rs)"), self.adm_fee_6m)
        l5.addRow(self._lbl("Annual Fee (Rs)"), self.adm_fee_annual)
        l5.addRow(self._lbl("Fixed Monthly Discount (Rs)"), self.adm_disc)
        l5.addRow(self._lbl("Admission Fee (Rs)"), self.adm_admission_fee)
        l5.addRow(self._lbl("Admission Fee Status"), self.adm_admission_fee_paid)
        self._on_billing_cycle_changed()

        w6 = QWidget(); l6 = QFormLayout(w6)
        l6.setContentsMargins(14, 10, 14, 12); l6.setVerticalSpacing(8); l6.setHorizontalSpacing(14)
        self.adm_med = self._input(); self.adm_alg = self._input()
        l6.addRow(self._lbl("Any Medical Notes / Conditions"), self.adm_med)
        l6.addRow(self._lbl("Any Allergies"), self.adm_alg)
        
        w7 = QWidget(); l7 = QVBoxLayout(w7)
        self.lbl_review = QLabel("Click the tabs to fill data. Review will appear here.")
        self.lbl_review.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lbl_review.setStyleSheet("font-size: 13px; color: #000000;")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        content = QWidget(); c_lay = QVBoxLayout(content)
        c_lay.addWidget(self.lbl_review); c_lay.addStretch()
        scroll.setWidget(content); l7.addWidget(scroll)

        self.wizard.addTab(self._scrollable_tab(w1), "1. Student")
        self.wizard.addTab(self._scrollable_tab(w2), "2. Parent")
        self.wizard.addTab(self._scrollable_tab(w3), "3. Education")
        self.wizard.addTab(self._scrollable_tab(w4), "4. Contact")
        self.wizard.addTab(self._scrollable_tab(w5), "5. Admission Details")
        self.wizard.addTab(self._scrollable_tab(w6), "6. Medical")
        self.wizard.addTab(w7, "7. Review")
        layout.addWidget(self.wizard)

        btn_row = QHBoxLayout()
        btn_save = ModernButton("Save Admission & Auto-Generate Forms", icon_name="check", variant="success")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.process_admission)
        btn_row.addStretch(); btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        return page

    def on_wizard_tab_changed(self, index):
        if index == 6:
            adm_st = "Paid" if self.adm_admission_fee_paid.isChecked() else "Pending"
            adm_color = "#059669" if self.adm_admission_fee_paid.isChecked() else "#DC2626"
            sib_txt = "No"
            if self.adm_has_sibling.currentText() == "Yes":
                sib_txt = f"Yes ({self.adm_sib_name.text().strip()} - {self.adm_sib_class.text().strip()} - ID: {self.adm_sib_roll.text().strip()})"
            review_text = f"""
            <h3>Student Summary</h3>
            <b>Name:</b> {self.adm_fname.text()} {self.adm_lname.text()}<br>
            <b>DOB:</b> {self.adm_dob.date().toString("yyyy-MM-dd")} | <b>Gender:</b> {self.adm_gender.currentText()}<br>
            <b>Father:</b> {self.adm_father.text()} | <b>Contact:</b> {self.adm_phone.text()}<br>
            <b>Sibling in School:</b> {sib_txt}<br>
            <h3>Academic Placement & Fee Structure</h3>
            <b>Class:</b> {self.adm_class.currentText()} | <b>Section:</b> {self.adm_section.currentText()}<br>
            <b>Selected Fee Plan:</b> {self.adm_billing_cycle.currentText()}<br>
            <b>Monthly Fee:</b> Rs. {self.adm_fee.value():,.0f} | <b>6-Month Fee:</b> Rs. {self.adm_fee_6m.value():,.0f} | <b>Annual Fee:</b> Rs. {self.adm_fee_annual.value():,.0f}<br>
            <b>Discount:</b> Rs. {self.adm_disc.value():,.0f}<br>
            <b>Admission Fee:</b> Rs. {self.adm_admission_fee.value():,.0f} (<span style='color: {adm_color}; font-weight: bold;'>{adm_st}</span>)
            """
            self.lbl_review.setText(review_text)

    def create_student_list_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)
        
        self.subtab_bar = SegmentedTabBar([
            "All Students",
            "Active Enrolled",
            "Graduated Alumni",
            "Migrated / Transferred",
            "Dropouts & Suspended"
        ], initial_index=1)
        self.subtab_bar.tab_changed.connect(self._on_subtab_changed)
        layout.addWidget(self.subtab_bar)

        self.tbl_students = QTableWidget()
        self.tbl_students.setColumnCount(8)
        self.tbl_students.setHorizontalHeaderLabels(["Student ID", "Name", "Father's Name", "Class", "Section", "Pending Fee", "Status", "Actions"])
        self.tbl_students.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_students.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tbl_students.setColumnWidth(7, 130)
        self.tbl_students.verticalHeader().setDefaultSectionSize(48)
        self.tbl_students.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        style_modern_table(self.tbl_students)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        self.search_bar = SearchInput("Search by Name, ID, or Father's Name...")
        
        # Debounce search input by 250ms to prevent laggy multi-keystroke re-queries
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_student_list)
        self.search_bar.textChanged.connect(lambda _: self._search_timer.start())

        self.filter_batch = self._combo(["All Batches"]); self.filter_batch.currentIndexChanged.connect(self.refresh_student_list)
        self.filter_class = self._combo(["All Classes"]); self.filter_class.currentIndexChanged.connect(self.refresh_student_list)
        self.filter_status = self._combo(["All Status", "Active", "Graduated", "Migrated", "Suspended", "Dropout", "Inactive"]); self.filter_status.currentIndexChanged.connect(self._on_combo_status_changed)
        
        self.lbl_student_count = QLabel("0 Students")
        self.lbl_student_count.setStyleSheet("font-size: 12px; font-weight: bold; color: #374151; padding: 4px 10px; background: #F3F4F6; border: 1px solid #E5E7EB; border-radius: 6px;")

        lbl_b = QLabel("Batch:"); lbl_b.setStyleSheet("font-weight: 600; color: #4B5563;")
        lbl_c = QLabel("Class:"); lbl_c.setStyleSheet("font-weight: 600; color: #4B5563;")
        lbl_s = QLabel("Status:"); lbl_s.setStyleSheet("font-weight: 600; color: #4B5563;")

        top_row.addWidget(self.search_bar, stretch=3)
        top_row.addWidget(lbl_b); top_row.addWidget(self.filter_batch, stretch=1)
        top_row.addWidget(lbl_c); top_row.addWidget(self.filter_class, stretch=1)
        top_row.addWidget(lbl_s); top_row.addWidget(self.filter_status, stretch=1)
        top_row.addWidget(self.lbl_student_count)
        layout.addLayout(top_row); layout.addWidget(self.tbl_students)
        self.filter_status.setCurrentText("Active")
        return page

    def _on_subtab_changed(self, idx: int, text: str):
        if not hasattr(self, 'filter_status'): return
        self.filter_status.blockSignals(True)
        if text == "All Students":
            self.filter_status.setCurrentText("All Status")
        elif text == "Active Enrolled":
            self.filter_status.setCurrentText("Active")
        elif text == "Graduated Alumni":
            self.filter_status.setCurrentText("Graduated")
        elif text == "Migrated / Transferred":
            self.filter_status.setCurrentText("Migrated")
        elif text == "Dropouts & Suspended":
            self.filter_status.setCurrentText("Suspended")
        self.filter_status.blockSignals(False)
        self.refresh_student_list()

    def _on_combo_status_changed(self):
        if hasattr(self, 'subtab_bar') and hasattr(self, 'filter_status'):
            st = self.filter_status.currentText()
            self.subtab_bar.blockSignals(True)
            if st in ["All Status", "All"]:
                self.subtab_bar.set_current_index(0)
            elif st == "Active":
                self.subtab_bar.set_current_index(1)
            elif st == "Graduated":
                self.subtab_bar.set_current_index(2)
            elif st in ["Migrated", "Transferred"]:
                self.subtab_bar.set_current_index(3)
            elif st in ["Suspended", "Dropout"]:
                self.subtab_bar.set_current_index(4)
            self.subtab_bar.blockSignals(False)
        self.refresh_student_list()


    def browse_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Student Photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.adm_photo_path = file_path
            self.lbl_photo_name.setText(os.path.basename(file_path))

    def load_academic_dropdowns(self):
        active_session = app_state.get_setting("session", "Default")
        self.classes = AcademicService.get_classes(session_filter=active_session)
        
        prev_adm_cls = self.adm_class.currentData() if hasattr(self, 'adm_class') else None
        prev_filter_cls = self.filter_class.currentData() if hasattr(self, 'filter_class') else None

        self.adm_class.blockSignals(True)
        self.filter_class.blockSignals(True)
        self.adm_class.clear()
        self.filter_class.clear()
        self.filter_class.addItem("All Classes", "All")
        for c in self.classes:
            self.adm_class.addItem(c.name, c.id)
            self.filter_class.addItem(c.name, c.id)

        if prev_adm_cls is not None:
            idx = self.adm_class.findData(prev_adm_cls)
            if idx >= 0:
                self.adm_class.setCurrentIndex(idx)
            elif self.adm_class.count() > 0:
                self.adm_class.setCurrentIndex(0)
        elif self.adm_class.count() > 0:
            self.adm_class.setCurrentIndex(0)

        if prev_filter_cls is not None:
            idx = self.filter_class.findData(prev_filter_cls)
            if idx >= 0:
                self.filter_class.setCurrentIndex(idx)

        self.adm_class.blockSignals(False)
        self.filter_class.blockSignals(False)
        
        if hasattr(self, 'filter_batch'):
            self.filter_batch.blockSignals(True)
            prev_b = self.filter_batch.currentText()
            self.filter_batch.clear()
            self.filter_batch.addItem("All Batches")
            batches = StudentService.get_student_batches()
            for b in batches:
                self.filter_batch.addItem(b)
            if prev_b and prev_b in batches:
                self.filter_batch.setCurrentText(prev_b)
            self.filter_batch.blockSignals(False)

        self.update_sections_dropdown()

    def update_sections_dropdown(self):
        class_id = self.adm_class.currentData() if hasattr(self, 'adm_class') else None
        if class_id is None and hasattr(self, 'adm_class') and self.adm_class.count() > 0:
            self.adm_class.setCurrentIndex(0)
            class_id = self.adm_class.currentData()

        prev_sec_id = self.adm_section.currentData() if hasattr(self, 'adm_section') else None
        self.adm_section.blockSignals(True)
        self.adm_section.clear()
        if class_id:
            sections = AcademicService.get_sections(class_id)
            for s in sections:
                self.adm_section.addItem(s.name, s.id)
            if prev_sec_id is not None:
                idx = self.adm_section.findData(prev_sec_id)
                if idx >= 0:
                    self.adm_section.setCurrentIndex(idx)
                elif self.adm_section.count() > 0:
                    self.adm_section.setCurrentIndex(0)
            elif self.adm_section.count() > 0:
                self.adm_section.setCurrentIndex(0)
        self.adm_section.blockSignals(False)

    def _on_billing_cycle_changed(self):
        if not hasattr(self, 'adm_billing_cycle'):
            return
        cycle = self.adm_billing_cycle.currentText()
        if "Annual" in cycle:
            self.adm_fee_annual.setEnabled(True)
            self.adm_fee.setEnabled(False)
            self.adm_fee_6m.setEnabled(False)
        elif "6-Month" in cycle:
            self.adm_fee_6m.setEnabled(True)
            self.adm_fee.setEnabled(False)
            self.adm_fee_annual.setEnabled(False)
        else: # Monthly Fee
            self.adm_fee.setEnabled(True)
            self.adm_fee_6m.setEnabled(False)
            self.adm_fee_annual.setEnabled(False)

    def process_admission(self):
        if not self.adm_fname.text().strip():
            QMessageBox.warning(self, "Missing Data", "First Name is required."); self.wizard.setCurrentIndex(0); return
        if not self.adm_class.currentData() or not self.adm_section.currentData():
            QMessageBox.warning(self, "Missing Data", "Class and Section must be selected."); self.wizard.setCurrentIndex(4); return

        billing_cycle_selected = self.adm_billing_cycle.currentText()
        admission_fee_val = float(self.adm_admission_fee.value())
        admission_fee_paid_val = bool(self.adm_admission_fee_paid.isChecked())

        data = {
            "first_name": self.adm_fname.text(), "last_name": self.adm_lname.text(), "gender": self.adm_gender.currentText(),
            "dob": self.adm_dob.date().toString("yyyy-MM-dd"), "b_form": self.adm_bform.text(), "nationality": self.adm_nat.text(),
            "religion": self.adm_rel.text(), "blood_group": self.adm_bg.currentText(), "place_of_birth": self.adm_pob.text(),
            "father_name": self.adm_father.text(), "father_cnic": self.adm_fcnic.text(), "father_occ": self.adm_focc.text(), "father_phone": self.adm_fphone.text(),
            "mother_name": self.adm_mother.text(), "mother_cnic": self.adm_mcnic.text(),
            "guardian_name": self.adm_guard.text(), "guardian_relationship": self.adm_grel.text(), "guardian_cnic": self.adm_gcnic.text(), "family_income": self.adm_inc.text(),
            "previous_school": self.adm_pschool.text(), "previous_class": self.adm_pclass.text(), "previous_exam": self.adm_pexam.text(),
            "previous_session": self.adm_psession.text(), "previous_result": self.adm_pgrade.text(), "tc_number": self.adm_tc.text(), "tc_date": self.adm_tcdate.date().toString("yyyy-MM-dd"),
            "address": self.adm_address.text(), "city": self.adm_city.text(), "district": self.adm_dist.text(), "phone": self.adm_phone.text(), "email": self.adm_email.text(),
            "emergency_contact_person": self.adm_em_name.text(), "emergency_relationship": self.adm_em_rel.text(), "emergency_contact_number": self.adm_em_num.text(),
            "admission_type": self.adm_type.currentText(), "admission_date": self.adm_date.date().toString("yyyy-MM-dd"),
            "class_id": self.adm_class.currentData(), "section_id": self.adm_section.currentData(), "admission_number": self.adm_number.text(),
            "monthly_fee": self.adm_fee.value(),
            "six_month_fee": self.adm_fee_6m.value(),
            "annual_fee": self.adm_fee_annual.value(),
            "discount": self.adm_disc.value(),
            "admission_fee": admission_fee_val,
            "admission_fee_paid": admission_fee_paid_val,
            "billing_cycle": billing_cycle_selected,
            "sibling_info": (
                f"Name: {self.adm_sib_name.text().strip()} | Class: {self.adm_sib_class.text().strip()} | ID: {self.adm_sib_roll.text().strip()}"
                if self.adm_has_sibling.currentText() == "Yes" else "None"
            ),
            "medical_notes": self.adm_med.text(), "allergies": self.adm_alg.text()
        }

        success, msg, stu_id = StudentService.admit_student(data, self.adm_photo_path)
        
        if success:
            stu_obj = StudentService.get_student_by_system_id(stu_id)
            doc_type = "Admission Form"
            doc_num = DocumentService.generate_number(doc_type)

            # ── AUTOMATIC ENROLLMENT FEE VOUCHER GENERATION ──
            vouch_ok, vouch_msg, vouch_id = FeeService.generate_admission_voucher(
                student_id_or_sys_id=stu_id,
                billing_cycle=billing_cycle_selected,
                admission_fee=admission_fee_val,
                admission_fee_paid=admission_fee_paid_val
            )

            # ==========================================
            # COMPLETE PDF MAPPING DICTIONARY
            # Includes all 40+ fields required by the PDF
            # ==========================================
            adm_status_text = "Paid" if admission_fee_paid_val else "Pending"
            pdf_data = {
                # 1. Header & System Info
                "academic_session": app_state.get_setting("session", "Default"),
                "application_no": doc_num,
                "date": self.adm_date.date().toString("yyyy-MM-dd"),
                
                # 2. Student Info
                "student_name": f"{self.adm_fname.text()} {self.adm_lname.text()}".strip(),
                "dob": self.adm_dob.date().toString("yyyy-MM-dd"),
                "b_form": self.adm_bform.text(),
                "nationality": self.adm_nat.text(),
                "blood_group": self.adm_bg.currentText(),
                "gender": self.adm_gender.currentText(),
                "religion": self.adm_rel.text(),
                "place_of_birth": self.adm_pob.text(),
                "student_photo": self.adm_photo_path,
                
                # 3. Parent / Guardian
                "father_name": self.adm_father.text(),
                "mother_name": self.adm_mother.text(),
                "father_cnic": self.adm_fcnic.text(),
                "mother_cnic": self.adm_mcnic.text(),
                "guardian_name": self.adm_guard.text(),
                "relationship": self.adm_grel.text(),
                "occupation": self.adm_focc.text(),
                "monthly_income": self.adm_inc.text(),
                
                # 4. Contact
                "address": self.adm_address.text(),
                "city": self.adm_city.text(),
                "district": self.adm_dist.text(),
                "mobile_no": self.adm_fphone.text() if self.adm_fphone.text() else self.adm_phone.text(),
                "alt_contact": self.adm_phone.text(),
                "email": self.adm_email.text(),
                
                # 5. Admission Details
                "apply_class": self.adm_class.currentText(),
                "apply_section": self.adm_section.currentText(),
                "admission_type": self.adm_type.currentText(),
                "prev_school": self.adm_pschool.text(),
                "prev_class": self.adm_pclass.text(),
                "prev_school_address": "",
                
                # 6. Education Record
                "prev_class_school": self.adm_pschool.text(),
                "prev_class_session": self.adm_psession.text(),
                "prev_class_grade": self.adm_pgrade.text(),
                "prev_exam_school": self.adm_pschool.text(),
                "prev_exam_session": self.adm_psession.text(),
                "prev_exam_grade": self.adm_pexam.text(),
                "transfer_cert_no": self.adm_tc.text(),
                "transfer_cert_date": self.adm_tcdate.date().toString("yyyy-MM-dd"),
                
                # 7. Medical & Emergency
                "emergency_person": self.adm_em_name.text(),
                "emergency_contact": self.adm_em_num.text(),
                "emergency_relationship": self.adm_em_rel.text(),
                "medical_info": f"Notes: {self.adm_med.text()} | Allergies: {self.adm_alg.text()}",
                
                # 7.5 Sibling Details
                "sibling_studying": "Yes" if self.adm_has_sibling.currentText() == "Yes" else "No",
                "sibling_name": self.adm_sib_name.text().strip() if self.adm_has_sibling.currentText() == "Yes" else "-",
                "sibling_class": self.adm_sib_class.text().strip() if self.adm_has_sibling.currentText() == "Yes" else "-",
                "sibling_roll": self.adm_sib_roll.text().strip() if self.adm_has_sibling.currentText() == "Yes" else "-",
                "sibling_info": f"Name: {self.adm_sib_name.text().strip()} | Class: {self.adm_sib_class.text().strip()} | ID: {self.adm_sib_roll.text().strip()}" if self.adm_has_sibling.currentText() == "Yes" else "None",

                # 8. Declarations & Office Use
                "declaration_parent_name": self.adm_father.text() or self.adm_guard.text(),
                "declaration_date": self.adm_date.date().toString("yyyy-MM-dd"),
                "admission_status": "Accepted",
                "allotted_class_section": f"{self.adm_class.currentText()} - {self.adm_section.currentText()}",
                "admission_fee": f"{admission_fee_val:,.0f}" if admission_fee_val > 0 else "0",
                "admission_fee_status": adm_status_text,
                "billing_cycle": billing_cycle_selected,
                "monthly_fee": f"{self.adm_fee.value():,.0f}",
                "six_month_fee": f"{self.adm_fee_6m.value():,.0f}",
                "annual_fee": f"{self.adm_fee_annual.value():,.0f}",
                "discount": f"{self.adm_disc.value():,.0f}",
                "roll_no": stu_id
            }
            
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "user_data", "generated_docs", "Admissions")
            os.makedirs(output_dir, exist_ok=True)
            out_path = os.path.join(output_dir, f"{doc_num}_{stu_id}.pdf")
            
            pdf_success, pdf_msg = PDFGenerationService.generate_document(doc_type, pdf_data, out_path)
            
            info_msg = f"Student admitted successfully!\nSystem ID: {stu_id}"
            if vouch_ok:
                info_msg += f"\n\nFee Voucher Generated ({billing_cycle_selected}): {vouch_msg}"
                if admission_fee_val > 0:
                    info_msg += f"\nAdmission Fee: Rs. {admission_fee_val:,.0f} [{adm_status_text.upper()}]"
            if pdf_success:
                DocumentService.log_document(stu_obj.id, doc_type, doc_num, out_path)
                info_msg += f"\n\nAdmission Form generated safely:\n{out_path}"
                try:
                    os.startfile(out_path)
                except Exception as e:
                    QMessageBox.information(self, "PDF Ready", f"PDF saved to: {out_path}")
            
            QMessageBox.information(self, "Admission Successful", info_msg)
            self.reset_form()
            self.load_academic_dropdowns()
            self.refresh_student_list()
            self.tabs.setCurrentIndex(1)
        else:
            QMessageBox.critical(self, "Admission Failed", msg)
            if "CNIC" in msg or "B-Form" in msg:
                self.wizard.setCurrentIndex(0)
                self.adm_bform.setFocus()
                self.adm_bform.selectAll()

    def reset_form(self):
        self.adm_fname.clear(); self.adm_lname.clear(); self.adm_bform.clear(); self.adm_nat.clear(); self.adm_rel.clear(); self.adm_pob.clear()
        self.adm_father.clear(); self.adm_fcnic.clear(); self.adm_focc.clear(); self.adm_fphone.clear()
        self.adm_mother.clear(); self.adm_mcnic.clear(); self.adm_guard.clear(); self.adm_grel.clear(); self.adm_gcnic.clear(); self.adm_inc.clear()
        self.adm_pschool.clear(); self.adm_pclass.clear(); self.adm_pexam.clear(); self.adm_psession.clear(); self.adm_pgrade.clear(); self.adm_tc.clear()
        self.adm_address.clear(); self.adm_city.clear(); self.adm_dist.clear(); self.adm_phone.clear(); self.adm_email.clear()
        self.adm_em_name.clear(); self.adm_em_rel.clear(); self.adm_em_num.clear()
        self.adm_number.clear(); self.adm_fee.setValue(0.0); self.adm_fee_6m.setValue(0.0); self.adm_fee_annual.setValue(0.0); self.adm_disc.setValue(0.0)
        self.adm_billing_cycle.setCurrentIndex(0)
        self.adm_admission_fee.setValue(0.0)
        self.adm_admission_fee_paid.setChecked(False)
        self.adm_has_sibling.setCurrentIndex(0)
        self.adm_sib_name.clear()
        self.adm_sib_class.clear()
        self.adm_sib_roll.clear()
        self._on_billing_cycle_changed()
        self.adm_med.clear(); self.adm_alg.clear()
        self.adm_photo_path = ""; self.lbl_photo_name.setText("No photo selected")
        self.wizard.setCurrentIndex(0)

    def refresh_student_list(self):
        if not hasattr(self, 'tbl_students'): return
        search_txt = self.search_bar.text().strip()
        cls_id = self.filter_class.currentData()
        status = self.filter_status.currentText()
        if hasattr(self, 'subtab_bar') and self.subtab_bar.current_index() > 0:
            subtab_text = self.subtab_bar.current_text()
            if subtab_text != "All Students":
                status = subtab_text
        batch = self.filter_batch.currentText() if hasattr(self, 'filter_batch') else "All Batches"
        session_arg = None if batch == "All Batches" else batch
        
        for child in self.tbl_students.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_students.clearContents()

        students = StudentService.get_students(
            search_text=search_txt,
            class_id=cls_id,
            status_filter=status,
            session_filter=session_arg
        )
        total_matched = len(students)
        DISPLAY_LIMIT = 300
        if total_matched > DISPLAY_LIMIT:
            if hasattr(self, 'lbl_student_count'):
                self.lbl_student_count.setText(f"Showing {DISPLAY_LIMIT} of {total_matched:,} Students")
            display_students = students[:DISPLAY_LIMIT]
        else:
            if hasattr(self, 'lbl_student_count'):
                self.lbl_student_count.setText(f"{total_matched:,} Students")
            display_students = students

        # Batch-fetch pending balances in a single indexed query (eliminates N+1 queries)
        stu_ids = [stu.id for stu in display_students]
        pending_map = FeeService.get_students_pending_balances(stu_ids)

        self.tbl_students.setRowCount(len(display_students))
        for row, stu in enumerate(display_students):
            self.tbl_students.setItem(row, 0, QTableWidgetItem(stu.student_id))
            name = f"{stu.first_name} {stu.last_name or ''}".strip()
            self.tbl_students.setItem(row, 1, QTableWidgetItem(name))
            self.tbl_students.setItem(row, 2, QTableWidgetItem(stu.father_name or "-"))
            
            cls_name = stu.academic_class.name if stu.academic_class else "None"
            sec_name = stu.academic_section.name if stu.academic_section else "None"
            
            self.tbl_students.setItem(row, 3, QTableWidgetItem(cls_name))
            self.tbl_students.setItem(row, 4, QTableWidgetItem(sec_name))
            
            pending_amt = pending_map.get(stu.id, 0.0)
            pending_item = QTableWidgetItem(f"Rs. {pending_amt:,.0f}")
            if pending_amt > 0: pending_item.setForeground(QColor("#EF4444")); pending_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tbl_students.setItem(row, 5, pending_item)
            
            st = stu.status or "Active"
            if st == "Active":
                b_var = "success"
            elif st == "Graduated":
                b_var = "purple"
            elif st in ["Migrated", "Transferred"]:
                b_var = "warning"
            elif st == "Suspended":
                b_var = "danger"
            elif st in ["Dropout", "Dropouts"]:
                b_var = "orange"
            else:
                b_var = "secondary"

            badge = StatusBadge(st, variant=b_var)
            badge_box = QWidget()
            b_lay = QHBoxLayout(badge_box)
            b_lay.setContentsMargins(6, 4, 6, 4)
            b_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_lay.addWidget(badge)
            self.tbl_students.setCellWidget(row, 6, badge_box)
            
            btn_view = TableTextButton("View Profile", icon_name="eye", variant="secondary")
            btn_view.clicked.connect(lambda checked=False, s=stu.student_id: self.show_student_profile(s))
            self.tbl_students.setCellWidget(row, 7, create_table_actions_cell([btn_view]))
            self.tbl_students.setRowHeight(row, 48)

    def show_student_profile(self, student_id):
        dlg = StudentProfileDialog(student_id, self)
        dlg.exec()

    def focus_student(self, student_id, open_profile: bool = True):
        """Switches to Student Directory, searches and highlights the student, and optionally opens profile."""
        self.tabs.setCurrentIndex(1)  # Tab 1: Student Directory
        if hasattr(self, 'search_bar'):
            self.search_bar.setText(str(student_id))
            self.refresh_student_list()
        if open_profile:
            try:
                self.show_student_profile(student_id)
            except Exception as e:
                print(f"Error opening student profile: {e}")

    # ==========================================
    # STUDENT PROMOTION TAB
    # ==========================================
    def create_promotion_tab(self):
        w = QWidget()
        main = QVBoxLayout(w)
        main.setContentsMargins(0, 8, 0, 0)
        main.setSpacing(12)

        # Header info
        info_card = ModernCard()
        info_lay = QHBoxLayout(info_card)
        info_lay.setContentsMargins(14, 10, 14, 10)
        info_lay.setSpacing(10)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconManager.get_pixmap("graduation-cap", "#2563EB", 20))
        info_lay.addWidget(icon_lbl)
        info_text = QLabel("Year-End Promotion — Bulk promote students from one class/section to another.")
        info_text.setStyleSheet("color: #475569; font-size: 13px; font-weight: 600; background: transparent;")
        info_lay.addWidget(info_text)
        info_lay.addStretch()
        main.addWidget(info_card)

        # Source selection
        src_frame = ModernCard()
        src_lay = QHBoxLayout(src_frame)
        src_lay.setContentsMargins(14, 10, 14, 10)
        src_lay.setSpacing(12)
        src_lay.addWidget(QLabel("<b>From Class:</b>"))
        self.promo_combo_src_class = QComboBox()
        self.promo_combo_src_class.currentIndexChanged.connect(self._promo_load_sections)
        src_lay.addWidget(self.promo_combo_src_class)

        src_lay.addWidget(QLabel("<b>Section:</b>"))
        self.promo_combo_src_sec = QComboBox()
        src_lay.addWidget(self.promo_combo_src_sec)

        btn_load_stu = ModernButton("Load Students", icon_name="search", variant="primary")
        btn_load_stu.clicked.connect(self._promo_load_students)
        src_lay.addWidget(btn_load_stu)
        src_lay.addStretch()
        main.addWidget(src_frame)

        # Target selection
        tgt_frame = ModernCard()
        tgt_lay = QHBoxLayout(tgt_frame)
        tgt_lay.setContentsMargins(14, 10, 14, 10)
        tgt_lay.setSpacing(12)
        tgt_lay.addWidget(QLabel("<b>Promote To Class:</b>"))
        self.promo_combo_tgt_class = QComboBox()
        self.promo_combo_tgt_class.currentIndexChanged.connect(self._promo_load_target_sections)
        tgt_lay.addWidget(self.promo_combo_tgt_class)

        tgt_lay.addWidget(QLabel("<b>Section:</b>"))
        self.promo_combo_tgt_sec = QComboBox()
        tgt_lay.addWidget(self.promo_combo_tgt_sec)

        tgt_lay.addWidget(QLabel("<b>New Session:</b>"))
        self.promo_inp_session = QLineEdit()
        self.promo_inp_session.setPlaceholderText("e.g. 2025-2026")
        self.promo_inp_session.setText(app_state.get_setting("session", ""))
        tgt_lay.addWidget(self.promo_inp_session)
        tgt_lay.addStretch()
        main.addWidget(tgt_frame)

        # Student table
        self.promo_tbl = QTableWidget()
        self.promo_tbl.setColumnCount(5)
        self.promo_tbl.setHorizontalHeaderLabels(["Select", "Student ID", "Name", "Percentage", "Status"])
        self.promo_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.promo_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        style_modern_table(self.promo_tbl)
        main.addWidget(self.promo_tbl)

        # Bottom action bar
        bot = QHBoxLayout()
        bot.setSpacing(10)
        btn_all = ModernButton("Select All", icon_name="check", variant="secondary")
        btn_all.clicked.connect(self._promo_select_all)
        btn_none = ModernButton("Deselect All", icon_name="x", variant="secondary")
        btn_none.clicked.connect(self._promo_deselect_all)
        btn_promote = ModernButton("Promote Selected Students", icon_name="arrow-up-right", variant="success")
        btn_promote.setFixedHeight(36)
        btn_promote.clicked.connect(self._promo_execute)
        
        bot.addWidget(btn_all)
        bot.addWidget(btn_none)
        bot.addStretch()
        bot.addWidget(btn_promote)
        main.addLayout(bot)
        return w

    def _promo_load_classes(self):
        data = PromotionService.get_all_classes_with_sections()
        self._promo_class_data = data
        for combo in [self.promo_combo_src_class, self.promo_combo_tgt_class]:
            combo.blockSignals(True); combo.clear()
            for cls, _ in data:
                combo.addItem(cls.name, cls.id)
            combo.blockSignals(False)
        self._promo_load_sections()
        self._promo_load_target_sections()

    def _promo_load_sections(self):
        if not hasattr(self, '_promo_class_data'): return
        cid = self.promo_combo_src_class.currentData()
        self.promo_combo_src_sec.clear()
        for cls, secs in self._promo_class_data:
            if cls.id == cid:
                for sec in secs:
                    self.promo_combo_src_sec.addItem(sec.name, sec.id)
                break

    def _promo_load_target_sections(self):
        if not hasattr(self, '_promo_class_data'): return
        cid = self.promo_combo_tgt_class.currentData()
        self.promo_combo_tgt_sec.clear()
        for cls, secs in self._promo_class_data:
            if cls.id == cid:
                for sec in secs:
                    self.promo_combo_tgt_sec.addItem(sec.name, sec.id)
                break

    def _promo_load_students(self):
        cid = self.promo_combo_src_class.currentData()
        sid = self.promo_combo_src_sec.currentData()
        if not cid or not sid:
            QMessageBox.warning(self,"Error","Select source class and section first."); return
        students = PromotionService.get_students_for_promotion(cid, sid)
        self.promo_tbl.setRowCount(len(students))
        self._promo_students = students
        for r, stu in enumerate(students):
            chk = QCheckBox(); chk.setChecked(True)
            chk_w = QWidget(); cl = QHBoxLayout(chk_w); cl.setContentsMargins(8,0,0,0); cl.addWidget(chk)
            self.promo_tbl.setCellWidget(r, 0, chk_w)
            self.promo_tbl.setItem(r, 1, QTableWidgetItem(stu["student_id"]))
            self.promo_tbl.setItem(r, 2, QTableWidgetItem(stu["name"]))
            pct = stu["percentage"]
            pct_text = f"{pct}%" if pct is not None else "No marks"
            pct_item = QTableWidgetItem(pct_text)
            if pct is not None and pct < 40:
                pct_item.setForeground(QColor("#DC2626"))
            elif pct is not None:
                pct_item.setForeground(QColor("#16A34A"))
            self.promo_tbl.setItem(r, 3, pct_item)
            status = "Pass" if (pct is not None and pct >= 40) else ("Fail" if pct is not None else "No Data")
            st_item = QTableWidgetItem(status)
            st_item.setForeground(QColor("#16A34A" if status == "Pass" else "#DC2626"))
            self.promo_tbl.setItem(r, 4, st_item)

    def _promo_select_all(self):
        for r in range(self.promo_tbl.rowCount()):
            w = self.promo_tbl.cellWidget(r, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk: chk.setChecked(True)

    def _promo_deselect_all(self):
        for r in range(self.promo_tbl.rowCount()):
            w = self.promo_tbl.cellWidget(r, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk: chk.setChecked(False)

    def _promo_execute(self):
        if not hasattr(self, '_promo_students') or not self._promo_students:
            QMessageBox.warning(self,"No Data","Load students first."); return
        tgt_class = self.promo_combo_tgt_class.currentData()
        tgt_sec   = self.promo_combo_tgt_sec.currentData()
        new_sess  = self.promo_inp_session.text().strip()
        if not tgt_class or not tgt_sec:
            QMessageBox.warning(self,"Error","Select target class and section."); return
        if not new_sess:
            QMessageBox.warning(self,"Error","Enter the new academic session (e.g. 2025-2026)."); return

        selected_ids = []
        for r in range(self.promo_tbl.rowCount()):
            w = self.promo_tbl.cellWidget(r, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    selected_ids.append(self._promo_students[r]["id"])

        if not selected_ids:
            QMessageBox.warning(self,"Nothing Selected","No students selected for promotion."); return

        reply = QMessageBox.question(self,"Confirm Promotion",
            f"Promote {len(selected_ids)} student(s) to the selected class with session '{new_sess}'?\n\nThis cannot be undone.")
        if reply != QMessageBox.StandardButton.Yes: return

        ok, msg = PromotionService.promote_students(selected_ids, tgt_class, tgt_sec, new_sess)
        if ok:
            QMessageBox.information(self, "Promoted", msg)
            self.promo_tbl.setRowCount(0)
            self._promo_students = []
            self.refresh_student_list()
        else:
            QMessageBox.critical(self,"Error", msg)
