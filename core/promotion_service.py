from database.connection import get_session
from database.models.student import Student
from database.models.academic import AcademicClass, AcademicSection
from core.state_manager import app_state


class PromotionService:

    @staticmethod
    def get_students_for_promotion(class_id: int, section_id: int):
        """Returns list of students with their latest exam result summary."""
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "")
            students = db.query(Student).filter_by(
                class_id=class_id, section_id=section_id, status="Active"
            ).order_by(Student.first_name).all()

            try:
                from database.models.examination import ExamResult
                records = db.query(ExamResult).filter_by(
                    class_id=class_id, section_id=section_id,
                    academic_session=active_session
                ).all()
            except Exception:
                records = []

            student_data = []
            for stu in students:
                stu_recs = [r for r in records if r.student_id == stu.id]
                if stu_recs:
                    total   = sum(r.total_marks for r in stu_recs)
                    obtained = sum(r.obtained_marks for r in stu_recs)
                    pct     = round((obtained / total * 100), 1) if total > 0 else 0
                else:
                    pct = None  # No marks entered

                student_data.append({
                    "id":         stu.id,
                    "student_id": stu.student_id,
                    "name":       f"{stu.first_name} {stu.last_name or ''}".strip(),
                    "percentage": pct,
                    "current_class_id":   class_id,
                    "current_section_id": section_id,
                })
            return student_data
        finally:
            db.close()

    @staticmethod
    def promote_students(student_ids: list, target_class_id: int,
                         target_section_id: int, new_session: str):
        """Promote selected students to new class/section/session."""
        if not student_ids:
            return False, "No students selected."
        db = get_session()
        try:
            # Fetch target class/section ONCE outside the loop (fix N+1 query)
            target_cls = db.query(AcademicClass).filter_by(id=target_class_id).first()
            target_sec = db.query(AcademicSection).filter_by(id=target_section_id).first()
            if not target_cls:
                return False, "Target class not found."

            count = 0
            for stu_id in student_ids:
                stu = db.query(Student).filter_by(id=stu_id).first()
                if stu:
                    # Update FK columns only — the ORM relationships update automatically
                    stu.class_id = target_class_id
                    stu.section_id = target_section_id if target_sec else None
                    stu.academic_session = new_session
                    # academic_class and academic_section are relationship properties —
                    # DO NOT assign strings to them. FK update handles everything.
                    count += 1
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after promotion: {e}")
            cls_name = target_cls.name
            sec_name = target_sec.name if target_sec else ""
            dest = f"{cls_name}{' — ' + sec_name if sec_name else ''}"
            return True, f"{count} student(s) promoted to {dest} successfully."
        except Exception as e:
            db.rollback()
            return False, f"Promotion failed: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def get_all_classes_with_sections():
        """Returns list of (class_obj, [section_obj,...]) tuples."""
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "")
            classes = []
            if active_session and active_session not in ["Default", "All"]:
                classes = db.query(AcademicClass).filter_by(
                    academic_session=active_session
                ).order_by(AcademicClass.name).all()
            if not classes:
                classes = db.query(AcademicClass).order_by(AcademicClass.name).all()
            result = []
            for cls in classes:
                secs = db.query(AcademicSection).filter_by(class_id=cls.id).order_by(AcademicSection.name).all()
                result.append((cls, secs))
            return result
        finally:
            db.close()
