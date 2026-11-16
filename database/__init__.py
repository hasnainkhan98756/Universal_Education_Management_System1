# Import connection utilities
from database.connection import init_db, get_session

# Import all models to ensure SQLAlchemy registers them in the database
from database.models.users import User
from database.models.institution import InstitutionSettings
from database.models.pdf_templates import PDFTemplateMapping

# Phase 9: Academic Foundation
from database.models.academic import AcademicClass, AcademicSection, AcademicSubject

# Phase 10: Student Management
from database.models.student import Student

# Phase 11: Fee Management & Financial Data
from database.models.fee import FeeVoucher, FeePayment

# Phase 12: Attendance Management
from database.models.attendance import AttendanceRecord

# PHASE 13: Unified Document History Tracker
from database.models.documents import DocumentHistory