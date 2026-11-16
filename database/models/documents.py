from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime
import database.models.student  # noqa: F401
import database.models.hr       # noqa: F401


class DocumentHistory(Base):
    """Tracks every PDF document (Certificates, Receipts, IDs) generated for a student."""
    __tablename__ = 'document_history'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete="CASCADE"), nullable=True)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=True)
    
    document_type = Column(String(100), nullable=False) # e.g., 'School Leaving Certificate', 'Salary Slip'
    document_number = Column(String(100), unique=True, nullable=False) # e.g., 'SLC-2026-0001'
    file_path = Column(String(500), nullable=False)
    
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    student = relationship("Student")
    employee = relationship("Employee")


class ManagedDocument(Base):
    """Tracks all user-uploaded and indexed institutional documents (B-Forms, CNIC, Invoices, Contracts, etc.)."""
    __tablename__ = 'managed_documents'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_uuid = Column(String(64), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_category = Column(String(50), nullable=False)  # Student, Employee, Finance, Inventory, Academic, Institutional
    entity_type = Column(String(50), nullable=True)     # Student, Employee, Expense, Purchase, General
    entity_id = Column(Integer, nullable=True)
    file_size = Column(Integer, default=0)
    file_extension = Column(String(20), nullable=True)
    storage_path = Column(String(500), nullable=False)
    description = Column(String(500), nullable=True)
    tags = Column(String(255), nullable=True)
    uploaded_by = Column(String(100), default="Admin")
    upload_date = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    is_archived = Column(Integer, default=0) # 0 = Active, 1 = Archived