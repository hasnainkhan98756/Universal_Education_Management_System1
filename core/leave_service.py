from datetime import date, datetime, timedelta
from database.connection import get_session
from database.models.leave import LeaveType, LeaveApplication


class LeaveService:

    @staticmethod
    def get_leave_types():
        db = get_session()
        try:
            return db.query(LeaveType).filter_by(is_active=True).order_by(LeaveType.id).all()
        finally:
            db.close()

    @staticmethod
    def apply_leave(employee_id: int, employee_name: str, leave_type_id: int,
                    from_date: date, to_date: date, reason: str,
                    allow_excess: bool = False, auto_approve: bool = False):
        db = get_session()
        try:
            if to_date < from_date:
                return False, "End date must be after start date."
            total_days = (to_date - from_date).days + 1
            lt = db.query(LeaveType).filter_by(id=leave_type_id).first()
            # Check remaining balance
            year_start = date(date.today().year, 1, 1)
            year_end   = date(date.today().year, 12, 31)
            used = db.query(LeaveApplication).filter(
                LeaveApplication.employee_id   == employee_id,
                LeaveApplication.leave_type_id == leave_type_id,
                LeaveApplication.status        == "Approved",
                LeaveApplication.from_date     >= year_start,
                LeaveApplication.to_date       <= year_end,
            ).all()
            used_days = sum(a.total_days for a in used)
            excess_note = ""
            if lt and (used_days + total_days) > lt.max_days_per_year:
                remaining = max(0, lt.max_days_per_year - used_days)
                excess = (used_days + total_days) - lt.max_days_per_year
                if not allow_excess:
                    return False, f"EXCEEDS_QUOTA:The requested duration ({total_days} days) exceeds the standard {lt.name} annual balance ({remaining} days remaining of {lt.max_days_per_year} days/year limit by {excess} days)."
                else:
                    excess_note = f" [Sanctioned excess: {excess} days over {lt.max_days_per_year}-day quota]"

            app = LeaveApplication(
                employee_id     = employee_id,
                employee_name   = employee_name,
                leave_type_id   = leave_type_id,
                leave_type_name = lt.name if lt else "",
                from_date       = from_date,
                to_date         = to_date,
                total_days      = total_days,
                reason          = (reason.strip() + excess_note).strip(),
                status          = "Approved" if auto_approve else "Pending",
                admin_remarks   = ("Approved by Admin" + excess_note) if auto_approve else (excess_note.strip() if excess_note else None),
                reviewed_on     = datetime.now() if auto_approve else None,
            )
            db.add(app)
            db.commit()

            if auto_approve:
                from database.models.hr import StaffAttendance, Employee
                curr = app.from_date
                while curr <= app.to_date:
                    d_str = curr.strftime("%Y-%m-%d")
                    att = db.query(StaffAttendance).filter_by(employee_id=app.employee_id, date=d_str).first()
                    if att:
                        att.status = "Leave"
                        att.remarks = f"Approved Leave ({app.leave_type_name})"
                    else:
                        db.add(StaffAttendance(
                            employee_id=app.employee_id,
                            date=d_str,
                            status="Leave",
                            remarks=f"Approved Leave ({app.leave_type_name})"
                        ))
                    curr += timedelta(days=1)

                today = date.today()
                if app.from_date <= today <= app.to_date:
                    emp = db.query(Employee).filter_by(id=app.employee_id).first()
                    if emp:
                        emp.status = "On Leave"
                db.commit()

            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
                app_state.trigger_dashboard_sync()
            except Exception:
                pass

            msg = f"Leave granted and attendance register updated for {total_days} day(s)." if auto_approve else f"Leave application submitted for {total_days} day(s)."
            return True, msg
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def approve_leave(app_id: int, admin_remarks: str = "Approved"):
        db = get_session()
        try:
            app = db.query(LeaveApplication).filter_by(id=app_id).first()
            if not app: return False, "Application not found."
            app.status       = "Approved"
            app.reviewed_on  = datetime.now()
            app.admin_remarks = admin_remarks.strip()

            # Auto-sync staff attendance records for the approved leave period
            from database.models.hr import StaffAttendance, Employee
            curr = app.from_date
            while curr <= app.to_date:
                d_str = curr.strftime("%Y-%m-%d")
                att = db.query(StaffAttendance).filter_by(employee_id=app.employee_id, date=d_str).first()
                if att:
                    att.status = "Leave"
                    att.remarks = f"Approved Leave ({app.leave_type_name})"
                else:
                    db.add(StaffAttendance(
                        employee_id=app.employee_id,
                        date=d_str,
                        status="Leave",
                        remarks=f"Approved Leave ({app.leave_type_name})"
                    ))
                curr += timedelta(days=1)

            today = date.today()
            if app.from_date <= today <= app.to_date:
                emp = db.query(Employee).filter_by(id=app.employee_id).first()
                if emp:
                    emp.status = "On Leave"

            db.commit()
            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
                app_state.trigger_dashboard_sync()
            except Exception:
                pass
            return True, "Leave approved and attendance register updated."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def reject_leave(app_id: int, admin_remarks: str = "Rejected"):
        db = get_session()
        try:
            app = db.query(LeaveApplication).filter_by(id=app_id).first()
            if not app: return False, "Application not found."
            app.status        = "Rejected"
            app.reviewed_on   = datetime.now()
            app.admin_remarks = admin_remarks.strip()

            # Revert any attendance marked as Approved Leave for this application
            from database.models.hr import StaffAttendance, Employee
            curr = app.from_date
            while curr <= app.to_date:
                d_str = curr.strftime("%Y-%m-%d")
                att = db.query(StaffAttendance).filter_by(employee_id=app.employee_id, date=d_str).first()
                if att and "Approved Leave" in (att.remarks or ""):
                    att.status = "Present"
                    att.remarks = ""
                curr += timedelta(days=1)

            today = date.today()
            if app.from_date <= today <= app.to_date:
                other_active = db.query(LeaveApplication).filter(
                    LeaveApplication.employee_id == app.employee_id,
                    LeaveApplication.id != app.id,
                    LeaveApplication.status == "Approved",
                    LeaveApplication.from_date <= today,
                    LeaveApplication.to_date >= today
                ).first()
                if not other_active:
                    emp = db.query(Employee).filter_by(id=app.employee_id).first()
                    if emp and emp.status in ["On Leave", "Leave"]:
                        emp.status = "Active"

            db.commit()
            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
                app_state.trigger_dashboard_sync()
            except Exception:
                pass
            return True, "Leave rejected."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def delete_leave(app_id: int):
        db = get_session()
        try:
            app = db.query(LeaveApplication).filter_by(id=app_id).first()
            if not app: return False, "Not found."

            from database.models.hr import StaffAttendance, Employee
            curr = app.from_date
            while curr <= app.to_date:
                d_str = curr.strftime("%Y-%m-%d")
                att = db.query(StaffAttendance).filter_by(employee_id=app.employee_id, date=d_str).first()
                if att and "Approved Leave" in (att.remarks or ""):
                    att.status = "Present"
                    att.remarks = ""
                curr += timedelta(days=1)

            today = date.today()
            if app.from_date <= today <= app.to_date:
                other_active = db.query(LeaveApplication).filter(
                    LeaveApplication.employee_id == app.employee_id,
                    LeaveApplication.id != app.id,
                    LeaveApplication.status == "Approved",
                    LeaveApplication.from_date <= today,
                    LeaveApplication.to_date >= today
                ).first()
                if not other_active:
                    emp = db.query(Employee).filter_by(id=app.employee_id).first()
                    if emp and emp.status in ["On Leave", "Leave"]:
                        emp.status = "Active"

            db.delete(app)
            db.commit()
            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
                app_state.trigger_dashboard_sync()
            except Exception:
                pass
            return True, "Leave application deleted."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_all_applications(status_filter: str = "All"):
        db = get_session()
        try:
            q = db.query(LeaveApplication)
            if status_filter != "All":
                q = q.filter_by(status=status_filter)
            return q.order_by(LeaveApplication.applied_on.desc()).all()
        finally:
            db.close()

    @staticmethod
    def get_employee_balance(employee_id: int):
        """Returns dict of leave_type_name -> {used, max, remaining}"""
        db = get_session()
        try:
            types = db.query(LeaveType).filter_by(is_active=True).all()
            year_start = date(date.today().year, 1, 1)
            year_end   = date(date.today().year, 12, 31)
            result = {}
            for lt in types:
                used_apps = db.query(LeaveApplication).filter(
                    LeaveApplication.employee_id   == employee_id,
                    LeaveApplication.leave_type_id == lt.id,
                    LeaveApplication.status        == "Approved",
                    LeaveApplication.from_date     >= year_start,
                    LeaveApplication.to_date       <= year_end,
                ).all()
                used = sum(a.total_days for a in used_apps)
                result[lt.name] = {
                    "used":      used,
                    "max":       lt.max_days_per_year,
                    "remaining": max(0, lt.max_days_per_year - used),
                }
            return result
        finally:
            db.close()

    @staticmethod
    def get_pending_count():
        db = get_session()
        try:
            return db.query(LeaveApplication).filter_by(status="Pending").count()
        finally:
            db.close()

    @staticmethod
    def get_active_leave_for_employee(employee_id: int, target_date=None):
        """
        Retrieves detailed active leave information for an employee.
        Checks for an approved LeaveApplication covering target_date,
        or falls back to employee profile status if marked On Leave.
        """
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        db = get_session()
        try:
            from database.models.hr import Employee
            emp = db.query(Employee).filter_by(id=employee_id).first()
            if not emp:
                return None

            # 1. Search for an approved LeaveApplication covering target_date
            app = db.query(LeaveApplication).filter(
                LeaveApplication.employee_id == employee_id,
                LeaveApplication.status == "Approved",
                LeaveApplication.from_date <= target_date,
                LeaveApplication.to_date >= target_date
            ).order_by(LeaveApplication.id.desc()).first()

            if not app:
                # Also check most recent approved leave
                app = db.query(LeaveApplication).filter(
                    LeaveApplication.employee_id == employee_id,
                    LeaveApplication.status == "Approved"
                ).order_by(LeaveApplication.id.desc()).first()

            if app:
                return {
                    "found": True,
                    "is_formal_application": True,
                    "application_id": app.id,
                    "employee_id": emp.id,
                    "emp_id": emp.emp_id,
                    "employee_name": f"{emp.first_name} {emp.last_name or ''}".strip(),
                    "designation": emp.designation or "Faculty / Staff",
                    "department": emp.department or "Academics",
                    "leave_type_name": app.leave_type_name or "Official Leave",
                    "from_date": app.from_date.strftime("%Y-%m-%d") if app.from_date else "-",
                    "to_date": app.to_date.strftime("%Y-%m-%d") if app.to_date else "-",
                    "total_days": app.total_days or 1,
                    "reason": app.reason or "No specific reason stated in application.",
                    "status": app.status,
                    "applied_on": app.applied_on.strftime("%Y-%m-%d %H:%M") if app.applied_on else "-",
                    "reviewed_on": app.reviewed_on.strftime("%Y-%m-%d %H:%M") if app.reviewed_on else "-",
                    "admin_remarks": app.admin_remarks or "Approved by Administration",
                }

            # 2. Fallback: Employee status is On Leave without formal application
            if emp.status in ["On Leave", "Leave"]:
                t_str = target_date.strftime("%Y-%m-%d")
                return {
                    "found": True,
                    "is_formal_application": False,
                    "application_id": None,
                    "employee_id": emp.id,
                    "emp_id": emp.emp_id,
                    "employee_name": f"{emp.first_name} {emp.last_name or ''}".strip(),
                    "designation": emp.designation or "Faculty / Staff",
                    "department": emp.department or "Academics",
                    "leave_type_name": "Sanctioned Medical / Official Leave",
                    "from_date": t_str,
                    "to_date": t_str,
                    "total_days": 1,
                    "reason": "Direct medical or administrative sanctioned leave recorded in employee profile.",
                    "status": "On Leave",
                    "applied_on": "-",
                    "reviewed_on": "-",
                    "admin_remarks": "Sanctioned Medical/Official Leave",
                }

            return None
        finally:
            db.close()

    @staticmethod
    def return_from_leave(employee_id: int, return_date=None, update_attendance: bool = True):
        """
        Ends an employee's active leave as of return_date.
        Sets Employee status to 'Active', curtails or marks LeaveApplication,
        and optionally updates StaffAttendance for return_date to 'Present'.
        """
        if return_date is None:
            return_date = date.today()
        elif isinstance(return_date, str):
            return_date = datetime.strptime(return_date, "%Y-%m-%d").date()

        date_str = return_date.strftime("%Y-%m-%d")
        db = get_session()
        try:
            from database.models.hr import Employee, StaffAttendance
            emp = db.query(Employee).filter_by(id=employee_id).first()
            if not emp:
                return False, "Employee not found."

            emp.status = "Active"

            # 1. Adjust approved LeaveApplications covering return_date or in the future
            active_leaves = db.query(LeaveApplication).filter(
                LeaveApplication.employee_id == employee_id,
                LeaveApplication.status == "Approved",
                LeaveApplication.to_date >= return_date
            ).all()

            for app in active_leaves:
                if return_date <= app.from_date:
                    app.status = "Returned Early"
                    app.total_days = 0
                    app.admin_remarks = f"Staff arrived/resumed duty early on {date_str}."
                else:
                    app.to_date = return_date - timedelta(days=1)
                    app.total_days = max(1, (app.to_date - app.from_date).days + 1)
                    prev_rem = app.admin_remarks or ""
                    app.admin_remarks = f"{prev_rem} [Resumed duty early on {date_str}].".strip()

            # 2. Update attendance for return_date
            if update_attendance:
                att_today = db.query(StaffAttendance).filter_by(employee_id=employee_id, date=date_str).first()
                if att_today:
                    att_today.status = "Present"
                    att_today.remarks = "Arrived / Resumed Duty"
                else:
                    db.add(StaffAttendance(
                        employee_id=employee_id,
                        date=date_str,
                        status="Present",
                        remarks="Arrived / Resumed Duty"
                    ))

            # 3. Clean up any future pre-marked 'Leave' records for this employee
            future_leaves = db.query(StaffAttendance).filter(
                StaffAttendance.employee_id == employee_id,
                StaffAttendance.date > date_str,
                StaffAttendance.status == "Leave"
            ).all()
            for fl in future_leaves:
                db.delete(fl)

            db.commit()
            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
                app_state.trigger_dashboard_sync()
            except Exception:
                pass

            emp_name = f"{emp.first_name} {emp.last_name or ''}".strip()
            return True, f"{emp_name} has been removed from Leave and marked Active."
        except Exception as e:
            db.rollback()
            return False, f"Database Error: {str(e)}"
        finally:
            db.close()

