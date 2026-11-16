import os
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QTabWidget, QMessageBox, QWidget, QFormLayout, QLineEdit, 
                               QAbstractItemView, QScrollArea, QComboBox, QDateEdit,
                               QFileDialog, QInputDialog, QDoubleSpinBox)
from PySide6.QtCore import Qt, QDate, QUrl
from PySide6.QtGui import QDesktopServices

from core.student_service import StudentService
from core.fee_service import FeeService
from core.attendance_service import AttendanceService
from core.document_service import DocumentService
from core.pdf_service import PDFGenerationService
from core.data_resolver import DataResolverService
from core.icon_manager import IconManager
from ui.components.stitch_widgets import (
    ModernCard, ModernButton, StatusBadge, style_modern_table, style_modern_tabs
)
from ui.components.loading_widgets import show_print_loading

class IntelligentDocumentDialog(QDialog):
    def __init__(self, document_title, field_definitions, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Generate {document_title}")
        self.setMinimumWidth(450)
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; } 
            QLabel { color: #111827; font-weight: bold; } 
            QLineEdit, QComboBox, QDateEdit { padding: 8px; border: 1px solid #D1D5DB; border-radius: 4px; background: white; }
        """)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<h3>Document-Specific Information</h3><p style='color:#4B5563;'>Student database information will be loaded automatically.</p>"))
        
        self.form = QFormLayout()
        self.inputs = {}
        
        for field in field_definitions:
            label = field["label"]
            key = field["key"]
            f_type = field.get("type", "text")
            
            if f_type == "combo":
                inp = QComboBox()
                inp.addItems(field.get("options", []))
            elif f_type == "date":
                inp = QDateEdit()
                inp.setCalendarPopup(True)
                inp.setDate(QDate.currentDate())
            else:
                inp = QLineEdit()
                
            self.inputs[key] = (inp, f_type)
            self.form.addRow(f"{label}:", inp)
            
        layout.addLayout(self.form)
        
        btn = QPushButton("Generate Final PDF")
        btn.setStyleSheet("background-color: #10B981; color: white; padding: 12px; font-weight: bold; border-radius: 6px; border: none; margin-top: 10px;")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
        
    def get_data(self):
        data = {}
        for key, (widget, f_type) in self.inputs.items():
            if f_type == "combo":
                val = widget.currentText()
            elif f_type == "date":
                val = widget.date().toString("yyyy-MM-dd")
            else:
                val = widget.text().strip()
                
            data[f"document.{key}"] = val
        return data

class EditStudentProfileDialog(QDialog):
    def __init__(self, student, parent=None):
        super().__init__(parent)
        self.student = student
        self.setWindowTitle(f"Edit Student — {student.name} ({student.student_id})")
        self.setMinimumWidth(520)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QLabel { color: #1E293B; font-weight: 600; font-size: 12px; }
            QLineEdit, QDoubleSpinBox { padding: 6px 10px; border: 1px solid #CBD5E1; border-radius: 6px; background: white; font-size: 13px; }
            QLineEdit:focus, QDoubleSpinBox:focus { border-color: #3B82F6; }
        """)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        
        hdr = QLabel(f"<h3>Edit Student Information & Fee Structure</h3>")
        lay.addWidget(hdr)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        form = QFormLayout(container)
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(14)
        
        self.inp_fname = QLineEdit(student.first_name or "")
        self.inp_lname = QLineEdit(student.last_name or "")
        self.inp_phone = QLineEdit(student.phone or "")
        self.inp_bform = QLineEdit(student.b_form or "")
        self.inp_addr = QLineEdit(student.current_address or "")
        
        self.sp_monthly = QDoubleSpinBox(); self.sp_monthly.setRange(0, 10000000); self.sp_monthly.setValue(float(student.monthly_fee or 0.0))
        self.sp_6m = QDoubleSpinBox(); self.sp_6m.setRange(0, 10000000); self.sp_6m.setValue(float(getattr(student, 'six_month_fee', 0.0) or 0.0))
        self.sp_annual = QDoubleSpinBox(); self.sp_annual.setRange(0, 10000000); self.sp_annual.setValue(float(getattr(student, 'annual_fee', 0.0) or 0.0))
        self.sp_disc = QDoubleSpinBox(); self.sp_disc.setRange(0, 10000000); self.sp_disc.setValue(float(student.discount or 0.0))
        
        form.addRow("First Name *:", self.inp_fname)
        form.addRow("Last Name:", self.inp_lname)
        form.addRow("Contact Phone:", self.inp_phone)
        form.addRow("B-Form / CRC:", self.inp_bform)
        form.addRow("Address:", self.inp_addr)
        form.addRow("Base Monthly Fee (Rs):", self.sp_monthly)
        form.addRow("6-Month Fee (Rs):", self.sp_6m)
        form.addRow("Annual Fee (Rs):", self.sp_annual)
        form.addRow("Monthly Discount (Rs):", self.sp_disc)
        
        scroll.setWidget(container)
        lay.addWidget(scroll)
        
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("padding: 8px 16px; border-radius: 6px; background: #E2E8F0; color: #334155; font-weight: 600;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Save Changes")
        btn_save.setStyleSheet("padding: 8px 20px; border-radius: 6px; background: #2563EB; color: white; font-weight: 700;")
        btn_save.clicked.connect(self.save_data)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        lay.addLayout(btn_box)

    def save_data(self):
        if not self.inp_fname.text().strip():
            QMessageBox.warning(self, "Validation Error", "First Name cannot be empty.")
            return
            
        data = {
            "first_name": self.inp_fname.text().strip(),
            "last_name": self.inp_lname.text().strip(),
            "phone": self.inp_phone.text().strip(),
            "b_form": self.inp_bform.text().strip(),
            "current_address": self.inp_addr.text().strip(),
            "monthly_fee": self.sp_monthly.value(),
            "six_month_fee": self.sp_6m.value(),
            "annual_fee": self.sp_annual.value(),
            "discount": self.sp_disc.value()
        }
        success, msg = StudentService.update_student(self.student.id, data)
        if success:
            QMessageBox.information(self, "Success", "Student record updated successfully.")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", msg)


class StudentProfileDialog(QDialog):
    def __init__(self, system_id, parent=None):
        super().__init__(parent)
        self.student = StudentService.get_student_by_system_id(system_id)
        if not self.student:
            self.setWindowTitle("Student Profile - Not Found")
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel(f"<h3>Student Record Not Found</h3><p>No student record matches ID: <b>{system_id}</b></p>"))
            return

        self.setWindowTitle(f"Unified Student Profile: {self.student.first_name}")
        self.setMinimumSize(950, 650)
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        header = QHBoxLayout()
        self.name_lbl = QLabel(f"{self.student.first_name} {self.student.last_name or ''}".strip())
        self.name_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #0F172A;")
        self.id_lbl = QLabel(f"ID: {self.student.student_id}")
        self.id_lbl.setStyleSheet("font-size: 15px; color: #64748B; font-weight: 700; margin-left: 10px;")
        
        self.batch_lbl = QLabel(f"Batch: {self.student.academic_session or 'Default'}")
        self.batch_lbl.setStyleSheet("font-size: 12px; color: #1E40AF; background: #DBEAFE; font-weight: 700; padding: 4px 10px; border-radius: 6px; margin-left: 10px;")
        
        header.addWidget(self.name_lbl)
        header.addWidget(self.id_lbl)
        header.addWidget(self.batch_lbl)
        header.addStretch()

        # Edit Profile Button
        btn_edit_profile = ModernButton("Edit Profile", icon_name="edit-3", variant="primary")
        btn_edit_profile.setFixedHeight(30)
        btn_edit_profile.clicked.connect(self.open_edit_profile)
        header.addWidget(btn_edit_profile)

        # Lifecycle Status Selector
        header.addWidget(QLabel("<b>Lifecycle Status:</b>"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Active", "Graduated", "Migrated", "Suspended", "Dropout", "Inactive"])
        if self.student.status in ["Active", "Graduated", "Migrated", "Suspended", "Dropout", "Inactive"]:
            self.combo_status.setCurrentText(self.student.status)
        elif self.student.status == "Transferred":
            self.combo_status.setCurrentText("Migrated")
        elif self.student.status == "Dropouts":
            self.combo_status.setCurrentText("Dropout")
        
        btn_update_status = ModernButton("Update Status", icon_name="refresh-cw", variant="secondary")
        btn_update_status.setFixedHeight(30)
        btn_update_status.clicked.connect(self.change_student_status)
        header.addWidget(self.combo_status)
        header.addWidget(btn_update_status)

        layout.addLayout(header)
        
        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)
        self.overview_tab_idx = self.tabs.addTab(self.create_overview_tab(), IconManager.get("user", "#2563EB", 16), "Overview & Data")
        self.tabs.addTab(self.create_documents_tab(), IconManager.get("file-text", "#2563EB", 16), "Documents & Certificates")
        layout.addWidget(self.tabs)

    def open_edit_profile(self):
        dlg = EditStudentProfileDialog(self.student, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.student = StudentService.get_student_by_system_id(self.student.student_id)
            self.refresh_profile()

    def refresh_profile(self):
        if not self.student:
            return
        self.name_lbl.setText(f"{self.student.first_name} {self.student.last_name or ''}".strip())
        self.batch_lbl.setText(f"Batch: {self.student.academic_session or 'Default'}")
        if self.student.status in ["Active", "Graduated", "Migrated", "Suspended", "Dropout", "Inactive"]:
            self.combo_status.setCurrentText(self.student.status)
        # Refresh overview tab
        new_overview = self.create_overview_tab()
        self.tabs.removeTab(self.overview_tab_idx)
        self.overview_tab_idx = self.tabs.insertTab(0, new_overview, IconManager.get("user", "#2563EB", 16), "Overview & Data")
        self.tabs.setCurrentIndex(0)

    def change_student_status(self):
        new_status = self.combo_status.currentText()
        success, msg = StudentService.update_student_status(self.student.student_id, new_status)
        if success:
            self.student = StudentService.get_student_by_system_id(self.student.student_id)
            self.refresh_profile()
            QMessageBox.information(self, "Status Updated", f"Student lifecycle status updated to: {new_status}")
        else:
            QMessageBox.critical(self, "Update Failed", msg)

    def create_overview_tab(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20, 20, 20, 20)
        
        m_fee = getattr(self.student, 'monthly_fee', 0.0) or 0.0
        s_fee = getattr(self.student, 'six_month_fee', 0.0) or 0.0
        a_fee = getattr(self.student, 'annual_fee', 0.0) or 0.0
        disc = getattr(self.student, 'discount', 0.0) or 0.0
        
        info_txt = f"""
        <table style='font-size: 14px; color: black; width: 100%; border-spacing: 6px;'>
        <tr><td><b>Father's Name:</b> {self.student.father_name or '-'}</td><td><b>Father CNIC:</b> {getattr(self.student, 'father_cnic', '-')}</td></tr>
        <tr><td><b>Class:</b> {self.student.academic_class.name if self.student.academic_class else '-'}</td><td><b>Section:</b> {self.student.academic_section.name if self.student.academic_section else '-'}</td></tr>
        <tr><td><b>Contact:</b> {self.student.phone or '-'}</td><td><b>B-Form/CRC:</b> {self.student.b_form or '-'}</td></tr>
        <tr><td><b>Admission Date:</b> {self.student.admission_date or '-'}</td><td><b>Address:</b> {self.student.current_address or '-'}</td></tr>
        <tr><td><b>Previous School:</b> {self.student.previous_school or '-'}</td><td><b>Blood Group:</b> {self.student.blood_group or '-'}</td></tr>
        <tr><td colspan='2' style='border-top: 1px solid #CBD5E1; padding-top: 6px;'></td></tr>
        <tr><td><b>Monthly Fee:</b> <span style='color:#1E40AF; font-weight:bold;'>Rs. {m_fee:,.0f}</span></td><td><b>Monthly Discount:</b> <span style='color:#059669; font-weight:bold;'>Rs. {disc:,.0f}</span></td></tr>
        <tr><td><b>6-Month Fee:</b> <span style='color:#1E40AF; font-weight:bold;'>Rs. {s_fee:,.0f}</span></td><td><b>Annual Fee:</b> <span style='color:#1E40AF; font-weight:bold;'>Rs. {a_fee:,.0f}</span></td></tr>
        </table>
        """
        lay.addWidget(QLabel(info_txt))
        lay.addWidget(QLabel("<br><b style='color:#1D4ED8; font-size:16px;'>Live Sync Analytics</b>"))
        pending_fee = FeeService.get_student_pending_balance(self.student.id)
        att_stats = AttendanceService.get_student_attendance_summary(self.student.id)
        
        stats_txt = f"""
        <b style='color:red;'>Total Pending Fees:</b> <span style='color:red;'>Rs. {pending_fee:,.0f}</span><br><br>
        <b style='color:black;'>Total Days Present:</b> <span style='color:green;'>{att_stats['present']}</span><br>
        <b style='color:black;'>Total Days Absent:</b> <span style='color:red;'>{att_stats['absent']}</span><br>
        <b style='color:black;'>Overall Attendance:</b> <span style='color:blue;'>{att_stats['percentage']:.1f}%</span>
        """
        s_lbl = QLabel(stats_txt); s_lbl.setStyleSheet("font-size: 14px;")
        lay.addWidget(s_lbl); lay.addStretch()
        scroll.setWidget(w)
        return scroll

    def create_documents_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(20, 20, 20, 20)
        # Row 1 of Certificates: Core Academic Documents
        btn_lay1 = QHBoxLayout()
        btn_upload = ModernButton("Upload Student File", icon_name="upload", variant="primary")
        btn_upload.setFixedHeight(34)
        btn_upload.clicked.connect(self.upload_student_document)
        btn_lay1.addWidget(btn_upload)

        btn_slc = QPushButton("School Leaving")
        btn_slc.clicked.connect(lambda: self.trigger_cert("School Leaving Certificate", [
            {"label": "Class at Time of Leaving", "key": "class_at_time_of_leaving", "type": "text"},
            {"label": "Date of Leaving", "key": "date_of_leaving", "type": "date"},
            {"label": "Last Academic Session", "key": "last_academic_session", "type": "text"},
            {"label": "Reason for Leaving", "key": "reason_for_leaving", "type": "text"},
            {"label": "Conduct", "key": "conduct", "type": "combo", "options": ["Excellent", "Good", "Satisfactory"]},
            {"label": "Academic Performance", "key": "academic_performance", "type": "combo", "options": ["Excellent", "Good", "Satisfactory", "Poor"]},
            {"label": "Purpose", "key": "purpose", "type": "text"}
        ]))
        
        btn_char = QPushButton("Character Cert")
        btn_char.clicked.connect(lambda: self.trigger_cert("Character Certificate", [
            {"label": "Character", "key": "character", "type": "combo", "options": ["Excellent", "Good", "Satisfactory"]},
            {"label": "Conduct", "key": "conduct", "type": "combo", "options": ["Excellent", "Good", "Satisfactory"]},
            {"label": "Discipline", "key": "discipline", "type": "combo", "options": ["Excellent", "Good", "Satisfactory"]},
            {"label": "Attendance", "key": "attendance", "type": "combo", "options": ["Regular", "Irregular"]},
            {"label": "General Behavior", "key": "general_behavior", "type": "text"},
            {"label": "Purpose", "key": "purpose", "type": "text"}
        ]))
        
        btn_eng = QPushButton("English Prof.")
        btn_eng.clicked.connect(lambda: self.trigger_cert("English Proficiency", [
            {"label": "Listening Level", "key": "listening_level", "type": "combo", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"label": "Speaking Level", "key": "speaking_level", "type": "combo", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"label": "Reading Level", "key": "reading_level", "type": "combo", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"label": "Writing Level", "key": "writing_level", "type": "combo", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"label": "Grammar Level", "key": "grammar_level", "type": "combo", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"label": "Vocabulary Level", "key": "vocabulary_level", "type": "combo", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"label": "Overall Proficiency", "key": "overall_english_proficiency", "type": "text"},
            {"label": "Medium of Instruction", "key": "medium_of_instruction", "type": "text"},
            {"label": "Overall Level (Checkbox)", "key": "overall_level", "type": "combo", "options": ["Beginner", "Elementary", "Intermediate", "Upper-Intermediate", "Advanced"]}
        ]))

        btn_id = QPushButton("ID Card")
        btn_id.clicked.connect(lambda: self.trigger_cert("Student ID Card", [
            {"label": "Valid Until", "key": "valid_until", "type": "date"}
        ]))

        btn_bonafide = QPushButton("Bonafide Cert")
        btn_bonafide.clicked.connect(lambda: self.trigger_cert("Bonafide Certificate", [
            {"label": "Purpose / Submitting To", "key": "purpose", "type": "text"}
        ]))

        for b in [btn_slc, btn_char, btn_eng, btn_id, btn_bonafide]:
            b.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; padding: 7px 10px; border-radius: 4px; border: none;")
            btn_lay1.addWidget(b)
        lay.addLayout(btn_lay1)

        # Row 2 of Certificates: Specialized & Financial Certificates
        btn_lay2 = QHBoxLayout()

        btn_merit = QPushButton("Merit / Excellence")
        btn_merit.clicked.connect(lambda: self.trigger_cert("Merit Certificate", [
            {"label": "Examination / Assessment Name", "key": "exam_name", "type": "text"},
            {"label": "Position / Rank Secured", "key": "position", "type": "combo", "options": ["1st Position / Distinct Honors", "2nd Position", "3rd Position", "Top 5% Merit Honors", "Special Distinction"]},
            {"label": "Grade / Marks Percentage", "key": "marks_obtained", "type": "text"},
            {"label": "Commendation Area", "key": "distinction_area", "type": "text"}
        ]))

        btn_att = QPushButton("Attendance Cert")
        btn_att.clicked.connect(lambda: self.trigger_cert("Attendance Certificate", []))

        btn_sports = QPushButton("Sports & Co-Curricular")
        btn_sports.clicked.connect(lambda: self.trigger_cert("Sports Certificate", [
            {"label": "Competition / Tournament Name", "key": "event_name", "type": "text"},
            {"label": "Position / Award Secured", "key": "position_secured", "type": "combo", "options": ["1st Place / Gold Medalist", "2nd Place / Silver Medalist", "3rd Place / Bronze Medalist", "Best Player / MVP", "Participation of Honor"]},
            {"label": "Activity Type / Category", "key": "activity_type", "type": "combo", "options": ["Athletics & Track Events", "Cricket / Football / Basketball", "Debates & Declamation", "Science & Robotics Exhibition", "Arts & Culture"]},
            {"label": "Event Date", "key": "event_date", "type": "date"}
        ]))

        btn_fee_cert = QPushButton("Fee Structure & No Dues")
        btn_fee_cert.clicked.connect(lambda: self.trigger_cert("Fee Structure & No Dues Certificate", [
            {"label": "Calculation & Billing Basis", "key": "fee_basis", "type": "combo", "options": ["Monthly", "6-Month", "Annual"]}
        ]))

        for b in [btn_merit, btn_att, btn_sports, btn_fee_cert]:
            b.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 7px 10px; border-radius: 4px; border: none;")
            btn_lay2.addWidget(b)
        lay.addLayout(btn_lay2)
        lay.addWidget(QLabel("<br><b style='color:#0F172A; font-size:14px;'>Student Documents & Archive Records</b>"))
        
        self.doc_table = QTableWidget()
        self.doc_table.setColumnCount(5)
        self.doc_table.setHorizontalHeaderLabels(["Date", "Source", "Document Title", "Type / Ref", "Action"])
        self.doc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.doc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.doc_table.setColumnWidth(0, 110)
        self.doc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.doc_table.setColumnWidth(1, 100)
        self.doc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.doc_table.setColumnWidth(4, 110)
        self.doc_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        style_modern_table(self.doc_table)
        lay.addWidget(self.doc_table)
        
        self.refresh_doc_history()
        return w

    def refresh_doc_history(self):
        docs = DocumentService.get_student_documents(self.student.id)
        self.doc_table.setRowCount(len(docs))
        for r, d in enumerate(docs):
            self.doc_table.setItem(r, 0, QTableWidgetItem(d.get("date", "-")))
            
            src = d.get("type", "Generated")
            badge = StatusBadge(src, variant="purple" if src == "Generated" else "success")
            bbox = QWidget()
            blay = QHBoxLayout(bbox); blay.setContentsMargins(4, 2, 4, 2); blay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            blay.addWidget(badge)
            self.doc_table.setCellWidget(r, 1, bbox)
            
            self.doc_table.setItem(r, 2, QTableWidgetItem(d.get("title", "-")))
            self.doc_table.setItem(r, 3, QTableWidgetItem(d.get("doc_number", "-")))
            
            fpath = d.get("file_path", "")
            b = ModernButton("Open", icon_name="external-link", variant="secondary")
            b.setFixedHeight(28)
            b.clicked.connect(lambda checked=False, p=fpath: QDesktopServices.openUrl(QUrl.fromLocalFile(p)) if (p and os.path.exists(p)) else QMessageBox.warning(self, "Error", "Document file moved or deleted."))
            
            box = QWidget()
            box_l = QHBoxLayout(box)
            box_l.setContentsMargins(4, 2, 4, 2)
            box_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_l.addWidget(b)
            self.doc_table.setCellWidget(r, 4, box)
            self.doc_table.setRowHeight(r, 44)

    def upload_student_document(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Upload Document for {self.student.first_name}", "",
            "Documents (*.pdf *.png *.jpg *.jpeg *.docx *.xlsx *.doc)"
        )
        if not file_path:
            return

        default_title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
        title, ok = QInputDialog.getText(
            self, "Document Title", "Enter title or description (e.g., B-Form Scan, Birth Certificate):",
            text=default_title
        )
        if not ok or not title.strip():
            return

        success, msg = DocumentService.upload_managed_document(
            source_file_path=file_path,
            title=title.strip(),
            category="Student Records",
            entity_type="Student",
            entity_id=self.student.id,
            description=f"Attached to student {self.student.first_name} ({self.student.student_id})"
        )
        if success:
            QMessageBox.information(self, "Success", "Student document uploaded and linked successfully!")
            self.refresh_doc_history()
        else:
            QMessageBox.critical(self, "Upload Failed", msg)

    def trigger_cert(self, doc_type, extra_fields):
        extra_data = {}
        if extra_fields:
            dlg = IntelligentDocumentDialog(doc_type, extra_fields, self)
            if not dlg.exec(): return
            extra_data = dlg.get_data()

        # Authoritative resolver routing
        doc_type_lower = doc_type.lower()
        if "fee structure" in doc_type_lower or "no dues" in doc_type_lower:
            fee_basis = extra_data.get("document.fee_basis", "Monthly")
            data = DataResolverService.get_student_fee_structure_data(self.student.student_id, basis=fee_basis)
        elif "attendance" in doc_type_lower:
            data = DataResolverService.get_student_attendance_cert_data(self.student.student_id)
        else:
            data = DataResolverService.get_student_data(self.student.student_id)

        data.update(extra_data)
        
        doc_num = DocumentService.generate_number(doc_type)
        data["document.certificate_number"] = doc_num
        data["document.date_of_issue"] = datetime.now().strftime("%Y-%m-%d")
        
        app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        output_dir = os.path.join(app_root, "user_data", "generated_docs", doc_type.replace(" ", "_"))
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"{doc_num}_{self.student.first_name}.pdf")
        
        with show_print_loading(self, title=f"Generating {doc_type}...", subtitle=f"Rendering document for {self.student.first_name}"):
            success, msg = PDFGenerationService.generate_document(doc_type, data, out_path)
        
        if success:
            DocumentService.log_document(self.student.id, doc_type, doc_num, out_path)
            
            # Catch the missing image warning
            if "Warning:" in msg:
                QMessageBox.warning(self, "Generated with Warnings", msg)
            else:
                QMessageBox.information(self, "Success", f"Document {doc_num} generated safely!\nSaved to: {out_path}")
                
            self.refresh_doc_history()
            try: 
                os.startfile(out_path)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open file: {e}")
        else:
            QMessageBox.critical(self, "Generation Failed", f"Ensure you mapped a template for '{doc_type}' in Settings.\n\nError: {msg}")