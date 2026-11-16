import os
from datetime import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QTabWidget, QWidget, QFormLayout, QLineEdit, QMessageBox, QGroupBox,
                               QComboBox, QDateEdit, QFileDialog, QInputDialog, QAbstractItemView)
from PySide6.QtCore import Qt, QUrl, QDate
from PySide6.QtGui import QFont, QColor, QDesktopServices
from core.hr_service import HRService
from core.document_service import DocumentService
from core.pdf_service import PDFGenerationService
from core.data_resolver import DataResolverService
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    ModernButton, StatusBadge, style_modern_table, style_modern_tabs
)

class StaffDocumentPromptDialog(QDialog):
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
        layout.addWidget(QLabel(f"<h3>{document_title} — Parameters</h3><p style='color:#4B5563;'>Employee profile and payroll database values are loaded automatically.</p>"))
        
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
        
        btn = QPushButton("Generate Final PDF Document")
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
            data[key] = val
        return data

class EmployeeProfileDialog(QDialog):
    def __init__(self, emp_db_id, parent=None):
        super().__init__(parent)
        self.emp_id = emp_db_id
        self.setWindowTitle("Employee 360 Profile")
        self.resize(850, 600)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(16, 16, 16, 16)
        main_lay.setSpacing(12)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_personal_tab(), "Personal & Employment")
        self.tabs.setTabIcon(0, get_icon("user", color="#475569"))
        self.tabs.addTab(self.create_qualifications_tab(), "Qualifications")
        self.tabs.setTabIcon(1, get_icon("award", color="#475569"))
        self.tabs.addTab(self.create_workload_tab(), "Teaching Workload")
        self.tabs.setTabIcon(2, get_icon("book-open", color="#475569"))
        self.tabs.addTab(self.create_history_tab(), "Attendance & Payroll History")
        self.tabs.setTabIcon(3, get_icon("calendar-check", color="#475569"))
        self.tabs.addTab(self.create_documents_tab(), "Documents & Files")
        self.tabs.setTabIcon(4, get_icon("file-text", color="#475569"))

        main_lay.addWidget(self.tabs)
        
        btn_close = ModernButton("Close Profile", icon_name="x", variant="secondary")
        btn_close.clicked.connect(self.accept)
        main_lay.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _display_row(self, label, value):
        l = QLabel(f"<b>{label}:</b>")
        v = QLabel(str(value or "-"))
        # No hardcoded color — inherits theme text color
        return l, v

    def create_personal_tab(self):
        page = QWidget()
        lay = QHBoxLayout(page)
        emp = HRService.get_employee_by_id(self.emp_id)
        if not emp:
            return page

        # Personal Box
        box_p = QGroupBox("Personal Information")
        form_p = QFormLayout(box_p)
        form_p.addRow(*self._display_row("Employee ID", emp.emp_id))
        form_p.addRow(*self._display_row("Full Name", f"{emp.first_name} {emp.last_name or ''}"))
        form_p.addRow(*self._display_row("Father / Husband", emp.father_husband_name))
        form_p.addRow(*self._display_row("CNIC / ID", emp.cnic))
        form_p.addRow(*self._display_row("Gender", emp.gender))
        form_p.addRow(*self._display_row("Date of Birth", emp.dob))
        form_p.addRow(*self._display_row("Marital Status", emp.marital_status))
        form_p.addRow(*self._display_row("Phone", emp.phone))
        form_p.addRow(*self._display_row("Address", f"{emp.address or ''}, {emp.city or ''}"))
        form_p.addRow(*self._display_row("Emergency Contact", f"{emp.emergency_name or '-'} ({emp.emergency_phone or '-'})"))

        # Employment Box
        box_e = QGroupBox("Employment & Compensation")
        form_e = QFormLayout(box_e)
        form_e.addRow(*self._display_row("Designation", emp.designation))
        form_e.addRow(*self._display_row("Department", emp.department))
        form_e.addRow(*self._display_row("Employee Type", emp.emp_type))
        
        status_box = QWidget()
        s_box_lay = QHBoxLayout(status_box)
        s_box_lay.setContentsMargins(0, 0, 0, 0)
        s_box_lay.setSpacing(8)
        self.combo_emp_status = QComboBox()
        self.combo_emp_status.addItems(["Active", "Retired", "On Leave", "Suspended", "Resigned", "Terminated", "Inactive"])
        if emp.status:
            self.combo_emp_status.setCurrentText(emp.status)
        btn_set_status = ModernButton("Update", icon_name="refresh-cw", variant="secondary")
        btn_set_status.setFixedHeight(28)
        btn_set_status.clicked.connect(self.change_emp_status)
        s_box_lay.addWidget(self.combo_emp_status)
        s_box_lay.addWidget(btn_set_status)
        form_e.addRow("Employment Status:", status_box)

        form_e.addRow(*self._display_row("Joining Date", emp.joining_date))
        form_e.addRow(*self._display_row("Basic Salary", f"Rs. {emp.basic_salary:,.2f}"))
        form_e.addRow(*self._display_row("House Allowance", f"Rs. {emp.house_allowance:,.2f}"))
        form_e.addRow(*self._display_row("Medical Allowance", f"Rs. {emp.medical_allowance:,.2f}"))
        form_e.addRow(*self._display_row("Transport Allowance", f"Rs. {emp.transport_allowance:,.2f}"))
        form_e.addRow(*self._display_row("Bank Name", emp.bank_name))
        form_e.addRow(*self._display_row("Account / IBAN", f"{emp.account_no or ''} / {emp.iban or ''}"))

        lay.addWidget(box_p)
        lay.addWidget(box_e)
        return page

    def change_emp_status(self):
        new_st = self.combo_emp_status.currentText()
        success, msg = HRService.update_employee_status(self.emp_id, new_st)
        if success:
            QMessageBox.information(self, "Status Updated", f"Employee status updated to {new_st}.")
        else:
            QMessageBox.critical(self, "Error", msg)

    def create_qualifications_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        
        # Add bar
        add_lay = QHBoxLayout()
        self.inp_degree = QLineEdit(); self.inp_degree.setPlaceholderText("Degree (e.g. BS Physics)")
        self.inp_major = QLineEdit(); self.inp_major.setPlaceholderText("Major")
        self.inp_inst = QLineEdit(); self.inp_inst.setPlaceholderText("Institution")
        self.inp_year = QLineEdit(); self.inp_year.setPlaceholderText("Year")
        self.inp_grade = QLineEdit(); self.inp_grade.setPlaceholderText("Grade/Marks")
        
        btn_add = ModernButton("Add Qualification", icon_name="plus", variant="secondary")
        btn_add.clicked.connect(self.save_qualification)

        add_lay.addWidget(self.inp_degree); add_lay.addWidget(self.inp_major)
        add_lay.addWidget(self.inp_inst); add_lay.addWidget(self.inp_year)
        add_lay.addWidget(self.inp_grade); add_lay.addWidget(btn_add)
        lay.addLayout(add_lay)

        self.tbl_qual = QTableWidget()
        self.tbl_qual.setColumnCount(6)
        self.tbl_qual.setHorizontalHeaderLabels(["Degree", "Major", "Institution", "Year", "Grade", "Action"])
        self.tbl_qual.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(self.tbl_qual)
        lay.addWidget(self.tbl_qual)

        self.load_qualifications()
        return page

    def load_qualifications(self):
        emp = HRService.get_employee_by_id(self.emp_id)
        if not emp: return
        self.tbl_qual.setRowCount(len(emp.qualifications))
        for r, q in enumerate(emp.qualifications):
            self.tbl_qual.setItem(r, 0, QTableWidgetItem(q.degree))
            self.tbl_qual.setItem(r, 1, QTableWidgetItem(q.major_subject or "-"))
            self.tbl_qual.setItem(r, 2, QTableWidgetItem(q.institution or "-"))
            self.tbl_qual.setItem(r, 3, QTableWidgetItem(q.passing_year or "-"))
            self.tbl_qual.setItem(r, 4, QTableWidgetItem(q.grade_marks or "-"))
            
            btn_del = ModernButton("Delete", icon_name="trash-2", variant="danger")
            btn_del.setFixedHeight(28)
            btn_del.clicked.connect(lambda checked=False, qid=q.id: self.delete_qual(qid))
            self.tbl_qual.setCellWidget(r, 5, btn_del)
            self.tbl_qual.setRowHeight(r, 40)

    def save_qualification(self):
        d = self.inp_degree.text().strip()
        if not d:
            QMessageBox.warning(self, "Error", "Degree is required."); return
        HRService.add_qualification(
            self.emp_id, d, self.inp_major.text().strip(), self.inp_inst.text().strip(),
            self.inp_year.text().strip(), self.inp_grade.text().strip()
        )
        self.inp_degree.clear(); self.inp_major.clear(); self.inp_inst.clear(); self.inp_year.clear(); self.inp_grade.clear()
        self.load_qualifications()

    def delete_qual(self, qid):
        HRService.delete_qualification(qid)
        self.load_qualifications()

    def create_workload_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        tbl = QTableWidget()
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(["Class", "Section", "Subject", "Periods / Week"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(tbl)

        assigns = HRService.get_assignments(filter_teacher_id=self.emp_id)
        tbl.setRowCount(len(assigns))
        for r, a in enumerate(assigns):
            tbl.setRowHeight(r, 40)
            tbl.setItem(r, 0, QTableWidgetItem(a.academic_class.name))
            tbl.setItem(r, 1, QTableWidgetItem(a.academic_section.name))
            tbl.setItem(r, 2, QTableWidgetItem(a.academic_subject.name))
            tbl.setItem(r, 3, QTableWidgetItem(str(a.periods_per_week)))

        lay.addWidget(tbl)
        return page

    def create_history_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        # Attendance Metrics
        att = HRService.get_employee_attendance_summary(self.emp_id)
        metric_lbl = QLabel(f"<b>Attendance Lifetime:</b> Present: {att['present']} | Absent: {att['absent']} | Leave: {att['leave']} | Late: {att['late']} | Half-Day: {att['half_day']} | Attendance: <b>{att['percentage']}%</b>")
        metric_lbl.setStyleSheet("padding: 10px; background: #F1F5F9; border-radius: 8px; font-size: 13px;")
        lay.addWidget(metric_lbl)

        # Payroll History
        lay.addWidget(QLabel("<b>Historical Payroll Payments:</b>"))
        tbl_pay = QTableWidget()
        tbl_pay.setColumnCount(6)
        tbl_pay.setHorizontalHeaderLabels(["Receipt #", "Month", "Gross", "Deductions", "Net Paid", "Date"])
        tbl_pay.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(tbl_pay)

        emp = HRService.get_employee_by_id(self.emp_id)
        if emp and emp.payroll:
            tbl_pay.setRowCount(len(emp.payroll))
            for r, p in enumerate(emp.payroll):
                tbl_pay.setRowHeight(r, 40)
                tbl_pay.setItem(r, 0, QTableWidgetItem(p.receipt_no))
                tbl_pay.setItem(r, 1, QTableWidgetItem(p.pay_month))
                tbl_pay.setItem(r, 2, QTableWidgetItem(f"Rs. {p.gross_salary:,.2f}"))
                tbl_pay.setItem(r, 3, QTableWidgetItem(f"Rs. {p.deductions:,.2f}"))
                tbl_pay.setItem(r, 4, QTableWidgetItem(f"Rs. {p.net_salary:,.2f}"))
                tbl_pay.setItem(r, 5, QTableWidgetItem(p.payment_date or "-"))
        lay.addWidget(tbl_pay)
        return page

    def create_documents_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)
        lay.setContentsMargins(10, 10, 10, 10)

        top_row = QHBoxLayout()
        lbl_info = QLabel("<b>Staff Documents & Files:</b> Uploaded files, ID scans, degrees, contracts, and salary records.")
        lbl_info.setStyleSheet("color: #475569; font-size: 13px;")
        top_row.addWidget(lbl_info)
        top_row.addStretch()

        btn_upload = ModernButton("Upload Staff Document", icon_name="upload", variant="primary")
        btn_upload.setFixedHeight(34)
        btn_upload.clicked.connect(self.upload_employee_document)
        top_row.addWidget(btn_upload)
        lay.addLayout(top_row)

        # 5 Newly Integrated Staff Certificates & Letters
        cert_bar = QHBoxLayout()
        btn_exp = QPushButton("Experience Cert")
        btn_exp.clicked.connect(lambda: self.trigger_staff_doc("Experience Certificate", [
            {"label": "Date of Leaving / Relieving", "key": "date_of_leaving", "type": "date"}
        ]))

        btn_appt = QPushButton("Appointment Letter")
        btn_appt.clicked.connect(lambda: self.trigger_staff_doc("Appointment Letter", [
            {"label": "Reporting / Joining Date", "key": "joining_date", "type": "date"},
            {"label": "Gross Remuneration (PKR)", "key": "salary", "type": "text"}
        ]))

        btn_sal = QPushButton("Salary / Income Cert")
        btn_sal.clicked.connect(lambda: self.trigger_staff_doc("Salary Certificate", []))

        btn_rel = QPushButton("Relieving Letter")
        btn_rel.clicked.connect(lambda: self.trigger_staff_doc("Relieving Letter", [
            {"label": "Resignation Submission Date", "key": "resignation_date", "type": "date"},
            {"label": "Effective Last Working Day", "key": "last_working_day", "type": "date"},
            {"label": "Clearance Status", "key": "clearance_status", "type": "combo", "options": ["Audited & Fully Cleared Across All Departments", "Provisional Handover Completed", "Pending Library Clearance"]}
        ]))

        btn_appr = QPushButton("Appreciation Cert")
        btn_appr.clicked.connect(lambda: self.trigger_staff_doc("Appreciation Certificate", [
            {"label": "Award / Citation Title", "key": "award_name", "type": "text"},
            {"label": "Reason / Commendation Summary", "key": "reason", "type": "text"}
        ]))

        for b in [btn_exp, btn_appt, btn_sal, btn_rel, btn_appr]:
            b.setStyleSheet("background-color: #4338CA; color: white; font-weight: bold; padding: 7px 11px; border-radius: 4px; border: none;")
            cert_bar.addWidget(b)
        lay.addLayout(cert_bar)

        self.tbl_docs = QTableWidget()
        self.tbl_docs.setColumnCount(5)
        self.tbl_docs.setHorizontalHeaderLabels(["Date", "Source", "Document Title", "Type / Ref", "Action"])
        self.tbl_docs.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_docs.setColumnWidth(0, 110)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_docs.setColumnWidth(1, 100)
        self.tbl_docs.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tbl_docs.setColumnWidth(4, 110)
        self.tbl_docs.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        style_modern_table(self.tbl_docs)
        lay.addWidget(self.tbl_docs)

        self.refresh_documents()
        return page

    def refresh_documents(self):
        docs = DocumentService.get_employee_documents(self.emp_id)
        self.tbl_docs.setRowCount(len(docs))
        for r, d in enumerate(docs):
            self.tbl_docs.setItem(r, 0, QTableWidgetItem(d.get("date", "-")))
            
            src = d.get("type", "Uploaded")
            badge = StatusBadge(src, variant="purple" if src == "Generated" else "success")
            bbox = QWidget()
            blay = QHBoxLayout(bbox); blay.setContentsMargins(4, 2, 4, 2); blay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            blay.addWidget(badge)
            self.tbl_docs.setCellWidget(r, 1, bbox)

            self.tbl_docs.setItem(r, 2, QTableWidgetItem(d.get("title", "-")))
            self.tbl_docs.setItem(r, 3, QTableWidgetItem(d.get("doc_number", "-")))

            fpath = d.get("file_path", "")
            b = ModernButton("Open", icon_name="external-link", variant="secondary")
            b.setFixedHeight(28)
            b.clicked.connect(lambda checked=False, p=fpath: QDesktopServices.openUrl(QUrl.fromLocalFile(p)) if (p and os.path.exists(p)) else QMessageBox.warning(self, "Error", "File moved or deleted."))

            box = QWidget()
            box_l = QHBoxLayout(box)
            box_l.setContentsMargins(4, 2, 4, 2)
            box_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box_l.addWidget(b)
            self.tbl_docs.setCellWidget(r, 4, box)
            self.tbl_docs.setRowHeight(r, 44)

    def upload_employee_document(self):
        emp = HRService.get_employee_by_id(self.emp_id)
        emp_name = f"{emp.first_name} {emp.last_name or ''}".strip() if emp else f"Staff #{self.emp_id}"
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Upload Document for {emp_name}", "",
            "Documents (*.pdf *.png *.jpg *.jpeg *.docx *.xlsx *.doc)"
        )
        if not file_path:
            return

        default_title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
        title, ok = QInputDialog.getText(
            self, "Document Title", "Enter title or description (e.g., CNIC Scan, Degree, Contract):",
            text=default_title
        )
        if not ok or not title.strip():
            return

        success, msg = DocumentService.upload_managed_document(
            source_file_path=file_path,
            title=title.strip(),
            category="Staff Records",
            entity_type="Employee",
            entity_id=self.emp_id,
            description=f"Attached to staff member {emp_name}"
        )
        if success:
            QMessageBox.information(self, "Success", "Document uploaded and linked to staff member successfully!")
            self.refresh_documents()
        else:
            QMessageBox.critical(self, "Upload Failed", msg)

    def trigger_staff_doc(self, doc_type, extra_fields):
        extra_data = {}
        if extra_fields:
            dlg = StaffDocumentPromptDialog(doc_type, extra_fields, self)
            if not dlg.exec(): return
            extra_data = dlg.get_data()

        data = DataResolverService.get_employee_data(self.emp_id)
        if not data:
            QMessageBox.critical(self, "Error", "Could not resolve employee data from database.")
            return

        data.update(extra_data)

        doc_num = DocumentService.generate_number(doc_type)
        data["document.certificate_number"] = doc_num
        data["document.date_of_issue"] = datetime.now().strftime("%Y-%m-%d")

        app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        output_dir = os.path.join(app_root, "user_data", "generated_docs", doc_type.replace(" ", "_"))
        os.makedirs(output_dir, exist_ok=True)
        staff_slug = data.get("employee.name", f"staff_{self.emp_id}").replace(" ", "_")
        out_path = os.path.join(output_dir, f"{doc_num}_{staff_slug}.pdf")

        success, msg = PDFGenerationService.generate_document(doc_type, data, out_path)

        if success:
            DocumentService.log_document(None, doc_type, doc_num, out_path, employee_id=self.emp_id)

            if "Warning:" in msg:
                QMessageBox.warning(self, "Generated with Warnings", msg)
            else:
                QMessageBox.information(self, "Success", f"Document {doc_num} generated safely!\nSaved to: {out_path}")

            self.refresh_documents()
            try:
                os.startfile(out_path)
            except Exception as e:
                QMessageBox.warning(self, "Notice", f"PDF generated, but could not launch default viewer: {e}")
        else:
            QMessageBox.critical(self, "Generation Failed", f"PDF Generation Error:\n{msg}")