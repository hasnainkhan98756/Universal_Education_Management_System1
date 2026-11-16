import os
from sqlalchemy.orm import joinedload
from sqlalchemy import text
from database.connection import get_session
from database.models.academic import AcademicClass, AcademicSection, AcademicSubject
from core.state_manager import app_state

class AcademicService:
    
    # ==========================================
    # OVERVIEW METRICS
    # ==========================================
    @staticmethod
    def get_dashboard_metrics():
        db = get_session()
        try:
            total_classes = db.query(AcademicClass).count()
            total_sections = db.query(AcademicSection.name).distinct().count()
            total_subjects = db.query(AcademicSubject).count()
            return {"classes": total_classes, "sections": total_sections, "subjects": total_subjects}
        finally: db.close()

    # ==========================================
    # CLASSES MANAGEMENT 
    # ==========================================
    @staticmethod
    def get_classes(session_filter=None):
        db = get_session()
        try:
            return db.query(AcademicClass).order_by(AcademicClass.id).all()
        finally: db.close()

    @staticmethod
    def get_classes_with_stats(session_filter=None):
        """Fetches classes and supports manual student quantity override without DB schema errors."""
        db = get_session()
        try:
            classes = db.query(AcademicClass).order_by(AcademicClass.id).all()
            result = []
            for c in classes:
                try:
                    # Live count fallback from students table
                    live_count = db.execute(text("SELECT count(*) FROM students WHERE class_id = :cid AND status = 'Active'"), {"cid": c.id}).scalar()
                except Exception:
                    live_count = 0
                
                # Use manual quantity from 'notes' column if available, else show live count
                manual_qty = c.notes if c.notes and str(c.notes).isdigit() else None
                final_count = int(manual_qty) if manual_qty is not None else (live_count or 0)
                
                result.append({
                    "id": c.id,
                    "name": c.name,
                    "student_count": final_count
                })
            return result
        finally: db.close()

    @staticmethod
    def add_class(name):
        db = get_session()
        try:
            session_name = app_state.get_setting("session", "Default")
            new_class = AcademicClass(name=name, academic_session=session_name)
            db.add(new_class)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after adding class: {e}")
            return True, "Class added successfully."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally: db.close()

    @staticmethod
    def update_class_quantity(class_id, quantity):
        """UPDATED: Modifies student quantity instead of name, saved safely in notes column."""
        db = get_session()
        try:
            cls = db.query(AcademicClass).filter_by(id=class_id).first()
            if not cls:
                return False, "Class not found."
            
            # Using 'notes' to safely store capacity without breaking the existing DB schema
            cls.notes = str(quantity)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after updating class capacity: {e}")
            return True, "Student quantity updated successfully."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally: db.close()

    @staticmethod
    def delete_class(class_id):
        db = get_session()
        try:
            db.query(AcademicClass).filter_by(id=class_id).delete()
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after deleting class: {e}")
            return True, "Class deleted successfully."
        except Exception as e:
            db.rollback()
            return False, "Cannot delete class. It is linked to existing students or sections."
        finally: db.close()

    # ==========================================
    # SECTIONS MANAGEMENT
    # ==========================================
    @staticmethod
    def get_sections(class_id=None, session_filter=None):
        db = get_session()
        try:
            q = db.query(AcademicSection)
            if class_id:
                q = q.filter(AcademicSection.class_id == class_id)
            return q.all()
        finally: db.close()

    @staticmethod
    def get_grouped_sections(session_filter=None):
        db = get_session()
        try:
            from database.models.student import Student
            sections = db.query(AcademicSection).options(joinedload(AcademicSection.academic_class)).all()
            groups = {}
            for sec in sections:
                if sec.name not in groups:
                    groups[sec.name] = {
                        "name": sec.name,
                        "capacity": sec.capacity or 40,
                        "classes": [],
                        "class_ids": [],
                        "section_ids": []
                    }
                groups[sec.name]["section_ids"].append(sec.id)
                if sec.academic_class:
                    groups[sec.name]["classes"].append(sec.academic_class.name)
                    groups[sec.name]["class_ids"].append(sec.academic_class.id)
            
            result = []
            for k, v in groups.items():
                v["class_string"] = ", ".join(sorted(v["classes"])) if v["classes"] else "None"
                # Query real active students enrolled in this section
                enrolled_count = 0
                if v["section_ids"]:
                    enrolled_count = db.query(Student).filter(
                        Student.section_id.in_(v["section_ids"]),
                        Student.status == "Active"
                    ).count()
                v["enrolled_count"] = enrolled_count
                result.append(v)
            return sorted(result, key=lambda x: x["name"])
        finally: db.close()

    @staticmethod
    def get_section_students(section_name):
        """Fetches full details of active students enrolled in a named section."""
        db = get_session()
        try:
            from database.models.student import Student
            sections = db.query(AcademicSection).filter_by(name=section_name).all()
            sec_ids = [s.id for s in sections]
            if not sec_ids:
                return []
            
            students = db.query(Student).options(
                joinedload(Student.academic_class),
                joinedload(Student.academic_section)
            ).filter(
                Student.section_id.in_(sec_ids),
                Student.status == "Active"
            ).order_by(Student.first_name).all()

            data = []
            for s in students:
                c_name = s.academic_class.name if s.academic_class else "-"
                sec_name = s.academic_section.name if s.academic_section else section_name
                data.append({
                    "id": s.id,
                    "student_id": s.student_id,
                    "name": f"{s.first_name} {s.last_name or ''}".strip(),
                    "father_name": s.father_name or "-",
                    "class_name": c_name,
                    "section_name": sec_name,
                    "phone": s.phone or s.father_phone or "-",
                    "b_form": s.b_form or "-",
                    "status": s.status
                })
            return data
        finally:
            db.close()

    @staticmethod
    def update_section_capacity(name, capacity):
        """Directly updates the capacity for all sections sharing this name."""
        db = get_session()
        try:
            sections = db.query(AcademicSection).filter_by(name=name).all()
            if not sections:
                return False, f"Section '{name}' not found."
            for sec in sections:
                sec.capacity = int(capacity)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after updating capacity: {e}")
            return True, f"Capacity for Section '{name}' updated to {capacity} students."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def add_grouped_section(name, class_ids_list, capacity):
        db = get_session()
        try:
            added_count = 0
            for cid in class_ids_list:
                existing = db.query(AcademicSection).filter_by(name=name, class_id=cid).first()
                if not existing:
                    new_sec = AcademicSection(name=name, class_id=cid, capacity=capacity)
                    db.add(new_sec)
                    added_count += 1
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after adding section: {e}")
            return True, f"Section '{name}' successfully assigned to {added_count} class(es)."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally: db.close()

    @staticmethod
    def update_grouped_section(old_name, new_name, new_class_ids_list, capacity):
        db = get_session()
        try:
            existing_sections = db.query(AcademicSection).filter_by(name=old_name).all()
            existing_class_ids = [sec.class_id for sec in existing_sections]

            for sec in existing_sections:
                sec.name = new_name
                sec.capacity = capacity

            classes_to_add = set(new_class_ids_list) - set(existing_class_ids)
            for cid in classes_to_add:
                new_sec = AcademicSection(name=new_name, class_id=cid, capacity=capacity)
                db.add(new_sec)

            classes_to_remove = set(existing_class_ids) - set(new_class_ids_list)
            for cid in classes_to_remove:
                db.query(AcademicSection).filter_by(name=old_name, class_id=cid).delete()

            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after updating section: {e}")
            return True, "Section updated successfully."
        except Exception as e:
            db.rollback()
            return False, "Cannot un-tick class: Students or data are already linked to this section in that class."
        finally: db.close()

    @staticmethod
    def delete_grouped_section(name):
        db = get_session()
        try:
            db.query(AcademicSection).filter_by(name=name).delete()
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after deleting section: {e}")
            return True, f"Section '{name}' deleted completely."
        except Exception as e:
            db.rollback()
            return False, "Cannot delete section. It is linked to existing students, attendance, or exams."
        finally: db.close()

    # ==========================================
    # SUBJECTS & LINKAGE MANAGEMENT
    # ==========================================
    @staticmethod
    def get_subjects(session_filter=None):
        db = get_session()
        try:
            return db.query(AcademicSubject).all()
        finally: db.close()

    @staticmethod
    def get_class_subject_assignment(class_id=None):
        db = get_session()
        try:
            subs = db.query(AcademicSubject).all()
            return subs, ""
        except Exception as e:
            return [], str(e)
        finally: db.close()

    @staticmethod
    def add_subject(name, code, sub_type):
        db = get_session()
        try:
            # FIX: Removed 'academic_session' keyword argument to match your database schema perfectly
            new_sub = AcademicSubject(name=name, code=code, subject_type=sub_type)
            db.add(new_sub)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after adding subject: {e}")
            return True, "Subject added successfully."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally: db.close()

    @staticmethod
    def delete_subject(sub_id):
        db = get_session()
        try:
            db.query(AcademicSubject).filter_by(id=sub_id).delete()
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed after deleting subject: {e}")
            return True, "Subject deleted successfully."
        except Exception as e:
            db.rollback()
            return False, "Cannot delete subject. It is in use."
        finally: db.close()