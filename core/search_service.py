from sqlalchemy import or_, func
from database.connection import get_session
from database.models.student import Student
from database.models.hr import Employee
from database.models.fee import FeeVoucher
from database.models.inventory import InventoryItem
from database.models.analytics import ExpenseRecord
from database.models.documents import ManagedDocument, DocumentHistory

class GlobalSearchService:
    """Universal search across students, staff, fee vouchers, inventory, expenses, and documents."""

    @staticmethod
    def search_all(query_str: str, limit_per_section=5) -> list:
        q = (query_str or "").strip()
        if not q or len(q) < 2:
            return []

        term = f"%{q}%"
        results = []
        db = get_session()
        try:
            # 1. STUDENTS (Page 3)
            try:
                students = db.query(Student).filter(
                    or_(
                        Student.first_name.ilike(term),
                        Student.last_name.ilike(term),
                        Student.student_id.ilike(term),
                        Student.admission_number.ilike(term),
                        Student.phone.ilike(term)
                    )
                ).limit(limit_per_section).all()
                for s in students:
                    s_name = f"{s.first_name} {s.last_name or ''}".strip()
                    results.append({
                        "category": "Students",
                        "icon_name": "graduation-cap",
                        "title": s_name,
                        "subtitle": f"ID: {s.student_id} • Adm: {s.admission_number or '—'} • Phone: {s.phone or '—'}",
                        "page_index": 3,
                        "payload": {"student_id": s.student_id, "id": s.id, "admission_number": s.admission_number}
                    })
            except Exception as e:
                print(f"Student search error: {e}")

            # 2. STAFF / TEACHERS (Page 7)
            try:
                staff = db.query(Employee).filter(
                    or_(
                        Employee.first_name.ilike(term),
                        Employee.last_name.ilike(term),
                        Employee.emp_id.ilike(term),
                        Employee.designation.ilike(term),
                        Employee.phone.ilike(term),
                        Employee.email.ilike(term)
                    )
                ).limit(limit_per_section).all()
                for emp in staff:
                    emp_name = f"{emp.first_name} {emp.last_name or ''}".strip()
                    results.append({
                        "category": "Faculty & Staff",
                        "icon_name": "users",
                        "title": emp_name,
                        "subtitle": f"ID: {emp.emp_id} • Designation: {emp.designation or 'Faculty'} • Phone: {emp.phone or '—'}",
                        "page_index": 7,
                        "payload": {"employee_id": emp.emp_id, "id": emp.id}
                    })
            except Exception as e:
                print(f"Staff search error: {e}")

            # 3. FEE VOUCHERS (Page 4)
            try:
                vouchers = db.query(FeeVoucher).join(Student, FeeVoucher.student_id == Student.id, isouter=True).filter(
                    or_(
                        FeeVoucher.voucher_no.ilike(term),
                        FeeVoucher.fee_month.ilike(term),
                        Student.first_name.ilike(term),
                        Student.last_name.ilike(term),
                        Student.student_id.ilike(term)
                    )
                ).limit(limit_per_section).all()
                for v in vouchers:
                    s_name = v.student.name if v.student else "Student"
                    results.append({
                        "category": "Fee Vouchers",
                        "icon_name": "receipt",
                        "title": f"Voucher #{v.voucher_no}",
                        "subtitle": f"Student: {s_name} • Due: Rs. {v.total_amount:,.0f} • Paid: Rs. {v.paid_amount:,.0f} • Status: {v.status}",
                        "page_index": 4,
                        "payload": {"voucher_id": v.id, "voucher_no": v.voucher_no}
                    })
            except Exception as e:
                print(f"Voucher search error: {e}")

            # 4. INVENTORY ITEMS (Page 14)
            try:
                items = db.query(InventoryItem).filter(
                    or_(
                        InventoryItem.name.ilike(term),
                        InventoryItem.sku.ilike(term),
                        InventoryItem.barcode.ilike(term),
                        InventoryItem.location.ilike(term)
                    )
                ).limit(limit_per_section).all()
                for it in items:
                    results.append({
                        "category": "Inventory",
                        "icon_name": "package",
                        "title": it.name,
                        "subtitle": f"SKU: {it.sku} • Stock: {it.current_stock:.0f} {it.unit} • Unit Cost: Rs. {it.unit_cost:,.2f}",
                        "page_index": 14,
                        "payload": {"item_id": it.id, "sku": it.sku}
                    })
            except Exception:
                pass

            # 5. EXPENSES (Page 10)
            try:
                expenses = db.query(ExpenseRecord).filter(
                    ExpenseRecord.status == "Active",
                    or_(
                        ExpenseRecord.category.ilike(term),
                        ExpenseRecord.vendor_payee.ilike(term),
                        ExpenseRecord.reference_no.ilike(term),
                        ExpenseRecord.description.ilike(term)
                    )
                ).limit(limit_per_section).all()
                for exp in expenses:
                    results.append({
                        "category": "Expenses",
                        "icon_name": "trending-down",
                        "title": f"{exp.category}: Rs. {exp.amount:,.0f}",
                        "subtitle": f"Payee: {exp.vendor_payee or '—'} • Date: {exp.expense_date} • Ref: {exp.reference_no or '—'}",
                        "page_index": 10,
                        "payload": {"expense_id": exp.id}
                    })
            except Exception:
                pass

            # 6. DOCUMENTS (Page 15)
            try:
                docs = db.query(ManagedDocument).filter(
                    ManagedDocument.is_archived == 0,
                    or_(
                        ManagedDocument.title.ilike(term),
                        ManagedDocument.original_filename.ilike(term),
                        ManagedDocument.file_category.ilike(term),
                        ManagedDocument.tags.ilike(term)
                    )
                ).limit(limit_per_section).all()
                for doc in docs:
                    results.append({
                        "category": "Documents",
                        "icon_name": "file-text",
                        "title": doc.title,
                        "subtitle": f"Category: {doc.file_category} • File: {doc.original_filename}",
                        "page_index": 15,
                        "payload": {"document_id": doc.id, "path": doc.storage_path}
                    })
            except Exception:
                pass

        finally:
            db.close()

        return results
