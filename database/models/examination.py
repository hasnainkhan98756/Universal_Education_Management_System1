from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database.models.base import Base

class ExamResult(Base):
    """Stores individual subject marks for students."""
    __tablename__ = 'exam_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    class_id = Column(Integer, ForeignKey('academic_classes.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('academic_sections.id'), nullable=False)
    
    academic_session = Column(String, nullable=False)
    exam_title = Column(String, nullable=False) # e.g., "Mid Term 2026"
    subject = Column(String, nullable=False)    # e.g., "Mathematics"
    
    total_marks = Column(Float, default=100.0)
    obtained_marks = Column(Float, default=0.0)
    grade = Column(String, default="F")
    remarks = Column(String, default="")

    # Relationships
    student = relationship("Student")
    academic_class = relationship("AcademicClass")
    academic_section = relationship("AcademicSection")