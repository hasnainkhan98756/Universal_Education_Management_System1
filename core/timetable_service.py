import os
import random
from database.connection import get_session
from database.models.timetable import Room, TimetablePeriod, TimetableEntry
from database.models.calendar import CalendarEvent
from database.models.hr import TeacherAssignment, Employee
from database.models.academic import AcademicSubject, AcademicClass
from core.state_manager import app_state
from sqlalchemy.orm import joinedload
from datetime import datetime

class TimetableService:
    # ==========================================
    # 1. IN-APP REMINDERS & CALENDAR EVENTS
    # ==========================================
    @staticmethod
    def get_upcoming_reminders():
        db = get_session()
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            session = app_state.get_setting("session", "Default")
            events = db.query(CalendarEvent).filter(
                CalendarEvent.academic_session == session,
                CalendarEvent.start_date >= today
            ).order_by(CalendarEvent.start_date).limit(3).all()
            
            reminders = []
            for e in events:
                tag = "Exam" if "Exam" in e.event_type else "Holiday" if "Holiday" in e.event_type else "Event"
                reminders.append(f"[{tag}] {e.start_date}: {e.title}")
            return reminders
        finally:
            db.close()

    @staticmethod
    def get_events():
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            return db.query(CalendarEvent).filter_by(academic_session=session).order_by(CalendarEvent.start_date.desc()).all()
        finally: db.close()

    @staticmethod
    def save_event(title, type_val, start, end, desc):
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            db.add(CalendarEvent(academic_session=session, title=title, event_type=type_val, start_date=start, end_date=end, description=desc))
            db.commit()
            app_state.notify_data_changed()
            return True, "Event added."
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()

    # ==========================================
    # 2. ROOMS & PERIOD CONFIGURATION
    # ==========================================
    @staticmethod
    def get_rooms():
        db = get_session()
        try: return db.query(Room).filter_by(is_active=True).order_by(Room.room_no).all()
        finally: db.close()

    @staticmethod
    def save_room(room_no, name, capacity, room_type):
        db = get_session()
        try:
            db.add(Room(room_no=room_no, name=name, capacity=capacity, room_type=room_type))
            db.commit(); return True, "Room saved."
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()

    @staticmethod
    def get_periods():
        db = get_session()
        try: return db.query(TimetablePeriod).order_by(TimetablePeriod.display_order).all()
        finally: db.close()

    @staticmethod
    def save_period(name, start_t, end_t, is_break, order):
        db = get_session()
        try:
            db.add(TimetablePeriod(name=name, start_time=start_t, end_time=end_t, is_break=is_break, display_order=order))
            db.commit(); return True, "Period saved."
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()

    # ==========================================
    # 3. SMART TIMETABLE ENGINE & AUTO-GENERATOR
    # ==========================================
    @staticmethod
    def get_class_timetable(class_id, section_id):
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            return db.query(TimetableEntry).options(
                joinedload(TimetableEntry.period), joinedload(TimetableEntry.academic_subject),
                joinedload(TimetableEntry.employee), joinedload(TimetableEntry.room)
            ).filter_by(academic_session=session, class_id=class_id, section_id=section_id).all()
        finally: db.close()

    @staticmethod
    def get_smart_teacher_assignments(class_id, section_id):
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            return db.query(TeacherAssignment).options(
                joinedload(TeacherAssignment.employee), joinedload(TeacherAssignment.academic_subject)
            ).filter_by(academic_session=session, class_id=class_id, section_id=section_id).all()
        finally: db.close()

    @staticmethod
    def get_workload_completion(class_id, section_id):
        """CRITICAL FIX: Combines Official HR Workloads with Live Ad-Hoc Scheduled Slots."""
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            
            # Get Official Workloads
            assignments = db.query(TeacherAssignment).options(
                joinedload(TeacherAssignment.academic_subject), 
                joinedload(TeacherAssignment.employee)
            ).filter_by(academic_session=session, class_id=class_id, section_id=section_id).all()
            
            # Get Actually Scheduled Slots in the Grid
            scheduled = db.query(TimetableEntry).options(
                joinedload(TimetableEntry.academic_subject), 
                joinedload(TimetableEntry.employee)
            ).filter_by(academic_session=session, class_id=class_id, section_id=section_id).all()
            
            tracker_map = {} 
            
            # Seed with official assignments
            for a in assignments:
                key = (a.subject_id, a.employee_id)
                tracker_map[key] = {
                    "subject": a.academic_subject.name if a.academic_subject else "Unknown",
                    "teacher": f"{a.employee.first_name} {a.employee.last_name or ''}".strip(),
                    "assigned": a.periods_per_week,
                    "scheduled": 0,
                    "assign_id": a.id
                }
                
            # Count scheduled slots, add them dynamically if they have no official workload
            for s in scheduled:
                key = (s.subject_id, s.employee_id)
                if key in tracker_map:
                    tracker_map[key]["scheduled"] += 1
                else:
                    tracker_map[key] = {
                        "subject": s.academic_subject.name if s.academic_subject else "Unknown",
                        "teacher": f"{s.employee.first_name} {s.employee.last_name or ''}".strip(),
                        "assigned": 0,
                        "scheduled": 1,
                        "assign_id": None
                    }
                    
            # Sort by subject name for clean display
            return sorted(list(tracker_map.values()), key=lambda x: x["subject"])
        finally: 
            db.close()

    @staticmethod
    def check_clash_and_save(class_id, section_id, day, period_id, subject_id, employee_id, room_id):
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            
            # Check Clashes
            class_clash = db.query(TimetableEntry).filter_by(academic_session=session, class_id=class_id, section_id=section_id, day_of_week=day, period_id=period_id).first()
            teacher_clash = db.query(TimetableEntry).options(joinedload(TimetableEntry.academic_class)).filter_by(academic_session=session, employee_id=employee_id, day_of_week=day, period_id=period_id).first()
            
            if class_clash and (class_clash.subject_id != subject_id or class_clash.employee_id != employee_id):
                db.delete(class_clash)
                db.flush()
            
            if teacher_clash and (teacher_clash.class_id != class_id or teacher_clash.section_id != section_id):
                return False, f"TEACHER CLASH: This teacher is already scheduled in {teacher_clash.academic_class.name} during this period."

            new_entry = TimetableEntry(
                academic_session=session, class_id=class_id, section_id=section_id,
                day_of_week=day, period_id=period_id, subject_id=subject_id, 
                employee_id=employee_id, room_id=room_id if room_id else None
            )
            db.add(new_entry)
            db.commit()
            return True, "Slot scheduled successfully."
        except Exception as e:
            db.rollback(); return False, f"Error: {e}"
        finally: db.close()

    @staticmethod
    def remove_slot(class_id, section_id, day, period_id):
        db = get_session()
        try:
            session = app_state.get_setting("session", "Default")
            entry = db.query(TimetableEntry).filter_by(academic_session=session, class_id=class_id, section_id=section_id, day_of_week=day, period_id=period_id).first()
            if entry:
                db.delete(entry); db.commit()
            return True, "Slot cleared."
        finally: db.close()

    @staticmethod
    def auto_generate_timetable(class_id, section_id):
        db = get_session()
        try:
            session_name = app_state.get_setting("session", "Default")
            
            periods = db.query(TimetablePeriod).filter_by(is_break=False).order_by(TimetablePeriod.display_order).all()
            if not periods:
                return False, "You must configure Bell Periods in the Config tab before auto-generating."

            workloads = db.query(TeacherAssignment).filter_by(academic_session=session_name, class_id=class_id, section_id=section_id).all()
            if not workloads:
                return False, "No teachers assigned to this class! Please assign workloads using the Quick Assign button first."

            db.query(TimetableEntry).filter_by(academic_session=session_name, class_id=class_id, section_id=section_id).delete()
            db.flush()

            tasks = []
            for w in workloads:
                for _ in range(w.periods_per_week):
                    tasks.append(w)
            
            random.shuffle(tasks)

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            placed_count = 0

            for day in days:
                for p in periods:
                    if not tasks: break 
                    
                    for i, task in enumerate(tasks):
                        clash = db.query(TimetableEntry).filter_by(academic_session=session_name, employee_id=task.employee_id, day_of_week=day, period_id=p.id).first()
                        if not clash:
                            entry = TimetableEntry(
                                academic_session=session_name, class_id=class_id, section_id=section_id,
                                day_of_week=day, period_id=p.id, subject_id=task.subject_id, employee_id=task.employee_id
                            )
                            db.add(entry)
                            db.flush()
                            tasks.pop(i) 
                            placed_count += 1
                            break 
            
            db.commit()
            if tasks:
                return True, f"Auto-Generated {placed_count} slots. \nWarning: {len(tasks)} periods could not be scheduled due to Teacher clashes or lack of periods."
            return True, f"Successfully Auto-Generated all {placed_count} required periods perfectly!"
        except Exception as e:
            db.rollback(); return False, f"Auto-Generation Error: {e}"
        finally:
            db.close()

    # ==========================================
    # 4. EXCEL EXPORTS
    # ==========================================
    @staticmethod
    def export_timetable_to_excel(class_id, section_id, filepath, class_name):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        db = get_session()
        try:
            session_name = app_state.get_setting("session", "Default")
            entries = db.query(TimetableEntry).options(
                joinedload(TimetableEntry.period), joinedload(TimetableEntry.academic_subject), joinedload(TimetableEntry.employee)
            ).filter_by(academic_session=session_name, class_id=class_id, section_id=section_id).all()
            periods = db.query(TimetablePeriod).order_by(TimetablePeriod.display_order).all()

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Class Timetable"

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            
            ws.append([f"Timetable for {class_name}"])
            ws.cell(row=1, column=1).font = Font(bold=True, size=16)
            ws.append(["Period / Time"] + days)
            
            header_fill = PatternFill(start_color="1D4ED8", fill_type="solid")
            for col in range(1, len(days) + 2):
                c = ws.cell(row=2, column=col)
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = header_fill
                c.alignment = Alignment(horizontal="center")

            for r_idx, p in enumerate(periods, start=3):
                timing_label = f"{p.name} — {p.start_time}–{p.end_time}" if (p.start_time and p.end_time) else p.name
                ws.cell(row=r_idx, column=1, value=timing_label).font = Font(bold=True)
                if p.is_break:
                    for c_idx in range(2, len(days) + 2):
                        cell = ws.cell(row=r_idx, column=c_idx, value="BREAK")
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                        cell.fill = PatternFill(start_color="E5E7EB", fill_type="solid")
                else:
                    for c_idx, day in enumerate(days, start=2):
                        entry_text = "-"
                        for e in entries:
                            if e.period_id == p.id and e.day_of_week == day:
                                entry_text = f"{e.academic_subject.name}\n({e.employee.first_name})"
                                break
                        cell = ws.cell(row=r_idx, column=c_idx, value=entry_text)
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            ws.column_dimensions['A'].width = 28
            for col in ['B', 'C', 'D', 'E', 'F', 'G']:
                ws.column_dimensions[col].width = 20

            wb.save(filepath)
            return True, "Export Successful"
        except Exception as e:
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def export_timetable_to_pdf(class_id, section_id, filepath, class_name):
        """Generates a high-clarity printable PDF Timetable with period timings."""
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from core.document_service import DocumentService

        db = get_session()
        try:
            session_name = app_state.get_setting("session", "Default")
            inst_name = DocumentService.get_setting("name", "Universal Education Management System")
            entries = db.query(TimetableEntry).options(
                joinedload(TimetableEntry.period), joinedload(TimetableEntry.academic_subject), joinedload(TimetableEntry.employee), joinedload(TimetableEntry.room)
            ).filter_by(academic_session=session_name, class_id=class_id, section_id=section_id).all()
            periods = db.query(TimetablePeriod).order_by(TimetablePeriod.display_order).all()

            doc = SimpleDocTemplate(filepath, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=15, leading=18, alignment=1, textColor=colors.HexColor('#1E3A8A'))
            sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, leading=13, alignment=1, textColor=colors.HexColor('#475569'))
            hdr_cell_style = ParagraphStyle('HdrCell', parent=styles['Normal'], fontSize=9, leading=11, alignment=1, textColor=colors.white, fontName='Helvetica-Bold')
            cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10, alignment=1)
            time_style = ParagraphStyle('TimeCell', parent=styles['Normal'], fontSize=8, leading=10, alignment=1, fontName='Helvetica-Bold', textColor=colors.HexColor('#1E293B'))

            elements = []
            elements.append(Paragraph(inst_name, title_style))
            elements.append(Paragraph(f"Class Timetable — {class_name} | Academic Session: {session_name}", sub_style))
            elements.append(Spacer(1, 12))

            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            table_data = [[Paragraph("Period / Timing", hdr_cell_style)] + [Paragraph(d, hdr_cell_style) for d in days]]

            for p in periods:
                p_time = f"{p.name}<br/>({p.start_time}–{p.end_time})" if (p.start_time and p.end_time) else p.name
                row = [Paragraph(p_time, time_style)]
                if p.is_break:
                    for _ in days:
                        row.append(Paragraph("<b>BREAK</b>", cell_style))
                else:
                    for d in days:
                        slot_text = "-"
                        for e in entries:
                            if e.period_id == p.id and e.day_of_week == d:
                                subj = e.academic_subject.name if e.academic_subject else "Subject"
                                teacher = e.employee.first_name if e.employee else ""
                                room = f" [{e.room.room_no}]" if getattr(e, 'room', None) else ""
                                slot_text = f"<b>{subj}</b><br/>{teacher}{room}"
                                break
                        row.append(Paragraph(slot_text, cell_style))
                table_data.append(row)

            col_widths = [120] + [98] * len(days)
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D4ED8')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(t)
            doc.build(elements)
            return True, "PDF Timetable Exported Successfully"
        except Exception as e:
            return False, f"PDF Export Error: {str(e)}"
        finally:
            db.close()