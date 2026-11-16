import os
try:
    import pymupdf as fitz  # Updated to modern standard
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QGraphicsView, QGraphicsScene, 
                               QGraphicsPixmapItem, QGraphicsTextItem, QListWidget, 
                               QMessageBox, QFrame, QSpinBox, QColorDialog, QSplitter)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QImage, QColor, QFont, QPen

from database.connection import get_session
from database.models.pdf_templates import PDFTemplateMapping
from core.pdf_service import PDFGenerationService

class DraggableField(QGraphicsTextItem):
    """A visually draggable marker representing a database field on the PDF."""
    def __init__(self, text, field_name, font_size=12, is_bold=False, color_hex="#000000"):
        super().__init__(text)
        self.field_name = field_name
        self.setFlags(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        self.font_size = font_size
        self.is_bold = is_bold
        self.color_hex = color_hex
        self.update_styling()

    def update_styling(self):
        font = QFont("Helvetica", int(self.font_size))
        font.setBold(self.is_bold)
        self.setFont(font)
        self.setDefaultTextColor(QColor(self.color_hex))

class PDFMapperWindow(QDialog):
    """
    REAL Visual PDF Mapper.
    Renders PDF pages to screen, allows drag-and-drop field mapping, converts 
    display coordinates to real PDF coordinates, and saves to the Database.
    """
    def __init__(self, document_type, pdf_path, parent=None):
        super().__init__(parent)
        
        # =========================================================
        # WINDOW FLAGS FOR MAXIMIZE/MINIMIZE
        # =========================================================
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowMinimizeButtonHint | 
            Qt.WindowType.WindowMaximizeButtonHint | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        self.setWindowTitle(f"Visual PDF Mapper - {document_type}")
        self.setMinimumSize(1200, 800)
        
        # Force dark text and clean backgrounds to prevent invisible white-on-white text
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; }
            QLabel { color: #111827; font-weight: bold; }
            QListWidget { background-color: #FFFFFF; color: #111827; border: 1px solid #D1D5DB; border-radius: 6px; padding: 5px; font-size: 13px; }
            QListWidget::item:selected { background-color: #DBEAFE; color: #1D4ED8; }
            QSpinBox { background-color: #FFFFFF; color: #111827; border: 1px solid #D1D5DB; border-radius: 4px; padding: 4px; }
        """)
        
        self.document_type = document_type
        self.pdf_path = pdf_path
        self.current_page = 0
        self.zoom_factor = 2.0 # Higher zoom for clear rendering
        
        self.doc = None
        if fitz:
            try:
                self.doc = fitz.open(self.pdf_path)
            except Exception as e:
                QMessageBox.critical(self, "PDF Error", f"Could not read PDF file: {e}")

        # Available Fields based on doc type
        self.available_fields = self.get_fields_for_doc(document_type)
        
        self.init_ui()
        self.load_page()
        self.load_existing_mappings()

    def get_fields_for_doc(self, doc_type):
        """Returns standard fields relevant to the selected document type."""
        base = ["institution_name", "institution_address", "institution_phone", "issue_date", "academic_session"]
        student = [
            "student_name", "father_name", "mother_name", "dob", "gender", "blood_group",
            "b_form", "nationality", "religion", "place_of_birth", "student_photo",
            "student_id", "admission_no", "roll_no", "class", "section",
            "address", "city", "district", "mobile_no", "email",
            "guardian_name", "guardian_cnic", "relationship", "father_cnic", "occupation"
        ]
        admission = [
            "application_no", "date", "admission_type", "admission_status",
            "admission_fee", "admission_fee_status", "billing_cycle",
            "monthly_fee", "six_month_fee", "annual_fee", "discount",
            "prev_school", "prev_class", "prev_session", "prev_result", "transfer_cert_no",
            "emergency_person", "emergency_contact", "emergency_relationship",
            "medical_info", "declaration_parent_name", "declaration_date"
        ]
        finance = [
            "receipt_number", "voucher_no", "fee_month", "billing_cycle",
            "monthly_fee", "six_month_fee", "annual_fee", "admission_fee", "admission_fee_status",
            "total_amount", "paid_amount", "remaining_balance", "discount",
            "payment_date", "payment_method", "due_date"
        ]
        academic = ["exam_name", "total_marks", "obtained_marks", "percentage", "grade", "gpa", "position"]
        slc_cert = [
            "certificate_no", "class_at_time_of_leaving", "date_of_leaving", "reason_for_leaving",
            "conduct", "academic_performance", "dues_paid_up_to", "attendance_percentage",
            "character", "discipline", "overall_english_proficiency", "overall_level", "purpose"
        ]
        id_card = ["valid_until", "emergency_contact", "student_photo"]

        dt_lower = (doc_type or "").lower()
        if "admission" in dt_lower:
            return base + student + admission
        elif "fee" in dt_lower or "receipt" in dt_lower or "voucher" in dt_lower or "challan" in dt_lower:
            return base + student + finance
        elif "transcript" in dt_lower or "dmc" in dt_lower or "result" in dt_lower:
            return base + student + academic
        elif "leaving" in dt_lower or "slc" in dt_lower or "transfer" in dt_lower:
            return base + student + slc_cert
        elif "character" in dt_lower or "english" in dt_lower or "certificate" in dt_lower:
            return base + student + slc_cert
        elif "id" in dt_lower or "card" in dt_lower:
            return base + student + id_card
        return base + student + admission + finance + academic + slc_cert

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # Left Panel: Tools & Fields
        left_panel = QFrame()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        title = QLabel(f"Mapping: {self.document_type}")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #1D4ED8;") # Blue title
        left_layout.addWidget(title)
        
        left_layout.addWidget(QLabel("1. Select a field below:"))
        self.field_list = QListWidget()
        self.field_list.addItems(self.available_fields)
        left_layout.addWidget(self.field_list)
        
        btn_add = QPushButton("2. Add Field to Center of Page")
        btn_add.setStyleSheet("background-color: #3B82F6; color: white; padding: 10px; font-weight:bold; border-radius:4px; border:none;")
        btn_add.clicked.connect(self.add_field_to_canvas)
        left_layout.addWidget(btn_add)
        
        left_layout.addWidget(QLabel("3. Drag field to position on PDF."))
        
        # Formatting Tools
        left_layout.addSpacing(20)
        left_layout.addWidget(QLabel("Selected Field Formatting:"))
        
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Size:"))
        self.spin_font = QSpinBox()
        self.spin_font.setRange(6, 72)
        self.spin_font.setValue(12)
        self.spin_font.valueChanged.connect(self.update_selected_item)
        font_row.addWidget(self.spin_font)
        left_layout.addLayout(font_row)
        
        # Page Controls
        left_layout.addSpacing(20)
        page_row = QHBoxLayout()
        btn_prev = QPushButton("< Prev Page")
        btn_prev.setStyleSheet("background-color: #E5E7EB; color: #111827; padding: 8px; font-weight:bold; border-radius:4px; border:none;")
        btn_prev.clicked.connect(self.prev_page)
        self.lbl_page = QLabel(f"Page 1 / {len(self.doc) if self.doc else 1}")
        self.lbl_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_next = QPushButton("Next Page >")
        btn_next.setStyleSheet("background-color: #E5E7EB; color: #111827; padding: 8px; font-weight:bold; border-radius:4px; border:none;")
        btn_next.clicked.connect(self.next_page)
        page_row.addWidget(btn_prev)
        page_row.addWidget(self.lbl_page)
        page_row.addWidget(btn_next)
        left_layout.addLayout(page_row)
        
        # Save Controls
        left_layout.addStretch()
        btn_preview = QPushButton("Preview with Sample Data")
        btn_preview.setStyleSheet("background-color: #6B7280; color: white; padding: 10px; font-weight:bold; border-radius:4px; border:none;")
        btn_preview.clicked.connect(self.preview_sample)
        left_layout.addWidget(btn_preview)
        
        btn_save = QPushButton("SAVE ALL MAPPINGS")
        btn_save.setStyleSheet("background-color: #10B981; color: white; padding: 15px; font-weight:bold; border-radius:4px; border:none;")
        btn_save.clicked.connect(self.save_mappings)
        left_layout.addWidget(btn_save)

        # Right Panel: PDF Canvas
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        self.pdf_pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pdf_pixmap_item)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.view)
        
        main_layout.addWidget(splitter)

    def load_page(self):
        if not self.doc: return
        
        # Render PDF to image using PyMuPDF Matrix for high-res scaling
        page = self.doc[self.current_page]
        mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to QPixmap
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        qpixmap = QPixmap.fromImage(img)
        
        self.pdf_pixmap_item.setPixmap(qpixmap)
        self.scene.setSceneRect(self.pdf_pixmap_item.boundingRect())
        self.lbl_page.setText(f"Page {self.current_page + 1} / {len(self.doc)}")

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.save_current_page_state() 
            self.current_page += 1
            self.clear_markers()
            self.load_page()
            self.load_existing_mappings()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.save_current_page_state()
            self.current_page -= 1
            self.clear_markers()
            self.load_page()
            self.load_existing_mappings()

    def add_field_to_canvas(self):
        if not self.field_list.currentItem():
            QMessageBox.warning(self, "Select Field", "Please select a field from the list first.")
            return
            
        field_name = self.field_list.currentItem().text()
        
        # Check if already on canvas
        for item in self.scene.items():
            if isinstance(item, DraggableField) and item.field_name == field_name:
                QMessageBox.information(self, "Already Exists", "This field is already on the page.")
                return
                
        # Create Marker
        display_text = f"[{field_name.upper()}]"
        marker = DraggableField(display_text, field_name, font_size=self.spin_font.value())
        
        # Place in center of current view
        center = self.view.mapToScene(self.view.viewport().rect().center())
        marker.setPos(center)
        self.scene.addItem(marker)

    def update_selected_item(self):
        for item in self.scene.selectedItems():
            if isinstance(item, DraggableField):
                item.font_size = self.spin_font.value()
                item.update_styling()

    def clear_markers(self):
        for item in self.scene.items():
            if isinstance(item, DraggableField):
                self.scene.removeItem(item)

    def save_current_page_state(self):
        pass 

    def load_existing_mappings(self):
        """Loads mappings from DB and converts back to screen coordinates."""
        session = get_session()
        try:
            mappings = session.query(PDFTemplateMapping).filter_by(
                document_type=self.document_type,
                page_number=self.current_page
            ).all()
            
            for m in mappings:
                # Convert PDF point coordinates back to scaled screen coordinates
                screen_x = m.x_coordinate * self.zoom_factor
                screen_y = m.y_coordinate * self.zoom_factor
                
                marker = DraggableField(f"[{m.field_name.upper()}]", m.field_name, font_size=m.font_size)
                marker.setPos(screen_x, screen_y)
                self.scene.addItem(marker)
        finally:
            session.close()

    def save_mappings(self):
        """Saves current markers to Database by converting screen coordinates to PDF points."""
        session = get_session()
        try:
            # Clear existing mappings for this exact doc and page to avoid duplicates
            session.query(PDFTemplateMapping).filter_by(
                document_type=self.document_type,
                page_number=self.current_page
            ).delete()
            
            count = 0
            for item in self.scene.items():
                if isinstance(item, DraggableField):
                    # Mathematical Conversion: Scene Pos -> PDF Point
                    pdf_x = item.pos().x() / self.zoom_factor
                    pdf_y = item.pos().y() / self.zoom_factor
                    
                    new_mapping = PDFTemplateMapping(
                        document_type=self.document_type,
                        template_path=self.pdf_path,
                        page_number=self.current_page,
                        field_name=item.field_name,
                        x_coordinate=pdf_x,
                        y_coordinate=pdf_y,
                        font_size=item.font_size,
                        text_color=item.color_hex,
                        is_bold=item.is_bold
                    )
                    session.add(new_mapping)
                    count += 1
                    
            session.commit()
            QMessageBox.information(self, "Success", f"Saved {count} fields for Page {self.current_page + 1}.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save mappings: {e}")
        finally:
            session.close()

    def preview_sample(self):
        """Generates a temporary PDF with dummy data to verify alignment."""
        self.save_mappings() # Force save first
        
        sample_data = {
            "student_name": "Muhammad Ali", "father_name": "Ahmad Khan", "roll_number": "15",
            "class": "10", "section": "A", "receipt_number": "REC-9999", "total_amount": "PKR 15,000",
            "institution_name": "University Public School", "issue_date": "2026-09-01"
        }
        
        from config import USER_DATA_DIR
        temp_out = os.path.join(str(USER_DATA_DIR), 'temp_preview.pdf')
        os.makedirs(os.path.dirname(temp_out), exist_ok=True)
        
        success, msg = PDFGenerationService.generate_document(self.document_type, sample_data, temp_out)
        
        if success:
            QMessageBox.information(self, "Preview Generated", f"Sample preview saved successfully.\n\nOpen this file to verify alignment:\n{temp_out}")
            try:
                os.startfile(temp_out)
            except: pass
        else:
            QMessageBox.critical(self, "Preview Failed", msg)