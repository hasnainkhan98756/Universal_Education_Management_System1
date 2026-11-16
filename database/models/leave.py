from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text
from datetime import datetime
from database.models.base import Base


class LeaveType(Base):
    __tablename__ = 'leave_types'
    id                = Column(Integer, primary_key=True, autoincrement=True)
    name              = Column(String(100), unique=True, nullable=False)
    max_days_per_year = Column(Integer, default=10)
    is_paid           = Column(Boolean, default=True)
    is_active         = Column(Boolean, default=True)
    created_at        = Column(DateTime, default=datetime.now)


class LeaveApplication(Base):
    __tablename__ = 'leave_applications'
    id              = Column(Integer, primary_key=True, autoincrement=True)
    employee_id     = Column(Integer, nullable=False)
    employee_name   = Column(String(200), default="")
    leave_type_id   = Column(Integer, ForeignKey('leave_types.id'), nullable=True)
    leave_type_name = Column(String(100), default="")
    from_date       = Column(Date, nullable=False)
    to_date         = Column(Date, nullable=False)
    total_days      = Column(Integer, default=1)
    reason          = Column(Text, default="")
    status          = Column(String(20), default="Pending")
    applied_on      = Column(DateTime, default=datetime.now)
    reviewed_on     = Column(DateTime, nullable=True)
    admin_remarks   = Column(Text, default="")
