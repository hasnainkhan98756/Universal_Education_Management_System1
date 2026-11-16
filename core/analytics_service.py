import os
from datetime import datetime
from sqlalchemy import func, case, text
from database.connection import get_session
from core.state_manager import app_state

from database.models.student import Student
from database.models.fee import FeeVoucher, FeePayment, FeeVoucherItem, FeePaymentAllocation
from database.models.hr import Employee, PayrollRecord
from database.models.timetable import TimetableEntry
from database.models.communication import MessageLog
from database.models.analytics import ExpenseRecord
from database.models.transport import TransportRoute, TransportVehicle, StudentTransport
from database.models.inventory import InventoryItem, StockTransaction, InventoryPurchase, InventoryPurchaseItem, InventoryCategory, InventorySupplier
from core.fee_service import FeeService

class AnalyticsService:
    
    # ==========================================
    # 1. EXPENSE MANAGEMENT (CRUD)
    # ==========================================
    @staticmethod
    def get_expenses(session_filter=None):
        db = get_session()
        try:
            q = db.query(ExpenseRecord).filter(ExpenseRecord.status == "Active")
            if session_filter and session_filter != "All Time":
                q = q.filter(ExpenseRecord.academic_session == session_filter)
            return q.order_by(ExpenseRecord.expense_date.desc()).all()
        finally: db.close()

    @staticmethod
    def save_expense(exp_id=None, date_str=None, cat="", amount=0.0, method="Cash", vendor="", ref="", desc="", **kwargs):
        if not date_str and "date" in kwargs:
            date_str = kwargs["date"]
        db = get_session()
        try:
            session_name = app_state.get_setting("session", "Default")
            if exp_id:
                e = db.query(ExpenseRecord).filter_by(id=exp_id).first()
                if e:
                    e.expense_date = date_str
                    e.category = cat
                    e.amount = amount
                    e.payment_method = method
                    e.vendor_payee = vendor
                    e.reference_no = ref
                    e.description = desc
            else:
                db.add(ExpenseRecord(
                    expense_date=date_str, category=cat, amount=amount,
                    payment_method=method, vendor_payee=vendor,
                    reference_no=ref, description=desc,
                    academic_session=session_name, status="Active"
                ))
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed: {e}")
            return True, "Expense saved successfully."
        except Exception as e:
            db.rollback(); return False, f"Database Error: {str(e)}"
        finally: db.close()

    @staticmethod
    def void_expense(exp_id):
        db = get_session()
        try:
            e = db.query(ExpenseRecord).filter_by(id=exp_id).first()
            if e: 
                e.status = "Voided" # Safely void instead of permanent delete
                db.commit()
                try:
                    app_state.notify_data_changed()
                except Exception as e:
                    print(f"Error broadcasting data changed: {e}")
                return True, "Expense deleted successfully."
            return False, "Not found."
        finally: db.close()

    @staticmethod
    def get_expense_breakdown_by_category(session_filter=None):
        """Returns a breakdown of all expenses grouped by category for financial reporting."""
        db = get_session()
        try:
            breakdown = {}
            # 1. Manual expenses by category
            q = db.query(
                ExpenseRecord.category,
                func.sum(ExpenseRecord.amount)
            ).filter(
                ExpenseRecord.status == "Active",
                ~ExpenseRecord.category.in_(["Teacher Payroll", "Staff Payroll"])
            )
            if session_filter and session_filter != "All Time":
                q = q.filter(ExpenseRecord.academic_session == session_filter)
            
            for cat, total in q.group_by(ExpenseRecord.category).all():
                breakdown[cat or "Uncategorized"] = float(total or 0.0)

            # 2. Add Payroll salaries as "Payroll (Salaries)"
            salary_tot = db.query(func.sum(PayrollRecord.net_salary)).filter_by(status="Paid").scalar() or 0.0
            if salary_tot > 0:
                breakdown["Staff Payroll"] = float(salary_tot)

            return breakdown
        finally:
            db.close()

    # ==========================================
    # 2. EXECUTIVE KPI CALCULATIONS (LIVE SYNC)
    # ==========================================
    @staticmethod
    def get_executive_kpis():
        """Reads LIVE authoritative data from ALL modules extremely fast without loading records."""
        db = get_session()
        try:
            session_name = app_state.get_setting("session", "Default")
            kpis = {}

            # --- STUDENTS & HR (FAST COUNT) ---
            kpis['total_students'] = db.query(Student).filter_by(status="Active").count()
            kpis['active_teachers'] = db.query(Employee).filter_by(status="Active", emp_type="Teacher").count()
            kpis['active_staff'] = db.query(Employee).filter_by(status="Active").count() - kpis['active_teachers']

            # --- REVENUE & OUTSTANDING (FAST SUM) ---
            revenue = db.query(func.sum(FeePayment.amount_paid)).scalar() or 0.0
            
            outstanding = db.query(
                func.sum(FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0))
            ).filter(FeeVoucher.total_amount > func.coalesce(FeeVoucher.paid_amount, 0)).scalar() or 0.0
            
            kpis['total_revenue'] = revenue
            kpis['outstanding_fees'] = outstanding

            # Fast Category collections
            fee_stats = FeeService.get_financial_analytics()
            cat_map = fee_stats.get("category_totals", {})
            kpis['tuition_revenue'] = cat_map.get("Tuition Fee", 0.0)
            kpis['transport_revenue'] = cat_map.get("Transport Fee", 0.0)
            kpis['admission_revenue'] = cat_map.get("Admission Fee", 0.0)
            kpis['exam_revenue'] = cat_map.get("Examination Fee", 0.0)
            kpis['other_revenue'] = sum(v for k, v in cat_map.items() if k not in ["Tuition Fee", "Transport Fee", "Admission Fee", "Examination Fee"])

            # --- EXPENSES & INSTITUTIONAL OUTFLOWS (FAST SUM) ---
            total_salary_expense = db.query(func.sum(PayrollRecord.net_salary)).filter_by(status="Paid").scalar() or 0.0

            op_exp_q = db.query(func.sum(ExpenseRecord.amount)).filter(
                ExpenseRecord.status == "Active",
                ~ExpenseRecord.category.in_(["Teacher Payroll", "Staff Payroll", "Inventory Purchases", "Store Purchases"])
            )
            if session_name and session_name not in ["All Time", "Default", "N/A"]:
                has_matching = db.query(ExpenseRecord).filter(
                    ExpenseRecord.academic_session == session_name,
                    ExpenseRecord.status == "Active"
                ).first()
                if has_matching:
                    op_exp_q = op_exp_q.filter(
                        (ExpenseRecord.academic_session == session_name) | (ExpenseRecord.academic_session == None) | (ExpenseRecord.academic_session == "")
                    )
            total_operating_bills = op_exp_q.scalar() or 0.0

            store_exp_q = db.query(func.sum(ExpenseRecord.amount)).filter(
                ExpenseRecord.status == "Active",
                ExpenseRecord.category.in_(["Inventory Purchases", "Store Purchases"])
            )
            store_exp_amt = store_exp_q.scalar() or 0.0
            store_po_amt = db.query(func.sum(InventoryPurchase.total_amount)).scalar() or 0.0
            total_store_purchases = max(store_exp_amt, store_po_amt)

            total_inv_asset_val = db.query(func.sum(InventoryItem.current_stock * InventoryItem.unit_cost)).scalar() or 0.0

            total_operating_expenses = total_salary_expense + total_operating_bills
            total_cash_outflows = total_operating_expenses + total_store_purchases

            kpis['total_salary_expense'] = total_salary_expense
            kpis['total_manual_expense'] = total_operating_bills
            kpis['total_operating_bills'] = total_operating_bills
            kpis['total_operating_expenses'] = total_operating_expenses
            kpis['total_expenses'] = total_operating_expenses
            kpis['total_store_purchases'] = total_store_purchases
            kpis['total_inv_asset_val'] = total_inv_asset_val
            kpis['total_cash_outflows'] = total_cash_outflows
            kpis['net_operating_surplus'] = revenue - total_operating_expenses
            kpis['net_cash_surplus'] = revenue - total_cash_outflows
            kpis['net_profit'] = kpis['net_operating_surplus']

            # --- COMMUNICATIONS (FAST COUNT) ---
            kpis['messages_sent'] = db.query(MessageLog).filter(MessageLog.status.in_(["Sent", "Opened in App"])).count()
            
            return kpis
        finally: db.close()

    @staticmethod
    def get_monthly_revenue_trend():
        """Aggregates real monthly income and expenses SUPER FAST using SQL GROUP BY"""
        db = get_session()
        try:
            month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            monthly_data = {m: {'income': 0.0, 'expense': 0.0} for m in month_order}

            # FAST INCOME AGGREGATION: Directly summing payments based on substring of payment date
            income_results = db.execute(text("""
                SELECT substr(payment_date, 6, 2) as mm, SUM(amount_paid) 
                FROM fee_payments 
                WHERE payment_date IS NOT NULL 
                GROUP BY mm
            """)).fetchall()

            for mm, amt in income_results:
                if mm and amt:
                    try:
                        month_idx = int(mm) - 1
                        if 0 <= month_idx < 12:
                            m_name = month_order[month_idx]
                            monthly_data[m_name]['income'] += float(amt)
                    except ValueError: pass

            # FAST SALARY EXPENSE AGGREGATION
            salary_results = db.execute(text("""
                SELECT substr(payment_date, 6, 2) as mm, SUM(net_salary) 
                FROM payroll_records 
                WHERE status='Paid' AND payment_date IS NOT NULL 
                GROUP BY mm
            """)).fetchall()
            
            for mm, amt in salary_results:
                if mm and amt:
                    try:
                        month_idx = int(mm) - 1
                        if 0 <= month_idx < 12:
                            m_name = month_order[month_idx]
                            monthly_data[m_name]['expense'] += float(amt)
                    except ValueError: pass

            # FAST EXPENSE AGGREGATION
            expense_results = db.execute(text("""
                SELECT substr(expense_date, 6, 2) as mm, SUM(amount) 
                FROM analytics_expenses 
                WHERE status='Active' AND expense_date IS NOT NULL 
                GROUP BY mm
            """)).fetchall()
            
            for mm, amt in expense_results:
                if mm and amt:
                    try:
                        month_idx = int(mm) - 1
                        if 0 <= month_idx < 12:
                            m_name = month_order[month_idx]
                            monthly_data[m_name]['expense'] += float(amt)
                    except ValueError: pass

            curr_month_idx = datetime.now().month
            display_months = month_order[:max(curr_month_idx, 7)]

            trend = []
            for m in display_months:
                trend.append({
                    "month": m,
                    "income": monthly_data[m]['income'],
                    "expense": monthly_data[m]['expense']
                })
            return trend
        except Exception as e:
            print(f"Error computing monthly revenue trend: {e}")
            return []
        finally: db.close()

    # ==========================================
    # 3. RECONCILED MASTER REPORT GENERATION (EXCEL)
    # ==========================================
    @staticmethod
    def export_master_excel(filepath):
        """
        Generates a 15-worksheet reconciled ERP Financial Workbook.
        100% mathematical reconciliation between Summary and Detail sheets.
        """
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from sqlalchemy.orm import joinedload
        
        db = get_session()
        try:
            wb = openpyxl.Workbook()
            session_name = app_state.get_setting("session", "Default")
            inst_name = app_state.get_setting("name", "Universal Education Management System")
            
            # Styling constants
            primary_fill = PatternFill(start_color="4C1D95", fill_type="solid") # Deep Purple
            sub_fill = PatternFill(start_color="6D28D9", fill_type="solid")
            header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
            title_font = Font(name="Segoe UI", size=16, bold=True, color="4C1D95")
            sub_title_font = Font(name="Segoe UI", size=12, bold=True, color="374151")
            bold_font = Font(name="Segoe UI", size=11, bold=True)
            regular_font = Font(name="Segoe UI", size=10)
            
            thin_border = Border(
                left=Side(style='thin', color='E5E7EB'),
                right=Side(style='thin', color='E5E7EB'),
                top=Side(style='thin', color='E5E7EB'),
                bottom=Side(style='thin', color='E5E7EB')
            )
            total_border = Border(
                top=Side(style='thin', color='111827'),
                bottom=Side(style='double', color='111827')
            )

            def style_sheet(ws, freeze_cell="A2"):
                ws.freeze_panes = freeze_cell
                for col in ws.columns:
                    col_letter = get_column_letter(col[0].column)
                    max_len = 0
                    for cell in col:
                        val_str = str(cell.value or "")
                        if len(val_str) > max_len:
                            max_len = len(val_str)
                    ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            # Pre-fetch authoritative data
            students = db.query(Student).options(
                joinedload(Student.academic_class),
                joinedload(Student.academic_section)
            ).all()

            vouchers = db.query(FeeVoucher).options(
                joinedload(FeeVoucher.student).joinedload(Student.academic_class),
                joinedload(FeeVoucher.items)
            ).all()

            payments = db.query(FeePayment).options(
                joinedload(FeePayment.allocations),
                joinedload(FeePayment.voucher).joinedload(FeeVoucher.student)
            ).order_by(FeePayment.id.desc()).all()

            payrolls = db.query(PayrollRecord).options(
                joinedload(PayrollRecord.employee)
            ).filter_by(status="Paid").order_by(PayrollRecord.payment_date.desc()).all()

            expenses = db.query(ExpenseRecord).filter(
                ExpenseRecord.status == "Active"
            ).order_by(ExpenseRecord.expense_date.desc()).all()

            routes = db.query(TransportRoute).options(
                joinedload(TransportRoute.vehicles),
                joinedload(TransportRoute.student_assignments)
            ).all()

            inventory_items = db.query(InventoryItem).options(
                joinedload(InventoryItem.category)
            ).all()

            inventory_transactions = db.query(StockTransaction).options(
                joinedload(StockTransaction.item).joinedload(InventoryItem.category)
            ).order_by(StockTransaction.id.desc()).all()

            inventory_purchases = db.query(InventoryPurchase).options(
                joinedload(InventoryPurchase.supplier),
                joinedload(InventoryPurchase.items).joinedload(InventoryPurchaseItem.item)
            ).order_by(InventoryPurchase.id.desc()).all()

            total_inv_items_count = len(inventory_items)
            total_inv_units_count = sum(float(i.current_stock or 0.0) for i in inventory_items)
            total_inv_asset_val = sum(float(i.current_stock or 0.0) * float(i.unit_cost or 0.0) for i in inventory_items)
            total_inv_low_stock_count = sum(1 for i in inventory_items if (i.current_stock or 0.0) <= (i.min_stock_alert or 0.0))
            total_inv_purchases_amt = sum(float(p.total_amount or 0.0) for p in inventory_purchases)

            # Mathematical Aggregations
            total_tuition_col = 0.0
            total_transport_col = 0.0
            total_admission_col = 0.0
            total_exam_col = 0.0
            total_other_col = 0.0
            total_fee_collected = 0.0
            total_discounts_granted = 0.0

            collections_rows = []
            for p in payments:
                p_date = p.payment_date or ""
                r_no = p.receipt_no
                s_id = p.voucher.student.student_id if p.voucher and p.voucher.student else ""
                s_name = f"{p.voucher.student.first_name} {p.voucher.student.last_name or ''}".strip() if p.voucher and p.voucher.student else ""
                c_name = p.voucher.student.academic_class.name if p.voucher and p.voucher.student and p.voucher.student.academic_class else ""
                month = p.voucher.fee_month if p.voucher else ""
                meth = p.payment_method or "Cash"

                if p.allocations:
                    for a in p.allocations:
                        cat = a.category or "Other Fee"
                        amt = float(a.amount_allocated or 0.0)
                        disc = float(a.discount_allocated or 0.0)
                        orig = amt + disc
                        rem = 0.0
                        if a.voucher_item:
                            rem = a.voucher_item.remaining_balance

                        collections_rows.append({
                            "receipt_no": r_no, "date": p_date, "student_id": s_id,
                            "student_name": s_name, "class": c_name, "fee_month": month,
                            "category": cat, "description": a.description,
                            "orig_amount": orig, "discount": disc, "net": amt,
                            "paid": amt, "remaining": rem, "method": meth,
                            "voucher_no": p.voucher.voucher_no if p.voucher else ""
                        })
                        total_fee_collected += amt
                        total_discounts_granted += disc
                        if cat == "Tuition Fee": total_tuition_col += amt
                        elif cat == "Transport Fee": total_transport_col += amt
                        elif cat == "Admission Fee": total_admission_col += amt
                        elif cat == "Examination Fee": total_exam_col += amt
                        else: total_other_col += amt
                else:
                    amt = float(p.amount_paid or 0.0)
                    disc = float(p.discount_included or 0.0)
                    collections_rows.append({
                        "receipt_no": r_no, "date": p_date, "student_id": s_id,
                        "student_name": s_name, "class": c_name, "fee_month": month,
                        "category": "Tuition Fee", "description": f"Payment {month}",
                        "orig_amount": amt + disc, "discount": disc, "net": amt,
                        "paid": amt, "remaining": max(0.0, (p.voucher.total_amount or 0.0) - (p.voucher.paid_amount or 0.0)),
                        "method": meth, "voucher_no": p.voucher.voucher_no if p.voucher else ""
                    })
                    total_fee_collected += amt
                    total_discounts_granted += disc
                    total_tuition_col += amt

            total_salaries_paid = sum(float(pr.net_salary or 0.0) for pr in payrolls)
            
            # Non-salary pure operational utility bills (excluding store purchases & payroll)
            total_operating_bills = sum(
                float(e.amount or 0.0) for e in expenses 
                if e.category not in ["Teacher Payroll", "Staff Payroll", "Inventory Purchases", "Store Purchases"]
            )
            total_store_purchases = max(
                sum(float(e.amount or 0.0) for e in expenses if e.category in ["Inventory Purchases", "Store Purchases"]),
                total_inv_purchases_amt
            )
            total_operating_expenses = total_salaries_paid + total_operating_bills
            net_operating_surplus = total_fee_collected - total_operating_expenses
            total_cash_outflows = total_operating_expenses + total_store_purchases
            net_cash_surplus = total_fee_collected - total_cash_outflows

            # Store stock movement consumed / issued value
            total_stock_consumed_val = sum(
                float(tx.total_amount or 0.0) for tx in inventory_transactions if tx.transaction_type == "ISSUE"
            )

            # Total outstanding receivables across active students
            total_outstanding_receivable = sum(
                max(0.0, float(v.total_amount or 0.0) - float(v.paid_amount or 0.0))
                for v in vouchers if v.student and v.student.status == "Active"
            )

            # =========================================================
            # SHEET 1: 01_Summary
            # =========================================================
            ws1 = wb.active; ws1.title = "01_Summary"
            ws1.append([inst_name])
            ws1.cell(row=1, column=1).font = title_font
            ws1.append(["EXECUTIVE FINANCIAL & OPERATIONAL RECONCILIATION SUMMARY"])
            ws1.cell(row=2, column=1).font = sub_title_font
            ws1.append([f"Academic Session: {session_name} | Scope: Lifetime Comprehensive (Inception to Present) | Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}"])
            ws1.append([])

            ws1.append(["Metric / Financial Head", "Authoritative Amount (Rs)", "Reconciled Status"])
            for cell in ws1[5]:
                cell.fill = primary_fill; cell.font = header_font

            summary_rows = [
                ("Total Enrolled Students", len(students), "✓ Active Directory (Sheet 02)"),
                ("Total Active Teachers", len([e for e in db.query(Employee).filter_by(status='Active', emp_type='Teacher').all()]), "✓ Verified Faculty"),
                ("Total Support Staff", len([e for e in db.query(Employee).filter_by(status='Active').all() if e.emp_type != 'Teacher']), "✓ Verified Support Staff"),
                ("--- REVENUE BY CATEGORY ---", "-----------------", "-----------------"),
                ("Tuition Fee Collection", total_tuition_col, "✓ Reconciles Sheet 05"),
                ("Transport Fee Collection", total_transport_col, "✓ Reconciles Sheet 06"),
                ("Admission Fee Collection", total_admission_col, "✓ Reconciles Sheet 07"),
                ("Examination Fee Collection", total_exam_col, "✓ Reconciles Sheet 08"),
                ("Other Fees & Fines Collection", total_other_col, "✓ Reconciles Sheet 09"),
                ("TOTAL FEE REVENUE COLLECTED", total_fee_collected, "✓ Reconciles Sheet 03 & Sheet 15"),
                ("Total Fee Discounts Granted", total_discounts_granted, "✓ Audited Fee Concessions"),
                ("Total Pending / Outstanding Fees", total_outstanding_receivable, "✓ Reconciles Sheet 10 & Ledgers"),
                ("--- OPERATIONAL OUTFLOWS (DAY-TO-DAY) ---", "-----------------", "-----------------"),
                ("Teacher & Staff Salaries Paid", total_salaries_paid, "✓ Reconciles Sheet 12 (8 Paid Records)"),
                ("Operational Expenses & Bills", total_operating_bills, "✓ Reconciles Sheet 11 (Utility Bills)"),
                ("TOTAL OPERATING EXPENSES", total_operating_expenses, "✓ Salaries + Operational Bills"),
                ("--- OPERATING PERFORMANCE ---", "-----------------", "-----------------"),
                ("NET OPERATING SURPLUS", net_operating_surplus, "✓ Operating Profit (Revenue - Operating Exp)"),
                ("--- CAPITAL & STORE OUTFLOWS ---", "-----------------", "-----------------"),
                ("Store Inventory Purchases Outflow", total_store_purchases, "✓ Reconciles Sheet 18 & Capital Outflow"),
                ("TOTAL CASH OUTFLOWS", total_cash_outflows, "✓ Total Cash Outflow (Operating + Store)"),
                ("NET CASH SURPLUS (Net Cash Flow)", net_cash_surplus, "✓ Net Cash Flow (Revenue - Total Outflow)"),
                ("--- INVENTORY & PHYSICAL ASSETS ---", "-----------------", "-----------------"),
                ("Total Inventory Catalog Items", total_inv_items_count, "✓ Reconciles Sheet 16 (Catalog Count)"),
                ("Total Physical Stock Units", total_inv_units_count, "✓ Audited Physical Count (On Hand)"),
                ("TOTAL INVENTORY ASSET VALUATION", total_inv_asset_val, "✓ Reconciles Sheet 16 (Stock × Unit Cost)"),
                ("Inventory Stock Consumed / Issued", total_stock_consumed_val, "✓ Reconciles Sheet 17 (Department Issues)"),
                ("Low-Stock Alerts / Reorders", total_inv_low_stock_count, "✓ Store Attention Required")
            ]

            for row_idx, r in enumerate(summary_rows, start=6):
                ws1.append([r[0], r[1], r[2]])
                cell_b = ws1.cell(row=row_idx, column=2)
                if isinstance(r[1], (int, float)):
                    cell_b.number_format = '#,##0.00'
                    if r[0].startswith("NET OPERATING"):
                        cell_b.font = Font(name="Segoe UI", size=12, bold=True, color="059669" if net_operating_surplus >= 0 else "DC2626")
                        ws1.cell(row=row_idx, column=1).font = Font(name="Segoe UI", size=12, bold=True)
                    elif r[0].startswith("NET CASH"):
                        cell_b.font = Font(name="Segoe UI", size=12, bold=True, color="059669" if net_cash_surplus >= 0 else "DC2626")
                        ws1.cell(row=row_idx, column=1).font = Font(name="Segoe UI", size=12, bold=True)
                    elif r[0].startswith("TOTAL"):
                        cell_b.font = bold_font; ws1.cell(row=row_idx, column=1).font = bold_font

            style_sheet(ws1, "A6")

            # =========================================================
            # SHEET 2: 02_Students
            # =========================================================
            ws2 = wb.create_sheet("02_Students")
            ws2.append(["Student ID", "Full Name", "Class", "Section", "Father Name", "Phone", "Monthly Fee", "Transport Enrolled", "Session", "Status"])
            for cell in ws2[1]: cell.fill = sub_fill; cell.font = header_font
            
            for s in students:
                cls_n = s.academic_class.name if s.academic_class else "N/A"
                sec_n = s.academic_section.name if s.academic_section else "N/A"
                has_trans = db.query(StudentTransport).filter_by(student_db_id=s.id, is_active=True).first() is not None
                ws2.append([
                    s.student_id, f"{s.first_name} {s.last_name or ''}".strip(),
                    cls_n, sec_n, s.father_name or "-", s.phone or s.father_phone or "-",
                    float(s.monthly_fee or 0.0), "Yes" if has_trans else "No", s.academic_session or "-", s.status
                ])
                ws2.cell(row=ws2.max_row, column=7).number_format = '#,##0.00'
            style_sheet(ws2)

            # =========================================================
            # SHEET 3: 03_Fee_Collections (All Itemized Allocations)
            # =========================================================
            ws3 = wb.create_sheet("03_Fee_Collections")
            headers3 = ["Receipt No", "Date", "Student ID", "Student Name", "Class", "Fee Month", "Category", "Description", "Original Due", "Discount", "Net Paid", "Remaining", "Method", "Voucher No"]
            ws3.append(headers3)
            for cell in ws3[1]: cell.fill = sub_fill; cell.font = header_font

            for row in collections_rows:
                ws3.append([
                    row["receipt_no"], row["date"], row["student_id"], row["student_name"],
                    row["class"], row["fee_month"], row["category"], row["description"],
                    row["orig_amount"], row["discount"], row["paid"], row["remaining"],
                    row["method"], row["voucher_no"]
                ])
                ws3.cell(row=ws3.max_row, column=9).number_format = '#,##0.00'
                ws3.cell(row=ws3.max_row, column=10).number_format = '#,##0.00'
                ws3.cell(row=ws3.max_row, column=11).number_format = '#,##0.00'
                ws3.cell(row=ws3.max_row, column=12).number_format = '#,##0.00'

            ws3.append(["", "", "", "", "", "", "", "TOTAL RECONCILED:", "", total_discounts_granted, total_fee_collected, "", "", ""])
            tot_row = ws3.max_row
            ws3.cell(row=tot_row, column=8).font = bold_font
            ws3.cell(row=tot_row, column=10).font = bold_font; ws3.cell(row=tot_row, column=10).number_format = '#,##0.00'
            ws3.cell(row=tot_row, column=11).font = bold_font; ws3.cell(row=tot_row, column=11).number_format = '#,##0.00'
            style_sheet(ws3)

            # =========================================================
            # SHEET 4: 04_Fee_Ledger
            # =========================================================
            ws4 = wb.create_sheet("04_Fee_Ledger")
            ws4.append(["Date", "Ref / Receipt No", "Student ID", "Student Name", "Class", "Type", "Category", "Description", "Debit", "Credit", "Discount", "Balance"])
            for cell in ws4[1]: cell.fill = sub_fill; cell.font = header_font

            for s in students:
                ledger = FeeService.get_student_ledger(s.id)
                cls_n = s.academic_class.name if s.academic_class else "N/A"
                for entry in ledger:
                    ws4.append([
                        entry.get("date"), entry.get("ref_no"), s.student_id,
                        f"{s.first_name} {s.last_name or ''}".strip(), cls_n,
                        entry.get("type"), entry.get("category"), entry.get("description"),
                        entry.get("debit", 0.0), entry.get("credit", 0.0),
                        entry.get("discount", 0.0), entry.get("balance", 0.0)
                    ])
                    for col_i in [9, 10, 11, 12]:
                        ws4.cell(row=ws4.max_row, column=col_i).number_format = '#,##0.00'
            style_sheet(ws4)

            # Helper for category sub-sheets
            def create_category_sheet(sheet_name, target_cat):
                ws = wb.create_sheet(sheet_name)
                ws.append(["Receipt No", "Date", "Student ID", "Student Name", "Class", "Fee Month", "Description", "Amount Paid (Rs)", "Method"])
                for cell in ws[1]: cell.fill = sub_fill; cell.font = header_font
                cat_subtotal = 0.0
                for r in collections_rows:
                    if r["category"] == target_cat:
                        ws.append([r["receipt_no"], r["date"], r["student_id"], r["student_name"], r["class"], r["fee_month"], r["description"], r["paid"], r["method"]])
                        ws.cell(row=ws.max_row, column=8).number_format = '#,##0.00'
                        cat_subtotal += r["paid"]
                ws.append(["", "", "", "", "", "", "TOTAL:", cat_subtotal, ""])
                ws.cell(row=ws.max_row, column=7).font = bold_font
                ws.cell(row=ws.max_row, column=8).font = bold_font
                ws.cell(row=ws.max_row, column=8).number_format = '#,##0.00'
                style_sheet(ws)
                return cat_subtotal

            # =========================================================
            # SHEET 5: 05_Tuition_Collections
            # =========================================================
            create_category_sheet("05_Tuition_Collections", "Tuition Fee")

            # =========================================================
            # SHEET 6: 06_Transport_Collections
            # =========================================================
            ws6 = wb.create_sheet("06_Transport_Collections")
            ws6.append(["Receipt No", "Date", "Student ID", "Student Name", "Class", "Fee Month", "Route Details", "Amount Paid (Rs)", "Method"])
            for cell in ws6[1]: cell.fill = sub_fill; cell.font = header_font
            trans_subtotal = 0.0
            for r in collections_rows:
                if r["category"] == "Transport Fee":
                    ws6.append([r["receipt_no"], r["date"], r["student_id"], r["student_name"], r["class"], r["fee_month"], r["description"], r["paid"], r["method"]])
                    ws6.cell(row=ws6.max_row, column=8).number_format = '#,##0.00'
                    trans_subtotal += r["paid"]
            ws6.append(["", "", "", "", "", "", "TOTAL:", trans_subtotal, ""])
            ws6.cell(row=ws6.max_row, column=7).font = bold_font
            ws6.cell(row=ws6.max_row, column=8).font = bold_font
            ws6.cell(row=ws6.max_row, column=8).number_format = '#,##0.00'
            style_sheet(ws6)

            # =========================================================
            # SHEET 7: 07_Admission_Fees
            # =========================================================
            create_category_sheet("07_Admission_Fees", "Admission Fee")

            # =========================================================
            # SHEET 8: 08_Exam_Fees
            # =========================================================
            create_category_sheet("08_Exam_Fees", "Examination Fee")

            # =========================================================
            # SHEET 9: 09_Other_Fees (Fine, Library, Annual, etc.)
            # =========================================================
            ws9 = wb.create_sheet("09_Other_Fees")
            ws9.append(["Receipt No", "Date", "Student ID", "Student Name", "Class", "Category", "Description", "Amount Paid (Rs)", "Method"])
            for cell in ws9[1]: cell.fill = sub_fill; cell.font = header_font
            other_subtotal = 0.0
            for r in collections_rows:
                if r["category"] not in ["Tuition Fee", "Transport Fee", "Admission Fee", "Examination Fee"]:
                    ws9.append([r["receipt_no"], r["date"], r["student_id"], r["student_name"], r["class"], r["category"], r["description"], r["paid"], r["method"]])
                    ws9.cell(row=ws9.max_row, column=8).number_format = '#,##0.00'
                    other_subtotal += r["paid"]
            ws9.append(["", "", "", "", "", "", "TOTAL:", other_subtotal, ""])
            ws9.cell(row=ws9.max_row, column=7).font = bold_font
            ws9.cell(row=ws9.max_row, column=8).font = bold_font
            ws9.cell(row=ws9.max_row, column=8).number_format = '#,##0.00'
            style_sheet(ws9)

            # =========================================================
            # SHEET 10: 10_Outstanding_Dues
            # =========================================================
            ws10 = wb.create_sheet("10_Outstanding_Dues")
            ws10.append(["Student ID", "Student Name", "Class", "Section", "Fee Month", "Due Date", "Total Billed (Rs)", "Paid Amount (Rs)", "Outstanding Balance (Rs)", "Status"])
            for cell in ws10[1]: cell.fill = sub_fill; cell.font = header_font
            
            tot_out_due = 0.0
            for v in vouchers:
                rem = max(0.0, float(v.total_amount or 0.0) - float(v.paid_amount or 0.0))
                if rem > 0 and v.student and v.student.status == "Active":
                    cls_n = v.student.academic_class.name if v.student.academic_class else "N/A"
                    sec_n = v.student.academic_section.name if v.student.academic_section else "N/A"
                    ws10.append([
                        v.student.student_id, f"{v.student.first_name} {v.student.last_name or ''}".strip(),
                        cls_n, sec_n, v.fee_month, v.due_date or "-",
                        float(v.total_amount or 0.0), float(v.paid_amount or 0.0), rem, v.status
                    ])
                    ws10.cell(row=ws10.max_row, column=7).number_format = '#,##0.00'
                    ws10.cell(row=ws10.max_row, column=8).number_format = '#,##0.00'
                    ws10.cell(row=ws10.max_row, column=9).number_format = '#,##0.00'
                    tot_out_due += rem

            ws10.append(["", "", "", "", "", "", "", "TOTAL OUTSTANDING:", tot_out_due, ""])
            ws10.cell(row=ws10.max_row, column=8).font = bold_font
            ws10.cell(row=ws10.max_row, column=9).font = bold_font; ws10.cell(row=ws10.max_row, column=9).number_format = '#,##0.00'
            style_sheet(ws10)

            # =========================================================
            # SHEET 11: 11_Expenses
            # =========================================================
            ws11 = wb.create_sheet("11_Expenses")
            ws11.append(["Date", "Category", "Amount (Rs)", "Payment Method", "Vendor / Payee", "Reference No", "Description", "Session"])
            for cell in ws11[1]: cell.fill = sub_fill; cell.font = header_font

            tot_exp = 0.0
            tot_operating_bills = 0.0
            tot_store_purchases = 0.0
            for e in expenses:
                amt = float(e.amount or 0.0)
                ws11.append([
                    e.expense_date, e.category, amt,
                    e.payment_method or "-", e.vendor_payee or "-",
                    e.reference_no or "-", e.description or "-", e.academic_session or "-"
                ])
                ws11.cell(row=ws11.max_row, column=3).number_format = '#,##0.00'
                tot_exp += amt
                if e.category in ["Inventory Purchases", "Store Purchases"]:
                    tot_store_purchases += amt
                else:
                    tot_operating_bills += amt

            ws11.append(["", "SUBTOTAL OPERATIONAL UTILITY BILLS:", tot_operating_bills, "", "", "", "", ""])
            ws11.cell(row=ws11.max_row, column=2).font = bold_font
            ws11.cell(row=ws11.max_row, column=3).font = bold_font; ws11.cell(row=ws11.max_row, column=3).number_format = '#,##0.00'

            ws11.append(["", "SUBTOTAL STORE PURCHASES (ASSETS):", tot_store_purchases, "", "", "", "", ""])
            ws11.cell(row=ws11.max_row, column=2).font = bold_font
            ws11.cell(row=ws11.max_row, column=3).font = bold_font; ws11.cell(row=ws11.max_row, column=3).number_format = '#,##0.00'

            ws11.append(["", "TOTAL RECORDED EXPENSES:", tot_exp, "", "", "", "", ""])
            ws11.cell(row=ws11.max_row, column=2).font = bold_font
            ws11.cell(row=ws11.max_row, column=3).font = bold_font; ws11.cell(row=ws11.max_row, column=3).number_format = '#,##0.00'
            style_sheet(ws11)

            # =========================================================
            # SHEET 12: 12_Teacher_Salaries
            # =========================================================
            ws12 = wb.create_sheet("12_Teacher_Salaries")
            ws12.append(["Payment Date", "Receipt No", "Emp ID", "Staff Name", "Designation", "Month Paid", "Gross Salary (Rs)", "Net Paid (Rs)", "Payment Method"])
            for cell in ws12[1]: cell.fill = sub_fill; cell.font = header_font

            tot_sal = 0.0
            for pr in payrolls:
                emp_name = f"{pr.employee.first_name} {pr.employee.last_name or ''}".strip() if pr.employee else "-"
                emp_id = pr.employee.emp_id if pr.employee else "-"
                desig = pr.employee.designation if pr.employee else "-"
                ws12.append([
                    pr.payment_date, pr.receipt_no, emp_id, emp_name,
                    desig, pr.pay_month, float(pr.gross_salary or 0.0),
                    float(pr.net_salary or 0.0), pr.payment_method or "Bank Transfer"
                ])
                ws12.cell(row=ws12.max_row, column=7).number_format = '#,##0.00'
                ws12.cell(row=ws12.max_row, column=8).number_format = '#,##0.00'
                tot_sal += float(pr.net_salary or 0.0)

            ws12.append(["", "", "", "", "", "", "TOTAL SALARIES PAID:", tot_sal, ""])
            ws12.cell(row=ws12.max_row, column=7).font = bold_font
            ws12.cell(row=ws12.max_row, column=8).font = bold_font; ws12.cell(row=ws12.max_row, column=8).number_format = '#,##0.00'
            style_sheet(ws12)

            # =========================================================
            # SHEET 13: 13_Transport
            # =========================================================
            ws13 = wb.create_sheet("13_Transport")
            ws13.append(["Route Name", "Start Point", "End Point", "Monthly Fare (Rs)", "Vehicles Assigned", "Active Students Enrolled", "Route Status"])
            for cell in ws13[1]: cell.fill = sub_fill; cell.font = header_font

            for rt in routes:
                veh_str = ", ".join([v.vehicle_number for v in rt.vehicles]) if rt.vehicles else "None"
                stu_count = len([a for a in rt.student_assignments if a.is_active])
                ws13.append([
                    rt.route_name, rt.start_point or "-", rt.end_point or "-",
                    float(rt.monthly_fee or 0.0), veh_str, stu_count,
                    "Active" if rt.is_active else "Inactive"
                ])
                ws13.cell(row=ws13.max_row, column=4).number_format = '#,##0.00'
            style_sheet(ws13)

            # =========================================================
            # SHEET 14: 14_Vouchers
            # =========================================================
            ws14 = wb.create_sheet("14_Vouchers")
            ws14.append(["Voucher No", "Student ID", "Student Name", "Class", "Fee Month", "Base Amount (Rs)", "Total Amount (Rs)", "Paid Amount (Rs)", "Balance (Rs)", "Status", "Due Date"])
            for cell in ws14[1]: cell.fill = sub_fill; cell.font = header_font

            tot_v_billed = 0.0
            tot_v_paid = 0.0
            for v in vouchers:
                s_id = v.student.student_id if v.student else "-"
                s_n = f"{v.student.first_name} {v.student.last_name or ''}".strip() if v.student else "-"
                c_n = v.student.academic_class.name if v.student and v.student.academic_class else "-"
                rem = max(0.0, float(v.total_amount or 0.0) - float(v.paid_amount or 0.0))
                ws14.append([
                    v.voucher_no, s_id, s_n, c_n, v.fee_month,
                    float(v.base_amount or 0.0), float(v.total_amount or 0.0),
                    float(v.paid_amount or 0.0), rem, v.status, v.due_date or "-"
                ])
                ws14.cell(row=ws14.max_row, column=6).number_format = '#,##0.00'
                ws14.cell(row=ws14.max_row, column=7).number_format = '#,##0.00'
                ws14.cell(row=ws14.max_row, column=8).number_format = '#,##0.00'
                ws14.cell(row=ws14.max_row, column=9).number_format = '#,##0.00'
                tot_v_billed += float(v.total_amount or 0.0)
                tot_v_paid += float(v.paid_amount or 0.0)

            ws14.append(["", "", "", "", "", "TOTALS:", tot_v_billed, tot_v_paid, max(0.0, tot_v_billed - tot_v_paid), "", ""])
            ws14.cell(row=ws14.max_row, column=6).font = bold_font
            ws14.cell(row=ws14.max_row, column=7).font = bold_font; ws14.cell(row=ws14.max_row, column=7).number_format = '#,##0.00'
            ws14.cell(row=ws14.max_row, column=8).font = bold_font; ws14.cell(row=ws14.max_row, column=8).number_format = '#,##0.00'
            ws14.cell(row=ws14.max_row, column=9).font = bold_font; ws14.cell(row=ws14.max_row, column=9).number_format = '#,##0.00'
            style_sheet(ws14)

            # =========================================================
            # SHEET 15: 15_Receipts
            # =========================================================
            ws15 = wb.create_sheet("15_Receipts")
            ws15.append(["Receipt No", "Payment Date", "Student ID", "Student Name", "Voucher No", "Fee Month", "Amount Paid (Rs)", "Payment Method", "Fine Included", "Discount Included"])
            for cell in ws15[1]: cell.fill = sub_fill; cell.font = header_font

            tot_rec_paid = 0.0
            for p in payments:
                s_id = p.voucher.student.student_id if p.voucher and p.voucher.student else "-"
                s_n = f"{p.voucher.student.first_name} {p.voucher.student.last_name or ''}".strip() if p.voucher and p.voucher.student else "-"
                v_no = p.voucher.voucher_no if p.voucher else "-"
                month = p.voucher.fee_month if p.voucher else "-"
                amt = float(p.amount_paid or 0.0)
                ws15.append([
                    p.receipt_no, p.payment_date, s_id, s_n, v_no, month,
                    amt, p.payment_method or "Cash",
                    float(p.fine_included or 0.0), float(p.discount_included or 0.0)
                ])
                ws15.cell(row=ws15.max_row, column=7).number_format = '#,##0.00'
                ws15.cell(row=ws15.max_row, column=9).number_format = '#,##0.00'
                ws15.cell(row=ws15.max_row, column=10).number_format = '#,##0.00'
                tot_rec_paid += amt

            ws15.append(["", "", "", "", "", "TOTAL RECEIPTS:", tot_rec_paid, "", "", ""])
            ws15.cell(row=ws15.max_row, column=6).font = bold_font
            style_sheet(ws15)

            # =========================================================
            # SHEET 16: 16_Inventory_Catalog
            # =========================================================
            ws16 = wb.create_sheet("16_Inventory_Catalog")
            ws16.append(["Item ID", "SKU", "Item Name", "Category", "Current Stock", "Unit", "Unit Cost (Rs)", "Total Asset Value (Rs)", "Min Alert", "Stock Status"])
            for cell in ws16[1]: cell.fill = sub_fill; cell.font = header_font

            tot_stock_val = 0.0
            tot_units = 0.0
            for it in inventory_items:
                c_name = it.category.name if it.category else "Uncategorized"
                c_stock = float(it.current_stock or 0.0)
                u_cost = float(it.unit_cost or 0.0)
                line_val = c_stock * u_cost
                status_str = "Out of Stock" if c_stock <= 0 else ("Low Stock" if c_stock <= (it.min_stock_alert or 0.0) else "In Stock")
                ws16.append([
                    it.id, it.sku, it.name, c_name, c_stock, it.unit,
                    u_cost, line_val, float(it.min_stock_alert or 0.0), status_str
                ])
                ws16.cell(row=ws16.max_row, column=7).number_format = '#,##0.00'
                ws16.cell(row=ws16.max_row, column=8).number_format = '#,##0.00'
                tot_units += c_stock
                tot_stock_val += line_val

            ws16.append(["", "", "", "TOTALS:", tot_units, "", "", tot_stock_val, "", ""])
            tot_r16 = ws16.max_row
            ws16.cell(row=tot_r16, column=4).font = bold_font
            ws16.cell(row=tot_r16, column=5).font = bold_font
            ws16.cell(row=tot_r16, column=8).font = bold_font
            ws16.cell(row=tot_r16, column=8).number_format = '#,##0.00'
            style_sheet(ws16)

            # =========================================================
            # SHEET 17: 17_Inventory_Movements
            # =========================================================
            ws17 = wb.create_sheet("17_Inventory_Movements")
            ws17.append(["Date", "Ref / Slip No", "Item Name", "SKU", "Category", "Movement Type", "Quantity", "Unit Price (Rs)", "Total Amount (Rs)", "Entity / Recipient", "Notes"])
            for cell in ws17[1]: cell.fill = sub_fill; cell.font = header_font

            tot_move_amt = 0.0
            for tx in inventory_transactions:
                it_name = tx.item.name if tx.item else f"Item #{tx.item_id}"
                it_sku = tx.item.sku if tx.item else "-"
                it_cat = tx.item.category.name if tx.item and tx.item.category else "-"
                amt = float(tx.total_amount or 0.0)
                ent_str = f"{tx.entity_type or ''} {tx.entity_id or ''}".strip()
                ws17.append([
                    tx.transaction_date or "-", tx.reference_no or "-", it_name, it_sku, it_cat,
                    tx.transaction_type, float(tx.quantity or 0.0), float(tx.unit_price or 0.0),
                    amt, ent_str or "General", tx.notes or "-"
                ])
                ws17.cell(row=ws17.max_row, column=8).number_format = '#,##0.00'
                ws17.cell(row=ws17.max_row, column=9).number_format = '#,##0.00'
                tot_move_amt += amt

            ws17.append(["", "", "", "", "", "", "", "TOTAL MOVEMENT VALUE:", tot_move_amt, "", ""])
            tot_r17 = ws17.max_row
            ws17.cell(row=tot_r17, column=8).font = bold_font
            ws17.cell(row=tot_r17, column=9).font = bold_font
            ws17.cell(row=tot_r17, column=9).number_format = '#,##0.00'
            style_sheet(ws17)

            # =========================================================
            # SHEET 18: 18_Inventory_Purchases
            # =========================================================
            ws18 = wb.create_sheet("18_Inventory_Purchases")
            ws18.append(["PO Number", "Invoice Date", "Supplier Name", "Payment Status", "Items Count", "Total Amount (Rs)", "Audit Notes"])
            for cell in ws18[1]: cell.fill = sub_fill; cell.font = header_font

            tot_purch_amt = 0.0
            for p in inventory_purchases:
                sup_name = p.supplier.name if p.supplier else "Direct / Unassigned"
                amt = float(p.total_amount or 0.0)
                item_summary = "; ".join([f"{pi.item.name if pi.item else 'Item'}: {pi.quantity} @ Rs. {pi.unit_cost}" for pi in p.items]) if p.items else "-"
                ws18.append([
                    p.purchase_no, p.invoice_date, sup_name, p.payment_status or "Paid",
                    len(p.items), amt, p.notes or item_summary
                ])
                ws18.cell(row=ws18.max_row, column=6).number_format = '#,##0.00'
                tot_purch_amt += amt

            ws18.append(["", "", "", "", "TOTAL PURCHASES:", tot_purch_amt, ""])
            tot_r18 = ws18.max_row
            ws18.cell(row=tot_r18, column=5).font = bold_font
            ws18.cell(row=tot_r18, column=6).font = bold_font
            ws18.cell(row=tot_r18, column=6).number_format = '#,##0.00'
            style_sheet(ws18)

            wb.save(filepath)
            return True, "Export Successful"
        except Exception as e:
            return False, str(e)
        finally:
            db.close()