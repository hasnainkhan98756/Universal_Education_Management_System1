import os
import json
import pymupdf as fitz
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QListWidget, QMessageBox, 
                               QInputDialog, QSpinBox, QGraphicsView, QGraphicsScene, 
                               QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QPen, QBrush
from database.connection import get_session
from database.models.pdf_templates import PDFTemplateMapping

class DraggableField(QGraphicsTextItem):
    def __init__(self, key, display_text, size=11):
        super().__init__(display_text)
        self.key = key
        self.is_image = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFont(QFont("Arial", size, QFont.Weight.Bold))
        self.setDefaultTextColor(QColor("#1E3A8A"))
        self.size = size

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if value: self.setDefaultTextColor(QColor("#DC2626"))
            else: self.setDefaultTextColor(QColor("#1E3A8A"))
        return super().itemChange(change, value)

class DraggableImageField(QGraphicsRectItem):
    """Visual Bounding Box for Passport Photos and Logos."""
    def __init__(self, key, display_text, width=100, height=120):
        super().__init__(0, 0, width, height)
        self.key = key
        self.is_image = True
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
                      
        # Transparent blue box with bold border
        self.setBrush(QBrush(QColor(59, 130, 246, 100))) 
        self.setPen(QPen(QColor("#1D4ED8"), 2))
        
        self.text_item = QGraphicsTextItem(display_text, self)
        self.text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.text_item.setDefaultTextColor(QColor("#111827"))
        self.recenter_text()

    def recenter_text(self):
        rect = self.rect()
        t_rect = self.text_item.boundingRect()
        self.text_item.setPos((rect.width() - t_rect.width())/2, (rect.height() - t_rect.height())/2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if value: self.setPen(QPen(QColor("#DC2626"), 3)) 
            else: self.setPen(QPen(QColor("#1D4ED8"), 2))
        return super().itemChange(change, value)

class VisualPDFMapperWindow(QMainWindow):
    def __init__(self, doc_type):
        super().__init__()
        self.doc_type = doc_type
        self.setWindowTitle(f"Visual PDF Mapper - {doc_type}")
        self.resize(1250, 850)

        self.db_record = None; self.pdf_doc = None; self.current_page = 0
        self.fields_on_pages = {}; self.custom_fields = []
        self.bg_item = None

        self.default_fields = [
            "system.institution_name", "system.institution_logo", 
            "student.name", "student.photo", "student.date_of_birth", 
            "student.b_form", "student.student_id", "student.roll_number",
            "academic.class", "academic.section", "academic.session",
            "parent.father_name", "parent.mother_name", "parent.father_cnic",
            "admission.admission_number", "admission.date_of_admission"
        ]
        
        if "Receipt" in doc_type or "Voucher" in doc_type:
            self.default_fields.extend([
                "fee.receipt_number", "fee.payment_date", "fee.fee_month", 
                "fee.monthly_fee", "fee.total_fee", "fee.amount_received", 
                "fee.remaining_balance", "fee.payment_method",
                "fee.tuition_fee", "fee.tuition_discount", "fee.tuition_paid", "fee.tuition_remaining",
                "fee.transport_fee", "fee.transport_paid", "fee.transport_remaining",
                "fee.admission_fee", "fee.admission_paid", "fee.admission_remaining",
                "fee.exam_fee", "fee.exam_paid", "fee.exam_remaining",
                "fee.other_charges", "fee.other_paid", "fee.other_remaining",
                "fee.fine", "fee.total_discount",
                "fee.previous_dues", "fee.current_fee", "fee.total_payable", "fee.total_remaining_balance",
                "fee.item_1_category", "fee.item_1_amount", "fee.item_1_discount", "fee.item_1_paid", "fee.item_1_remaining",
                "fee.item_2_category", "fee.item_2_amount", "fee.item_2_discount", "fee.item_2_paid", "fee.item_2_remaining",
                "fee.item_3_category", "fee.item_3_amount", "fee.item_3_discount", "fee.item_3_paid", "fee.item_3_remaining"
            ])
        elif doc_type == "Admission Form":
            self.default_fields.extend([
                "admission.application_number", "student.nationality", "student.religion", 
                "student.place_of_birth", "student.blood_group", "student.address", 
                "student.city", "student.contact_number", "parent.father_mobile",
                "parent.father_occupation", "parent.monthly_income", "admission.previous_school",
                "admission.previous_class", "admission.previous_result"
            ])
        elif doc_type == "Student ID Card":
            self.default_fields.extend([
                "document.date_of_issue", "document.valid_until", "student.blood_group",
                "medical.emergency_contact_number"
            ])
        elif doc_type == "School Leaving Certificate":
            self.default_fields.extend([
                "document.certificate_number", "document.date_of_issue",
                "document.class_at_time_of_leaving", "document.date_of_leaving", 
                "document.last_academic_session", "document.reason_for_leaving", 
                "document.conduct", "document.academic_performance", "document.purpose"
            ])
        elif doc_type == "Character Certificate":
            self.default_fields.extend([
                "document.certificate_number", "document.date_of_issue",
                "document.character", "document.conduct", "document.discipline", 
                "document.attendance", "document.general_behavior", "document.purpose"
            ])
        elif doc_type == "English Proficiency":
            self.default_fields.extend([
                "document.certificate_number", "document.date_of_issue",
                "document.listening_level", "document.speaking_level", 
                "document.reading_level", "document.writing_level", 
                "document.grammar_level", "document.vocabulary_level", 
                "document.overall_english_proficiency", "document.medium_of_instruction", 
                "document.overall_level", "document.purpose"
            ])
        elif doc_type == "Transcript":
            self.default_fields.extend([
                "document.number", "document.date_of_issue",
                "examination.title",
                "result.grand_total", "result.total_obtained", 
                "result.percentage", "result.overall_grade"
            ])
            for i in range(1, 16):
                self.default_fields.extend([
                    f"subject_{i}.name", f"subject_{i}.total", 
                    f"subject_{i}.obtained", f"subject_{i}.grade"
                ])
        elif doc_type == "Salary Slip":
            self.default_fields.extend([
                "employee.name", "employee.emp_id", "employee.designation",
                "payroll.receipt_no", "payroll.month", "payroll.basic",
                "payroll.allowances", "payroll.deductions", "payroll.net_salary",
                "payroll.payment_date", "payroll.method"
            ])

        self.init_ui()
        self.load_data()

    def init_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(central); main_layout.setContentsMargins(15, 15, 15, 15)

        sidebar = QWidget(); sidebar.setFixedWidth(350)
        sidebar_lay = QVBoxLayout(sidebar); sidebar_lay.setSpacing(10)

        title = QLabel(f"Mapping: {self.doc_type}"); title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1D4ED8;")
        sidebar_lay.addWidget(title)

        btn_lay = QHBoxLayout()
        btn_add = QPushButton("Add Custom Field"); btn_add.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; border-radius: 6px; padding: 8px;")
        btn_add.clicked.connect(self.add_custom_field)

        btn_del = QPushButton("Delete Field"); btn_del.setStyleSheet("background-color: #EF4444; color: white; font-weight: bold; border-radius: 6px; padding: 8px;")
        btn_del.clicked.connect(self.delete_selected_field)

        btn_lay.addWidget(btn_add); btn_lay.addWidget(btn_del)
        sidebar_lay.addLayout(btn_lay)

        self.list_fields = QListWidget(); self.list_fields.setStyleSheet("font-size: 13px; padding: 5px; border: 1px solid #D1D5DB; border-radius: 4px;")
        sidebar_lay.addWidget(self.list_fields)

        btn_place = QPushButton("Place Selected Field on PDF"); btn_place.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold; font-size: 13px; padding: 10px; border-radius: 4px;")
        btn_place.clicked.connect(self.place_field)
        sidebar_lay.addWidget(btn_place)

        # Dynamic Controls Setup
        controls_lay = QHBoxLayout()
        
        # Text Size Control
        size_lay = QVBoxLayout()
        size_lay.addWidget(QLabel("Text Size:"))
        self.spin_size = QSpinBox(); self.spin_size.setRange(7, 48); self.spin_size.setValue(11)
        self.spin_size.valueChanged.connect(self.update_field_size)
        size_lay.addWidget(self.spin_size)
        
        # Image Width Control
        width_lay = QVBoxLayout()
        width_lay.addWidget(QLabel("Image Width:"))
        self.spin_width = QSpinBox(); self.spin_width.setRange(20, 800); self.spin_width.setValue(100)
        self.spin_width.valueChanged.connect(self.update_image_size)
        width_lay.addWidget(self.spin_width)

        # Image Height Control
        height_lay = QVBoxLayout()
        height_lay.addWidget(QLabel("Image Height:"))
        self.spin_height = QSpinBox(); self.spin_height.setRange(20, 800); self.spin_height.setValue(120)
        self.spin_height.valueChanged.connect(self.update_image_size)
        height_lay.addWidget(self.spin_height)

        controls_lay.addLayout(size_lay)
        controls_lay.addLayout(width_lay)
        controls_lay.addLayout(height_lay)
        sidebar_lay.addLayout(controls_lay)

        nav_lay = QHBoxLayout()
        self.btn_prev = QPushButton("< Prev Page"); self.btn_prev.clicked.connect(lambda: self.change_page(-1))
        self.lbl_page = QLabel("Page 1 / 1"); self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_next = QPushButton("Next Page >"); self.btn_next.clicked.connect(lambda: self.change_page(1))
        nav_lay.addWidget(self.btn_prev); nav_lay.addWidget(self.lbl_page); nav_lay.addWidget(self.btn_next)
        sidebar_lay.addLayout(nav_lay)
        sidebar_lay.addStretch()

        btn_save = QPushButton("Save All Mappings")
        btn_save.setStyleSheet("background-color: #2563EB; color: white; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 6px;")
        btn_save.clicked.connect(self.save_mapping)
        sidebar_lay.addWidget(btn_save)

        self.view = QGraphicsView(); self.scene = QGraphicsScene(); self.view.setScene(self.scene); self.view.setStyleSheet("background-color: #4B5563; border: 1px solid #D1D5DB; border-radius: 8px;")
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        main_layout.addWidget(sidebar); main_layout.addWidget(self.view, stretch=1)

    def load_data(self):
        db = get_session()
        try:
            self.db_record = db.query(PDFTemplateMapping).filter_by(document_type=self.doc_type).first()
            if not self.db_record or not os.path.exists(self.db_record.template_path):
                QMessageBox.critical(self, "Error", f"Template file missing."); self.close(); return

            self.pdf_doc = fitz.open(self.db_record.template_path)
            try:
                saved_data = json.loads(self.db_record.mapping_data)
                self.custom_fields = saved_data.get("custom_fields", [])
                saved_mappings = saved_data.get("mappings", saved_data)
            except (json.JSONDecodeError, ValueError, TypeError):
                self.custom_fields = []; saved_mappings = {}

            self.refresh_field_list()

            for key, info in saved_mappings.items():
                base_key = key.split('_copy')[0]
                if base_key not in self.default_fields and base_key not in self.custom_fields:
                    self.custom_fields.append(base_key); self.refresh_field_list()

                page_num = int(info.get('page', 1)) - 1
                if page_num not in self.fields_on_pages: self.fields_on_pages[page_num] = []

                f_type = info.get('type', 'text')
                page_rect = self.pdf_doc[page_num].rect
                scene_w = page_rect.width * 2
                scene_h = page_rect.height * 2
                
                is_img_field = (f_type == "image" or "photo" in base_key or "logo" in base_key or "signature" in base_key)

                if is_img_field:
                    w_pct = float(info.get('width', 15))
                    h_pct = float(info.get('height', 15))
                    
                    px_w = (w_pct / 100.0) * scene_w if info.get('is_percentage') else w_pct * 2
                    px_h = (h_pct / 100.0) * scene_h if info.get('is_percentage') else h_pct * 2
                    
                    if px_w < 10: px_w = 100
                    if px_h < 10: px_h = 120
                    
                    df = DraggableImageField(key, f"[{base_key}]", px_w, px_h)
                else:
                    df = DraggableField(key, f"[{base_key}]", int(info.get('size', 11)))
                
                if info.get('is_percentage', False):
                    abs_x = (float(info['x']) / 100.0) * scene_w
                    abs_y = (float(info['y']) / 100.0) * scene_h
                else:
                    abs_x = float(info['x']) * 2
                    abs_y = float(info['y']) * 2

                df.setPos(abs_x, abs_y)
                self.fields_on_pages[page_num].append(df)

            self.render_page()
        finally: db.close()

    def refresh_field_list(self):
        self.list_fields.clear()
        for f in self.default_fields: self.list_fields.addItem(f)
        for f in self.custom_fields: self.list_fields.addItem(f"{f} (Custom)")

    def add_custom_field(self):
        name, ok = QInputDialog.getText(self, "Add Custom Field", "Enter namespaced key (e.g., document.remarks):")
        if ok and name.strip():
            clean_name = name.strip().lower().replace(" ", "_")
            if clean_name in self.default_fields or clean_name in self.custom_fields: return
            self.custom_fields.append(clean_name); self.refresh_field_list()

    def delete_selected_field(self):
        selected_canvas = [item for item in self.scene.selectedItems() if hasattr(item, 'key')]
        if selected_canvas:
            for item in selected_canvas:
                self.scene.removeItem(item)
                if self.current_page in self.fields_on_pages:
                    if item in self.fields_on_pages[self.current_page]:
                        self.fields_on_pages[self.current_page].remove(item)
            return

        item = self.list_fields.currentItem()
        if not item: return
        field_name = item.text()
        if "(Custom)" not in field_name:
            QMessageBox.warning(self, "System Field", "System fields cannot be deleted from the list, but you CAN click them on the canvas and delete them."); return

        clean_name = field_name.replace(" (Custom)", "")
        self.custom_fields.remove(clean_name); self.refresh_field_list()

    def place_field(self):
        item = self.list_fields.currentItem()
        if not item: return
        base_key = item.text().replace(" (Custom)", "")
        
        if self.current_page not in self.fields_on_pages: 
            self.fields_on_pages[self.current_page] = []
            
        existing_keys = [f.key for f in self.fields_on_pages[self.current_page]]
        final_key = base_key
        copy_num = 1
        while final_key in existing_keys:
            final_key = f"{base_key}_copy{copy_num}"
            copy_num += 1

        is_image = "photo" in base_key or "logo" in base_key or "signature" in base_key
        if is_image:
            df = DraggableImageField(final_key, f"[{base_key}]")
        else:
            df = DraggableField(final_key, f"[{base_key}]", self.spin_size.value())
        
        center_x = self.scene.sceneRect().width() / 3 + (copy_num * 15)
        center_y = self.scene.sceneRect().height() / 3 + (copy_num * 15)
        
        df.setPos(center_x, center_y)
        self.scene.addItem(df)
        self.fields_on_pages[self.current_page].append(df)

    def on_selection_changed(self):
        items = self.scene.selectedItems()
        if items:
            item = items[0]
            if getattr(item, 'is_image', False):
                self.spin_width.blockSignals(True)
                self.spin_height.blockSignals(True)
                self.spin_width.setValue(int(item.rect().width()))
                self.spin_height.setValue(int(item.rect().height()))
                self.spin_width.blockSignals(False)
                self.spin_height.blockSignals(False)

    def update_field_size(self):
        for item in self.scene.selectedItems():
            if not getattr(item, 'is_image', False):
                item.size = self.spin_size.value()
                item.setFont(QFont("Arial", item.size, QFont.Weight.Bold))

    def update_image_size(self):
        for item in self.scene.selectedItems():
            if getattr(item, 'is_image', False):
                item.setRect(0, 0, self.spin_width.value(), self.spin_height.value())
                item.recenter_text()

    def change_page(self, delta):
        if not self.pdf_doc: return
        new_page = self.current_page + delta
        if 0 <= new_page < len(self.pdf_doc):
            self.current_page = new_page; self.render_page()

    def render_page(self):
        page = self.pdf_doc[self.current_page]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        
        if not self.bg_item:
            self.bg_item = self.scene.addPixmap(QPixmap.fromImage(img))
            self.bg_item.setZValue(-1) 
        else:
            self.bg_item.setPixmap(QPixmap.fromImage(img))
            
        self.scene.setSceneRect(0, 0, pix.width, pix.height)
        self.lbl_page.setText(f"Page {self.current_page + 1} / {len(self.pdf_doc)}")
        
        for p_num, fields in self.fields_on_pages.items():
            for f in fields:
                if f.scene() != self.scene:
                    self.scene.addItem(f)
                if p_num == self.current_page: f.show()
                else: f.hide()

    def save_mapping(self):
        db = get_session()
        try:
            record = db.query(PDFTemplateMapping).filter_by(document_type=self.doc_type).first()
            final_mappings = {}

            for page_num, fields in self.fields_on_pages.items():
                scene_w = self.scene.sceneRect().width()
                scene_h = self.scene.sceneRect().height()
                
                for f in fields:
                    pct_x = (f.scenePos().x() / scene_w) * 100.0
                    pct_y = (f.scenePos().y() / scene_h) * 100.0
                    
                    if getattr(f, 'is_image', False):
                        pct_w = (f.rect().width() / scene_w) * 100.0
                        pct_h = (f.rect().height() / scene_h) * 100.0
                        f_type = "image"
                        f_size = 11
                    else:
                        pct_w = (180 / scene_w) * 100.0
                        pct_h = (24 / scene_h) * 100.0
                        f_type = "text"
                        f_size = getattr(f, 'size', 11)
                        
                    final_mappings[f.key] = {
                        "page": page_num + 1, "x": pct_x, "y": pct_y, 
                        "width": pct_w, "height": pct_h, "size": f_size, 
                        "is_percentage": True, "type": f_type
                    }
                    
            payload = {"custom_fields": self.custom_fields, "mappings": final_mappings}
            record.mapping_data = json.dumps(payload); db.commit()
            QMessageBox.information(self, "Success", f"Mappings Saved successfully!")
            self.close()
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save mapping: {e}")
        finally: db.close()