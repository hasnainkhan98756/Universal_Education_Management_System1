import os
from database.connection import get_session
from database.models.hr import Employee, EmployeeQualification, TeacherAssignment, StaffAttendance, PayrollRecord
from database.models.academic import AcademicClass, AcademicSection, AcademicSubject
from core.document_service import DocumentService
from core.state_manager import app_state
from sqlalchemy.orm import joinedload
from datetime import datetime, date

class HRService:
    # ==========================================
    # 1. DASHBOARD & OVERVIEW ANALYTICS
    # ==========================================
    @staticmethod
    def get_hr_dashboard_stats(date_str=None, month_str=None):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        if not month_str:
            month_str = datetime.now().strftime("%B %Y")

        db = get_session()
        try:
            all_staff = db.query(Employee).all()
            total_staff = len(all_staff)
            active_staff = sum(1 for e in all_staff if e.status == "Active")
            teachers_count = sum(1 for e in all_staff if e.emp_type == "Teacher" and e.status == "Active")
            support_count = active_staff - teachers_count
            retired_count = sum(1 for e in all_staff if e.status == "Retired")
            suspended_count = sum(1 for e in all_staff if e.status == "Suspended")
            leave_count = sum(1 for e in all_staff if e.status in ["On Leave", "Leave"])
            resigned_count = sum(1 for e in all_staff if e.status in ["Resigned", "Terminated"])

            att_records = db.query(StaffAttendance).join(
                Employee, StaffAttendance.employee_id == Employee.id
            ).filter(
                StaffAttendance.date == date_str,
                Employee.status.in_(["Active", "On Leave", "Leave"])
            ).all()
            working_staff = sum(1 for e in all_staff if e.status in ["Active", "On Leave", "Leave"])
            total_marked = len(att_records)

            if total_marked > 0:
                att_present = sum(1 for a in att_records if a.status == "Present")
                att_absent = sum(1 for a in att_records if a.status == "Absent")
                att_leave = sum(1 for a in att_records if a.status == "Leave")
                att_late = sum(1 for a in att_records if a.status == "Late")
                att_half = sum(1 for a in att_records if a.status == "Half Day")
                base_count = max(working_staff, total_marked) if max(working_staff, total_marked) > 0 else (active_staff if active_staff > 0 else 1)
                att_rate = min(100.0, ((att_present + (att_half * 0.5) + att_late) / base_count * 100))
            else:
                # If attendance has not been explicitly taken for this date, check approved leaves
                from database.models.leave import LeaveApplication
                try:
                    target_d = datetime.strptime(date_str, "%Y-%m-%d").date()
                    approved_leaves = db.query(LeaveApplication).filter(
                        LeaveApplication.status == "Approved",
                        LeaveApplication.from_date <= target_d,
                        LeaveApplication.to_date >= target_d
                    ).all()
                    leave_emp_ids = {a.employee_id for a in approved_leaves}
                    att_leave = len(leave_emp_ids)
                    att_present = max(0, active_staff - att_leave)
                    att_absent = 0
                    att_late = 0
                    att_half = 0
                    att_rate = round((att_present / active_staff * 100), 1) if active_staff > 0 else 0.0
                except Exception:
                    att_present = active_staff
                    att_absent = 0
                    att_leave = 0
                    att_late = 0
                    att_half = 0
                    att_rate = 100.0 if active_staff > 0 else 0.0

            payroll_records = db.query(PayrollRecord).filter_by(pay_month=month_str).all()
            total_expense_budget = sum((p.gross_salary or 0.0) for p in payroll_records)
            total_paid = sum((p.net_salary or 0.0) for p in payroll_records if p.status == "Paid")
            total_pending = sum((p.net_salary or 0.0) for p in payroll_records if p.status != "Paid")
            paid_count = sum(1 for p in payroll_records if p.status == "Paid")
            pending_count = sum(1 for p in payroll_records if p.status != "Paid")

            return {
                "total_staff": total_staff, "active_staff": active_staff, "teachers_count": teachers_count,
                "support_count": support_count, "retired_count": retired_count,
                "suspended_count": suspended_count, "leave_count": leave_count,
                "resigned_count": resigned_count,
                "date_str": date_str, "att_present": att_present,
                "att_absent": att_absent, "att_leave": att_leave, "att_late": att_late,
                "att_half": att_half, "att_rate": round(att_rate, 1), "month_str": month_str,
                "total_expense_budget": total_expense_budget, "total_paid": total_paid,
                "total_pending": total_pending, "paid_count": paid_count, "pending_count": pending_count
            }
        finally: db.close()

    @staticmethod
    def get_teacher_count():
        db = get_session()
        try:
            return db.query(Employee).filter(
                (Employee.status == "Active") &
                ((Employee.emp_type == "Teacher") | (Employee.designation.ilike("%teacher%")))
            ).count()
        except Exception:
            return 0
        finally:
            db.close()

    @staticmethod
    def get_active_staff_count():
        db = get_session()
        try:
            return db.query(Employee).filter_by(status="Active").count()
        except Exception:
            return 0
        finally:
            db.close()

    # ==========================================
    # 2. EMPLOYEES CRUD
    # ==========================================
    @staticmethod
    def get_employees(status_filter=None, type_filter=None, search_query=None):
        db = get_session()
        try:
            query = db.query(Employee)
            if status_filter and status_filter not in ["All", "All Personnel", "All Staff"]:
                if status_filter in ["Resigned & Terminated", "Resigned/Terminated"]:
                    query = query.filter(Employee.status.in_(["Resigned", "Terminated"]))
                elif status_filter in ["Active Faculty & Staff", "Active Staff", "Active"]:
                    query = query.filter(Employee.status == "Active")
                elif status_filter in ["Retired Veterans", "Retired"]:
                    query = query.filter(Employee.status == "Retired")
                elif status_filter in ["Suspended Under Inquiry", "Suspended"]:
                    query = query.filter(Employee.status == "Suspended")
                elif status_filter in ["On Leave", "Leave"]:
                    query = query.filter(Employee.status.in_(["On Leave", "Leave"]))
                else:
                    query = query.filter(Employee.status == status_filter)
            if type_filter and type_filter != "All": query = query.filter(Employee.emp_type == type_filter)
            if search_query:
                term = f"%{search_query.strip()}%"
                query = query.filter(
                    (Employee.first_name.ilike(term)) | (Employee.last_name.ilike(term)) |
                    (Employee.emp_id.ilike(term)) | (Employee.cnic.ilike(term)) |
                    (Employee.phone.ilike(term)) | (Employee.designation.ilike(term)) |
                    (Employee.department.ilike(term))
                )
            return query.order_by(Employee.first_name).all()
        finally: db.close()

    get_all_employees = get_employees

    @staticmethod
    def get_employee_by_id(emp_db_id):
        db = get_session()
        try:
            return db.query(Employee).options(
                joinedload(Employee.qualifications),
                joinedload(Employee.assignments).joinedload(TeacherAssignment.academic_class),
                joinedload(Employee.assignments).joinedload(TeacherAssignment.academic_section),
                joinedload(Employee.assignments).joinedload(TeacherAssignment.academic_subject),
                joinedload(Employee.payroll)
            ).filter(Employee.id == emp_db_id).first()
        finally: db.close()

    @staticmethod
    def save_employee(emp_db_id, data):
        db = get_session()
        try:
            if emp_db_id:
                emp = db.query(Employee).filter_by(id=emp_db_id).first()
                if not emp: return False, "Employee not found."
                for key, val in data.items():
                    if hasattr(emp, key) and key not in ['id', 'emp_id']: setattr(emp, key, val)
            else:
                sys_id = DocumentService.generate_number("Employee ID")
                emp = Employee(emp_id=sys_id)
                for key, val in data.items():
                    if hasattr(emp, key) and key != 'id': setattr(emp, key, val)
                db.add(emp)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as ex:
                print(f"Error broadcasting employee change: {ex}")
            return True, "Employee record saved securely."
        except Exception as e: db.rollback(); return False, f"Database Error: {e}"
        finally: db.close()

    @staticmethod
    def add_employee(data):
        return HRService.save_employee(None, data)

    @staticmethod
    def update_employee(emp_db_id, data):
        return HRService.save_employee(emp_db_id, data)

    @staticmethod
    def toggle_status(emp_db_id, new_status):
        return HRService.update_employee_status(emp_db_id, new_status)

    @staticmethod
    def update_employee_status(emp_db_id, new_status):
        db = get_session()
        try:
            emp = db.query(Employee).filter_by(id=emp_db_id).first()
            if not emp: return False, "Employee not found."
            emp.status = new_status

            # If employee is no longer active or on leave, purge today's attendance so they vanish immediately
            if new_status in ["Retired", "Resigned", "Terminated", "Suspended", "Inactive"]:
                try:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    db.query(StaffAttendance).filter(
                        StaffAttendance.employee_id == emp.id,
                        StaffAttendance.date == today_str
                    ).delete(synchronize_session=False)
                except Exception as purge_err:
                    print(f"Warning: Could not purge same-day staff attendance for emp {emp.id}: {purge_err}")

            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as ex:
                print(f"Error broadcasting employee status change: {ex}")
            return True, f"Employee status set to {new_status}."
        except Exception as e: db.rollback(); return False, str(e)
        finally: db.close()

    # ==========================================
    # 3. QUALIFICATIONS
    # ==========================================
    @staticmethod
    def add_qualification(emp_db_id, degree, major, inst, year, grade, notes=""):
        db = get_session()
        try:
            qual = EmployeeQualification(
                employee_id=emp_db_id, degree=degree, major_subject=major,
                institution=inst, passing_year=year, grade_marks=grade, notes=notes
            )
            db.add(qual); db.commit(); return True, "Qualification added."
        except Exception as e: db.rollback(); return False, str(e)
        finally: db.close()

    @staticmethod
    def delete_qualification(qual_id):
        db = get_session()
        try:
            qual = db.query(EmployeeQualification).filter_by(id=qual_id).first()
            if qual: db.delete(qual); db.commit(); return True, "Qualification removed."
            return False, "Record not found."
        except Exception as e: db.rollback(); return False, str(e)
        finally: db.close()

    # ==========================================
    # 4. TEACHER ASSIGNMENTS
    # ==========================================
    @staticmethod
    def get_assignments(filter_teacher_id=None):
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "Default")
            query = db.query(TeacherAssignment).options(
                joinedload(TeacherAssignment.employee), joinedload(TeacherAssignment.academic_class),
                joinedload(TeacherAssignment.academic_section), joinedload(TeacherAssignment.academic_subject)
            ).filter(TeacherAssignment.academic_session == active_session)
            if filter_teacher_id: query = query.filter(TeacherAssignment.employee_id == filter_teacher_id)
            return query.all()
        finally: db.close()

    @staticmethod
    def assign_teacher(employee_id, class_id, section_id, subject_id, periods=5):
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "Default")
            existing = db.query(TeacherAssignment).filter_by(
                employee_id=employee_id, class_id=class_id, section_id=section_id, 
                subject_id=subject_id, academic_session=active_session
            ).first()
            if existing: return False, "This exact teaching assignment already exists for this session."

            assign = TeacherAssignment(
                employee_id=employee_id, class_id=class_id, section_id=section_id, 
                subject_id=subject_id, academic_session=active_session, periods_per_week=periods
            )
            db.add(assign); db.commit(); return True, "Workload assigned successfully."
        except Exception as e: db.rollback(); return False, f"Assignment Error: {e}"
        finally: db.close()

    @staticmethod
    def delete_assignment(assign_id):
        db = get_session()
        try:
            rec = db.query(TeacherAssignment).filter_by(id=assign_id).first()
            if rec: db.delete(rec); db.commit(); return True, "Workload assignment removed."
            return False, "Not found."
        except Exception as e: db.rollback(); return False, str(e)
        finally: db.close()

    # ==========================================
    # 5. STAFF ATTENDANCE
    # ==========================================
    @staticmethod
    def get_staff_attendance_sheet(date_str):
        db = get_session()
        try:
            # Strictly active faculty & staff and sanctioned leaves only (Retired, Resigned, Terminated, Suspended never appear)
            staff = db.query(Employee).filter(
                Employee.status.in_(["Active", "On Leave", "Leave"])
            ).order_by(Employee.first_name).all()
            existing = db.query(StaffAttendance).filter_by(date=date_str).all()
            record_map = {rec.employee_id: rec for rec in existing}

            # Check approved leaves for this date
            from database.models.leave import LeaveApplication
            try:
                target_d = datetime.strptime(date_str, "%Y-%m-%d").date()
                approved_leaves = db.query(LeaveApplication).filter(
                    LeaveApplication.status == "Approved",
                    LeaveApplication.from_date <= target_d,
                    LeaveApplication.to_date >= target_d
                ).all()
                leave_map = {a.employee_id: a for a in approved_leaves}
            except Exception:
                leave_map = {}
            
            from core.calendar_service import CalendarService
            holiday_info = CalendarService.get_holiday_or_event(date_str)

            sheet = []
            for s in staff:
                rec = record_map.get(s.id)
                app_leave = leave_map.get(s.id)

                if rec:
                    st = rec.status
                    rem = rec.remarks or ""
                    is_exist = True
                elif app_leave:
                    st = "Leave"
                    rem = f"Approved Leave ({app_leave.leave_type_name})"
                    is_exist = False
                elif s.status in ["On Leave", "Leave"]:
                    st = "Leave"
                    rem = "Sanctioned Medical/Official Leave"
                    is_exist = False
                elif holiday_info:
                    st = "Holiday"
                    rem = holiday_info["title"]
                    is_exist = False
                else:
                    st = "Present"
                    rem = ""
                    is_exist = False

                sheet.append({
                    "id": s.id, "emp_id": s.emp_id, "name": f"{s.first_name} {s.last_name or ''}".strip(),
                    "designation": s.designation or "-", "department": s.department or "-",
                    "status": st, "remarks": rem, "is_existing": is_exist
                })
            return sheet
        finally: db.close()

    @staticmethod
    def mark_employee_arrived(emp_id, date_str=None):
        """Marks an employee arrived, restores status to Active, ends leave, and records Present."""
        from core.leave_service import LeaveService
        return LeaveService.return_from_leave(emp_id, return_date=date_str, update_attendance=True)

    @staticmethod
    def save_staff_attendance(date_str, data_list):
        db = get_session()
        try:
            from database.models.leave import LeaveApplication
            from datetime import timedelta
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            for d in data_list:
                emp_id = d['id']
                st = d['status']
                rem = d['remarks']

                emp = db.query(Employee).filter_by(id=emp_id).first()

                # If staff member is marked Present, Late, or Half Day, automatically remove from leave!
                if st in ["Present", "Late", "Half Day"]:
                    if emp and emp.status in ["On Leave", "Leave"]:
                        emp.status = "Active"

                    # Automatically conclude/adjust active approved LeaveApplication for this staff member
                    try:
                        active_leaves = db.query(LeaveApplication).filter(
                            LeaveApplication.employee_id == emp_id,
                            LeaveApplication.status == "Approved",
                            LeaveApplication.to_date >= target_date
                        ).all()
                        for app in active_leaves:
                            if target_date <= app.from_date:
                                app.status = "Returned Early"
                                app.total_days = 0
                                app.admin_remarks = f"Staff marked {st} on {date_str}."
                            else:
                                app.to_date = target_date - timedelta(days=1)
                                app.total_days = max(1, (app.to_date - app.from_date).days + 1)
                                prev_r = app.admin_remarks or ""
                                app.admin_remarks = f"{prev_r} [Marked {st} on {date_str}].".strip()
                    except Exception as l_err:
                        print(f"Leave adjust note: {l_err}")

                elif st == "Leave":
                    if emp and emp.status == "Active":
                        emp.status = "On Leave"

                rec = db.query(StaffAttendance).filter_by(employee_id=emp_id, date=date_str).first()
                if rec:
                    rec.status = st
                    rec.remarks = rem
                else:
                    db.add(StaffAttendance(employee_id=emp_id, date=date_str, status=st, remarks=rem))

            db.commit()
            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
                app_state.trigger_dashboard_sync()
            except Exception:
                pass
            return True, "Staff attendance saved successfully."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_monthly_staff_attendance_report(target_year, target_month=0):
        db = get_session()
        try:
            staff = db.query(Employee).filter(
                Employee.status.in_(["Active", "On Leave", "Leave"])
            ).order_by(Employee.first_name).all()
            all_records = db.query(StaffAttendance).all()

            valid_records = []
            for r in all_records:
                try:
                    r_date = datetime.strptime(str(r.date), "%Y-%m-%d").date()
                    if r_date.year == target_year:
                        if target_month == 0 or r_date.month == target_month: valid_records.append((r.employee_id, r.status))
                except Exception: pass

            report = []
            for s in staff:
                s_records = [status for emp_id, status in valid_records if emp_id == s.id]
                total = len(s_records)
                present = s_records.count("Present"); absent = s_records.count("Absent")
                leave = s_records.count("Leave"); late = s_records.count("Late"); half = s_records.count("Half Day")
                pct = ((present + (half * 0.5) + late) / total * 100) if total > 0 else 0.0

                report.append({
                    "id": s.id, "emp_id": s.emp_id, "name": f"{s.first_name} {s.last_name or ''}".strip(),
                    "designation": s.designation or "-", "department": s.department or "-", "total_days": total,
                    "present": present, "absent": absent, "leave": leave, "late": late, "half_day": half, "percentage": round(pct, 1)
                })
            return report
        finally: db.close()

    @staticmethod
    def get_employee_attendance_summary(emp_db_id):
        db = get_session()
        try:
            records = db.query(StaffAttendance).filter_by(employee_id=emp_db_id).all()
            total = len(records)
            present = sum(1 for r in records if r.status == "Present"); absent = sum(1 for r in records if r.status == "Absent")
            late = sum(1 for r in records if r.status == "Late"); leave = sum(1 for r in records if r.status == "Leave")
            half = sum(1 for r in records if r.status == "Half Day")
            pct = ((present + (half * 0.5) + late) / total * 100) if total > 0 else 0.0
            return { "total": total, "present": present, "absent": absent, "late": late, "leave": leave, "half_day": half, "percentage": round(pct, 1) }
        finally: db.close()

    # ==========================================
    # 6. PAYROLL & AUTOMATED FINANCE SYNC
    # ==========================================
    @staticmethod
    def get_payroll(month_str, status_filter="All"):
        db = get_session()
        try:
            query = db.query(PayrollRecord).options(joinedload(PayrollRecord.employee)).filter_by(pay_month=month_str)
            if status_filter and status_filter != "All": query = query.filter(PayrollRecord.status == status_filter)
            return query.all()
        finally: db.close()

    @staticmethod
    def generate_payroll(month_str):
        db = get_session()
        generated = 0
        try:
            staff = db.query(Employee).filter_by(status="Active").all()
            for s in staff:
                existing = db.query(PayrollRecord).filter_by(employee_id=s.id, pay_month=month_str).first()
                if not existing:
                    sys_id = DocumentService.generate_number("Salary Slip")
                    tot_allowances = (s.house_allowance or 0.0) + (s.medical_allowance or 0.0) + (s.transport_allowance or 0.0) + (s.other_allowance or 0.0)
                    gross = (s.basic_salary or 0.0) + tot_allowances
                    tax = s.tax_deduction or 0.0
                    net = gross - tax
                    pay = PayrollRecord(
                        receipt_no=sys_id, employee_id=s.id, pay_month=month_str, basic_salary=s.basic_salary or 0.0,
                        allowances=tot_allowances, bonus=0.0, overtime=0.0, gross_salary=gross,
                        deductions=0.0, advance=0.0, tax=tax, net_salary=max(0.0, net), status="Pending"
                    )
                    db.add(pay)
                    generated += 1
            db.commit(); return True, f"Generated {generated} payroll entries for {month_str}."
        except Exception as e: db.rollback(); return False, str(e)
        finally: db.close()

    @staticmethod
    def process_payroll_payment(payroll_id, allowances, bonus, overtime, deductions, advance, tax, method):
        db = get_session()
        try:
            rec = db.query(PayrollRecord).options(joinedload(PayrollRecord.employee)).filter_by(id=payroll_id).first()
            if not rec: return False, "Record not found.", None
            
            rec.allowances = allowances; rec.bonus = bonus; rec.overtime = overtime
            rec.gross_salary = rec.basic_salary + allowances + bonus + overtime
            rec.deductions = deductions; rec.advance = advance; rec.tax = tax
            rec.net_salary = max(0.0, rec.gross_salary - (deductions + advance + tax))
            rec.payment_method = method
            rec.payment_date = datetime.now().strftime("%Y-%m-%d")
            rec.status = "Paid"
            db.commit()
            
            # ==============================================================
            # NEW: AUTO-SYNC SALARY TO ANALYTICS (EXPENSE) MODULE!
            # ==============================================================
            try:
                from core.analytics_service import AnalyticsService
                cat_name = "Teacher Payroll" if rec.employee.emp_type == "Teacher" else "Staff Payroll"
                emp_name = f"{rec.employee.first_name} {rec.employee.last_name or ''}".strip()
                desc_text = f"Auto-generated salary for {rec.pay_month} ({rec.employee.emp_id})"
                
                AnalyticsService.save_expense(
                    exp_id=None,
                    date_str=rec.payment_date,
                    cat=cat_name,
                    amount=rec.net_salary,
                    method=method,
                    vendor=emp_name,
                    ref=rec.receipt_no,
                    desc=desc_text
                )
            except Exception as exp_err:
                print(f"Failed to auto-log expense: {exp_err}")
            # ==============================================================

            data_dict = {
                "employee.name": f"{rec.employee.first_name} {rec.employee.last_name or ''}".strip(), "employee.emp_id": rec.employee.emp_id,
                "employee.designation": rec.employee.designation or "-", "employee.department": rec.employee.department or "-",
                "payroll.receipt_no": rec.receipt_no, "payroll.month": rec.pay_month, "payroll.basic": f"{rec.basic_salary:,.2f}",
                "payroll.allowances": f"{rec.allowances:,.2f}", "payroll.bonus": f"{rec.bonus:,.2f}", "payroll.overtime": f"{rec.overtime:,.2f}",
                "payroll.gross": f"{rec.gross_salary:,.2f}", "payroll.deductions": f"{rec.deductions:,.2f}", "payroll.advance": f"{rec.advance:,.2f}",
                "payroll.tax": f"{rec.tax:,.2f}", "payroll.net_salary": f"{rec.net_salary:,.2f}", "payroll.payment_date": rec.payment_date,
                "payroll.method": rec.payment_method,
                "employee_id": rec.employee_id, "employee.id": rec.employee_id
            }
            return True, "Payment recorded successfully.", data_dict
        except Exception as e: db.rollback(); return False, str(e), None
        finally: db.close()

    # ==========================================
    # 7. EXCEL EXPORTS
    # ==========================================
    @staticmethod
    def export_employees_to_excel(filepath):
        import openpyxl; from openpyxl.styles import Font, PatternFill
        staff = HRService.get_employees(); wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Staff Directory"
        headers = ["Emp ID", "Full Name", "CNIC", "Type", "Department", "Designation", "Phone", "Joining Date", "Status", "Basic Salary"]
        ws.append(headers)
        for col in range(1, len(headers) + 1): cell = ws.cell(row=1, column=col); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill(start_color="1E3A8A", fill_type="solid")
        for s in staff: ws.append([s.emp_id, f"{s.first_name} {s.last_name or ''}".strip(), s.cnic or "-", s.emp_type, s.department or "-", s.designation or "-", s.phone or "-", s.joining_date or "-", s.status, s.basic_salary])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 16
        wb.save(filepath)

    @staticmethod
    def export_workload_to_excel(filepath):
        import openpyxl; from openpyxl.styles import Font, PatternFill
        assigns = HRService.get_assignments(); wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Teaching Workload"
        headers = ["Teacher Name", "Employee ID", "Class", "Section", "Subject", "Periods/Week", "Session"]
        ws.append(headers)
        for col in range(1, len(headers) + 1): cell = ws.cell(row=1, column=col); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill(start_color="7C3AED", fill_type="solid")
        for a in assigns: ws.append([f"{a.employee.first_name} {a.employee.last_name or ''}".strip(), a.employee.emp_id, a.academic_class.name, a.academic_section.name, a.academic_subject.name, a.periods_per_week, a.academic_session])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 16
        wb.save(filepath)

    @staticmethod
    def export_monthly_attendance_to_excel(target_year, target_month, filepath):
        import openpyxl; from openpyxl.styles import Font, PatternFill
        data = HRService.get_monthly_staff_attendance_report(target_year, target_month); wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Staff Attendance Report"
        headers = ["Emp ID", "Staff Name", "Department", "Designation", "Total Days", "Present", "Absent", "Leave", "Late", "Half Day", "Attendance %"]
        ws.append(headers)
        for col in range(1, len(headers) + 1): cell = ws.cell(row=1, column=col); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill(start_color="1D4ED8", fill_type="solid")
        for s in data: ws.append([s["emp_id"], s["name"], s["department"], s["designation"], s["total_days"], s["present"], s["absent"], s["leave"], s["late"], s["half_day"], f"{s['percentage']}%"])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 15
        wb.save(filepath)

    @staticmethod
    def export_payroll_to_excel(month_str, filepath):
        import openpyxl; from openpyxl.styles import Font, PatternFill
        recs = HRService.get_payroll(month_str); wb = openpyxl.Workbook(); ws = wb.active; ws.title = f"Payroll {month_str}"
        headers = ["Receipt No", "Emp ID", "Name", "Designation", "Basic Salary", "Allowances", "Bonus", "Overtime", "Gross Salary", "Deductions", "Advance", "Tax", "Net Salary", "Status", "Payment Date", "Method"]
        ws.append(headers)
        for col in range(1, len(headers) + 1): cell = ws.cell(row=1, column=col); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill(start_color="059669", fill_type="solid")
        for p in recs: ws.append([p.receipt_no, p.employee.emp_id, f"{p.employee.first_name} {p.employee.last_name or ''}".strip(), p.employee.designation or "-", p.basic_salary, p.allowances, p.bonus, p.overtime, p.gross_salary, p.deductions, p.advance, p.tax, p.net_salary, p.status, p.payment_date or "-", p.payment_method or "-"])
        for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = 15
        wb.save(filepath)