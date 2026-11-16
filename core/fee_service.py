import os
import json
import calendar
from datetime import datetime
from database.connection import get_session
from database.models.student import Student
from database.models.fee import FeeVoucher, FeePayment, FeeVoucherItem, FeePaymentAllocation
from database.models.transport import StudentTransport, TransportRoute
from core.document_service import DocumentService
from core.state_manager import app_state
from sqlalchemy.orm import joinedload
from sqlalchemy import func, case

STANDARD_FEE_CATEGORIES = [
    "Tuition Fee",
    "Transport Fee",
    "Admission Fee",
    "Examination Fee",
    "Library Fee",
    "Hostel Fee",
    "Fine",
    "Registration Fee",
    "Annual Charges",
    "Other Fee"
]

class FeeService:
    """Centralized Financial Engine ensuring transaction safety and real-time analytics."""

    @staticmethod
    def get_supported_categories():
        cats = list(STANDARD_FEE_CATEGORIES)
        custom_str = DocumentService.get_setting("custom_fee_categories", "")
        if custom_str:
            for c in custom_str.split(","):
                c_clean = c.strip()
                if c_clean and c_clean not in cats:
                    cats.append(c_clean)
        return cats

    @staticmethod
    def get_voucher_covered_months(voucher):
        """Returns set of normalized month strings covered by a voucher, e.g. {'October 2026'}."""
        covered = set()
        if not voucher:
            return covered
        
        # 1. From coverage_months field (JSON or comma separated)
        if voucher.coverage_months:
            raw = str(voucher.coverage_months).strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    for m in json.loads(raw):
                        covered.add(str(m).strip())
                except Exception:
                    pass
            if not covered:
                for part in raw.split(","):
                    p_clean = part.strip()
                    if p_clean:
                        covered.add(p_clean)

        # 2. From fee_month field
        if voucher.fee_month:
            fm = str(voucher.fee_month).strip()
            covered.add(fm)
            for m_name in ["January", "February", "March", "April", "May", "June", 
                           "July", "August", "September", "October", "November", "December"]:
                if m_name in fm:
                    clean_fm = fm.replace("(", " ").replace(")", " ").replace("–", " ").replace("-", " ")
                    words = clean_fm.split()
                    for idx, w in enumerate(words):
                        if w == m_name and idx + 1 < len(words) and words[idx+1].isdigit():
                            covered.add(f"{w} {words[idx+1]}")

        # 3. From date range coverage_start_date to coverage_end_date
        if voucher.coverage_start_date and voucher.coverage_end_date:
            try:
                s_dt = datetime.strptime(str(voucher.coverage_start_date)[:7], "%Y-%m")
                e_dt = datetime.strptime(str(voucher.coverage_end_date)[:7], "%Y-%m")
                cur = s_dt
                while cur <= e_dt:
                    covered.add(cur.strftime("%B %Y"))
                    y = cur.year + (1 if cur.month == 12 else 0)
                    m = 1 if cur.month == 12 else cur.month + 1
                    cur = datetime(y, m, 1)
            except Exception:
                pass

        return covered

    @staticmethod
    def is_student_covered_for_months(db, student_id, target_months):
        """
        Determines if a student already has ANY voucher (Paid, Partial, or Pending)
        that covers ANY of the target_months.
        target_months can be a single month str or list of month strings.
        Returns (is_covered, matching_voucher, covered_month).
        """
        if isinstance(target_months, str):
            target_months = [target_months]
        
        target_set = {str(m).strip() for m in target_months if str(m).strip()}
        if not target_set:
            return False, None, None

        vouchers = db.query(FeeVoucher).filter(FeeVoucher.student_id == student_id).all()
        for v in vouchers:
            v_months = FeeService.get_voucher_covered_months(v)
            intersection = target_set.intersection(v_months)
            if intersection:
                return True, v, list(intersection)[0]
        return False, None, None

    @staticmethod
    def _is_month_covered_by_multiterm(db, student_id, month_name):
        """Helper backward-compatible check."""
        is_cov, _, _ = FeeService.is_student_covered_for_months(db, student_id, month_name)
        return is_cov

    @staticmethod
    def generate_monthly_fees(month_name, due_date):
        db = get_session()
        generated_count = 0
        skipped_count = 0
        covered_count = 0
        try:
            active_students = db.query(Student).filter_by(status="Active").all()
            batch_assigned_vouchers = set()
            
            for student in active_students:
                # Robust duplicate protection: Check if student has ANY voucher (Monthly, 6-Month, Annual, Paid or Pending) covering month_name
                is_cov, existing_v, c_month = FeeService.is_student_covered_for_months(db, student.id, month_name)
                if is_cov:
                    skipped_count += 1
                    covered_count += 1
                    continue

                v_no = DocumentService.generate_number("Fee Voucher", session=db)
                while v_no in batch_assigned_vouchers:
                    v_no = DocumentService.generate_number("Fee Voucher", session=db)
                batch_assigned_vouchers.add(v_no)

                base_tuition = float(student.monthly_fee or 0.0)
                stu_disc = float(student.discount or 0.0)
                tuition_net = max(0.0, base_tuition - stu_disc)

                transport_fee = 0.0
                route_name = ""
                trans_record = db.query(StudentTransport).filter_by(
                    student_db_id=student.id, is_active=True
                ).first()

                if trans_record and trans_record.route_id:
                    route = db.query(TransportRoute).filter_by(id=trans_record.route_id, is_active=True).first()
                    if route and (route.monthly_fee or 0.0) > 0:
                        transport_fee = float(route.monthly_fee)
                        route_name = route.route_name or "Assigned Route"

                total_voucher_amount = tuition_net + transport_fee

                new_voucher = FeeVoucher(
                    voucher_no=v_no,
                    student_id=student.id,
                    fee_month=month_name,
                    fee_type="Monthly",
                    base_amount=base_tuition,
                    total_amount=total_voucher_amount if total_voucher_amount > 0 else 0.0,
                    paid_amount=0.0,
                    status="Paid" if total_voucher_amount <= 0 else "Pending",
                    due_date=due_date
                )
                db.add(new_voucher)
                db.flush() 

                tuition_item = FeeVoucherItem(
                    voucher_id=new_voucher.id,
                    category="Tuition Fee",
                    description=f"{month_name} Tuition",
                    amount=base_tuition,
                    discount=stu_disc,
                    paid_amount=0.0
                )
                db.add(tuition_item)

                if transport_fee > 0:
                    trans_item = FeeVoucherItem(
                        voucher_id=new_voucher.id,
                        category="Transport Fee",
                        description=f"{month_name} Transport Fee ({route_name})",
                        amount=transport_fee,
                        discount=0.0,
                        paid_amount=0.0
                    )
                    db.add(trans_item)

                generated_count += 1

            db.commit()

            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed: {e}")

            msg = f"Successfully generated {generated_count} monthly vouchers."
            if skipped_count > 0:
                msg += f"\nSkipped {skipped_count} ({covered_count} covered by 6-Month/Annual packages)."
            return True, msg
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {e}"
        finally:
            db.close()

    @staticmethod
    def generate_multi_term_voucher(student_id, term_type="6-Month", start_month="January", year=None, due_date=None):
        """
        Generates a 6-Month or Annual voucher for a student with exact coverage date ranges.
        term_type: "6-Month" or "Annual"
        """
        db = get_session()
        try:
            student = db.query(Student).filter_by(id=student_id).first()
            if not student:
                return False, "Student not found.", None
                
            if not year:
                year = str(datetime.now().year)
                
            months_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            
            try:
                start_idx = months_list.index(start_month)
            except ValueError:
                start_idx = 0
                
            duration = 6 if term_type == "6-Month" else 12
            covered_months = []
            cur_idx = start_idx
            cur_y = int(year)
            
            for _ in range(duration):
                covered_months.append(f"{months_list[cur_idx]} {cur_y}")
                cur_idx += 1
                if cur_idx >= 12:
                    cur_idx = 0
                    cur_y += 1
                    
            coverage_months_str = ", ".join(covered_months)

            # Prevent duplicate voucher generation across any already covered month
            is_cov, existing_v, c_month = FeeService.is_student_covered_for_months(db, student.id, covered_months)
            if is_cov:
                st_text = existing_v.status or "Pending"
                return False, f"Voucher cannot be generated: Month '{c_month}' is already covered by voucher #{existing_v.voucher_no} ({existing_v.fee_month}, Status: {st_text}) for {student.name}. Duplicate billing prevented.", existing_v.id
            
            start_m_num = months_list.index(covered_months[0].split()[0]) + 1
            start_y_num = int(covered_months[0].split()[1])
            coverage_start_date = f"{start_y_num:04d}-{start_m_num:02d}-01"
            
            end_m_num = months_list.index(covered_months[-1].split()[0]) + 1
            end_y_num = int(covered_months[-1].split()[1])
            last_day = calendar.monthrange(end_y_num, end_m_num)[1]
            coverage_end_date = f"{end_y_num:04d}-{end_m_num:02d}-{last_day:02d}"
            
            if term_type == "6-Month":
                fee_label = f"{covered_months[0]} – {covered_months[-1]} (6-Month)"
                base_fee = float(getattr(student, 'six_month_fee', 0.0) or 0.0)
                if base_fee <= 0:
                    base_fee = float(student.monthly_fee or 0.0) * 6
                disc = float(student.discount or 0.0) * 6
            else:
                fee_label = f"Annual Session {year} ({covered_months[0]} – {covered_months[-1]})"
                base_fee = float(getattr(student, 'annual_fee', 0.0) or 0.0)
                if base_fee <= 0:
                    base_fee = float(student.monthly_fee or 0.0) * 12
                disc = float(student.discount or 0.0) * 12
                
            net_tuition = max(0.0, base_fee - disc)
            
            # Transport for multi-month period
            transport_total = 0.0
            route_name = ""
            trans_record = db.query(StudentTransport).filter_by(
                student_db_id=student.id, is_active=True
            ).first()
            if trans_record and trans_record.route_id:
                route = db.query(TransportRoute).filter_by(id=trans_record.route_id, is_active=True).first()
                if route and (route.monthly_fee or 0.0) > 0:
                    transport_total = float(route.monthly_fee) * duration
                    route_name = route.route_name or "Assigned Route"
                    
            total_amount = net_tuition + transport_total
            if not due_date:
                due_date = f"10 {covered_months[0]}"
                
            v_no = DocumentService.generate_number("Fee Voucher", session=db)
            
            new_voucher = FeeVoucher(
                voucher_no=v_no,
                student_id=student.id,
                fee_month=fee_label,
                fee_type=term_type,
                coverage_start_date=coverage_start_date,
                coverage_end_date=coverage_end_date,
                coverage_months=coverage_months_str,
                base_amount=base_fee,
                total_amount=total_amount if total_amount > 0 else 0.0,
                paid_amount=0.0,
                status="Paid" if total_amount <= 0 else "Pending",
                due_date=due_date
            )
            db.add(new_voucher)
            db.flush()
            
            tuition_item = FeeVoucherItem(
                voucher_id=new_voucher.id,
                category="Tuition Fee",
                description=f"{term_type} Tuition ({fee_label})",
                amount=base_fee,
                discount=disc,
                paid_amount=0.0
            )
            db.add(tuition_item)
            
            if transport_total > 0:
                trans_item = FeeVoucherItem(
                    voucher_id=new_voucher.id,
                    category="Transport Fee",
                    description=f"{term_type} Transport Fee ({route_name})",
                    amount=transport_total,
                    discount=0.0,
                    paid_amount=0.0
                )
                db.add(trans_item)
                
            db.commit()
            app_state.notify_data_changed()
            return True, f"{term_type} voucher generated successfully for {student.name}.", new_voucher.id
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {e}", None
        finally:
            db.close()

    @staticmethod
    def generate_admission_voucher(student_id_or_sys_id, billing_cycle="Monthly", admission_fee=0.0, admission_fee_paid=False, due_date=None):
        """
        Automatically generates the initial enrollment fee voucher upon student admission:
        - If billing_cycle is Monthly: generates the monthly voucher for the current month.
        - If billing_cycle is 6-Month or Annual: generates multi-term package voucher.
        - Attaches Admission Fee line item (if admission_fee > 0).
        - If admission_fee_paid is True: records immediate FeePayment allocation for the admission fee
          so it is marked [PAID] and only the tuition/package dues remain pending.
        - If admission_fee_paid is False: the admission fee remains [PENDING] on the voucher.
        """
        db = get_session()
        try:
            student = db.query(Student).filter(
                (Student.id == student_id_or_sys_id) | (Student.student_id == str(student_id_or_sys_id))
            ).first()
            if not student:
                return False, "Student not found for voucher generation.", None

            now = datetime.now()
            current_month = now.strftime("%B")
            current_year = now.year
            month_name = now.strftime("%B %Y")
            
            cycle_clean = str(billing_cycle).strip().lower()
            if "annual" in cycle_clean:
                term_type = "Annual"
                duration = 12
            elif "6" in cycle_clean or "six" in cycle_clean:
                term_type = "6-Month"
                duration = 6
            else:
                term_type = "Monthly"
                duration = 1

            all_months = ["January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"]
            
            if term_type == "Monthly":
                fee_label = month_name
                base_fee = float(student.monthly_fee or 0.0)
                disc = float(student.discount or 0.0)
                coverage_start = f"{current_year}-{now.month:02d}-01"
                coverage_end = f"{current_year}-{now.month:02d}-28"
                coverage_months_str = month_name
            elif term_type == "6-Month":
                start_idx = all_months.index(current_month) if current_month in all_months else 0
                covered_months = [all_months[(start_idx + i) % 12] for i in range(6)]
                fee_label = f"6-Month Package ({covered_months[0]} – {covered_months[-1]} {current_year})"
                base_fee = float(student.six_month_fee or 0.0)
                if base_fee <= 0:
                    base_fee = float(student.monthly_fee or 0.0) * 6
                disc = float(student.discount or 0.0) * 6
                coverage_start = f"{current_year}-{now.month:02d}-01"
                coverage_end = f"{current_year + (1 if start_idx + 6 > 12 else 0)}-{((start_idx + 5) % 12 + 1):02d}-28"
                coverage_months_str = json.dumps([f"{m} {current_year}" for m in covered_months])
            else: # Annual
                start_idx = all_months.index(current_month) if current_month in all_months else 0
                covered_months = [all_months[(start_idx + i) % 12] for i in range(12)]
                fee_label = f"Annual Package ({covered_months[0]} {current_year} – {covered_months[-1]} {current_year + 1})"
                base_fee = float(student.annual_fee or 0.0)
                if base_fee <= 0:
                    base_fee = float(student.monthly_fee or 0.0) * 12
                disc = float(student.discount or 0.0) * 12
                coverage_start = f"{current_year}-{now.month:02d}-01"
                coverage_end = f"{current_year + 1}-{now.month:02d}-01"
                coverage_months_str = json.dumps([f"{m} {current_year}" for m in covered_months])

            # Check if student is already covered for this period
            check_months = covered_months if term_type != "Monthly" else [month_name]
            is_cov, existing_v, c_month = FeeService.is_student_covered_for_months(db, student.id, check_months)
            if is_cov:
                return True, f"Student {student.name} already has voucher #{existing_v.voucher_no} ({existing_v.fee_month}). Duplicate voucher avoided.", existing_v.id

            net_tuition = max(0.0, base_fee - disc)
            adm_fee = float(admission_fee or 0.0)

            # Transport
            transport_total = 0.0
            route_name = ""
            trans_record = db.query(StudentTransport).filter_by(student_db_id=student.id, is_active=True).first()
            if trans_record and trans_record.route_id:
                route = db.query(TransportRoute).filter_by(id=trans_record.route_id, is_active=True).first()
                if route and (route.monthly_fee or 0.0) > 0:
                    transport_total = float(route.monthly_fee) * duration
                    route_name = route.route_name or "Assigned Route"

            total_voucher_amt = net_tuition + adm_fee + transport_total
            total_base_amt = base_fee + adm_fee + transport_total

            if not due_date:
                due_date = f"10 {current_month} {current_year}"

            v_no = DocumentService.generate_number("Fee Voucher", session=db)
            new_voucher = FeeVoucher(
                voucher_no=v_no,
                student_id=student.id,
                fee_month=fee_label,
                fee_type=term_type,
                coverage_start_date=coverage_start,
                coverage_end_date=coverage_end,
                coverage_months=coverage_months_str,
                base_amount=total_base_amt,
                total_amount=total_voucher_amt,
                paid_amount=0.0,
                status="Pending",
                due_date=due_date
            )
            db.add(new_voucher)
            db.flush()

            # Item 1: Tuition
            tuition_item = FeeVoucherItem(
                voucher_id=new_voucher.id,
                category="Tuition Fee",
                description=f"{term_type} Tuition ({fee_label})",
                amount=base_fee,
                discount=disc,
                paid_amount=0.0
            )
            db.add(tuition_item)

            # Item 2: Transport (if any)
            if transport_total > 0:
                trans_item = FeeVoucherItem(
                    voucher_id=new_voucher.id,
                    category="Transport Fee",
                    description=f"{term_type} Transport ({route_name})",
                    amount=transport_total,
                    discount=0.0,
                    paid_amount=0.0
                )
                db.add(trans_item)

            # Item 3: Admission Fee (if any)
            adm_item = None
            if adm_fee > 0:
                adm_item = FeeVoucherItem(
                    voucher_id=new_voucher.id,
                    category="Admission Fee",
                    description="One-time Admission / Registration Fee",
                    amount=adm_fee,
                    discount=0.0,
                    paid_amount=0.0
                )
                db.add(adm_item)

            db.flush()

            # If admission fee was paid during admission:
            if admission_fee_paid and adm_fee > 0 and adm_item:
                adm_item.paid_amount = adm_fee
                new_voucher.paid_amount = adm_fee
                if new_voucher.paid_amount >= new_voucher.total_amount:
                    new_voucher.status = "Paid"
                else:
                    new_voucher.status = "Partial"

                receipt_no = DocumentService.generate_number("Fee Receipt", session=db)
                payment = FeePayment(
                    receipt_no=receipt_no,
                    voucher_id=new_voucher.id,
                    amount_paid=adm_fee,
                    fine_included=0.0,
                    discount_included=0.0,
                    payment_method="Cash",
                    payment_date=now.strftime("%Y-%m-%d"),
                    notes="Admission Fee paid at the time of admission enrollment."
                )
                db.add(payment)
                db.flush()

                allocation = FeePaymentAllocation(
                    payment_id=payment.id,
                    voucher_item_id=adm_item.id,
                    category="Admission Fee",
                    description="Admission Fee Paid at Enrollment",
                    amount_allocated=adm_fee,
                    discount_allocated=0.0
                )
                db.add(allocation)
            elif total_voucher_amt <= 0:
                new_voucher.status = "Paid"

            db.commit()
            app_state.notify_data_changed()
            return True, f"Voucher {v_no} generated successfully for {student.name}.", new_voucher.id
        except Exception as e:
            db.rollback()
            return False, f"Voucher Error: {e}", None
        finally:
            db.close()

    @staticmethod
    def generate_bulk_multi_term_fees(term_type="6-Month", start_month="January", year=None, due_date=None):
        """Bulk generates 6-Month or Annual vouchers for all active students."""
        db = get_session()
        generated_count = 0
        skipped_count = 0
        try:
            active_students = db.query(Student).filter_by(status="Active").all()
            for s in active_students:
                success, msg, v_id = FeeService.generate_multi_term_voucher(s.id, term_type, start_month, year, due_date)
                if success:
                    generated_count += 1
                else:
                    skipped_count += 1
            return True, f"Generated {generated_count} {term_type} vouchers.\nSkipped {skipped_count}."
        except Exception as e:
            return False, f"Bulk Generation Error: {e}"
        finally:
            db.close()

    @staticmethod
    def get_fee_reminder_status():
        """
        Dashboard reminder check: Checks if current month has pending fee vouchers for active students.
        """
        db = get_session()
        try:
            now = datetime.now()
            current_month_str = now.strftime("%B %Y")
            active_students = db.query(Student).filter_by(status="Active").all()
            if not active_students:
                return {"all_generated": True, "unbilled_count": 0, "message": ""}
                
            unbilled = 0
            for stu in active_students:
                vouch = db.query(FeeVoucher).filter_by(student_id=stu.id, fee_month=current_month_str).first()
                if vouch:
                    continue
                if FeeService._is_month_covered_by_multiterm(db, stu.id, current_month_str):
                    continue
                unbilled += 1
                
            if unbilled > 0:
                return {
                    "all_generated": False,
                    "unbilled_count": unbilled,
                    "current_month": current_month_str,
                    "message": f"Monthly Fee Reminder: {unbilled} active student(s) do not have fee vouchers for {current_month_str}."
                }
            return {"all_generated": True, "unbilled_count": 0, "current_month": current_month_str, "message": ""}
        except Exception as e:
            return {"all_generated": True, "unbilled_count": 0, "message": ""}
        finally:
            db.close()

    @staticmethod
    def search_student_for_payment(search_text):
        db = get_session()
        try:
            search = f"%{search_text.strip()}%"

            student = db.query(Student).options(
                joinedload(Student.academic_class),
                joinedload(Student.academic_section)
            ).filter(Student.student_id.ilike(search_text.strip())).first()

            if not student:
                student = db.query(Student).options(
                    joinedload(Student.academic_class),
                    joinedload(Student.academic_section)
                ).filter(
                    (Student.first_name.ilike(search)) |
                    (Student.last_name.ilike(search)) |
                    (Student.phone.ilike(search)) |
                    (Student.admission_number.ilike(search))
                ).first()

            if not student:
                return None, []

            all_vouchers = db.query(FeeVoucher).options(
                joinedload(FeeVoucher.items)
            ).filter(
                FeeVoucher.student_id == student.id
            ).order_by(FeeVoucher.id.asc()).all()

            pending_vouchers = [v for v in all_vouchers if (v.total_amount - (v.paid_amount or 0.0)) > 0]

            return student, pending_vouchers
        finally:
            db.close()

    @staticmethod
    def search_students_with_dues(search_text, limit=15):
        """
        Searches students by name, ID, phone, admission number.
        Calculates each matched student's total pending fee and number of pending vouchers.
        Sorts students so those with pending fees appear FIRST (highest pending dues first),
        followed by students with zero pending dues.
        Returns a list of student fee summary dicts.
        """
        txt = (search_text or "").strip()
        if not txt:
            return []
        db = get_session()
        try:
            search_pattern = f"%{txt}%"
            students = db.query(Student).options(
                joinedload(Student.academic_class),
                joinedload(Student.academic_section)
            ).filter(
                (Student.student_id.ilike(search_pattern)) |
                (Student.first_name.ilike(search_pattern)) |
                (Student.last_name.ilike(search_pattern)) |
                (Student.phone.ilike(search_pattern)) |
                (Student.admission_number.ilike(search_pattern))
            ).limit(40).all()

            results = []
            for s in students:
                vouchers = db.query(FeeVoucher).filter_by(student_id=s.id).all()
                total_pending = 0.0
                pending_count = 0
                for v in vouchers:
                    rem = float(v.total_amount or 0.0) - float(v.paid_amount or 0.0)
                    if rem > 0:
                        total_pending += rem
                        pending_count += 1
                cls_name = s.academic_class.name if s.academic_class else "No Class"
                sec_name = f" - {s.academic_section.name}" if s.academic_section else ""
                s_name = f"{s.first_name} {s.last_name or ''}".strip()
                results.append({
                    "id": s.id,
                    "student_id": s.student_id or str(s.id),
                    "name": s_name,
                    "class_name": f"{cls_name}{sec_name}",
                    "father_name": s.father_name or "",
                    "phone": s.phone or s.father_phone or "",
                    "pending_dues": total_pending,
                    "pending_vouchers_count": pending_count,
                    "has_dues": total_pending > 0
                })

            # Prioritize students with pending dues (highest first), then alphabetical
            results.sort(key=lambda r: (not r["has_dues"], -r["pending_dues"], r["name"].lower()))
            return results[:limit]
        finally:
            db.close()

    @staticmethod
    def get_student_category_position(student_id):
        db = get_session()
        try:
            vouchers = db.query(FeeVoucher).options(
                joinedload(FeeVoucher.items)
            ).filter(FeeVoucher.student_id == student_id).all()

            category_dues = {}
            total_billed = 0.0
            total_discount = 0.0
            total_paid = 0.0
            total_outstanding = 0.0

            for v in vouchers:
                items = v.effective_items
                total_paid += (v.paid_amount or 0.0)
                total_billed += (v.base_amount or v.total_amount or 0.0)
                
                for it in items:
                    cat = it.category or "Other Fee"
                    rem = it.remaining_balance
                    if rem > 0:
                        category_dues[cat] = category_dues.get(cat, 0.0) + rem
                        total_outstanding += rem
                    total_discount += (it.discount or 0.0)

            return {
                "category_dues": category_dues,
                "total_billed": total_billed,
                "total_discount": total_discount,
                "total_paid": total_paid,
                "total_outstanding": total_outstanding
            }
        finally:
            db.close()

    @staticmethod
    def process_payment(voucher_id, amount_paid, fine=0.0, discount=0.0, method="Cash", allocations=None, notes=None):
        db = get_session()
        try:
            voucher = db.query(FeeVoucher).options(
                joinedload(FeeVoucher.student).joinedload(Student.academic_class),
                joinedload(FeeVoucher.student).joinedload(Student.academic_section),
                joinedload(FeeVoucher.items)
            ).filter_by(id=voucher_id).first()
            if not voucher:
                return False, "Voucher not found.", None

            if amount_paid <= 0:
                return False, "Payment amount must be greater than zero.", None

            receipt_no = DocumentService.generate_number("Fee Receipt", session=db)

            payment = FeePayment(
                receipt_no=receipt_no,
                voucher_id=voucher.id,
                amount_paid=amount_paid,
                fine_included=fine,
                discount_included=discount,
                payment_method=method,
                payment_date=datetime.now().strftime("%Y-%m-%d"),
                notes=notes
            )
            db.add(payment)
            db.flush() 

            allocated_items_data = []

            if allocations and len(allocations) > 0:
                for alloc in allocations:
                    cat = alloc.get("category", "Tuition Fee")
                    desc = alloc.get("description", "")
                    pay_now = float(alloc.get("paid_now", 0.0))
                    row_disc = float(alloc.get("discount", 0.0))
                    item_id = alloc.get("voucher_item_id")

                    v_item = None
                    if item_id:
                        v_item = db.query(FeeVoucherItem).filter_by(id=item_id, voucher_id=voucher.id).first()
                    
                    if not v_item:
                        v_item = db.query(FeeVoucherItem).filter_by(voucher_id=voucher.id, category=cat).first()

                    if v_item:
                        if row_disc > 0:
                            v_item.discount = (v_item.discount or 0.0) + row_disc
                        v_item.paid_amount = min(v_item.net_payable, (v_item.paid_amount or 0.0) + pay_now)
                    else:
                        v_item = FeeVoucherItem(
                            voucher_id=voucher.id,
                            category=cat,
                            description=desc or f"{cat} charge",
                            amount=alloc.get("amount", pay_now + row_disc),
                            discount=row_disc,
                            paid_amount=pay_now
                        )
                        db.add(v_item)
                        db.flush()

                    db.add(FeePaymentAllocation(
                        payment_id=payment.id,
                        voucher_item_id=v_item.id,
                        category=cat,
                        description=desc or v_item.description,
                        amount_allocated=pay_now,
                        discount_allocated=row_disc
                    ))

                    allocated_items_data.append({
                        "category": cat,
                        "description": desc or v_item.description,
                        "amount": v_item.amount,
                        "discount": v_item.discount,
                        "net": v_item.net_payable,
                        "paid": pay_now,
                        "remaining": v_item.remaining_balance
                    })
            else:
                rem_to_allocate = amount_paid
                for item in voucher.effective_items:
                    if rem_to_allocate <= 0:
                        break
                    due = item.remaining_balance
                    if due > 0:
                        alloc_amt = min(rem_to_allocate, due)
                        if item.id:
                            item.paid_amount = (item.paid_amount or 0.0) + alloc_amt
                            alloc_item_id = item.id
                        else:
                            real_item = FeeVoucherItem(
                                voucher_id=voucher.id,
                                category=item.category,
                                description=item.description,
                                amount=item.amount,
                                discount=item.discount,
                                paid_amount=(item.paid_amount or 0.0) + alloc_amt
                            )
                            db.add(real_item)
                            db.flush()
                            alloc_item_id = real_item.id

                        db.add(FeePaymentAllocation(
                            payment_id=payment.id,
                            voucher_item_id=alloc_item_id,
                            category=item.category,
                            description=item.description,
                            amount_allocated=alloc_amt,
                            discount_allocated=0.0
                        ))
                        allocated_items_data.append({
                            "category": item.category,
                            "description": item.description,
                            "amount": item.amount,
                            "discount": item.discount,
                            "net": item.net_payable,
                            "paid": alloc_amt,
                            "remaining": max(0.0, item.net_payable - (item.paid_amount or 0.0))
                        })
                        rem_to_allocate -= alloc_amt

            voucher_items = db.query(FeeVoucherItem).filter_by(voucher_id=voucher.id).all()
            if voucher_items:
                voucher.total_amount = sum(it.net_payable for it in voucher_items)
                voucher.paid_amount = sum(it.paid_amount for it in voucher_items)
            else:
                voucher.total_amount = max(0.0, (voucher.total_amount or 0.0) + fine - discount)
                voucher.paid_amount = (voucher.paid_amount or 0.0) + amount_paid

            if voucher.paid_amount >= voucher.total_amount:
                voucher.status = "Paid"
            elif voucher.paid_amount > 0:
                voucher.status = "Partially Paid"

            db.commit()

            try:
                from core.backup_service import BackupService
                BackupService.trigger_auto_backup_async("Fee Payment Collection")
            except Exception:
                pass

            stu = voucher.student
            stu_full_name = f"{stu.first_name} {stu.last_name or ''}".strip()
            cls_name = stu.academic_class.name if stu.academic_class else ""
            sec_name = stu.academic_section.name if stu.academic_section else ""

            cat_orig_map = {}
            cat_disc_map = {}
            cat_paid_map = {}
            cat_rem_map = {}
            for row in allocated_items_data:
                c = row["category"]
                cat_orig_map[c] = cat_orig_map.get(c, 0.0) + float(row.get("amount") or 0.0)
                cat_disc_map[c] = cat_disc_map.get(c, 0.0) + float(row.get("discount") or 0.0)
                cat_paid_map[c] = cat_paid_map.get(c, 0.0) + float(row.get("paid") or 0.0)
                cat_rem_map[c] = float(row.get("remaining") or 0.0)

            for it in voucher.effective_items:
                c = it.category or "Other Fee"
                if c not in cat_orig_map:
                    cat_orig_map[c] = float(it.amount or 0.0)
                    cat_disc_map[c] = float(it.discount or 0.0)
                    cat_rem_map[c] = it.remaining_balance

            gross_voucher_total = sum(float(it.amount or 0.0) for it in voucher.effective_items) + float(fine or 0.0)
            if gross_voucher_total <= 0:
                gross_voucher_total = float(voucher.total_amount or 0.0)

            total_voucher_discount = max(
                float(discount or 0.0),
                sum(float(it.discount or 0.0) for it in voucher.effective_items)
            )

            current_net_fee = float(voucher.total_amount or 0.0)
            if current_net_fee <= 0 and gross_voucher_total > 0:
                current_net_fee = max(0.0, gross_voucher_total - total_voucher_discount)

            other_vouchers = db.query(FeeVoucher).filter(
                FeeVoucher.student_id == stu.id,
                FeeVoucher.id != voucher.id
            ).all()
            prev_dues = sum(max(0.0, float(v.total_amount or 0.0) - float(v.paid_amount or 0.0)) for v in other_vouchers)
            total_payable_before = prev_dues + current_net_fee

            rem_balance = max(0.0, current_net_fee - float(voucher.paid_amount or 0.0))
            overall_remaining = prev_dues + rem_balance

            receipt_data = {
                "_payment_id": payment.id,
                "_voucher_id": voucher.id,
                "student.name": stu_full_name,
                "student.student_id": stu.student_id,
                "academic.class": cls_name,
                "academic.section": sec_name,
                "academic.session": stu.academic_session or "",
                "fee.fee_month": voucher.fee_month,
                "fee.receipt_number": receipt_no,
                "fee.total_fee": f"{gross_voucher_total:,.0f}",
                "fee.total_discount": f"{total_voucher_discount:,.0f}",
                "fee.monthly_fee": f"{voucher.base_amount:,.0f}",
                "fee.current_fee": f"{current_net_fee:,.0f}",
                "fee.previous_dues": f"{prev_dues:,.0f}",
                "fee.total_payable": f"{total_payable_before:,.0f}",
                "fee.amount_received": f"{amount_paid:,.0f}",
                "fee.remaining_balance": f"{rem_balance:,.0f}",
                "fee.total_remaining_balance": f"{overall_remaining:,.0f}",
                "fee.payment_date": payment.payment_date,
                "fee.payment_method": method,
                "fee.status": "Paid" if rem_balance <= 0 else "Pending",
                
                "fee.tuition_fee": f"{cat_orig_map.get('Tuition Fee', voucher.base_amount or 0.0):,.0f}",
                "fee.tuition_discount": f"{cat_disc_map.get('Tuition Fee', discount):,.0f}",
                "fee.tuition_paid": f"{cat_paid_map.get('Tuition Fee', 0.0):,.0f}",
                "fee.tuition_remaining": f"{cat_rem_map.get('Tuition Fee', 0.0):,.0f}",
                
                "fee.transport_fee": f"{cat_orig_map.get('Transport Fee', 0.0):,.0f}",
                "fee.transport_discount": f"{cat_disc_map.get('Transport Fee', 0.0):,.0f}",
                "fee.transport_paid": f"{cat_paid_map.get('Transport Fee', 0.0):,.0f}",
                "fee.transport_remaining": f"{cat_rem_map.get('Transport Fee', 0.0):,.0f}",

                "fee.admission_fee": f"{cat_orig_map.get('Admission Fee', 0.0):,.0f}",
                "fee.admission_discount": f"{cat_disc_map.get('Admission Fee', 0.0):,.0f}",
                "fee.admission_paid": f"{cat_paid_map.get('Admission Fee', 0.0):,.0f}",
                "fee.admission_remaining": f"{cat_rem_map.get('Admission Fee', 0.0):,.0f}",

                "fee.exam_fee": f"{cat_orig_map.get('Examination Fee', 0.0):,.0f}",
                "fee.exam_discount": f"{cat_disc_map.get('Examination Fee', 0.0):,.0f}",
                "fee.exam_paid": f"{cat_paid_map.get('Examination Fee', 0.0):,.0f}",
                "fee.exam_remaining": f"{cat_rem_map.get('Examination Fee', 0.0):,.0f}",

                "fee.other_charges": f"{cat_orig_map.get('Other Fee', 0.0):,.0f}",
                "fee.other_discount": f"{cat_disc_map.get('Other Fee', 0.0):,.0f}",
                "fee.other_paid": f"{cat_paid_map.get('Other Fee', 0.0):,.0f}",
                "fee.other_remaining": f"{cat_rem_map.get('Other Fee', 0.0):,.0f}",

                "fee.fine": f"{fine:,.0f}",

                "student_name": stu_full_name,
                "student_id": stu.student_id,
                "class": cls_name,
                "fee_month": voucher.fee_month,
                "receipt_number": receipt_no,
                "total_amount": str(current_net_fee),
                "paid_amount": str(amount_paid),
                "remaining_balance": str(rem_balance),
                "payment_date": payment.payment_date
            }

            for i, itm in enumerate(allocated_items_data[:10], 1):
                receipt_data[f"fee.item_{i}_category"] = itm["category"]
                receipt_data[f"fee.item_{i}_description"] = itm["description"]
                receipt_data[f"fee.item_{i}_amount"] = f"{itm['amount']:,.0f}"
                receipt_data[f"fee.item_{i}_discount"] = f"{itm['discount']:,.0f}"
                receipt_data[f"fee.item_{i}_paid"] = f"{itm['paid']:,.0f}"
                receipt_data[f"fee.item_{i}_remaining"] = f"{itm['remaining']:,.0f}"

            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed: {e}")

            return True, "Payment successful!", receipt_data
        except Exception as e:
            db.rollback()
            return False, f"Transaction Error: {e}", None
        finally:
            db.close()

    @staticmethod
    def get_student_ledger(student_id):
        db = get_session()
        try:
            vouchers = db.query(FeeVoucher).options(
                joinedload(FeeVoucher.items),
                joinedload(FeeVoucher.payments).joinedload(FeePayment.allocations)
            ).filter(FeeVoucher.student_id == student_id).order_by(FeeVoucher.id.asc()).all()

            events = []
            for v in vouchers:
                v_date = v.created_at[:10] if v.created_at else "2026-01-01"
                for item in v.effective_items:
                    pmt_disc_for_item = 0.0
                    for p in v.payments:
                        if p.allocations:
                            for a in p.allocations:
                                if a.voucher_item_id == item.id:
                                    pmt_disc_for_item += float(a.discount_allocated or 0.0)
                        else:
                            pmt_disc_for_item += float(p.discount_included or 0.0)

                    init_item_disc = max(0.0, float(item.discount or 0.0) - pmt_disc_for_item)

                    events.append({
                        "date": v_date,
                        "timestamp": v.created_at or "",
                        "ref_no": v.voucher_no,
                        "type": "Charge",
                        "category": item.category,
                        "description": item.description or f"{v.fee_month} {item.category}",
                        "debit": float(item.amount or 0.0),
                        "credit": 0.0,
                        "discount": init_item_disc
                    })

                for p in v.payments:
                    p_date = p.payment_date or "2026-01-01"
                    if p.allocations:
                        for alloc in p.allocations:
                            events.append({
                                "date": p_date,
                                "timestamp": p_date,
                                "ref_no": p.receipt_no,
                                "type": "Payment",
                                "category": alloc.category,
                                "description": alloc.description or f"Payment - {alloc.category}",
                                "debit": 0.0,
                                "credit": float(alloc.amount_allocated or 0.0),
                                "discount": float(alloc.discount_allocated or 0.0)
                            })
                    else:
                        events.append({
                            "date": p_date,
                            "timestamp": p_date,
                            "ref_no": p.receipt_no,
                            "type": "Payment",
                            "category": "Tuition Fee",
                            "description": f"Payment - {v.fee_month}",
                            "debit": 0.0,
                            "credit": float(p.amount_paid or 0.0),
                            "discount": float(p.discount_included or 0.0)
                        })

            def sort_key(e):
                type_order = 0 if e["type"] == "Charge" else 1
                return (e["date"], type_order)

            events.sort(key=sort_key)

            running_balance = 0.0
            ledger = []
            for ev in events:
                running_balance += ev["debit"]
                running_balance -= (ev["credit"] + ev["discount"])
                ev["balance"] = max(0.0, running_balance)
                ledger.append(ev)

            return ledger
        finally:
            db.close()

    @staticmethod
    def get_financial_analytics():
        db = get_session()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            month_str = datetime.now().strftime("%Y-%m")
            
            # FAST CALCULATION: Direct SUM from DB instead of loading records in Python
            today_collection = db.query(func.sum(FeePayment.amount_paid)).filter(FeePayment.payment_date == today_str).scalar() or 0.0
            monthly_collection = db.query(func.sum(FeePayment.amount_paid)).filter(FeePayment.payment_date.like(f"{month_str}%")).scalar() or 0.0
            
            # FAST PENDING CALCULATION
            pending_query = db.query(
                func.sum(FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)),
                func.count(FeeVoucher.id)
            ).filter((FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)) > 0).first()
            
            total_pending = float(pending_query[0] or 0.0)
            pending_count = int(pending_query[1] or 0)

            # CATEGORY TOTALS
            category_totals = {}
            allocs = db.query(
                FeePaymentAllocation.category, 
                func.sum(FeePaymentAllocation.amount_allocated)
            ).group_by(FeePaymentAllocation.category).all()
            
            for cat, amt in allocs:
                category_totals[cat or "Other Fee"] = float(amt or 0.0)
                
            # Fallback for unallocated old records
            unallocated_payments = db.query(func.sum(FeePayment.amount_paid)).outerjoin(
                FeePaymentAllocation, FeePayment.id == FeePaymentAllocation.payment_id
            ).filter(FeePaymentAllocation.id == None).scalar() or 0.0
            
            if unallocated_payments > 0:
                category_totals["Tuition Fee"] = category_totals.get("Tuition Fee", 0.0) + unallocated_payments

            return {
                "today_collection": today_collection,
                "monthly_collection": monthly_collection,
                "total_pending": total_pending,
                "pending_count": pending_count,
                "category_totals": category_totals
            }
        finally:
            db.close()

    @staticmethod
    def get_students_pending_balances(student_ids):
        """Batch-computes pending fee balance for multiple students in a single indexed query."""
        if not student_ids:
            return {}
        from sqlalchemy import func, case
        db = get_session()
        try:
            rows = db.query(
                FeeVoucher.student_id,
                func.sum(
                    case(
                        (FeeVoucher.total_amount > func.coalesce(FeeVoucher.paid_amount, 0), FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)),
                        else_=0.0
                    )
                )
            ).filter(FeeVoucher.student_id.in_(student_ids)).group_by(FeeVoucher.student_id).all()
            result = {sid: 0.0 for sid in student_ids}
            for sid, amt in rows:
                result[sid] = float(amt or 0.0)
            return result
        finally:
            db.close()

    @staticmethod
    def get_student_pending_balance(student_id):
        db = get_session()
        try:
            vouchers = db.query(FeeVoucher).filter(FeeVoucher.student_id == student_id).all()
            return sum([max(0.0, (v.total_amount or 0.0) - (v.paid_amount or 0.0)) for v in vouchers])
        finally:
            db.close()

    @staticmethod
    def get_class_pending_balances(class_id):
        db = get_session()
        try:
            students = db.query(Student).options(joinedload(Student.academic_section)).filter_by(class_id=class_id, status="Active").all()
            if not students:
                return []
            stu_ids = [s.id for s in students]
            balances = FeeService.get_students_pending_balances(stu_ids)
            results = []
            for stu in students:
                pending = balances.get(stu.id, 0.0)
                if pending > 0:
                    results.append({
                        "student_id": stu.student_id,
                        "name": f"{stu.first_name} {stu.last_name or ''}".strip(),
                        "section": stu.academic_section.name if stu.academic_section else "N/A",
                        "phone": stu.phone or stu.father_phone or "-",
                        "pending_amount": pending
                    })
            results.sort(key=lambda x: (x["section"], x["name"]))
            return results
        finally:
            db.close()

    @staticmethod
    def get_all_pending_vouchers(class_id=None):
        db = get_session()
        try:
            # FAST LOADING: Load ONLY vouchers that are actually pending
            query = db.query(FeeVoucher).options(
                joinedload(FeeVoucher.student).joinedload(Student.academic_class),
                joinedload(FeeVoucher.items)
            ).filter((FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)) > 0)
            
            if class_id and class_id != "All":
                query = query.join(Student).filter(Student.class_id == class_id)

            return query.all()
        finally:
            db.close()

    @staticmethod
    def get_payment_history(limit=100):
        db = get_session()
        try:
            return db.query(FeePayment).options(
                joinedload(FeePayment.voucher).joinedload(FeeVoucher.student),
                joinedload(FeePayment.allocations)
            ).order_by(FeePayment.id.desc()).limit(limit).all()
        finally:
            db.close()

    @staticmethod
    def get_fee_collection_stats():
        db = get_session()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # FAST CALCULATION
            collected = db.query(func.sum(FeePayment.amount_paid)).scalar() or 0.0
            
            # Fast Due & Overdue calculation natively in SQLite
            stats = db.query(
                func.sum(
                    case(
                        (((FeeVoucher.status == "Overdue") | (FeeVoucher.due_date < today_str)), 
                         FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)),
                        else_=0.0
                    )
                ).label("overdue"),
                func.sum(
                    case(
                        (((FeeVoucher.status != "Overdue") & ((FeeVoucher.due_date >= today_str) | (FeeVoucher.due_date == None))), 
                         FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)),
                        else_=0.0
                    )
                ).label("due")
            ).filter((FeeVoucher.total_amount - func.coalesce(FeeVoucher.paid_amount, 0)) > 0).first()

            return {
                "collected": float(collected),
                "due": float(stats.due or 0.0) if stats else 0.0,
                "overdue": float(stats.overdue or 0.0) if stats else 0.0
            }
        except Exception as e:
            print(f"Stats Error: {e}")
            return {"collected": 0.0, "due": 0.0, "overdue": 0.0}
        finally: 
            db.close()