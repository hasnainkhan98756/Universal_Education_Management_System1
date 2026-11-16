import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QMessageBox, QInputDialog, QDialog, QFormLayout, QComboBox)
from PySide6.QtCore import Qt
from core.pdf_service import PDFGenerationService

class PDFMapperWidget(QWidget):
    """Advanced Visual PDF Mapper with Dynamic Custom Field Injection."""
    def __init__(self, doc_type, parent=None):
        super().__init__(parent)
        self.doc_type = doc_type
        self.mappings = {}
        self.custom_fields = []
        
        # UI Setup
        main_layout = QVBoxLayout(self)
        
        # Tools row
        tool_lay = QHBoxLayout()
        btn_add = QPushButton("Add Custom Field")
        btn_add.setStyleSheet("background-color: #10B981; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; border: none;")
        btn_add.clicked.connect(self.add_custom_field)
        
        btn_del = QPushButton("Delete Selected Field")
        btn_del.setStyleSheet("background-color: #EF4444; color: white; padding: 6px 12px; font-weight: bold; border-radius: 6px; border: none;")
        btn_del.clicked.connect(self.delete_custom_field)
        
        tool_lay.addWidget(btn_add)
        tool_lay.addWidget(btn_del)
        tool_lay.addStretch()
        main_layout.addLayout(tool_lay)

        lbl = QLabel("1. Select a field below:")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #111827;")
        main_layout.addWidget(lbl)
        
        self.field_list = QListWidget()
        self.field_list.setStyleSheet("background-color: white; color: #111827; border: 1px solid #ccc; font-size: 13px;")
        main_layout.addWidget(self.field_list)

        self.load_fields()

    def load_fields(self):
        self.field_list.clear()
        
        # Standard Default Fields
        standard = [
            "Institution Name", "Student Name", "Father Name", "Class", "Section", "Date of Birth",
            "Student ID", "Roll Number", "Receipt Number", "Application Number", "Certificate Number",
            "Date of Issue"
        ]
        
        for f in standard:
            self.field_list.addItem(f"{f} (System)")
            
        # We would normally parse existing JSON here.
        # Example of loading custom fields if retrieved from service:
        # For this widget scope, custom fields are appended dynamically.
        for cf in self.custom_fields:
            cf_name = cf['name'] if isinstance(cf, dict) else cf
            self.field_list.addItem(f"{cf_name} (Custom)")

    def add_custom_field(self):
        name, ok = QInputDialog.getText(self, "Add Custom Field", "Field Name (e.g., Library Clearance):")
        if ok and name.strip():
            # Validate it's not already there
            existing_names = [cf['name'].lower() if isinstance(cf, dict) else cf.lower() for cf in self.custom_fields]
            if name.strip().lower() in existing_names:
                QMessageBox.warning(self, "Error", "Field already exists.")
                return
                
            self.custom_fields.append({
                "name": name.strip(),
                "key": name.strip() # The exact string the dictionary uses!
            })
            self.load_fields()
            QMessageBox.information(self, "Success", f"Custom field '{name}' added. You can now map it.\nNote: During generation, if this exact text is passed to the data dictionary, it will render automatically.")

    def delete_custom_field(self):
        item = self.field_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Please select a field to delete.")
            return
            
        text = item.text()
        if "(System)" in text:
            QMessageBox.warning(self, "Warning", "You cannot delete a System field. Just leave it unmapped.")
            return
            
        name = text.replace(" (Custom)", "")
        reply = QMessageBox.question(self, "Delete", f"Delete the custom field '{name}' mapping? The underlying database data is NOT destroyed.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.custom_fields = [cf for cf in self.custom_fields if (cf['name'] if isinstance(cf, dict) else cf) != name]
            self.load_fields()
            QMessageBox.information(self, "Deleted", "Field mapping removed.")

    def get_save_data(self):
        """Called by the parent Settings View to extract the configuration for PDFGenerationService."""
        return {
            "custom_fields": self.custom_fields,
            "mappings": self.mappings # Usually populated by the drag-and-drop logic
        }