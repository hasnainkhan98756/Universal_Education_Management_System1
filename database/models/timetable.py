from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime
from database.models.academic import AcademicClass, AcademicSection, AcademicSubject
from database.models.hr import Employee

class Room(Base):
    __tablename__ = 'rooms'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_no = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    capacity = Column(Integer, default=40)
    room_type = Column(String(50), default="Classroom") # Classroom, Lab, Library, Hall
    is_active = Column(Boolean, default=True)

class TimetablePeriod(Base):
    __tablename__ = 'timetable_periods'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False) # e.g., "Period 1", "Break", "Period 2"
    start_time = Column(String(20), nullable=False) # e.g., "08:00 AM"
    end_time = Column(String(20), nullable=False)   # e.g., "08:40 AM"
    is_break = Column(Boolean, default=False)
    display_order = Column(Integer, default=1)

class TimetableEntry(Base):
    __tablename__ = 'timetable_entries'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_session = Column(String(50), nullable=False)
    class_id = Column(Integer, ForeignKey('academic_classes.id', ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey('academic_sections.id', ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(20), nullable=False) # Monday, Tuesday, etc.
    
    period_id = Column(Integer, ForeignKey('timetable_periods.id', ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey('academic_subjects.id', ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id', ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id', ondelete="SET NULL"), nullable=True)

    # Relationships
    academic_class = relationship("AcademicClass")
    academic_section = relationship("AcademicSection")
    academic_subject = relationship("AcademicSubject")
    employee = relationship("Employee")
    period = relationship("TimetablePeriod")
    room = relationship("Room")
