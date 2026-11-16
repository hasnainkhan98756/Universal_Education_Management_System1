from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime

class AttendanceRecord(Base):
    """Stores daily attendance records for students."""
    __tablename__ = 'attendance_records'
    
    # CRITICAL FIX: The UniqueConstraint prevents duplicate attendance records for the same student on the same day!
    __table_args__ = (
        UniqueConstraint('student_id', 'date', name='uq_student_date_attendance'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id', ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey('academic_classes.id', ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey('academic_sections.id', ondelete="CASCADE"), nullable=False)
    
    date = Column(String(20), nullable=False) # Format: YYYY-MM-DD
    status = Column(String(20), nullable=False, default="Present") # Present, Absent, Leave, Late
    remarks = Column(String(200), nullable=True)
    
    academic_session = Column(String(50), nullable=False)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    student = relationship("database.models.student.Student")