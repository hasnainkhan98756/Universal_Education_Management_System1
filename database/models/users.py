from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from database.models.base import Base

class User(Base):
    """
    Stores the login accounts for the application.
    As per specifications, there are only two roles: "Principal" and "Admin".
    Passwords are NOT stored as plain text, only as secure bcrypt hashes.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Login Details
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Account Type and Status
    role = Column(String(50), nullable=False)  # Will be strictly "Principal" or "Admin"
    is_active = Column(Boolean, default=True)  # Can be used to disable an Admin account if they leave
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now)