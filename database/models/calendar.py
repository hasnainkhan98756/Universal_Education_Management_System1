from sqlalchemy import Column, Integer, String, Text
from database.models.base import Base

class CalendarEvent(Base):
    """
    Stores school events, holidays, and reminders.
    These will be displayed on the Main Dashboard and School Calendar.
    """
    __tablename__ = 'calendar_events'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    academic_session = Column(String(50), nullable=False)
    title = Column(String(150), nullable=False)
    event_type = Column(String(50), nullable=True, default="General")
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    description = Column(String(500), nullable=True)