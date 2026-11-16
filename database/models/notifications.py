from sqlalchemy import Column, Integer, String, Text
from datetime import datetime
from database.models.base import Base

class SystemNotification(Base):
    """Stores system alerts, reminders, and notifications for user interaction and audit history."""
    __tablename__ = 'system_notifications'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="System")  # Finance, Inventory, HR, Library, System
    severity = Column(String(20), default="info")    # info, warning, error, success
    icon = Column(String(20), default="🔔")
    action_target = Column(String(100), nullable=True)  # e.g., "page:4", "page:14"
    action_payload = Column(Text, nullable=True)
    is_read = Column(Integer, default=0)
    is_dismissed = Column(Integer, default=0)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
