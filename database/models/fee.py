from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database.models.base import Base
from datetime import datetime

class FeeVoucher(Base):
    """Represents a monthly fee obligation/challan for a student."""
    __tablename__ = 'fee_vouchers'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    voucher_no = Column(String(50), unique=True, nullable=False) # e.g. VOU-0001
    student_id = Column(Integer, ForeignKey('students.id', ondelete="CASCADE"), nullable=False)
    
    fee_month = Column(String(50), nullable=False) # e.g. "September 2026"
    fee_type = Column(String(50), default="Monthly") # Monthly, 6-Month, Annual, Custom
    coverage_start_date = Column(String(20), nullable=True) # e.g. "2026-01-01"
    coverage_end_date = Column(String(20), nullable=True) # e.g. "2026-06-30"
    coverage_months = Column(String(500), nullable=True) # e.g. "January 2026, February 2026..."
    base_amount = Column(Float, default=0.0) # Captured from student profile at time of generation
    total_amount = Column(Float, default=0.0) # Base + Arrears/Fines - Discounts
    paid_amount = Column(Float, default=0.0)
    
    status = Column(String(50), default="Pending") # Pending, Partially Paid, Paid, Overdue
    due_date = Column(String(20), nullable=True)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    student = relationship("database.models.student.Student")
    payments = relationship("FeePayment", back_populates="voucher", cascade="all, delete-orphan")
    items = relationship("FeeVoucherItem", back_populates="voucher", cascade="all, delete-orphan")

    @property
    def voucher_number(self):
        return self.voucher_no

    @property
    def effective_items(self):
        """
        Returns real FeeVoucherItem list if present;
        Otherwise synthesizes a virtual Tuition item for legacy vouchers so
        downstream logic has ONE unified, authoritative interface without
        physically mutating historical records.
        """
        if self.items:
            return self.items
        base = self.base_amount or 0.0
        tot = self.total_amount or 0.0
        disc = max(0.0, base - tot)
        virtual = FeeVoucherItem(
            id=None,
            voucher_id=self.id,
            category="Tuition Fee",
            description=f"{self.fee_month} Tuition",
            amount=base if base > 0 else tot,
            discount=disc,
            paid_amount=self.paid_amount or 0.0
        )
        return [virtual]


class FeePayment(Base):
    """Represents an actual financial transaction/payment made against a voucher."""
    __tablename__ = 'fee_payments'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_no = Column(String(50), unique=True, nullable=False) # e.g. REC-0001
    voucher_id = Column(Integer, ForeignKey('fee_vouchers.id', ondelete="CASCADE"), nullable=False)
    
    amount_paid = Column(Float, nullable=False)
    fine_included = Column(Float, default=0.0)
    discount_included = Column(Float, default=0.0)
    
    payment_method = Column(String(50), default="Cash") # Cash, Bank, Online
    payment_date = Column(String(20), default=lambda: datetime.now().strftime("%Y-%m-%d"))
    notes = Column(String(500), nullable=True)

    # Relationships
    voucher = relationship("FeeVoucher", back_populates="payments")
    allocations = relationship("FeePaymentAllocation", back_populates="payment", cascade="all, delete-orphan")


class FeeVoucherItem(Base):
    """Represents a structured itemized charge within a fee voucher (Tuition, Transport, etc.)."""
    __tablename__ = 'fee_voucher_items'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    voucher_id = Column(Integer, ForeignKey('fee_vouchers.id', ondelete="CASCADE"), nullable=False)
    
    category = Column(String(50), nullable=False, default="Tuition Fee") # Tuition Fee, Transport Fee, Admission Fee, etc.
    description = Column(String(200), default="")
    amount = Column(Float, default=0.0) # Original amount
    discount = Column(Float, default=0.0) # Discount allocated
    paid_amount = Column(Float, default=0.0) # Amount paid towards this specific item
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def net_payable(self) -> float:
        return max(0.0, (self.amount or 0.0) - (self.discount or 0.0))

    @property
    def remaining_balance(self) -> float:
        return max(0.0, self.net_payable - (self.paid_amount or 0.0))

    # Relationships
    voucher = relationship("FeeVoucher", back_populates="items")


class FeePaymentAllocation(Base):
    """Represents an itemized allocation of a payment across categories."""
    __tablename__ = 'fee_payment_allocations'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(Integer, ForeignKey('fee_payments.id', ondelete="CASCADE"), nullable=False)
    voucher_item_id = Column(Integer, ForeignKey('fee_voucher_items.id', ondelete="SET NULL"), nullable=True)
    
    category = Column(String(50), nullable=False, default="Tuition Fee")
    description = Column(String(200), default="")
    amount_allocated = Column(Float, default=0.0)
    discount_allocated = Column(Float, default=0.0)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Relationships
    payment = relationship("FeePayment", back_populates="allocations")
    voucher_item = relationship("FeeVoucherItem")