from sqlalchemy import Column, Integer, String, Boolean, Text, Float
from database.models.base import Base
from datetime import datetime

class ExpenseRecord(Base):
    """Tracks all institutional expenses to calculate Net Profit/Loss."""
    __tablename__ = 'analytics_expenses'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_date = Column(String(50), nullable=False)
    category = Column(String(100), nullable=False) # e.g. Payroll, Electricity, Maintenance
    amount = Column(Float, default=0.0)
    payment_method = Column(String(50), nullable=True)
    vendor_payee = Column(String(150), nullable=True)
    reference_no = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    academic_session = Column(String(50), nullable=True)
    
    status = Column(String(50), default="Active") # Active or Voided
    
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))