import os
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QLineEdit, QComboBox, QMessageBox, QDoubleSpinBox, QFileDialog, QGroupBox, QAbstractSpinBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from core.academic_service import AcademicService
from core.examination_service import ExaminationService
from core.pdf_service import PDFGenerationService
from core.document_service import DocumentService
from core.state_manager import app_state
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, MetricCard, StatusBadge,
    ModernButton, SearchInput, style_modern_table, style_modern_tabs
)
from database.connection import get_session, DB_DIR

class ExaminationView(QWidget):
    """Phase 13: Examinations, Auto-Grading, Smart Subjects, Excel Export & PDF Transcripts."""
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)
        
        header = PageHeader(
            title="Examinations & Transcripts",
            subtitle="Record exam results, compute auto-grading, and generate report cards or transcripts",
            icon_name="award",
        )
        btn_excel = ModernButton("Export Excel", icon_name="download", variant="secondary")
        btn_excel.clicked.connect(self.export_excel)
        
        btn_pdf = ModernButton("Auto-Generate PDF Transcripts", icon_name="printer", variant="primary")
        btn_pdf.clicked.connect(self.generate_transcripts)
        
        header.add_action_widget(btn_excel)
        header.add_action_widget(btn_pdf)
        main_layout.addWidget(header)

        # Control Bar
        control_lay = QHBoxLayout()
        self.combo_class = self._combo()
        self.combo_class.currentIndexChanged.connect(self.update_sections)
        self.combo_section = self._combo()
        
        self.inp_exam_title = QLineEdit()
        self.inp_exam_title.setPlaceholderText("e.g., Mid Term 2026")
        
        self._exam_debounce = QTimer(self)
        self._exam_debounce.setSingleShot(True)
        self._exam_debounce.setInterval(400)
        self._exam_debounce.timeout.connect(self.update_subjects)
        
        self.inp_exam_title.textChanged.connect(self._exam_debounce.start)
        
        self.combo_subject = self._combo()
        self.combo_subject.setEditable(True) 
        
        btn_load = ModernButton("Load Mark Sheet", icon_name="refresh-cw", variant="secondary")
        btn_load.clicked.connect(self.load_mark_sheet)
        
        control_lay.addWidget(self._lbl("Class:")); control_lay.addWidget(self.combo_class)
        control_lay.addWidget(self._lbl("Section:")); control_lay.addWidget(self.combo_section)
        control_lay.addWidget(self._lbl("Exam Title:")); control_lay.addWidget(self.inp_exam_title)
        control_lay.addWidget(self._lbl("Subject:")); control_lay.addWidget(self.combo_subject)
        control_lay.addWidget(btn_load)
        main_layout.addLayout(control_lay)

        self.lbl_status = QLabel("Ready to enter marks.")
        self.lbl_status.setStyleSheet("color: #6B7280; font-style: italic; font-size: 11px;")
        main_layout.addWidget(self.lbl_status)

        self.tbl_sheet = QTableWidget()
        self.tbl_sheet.setColumnCount(7)
        col_w = {0: 120, 1: 160, 2: 95, 3: 105, 4: 80, 5: 140}
        for c, w in col_w.items():
            if c in (1, 5):
                self.tbl_sheet.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
            else:
                self.tbl_sheet.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
                self.tbl_sheet.setColumnWidth(c, w)
        self.tbl_sheet.horizontalHeader().setMinimumSectionSize(65)
        self.tbl_sheet.verticalHeader().setDefaultSectionSize(40)
        style_modern_table(self.tbl_sheet)
        self.tbl_sheet.setColumnHidden(6, True) 
        main_layout.addWidget(self.tbl_sheet)
        
        btn_save = ModernButton("Save & Lock Marks", icon_name="save", variant="primary")
        btn_save.clicked.connect(self.save_marks)
        main_layout.addWidget(btn_save)

        app_state.subscribe_settings_change(self.load_dropdowns)
        self.load_dropdowns()

    def showEvent(self, event):
        self.update_subjects()
        super().showEvent(event)

    def _lbl(self, text):
        lbl = QLabel(text); lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold)); return lbl

    def _combo(self, items=None):
        cb = QComboBox(); cb.setMinimumHeight(32)
        if items: cb.addItems(items)
        return cb

    def load_dropdowns(self):
        active_session = app_state.get_setting("session", "Default")
        self.classes = AcademicService.get_classes(session_filter=active_session)
        self.combo_class.blockSignals(True)
        self.combo_class.clear()
        for c in self.classes: self.combo_class.addItem(c.name, c.id)
        self.combo_class.blockSignals(False)
        self.update_sections()

    def update_sections(self):
        cid = self.combo_class.currentData()
        self.combo_section.clear()
        if cid:
            secs = AcademicService.get_sections(cid)
            for s in secs: self.combo_section.addItem(s.name, s.id)
        self.update_subjects()

    def update_subjects(self):
        cid = self.combo_class.currentData()
        title = self.inp_exam_title.text().strip()
        self.combo_subject.clear()
        
        if cid:
            try:
                assigned_subs, unassigned_subs = AcademicService.get_class_subject_assignment(cid)
                for s in assigned_subs: 
                    self.combo_subject.addItem(s.name)
                
                if title:
                    db = get_session()
                    try:
                        from database.models.examination import ExamResult
                        historical = db.query(ExamResult.subject).filter_by(class_id=cid, exam_title=title).distinct().all()
                        existing = [self.combo_subject.itemText(i) for i in range(self.combo_subject.count())]
                        for h in historical:
                            if h[0] and h[0] not in existing:
                                self.combo_subject.addItem(h[0])
                    finally:
                        db.close()
            except Exception as e:
                print(f"Error syncing subjects: {e}")
                
        if self.combo_subject.count() == 0:
            self.combo_subject.addItems(["Mathematics", "English", "Science", "History", "Computer", "Urdu", "Islamiat"])

    def load_mark_sheet(self):
        cid = self.combo_class.currentData(); sid = self.combo_section.currentData()
        title = self.inp_exam_title.text().strip(); sub = self.combo_subject.currentText().strip()
        
        if not cid or not sid or not title or not sub:
            QMessageBox.warning(self, "Validation", "Please fill in Class, Section, Exam Title, and Subject.")
            return
            
        data = ExaminationService.get_mark_sheet(cid, sid, title, sub)
        self.tbl_sheet.setRowCount(len(data))
        
        existing = sum(1 for d in data if d["is_existing"])
        if existing > 0:
            self.lbl_status.setText(f"Loaded {len(data)} students. Marks exist. Saving will UPDATE records."); self.lbl_status.setStyleSheet("color: #F59E0B; font-weight: bold; background: transparent; border: none;")
        else:
            self.lbl_status.setText(f"Loaded {len(data)} students for new entry."); self.lbl_status.setStyleSheet("color: #10B981; font-weight: bold; background: transparent; border: none;")

        for row, stu in enumerate(data):
            self.tbl_sheet.setItem(row, 0, QTableWidgetItem(stu["student_system_id"]))
            self.tbl_sheet.setItem(row, 1, QTableWidgetItem(stu["name"]))
            self.tbl_sheet.setItem(row, 6, QTableWidgetItem(str(stu["student_id"]))) 
            
            sp_total = QDoubleSpinBox()
            sp_total.setRange(0, 1000)
            sp_total.setDecimals(0)
            sp_total.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sp_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sp_total.setValue(stu["total_marks"])
            sp_total.setStyleSheet("border: none; background: transparent; font-weight: 600; font-size: 11px;")

            sp_obt = QDoubleSpinBox()
            sp_obt.setRange(0, 1000)
            sp_obt.setDecimals(1)
            sp_obt.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            sp_obt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sp_obt.setValue(stu["obtained_marks"])
            sp_obt.setStyleSheet("border: 1px solid #3B82F6; background: #EFF6FF; border-radius: 4px; font-weight: 600; font-size: 11px; padding: 2px 4px;")
            lbl_grade = QLabel(stu["grade"]); lbl_grade.setAlignment(Qt.AlignmentFlag.AlignCenter); lbl_grade.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            
            def update_grade(val=None, t_sp=sp_total, o_sp=sp_obt, g_lbl=lbl_grade):
                g = ExaminationService.calculate_grade(o_sp.value(), t_sp.value())
                g_lbl.setText(g)
                if g in ["A+", "A", "B"]: g_lbl.setStyleSheet("color: #10B981;")
                elif g in ["C", "D"]: g_lbl.setStyleSheet("color: #F59E0B;")
                else: g_lbl.setStyleSheet("color: #EF4444;")

            update_grade()
            sp_total.valueChanged.connect(update_grade)
            sp_obt.valueChanged.connect(update_grade)
            
            self.tbl_sheet.setCellWidget(row, 2, sp_total)
            self.tbl_sheet.setCellWidget(row, 3, sp_obt)
            self.tbl_sheet.setCellWidget(row, 4, lbl_grade)
            
            inp_rem = QLineEdit(stu["remarks"])
            inp_rem.setStyleSheet("border: none; background: transparent; color: #1E293B; font-size: 12px; padding: 2px 4px;")
            self.tbl_sheet.setCellWidget(row, 5, inp_rem)

    def save_marks(self):
        cid = self.combo_class.currentData(); sid = self.combo_section.currentData()
        title = self.inp_exam_title.text().strip(); sub = self.combo_subject.currentText().strip()
        
        rows = self.tbl_sheet.rowCount()
        if rows == 0: return
            
        marks_data = []
        for r in range(rows):
            marks_data.append({
                "student_id": self.tbl_sheet.item(r, 6).text(),
                "total_marks": self.tbl_sheet.cellWidget(r, 2).value(),
                "obtained_marks": self.tbl_sheet.cellWidget(r, 3).value(),
                "remarks": self.tbl_sheet.cellWidget(r, 5).text()
            })
            
        success, msg = ExaminationService.save_marks(cid, sid, title, sub, marks_data)
        if success:
            QMessageBox.information(self, "Success", msg)
            self.update_subjects() 
            self.load_mark_sheet()
        else: QMessageBox.critical(self, "Error", msg)

    def export_excel(self):
        cid = self.combo_class.currentData(); sid = self.combo_section.currentData(); title = self.inp_exam_title.text().strip()
        if not cid or not sid or not title:
            QMessageBox.warning(self, "Error", "Select Class, Section, and Exam Title first.")
            return
            
        try: import openpyxl; from openpyxl.styles import Font, PatternFill
        except ImportError: QMessageBox.critical(self, "Missing", "Run: pip install openpyxl"); return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export Exam Result", f"{title}_Results.xlsx", "Excel (*.xlsx)")
        if not path: return
        
        subjects, transcripts = ExaminationService.get_class_transcript_data(cid, sid, title)
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Results"
        
        headers = ["Student ID", "Name", "Class"] + subjects + ["Grand Total", "Obtained", "Percentage", "Grade"]
        ws.append(headers)
        for col in range(1, len(headers) + 1): ws.cell(row=1, column=col).font = Font(bold=True, color="FFFFFF"); ws.cell(row=1, column=col).fill = PatternFill(start_color="8B5CF6", fill_type="solid")
            
        for stu_id, data in transcripts:
            row = [data["student.student_id"], data["student.name"], data["academic.class"]]
            for sub in subjects:
                sub_data = next((s for s in data["raw_subjects"] if s["name"] == sub), None)
                row.append(sub_data["obtained"] if sub_data else "-")
            row.extend([data["result.grand_total"], data["result.total_obtained"], data["result.percentage"], data["result.overall_grade"]])
            ws.append(row)
            
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 15
        wb.save(path)
        QMessageBox.information(self, "Success", "Class Marksheet exported to Excel successfully!")

    def generate_transcripts(self):
        cid = self.combo_class.currentData(); sid = self.combo_section.currentData(); title = self.inp_exam_title.text().strip()
        if not cid or not sid or not title:
            QMessageBox.warning(self, "Error", "Select Class, Section, and Exam Title first.")
            return
            
        subjects, transcripts = ExaminationService.get_class_transcript_data(cid, sid, title)
        if not transcripts:
            QMessageBox.warning(self, "No Data", "No marks found for this class in this exam.")
            return

        target_dir = os.path.join(os.path.dirname(DB_DIR), "generated_docs", "transcripts", title.replace(" ","_"))
        os.makedirs(target_dir, exist_ok=True)
        
        # Safe import of DataResolver to pull the ENTIRE student profile
        try:
            from core.data_resolver import DataResolverService
            has_resolver = True
        except ImportError:
            has_resolver = False

        success_count = 0
        for stu_id, data_dict in transcripts:
            
            # 1. Pull Full Profile from DB
            if has_resolver:
                sys_id = data_dict.get("student.student_id") or data_dict.get("student_id")
                if sys_id:
                    try:
                        full_profile = DataResolverService.get_student_data(sys_id)
                        for k, v in full_profile.items():
                            if k not in data_dict or not data_dict[k] or data_dict[k] == "-":
                                data_dict[k] = v
                    except Exception: pass

            doc_no = DocumentService.generate_number("Transcript")
            data_dict["document.number"] = doc_no
            data_dict["document.date_of_issue"] = datetime.now().strftime("%Y-%m-%d")
            
            # 2. ULTIMATE KEY INJECTION: Forces all possible mapper names to hold data
            f_name = data_dict.get("father_name") or data_dict.get("student.father_name") or data_dict.get("parent.father_name", "")
            dob = data_dict.get("dob") or data_dict.get("student.dob") or data_dict.get("student.date_of_birth", "")
            adm = data_dict.get("admission_no") or data_dict.get("student.admission_number") or data_dict.get("student.admission_no", "")
            c_name = data_dict.get("class") or data_dict.get("academic.class", "")
            s_name = data_dict.get("section") or data_dict.get("academic.section", "")
            session = data_dict.get("session") or data_dict.get("academic.session", "")
            exam = data_dict.get("exam_title") or data_dict.get("examination.title", "")
            
            # Force assigning to every variation
            data_dict["student_father_name"] = f_name
            data_dict["student.father_name"] = f_name
            data_dict["father_name"] = f_name
            
            data_dict["student_dob"] = dob
            data_dict["student.dob"] = dob
            data_dict["dob"] = dob
            
            data_dict["student_admission_no"] = adm
            data_dict["student.admission_number"] = adm
            data_dict["admission_no"] = adm
            data_dict["admission_number"] = adm
            data_dict["roll_no"] = adm
            data_dict["student.roll_number"] = adm
            
            data_dict["academic_session"] = session
            data_dict["academic.session"] = session
            data_dict["session"] = session
            
            data_dict["academic_section"] = s_name
            data_dict["academic.section"] = s_name
            data_dict["section"] = s_name
            
            data_dict["exam_title"] = exam
            data_dict["examination.title"] = exam
            data_dict["exam.title"] = exam
            data_dict["examination"] = exam
            
            # 3. Generate PDF
            pdf_path = os.path.join(target_dir, f"{data_dict.get('student.student_id', 'stu')}_{title}_Transcript.pdf")
            success, msg = PDFGenerationService.generate_document("Transcript", data_dict, pdf_path)
            
            if success:
                DocumentService.log_document(stu_id, "Transcript", doc_no, pdf_path)
                success_count += 1
                
        QMessageBox.information(self, "Complete", f"Successfully generated {success_count} PDF Transcripts.\nSaved in:\n{target_dir}")