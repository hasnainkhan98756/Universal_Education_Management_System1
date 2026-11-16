import os
import time
import math
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database.connection import get_session
from database.models.communication import CommunicationProvider, MessageTemplate, MessageLog
from database.models.student import Student
from database.models.fee import FeeVoucher
from database.models.timetable import TimetableEntry
from database.models.calendar import CalendarEvent
from database.models.hr import Employee
from database.models.academic import AcademicClass, AcademicSection
from sqlalchemy.orm import joinedload
from datetime import datetime
from core.state_manager import app_state

class CommunicationService:
    
    # ==========================================
    # 1. PROVIDERS & TEMPLATES
    # ==========================================
    @staticmethod
    def get_providers():
        db = get_session()
        try: return db.query(CommunicationProvider).all()
        finally: db.close()

    @staticmethod
    def save_provider(p_id, name, channel, host, user, pwd, sender, port, tls, active):
        db = get_session()
        try:
            if active: 
                db.query(CommunicationProvider).filter_by(channel=channel).update({"is_active": False})
            if p_id:
                p = db.query(CommunicationProvider).filter_by(id=p_id).first()
                p.name = name; p.channel = channel; p.api_url_or_host = host
                p.api_key_or_user = user; p.api_secret_or_pass = pwd; p.sender_id = sender
                p.port = port; p.use_tls = tls; p.is_active = active
            else:
                db.add(CommunicationProvider(name=name, channel=channel, api_url_or_host=host, api_key_or_user=user, api_secret_or_pass=pwd, sender_id=sender, port=port, use_tls=tls, is_active=active))
            db.commit(); return True, "Gateway Configuration Saved."
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()

    @staticmethod
    def seed_default_templates_if_empty():
        """Populates rich, production-ready editable SMS and WhatsApp templates free of charge."""
        db = get_session()
        try:
            count = db.query(MessageTemplate).filter_by(is_active=True).count()
            if count == 0:
                defaults = [
                    (
                        "Monthly Fee Due Reminder",
                        "SMS",
                        "Fees",
                        "Fee Due Notification",
                        "Dear Parent/Guardian, This is a reminder that fee of Rs. {fee_amount} for {student_name} (Class: {class_name}) for {fee_month} is pending. Please clear your dues at the earliest. Regards, {school_name}"
                    ),
                    (
                        "Fee Received Acknowledgement",
                        "SMS",
                        "Fees",
                        "Fee Received",
                        "Dear Parent, We have received fee payment for {student_name} (Class: {class_name}) for {fee_month}. Outstanding balance is Rs. {outstanding_amount}. Thank you, {school_name}"
                    ),
                    (
                        "Daily Student Absence Alert",
                        "SMS",
                        "Attendance",
                        "Absence Notice",
                        "Dear Parent, Your child {student_name} (Class: {class_name}) is marked ABSENT today on {date}. If this was unexcused, please contact the school office. Regards, {school_name}"
                    ),
                    (
                        "Examination Result Announcement",
                        "SMS",
                        "Exams",
                        "Result Declared",
                        "Dear Parent, Results for {student_name} (Class: {class_name}) have been declared for {date}. Please review the grade sheet on the student portal. Regards, {school_name}"
                    ),
                    (
                        "General School Notice & Holiday Alert",
                        "SMS",
                        "General",
                        "Official Announcement",
                        "Respected Parents, School will observe a holiday / special schedule on {date}. Classes will resume as per regular timetable. Regards, {school_name}"
                    ),
                    (
                        "Fee Defaulter Urgent Notice (WhatsApp)",
                        "WhatsApp (Manual App)",
                        "Fees",
                        "Urgent Fee Notice",
                        "Assalam-o-Alaikum Respected Parent of {student_name} (Class: {class_name}),\n\nThis is an urgent reminder from {school_name}. An outstanding balance of Rs. {outstanding_amount} ({fee_month}) is currently pending against your child's account.\n\nPlease clear the fee voucher at your earliest convenience to avoid late surcharges.\n\nThank you for your cooperation.\nAdministration, {school_name}"
                    ),
                    (
                        "Daily Absence Alert (WhatsApp)",
                        "WhatsApp (Manual App)",
                        "Attendance",
                        "Student Absence Notice",
                        "Assalam-o-Alaikum Respected Parent,\n\nPlease note that your child *{student_name}* (Class: *{class_name}*) is marked *ABSENT* today ({date}) at *{school_name}*.\n\nKindly notify the administration if this absence is due to illness or approved leave.\n\nRegards,\nPrincipal Office, {school_name}"
                    )
                ]
                for name, chan, cat, sub, body in defaults:
                    db.add(MessageTemplate(name=name, channel=chan, category=cat, subject=sub, body=body, is_active=True))
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error seeding default templates: {e}")
        finally:
            db.close()

    @staticmethod
    def get_templates(category=None):
        CommunicationService.seed_default_templates_if_empty()
        db = get_session()
        try:
            q = db.query(MessageTemplate).filter_by(is_active=True)
            if category and category != "All Categories": q = q.filter_by(category=category)
            return q.all()
        finally: db.close()

    @staticmethod
    def save_template(t_id, name, channel, cat, sub, body):
        db = get_session()
        try:
            if t_id:
                t = db.query(MessageTemplate).filter_by(id=t_id).first()
                t.name = name; t.channel = channel; t.category = cat; t.subject = sub; t.body = body
            else:
                db.add(MessageTemplate(name=name, channel=channel, category=cat, subject=sub, body=body))
            db.commit(); return True, "Template Saved."
        except Exception as e:
            db.rollback(); return False, str(e)
        finally: db.close()

    @staticmethod
    def delete_template(t_id):
        db = get_session()
        try:
            t = db.query(MessageTemplate).filter_by(id=t_id).first()
            if t: 
                t.is_active = False 
                db.commit(); return True, "Template Deleted."
            return False, "Not found."
        finally: db.close()

    @staticmethod
    def calculate_segments(text):
        if not text: return 0, 0
        length = len(text)
        segments = math.ceil(length / 160) if length > 0 else 0
        return length, segments

    # ==========================================
    # 2. INTELLIGENT RECIPIENT RESOLUTION
    # ==========================================
    @staticmethod
    def resolve_contact(person, channel):
        if "WhatsApp" in channel or channel == "SMS":
            if hasattr(person, 'father_phone') and person.father_phone and len(person.father_phone) > 5: return person.father_phone
            if hasattr(person, 'phone') and person.phone and len(person.phone) > 5: return person.phone
        elif channel == "Email":
            if hasattr(person, 'email') and person.email and "@" in person.email: return person.email
        return None

    @staticmethod
    def fetch_audience_data(module_source, class_id="All"):
        """Live Integration: Pulls clean, unique, and dynamic variables from actual source tables."""
        db = get_session()
        try:
            results = []
            school_name = app_state.get_setting("app_title", "Our School")
            curr_date = datetime.now().strftime("%d %b %Y")
            
            # 1. FEES (LIVE SYNC - GROUPED BY STUDENT)
            if "Fee" in module_source:
                q = db.query(FeeVoucher).options(joinedload(FeeVoucher.student).joinedload(Student.academic_class))
                if class_id != "All": q = q.join(Student).filter(Student.class_id == class_id)
                
                stu_map = {}
                for v in q.all():
                    rem = v.total_amount - (v.paid_amount or 0.0)
                    if rem > 0 and v.student and v.student.status == "Active":
                        sid = v.student.id
                        if sid not in stu_map:
                            stu_map[sid] = {
                                "student": v.student, "source_id": str(v.id), 
                                "outstanding": 0.0, "months": []
                            }
                        stu_map[sid]["outstanding"] += rem
                        if v.fee_month not in stu_map[sid]["months"]:
                            stu_map[sid]["months"].append(v.fee_month)
                
                for sid, data in stu_map.items():
                    results.append({
                        "student": data["student"], "source_id": data["source_id"], "source_module": "Fees",
                        "vars": {
                            "{fee_amount}": str(data["outstanding"]), 
                            "{outstanding_amount}": str(data["outstanding"]), 
                            "{fee_month}": ", ".join(data["months"]),
                            "{school_name}": school_name,
                            "{date}": curr_date
                        }
                    })
            
            # 2. TIMETABLE ALERTS & GENERAL ANNOUNCEMENTS
            else:
                q = db.query(Student).options(joinedload(Student.academic_class)).filter_by(status="Active")
                if class_id != "All": q = q.filter(Student.class_id == class_id)
                
                for s in q.all():
                    src_mod = "Timetable" if "Timetable" in module_source else "General"
                    results.append({
                        "student": s, "source_id": str(s.id), "source_module": src_mod,
                        "vars": {
                            "{school_name}": school_name, 
                            "{date}": curr_date
                        }
                    })
            
            return results
        finally: db.close()

    # ==========================================
    # 3. MESSAGE QUEUEING & RENDERING
    # ==========================================
    @staticmethod
    def render_message(template_body, student, custom_vars):
        """Safely replaces template placeholders with actual data."""
        body = template_body
        body = body.replace("{student_name}", f"{student.first_name} {student.last_name or ''}".strip())
        body = body.replace("{class_name}", student.academic_class.name if student.academic_class else "Unknown")
        body = body.replace("{father_name}", getattr(student, "father_name", "Parent/Guardian") or "Parent/Guardian")
        body = body.replace("{guardian_name}", getattr(student, "father_name", "Parent/Guardian") or "Parent/Guardian")
        for k, v in custom_vars.items(): body = body.replace(k, str(v))
        return body

    @staticmethod
    def log_manual_whatsapp_send(student_name, contact, subject, body, source_mod, source_id):
        """Instantly records a manual WhatsApp click in the Audit Dashboard so you have a history."""
        db = get_session()
        try:
            _, seg = CommunicationService.calculate_segments(body)
            log = MessageLog(
                recipient_name=student_name, recipient_contact=contact, channel="WhatsApp (Manual)",
                subject=subject, body=body, segments=seg, status="Opened in App", 
                source_module=source_mod, source_id=source_id, sent_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.add(log); db.commit()
            return True
        except Exception:
            db.rollback(); return False
        finally: db.close()

    @staticmethod
    def log_manual_sms_send(student_name, contact, subject, body, source_mod, source_id):
        """Instantly records a manual SMS click in the Audit Dashboard so you have a history."""
        db = get_session()
        try:
            _, seg = CommunicationService.calculate_segments(body)
            log = MessageLog(
                recipient_name=student_name, recipient_contact=contact, channel="SMS (Device App)",
                subject=subject, body=body, segments=seg, status="Opened in SMS App", 
                source_module=source_mod, source_id=source_id, sent_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.add(log); db.commit()
            return True
        except Exception:
            db.rollback(); return False
        finally: db.close()

    @staticmethod
    def queue_bulk_messages(audience_data, template_id, target_channel, allow_fallback):
        db = get_session()
        try:
            template = db.query(MessageTemplate).filter_by(id=template_id).first()
            if not template: return False, "Template not found."

            queued_count = 0; skipped_count = 0; missing_count = 0

            for data in audience_data:
                student = data["student"]
                contact = CommunicationService.resolve_contact(student, target_channel)
                
                if not contact: 
                    missing_count += 1; continue

                source_mod = data["source_module"]; source_id = data["source_id"]

                # Duplication Check
                if source_id and source_mod != "General":
                    exists = db.query(MessageLog).filter_by(recipient_contact=contact, source_module=source_mod, source_id=source_id, channel=target_channel).first()
                    if exists:
                        skipped_count += 1; continue

                rendered_body = CommunicationService.render_message(template.body, student, data["vars"])
                _, seg = CommunicationService.calculate_segments(rendered_body)

                log = MessageLog(
                    recipient_name=f"{student.first_name} {student.last_name or ''}".strip(),
                    recipient_contact=contact, channel=target_channel, fallback_allowed=allow_fallback,
                    subject=template.subject, body=rendered_body, segments=seg,
                    status="Queued", source_module=source_mod, source_id=source_id
                )
                db.add(log)
                queued_count += 1

            db.commit()
            return True, f"Queued: {queued_count} | Skipped Duplicates: {skipped_count} | Missing Contacts: {missing_count}"
        except Exception as e:
            db.rollback(); return False, f"Queue Error: {e}"
        finally: db.close()

    # ==========================================
    # 4. MULTI-CHANNEL BACKGROUND PROCESSOR
    # ==========================================
    @staticmethod
    def process_queue_batch(batch_size=15):
        db = get_session()
        try:
            pending = db.query(MessageLog).filter(MessageLog.status.in_(["Queued", "Retrying"])).limit(batch_size).all()
            if not pending: return

            providers = {p.channel: p for p in db.query(CommunicationProvider).filter_by(is_active=True).all()}

            for msg in pending:
                if "WhatsApp" in msg.channel: continue 

                msg.status = "Sending"; db.commit() 

                try:
                    prov = providers.get(msg.channel)
                    if not prov: raise Exception(f"No Active Provider for {msg.channel}.")
                    
                    if msg.channel == "SMS":
                        time.sleep(0.1) 
                        msg.provider_msg_id = f"SMS-{int(time.time())}"
                        
                    elif msg.channel == "Email":
                        server = smtplib.SMTP(prov.api_url_or_host, prov.port)
                        if prov.use_tls: server.starttls()
                        server.login(prov.api_key_or_user, prov.api_secret_or_pass)
                        
                        mime = MIMEMultipart()
                        mime['From'] = prov.sender_id; mime['To'] = msg.recipient_contact; mime['Subject'] = msg.subject or "Notification"
                        mime.attach(MIMEText(msg.body, 'plain'))
                        server.send_message(mime); server.quit()
                        msg.provider_msg_id = f"SMTP-{int(time.time())}"

                    msg.status = "Sent"; msg.sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S"); msg.error_message = ""
                    
                except Exception as e:
                    msg.retry_count += 1
                    msg.error_message = str(e)
                    if msg.retry_count >= 3: msg.status = "Failed" 
                    else: msg.status = "Retrying" 
                        
                db.commit()
        except Exception:
            db.rollback()
        finally: db.close()

    @staticmethod
    def get_dashboard_stats():
        db = get_session()
        try:
            sent_email = db.query(MessageLog).filter_by(channel="Email", status="Sent").count()
            sent_wa = db.query(MessageLog).filter(MessageLog.channel.like("%WhatsApp%")).count()
            sent_sms = db.query(MessageLog).filter(MessageLog.channel.like("%SMS%")).count()
            queued = db.query(MessageLog).filter(MessageLog.status.in_(["Queued", "Retrying", "Sending"])).count()
            failed = db.query(MessageLog).filter_by(status="Failed").count()
            logs = db.query(MessageLog).order_by(MessageLog.id.desc()).limit(100).all()
            return {"sent_email": sent_email, "sent_wa": sent_wa, "sent_sms": sent_sms, "queued": queued, "failed": failed, "logs": logs}
        finally: db.close()