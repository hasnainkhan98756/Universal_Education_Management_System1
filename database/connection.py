import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.models.base import Base

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_data', 'database')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'school_management.db')

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_db():
    """Safely upgrades database schema. Backs up conflicting old tables instead of deleting them."""
    db = get_session()
    try:
        res = db.execute(text("PRAGMA table_info(students)")).fetchall()
        if res:
            existing_cols = [row[1] for row in res]
            new_cols = {
                "place_of_birth": "VARCHAR(100)", "father_cnic": "VARCHAR(50)",
                "mother_name": "VARCHAR(100)", "mother_cnic": "VARCHAR(50)",
                "guardian_cnic": "VARCHAR(50)", "guardian_relationship": "VARCHAR(50)",
                "family_income": "VARCHAR(50)", "city": "VARCHAR(100)",
                "district": "VARCHAR(100)", "emergency_contact_person": "VARCHAR(100)",
                "emergency_contact_number": "VARCHAR(50)", "emergency_relationship": "VARCHAR(50)",
                "admission_type": "VARCHAR(50)", "previous_class": "VARCHAR(50)",
                "previous_exam": "VARCHAR(50)", "previous_session": "VARCHAR(50)",
                "previous_result": "VARCHAR(50)", "tc_number": "VARCHAR(50)",
                "tc_date": "VARCHAR(50)", "medical_notes": "VARCHAR(500)",
                "allergies": "VARCHAR(500)", "sibling_info": "VARCHAR(500)",
                "six_month_fee": "FLOAT DEFAULT 0.0",
                "annual_fee": "FLOAT DEFAULT 0.0",
                "admission_fee": "FLOAT DEFAULT 0.0",
                "admission_fee_paid": "BOOLEAN DEFAULT 0",
                "billing_cycle": "VARCHAR(50) DEFAULT 'Monthly'"
            }
            for col, ctype in new_cols.items():
                if col not in existing_cols:
                    db.execute(text(f"ALTER TABLE students ADD COLUMN {col} {ctype}"))

        res_vouch = db.execute(text("PRAGMA table_info(fee_vouchers)")).fetchall()
        if res_vouch:
            existing_vouch_cols = [row[1] for row in res_vouch]
            vouch_new_cols = {
                "fee_type": "VARCHAR(50) DEFAULT 'Monthly'",
                "coverage_start_date": "VARCHAR(20)",
                "coverage_end_date": "VARCHAR(20)",
                "coverage_months": "TEXT"
            }
            for vcol, vtype in vouch_new_cols.items():
                if vcol not in existing_vouch_cols:
                    db.execute(text(f"ALTER TABLE fee_vouchers ADD COLUMN {vcol} {vtype}"))

        res_pdf = db.execute(text("PRAGMA table_info(pdf_template_mappings)")).fetchall()
        if res_pdf:
            existing_pdf_cols = [row[1] for row in res_pdf]
            if "field_name" in existing_pdf_cols:
                db.execute(text("ALTER TABLE pdf_template_mappings RENAME TO pdf_template_mappings_legacy"))
            elif "mapping_data" not in existing_pdf_cols:
                db.execute(text("ALTER TABLE pdf_template_mappings ADD COLUMN mapping_data TEXT DEFAULT '{}'"))
                
        res_doc = db.execute(text("PRAGMA table_info(document_history)")).fetchall()
        if res_doc:
            existing_doc_cols = [row[1] for row in res_doc]
            if "employee_id" not in existing_doc_cols:
                db.execute(text("ALTER TABLE document_history ADD COLUMN employee_id INTEGER REFERENCES employees(id)"))
            student_col = next((row for row in res_doc if row[1] == "student_id"), None)
            if student_col and student_col[3] == 1:
                db.execute(text("""
                    CREATE TABLE document_history_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id INTEGER,
                        employee_id INTEGER,
                        document_type VARCHAR(100) NOT NULL,
                        document_number VARCHAR(100) UNIQUE NOT NULL,
                        file_path VARCHAR(500) NOT NULL,
                        created_at VARCHAR(50)
                    );
                """))
                db.execute(text("""
                    INSERT INTO document_history_temp (id, student_id, employee_id, document_type, document_number, file_path, created_at)
                    SELECT id, student_id, employee_id, document_type, document_number, file_path, created_at FROM document_history;
                """))
                db.execute(text("DROP TABLE document_history;"))
                db.execute(text("ALTER TABLE document_history_temp RENAME TO document_history;"))

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Safe Migration Check Failed: {e}")
    finally:
        db.close()

