from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime

# Association Table for Class-Subject Many-to-Many Relationship
class_subject_association = Table(
    'class_subject_assignments',
    Base.metadata,
    Column('class_id', Integer, ForeignKey('academic_classes.id', ondelete="CASCADE"), primary_key=True),
    Column('subject_id', Integer, ForeignKey('academic_subjects.id', ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)

class AcademicClass(Base):
    __tablename__ = 'academic_classes'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) # e.g., "Class 10", "FSc Pre-Medical"
    code = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0) # For custom sorting (1, 2, 3...)
    academic_session = Column(String(50), nullable=False) # Ties class to a session like "2026-2027"
    is_active = Column(Boolean, default=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    sections = relationship("database.models.academic.AcademicSection", back_populates="academic_class", cascade="all, delete-orphan")
    subjects = relationship("database.models.academic.AcademicSubject", secondary=class_subject_association, back_populates="classes")

class AcademicSection(Base):
    __tablename__ = 'academic_sections'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey('academic_classes.id', ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False) # e.g., "A", "Rose"
    code = Column(String(50), nullable=True)
    capacity = Column(Integer, default=40)
    is_active = Column(Boolean, default=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    academic_class = relationship("database.models.academic.AcademicClass", back_populates="sections")

class AcademicSubject(Base):
    __tablename__ = 'academic_subjects'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    code = Column(String(50), nullable=True)
    short_name = Column(String(20), nullable=True)
    subject_type = Column(String(50), default="Compulsory") # Compulsory, Optional, Practical
    
    full_marks = Column(Float, default=100.0)
    passing_marks = Column(Float, default=33.0)
    theory_marks = Column(Float, default=0.0)
    practical_marks = Column(Float, default=0.0)
    credit_hours = Column(Float, default=0.0)
    
    is_active = Column(Boolean, default=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    classes = relationship("database.models.academic.AcademicClass", secondary=class_subject_association, back_populates="subjects")