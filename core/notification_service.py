from datetime import date, datetime, timedelta
from database.connection import get_session
from core.state_manager import app_state

class NotificationService:
    """Enterprise Notification & Alert Engine.
    Queries active system state and persistent notifications without mutating core data."""

    @staticmethod
    def get_all_notifications(category_filter=None) -> list:
        """Returns a list of dicts: {id, type, icon, title, message, category, page_index}"""
        alerts = []
        db = get_session()
        try:
            # 1. Fee overdue alert (Finance)
            try:
                from database.models.fee import FeeVoucher
                overdue = db.query(FeeVoucher).filter(
                    FeeVoucher.status != "Paid",
                    FeeVoucher.due_date < date.today().strftime("%Y-%m-%d")
                ).count()
                if overdue > 0:
                    alerts.append({
                        "id": "notif_fee_overdue",
                        "type": "error",
                        "icon": "💰",
                        "title": "Fee Overdue",
                        "message": f"{overdue} student(s) have unpaid overdue fee vouchers.",
                        "category": "Finance",
                        "page_index": 4,
                    })
            except Exception:
                pass

            # 2. Inventory low-stock alert (Inventory)
            try:
                from database.models.inventory import InventoryItem
                low_stock = db.query(InventoryItem).filter(
                    InventoryItem.current_stock <= InventoryItem.min_stock_alert,
                    InventoryItem.status == "Active"
                ).all()
                if low_stock:
                    item_names = ", ".join([i.name for i in low_stock[:2]])
                    extra = f" and {len(low_stock) - 2} more" if len(low_stock) > 2 else ""
                    alerts.append({
                        "id": "notif_low_stock",
                        "type": "warning",
                        "icon": "📦",
                        "title": "Low Stock Reorder Alert",
                        "message": f"{len(low_stock)} item(s) need replenishment ({item_names}{extra}).",
                        "category": "Inventory",
                        "page_index": 14,
                    })
            except Exception:
                pass

            # 3. Library overdue alert (Library)
            try:
                from database.models.library import BookIssue
                lib_overdue = db.query(BookIssue).filter(
                    BookIssue.status == "Issued",
                    BookIssue.due_date < date.today()
                ).count()
                if lib_overdue > 0:
                    alerts.append({
                        "id": "notif_lib_overdue",
                        "type": "warning",
                        "icon": "📚",
                        "title": "Library Overdue",
                        "message": f"{lib_overdue} book(s) are overdue and not yet returned.",
                        "category": "Library",
                        "page_index": 11,
                    })
            except Exception:
                pass

            # 4. Leave pending approval alert (HR)
            try:
                from database.models.leave import LeaveApplication
                pending = db.query(LeaveApplication).filter_by(status="Pending").count()
                if pending > 0:
                    alerts.append({
                        "id": "notif_leave_pending",
                        "type": "info",
                        "icon": "📋",
                        "title": "Leave Pending",
                        "message": f"{pending} staff leave application(s) awaiting your approval.",
                        "category": "HR",
                        "page_index": 7,
                    })
            except Exception:
                pass

            # 5. Today staff birthdays (HR)
            try:
                from database.models.hr import Employee
                today_str = date.today().strftime("%m-%d")
                employees = db.query(Employee).filter(Employee.is_active == True).all()
                birthdays = []
                for emp in employees:
                    dob = getattr(emp, "date_of_birth", None) or getattr(emp, "dob", None)
                    if dob and len(str(dob)) >= 5:
                        dob_str = str(dob)
                        dob_mmdd = dob_str[5:10] if len(dob_str) >= 10 else dob_str
                        if dob_mmdd == today_str:
                            name = getattr(emp, "full_name", None) or getattr(emp, "name", str(emp.id))
                            birthdays.append(name)
                if birthdays:
                    alerts.append({
                        "id": "notif_birthdays",
                        "type": "success",
                        "icon": "🎂",
                        "title": "Staff Birthday Today",
                        "message": f"Today is {', '.join(birthdays[:3])}'s birthday!",
                        "category": "HR",
                        "page_index": 7,
                    })
            except Exception:
                pass

            # 6. Upcoming School Events (Events)
            try:
                from database.models.calendar import CalendarEvent
                today = date.today()
                target_date = today + timedelta(days=2)
                today_str = today.strftime("%Y-%m-%d")
                target_str = target_date.strftime("%Y-%m-%d")

                events = db.query(CalendarEvent).filter(
                    CalendarEvent.start_date >= today_str,
                    CalendarEvent.start_date <= target_str,
                ).order_by(CalendarEvent.start_date).all()

                for ev in events:
                    try:
                        ev_d = date.fromisoformat(ev.start_date[:10])
                        diff_days = (ev_d - today).days
                        when_str = "TODAY" if diff_days == 0 else ("TOMORROW" if diff_days == 1 else f"in {diff_days} days")
                    except Exception:
                        when_str = f"on {ev.start_date}"

                    alerts.append({
                        "id": f"notif_event_{ev.id}",
                        "type": "info",
                        "icon": "📅",
                        "title": f"Upcoming Event: {ev.title}",
                        "message": f"'{ev.title}' ({ev.event_type or 'School Event'}) is scheduled {when_str}.",
                        "category": "Events",
                        "page_index": 13,
                    })
            except Exception:
                pass

            # 7. System Backup Freshness (System)
            try:
                today_ymd = date.today().strftime("%Y-%m-%d")
                last_backup = app_state.get_setting("last_auto_backup_date", "")
                if last_backup != today_ymd:
                    alerts.append({
                        "id": "notif_backup_pending",
                        "type": "info",
                        "icon": "💾",
                        "title": "Daily Backup Check",
                        "message": "Routine daily backup check recommended to safeguard institutional data.",
                        "category": "System",
                        "page_index": 1,
                    })
            except Exception:
                pass

            # 8. Persistent System Notifications from DB (custom alerts)
            try:
                from database.models.notifications import SystemNotification
                db_notifs = db.query(SystemNotification).filter_by(is_dismissed=0).order_by(SystemNotification.id.desc()).limit(20).all()
                for sn in db_notifs:
                    pi = None
                    if sn.action_target and sn.action_target.startswith("page:"):
                        try:
                            pi = int(sn.action_target.split(":")[1])
                        except Exception:
                            pi = None
                    alerts.append({
                        "id": f"db_notif_{sn.id}",
                        "type": sn.severity,
                        "icon": sn.icon or "🔔",
                        "title": sn.title,
                        "message": sn.message,
                        "category": sn.category or "System",
                        "page_index": pi,
                    })
            except Exception:
                pass

        finally:
            db.close()

        if category_filter and category_filter != "All":
            alerts = [a for a in alerts if a.get("category") == category_filter]

        return alerts

    @staticmethod
    def get_count() -> int:
        return len(NotificationService.get_all_notifications())

    @staticmethod
    def create_notification(title, message, category="System", severity="info", icon="🔔", action_target=None):
        """Creates a persistent system notification."""
        db = get_session()
        try:
            from database.models.notifications import SystemNotification
            sn = SystemNotification(
                title=title, message=message, category=category,
                severity=severity, icon=icon, action_target=action_target
            )
            db.add(sn)
            db.commit()
            app_state.notify_data_changed()
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def dismiss_notification(notif_id):
        """Dismisses a persistent notification if from DB."""
        if str(notif_id).startswith("db_notif_"):
            db_id = int(str(notif_id).replace("db_notif_", ""))
            db = get_session()
            try:
                from database.models.notifications import SystemNotification
                sn = db.query(SystemNotification).filter_by(id=db_id).first()
                if sn:
                    sn.is_dismissed = 1
                    db.commit()
                    app_state.notify_data_changed()
                    return True
            except Exception:
                db.rollback()
            finally:
                db.close()
        return False
