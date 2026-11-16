import os
import shutil
import re
from database.connection import get_session
from database.models.student import Student
from core.state_manager import app_state
from core.document_service import DocumentService 
from sqlalchemy.orm import joinedload

def normalize_cnic(val: str) -> str:
    """
    Normalizes a Pakistani CNIC / B-Form / CRC string into canonical format: XXXXX-XXXXXXX-X.
    If 13 digits are provided (with or without dashes/spaces/dots), returns standard 15-char format.
    If empty or None, returns None.
    If non-empty but not 13 digits, returns stripped string.
    """
    if not val:
        return None
    val_str = str(val).strip()
    digits = re.sub(r'[^0-9]', '', val_str)
    if len(digits) == 13:
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return val_str if val_str else None

class StudentService:
    normalize_cnic = staticmethod(normalize_cnic)

    @staticmethod
    def generate_student_id():
        return DocumentService.generate_number("Student ID")

    @staticmethod
    def save_photo(source_path, student_id):
        if not source_path or not os.path.exists(source_path):
            return None
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            photos_dir = os.path.join(base_dir, 'user_data', 'student_photos')
            os.makedirs(photos_dir, exist_ok=True)
            
            ext = os.path.splitext(source_path)[1]
            dest_path = os.path.join(photos_dir, f"{student_id}{ext}")
            shutil.copy2(source_path, dest_path)
            return dest_path
        except Exception as e:
            return None

    @staticmethod
    def admit_student(data_dict, photo_source_path=None):
        db = get_session()
        try:
            # 1. Normalize and strictly validate CNIC / B-Form uniqueness
            raw_bform = data_dict.get('b_form') or data_dict.get('cnic')
            normalized_bform = normalize_cnic(raw_bform)
            if normalized_bform:
                existing = db.query(Student).filter(Student.b_form == normalized_bform).first()
                if existing:
                    ex_name = f"{existing.first_name} {existing.last_name or ''}".strip()
                    return False, f"CNIC / B-Form '{normalized_bform}' is already registered to student '{ex_name}' (Student ID: {existing.student_id}).", None

            active_session = app_state.get_setting("session", "Default")
            new_id = data_dict.get('student_id') or StudentService.generate_student_id()
            adm_no = data_dict.get('admission_number') or DocumentService.generate_number("Admission Form")
            saved_photo_path = StudentService.save_photo(photo_source_path, new_id)

            student = Student(
                student_id=new_id,
                admission_number=adm_no,
                academic_session=active_session,
                first_name=data_dict.get('first_name'),
                last_name=data_dict.get('last_name'),
                gender=data_dict.get('gender'),
                dob=data_dict.get('dob'),
                blood_group=data_dict.get('blood_group'),
                nationality=data_dict.get('nationality'),
                religion=data_dict.get('religion'),
                place_of_birth=data_dict.get('place_of_birth'),
                b_form=normalized_bform,
                photo_path=saved_photo_path,
                
                phone=data_dict.get('phone'),
                email=data_dict.get('email'),
                current_address=data_dict.get('address'),
                city=data_dict.get('city'),
                district=data_dict.get('district'),
                
                father_name=data_dict.get('father_name'),
                father_cnic=data_dict.get('father_cnic'),
                father_phone=data_dict.get('father_phone'),
                father_occupation=data_dict.get('father_occ'),
                mother_name=data_dict.get('mother_name'),
                mother_cnic=data_dict.get('mother_cnic'),
                guardian_name=data_dict.get('guardian_name'),
                guardian_cnic=data_dict.get('guardian_cnic'),
                guardian_relationship=data_dict.get('guardian_relationship'),
                family_income=data_dict.get('family_income'),
                
                emergency_contact_person=data_dict.get('emergency_contact_person'),
                emergency_contact_number=data_dict.get('emergency_contact_number'),
                emergency_relationship=data_dict.get('emergency_relationship'),
                medical_notes=data_dict.get('medical_notes'),
                allergies=data_dict.get('allergies'),
                
                previous_school=data_dict.get('previous_school'),
                previous_class=data_dict.get('previous_class'),
                previous_exam=data_dict.get('previous_exam'),
                previous_session=data_dict.get('previous_session'),
                previous_result=data_dict.get('previous_result'),
                tc_number=data_dict.get('tc_number'),
                tc_date=data_dict.get('tc_date'),
                
                class_id=data_dict.get('class_id'),
                section_id=data_dict.get('section_id'),
                admission_date=data_dict.get('admission_date'),
                admission_type=data_dict.get('admission_type'),
                monthly_fee=float(data_dict.get('monthly_fee', 0.0) or 0.0),
                six_month_fee=float(data_dict.get('six_month_fee', 0.0) or 0.0),
                annual_fee=float(data_dict.get('annual_fee', 0.0) or 0.0),
                admission_fee=float(data_dict.get('admission_fee', 0.0) or 0.0),
                admission_fee_paid=bool(data_dict.get('admission_fee_paid', False)),
                billing_cycle=str(data_dict.get('billing_cycle') or "Monthly"),
                discount=float(data_dict.get('discount', 0.0) or 0.0),
                sibling_info=data_dict.get('sibling_info'),
                status="Active"
            )
            db.add(student)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed: {e}")
            return True, "Student admitted successfully!", student.student_id
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {str(e)}", None
        finally:
            db.close()

    @staticmethod
    def get_students(search_text=None, class_id=None, status_filter=None, session_filter=None, limit=None, offset=None):
        db = get_session()
        try:
            query = db.query(Student).options(joinedload(Student.academic_class), joinedload(Student.academic_section))
            if session_filter and session_filter not in ["All", "All Batches", "All Sessions"]:
                query = query.filter(Student.academic_session == session_filter)
            if status_filter and status_filter not in ["All", "All Status", "All Students"]:
                if status_filter in ["Migrated", "Transferred", "Migrated / Transferred"]:
                    query = query.filter(Student.status.in_(["Migrated", "Transferred"]))
                elif status_filter in ["Dropout", "Dropouts"]:
                    query = query.filter(Student.status.in_(["Dropout", "Dropouts"]))
                elif status_filter in ["Suspended", "Dropouts & Suspended"]:
                    query = query.filter(Student.status.in_(["Suspended", "Dropout", "Dropouts"]))
                elif status_filter in ["Active", "Active Enrolled"]:
                    query = query.filter(Student.status == "Active")
                elif status_filter in ["Graduated", "Graduated Alumni"]:
                    query = query.filter(Student.status == "Graduated")
                else:
                    query = query.filter(Student.status == status_filter)
            if class_id and class_id not in ["All", "All Classes"]:
                query = query.filter(Student.class_id == class_id)
            if search_text:
                search = f"%{search_text}%"
                query = query.filter(
                    (Student.first_name.ilike(search)) | 
                    (Student.last_name.ilike(search)) |
                    (Student.student_id.ilike(search)) |
                    (Student.admission_number.ilike(search)) |
                    (Student.father_name.ilike(search))
                )
            query = query.order_by(Student.id.desc())
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return query.all()
        finally:
            db.close()

    @staticmethod
    def get_student_batches():
        """Returns all distinct academic batches/sessions found in student records."""
        db = get_session()
        try:
            results = db.query(Student.academic_session).distinct().all()
            sessions = [r[0] for r in results if r[0]]
            return sorted(sessions, reverse=True)
        finally:
            db.close()

    @staticmethod
    def update_student_status(student_id_or_sys_id, new_status, reason=""):
        """Updates student status (Active, Graduated, Migrated, Suspended, Dropout, Inactive) with live notification."""
        db = get_session()
        try:
            stu = db.query(Student).filter(
                (Student.student_id == str(student_id_or_sys_id)) | (Student.id == student_id_or_sys_id)
            ).first()
            if not stu:
                return False, "Student not found."
            stu.status = new_status

            # If student is no longer active, purge any attendance logged for today so they instantly disappear
            if new_status != "Active":
                try:
                    from datetime import datetime
                    from database.models.attendance import AttendanceRecord
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    today_date = datetime.now().date()
                    db.query(AttendanceRecord).filter(
                        AttendanceRecord.student_id == stu.id,
                        (AttendanceRecord.date == today_str) | (AttendanceRecord.date == today_date)
                    ).delete(synchronize_session=False)
                except Exception as purge_err:
                    print(f"Warning: Could not purge same-day attendance for student {stu.id}: {purge_err}")

            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as ex:
                print(f"Error broadcasting status change: {ex}")
            return True, f"Student status successfully updated to {new_status}."
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def update_student(student_id_or_sys_id, data_dict, photo_source_path=None):
        """Updates an existing student profile with strict CNIC uniqueness check excluding self."""
        db = get_session()
        try:
            stu = db.query(Student).filter(
                (Student.id == student_id_or_sys_id) | (Student.student_id == str(student_id_or_sys_id))
            ).first()
            if not stu:
                return False, f"Student '{student_id_or_sys_id}' not found."

            raw_bform = data_dict.get('b_form') or data_dict.get('cnic')
            if raw_bform is not None:
                norm_bform = normalize_cnic(raw_bform)
                if norm_bform:
                    # Check if another student already has this CNIC
                    duplicate = db.query(Student).filter(
                        Student.b_form == norm_bform,
                        Student.id != stu.id
                    ).first()
                    if duplicate:
                        dup_name = f"{duplicate.first_name} {duplicate.last_name or ''}".strip()
                        return False, f"CNIC / B-Form '{norm_bform}' is already registered to another student '{dup_name}' (Student ID: {duplicate.student_id})."
                data_dict['b_form'] = norm_bform

            for field, val in data_dict.items():
                if hasattr(stu, field) and field not in ['id', 'student_id', 'created_at']:
                    setattr(stu, field, val)

            if photo_source_path and os.path.exists(photo_source_path):
                saved_photo = StudentService.save_photo(photo_source_path, stu.student_id)
                if saved_photo:
                    stu.photo_path = saved_photo

            db.commit()
            app_state.notify_data_changed()
            return True, "Student record successfully updated."
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def get_student_statistics(session_filter=None):
        """Returns statistics breakdown by student lifecycle status."""
        db = get_session()
        try:
            q = db.query(Student)
            if session_filter and session_filter not in ["All", "All Batches", "All Sessions"]:
                q = q.filter(Student.academic_session == session_filter)
            all_students = q.all()
            total = len(all_students)
            active = sum(1 for s in all_students if s.status == "Active")
            graduated = sum(1 for s in all_students if s.status == "Graduated")
            migrated = sum(1 for s in all_students if s.status in ["Migrated", "Transferred"])
            suspended = sum(1 for s in all_students if s.status == "Suspended")
            dropout = sum(1 for s in all_students if s.status in ["Dropout", "Dropouts"])
            inactive = sum(1 for s in all_students if s.status in ["Inactive", "Withdrawn"])
            return {
                "total": total,
                "active": active,
                "graduated": graduated,
                "migrated": migrated,
                "suspended": suspended,
                "dropout": dropout,
                "inactive": inactive
            }
        finally:
            db.close()

    @staticmethod
    def count_active_students():
        db = get_session()
        try:
            return db.query(Student).filter_by(status="Active").count()
        finally:
            db.close()

    @staticmethod
    def get_student_count():
        return StudentService.count_active_students()

    @staticmethod
    def get_student_by_system_id(sys_id):
        db = get_session()
        try:
            return db.query(Student).options(joinedload(Student.academic_class), joinedload(Student.academic_section)).filter_by(student_id=sys_id).first()
        finally:
            db.close()