import os
import shutil
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QDialog, QFormLayout, QMessageBox,
    QFileDialog, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from core.theme_manager import ThemeManager
from core.state_manager import app_state
from core.document_service import DocumentService
from core.icon_manager import icon_mgr
from ui.components.stitch_widgets import (
    PageHeader, ModernButton, TableActionButton, TableTextButton, TableDropdownButton, create_table_actions_cell,
    SearchInput, ModernCard, StatusBadge,
    style_modern_table, style_modern_tabs
)
from ui.components.loading_widgets import show_print_loading

class DocumentView(QWidget):
    """Centralized Institutional Document Archive and Records Management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_all()
        app_state.subscribe(self.refresh_all)

    def init_ui(self):
        t = ThemeManager.tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header Row
        btn_refresh = ModernButton("Refresh", icon_name="rotate-cw", variant="secondary")
        btn_refresh.clicked.connect(self.refresh_all)

        btn_gen_cert = ModernButton("Generate Certificate", icon_name="award", variant="primary")
        btn_gen_cert.clicked.connect(self._on_generate_certificate_dialog)

        btn_upload = ModernButton("Upload Document", icon_name="upload", variant="secondary")
        btn_upload.clicked.connect(self._on_upload_dialog)

        header = PageHeader(
            title="Document Management",
            subtitle="Archive, index, and retrieve student files, staff records, invoices, and certificates",
            icon_name="folder",
            actions=[btn_refresh, btn_gen_cert, btn_upload]
        )
        main_layout.addWidget(header)

        # Tab Widget
        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        # 1. Managed Document Archive Tab
        self.tab_archive = QWidget()
        self._init_archive_tab()
        self.tabs.addTab(self.tab_archive, "Document Archive")
        self.tabs.setTabIcon(0, icon_mgr.get_icon("archive", color=t["text_secondary"]))

        # 2. System Generated Documents Tab
        self.tab_generated = QWidget()
        self._init_generated_tab()
        self.tabs.addTab(self.tab_generated, "System Certificates & Receipts")
        self.tabs.setTabIcon(1, icon_mgr.get_icon("file-text", color=t["text_secondary"]))

        main_layout.addWidget(self.tabs)

    def _init_archive_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_archive)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        # Search & Filter Bar inside ModernCard
        filter_card = ModernCard()
        f_row = QHBoxLayout(filter_card)
        f_row.setContentsMargins(14, 10, 14, 10)
        f_row.setSpacing(12)

        self.txt_search = SearchInput("Search by Title, File Name, Tags, or Description...")
        self._archive_search_timer = QTimer(self)
        self._archive_search_timer.setSingleShot(True)
        self._archive_search_timer.setInterval(250)
        self._archive_search_timer.timeout.connect(self._refresh_archive)
        self.txt_search.textChanged.connect(lambda _: self._archive_search_timer.start())
        f_row.addWidget(self.txt_search, 3)

        self.cmb_cat_filter = QComboBox()
        self.cmb_cat_filter.setMinimumHeight(36)
        self.cmb_cat_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                selection-background-color: {t['accent']};
                selection-color: #FFFFFF;
                border: 1px solid {t['border_color']};
                border-radius: 6px;
            }}
        """)
        self.cmb_cat_filter.addItems([
            "All Categories", "Student Records", "Staff Records",
            "Certificates & Degrees", "Admission & Identification",
            "Finance & Receipts", "Inventory & Invoices", "Institutional", "General"
        ])
        self.cmb_cat_filter.currentIndexChanged.connect(self._refresh_archive)
        f_row.addWidget(self.cmb_cat_filter, 2)
        layout.addWidget(filter_card)

        # Table inside ModernCard
        tbl_card = ModernCard()
        tbl_lay = QVBoxLayout(tbl_card)
        tbl_lay.setContentsMargins(0, 0, 0, 0)

        self.tbl_archive = QTableWidget()
        self.tbl_archive.setColumnCount(7)
        self.tbl_archive.setHorizontalHeaderLabels([
            "ID", "Document Title", "Category", "File Name", "Size", "Upload Date", "Actions"
        ])
        self.tbl_archive.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_archive.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tbl_archive.setColumnWidth(0, 50)
        self.tbl_archive.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_archive.setColumnWidth(6, 115)
        self.tbl_archive.verticalHeader().setDefaultSectionSize(48)
        self.tbl_archive.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_archive.setAlternatingRowColors(True)
        style_modern_table(self.tbl_archive)
        tbl_lay.addWidget(self.tbl_archive)

        layout.addWidget(tbl_card)

    def _init_generated_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_generated)
        layout.setContentsMargins(0, 14, 0, 0)
        layout.setSpacing(12)

        # Search & Filter Bar inside ModernCard
        filter_card = ModernCard()
        f_row = QHBoxLayout(filter_card)
        f_row.setContentsMargins(14, 10, 14, 10)
        f_row.setSpacing(12)

        self.txt_gen_search = SearchInput("Search by Document #, Student/Staff ID, or Type...")
        self._gen_search_timer = QTimer(self)
        self._gen_search_timer.setSingleShot(True)
        self._gen_search_timer.setInterval(250)
        self._gen_search_timer.timeout.connect(self._refresh_generated)
        self.txt_gen_search.textChanged.connect(lambda _: self._gen_search_timer.start())
        f_row.addWidget(self.txt_gen_search, 3)

        self.cmb_gen_filter = QComboBox()
        self.cmb_gen_filter.setMinimumHeight(36)
        self.cmb_gen_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                selection-background-color: {t['accent']};
                selection-color: #FFFFFF;
                border: 1px solid {t['border_color']};
                border-radius: 6px;
            }}
        """)
        self.cmb_gen_filter.addItems([
            "All Document Types", "School Leaving Certificate", "Character Certificate",
            "English Proficiency", "Bonafide Certificate", "Merit Certificate",
            "Attendance Certificate", "Sports Certificate", "Fee Structure & No Dues Certificate",
            "Experience Certificate", "Appointment Letter", "Salary Certificate",
            "Relieving Letter", "Appreciation Certificate",
            "Student ID Card", "Fee Receipt", "Salary Slip", "Transcript", "Admission Form"
        ])
        self.cmb_gen_filter.currentIndexChanged.connect(self._refresh_generated)
        f_row.addWidget(self.cmb_gen_filter, 2)
        layout.addWidget(filter_card)

        tbl_card = ModernCard()
        tbl_lay = QVBoxLayout(tbl_card)
        tbl_lay.setContentsMargins(0, 0, 0, 0)

        self.tbl_generated = QTableWidget()
        self.tbl_generated.setColumnCount(6)
        self.tbl_generated.setHorizontalHeaderLabels([
            "ID", "Document Type", "Document Number", "Student / Staff ID", "Generated At", "Action"
        ])
        self.tbl_generated.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_generated.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tbl_generated.setColumnWidth(5, 140)
        self.tbl_generated.verticalHeader().setDefaultSectionSize(48)
        self.tbl_generated.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_generated.setAlternatingRowColors(True)
        style_modern_table(self.tbl_generated)
        tbl_lay.addWidget(self.tbl_generated)

        layout.addWidget(tbl_card)

    def refresh_all(self):
        self._refresh_archive()
        self._refresh_generated()

    def _refresh_archive(self):
        for r in range(self.tbl_archive.rowCount()):
            w = self.tbl_archive.cellWidget(r, 6)
            if w:
                self.tbl_archive.removeCellWidget(r, 6)
                w.deleteLater()
        self.tbl_archive.clearContents()
        self.tbl_archive.setRowCount(0)

        cat = self.cmb_cat_filter.currentText()
        if cat == "All Categories":
            cat = None
        search = self.txt_search.text().strip()

        docs = DocumentService.get_managed_documents(category=cat, search=search)
        self.tbl_archive.setRowCount(len(docs))
        for r, d in enumerate(docs):
            self.tbl_archive.setItem(r, 0, QTableWidgetItem(str(d.id)))
            self.tbl_archive.setItem(r, 1, QTableWidgetItem(d.title))
            self.tbl_archive.setItem(r, 2, QTableWidgetItem(d.file_category))
            self.tbl_archive.setItem(r, 3, QTableWidgetItem(d.original_filename))
            
            # Format file size
            kb = (d.file_size or 0) / 1024.0
            size_str = f"{kb:.1f} KB" if kb < 1024 else f"{kb/1024.0:.1f} MB"
            self.tbl_archive.setItem(r, 4, QTableWidgetItem(size_str))
            
            self.tbl_archive.setItem(r, 5, QTableWidgetItem(d.upload_date or ""))

            btn_act = TableDropdownButton("Action", icon_name="file-text", variant="secondary", height=28)
            btn_act.add_menu_action("Open Document", lambda _, path=d.storage_path: self._open_file(path), icon_name="file-text", icon_color="#2563EB")
            btn_act.add_menu_action("Save As...", lambda _, src=d.storage_path, orig=d.original_filename: self._save_file_as(src, orig), icon_name="download", icon_color="#059669")
            btn_act.add_menu_action("Archive Record", lambda _, doc_id=d.id: self._archive_doc(doc_id), icon_name="archive", icon_color="#DC2626")

            act_cell = create_table_actions_cell([btn_act])
            self.tbl_archive.setCellWidget(r, 6, act_cell)
            self.tbl_archive.setRowHeight(r, 48)

    def _refresh_generated(self):
        for r in range(self.tbl_generated.rowCount()):
            w = self.tbl_generated.cellWidget(r, 5)
            if w:
                self.tbl_generated.removeCellWidget(r, 5)
                w.deleteLater()
        self.tbl_generated.clearContents()
        self.tbl_generated.setRowCount(0)

        search_kw = self.txt_gen_search.text().strip() if hasattr(self, 'txt_gen_search') else None
        doc_type = self.cmb_gen_filter.currentText() if hasattr(self, 'cmb_gen_filter') else None

        docs = DocumentService.get_all_generated_documents(search=search_kw, doc_type=doc_type)
        self.tbl_generated.setRowCount(len(docs))
        for r, d in enumerate(docs):
            self.tbl_generated.setItem(r, 0, QTableWidgetItem(str(d.id)))
            self.tbl_generated.setItem(r, 1, QTableWidgetItem(d.document_type))
            self.tbl_generated.setItem(r, 2, QTableWidgetItem(d.document_number))
            ref_id = f"Student #{d.student_id}" if d.student_id else (f"Staff #{d.employee_id}" if getattr(d, 'employee_id', None) else "-")
            self.tbl_generated.setItem(r, 3, QTableWidgetItem(ref_id))
            self.tbl_generated.setItem(r, 4, QTableWidgetItem(d.created_at or ""))

            btn_open = TableTextButton("Open PDF", icon_name="file-text", variant="secondary")
            btn_open.clicked.connect(lambda _, path=d.file_path: self._open_file(path))
            act_cell = create_table_actions_cell([btn_open])
            self.tbl_generated.setCellWidget(r, 5, act_cell)
            self.tbl_generated.setRowHeight(r, 48)

    def _open_file(self, file_path):
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"The requested file does not exist on disk:\n{file_path}")
            return
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open document: {str(e)}")

    def _save_file_as(self, src_path, orig_name):
        if not src_path or not os.path.exists(src_path):
            QMessageBox.warning(self, "File Not Found", "Source file not found on disk.")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Save Document Copy", orig_name)
        if dest:
            try:
                shutil.copy2(src_path, dest)
                QMessageBox.information(self, "Saved", f"File saved successfully to:\n{dest}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed saving file: {str(e)}")

    def _archive_doc(self, doc_id):
        res = QMessageBox.question(
            self, "Confirm Archive",
            "Are you sure you want to archive this document? It will be hidden from the active view.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            DocumentService.archive_managed_document(doc_id)
            self._refresh_archive()

    def _on_upload_dialog(self):
        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Upload & Index Document")
        dlg.setMinimumWidth(480)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {t['dialog_bg']};
                color: {t['text_primary']};
            }}
            QLabel {{
                color: {t['text_primary']};
                font-weight: 500;
                font-size: 13px;
            }}
            QLineEdit, QComboBox {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1.5px solid {t['accent']};
            }}
        """)

        form = QFormLayout(dlg)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(14)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        txt_path = QLineEdit()
        txt_path.setReadOnly(True)
        txt_path.setPlaceholderText("Select file to upload...")
        txt_path.setMinimumHeight(32)
        btn_browse = ModernButton("Browse...", icon_name="folder", variant="secondary")
        btn_browse.setFixedHeight(32)

        def browse():
            p, _ = QFileDialog.getOpenFileName(dlg, "Select Document", "", "All Files (*.*);;PDF Files (*.pdf);;Images (*.png *.jpg *.jpeg)")
            if p:
                txt_path.setText(p)
                if not txt_title.text():
                    base = os.path.splitext(os.path.basename(p))[0]
                    txt_title.setText(base.replace("_", " ").title())

        btn_browse.clicked.connect(browse)
        file_row.addWidget(txt_path)
        file_row.addWidget(btn_browse)
        form.addRow("File *:", file_row)

        txt_title = QLineEdit()
        txt_title.setMinimumHeight(32)
        form.addRow("Document Title *:", txt_title)

        cmb_cat = QComboBox()
        cmb_cat.setMinimumHeight(32)
        cmb_cat.addItems([
            "Student Records", "Staff Records", "Finance & Receipts",
            "Inventory & Invoices", "Institutional", "General"
        ])
        form.addRow("Category *:", cmb_cat)

        txt_tags = QLineEdit()
        txt_tags.setPlaceholderText("e.g. cnic, degree, b-form, receipt")
        txt_tags.setMinimumHeight(32)
        form.addRow("Search Tags:", txt_tags)

        txt_desc = QLineEdit()
        txt_desc.setPlaceholderText("Optional notes or description...")
        txt_desc.setMinimumHeight(32)
        form.addRow("Description:", txt_desc)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_save = ModernButton("Upload & Save", icon_name="upload", variant="primary")
        btn_save.setFixedHeight(34)

        def save():
            src = txt_path.text().strip()
            title = txt_title.text().strip()
            if not src or not os.path.exists(src):
                QMessageBox.warning(dlg, "Validation", "Please select a valid file.")
                return
            if not title:
                QMessageBox.warning(dlg, "Validation", "Document title is required.")
                return

            success, msg = DocumentService.upload_managed_document(
                source_file_path=src,
                title=title,
                category=cmb_cat.currentText(),
                description=txt_desc.text(),
                tags=txt_tags.text()
            )
            if success:
                QMessageBox.information(dlg, "Success", msg)
                dlg.accept()
                self._refresh_archive()
            else:
                QMessageBox.critical(dlg, "Error", msg)

        btn_save.clicked.connect(save)
        btn_cancel = ModernButton("Cancel", variant="secondary")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        form.addRow(btn_box)

        dlg.exec()

    def _on_generate_certificate_dialog(self):
        """Unified One-Click Certificate Generation Modal."""
        from database.connection import get_session
        from database.models.student import Student
        from database.models.hr import Employee
        from core.data_resolver import DataResolverService
        from core.pdf_service import PDFGenerationService

        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Generate Institutional Certificate / Letter")
        dlg.setMinimumWidth(500)
        dlg.setStyleSheet(f"""
            QDialog {{ background-color: {t['dialog_bg']}; color: {t['text_primary']}; }}
            QLabel {{ color: {t['text_primary']}; font-weight: 500; font-size: 13px; }}
            QLineEdit, QComboBox {{
                background-color: {t['input_bg']}; color: {t['text_primary']};
                border: 1px solid {t['border_color']}; border-radius: 6px; padding: 6px 10px;
            }}
        """)

        form = QFormLayout(dlg)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(14)

        cmb_target_group = QComboBox()
        cmb_target_group.addItems(["Student Certificates", "Staff & HR Documents"])
        form.addRow("Target Group *:", cmb_target_group)

        cmb_person = QComboBox()
        cmb_doc_type = QComboBox()

        student_doc_types = [
            "Bonafide Certificate", "Academic Excellence / Merit Certificate",
            "Attendance Certificate", "Sports & Extra-Curricular Certificate",
            "Fee Structure & No Dues Certificate", "School Leaving Certificate",
            "Character Certificate", "English Proficiency"
        ]
        staff_doc_types = [
            "Experience Certificate - Staff", "Appointment Letter - Staff",
            "Salary / Income Certificate - Staff", "Relieving Letter - Staff",
            "Appreciation Certificate - Staff"
        ]

        # Load database records
        db = get_session()
        students = []
        employees = []
        try:
            students = db.query(Student).order_by(Student.first_name, Student.last_name).all()
            employees = db.query(Employee).order_by(Employee.first_name, Employee.last_name).all()
        finally:
            db.close()

        def update_options():
            cmb_person.clear()
            cmb_doc_type.clear()
            if cmb_target_group.currentIndex() == 0:
                for s in students:
                    cmb_person.addItem(f"{s.name} ({s.student_id}) - {s.class_enrolled or ''}", s.student_id)
                cmb_doc_type.addItems(student_doc_types)
            else:
                for e in employees:
                    full_n = f"{e.first_name} {e.last_name or ''}".strip()
                    cmb_person.addItem(f"{full_n} ({e.emp_id}) - {e.designation or ''}", e.id)
                cmb_doc_type.addItems(staff_doc_types)

        cmb_target_group.currentIndexChanged.connect(update_options)
        update_options()

        form.addRow("Select Student / Staff *:", cmb_person)
        form.addRow("Certificate / Document *:", cmb_doc_type)

        cmb_basis = QComboBox()
        cmb_basis.addItems(["Monthly", "6-Month", "Annual"])
        form.addRow("Fee Calculation Basis (If Fee Cert):", cmb_basis)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_gen = ModernButton("Generate & Open PDF", icon_name="file-text", variant="primary")
        btn_gen.setFixedHeight(36)

        def do_generate():
            doc_type = cmb_doc_type.currentText().strip()
            person_val = cmb_person.currentData()
            if not person_val:
                QMessageBox.warning(dlg, "Notice", "No record selected.")
                return

            # Resolve live data
            if cmb_target_group.currentIndex() == 0:
                stu_sys_id = person_val
                if "fee" in doc_type.lower():
                    data = DataResolverService.get_student_fee_structure_data(stu_sys_id, basis=cmb_basis.currentText())
                elif "attendance" in doc_type.lower():
                    data = DataResolverService.get_student_attendance_cert_data(stu_sys_id)
                else:
                    data = DataResolverService.get_student_data(stu_sys_id)
                entity_id = stu_sys_id
                emp_id = None
                p_name = data.get("student_name", "Student")
            else:
                emp_db_id = person_val
                data = DataResolverService.get_employee_data(emp_db_id)
                entity_id = None
                emp_id = emp_db_id
                p_name = data.get("employee_name", "Staff")

            # Document Numbering
            doc_num = DocumentService.generate_number(doc_type)
            data["document.certificate_number"] = doc_num
            data["document.date_of_issue"] = datetime.now().strftime("%Y-%m-%d")

            out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "user_data", "generated_docs", doc_type.replace(" ", "_"))
            os.makedirs(out_dir, exist_ok=True)
            slug = str(p_name).replace(" ", "_")
            out_path = os.path.join(out_dir, f"{doc_num}_{slug}.pdf")

            with show_print_loading(dlg, title=f"Generating {doc_type}...", subtitle=f"Rendering document for {p_name}"):
                success, msg = PDFGenerationService.generate_document(doc_type, data, out_path)
            if success:
                # Log generated doc
                stu_id_val = None
                if cmb_target_group.currentIndex() == 0:
                    db2 = get_session()
                    try:
                        stu_rec = db2.query(Student).filter_by(student_id=person_val).first()
                        if stu_rec:
                            stu_id_val = stu_rec.id
                    finally:
                        db2.close()

                DocumentService.log_document(stu_id_val, doc_type, doc_num, out_path, employee_id=emp_id)
                dlg.accept()
                self._refresh_generated()

                try:
                    os.startfile(out_path)
                except Exception as e:
                    QMessageBox.warning(self, "Notice", f"PDF generated at:\n{out_path}\nCould not launch viewer: {e}")
            else:
                QMessageBox.critical(dlg, "Generation Failed", msg)

        btn_gen.clicked.connect(do_generate)
        btn_cancel = ModernButton("Cancel", variant="secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(dlg.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_gen)
        form.addRow(btn_box)

        dlg.exec()