def seed_pdf_mappings(db):
    """SAFE SEEDER - Only seeds if the document mapping is completely missing."""
    try:
        from database.models.pdf_templates import PDFTemplateMapping
        
        # =======================================================
        # 1. ADMISSION FORM
        # =======================================================
        admission_data = {"mappings": {
            "academic_session": {"type": "text", "page": 1, "x": 25, "y": 10.5, "width": 20, "height": 3, "size": 12, "is_percentage": True},
            "application_no": {"type": "text", "page": 1, "x": 80, "y": 10.5, "width": 15, "height": 3, "size": 12, "is_percentage": True},
            "date": {"type": "text", "page": 1, "x": 80, "y": 13, "width": 15, "height": 3, "size": 12, "is_percentage": True},
            "student_name": {"type": "text", "page": 1, "x": 30, "y": 18.5, "width": 40, "height": 3, "size": 11, "is_percentage": True},
            "dob": {"type": "text", "page": 1, "x": 30, "y": 21.5, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "b_form": {"type": "text", "page": 1, "x": 30, "y": 24.5, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "nationality": {"type": "text", "page": 1, "x": 30, "y": 27.5, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "blood_group": {"type": "text", "page": 1, "x": 30, "y": 30.5, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "gender": {"type": "text", "page": 1, "x": 65, "y": 21.5, "width": 10, "height": 3, "size": 11, "is_percentage": True},
            "religion": {"type": "text", "page": 1, "x": 65, "y": 24.5, "width": 15, "height": 3, "size": 11, "is_percentage": True},
            "place_of_birth": {"type": "text", "page": 1, "x": 65, "y": 27.5, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "student_photo": {"type": "image", "page": 1, "x": 78, "y": 18, "width": 14, "height": 16, "is_percentage": True},
            "father_name": {"type": "text", "page": 1, "x": 30, "y": 37, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "mother_name": {"type": "text", "page": 1, "x": 70, "y": 37, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "father_cnic": {"type": "text", "page": 1, "x": 30, "y": 40, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "mother_cnic": {"type": "text", "page": 1, "x": 70, "y": 40, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "guardian_name": {"type": "text", "page": 1, "x": 35, "y": 43, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "relationship": {"type": "text", "page": 1, "x": 70, "y": 43, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "occupation": {"type": "text", "page": 1, "x": 35, "y": 46, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "monthly_income": {"type": "text", "page": 1, "x": 70, "y": 46, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "address": {"type": "text", "page": 1, "x": 30, "y": 52, "width": 60, "height": 3, "size": 11, "is_percentage": True},
            "city": {"type": "text", "page": 1, "x": 20, "y": 55, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "district": {"type": "text", "page": 1, "x": 60, "y": 55, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "mobile_no": {"type": "text", "page": 1, "x": 35, "y": 58, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "alt_contact": {"type": "text", "page": 1, "x": 70, "y": 58, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "email": {"type": "text", "page": 1, "x": 20, "y": 61, "width": 40, "height": 3, "size": 11, "is_percentage": True},
            "apply_class": {"type": "text", "page": 1, "x": 30, "y": 68, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "apply_section": {"type": "text", "page": 1, "x": 70, "y": 68, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "admission_type": {"type": "text", "page": 1, "x": 30, "y": 71, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "prev_school": {"type": "text", "page": 1, "x": 35, "y": 74, "width": 55, "height": 3, "size": 11, "is_percentage": True},
            "prev_class": {"type": "text", "page": 1, "x": 30, "y": 77, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "prev_school_address": {"type": "text", "page": 1, "x": 65, "y": 77, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "prev_class_school": {"type": "text", "page": 1, "x": 40, "y": 86, "width": 20, "height": 3, "size": 10, "is_percentage": True},
            "prev_class_session": {"type": "text", "page": 1, "x": 65, "y": 86, "width": 15, "height": 3, "size": 10, "is_percentage": True},
            "prev_class_grade": {"type": "text", "page": 1, "x": 85, "y": 86, "width": 10, "height": 3, "size": 10, "is_percentage": True},
            "prev_exam_school": {"type": "text", "page": 1, "x": 40, "y": 89, "width": 20, "height": 3, "size": 10, "is_percentage": True},
            "prev_exam_session": {"type": "text", "page": 1, "x": 65, "y": 89, "width": 15, "height": 3, "size": 10, "is_percentage": True},
            "prev_exam_grade": {"type": "text", "page": 1, "x": 85, "y": 89, "width": 10, "height": 3, "size": 10, "is_percentage": True},
            "transfer_cert_no": {"type": "text", "page": 1, "x": 45, "y": 93, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "transfer_cert_date": {"type": "text", "page": 1, "x": 75, "y": 93, "width": 15, "height": 3, "size": 11, "is_percentage": True},
            "sibling_yes_no": {"type": "text", "page": 2, "x": 65, "y": 12, "width": 10, "height": 3, "size": 11, "is_percentage": True}, 
            "sibling_name": {"type": "text", "page": 2, "x": 20, "y": 15, "width": 30, "height": 3, "size": 11, "is_percentage": True},
            "sibling_class": {"type": "text", "page": 2, "x": 60, "y": 15, "width": 15, "height": 3, "size": 11, "is_percentage": True},
            "sibling_section": {"type": "text", "page": 2, "x": 85, "y": 15, "width": 10, "height": 3, "size": 11, "is_percentage": True},
            "emergency_person": {"type": "text", "page": 2, "x": 35, "y": 25, "width": 30, "height": 3, "size": 11, "is_percentage": True},
            "emergency_contact": {"type": "text", "page": 2, "x": 35, "y": 28, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "emergency_relationship": {"type": "text", "page": 2, "x": 75, "y": 28, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "medical_info": {"type": "text", "page": 2, "x": 45, "y": 31, "width": 45, "height": 3, "size": 11, "is_percentage": True},
            "declaration_parent_name": {"type": "text", "page": 2, "x": 35, "y": 55, "width": 40, "height": 3, "size": 11, "is_percentage": True},
            "declaration_date": {"type": "text", "page": 2, "x": 20, "y": 58, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "test_required": {"type": "text", "page": 2, "x": 35, "y": 70, "width": 10, "height": 3, "size": 11, "is_percentage": True},
            "test_date": {"type": "text", "page": 2, "x": 65, "y": 70, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "admission_status": {"type": "text", "page": 2, "x": 35, "y": 73, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "test_result": {"type": "text", "page": 2, "x": 70, "y": 73, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "allotted_class_section": {"type": "text", "page": 2, "x": 35, "y": 76, "width": 30, "height": 3, "size": 11, "is_percentage": True},
            "admission_fee": {"type": "text", "page": 2, "x": 30, "y": 79, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "admission_fee_status": {"type": "text", "page": 2, "x": 65, "y": 79, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "billing_cycle": {"type": "text", "page": 2, "x": 30, "y": 82, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "remarks": {"type": "text", "page": 2, "x": 60, "y": 82, "width": 35, "height": 3, "size": 11, "is_percentage": True},
            "roll_no": {"type": "text", "page": 2, "x": 25, "y": 85, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "receipt_no": {"type": "text", "page": 2, "x": 65, "y": 85, "width": 25, "height": 3, "size": 11, "is_percentage": True}
        }}

        # =======================================================
        # 2. FEE RECEIPT
        # =======================================================
        fee_data = {"mappings": {
            "student.name": {"type": "text", "page": 1, "x": 30, "y": 30, "width": 40, "height": 3, "size": 11, "is_percentage": True},
            "student.student_id": {"type": "text", "page": 1, "x": 30, "y": 35, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "academic.class": {"type": "text", "page": 1, "x": 70, "y": 35, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.fee_month": {"type": "text", "page": 1, "x": 70, "y": 30, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.receipt_number": {"type": "text", "page": 1, "x": 80, "y": 10, "width": 15, "height": 3, "size": 11, "is_percentage": True},
            "fee.previous_dues": {"type": "text", "page": 1, "x": 70, "y": 45, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.current_fee": {"type": "text", "page": 1, "x": 70, "y": 50, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.total_payable": {"type": "text", "page": 1, "x": 70, "y": 55, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.amount_received": {"type": "text", "page": 1, "x": 70, "y": 60, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.total_remaining_balance": {"type": "text", "page": 1, "x": 70, "y": 65, "width": 20, "height": 3, "size": 12, "is_percentage": True},
            "fee.payment_date": {"type": "text", "page": 1, "x": 25, "y": 65, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "fee.payment_method": {"type": "text", "page": 1, "x": 25, "y": 60, "width": 20, "height": 3, "size": 11, "is_percentage": True}
        }}

        # =======================================================
        # 3. SALARY SLIP (INCLUDES BONUS, OVERTIME, ADVANCE)
        # =======================================================
        salary_data = {"mappings": {
            "payroll.receipt_no": {"type": "text", "page": 1, "x": 75, "y": 10, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.month": {"type": "text", "page": 1, "x": 75, "y": 13, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.payment_date": {"type": "text", "page": 1, "x": 75, "y": 16, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "employee.name": {"type": "text", "page": 1, "x": 25, "y": 25, "width": 40, "height": 3, "size": 12, "is_percentage": True},
            "employee.emp_id": {"type": "text", "page": 1, "x": 25, "y": 28, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "employee.designation": {"type": "text", "page": 1, "x": 25, "y": 31, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "employee.department": {"type": "text", "page": 1, "x": 65, "y": 31, "width": 25, "height": 3, "size": 11, "is_percentage": True},
            "payroll.basic": {"type": "text", "page": 1, "x": 30, "y": 45, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.allowances": {"type": "text", "page": 1, "x": 30, "y": 48, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.bonus": {"type": "text", "page": 1, "x": 30, "y": 51, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.overtime": {"type": "text", "page": 1, "x": 30, "y": 54, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.gross": {"type": "text", "page": 1, "x": 30, "y": 59, "width": 20, "height": 3, "size": 12, "is_percentage": True},
            "payroll.tax": {"type": "text", "page": 1, "x": 75, "y": 45, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.advance": {"type": "text", "page": 1, "x": 75, "y": 48, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.deductions": {"type": "text", "page": 1, "x": 75, "y": 51, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "payroll.net_salary": {"type": "text", "page": 1, "x": 75, "y": 68, "width": 20, "height": 4, "size": 14, "is_percentage": True},
            "payroll.method": {"type": "text", "page": 1, "x": 25, "y": 68, "width": 20, "height": 3, "size": 11, "is_percentage": True}
        }}

        # =======================================================
        # 4. STUDENT ID CARD
        # =======================================================
        id_data = {"mappings": {
            "student_name": {"type": "text", "page": 1, "x": 35, "y": 60, "width": 40, "height": 4, "size": 12, "is_percentage": True},
            "father_name": {"type": "text", "page": 1, "x": 35, "y": 66, "width": 40, "height": 4, "size": 11, "is_percentage": True},
            "student_id": {"type": "text", "page": 1, "x": 35, "y": 72, "width": 30, "height": 4, "size": 11, "is_percentage": True},
            "dob": {"type": "text", "page": 1, "x": 35, "y": 78, "width": 30, "height": 4, "size": 11, "is_percentage": True},
            "blood_group": {"type": "text", "page": 1, "x": 35, "y": 84, "width": 30, "height": 4, "size": 11, "is_percentage": True},
            "phone": {"type": "text", "page": 1, "x": 35, "y": 90, "width": 40, "height": 4, "size": 11, "is_percentage": True},
            "document.valid_until": {"type": "text", "page": 1, "x": 50, "y": 95, "width": 30, "height": 4, "size": 10, "is_percentage": True},
            "student_photo": {"type": "image", "page": 1, "x": 35, "y": 20, "width": 30, "height": 35, "is_percentage": True}
        }}

        # =======================================================
        # 5. TRANSCRIPT
        # =======================================================
        transcript_data = {"mappings": {
            "document.certificate_number": {"type": "text", "page": 1, "x": 80, "y": 10, "width": 15, "height": 3, "size": 11, "is_percentage": True},
            "document.date_of_issue": {"type": "text", "page": 1, "x": 80, "y": 14, "width": 15, "height": 3, "size": 11, "is_percentage": True},
            "student_name": {"type": "text", "page": 1, "x": 30, "y": 30, "width": 50, "height": 3, "size": 12, "is_percentage": True},
            "father_name": {"type": "text", "page": 1, "x": 30, "y": 28, "width": 30, "height": 3, "size": 11, "is_percentage": True},
            "student_id": {"type": "text", "page": 1, "x": 30, "y": 40, "width": 30, "height": 3, "size": 12, "is_percentage": True},
            "dob": {"type": "text", "page": 1, "x": 30, "y": 32, "width": 30, "height": 3, "size": 11, "is_percentage": True},
            "admission_no": {"type": "text", "page": 1, "x": 75, "y": 32, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "session": {"type": "text", "page": 1, "x": 75, "y": 36, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "roll_no": {"type": "text", "page": 1, "x": 75, "y": 40, "width": 20, "height": 3, "size": 11, "is_percentage": True},
            "section": {"type": "text", "page": 1, "x": 75, "y": 44, "width": 20, "height": 3, "size": 11, "is_percentage": True}
        }}

        docs_map = {
            "Admission Form": admission_data,
            "Fee Receipt": fee_data,
            "Salary Slip": salary_data,
            "Student ID Card": id_data,
            "Transcript": transcript_data
        }

        # SAFE SEED LOGIC (Only runs if the document mapping doesn't exist at all)
        for doc_name, map_dict in docs_map.items():
            existing = db.query(PDFTemplateMapping).filter_by(document_type=doc_name).first()
            if not existing:
                new_map = PDFTemplateMapping(
                    document_type=doc_name,
                    template_path=f"templates/{doc_name.replace(' ', '_')}.pdf",
                    mapping_data=json.dumps(map_dict)
                )
                db.add(new_map)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Auto-Seeder Note: {e}")

def _seed_leave_types(db):
    """Seed 4 default leave types if the table is empty."""
    try:
        from database.models.leave import LeaveType
        if db.query(LeaveType).count() == 0:
            for lt in [
                LeaveType(name="Casual Leave",    max_days_per_year=10, is_paid=True),
                LeaveType(name="Sick Leave",       max_days_per_year=10, is_paid=True),
                LeaveType(name="Annual Leave",     max_days_per_year=15, is_paid=True),
                LeaveType(name="Emergency Leave",  max_days_per_year=5,  is_paid=False),
            ]:
                db.add(lt)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Leave type seeder: {e}")


def apply_performance_indexes(db):
    """Safely adds non-destructive indexes to eliminate full table scans on hot queries."""
    index_statements = [
        ("idx_students_class_status", "CREATE INDEX IF NOT EXISTS idx_students_class_status ON students(class_id, status)"),
        ("idx_attendance_date_session", "CREATE INDEX IF NOT EXISTS idx_attendance_date_session ON attendance_records(date, academic_session)"),
        ("idx_staff_attendance_date", "CREATE INDEX IF NOT EXISTS idx_staff_attendance_date ON staff_attendance(date)"),
        ("idx_fee_vouchers_student_status", "CREATE INDEX IF NOT EXISTS idx_fee_vouchers_student_status ON fee_vouchers(student_id, status)"),
        ("idx_fee_payments_voucher", "CREATE INDEX IF NOT EXISTS idx_fee_payments_voucher ON fee_payments(voucher_id)"),
        ("idx_fee_voucher_items_vid", "CREATE INDEX IF NOT EXISTS idx_fee_voucher_items_vid ON fee_voucher_items(voucher_id)"),
        ("idx_fee_payment_allocations_pid", "CREATE INDEX IF NOT EXISTS idx_fee_payment_allocations_pid ON fee_payment_allocations(payment_id)"),
        ("idx_expenses_session_date", "CREATE INDEX IF NOT EXISTS idx_expenses_session_date ON analytics_expenses(academic_session, expense_date)"),
        ("idx_calendar_events_dates", "CREATE INDEX IF NOT EXISTS idx_calendar_events_dates ON calendar_events(start_date, end_date)"),
        ("idx_inventory_items_sku", "CREATE INDEX IF NOT EXISTS idx_inventory_items_sku ON inventory_items(sku)"),
        ("idx_inventory_items_cat", "CREATE INDEX IF NOT EXISTS idx_inventory_items_cat ON inventory_items(category_id)"),
        ("idx_inventory_tx_item", "CREATE INDEX IF NOT EXISTS idx_inventory_tx_item ON inventory_transactions(item_id, transaction_date)"),
        ("idx_managed_docs_cat", "CREATE INDEX IF NOT EXISTS idx_managed_docs_cat ON managed_documents(file_category, entity_type, entity_id)"),
        ("idx_managed_docs_entity", "CREATE INDEX IF NOT EXISTS idx_managed_docs_entity ON managed_documents(entity_type, entity_id)"),
        ("idx_system_notifs_read", "CREATE INDEX IF NOT EXISTS idx_system_notifs_read ON system_notifications(is_dismissed, is_read)"),
        ("idx_students_b_form_uq", "CREATE UNIQUE INDEX IF NOT EXISTS idx_students_b_form_uq ON students(b_form) WHERE b_form IS NOT NULL AND b_form != ''"),
        ("idx_document_history_student", "CREATE INDEX IF NOT EXISTS idx_document_history_student ON document_history(student_id)"),
        ("idx_document_history_employee", "CREATE INDEX IF NOT EXISTS idx_document_history_employee ON document_history(employee_id)"),
        ("idx_fee_vouchers_student_id", "CREATE INDEX IF NOT EXISTS idx_fee_vouchers_student_id ON fee_vouchers(student_id)"),
        ("idx_timetable_entries_class_sec", "CREATE INDEX IF NOT EXISTS idx_timetable_entries_class_sec ON timetable_entries(class_id, section_id, academic_session)"),
    ]
    try:
        for idx_name, sql in index_statements:
            db.execute(text(sql))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Index migration note: {e}")


def init_db():
    # Import new models so Base.metadata knows about their tables
    import database.models.fee           # noqa: F401  — registers FeeVoucher, FeePayment, FeeVoucherItem, FeePaymentAllocation
    import database.models.library       # noqa: F401  — registers Book, BookIssue
    import database.models.transport     # noqa: F401  — registers TransportRoute, Vehicle, StudentTransport
    import database.models.leave         # noqa: F401  — registers LeaveType, LeaveApplication
    import database.models.inventory     # noqa: F401  — registers InventoryCategory, InventorySupplier, InventoryItem, etc.
    import database.models.documents     # noqa: F401  — registers DocumentHistory, ManagedDocument
    import database.models.notifications # noqa: F401  — registers SystemNotification
    import database.models.examination   # noqa: F401  — registers ExamResult
    import database.models.hr            # noqa: F401  — registers Employee, StaffAttendance, PayrollRecord, etc.
    import database.models.timetable     # noqa: F401  — registers Room, TimetablePeriod, TimetableEntry
    import database.models.calendar      # noqa: F401  — registers CalendarEvent
    import database.models.analytics     # noqa: F401  — registers ExpenseRecord
    import database.models.communication # noqa: F401  — registers CommunicationProvider, MessageTemplate, MessageLog

    migrate_db()
    Base.metadata.create_all(bind=engine)   # Creates ALL tables including new ones

    db = get_session()
    try:
        seed_pdf_mappings(db)
        _seed_leave_types(db)
        apply_performance_indexes(db)
    finally:
        db.close()


def get_session():
    return SessionLocal()