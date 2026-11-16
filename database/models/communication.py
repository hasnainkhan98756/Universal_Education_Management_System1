from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, Float
from database.models.base import Base
from datetime import datetime

class CommunicationProvider(Base):
    """Stores SMS/WhatsApp/Email Gateway configurations securely."""
    __tablename__ = 'comm_providers'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False) 
    channel = Column(String(50), nullable=False) # SMS, WhatsApp, Email
    is_active = Column(Boolean, default=False)
    
    # Official API Credentials
    api_url_or_host = Column(String(255), nullable=True) # SMTP Host or WhatsApp API Endpoint
    api_key_or_user = Column(String(255), nullable=True) # WhatsApp Phone Number ID / SMTP User
    api_secret_or_pass = Column(String(255), nullable=True) # WhatsApp Access Token / SMTP Pass
    sender_id = Column(String(100), nullable=True) # Business Account ID / Sender Name
    port = Column(Integer, default=587)
    use_tls = Column(Boolean, default=True)

class MessageTemplate(Base):
    """Reusable, dynamic message blueprints with variables."""
    __tablename__ = 'comm_templates'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    channel = Column(String(50), default="SMS") # SMS, WhatsApp, Email, Any
    category = Column(String(50), default="General") # Fee Reminder, Attendance Alert, Exam Result, Timetable, General
    language = Column(String(50), default="English")
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class MessageLog(Base):
    """The Universal Outbox, Queue, and Audit Trail."""
    __tablename__ = 'comm_message_log'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipient_name = Column(String(150), nullable=True)
    recipient_contact = Column(String(150), nullable=False)
    channel = Column(String(50), nullable=False) # SMS, WhatsApp, Email
    fallback_allowed = Column(Boolean, default=False) # If WhatsApp fails, try SMS
    
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    segments = Column(Integer, default=1)
    
    status = Column(String(50), default="Queued") # Queued, Sending, Sent, Delivered, Failed, Cancelled, Retrying
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Traceability links
    source_module = Column(String(100), nullable=True) # FeeVoucher, Attendance, Exam, TimetableEntry
    source_id = Column(String(100), nullable=True)
    
    provider_msg_id = Column(String(255), nullable=True) # Webhook Tracking ID
    
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sent_at = Column(String(50), nullable=True)