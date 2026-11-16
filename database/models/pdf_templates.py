from sqlalchemy import Column, Integer, String, Text
from database.models.base import Base

class PDFTemplateMapping(Base):
    """Stores the file paths and JSON coordinate mappings for PDF Document Generation."""
    __tablename__ = 'pdf_template_mappings'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_type = Column(String(100), unique=True, nullable=False)
    template_path = Column(String(500), nullable=True)
    
    # CRITICAL FIX: This column stores the JSON payload with custom fields & coordinates
    mapping_data = Column(Text, default="{}")