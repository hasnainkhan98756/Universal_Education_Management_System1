import os
from datetime import datetime
from database.connection import get_session
from core.state_manager import app_state
from sqlalchemy.orm import joinedload

class DataResolverService:
    """
    Centralized Field Resolver utilizing strict Namespaces (student.*, parent.*, admission.*, fee.*, system.*).
    Guarantees a single, collision-free source of truth for the PDF Engine.
    """

    @staticmethod
    def get_student_data(student_system_id):
        from database.models.student import Student
        db = get_session()
        try:
            student = db.query(Student).options(
                joinedload(Student.academic_class),
                joinedload(Student.academic_section)
            ).filter_by(student_id=student_system_id).first()

            if not student:
                return {}

            full_name = f"{student.first_name} {student.last_name or ''}".strip()
            cls_name = student.academic_class.name if student.academic_class else ""
            sec_name = student.academic_section.name if student.academic_section else ""

            data = {
                # Student Identity
                "student.name": full_name,
                "student.date_of_birth": student.dob or "",
                "student.b_form": student.b_form or "",
                "student.student_id": student.student_id or "",
                "student.roll_number": str(student.id),
                "student.blood_group": student.blood_group or "",
                "student.gender": student.gender or "",
                "student.nationality": student.nationality or "",
                "student.religion": student.religion or "",
                "student.place_of_birth": getattr(student, "place_of_birth", ""),
                "student.contact_number": student.phone or "",
                "student.address": student.current_address or "",
                "student.city": getattr(student, "city", ""),
                "student.district": getattr(student, "district", ""),
                "student.email": student.email or "",
                "student.photo": student.photo_path if student.photo_path and os.path.exists(student.photo_path) else "",

                # Parent / Guardian Information
                "parent.father_name": student.father_name or "",
                "parent.father_cnic": getattr(student, "father_cnic", ""),
                "parent.father_mobile": student.father_phone or "",
                "parent.father_occupation": getattr(student, "father_occupation", ""),
                "parent.mother_name": getattr(student, "mother_name", ""),
                "parent.mother_cnic": getattr(student, "mother_cnic", ""),
                "parent.guardian_name": student.guardian_name or "",
                "parent.guardian_relationship": getattr(student, "guardian_relationship", ""),
                "parent.guardian_cnic": getattr(student, "guardian_cnic", ""),
                "parent.monthly_income": getattr(student, "family_income", ""),

                # Academic Information
                "academic.class": cls_name,
                "academic.section": sec_name,
                "academic.session": student.academic_session or "",

                # Admission / Previous Education
                "admission.application_number": student.admission_number or "",
                "admission.admission_number": student.admission_number or "",
                "admission.date_of_admission": student.admission_date or "",
                "admission.admission_type": getattr(student, "admission_type", "New Admission"),
                "admission.previous_school": student.previous_school or "",
                "admission.previous_class": getattr(student, "previous_class", ""),
                "admission.previous_session": getattr(student, "previous_session", ""),
                "admission.previous_examination": getattr(student, "previous_exam", ""),
                "admission.previous_result": getattr(student, "previous_result", ""),
                "admission.transfer_certificate_number": getattr(student, "tc_number", ""),
                "admission.transfer_certificate_date": getattr(student, "tc_date", ""),

                # Medical / Emergency
                "medical.emergency_contact_person": getattr(student, "emergency_contact_person", ""),
                "medical.emergency_relationship": getattr(student, "emergency_relationship", ""),
                "medical.emergency_contact_number": getattr(student, "emergency_contact_number", ""),
                "medical.medical_information": getattr(student, "medical_notes", ""),

                # System / Institution Information
                "system.institution_name": app_state.get_setting("name", "Institution"),
                "system.institution_address": app_state.get_setting("address", ""),
                "system.institution_phone": app_state.get_setting("phone", ""),
                "system.institution_logo": app_state.get_setting("institution_logo", ""),

                # Authoritative Flat Aliases (Prevents Missing Field Bugs in all Certificate & Form Generators)
                "student_name": full_name,
                "name": full_name,
                "full_name": full_name,
                "father_name": student.father_name or "",
                "father": student.father_name or "",
                "mother_name": getattr(student, "mother_name", "") or "",
                "guardian_name": student.guardian_name or "",
                "dob": student.dob or "",
                "b_form": student.b_form or "",
                "roll_no": str(student.id),
                "roll_number": str(student.id),
                "student_id": student.student_id or "",
                "admission_no": student.admission_number or "",
                "admission_number": student.admission_number or "",
                "class": cls_name,
                "section": sec_name,
                "photo": student.photo_path if student.photo_path and os.path.exists(student.photo_path) else "",
                "student_photo": student.photo_path if student.photo_path and os.path.exists(student.photo_path) else "",
                "photo_path": student.photo_path if student.photo_path and os.path.exists(student.photo_path) else "",
                "mobile_no": student.phone or student.father_phone or "",
                "address": student.current_address or "",
                "city": getattr(student, "city", "") or "",
                "district": getattr(student, "district", "") or "",
                "gender": student.gender or "",
                "blood_group": student.blood_group or "",
                "nationality": student.nationality or "",
                "religion": student.religion or "",
                "academic_session": student.academic_session or "",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "date_of_issue": datetime.now().strftime("%Y-%m-%d"),
            }
            return data
        finally:
            db.close()

    @staticmethod
    def get_fee_receipt_data(payment_id):
        from database.models.fee import FeePayment, FeeVoucher
        db = get_session()
        try:
            payment = db.query(FeePayment).options(
                joinedload(FeePayment.allocations),
                joinedload(FeePayment.voucher).joinedload(FeeVoucher.student),
                joinedload(FeePayment.voucher).joinedload(FeeVoucher.items)
            ).filter_by(id=payment_id).first()

            if not payment:
                return {}

            voucher = payment.voucher
            student = voucher.student
            data = DataResolverService.get_student_data(student.student_id)

            paid_val = float(payment.amount_paid or 0.0)

            # Category allocation maps from voucher items
            cat_orig_map = {}
            cat_disc_map = {}
            cat_rem_map = {}
            for item in voucher.effective_items:
                c = item.category or "Other Fee"
                cat_orig_map[c] = cat_orig_map.get(c, 0.0) + float(item.amount or 0.0)
                cat_disc_map[c] = cat_disc_map.get(c, 0.0) + float(item.discount or 0.0)
                cat_rem_map[c] = cat_rem_map.get(c, 0.0) + item.remaining_balance

            # Category allocation maps from payment records
            cat_paid_map = {}
            for alloc in payment.allocations:
                c = alloc.category or "Other Fee"
                cat_paid_map[c] = cat_paid_map.get(c, 0.0) + float(alloc.amount_allocated or 0.0)
                cat_disc_map[c] = max(cat_disc_map.get(c, 0.0), float(alloc.discount_allocated or 0.0))

            # If legacy payment without allocations, assume Tuition Fee
            if not cat_paid_map:
                cat_paid_map["Tuition Fee"] = paid_val

            # Authoritative calculations:
            # 1. Gross total before discount
            fine_val = float(payment.fine_included or 0.0)
            gross_total = sum(float(it.amount or 0.0) for it in voucher.effective_items) + fine_val
            if gross_total <= 0:
                gross_total = float(voucher.total_amount or 0.0)

            # 2. Total voucher discount
            voucher_total_discount = max(
                float(payment.discount_included or 0.0),
                sum(float(it.discount or 0.0) for it in voucher.effective_items)
            )

            # 3. Net current voucher payable
            current_net_fee = float(voucher.total_amount or 0.0)
            if current_net_fee <= 0 and gross_total > 0:
                current_net_fee = max(0.0, gross_total - voucher_total_discount)

            # 4. Previous dues across other student vouchers
            other_vouchers = db.query(FeeVoucher).filter(
                FeeVoucher.student_id == student.id,
                FeeVoucher.id != voucher.id
            ).all()
            prev_dues = sum(max(0.0, float(v.total_amount or 0.0) - float(v.paid_amount or 0.0)) for v in other_vouchers)

            # 5. Total payable before this payment
            tot_payable = prev_dues + current_net_fee

            # 6. Current voucher remaining balance post-payment
            voucher_rem = max(0.0, float(voucher.total_amount or 0.0) - float(voucher.paid_amount or 0.0))

            # 7. Total remaining balance across ALL student vouchers post-payment
            overall_rem = prev_dues + voucher_rem

            financial_fields = {
                "fee.receipt_number": payment.receipt_no,
                "fee.payment_date": payment.payment_date,
                "fee.fee_month": voucher.fee_month,
                "fee.monthly_fee": f"{voucher.base_amount:,.0f}",
                "fee.total_fee": f"{gross_total:,.0f}",
                "fee.total_discount": f"{voucher_total_discount:,.0f}",
                "fee.current_fee": f"{current_net_fee:,.0f}",
                "fee.previous_dues": f"{prev_dues:,.0f}",
                "fee.total_payable": f"{tot_payable:,.0f}",
                "fee.amount_received": f"{paid_val:,.0f}",
                "fee.remaining_balance": f"{voucher_rem:,.0f}",
                "fee.total_remaining_balance": f"{overall_rem:,.0f}",
                "fee.total_remaining_balance_copy1": f"{overall_rem:,.0f}",
                "fee.payment_method": payment.payment_method or "Cash",
                "fee.status": "Paid" if voucher_rem <= 0 else "Pending",

                # Category Breakdown Tags
                "fee.tuition_fee": f"{cat_orig_map.get('Tuition Fee', voucher.base_amount or 0.0):,.0f}",
                "fee.tuition_discount": f"{cat_disc_map.get('Tuition Fee', payment.discount_included or 0.0):,.0f}",
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

                "fee.fine": f"{fine_val:,.0f}",
            }

            # Itemized line tags (fee.item_1_category, fee.item_1_paid, etc.)
            alloc_list = payment.allocations or []
            for i, alloc in enumerate(alloc_list[:10], 1):
                financial_fields[f"fee.item_{i}_category"] = alloc.category
                financial_fields[f"fee.item_{i}_description"] = alloc.description or ""
                financial_fields[f"fee.item_{i}_paid"] = f"{(alloc.amount_allocated or 0.0):,.0f}"
                financial_fields[f"fee.item_{i}_discount"] = f"{(alloc.discount_allocated or 0.0):,.0f}"
                if alloc.voucher_item:
                    financial_fields[f"fee.item_{i}_amount"] = f"{(alloc.voucher_item.amount or 0.0):,.0f}"
                    financial_fields[f"fee.item_{i}_remaining"] = f"{alloc.voucher_item.remaining_balance:,.0f}"

            data.update(financial_fields)
            return data
        finally:
            db.close()

    @staticmethod
    def get_employee_data(employee_id_or_sys_id):
        """Authoritative live resolution for Staff and Faculty records across all HR certificates."""
        from database.models.hr import Employee
        db = get_session()
        try:
            emp = None
            if isinstance(employee_id_or_sys_id, int) or (isinstance(employee_id_or_sys_id, str) and str(employee_id_or_sys_id).isdigit()):
                emp = db.query(Employee).filter_by(id=int(employee_id_or_sys_id)).first()
            if not emp:
                emp = db.query(Employee).filter_by(emp_id=str(employee_id_or_sys_id).strip()).first()
            if not emp:
                return {}

            full_name = f"{emp.first_name} {emp.last_name or ''}".strip()
            basic = float(emp.basic_salary or 0.0)
            house = float(emp.house_allowance or 0.0)
            med = float(emp.medical_allowance or 0.0)
            trans = float(emp.transport_allowance or 0.0)
            oth = float(emp.other_allowance or 0.0)
            gross = basic + house + med + trans + oth
            tax = float(emp.tax_deduction or 0.0)
            net_sal = max(0.0, gross - tax)

            data = {
                # Namespaced
                "employee.name": full_name,
                "employee.emp_id": emp.emp_id or "",
                "employee.first_name": emp.first_name or "",
                "employee.last_name": emp.last_name or "",
                "employee.father_husband_name": emp.father_husband_name or "",
                "employee.cnic": emp.cnic or "",
                "employee.gender": emp.gender or "",
                "employee.dob": emp.dob or "",
                "employee.phone": emp.phone or "",
                "employee.email": emp.email or "",
                "employee.address": emp.address or "",
                "employee.city": emp.city or "",
                "employee.designation": emp.designation or "",
                "employee.department": emp.department or "",
                "employee.emp_type": emp.emp_type or "Teacher",
                "employee.status": emp.status or "Active",
                "employee.employment_type": emp.employment_type or "Permanent",
                "employee.joining_date": emp.joining_date or "",
                "employee.experience": emp.experience or "",
                "employee.basic_salary": f"{basic:,.2f}",
                "employee.house_allowance": f"{house:,.2f}",
                "employee.medical_allowance": f"{med:,.2f}",
                "employee.transport_allowance": f"{trans:,.2f}",
                "employee.other_allowance": f"{oth:,.2f}",
                "employee.gross_salary": f"{gross:,.2f}",
                "employee.tax_deduction": f"{tax:,.2f}",
                "employee.net_salary": f"{net_sal:,.2f}",
                "employee.bank_name": emp.bank_name or "",
                "employee.account_no": emp.account_no or "",
                "employee.photo": emp.photo_path if emp.photo_path and os.path.exists(emp.photo_path) else "",

                # Authoritative Flat Aliases
                "employee_name": full_name,
                "staff_name": full_name,
                "name": full_name,
                "emp_id": emp.emp_id or "",
                "employee_id": emp.emp_id or "",
                "father_husband_name": emp.father_husband_name or "",
                "father_name": emp.father_husband_name or "",
                "designation": emp.designation or "",
                "department": emp.department or "",
                "cnic": emp.cnic or "",
                "phone": emp.phone or "",
                "email": emp.email or "",
                "address": emp.address or "",
                "joining_date": emp.joining_date or "",
                "date_of_joining": emp.joining_date or "",
                "salary": f"{gross:,.2f}",
                "basic_salary": f"{basic:,.2f}",
                "gross_salary": f"{gross:,.2f}",
                "net_salary": f"{net_sal:,.2f}",
                "photo": emp.photo_path if emp.photo_path and os.path.exists(emp.photo_path) else "",
                "photo_path": emp.photo_path if emp.photo_path and os.path.exists(emp.photo_path) else "",
                "status": emp.status or "Active",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "date_of_issue": datetime.now().strftime("%Y-%m-%d"),
            }
            return data
        finally:
            db.close()

    @staticmethod
    def get_student_fee_structure_data(student_system_id, basis="Monthly"):
        """Compiles dynamic fee structural costs and live student ledger balance position."""
        from database.models.student import Student
        from database.models.fee import FeeVoucher
        from core.fee_service import FeeService

        data = DataResolverService.get_student_data(student_system_id)
        if not data:
            return {}

        db = get_session()
        try:
            student = db.query(Student).filter_by(student_id=student_system_id).first()
            if not student:
                return data

            basis_clean = str(basis).strip().title()
            if "6" in basis_clean or "Six" in basis_clean:
                basis_clean = "6-Month"
            elif "Ann" in basis_clean or "Year" in basis_clean:
                basis_clean = "Annual"
            else:
                basis_clean = "Monthly"

            m_fee = float(student.monthly_fee or 0.0)
            fee_6m = float(getattr(student, 'six_month_fee', 0.0) or 0.0)
            fee_ann = float(getattr(student, 'annual_fee', 0.0) or 0.0)

            if fee_6m <= 0 and m_fee > 0:
                fee_6m = m_fee * 6
            if fee_ann <= 0 and m_fee > 0:
                fee_ann = m_fee * 12

            pos = FeeService.get_student_category_position(student.id)
            total_pending = float(pos.get("total_pending", 0.0))
            category_dues = pos.get("category_dues", {})

            vouchers = db.query(FeeVoucher).filter_by(student_id=student.id).all()
            total_billed = sum(float(v.total_amount or 0.0) for v in vouchers)
            total_paid = sum(float(v.paid_amount or 0.0) for v in vouchers)
            total_discount = sum(
                sum(float(it.discount or 0.0) for it in v.effective_items) for v in vouchers
            )

            structural_items = []
            if basis_clean == "Monthly":
                structural_items.append({"title": "Monthly Tuition Fee", "amount": m_fee})
                trans_fee = float(category_dues.get("Transport Fee", 0.0))
                if trans_fee > 0:
                    structural_items.append({"title": "Monthly Transport / Transit Fee", "amount": trans_fee})
                total_structure_cost = m_fee + trans_fee
            elif basis_clean == "6-Month":
                structural_items.append({"title": "Bi-Annual / 6-Month Tuition Package", "amount": fee_6m})
                trans_6m = float(category_dues.get("Transport Fee", 0.0)) * 6
                if trans_6m > 0:
                    structural_items.append({"title": "6-Month Transport / Transit Fee", "amount": trans_6m})
                total_structure_cost = fee_6m + trans_6m
            else:  # Annual
                structural_items.append({"title": "Full Academic Year Tuition Package", "amount": fee_ann})
                adm_fee = float(category_dues.get("Admission Fee", 0.0))
                if adm_fee > 0:
                    structural_items.append({"title": "Annual Registration / Admission Fee", "amount": adm_fee})
                exam_fee = float(category_dues.get("Examination Fee", 0.0))
                if exam_fee > 0:
                    structural_items.append({"title": "Annual Examination & Evaluation Fee", "amount": exam_fee})
                trans_ann = float(category_dues.get("Transport Fee", 0.0)) * 12
                if trans_ann > 0:
                    structural_items.append({"title": "Annual Fleet & Transport Services", "amount": trans_ann})
                total_structure_cost = sum(x["amount"] for x in structural_items)

            is_cleared = (total_pending <= 0)
            status_badge = "PAID IN FULL" if is_cleared else "PENDING DUES"
            clearance_summary = "NO DUES OUTSTANDING — ALL ACCOUNTS AUDITED & CLEARED" if is_cleared else f"PROVISIONAL — OUTSTANDING DUES PENDING: Rs. {total_pending:,.0f}"

            fee_cert_data = {
                "fee_basis": basis_clean,
                "fee.basis": basis_clean,
                "fee.structure_cost": f"{total_structure_cost:,.0f}",
                "fee.total_structure_cost": f"{total_structure_cost:,.0f}",
                "fee.total_billed": f"{total_billed:,.0f}",
                "fee.total_paid": f"{total_paid:,.0f}",
                "fee.total_discount": f"{total_discount:,.0f}",
                "fee.total_pending": f"{total_pending:,.0f}",
                "fee.clearance_status": clearance_summary,
                "fee.status_badge": status_badge,
                "fee.is_cleared": is_cleared,
                "fee.structural_items": structural_items,
                "fee.category_dues": category_dues
            }
            data.update(fee_cert_data)
            return data
        finally:
            db.close()

    @staticmethod
    def get_student_attendance_cert_data(student_system_id):
        """Live synchronization of verified student attendance statistics."""
        from core.attendance_service import AttendanceService
        from database.models.student import Student
        data = DataResolverService.get_student_data(student_system_id)
        if not data:
            return {}

        db = get_session()
        try:
            student = db.query(Student).filter_by(student_id=student_system_id).first()
            if student:
                summary = AttendanceService.get_student_attendance_summary(student.id)
                present = summary.get("present", 0)
                late = summary.get("late", 0)
                absent = summary.get("absent", 0)
                leave = summary.get("leave", 0)
                total_days = present + late + absent + leave
                pct = summary.get("percentage", 100.0 if total_days == 0 else 0.0)

                data.update({
                    "attendance.total_working_days": str(total_days),
                    "attendance.days_present": str(present + late),
                    "attendance.days_absent": str(absent),
                    "attendance.days_leave": str(leave),
                    "attendance.percentage": f"{pct:.1f}%",
                    "attendance_percentage": f"{pct:.1f}%",
                    "total_working_days": str(total_days),
                    "days_present": str(present + late),
                })
            return data
        finally:
            db.close()