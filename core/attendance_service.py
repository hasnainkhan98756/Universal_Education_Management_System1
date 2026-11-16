from database.connection import get_session
from database.models.student import Student
from database.models.attendance import AttendanceRecord
from core.state_manager import app_state
from sqlalchemy.orm import joinedload
from datetime import datetime, date

class AttendanceService:
    """Centralized logic for managing student attendance, duplicates, and analytics."""

    @staticmethod
    def get_holiday_or_event(date_str, session_name=None):
        """Checks if a given date (YYYY-MM-DD) falls on a Gazetted Holiday, Vacation, School Closure, or Sunday."""
        from core.calendar_service import CalendarService
        return CalendarService.get_holiday_or_event(date_str, session_name)

    @staticmethod
    def is_attendance_marked_today():
        """Fast check to see if any attendance was marked today for the Dashboard Reminder Banner.
        If today is an official Holiday or Vacation, returns True (no reminder needed)."""
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            if AttendanceService.get_holiday_or_event(today_str):
                return True
        except Exception:
            pass

        db = get_session()
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_date = datetime.now().date()
            record = db.query(AttendanceRecord).filter(
                (AttendanceRecord.date == today_str) | (AttendanceRecord.date == today_date)
            ).first()
            return record is not None
        except Exception:
            return False
        finally:
            db.close()

    @staticmethod
    def get_attendance_reminder_status():
        """
        Dashboard intelligent attendance reminder check:
        1. Checks if attendance is marked for today (if today is not a Sunday/Holiday).
        2. Checks recent working days (up to 7 days back, skipping Sundays and gazetted holidays).
        3. Returns status dict with all_marked, missed_days, and human-readable message.
        """
        from datetime import datetime, timedelta
        from core.calendar_service import CalendarService

        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")

        db = get_session()
        try:
            active_students_count = db.query(Student).filter_by(status="Active").count()
            if active_students_count == 0:
                return {"all_marked": True, "missed_days": [], "message": ""}

            start_check_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
            records = db.query(AttendanceRecord.date).filter(
                AttendanceRecord.date >= start_check_date
            ).all()
            marked_dates = set()
            for r in records:
                d_val = r[0]
                if isinstance(d_val, str):
                    marked_dates.add(d_val[:10])
                elif hasattr(d_val, "strftime"):
                    marked_dates.add(d_val.strftime("%Y-%m-%d"))

            missed_working_days = []
            is_today_missed = False

            for offset in range(0, 7):
                check_d = today - timedelta(days=offset)
                check_str = check_d.strftime("%Y-%m-%d")
                
                # Skip Sundays and Gazetted Holidays / Vacations
                if CalendarService.get_holiday_or_event(check_str):
                    continue
                
                if check_str not in marked_dates:
                    missed_working_days.append(check_d)
                    if offset == 0:
                        is_today_missed = True

            if not missed_working_days:
                return {
                    "all_marked": True,
                    "missed_days": [],
                    "message": ""
                }

            past_missed = [d for d in missed_working_days if d != today]
            formatted_past = [d.strftime("%d %b") for d in past_missed[:3]]

            if is_today_missed and not past_missed:
                msg = f"Attendance Reminder: Today's ({today.strftime('%d %b %Y')}) student attendance has not been marked yet."
            elif is_today_missed and past_missed:
                msg = f"Attendance Alert: Attendance pending for Today and {len(past_missed)} previous working day(s) ({', '.join(formatted_past)})."
            else:
                msg = f"Attendance Alert: Attendance was missed on {len(past_missed)} recent working day(s) ({', '.join(formatted_past)})."

            return {
                "all_marked": False,
                "missed_days": [d.strftime("%Y-%m-%d") for d in missed_working_days],
                "missed_count": len(missed_working_days),
                "is_today_missed": is_today_missed,
                "message": msg
            }
        except Exception as e:
            return {"all_marked": True, "missed_days": [], "message": ""}
        finally:
            db.close()

    @staticmethod
    def get_attendance_sheet(class_id, section_id, date_str):
        """Loads active students for a class and fetches existing attendance if already saved."""
        db = get_session()
        try:
            try: parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except: parsed_date = date_str

            # Strictly query active enrolled students only (Graduated, Migrated, Suspended, Dropout never appear)
            students = db.query(Student).filter(
                Student.class_id == class_id,
                Student.section_id == section_id,
                Student.status == "Active"
            ).order_by(Student.first_name).all()
            
            existing_records = db.query(AttendanceRecord).filter(
                (AttendanceRecord.class_id == class_id) &
                (AttendanceRecord.section_id == section_id) &
                ((AttendanceRecord.date == date_str) | (AttendanceRecord.date == parsed_date))
            ).all()
            
            record_map = {rec.student_id: rec for rec in existing_records}
            holiday_info = AttendanceService.get_holiday_or_event(date_str)
            default_st = "Holiday" if holiday_info else "Present"
            default_rem = holiday_info["title"] if holiday_info else ""

            sheet_data = []
            for stu in students:
                rec = record_map.get(stu.id)
                sheet_data.append({
                    "student_id": stu.id,
                    "student_system_id": stu.student_id,
                    "name": f"{stu.first_name} {stu.last_name or ''}".strip(),
                    "father_name": stu.father_name or "-",
                    "status": rec.status if rec else default_st, 
                    "remarks": rec.remarks if rec else default_rem,
                    "is_existing": True if rec else False
                })
            return sheet_data
        finally:
            db.close()

    @staticmethod
    def save_attendance(class_id, section_id, date_str, attendance_data):
        """Saves or updates bulk attendance safely with type-casted dates."""
        db = get_session()
        try:
            active_session = app_state.get_setting("session", "Default")
            try: parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except: parsed_date = date_str
            
            for data in attendance_data:
                s_id = int(data['student_id'])
                record = db.query(AttendanceRecord).filter(
                    (AttendanceRecord.student_id == s_id) & 
                    ((AttendanceRecord.date == date_str) | (AttendanceRecord.date == parsed_date))
                ).first()
                
                if record:
                    record.status = data['status']
                    record.remarks = data['remarks']
                else:
                    new_record = AttendanceRecord(
                        student_id=s_id, class_id=class_id, section_id=section_id,
                        date=parsed_date, status=data['status'], remarks=data['remarks'], academic_session=active_session
                    )
                    db.add(new_record)
            
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as e:
                print(f"Error broadcasting data changed: {e}")

            try:
                from core.backup_service import BackupService
                BackupService.trigger_auto_backup(f"Attendance Saved for {date_str}")
            except Exception: pass

            return True, "Attendance saved and updated successfully!"
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {e}"
        finally:
            db.close()

    @staticmethod
    def get_dashboard_analytics(date_str=None):
        if not date_str: date_str = datetime.now().strftime("%Y-%m-%d")
        db = get_session()
        try:
            try: parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except: parsed_date = None

            q = db.query(AttendanceRecord).join(Student, AttendanceRecord.student_id == Student.id).filter(
                Student.status == "Active"
            )
            if parsed_date:
                records = q.filter((AttendanceRecord.date == date_str) | (AttendanceRecord.date == parsed_date)).all()
            else:
                records = q.filter(AttendanceRecord.date == date_str).all()

            working_records = [r for r in records if r.status != "Holiday"]
            total_recorded = len(working_records)
            stats = {"total": total_recorded, "present": 0, "absent": 0, "leave": 0, "late": 0, "percentage": 0.0}
            
            for r in working_records:
                if r.status == "Present": stats["present"] += 1
                elif r.status == "Absent": stats["absent"] += 1
                elif r.status == "Leave": stats["leave"] += 1
                elif r.status == "Late": stats["late"] += 1
                
            if total_recorded > 0:
                stats["percentage"] = ((stats["present"] + stats["late"]) / total_recorded) * 100
            return stats
        finally:
            db.close()

    @staticmethod
    def get_student_attendance_summary(student_id):
        db = get_session()
        try:
            records = db.query(AttendanceRecord).filter_by(student_id=student_id).all()
            working_records = [r for r in records if r.status != "Holiday"]
            total = len(working_records)
            stats = {"present": 0, "absent": 0, "leave": 0, "late": 0, "percentage": 0.0}
            for r in working_records:
                if r.status == "Present": stats["present"] += 1
                elif r.status == "Absent": stats["absent"] += 1
                elif r.status == "Leave": stats["leave"] += 1
                elif r.status == "Late": stats["late"] += 1
            if total > 0:
                stats["percentage"] = ((stats["present"] + stats["late"]) / total) * 100
            return stats
        finally:
            db.close()

    @staticmethod
    def get_class_attendance_report(class_id, section_id, target_year, target_month=0):
        """
        BULLETPROOF REPORT ENGINE: Fetches attendance over a specific month or entire year.
        Uses Python-level date filtering to bypass any SQLite date formatting errors.
        target_month: 1-12 (Specific Month) or 0 (Entire Year)
        """
        db = get_session()
        try:
            students = db.query(Student).filter(
                Student.class_id == class_id,
                Student.section_id == section_id,
                Student.status == "Active"
            ).order_by(Student.first_name).all()
            all_records = db.query(AttendanceRecord).filter_by(class_id=class_id, section_id=section_id).all()
            
            # 1. Safely filter records by the requested date range
            valid_records = []
            for r in all_records:
                try:
                    r_date = r.date if isinstance(r.date, date) else datetime.strptime(str(r.date), "%Y-%m-%d").date()
                    if r_date.year == target_year:
                        if target_month == 0 or r_date.month == target_month:
                            valid_records.append((r.student_id, r.status))
                except Exception:
                    pass # Ignore badly formatted legacy dates

            # 2. Aggregate data per student (excluding holidays from required total)
            report_data = []
            for stu in students:
                stu_records = [status for sid, status in valid_records if sid == stu.id]
                working_records = [status for status in stu_records if status != "Holiday"]
                total = len(working_records)
                
                present = working_records.count("Present")
                absent = working_records.count("Absent")
                leave = working_records.count("Leave")
                late = working_records.count("Late")
                
                pct = ((present + late) / total * 100) if total > 0 else 0.0
                
                report_data.append({
                    "id": stu.student_id,
                    "name": f"{stu.first_name} {stu.last_name or ''}".strip(),
                    "total": total,
                    "present": present,
                    "absent": absent,
                    "leave": leave,
                    "late": late,
                    "percentage": round(pct, 1)
                })
            
            return report_data
        finally:
            db.close()