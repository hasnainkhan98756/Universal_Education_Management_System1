from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database.models.base import Base

class InventoryCategory(Base):
    __tablename__ = 'inventory_categories'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    items = relationship("InventoryItem", back_populates="category", cascade="all, delete-orphan")


class InventorySupplier(Base):
    __tablename__ = 'inventory_suppliers'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    contact_person = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    tax_number = Column(String(50), nullable=True)
    status = Column(String(20), default="Active")
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    purchases = relationship("InventoryPurchase", back_populates="supplier")


class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(50), nullable=False, unique=True)
    barcode = Column(String(50), nullable=True)
    name = Column(String(150), nullable=False)
    category_id = Column(Integer, ForeignKey('inventory_categories.id'), nullable=True)
    unit = Column(String(30), default="pcs")  # pcs, box, kg, meter, packet, etc.
    unit_cost = Column(Float, default=0.0)
    unit_sale = Column(Float, default=0.0)
    current_stock = Column(Float, default=0.0)
    min_stock_alert = Column(Float, default=5.0)
    reorder_level = Column(Float, default=10.0)
    location = Column(String(100), nullable=True) # Shelf A-1, Main Store, Lab 2, etc.
    status = Column(String(20), default="Active") # Active, Inactive, Discontinued
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    category = relationship("InventoryCategory", back_populates="items")
    transactions = relationship("StockTransaction", back_populates="item", cascade="all, delete-orphan")


class StockTransaction(Base):
    """Complete audit trail for all stock movements."""
    __tablename__ = 'inventory_transactions'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    transaction_type = Column(String(30), nullable=False)  # PURCHASE, ISSUE, RETURN, ADJUSTMENT, DAMAGE, LOSS
    quantity = Column(Float, nullable=False)  # Positive for additions, negative or absolute tracked with type
    unit_price = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    reference_no = Column(String(100), nullable=True)  # PO#, Invoice#, Issue slip#
    entity_type = Column(String(50), nullable=True)    # Student, Employee, Department, Supplier, Audit
    entity_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    transaction_date = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d"))
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    item = relationship("InventoryItem", back_populates="transactions")


class InventoryPurchase(Base):
    __tablename__ = 'inventory_purchases'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_no = Column(String(50), nullable=False, unique=True)
    supplier_id = Column(Integer, ForeignKey('inventory_suppliers.id'), nullable=True)
    invoice_date = Column(String(50), nullable=False)
    total_amount = Column(Float, default=0.0)
    payment_status = Column(String(30), default="Paid")  # Paid, Pending, Partial
    notes = Column(Text, nullable=True)
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    supplier = relationship("InventorySupplier", back_populates="purchases")
    items = relationship("InventoryPurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class InventoryPurchaseItem(Base):
    __tablename__ = 'inventory_purchase_items'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_id = Column(Integer, ForeignKey('inventory_purchases.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    purchase = relationship("InventoryPurchase", back_populates="items")
    item = relationship("InventoryItem")


class InventoryIssue(Base):
    __tablename__ = 'inventory_issues'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_no = Column(String(50), nullable=False, unique=True)
    issued_to_type = Column(String(50), nullable=False)  # Student, Employee, Department
    issued_to_id = Column(Integer, nullable=True)
    issued_to_name = Column(String(150), nullable=False)
    issue_date = Column(String(50), nullable=False)
    purpose = Column(Text, nullable=True)
    status = Column(String(30), default="Issued")  # Issued, Returned, Partially Returned
    created_at = Column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    items = relationship("InventoryIssueItem", back_populates="issue", cascade="all, delete-orphan")


class InventoryIssueItem(Base):
    __tablename__ = 'inventory_issue_items'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey('inventory_issues.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    quantity = Column(Float, default=1.0)
    notes = Column(String(255), nullable=True)

    issue = relationship("InventoryIssue", back_populates="items")
    item = relationship("InventoryItem")
