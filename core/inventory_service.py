from datetime import datetime
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from database.connection import get_session
from core.state_manager import app_state

from database.models.inventory import (
    InventoryCategory, InventorySupplier, InventoryItem,
    StockTransaction, InventoryPurchase, InventoryPurchaseItem,
    InventoryIssue, InventoryIssueItem
)
from database.models.analytics import ExpenseRecord

class InventoryService:
    """Enterprise inventory and store management engine.
    Handles multi-category stock catalog, supplier orders, issuing, returns,
    auditing adjustments, and real-time asset valuation."""

    # ──────────────────────────────────────────────────────────────────────────
    # 1. CATEGORIES
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_categories():
        db = get_session()
        try:
            return db.query(InventoryCategory).order_by(InventoryCategory.name.asc()).all()
        finally:
            db.close()

    @staticmethod
    def save_category(cat_id=None, name="", code="", description=""):
        name = name.strip()
        if not name:
            return False, "Category name is required."
        db = get_session()
        try:
            if cat_id:
                cat = db.query(InventoryCategory).filter_by(id=cat_id).first()
                if not cat:
                    return False, "Category not found."
                cat.name = name
                cat.code = code.strip()
                cat.description = description.strip()
            else:
                existing = db.query(InventoryCategory).filter(func.lower(InventoryCategory.name) == name.lower()).first()
                if existing:
                    return False, f"Category '{name}' already exists."
                cat = InventoryCategory(name=name, code=code.strip(), description=description.strip())
                db.add(cat)
            db.commit()
            app_state.notify_data_changed()
            return True, "Category saved successfully."
        except Exception as e:
            db.rollback()
            return False, f"Error saving category: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def delete_category(cat_id):
        db = get_session()
        try:
            cat = db.query(InventoryCategory).filter_by(id=cat_id).first()
            if not cat:
                return False, "Category not found."
            # Check if any items belong to this category
            has_items = db.query(InventoryItem).filter_by(category_id=cat_id).first()
            if has_items:
                return False, "Cannot delete category that contains items. Please reassign or delete items first."
            db.delete(cat)
            db.commit()
            app_state.notify_data_changed()
            return True, "Category deleted."
        except Exception as e:
            db.rollback()
            return False, f"Error deleting category: {str(e)}"
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. SUPPLIERS / VENDORS
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_suppliers(status_filter=None):
        db = get_session()
        try:
            q = db.query(InventorySupplier)
            if status_filter:
                q = q.filter_by(status=status_filter)
            return q.order_by(InventorySupplier.name.asc()).all()
        finally:
            db.close()

    @staticmethod
    def save_supplier(supplier_id=None, name="", contact_person="", phone="", email="", address="", tax_number="", status="Active"):
        name = name.strip()
        if not name:
            return False, "Supplier name is required."
        db = get_session()
        try:
            if supplier_id:
                s = db.query(InventorySupplier).filter_by(id=supplier_id).first()
                if not s:
                    return False, "Supplier not found."
                s.name = name
                s.contact_person = contact_person.strip()
                s.phone = phone.strip()
                s.email = email.strip()
                s.address = address.strip()
                s.tax_number = tax_number.strip()
                s.status = status
            else:
                s = InventorySupplier(
                    name=name, contact_person=contact_person.strip(), phone=phone.strip(),
                    email=email.strip(), address=address.strip(), tax_number=tax_number.strip(),
                    status=status
                )
                db.add(s)
            db.commit()
            app_state.notify_data_changed()
            return True, "Supplier saved successfully."
        except Exception as e:
            db.rollback()
            return False, f"Error saving supplier: {str(e)}"
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. ITEMS CATALOG
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_items(category_id=None, search=None, low_stock_only=False):
        db = get_session()
        try:
            q = db.query(InventoryItem).options(joinedload(InventoryItem.category))
            if category_id and category_id != "All":
                q = q.filter(InventoryItem.category_id == int(category_id))
            if low_stock_only:
                q = q.filter(InventoryItem.current_stock <= InventoryItem.min_stock_alert)
            if search:
                term = f"%{search.strip()}%"
                q = q.filter(or_(
                    InventoryItem.name.ilike(term),
                    InventoryItem.sku.ilike(term),
                    InventoryItem.barcode.ilike(term),
                    InventoryItem.location.ilike(term)
                ))
            return q.order_by(InventoryItem.name.asc()).all()
        finally:
            db.close()

    @staticmethod
    def get_item(item_id):
        db = get_session()
        try:
            return db.query(InventoryItem).filter_by(id=item_id).first()
        finally:
            db.close()

    @staticmethod
    def save_item(item_id=None, sku="", barcode="", name="", category_id=None,
                  unit="pcs", unit_cost=0.0, unit_sale=0.0, current_stock=0.0,
                  min_stock_alert=5.0, reorder_level=10.0, location="", status="Active"):
        name = name.strip()
        sku = sku.strip()
        if not name:
            return False, "Item name is required."
        if not sku:
            sku = f"ITM-{int(datetime.now().timestamp())}"

        db = get_session()
        try:
            if item_id:
                item = db.query(InventoryItem).filter_by(id=item_id).first()
                if not item:
                    return False, "Item not found."
                # Check unique SKU
                existing_sku = db.query(InventoryItem).filter(InventoryItem.sku == sku, InventoryItem.id != item_id).first()
                if existing_sku:
                    return False, f"SKU '{sku}' is already used by another item."
                item.sku = sku
                item.barcode = barcode.strip() if barcode else None
                item.name = name
                item.category_id = category_id if category_id else None
                item.unit = unit
                item.unit_cost = float(unit_cost)
                item.unit_sale = float(unit_sale)
                item.min_stock_alert = float(min_stock_alert)
                item.reorder_level = float(reorder_level)
                item.location = location.strip() if location else None
                item.status = status
                item.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                existing_sku = db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
                if existing_sku:
                    return False, f"SKU '{sku}' already exists."
                item = InventoryItem(
                    sku=sku, barcode=barcode.strip() if barcode else None,
                    name=name, category_id=category_id if category_id else None,
                    unit=unit, unit_cost=float(unit_cost), unit_sale=float(unit_sale),
                    current_stock=float(current_stock), min_stock_alert=float(min_stock_alert),
                    reorder_level=float(reorder_level), location=location.strip() if location else None,
                    status=status
                )
                db.add(item)
                db.flush()

                # If initial stock > 0, log opening stock transaction
                if float(current_stock) > 0:
                    tx = StockTransaction(
                        item_id=item.id,
                        transaction_type="OPENING_STOCK",
                        quantity=float(current_stock),
                        unit_price=float(unit_cost),
                        total_amount=float(current_stock) * float(unit_cost),
                        reference_no="INITIAL",
                        entity_type="SYSTEM",
                        notes="Opening inventory balance recorded upon item creation.",
                        transaction_date=datetime.now().strftime("%Y-%m-%d")
                    )
                    db.add(tx)

            db.commit()
            app_state.notify_data_changed()
            return True, "Item saved successfully."
        except Exception as e:
            db.rollback()
            return False, f"Error saving item: {str(e)}"
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. PURCHASES / STOCK IN (With Optional Expense Auto-Logging)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def record_purchase(supplier_id, invoice_date, items_list, notes="", payment_status="Paid", auto_log_expense=True):
        """
        Records a purchase order / stock-in receipt.
        items_list format: [{'item_id': int, 'quantity': float, 'unit_cost': float}]
        Atomically updates current stock on all items and writes ledger transactions.
        """
        if not items_list:
            return False, "At least one item is required for purchase."
        
        db = get_session()
        try:
            purchase_no = f"PO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            total_amount = sum(float(it.get('quantity', 1)) * float(it.get('unit_cost', 0)) for it in items_list)

            purchase = InventoryPurchase(
                purchase_no=purchase_no,
                supplier_id=supplier_id if supplier_id else None,
                invoice_date=invoice_date,
                total_amount=total_amount,
                payment_status=payment_status,
                notes=notes
            )
            db.add(purchase)
            db.flush()

            supplier_name = "Supplier"
            if supplier_id:
                sup = db.query(InventorySupplier).filter_by(id=supplier_id).first()
                if sup:
                    supplier_name = sup.name

            for it in items_list:
                iid = int(it['item_id'])
                qty = float(it['quantity'])
                cost = float(it.get('unit_cost', 0))
                subtotal = qty * cost

                # Create purchase line item
                p_item = InventoryPurchaseItem(
                    purchase_id=purchase.id,
                    item_id=iid,
                    quantity=qty,
                    unit_cost=cost,
                    total_cost=subtotal
                )
                db.add(p_item)

                # Increment stock
                item_obj = db.query(InventoryItem).filter_by(id=iid).first()
                if item_obj:
                    item_obj.current_stock += qty
                    item_obj.unit_cost = cost # Update latest purchase cost
                    item_obj.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Record transaction
                tx = StockTransaction(
                    item_id=iid,
                    transaction_type="PURCHASE",
                    quantity=qty,
                    unit_price=cost,
                    total_amount=subtotal,
                    reference_no=purchase_no,
                    entity_type="Supplier",
                    entity_id=supplier_id,
                    notes=f"Purchase from {supplier_name}. {notes}".strip(),
                    transaction_date=invoice_date
                )
                db.add(tx)

            # Auto-log expense in analytics_expenses if requested
            if auto_log_expense and total_amount > 0:
                current_session = app_state.get_setting("session", "Default")
                exp = ExpenseRecord(
                    expense_date=invoice_date,
                    category="Inventory Purchases",
                    amount=total_amount,
                    payment_method="Cash",
                    vendor_payee=supplier_name,
                    reference_no=purchase_no,
                    description=f"Automated purchase entry for {len(items_list)} inventory item(s).",
                    academic_session=current_session,
                    status="Active"
                )
                db.add(exp)

            db.commit()
            app_state.notify_data_changed()
            return True, f"Purchase {purchase_no} recorded successfully. Stock updated."
        except Exception as e:
            db.rollback()
            return False, f"Error recording purchase: {str(e)}"
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. ISSUES / STOCK OUT
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def record_issue(issued_to_type, issued_to_id, issued_to_name, issue_date, items_list, purpose=""):
        """
        Issues items to a Student, Employee, or Department.
        items_list format: [{'item_id': int, 'quantity': float, 'notes': str}]
        Atomically decrements stock and writes ledger transactions.
        """
        if not items_list:
            return False, "At least one item is required for issuance."
        if not issued_to_name.strip():
            return False, "Recipient name is required."

        db = get_session()
        try:
            # Check stock availability first
            for it in items_list:
                iid = int(it['item_id'])
                qty = float(it['quantity'])
                item_obj = db.query(InventoryItem).filter_by(id=iid).first()
                if not item_obj:
                    return False, f"Item ID {iid} not found."
                if item_obj.current_stock < qty:
                    return False, f"Insufficient stock for '{item_obj.name}'. Current: {item_obj.current_stock}, Requested: {qty}."

            issue_no = f"ISS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            issue = InventoryIssue(
                issue_no=issue_no,
                issued_to_type=issued_to_type,
                issued_to_id=issued_to_id if issued_to_id else None,
                issued_to_name=issued_to_name.strip(),
                issue_date=issue_date,
                purpose=purpose.strip(),
                status="Issued"
            )
            db.add(issue)
            db.flush()

            for it in items_list:
                iid = int(it['item_id'])
                qty = float(it['quantity'])
                item_notes = it.get('notes', '')

                i_item = InventoryIssueItem(
                    issue_id=issue.id,
                    item_id=iid,
                    quantity=qty,
                    notes=item_notes
                )
                db.add(i_item)

                # Decrement stock
                item_obj = db.query(InventoryItem).filter_by(id=iid).first()
                item_obj.current_stock -= qty
                item_obj.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Record transaction
                tx = StockTransaction(
                    item_id=iid,
                    transaction_type="ISSUE",
                    quantity=-qty,
                    unit_price=item_obj.unit_cost,
                    total_amount=qty * item_obj.unit_cost,
                    reference_no=issue_no,
                    entity_type=issued_to_type,
                    entity_id=issued_to_id,
                    notes=f"Issued to {issued_to_name} ({issued_to_type}). {purpose}".strip(),
                    transaction_date=issue_date
                )
                db.add(tx)

            db.commit()
            app_state.notify_data_changed()
            return True, f"Issue {issue_no} completed successfully. Stock decremented."
        except Exception as e:
            db.rollback()
            return False, f"Error issuing items: {str(e)}"
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. ADJUSTMENTS & AUDIT MOVEMENTS (Damage, Loss, Surplus)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def record_adjustment(item_id, adjustment_type, quantity, reason="", date_str=None):
        """
        Adjustment types: ADJUSTMENT (positive or negative), DAMAGE, LOSS, RETURN
        """
        if quantity == 0:
            return False, "Quantity cannot be zero."
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")

        db = get_session()
        try:
            item = db.query(InventoryItem).filter_by(id=item_id).first()
            if not item:
                return False, "Item not found."

            qty = float(quantity)
            if adjustment_type in ["DAMAGE", "LOSS"]:
                # Damage and Loss always reduce current stock
                if abs(qty) > item.current_stock:
                    return False, f"Cannot record damage/loss greater than current stock ({item.current_stock})."
                applied_qty = -abs(qty)
            elif adjustment_type == "RETURN":
                # Return increases stock
                applied_qty = abs(qty)
            else:
                # General adjustment (can be positive or negative)
                applied_qty = qty

            item.current_stock += applied_qty
            item.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            tx = StockTransaction(
                item_id=item_id,
                transaction_type=adjustment_type,
                quantity=applied_qty,
                unit_price=item.unit_cost,
                total_amount=abs(applied_qty) * item.unit_cost,
                reference_no="ADJ-AUDIT",
                entity_type="Audit",
                notes=reason.strip(),
                transaction_date=date_str
            )
            db.add(tx)
            db.commit()
            app_state.notify_data_changed()
            return True, f"Stock adjustment for '{item.name}' recorded. New stock: {item.current_stock}."
        except Exception as e:
            db.rollback()
            return False, f"Error adjusting stock: {str(e)}"
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. AUDIT TRAIL & VALUATION
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_transactions(item_id=None, type_filter=None, limit=200):
        db = get_session()
        try:
            q = db.query(StockTransaction).options(
                joinedload(StockTransaction.item).joinedload(InventoryItem.category)
            )
            if item_id:
                q = q.filter_by(item_id=item_id)
            if type_filter and type_filter != "All":
                q = q.filter_by(transaction_type=type_filter)
            return q.order_by(StockTransaction.id.desc()).limit(limit).all()
        finally:
            db.close()

    @staticmethod
    def get_low_stock_items():
        db = get_session()
        try:
            return db.query(InventoryItem).options(joinedload(InventoryItem.category)).filter(
                InventoryItem.current_stock <= InventoryItem.min_stock_alert,
                InventoryItem.status == "Active"
            ).all()
        finally:
            db.close()

    @staticmethod
    def get_inventory_valuation():
        """Returns overview statistics: total distinct items, total units in store, total asset cost."""
        db = get_session()
        try:
            items = db.query(InventoryItem).filter_by(status="Active").all()
            total_items = len(items)
            total_units = sum(i.current_stock for i in items)
            total_valuation = sum(i.current_stock * i.unit_cost for i in items)
            low_stock_count = sum(1 for i in items if i.current_stock <= i.min_stock_alert)
            return {
                "total_items": total_items,
                "total_units": total_units,
                "total_valuation": round(total_valuation, 2),
                "low_stock_count": low_stock_count
            }
        finally:
            db.close()
