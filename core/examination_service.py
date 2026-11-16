import os
from datetime import datetime
from database.connection import get_session
from database.models.student import Student
from database.models.examination import ExamResult
from core.state_manager import app_state

class ExaminationService:
    @staticmethod
    def calculate_grade(obtained, total):
        if total <= 0: return "N/A"
        pct = (obtained / total) * 100
        if pct >= 80: return "A+"
        elif pct >= 70: return "A"
        elif pct >= 60: return "B"
        elif pct >= 50: return "C"
        elif pct >= 40: return "D"
        else: return "F"

    @staticmethod
    def get_mark_sheet(class_id, section_id, exam_title, subject):
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "Default")
            students = db.query(Student).filter_by(class_id=class_id, section_id=section_id, status="Active").order_by(Student.first_name).all()
            existing_records = db.query(ExamResult).filter_by(class_id=class_id, section_id=section_id, exam_title=exam_title, subject=subject, academic_session=active_session).all()
            record_map = {rec.student_id: rec for rec in existing_records}
            
            sheet_data = []
            for stu in students:
                rec = record_map.get(stu.id)
                sheet_data.append({
                    "student_id": stu.id, "student_system_id": stu.student_id,
                    "name": f"{stu.first_name} {stu.last_name or ''}".strip(),
                    "total_marks": rec.total_marks if rec else 100.0,
                    "obtained_marks": rec.obtained_marks if rec else 0.0,
                    "grade": rec.grade if rec else "-", "remarks": rec.remarks if rec else "",
                    "is_existing": True if rec else False
                })
            return sheet_data
        finally: db.close()

    @staticmethod
    def save_marks(class_id, section_id, exam_title, subject, marks_data):
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "Default")
            for data in marks_data:
                s_id = int(data['student_id'])
                record = db.query(ExamResult).filter_by(student_id=s_id, exam_title=exam_title, subject=subject, academic_session=active_session).first()
                total = float(data['total_marks']); obtained = float(data['obtained_marks'])
                grade = ExaminationService.calculate_grade(obtained, total)
                
                if record:
                    record.total_marks = total; record.obtained_marks = obtained; record.grade = grade; record.remarks = data['remarks']
                else:
                    db.add(ExamResult(student_id=s_id, class_id=class_id, section_id=section_id, academic_session=active_session, exam_title=exam_title, subject=subject, total_marks=total, obtained_marks=obtained, grade=grade, remarks=data['remarks']))
            db.commit()
            
            try:
                from core.backup_service import BackupService
                BackupService.trigger_auto_backup(f"Marks Saved for {subject}")
            except Exception: pass
            
            return True, "Marks saved and updated successfully!"
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {e}"
        finally: db.close()

    @staticmethod
    def get_class_transcript_data(class_id, section_id, exam_title):
        """Aggregates ALL subjects for the Transcript PDF Mapping and Excel Export."""
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "Default")
            students = db.query(Student).filter_by(class_id=class_id, section_id=section_id, status="Active").order_by(Student.first_name).all()
            records = db.query(ExamResult).filter_by(class_id=class_id, section_id=section_id, exam_title=exam_title, academic_session=active_session).all()
            
            # Identify all subjects dynamically
            subjects = sorted(list(set([r.subject for r in records])))
            
            transcripts = []
            today_date = datetime.now().strftime("%Y-%m-%d")
            
            for stu in students:
                stu_records = [r for r in records if r.student_id == stu.id]
                if not stu_records: continue # Skip if no marks entered at all
                
                grand_total = sum([r.total_marks for r in stu_records])
                obtained = sum([r.obtained_marks for r in stu_records])
                pct = (obtained / grand_total * 100) if grand_total > 0 else 0
                grade = ExaminationService.calculate_grade(obtained, grand_total)
                
                c_name = stu.academic_class.name if getattr(stu, 'academic_class', None) else "-"
                s_name = stu.academic_section.name if getattr(stu, 'academic_section', None) else "-"
                
                data_dict = {
                    # ---------------------------------------------------------
                    # FLAT KEYS (For basic Visual Mapper variables)
                    # ---------------------------------------------------------
                    "student_name": f"{stu.first_name} {stu.last_name or ''}".strip(),
                    "father_name": stu.father_name or "-",
                    "dob": stu.dob or "-",
                    "admission_no": stu.admission_number or "-",
                    "roll_no": stu.admission_number or "-",
                    "class": c_name,
                    "section": s_name,
                    "session": active_session,
                    "student_id": stu.student_id,
                    "issue_date": today_date,
                    "exam_title": exam_title,
                    
                    # ---------------------------------------------------------
                    # DOT NOTATION KEYS (For advanced mapping structure)
                    # ---------------------------------------------------------
                    "student.student_id": stu.student_id,
                    "student.name": f"{stu.first_name} {stu.last_name or ''}".strip(),
                    "student.father_name": stu.father_name or "-",
                    "student.dob": stu.dob or "-",
                    "student.admission_number": stu.admission_number or "-",
                    "student.roll_number": stu.admission_number or "-", 
                    "academic.class": c_name,
                    "academic.section": s_name,
                    "academic.session": active_session,
                    "document.date_of_issue": today_date,
                    
                    "examination.title": exam_title,
                    "result.grand_total": grand_total,
                    "result.total_obtained": obtained,
                    "result.percentage": round(pct, 2),
                    "result.overall_grade": grade,
                    "raw_subjects": [] # Pure dict for Excel Loop
                }
                
                # Dynamically map Subject 1, Subject 2, etc. for the PDF Mapper
                for i, sub in enumerate(subjects):
                    sub_rec = next((r for r in stu_records if r.subject == sub), None)
                    data_dict[f"subject_{i+1}.name"] = sub
                    data_dict[f"subject_{i+1}.total"] = sub_rec.total_marks if sub_rec else "-"
                    data_dict[f"subject_{i+1}.obtained"] = sub_rec.obtained_marks if sub_rec else "-"
                    data_dict[f"subject_{i+1}.grade"] = sub_rec.grade if sub_rec else "-"
                    
                    data_dict["raw_subjects"].append({
                        "name": sub, "total": sub_rec.total_marks if sub_rec else 0,
                        "obtained": sub_rec.obtained_marks if sub_rec else 0,
                        "grade": sub_rec.grade if sub_rec else "-"
                    })
                transcripts.append((stu.id, data_dict))
                
            return subjects, transcripts
        finally: db.close()