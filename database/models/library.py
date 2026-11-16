from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database.models.base import Base


class Book(Base):
    """Library book catalog."""
    __tablename__ = 'library_books'

    id               = Column(Integer, primary_key=True, autoincrement=True)
    book_id          = Column(String(50), unique=True, nullable=False)
    title            = Column(String(255), nullable=False)
    author           = Column(String(200), default="")
    isbn             = Column(String(50), default="")
    category         = Column(String(100), default="General")
    publisher        = Column(String(200), default="")
    edition          = Column(String(50), default="")
    total_copies     = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    rack_number      = Column(String(50), default="")
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.now)

    issues = relationship("BookIssue", back_populates="book", cascade="all, delete-orphan")


class BookIssue(Base):
    """Track book issue/return per student."""
    __tablename__ = 'library_issues'

    id              = Column(Integer, primary_key=True, autoincrement=True)
    book_id         = Column(Integer, ForeignKey('library_books.id'), nullable=False)
    student_db_id   = Column(Integer, nullable=True)
    student_name    = Column(String(200), default="")
    student_sys_id  = Column(String(50), default="")
    issued_date     = Column(Date, nullable=False)
    due_date        = Column(Date, nullable=False)
    returned_date   = Column(Date, nullable=True)
    fine_per_day    = Column(Float, default=5.0)
    fine_amount     = Column(Float, default=0.0)
    status          = Column(String(20), default="Issued")
    notes           = Column(Text, default="")
    issued_at       = Column(DateTime, default=datetime.now)
    book = relationship("Book", back_populates="issues")

    @property
    def issue_date(self):
        return self.issued_date
