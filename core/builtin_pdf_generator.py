import os
import urllib.request
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.units import inch, mm

from core.document_service import DocumentService

class BuiltinPDFGenerator:
    """
    Enterprise-grade built-in ReportLab PDF Engine.
    Generates publication-quality A4 documents and ID badges with dynamic institution
    branding, double navy borders, centered faded watermark, elegant typography,
    structured tables, and signature blocks.
    """

    @classmethod
    def get_institution_info(cls):
        logo_setting = DocumentService.get_setting("logo_path", "")
        if not (logo_setting and os.path.exists(logo_setting)):
            for candidate in [
                r"C:\Users\Nain\Desktop\images.jpg",
                os.path.join(os.getcwd(), "assets", "logo.png"),
                os.path.join(os.getcwd(), "assets", "logo.jpg")
            ]:
                if os.path.exists(candidate):
                    logo_setting = candidate
                    break

        return {
            "name": DocumentService.get_setting("name", "UNIVERSITY PUBLIC SCHOOL AND COLLEGE MARDAN"),
            "tagline": DocumentService.get_setting("tagline", "Excellence in Education"),
            "address": DocumentService.get_setting("address", "Opposite AWKUM Garden Campus, Toru Road, Mardan"),
            "phone": DocumentService.get_setting("phone", "0937-548800 | 03009035036 | 03149645245"),
            "email": DocumentService.get_setting("email", "info@upscm.edu.pk"),
            "website": DocumentService.get_setting("website", "www.upscm.edu.pk"),
            "logo_path": logo_setting
        }

    @classmethod
    def create_page_decorator(cls, inst_info, page_type="a4"):
        """
        Creates a canvas callback that draws:
          1. Double navy border around the document perimeter
          2. Bottom running contact footer (on A4 pages)
          3. Faint institution crest watermark in the exact center of each page
        """
        def decorator(canvas, doc):
            canvas.saveState()
            w, h = doc.pagesize

            # 1. Double Navy Border
            if page_type == "idcard":
                canvas.setStrokeColor(colors.HexColor('#1E3A8A'))
                canvas.setLineWidth(1.2)
                canvas.rect(5, 5, w - 10, h - 10)
                canvas.setLineWidth(0.5)
                canvas.rect(7, 7, w - 14, h - 14)
            else:
                canvas.setStrokeColor(colors.HexColor('#1E3A8A'))
                canvas.setLineWidth(1.5)
                canvas.rect(18, 18, w - 36, h - 36)
                canvas.setLineWidth(0.5)
                canvas.rect(21, 21, w - 42, h - 42)

                # Bottom running contact footer on A4
                parts = []
                if inst_info.get("name"): parts.append(inst_info["name"].upper())
                if inst_info.get("address"): parts.append(inst_info["address"])
                if inst_info.get("phone"): parts.append(f"Contact: {inst_info['phone']}")
                footer_str = " | ".join(parts) if parts else "UNIVERSAL EDUCATION MANAGEMENT SYSTEM"
                canvas.setFont("Helvetica", 6.8)
                canvas.setFillColor(colors.HexColor('#64748B'))
                canvas.drawCentredString(w / 2.0, 26, footer_str[:130])

            # 2. Centered Faded Watermark in Page Middle
            logo_path = inst_info.get("logo_path")
            if logo_path and os.path.exists(logo_path):
                try:
                    canvas.setFillAlpha(0.08)
                    wm_size = 210 if page_type != "idcard" else 75
                    wm_x = (w - wm_size) / 2.0
                    wm_y = (h - wm_size) / 2.0
                    canvas.drawImage(logo_path, wm_x, wm_y, width=wm_size, height=wm_size, mask='auto', preserveAspectRatio=True)
                except Exception:
                    pass

            canvas.restoreState()

        return decorator

    @classmethod
    def build_header(cls, inst_info, title=None):
        elements = []
        styles = getSampleStyleSheet()

        inst_name_style = ParagraphStyle(
            'InstNameH',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1
        )
        sub_style = ParagraphStyle(
            'InstSubH',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#374151'),
            alignment=1
        )
        contact_style = ParagraphStyle(
            'InstContactH',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#4B5563'),
            alignment=1
        )
        title_style = ParagraphStyle(
            'DocTitleH',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12.5,
            leading=15,
            textColor=colors.HexColor('#1E3A8A'),
            alignment=1
        )

        logo_path = inst_info.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=44, height=44)
                logo_img.hAlign = 'CENTER'
                elements.append(logo_img)
                elements.append(Spacer(1, 2))
            except Exception:
                pass

        elements.append(Paragraph(inst_info.get("name", "UNIVERSAL EDUCATION SYSTEM").upper(), inst_name_style))
        if inst_info.get("address"):
            elements.append(Spacer(1, 2))
            elements.append(Paragraph(inst_info["address"], sub_style))

        contact_parts = []
        if inst_info.get("phone"): contact_parts.append(f"Contact: {inst_info['phone']}")
        if inst_info.get("email"): contact_parts.append(inst_info["email"])
        if contact_parts:
            elements.append(Spacer(1, 2))
            elements.append(Paragraph(" | ".join(contact_parts), contact_style))

        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#1E3A8A'), spaceBefore=2, spaceAfter=6))

        if title:
            elements.append(Paragraph(title.upper(), title_style))
            elements.append(Spacer(1, 8))

        return elements

    @classmethod
    def build_footer(cls, footer_note=""):
        elements = []
        styles = getSampleStyleSheet()
        sig_style = ParagraphStyle(
            'SigStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            alignment=1
        )
        note_style = ParagraphStyle(
            'NoteStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#6B7280'),
            alignment=1
        )

        elements.append(Spacer(1, 20))
        sig_data = [
            [
                Paragraph("__________________________<br/><b>Prepared / Checked By</b>", sig_style),
                Paragraph("__________________________<br/><b>Accountant / Cashier</b>", sig_style),
                Paragraph("__________________________<br/><b>Principal / Authorized</b>", sig_style)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[175, 175, 175])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(sig_table)
        elements.append(Spacer(1, 8))

        if not footer_note:
            footer_note = DocumentService.get_setting("receipt_footer_note", "This is an official computer-generated document.")
        elements.append(Paragraph(footer_note, note_style))
        return elements

    @classmethod
    def _val(cls, data_dict, k, default="-"):
        if not data_dict:
            return default

        candidates = [k]
        k_clean = str(k).lower().strip().replace(".", "_")

        # Specific high-priority semantic aliases
        if any(x in k_clean for x in ["student_name", "student", "full_name"]) and "photo" not in k_clean:
            candidates.extend(["student_name", "student.name", "name", "full_name", "student.full_name", "student_full_name", "student.student_name"])
        if "father" in k_clean:
            candidates.extend(["father_name", "parent.father_name", "father", "parent.father", "student.father_name", "father_full_name", "guardian_name", "parent.guardian_name"])
        if "mother" in k_clean:
            candidates.extend(["mother_name", "parent.mother_name", "mother", "parent.mother"])
        if any(x in k_clean for x in ["photo", "picture", "image"]):
            candidates.extend(["student_photo", "student.photo", "photo", "photo_path", "student.photo_path", "picture", "student_picture", "image"])
        if "roll" in k_clean:
            candidates.extend(["roll_no", "roll_number", "student.roll_number", "student.roll_no", "student_id", "student.student_id"])
        if "class" in k_clean and "section" not in k_clean:
            candidates.extend(["class", "academic.class", "class_name", "apply_class", "allotted_class"])
        if "section" in k_clean:
            candidates.extend(["section", "academic.section", "section_name", "apply_section"])
        if "b_form" in k_clean or "cnic" in k_clean:
            candidates.extend(["b_form", "student.b_form", "cnic", "student.cnic", "bform"])
        if "session" in k_clean:
            candidates.extend(["academic_session", "academic.session", "session", "academic_year"])
        if "date" in k_clean:
            candidates.extend(["date", "date_of_issue", "document.date_of_issue", "issue_date"])

        # Generic namespace variants
        candidates.extend([
            f"student.{k}", f"parent.{k}", f"academic.{k}", f"fee.{k}", f"document.{k}", f"admission.{k}",
            k.replace("student.", ""), k.replace("parent.", ""), k.replace("academic.", ""), k.replace("document.", "")
        ])

        for cand in candidates:
            if cand in data_dict and data_dict[cand] is not None and str(data_dict[cand]).strip() != "":
                return str(data_dict[cand]).strip()
        return default

    @classmethod
    def resolve_image_path(cls, path_or_url):
        """
        Resolves local path or cloud URL (e.g. AWS S3, Cloudinary, HTTP/HTTPS).
        If URL, downloads and caches to avoid repetitive latency and ensure offline resilience.
        """
        if not path_or_url:
            return None
        path_str = str(path_or_url).strip()
        if not path_str:
            return None

        # If already exists locally
        if os.path.exists(path_str) and os.path.isfile(path_str):
            return path_str

        # If remote cloud URL (S3, HTTP, HTTPS)
        if path_str.lower().startswith(("http://", "https://")):
            try:
                cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_data", "cache", "cloud_media")
                os.makedirs(cache_dir, exist_ok=True)
                url_hash = hashlib.md5(path_str.encode("utf-8")).hexdigest()
                ext = os.path.splitext(path_str.split("?")[0])[1] or ".jpg"
                if ext.lower() not in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
                    ext = ".jpg"
                cache_file = os.path.join(cache_dir, f"{url_hash}{ext}")

                if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
                    return cache_file

                req = urllib.request.Request(path_str, headers={"User-Agent": "UniversalEducationSystem/2.0"})
                with urllib.request.urlopen(req, timeout=8) as response, open(cache_file, "wb") as out_f:
                    out_f.write(response.read())

                if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
                    return cache_file
            except Exception:
                pass
        return None

    @classmethod
    def resolve_photo_flowable(cls, data_dict, width=80, height=95):
        """
        Extracts student or staff photo, resolves local/remote media, and returns
        a Flowable Image with strict aspect ratio preservation (no distortion/stretching).
        """
        styles = getSampleStyleSheet()
        raw_photo = cls._val(data_dict, "photo", cls._val(data_dict, "student_photo", cls._val(data_dict, "employee.photo", "")))
        resolved = cls.resolve_image_path(raw_photo)

        if resolved and os.path.exists(resolved):
            try:
                # ReportLab Image with keepAspectRatio preserves aspect ratio cleanly
                img = Image(resolved, width=width, height=height, kind='proportional')
                return img
            except Exception:
                pass

        # Elegant fallback box
        fallback_style = ParagraphStyle(
            'PhFallback',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            alignment=1,
            textColor=colors.HexColor('#94A3B8')
        )
        t_fallback = Table([[Paragraph("<br/><br/>OFFICIAL<br/>PHOTOGRAPH", fallback_style)]], colWidths=[width], rowHeights=[height])
        t_fallback.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        return t_fallback

    @classmethod
    def generate(cls, document_type, data_dict, output_path):
        """Dispatches generation according to document type."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc_type_clean = str(document_type).strip().lower()

        try:
            # 1. Specialized Certificates & Staff Letters
            if "bonafide" in doc_type_clean:
                return cls.generate_bonafide_certificate(data_dict, output_path)
            elif "merit" in doc_type_clean or "academic excellence" in doc_type_clean:
                return cls.generate_merit_certificate(data_dict, output_path)
            elif "attendance" in doc_type_clean and "cert" in doc_type_clean:
                return cls.generate_attendance_certificate(data_dict, output_path)
            elif "sports" in doc_type_clean or "extra-curricular" in doc_type_clean or "curricular" in doc_type_clean:
                return cls.generate_sports_certificate(data_dict, output_path)
            elif "experience" in doc_type_clean:
                return cls.generate_experience_certificate(data_dict, output_path)
            elif "appointment" in doc_type_clean:
                return cls.generate_appointment_letter(data_dict, output_path)
            elif "salary" in doc_type_clean and ("cert" in doc_type_clean or "income" in doc_type_clean):
                return cls.generate_salary_certificate(data_dict, output_path)
            elif "relieving" in doc_type_clean:
                return cls.generate_relieving_letter(data_dict, output_path)
            elif "appreciation" in doc_type_clean:
                return cls.generate_appreciation_certificate(data_dict, output_path)
            elif "fee structure" in doc_type_clean or "no dues" in doc_type_clean:
                return cls.generate_fee_structure_certificate(data_dict, output_path)

            # 2. Existing Primary Documents
            elif "leaving" in doc_type_clean or "slc" in doc_type_clean or "transfer" in doc_type_clean:
                return cls.generate_school_leaving_certificate(data_dict, output_path)
            elif "character" in doc_type_clean:
                return cls.generate_character_certificate(data_dict, output_path)
            elif "english" in doc_type_clean:
                return cls.generate_english_proficiency_certificate(data_dict, output_path)
            elif "transcript" in doc_type_clean or "dmc" in doc_type_clean or "result" in doc_type_clean or "mark sheet" in doc_type_clean:
                return cls.generate_academic_transcript(data_dict, output_path)
            elif "id card" in doc_type_clean or "identity card" in doc_type_clean or "student card" in doc_type_clean:
                return cls.generate_student_id_card(data_dict, output_path)
            elif "admission" in doc_type_clean:
                return cls.generate_admission_form(data_dict, output_path)
            elif "thermal" in doc_type_clean and ("fee" in doc_type_clean or "receipt" in doc_type_clean):
                return cls.generate_thermal_fee_receipt(data_dict, output_path)
            elif "thermal" in doc_type_clean and ("salary" in doc_type_clean or "payroll" in doc_type_clean):
                return cls.generate_thermal_salary_slip(data_dict, output_path)
            elif "receipt" in doc_type_clean:
                # Check paper size setting: if POS Thermal Receipt is chosen as default, render thermal
                paper_setting = DocumentService.get_setting("paper_size", "A4 Size (Standard)")
                if "thermal" in paper_setting.lower() or "pos" in paper_setting.lower() or "80mm" in paper_setting.lower():
                    return cls.generate_thermal_fee_receipt(data_dict, output_path)
                return cls.generate_fee_receipt(data_dict, output_path)
            elif "voucher" in doc_type_clean or "challan" in doc_type_clean:
                return cls.generate_fee_voucher(data_dict, output_path)
            elif "salary" in doc_type_clean or "payroll" in doc_type_clean:
                paper_setting = DocumentService.get_setting("paper_size", "A4 Size (Standard)")
                if "thermal" in paper_setting.lower() or "pos" in paper_setting.lower() or "80mm" in paper_setting.lower():
                    return cls.generate_thermal_salary_slip(data_dict, output_path)
                return cls.generate_salary_slip(data_dict, output_path)
            elif "exam" in doc_type_clean or "admit" in doc_type_clean or "roll no" in doc_type_clean or "slip" in doc_type_clean:
                return cls.generate_exam_admit_card(data_dict, output_path)
            elif "certificate" in doc_type_clean:
                return cls.generate_certificate(document_type, data_dict, output_path)
            else:
                return cls.generate_generic_document(document_type, data_dict, output_path)
        except Exception as e:
            return False, f"ReportLab Engine Error: {str(e)}"

    # ──────────────────────────────────────────────────────────────────────────
    # 0. SCHOOL LEAVING / TRANSFER CERTIFICATE (Publication Quality)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_school_leaving_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('SlcLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('SlcVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('SlcValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('SlcBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=16, textColor=colors.HexColor('#1E293B'))
        th_s = ParagraphStyle('SlcTh', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))

        elements.extend(cls.build_header(inst_info, "SCHOOL LEAVING CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "SLC-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        dob = cls._val(data_dict, "dob", cls._val(data_dict, "date_of_birth", "-"))
        b_form = cls._val(data_dict, "b_form", "-")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", cls._val(data_dict, "apply_class", "-"))
        sec_name = cls._val(data_dict, "section", cls._val(data_dict, "apply_section", "-"))
        roll_no = cls._val(data_dict, "roll_no", adm_no)
        session_val = cls._val(data_dict, "academic_session", cls._val(data_dict, "last_academic_session", "2025-2026"))

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Date of Birth:", lbl_s), Paragraph(dob, val_s),
             Paragraph("B-Form / Reg No.:", lbl_s), Paragraph(b_form, val_s)],
            [Paragraph("Admission No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class & Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s)],
            [Paragraph("Roll No.:", lbl_s), Paragraph(roll_no, val_s),
             Paragraph("Academic Session:", lbl_s), Paragraph(session_val, val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[105, 155, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 10))

        cert_intro = f"""
        This is to certify that <b>{stu_name}</b>, son/daughter of <b>{father_name}</b>, has been a bona fide 
        student of <b>{inst_info.get('name', 'Universal Education System')}</b>. The verified official records of the 
        student at the time of leaving the institution are certified as under:
        """
        elements.append(Paragraph(cert_intro, body_s))
        elements.append(Spacer(1, 8))

        # Academic & Clearance Particulars Table
        adm_date = cls._val(data_dict, "admission_date", "-")
        leaving_date = cls._val(data_dict, "date_of_leaving", cls._val(data_dict, "leaving_date", datetime.now().strftime("%d-%m-%Y")))
        class_leaving = cls._val(data_dict, "class_at_time_of_leaving", cls_name)
        reason_leaving = cls._val(data_dict, "reason_for_leaving", "Completion of Academic Studies / Relocation")
        perf_val = cls._val(data_dict, "academic_performance", "Satisfactory / Passed & Promoted")
        conduct_val = cls._val(data_dict, "conduct", "Exemplary")
        purpose_val = cls._val(data_dict, "purpose", "Further Studies & College Admission")

        particulars = [
            [Paragraph("<b>SR.</b>", th_s), Paragraph("<b>PARTICULAR / SPECIFICATION</b>", th_s), Paragraph("<b>OFFICIAL RECORD & VERIFICATION</b>", th_s)],
            [Paragraph("1", val_s), Paragraph("Date of Student's Admission:", lbl_s), Paragraph(adm_date, val_s)],
            [Paragraph("2", val_s), Paragraph("Class in Which First Admitted:", lbl_s), Paragraph(cls._val(data_dict, "initial_class", cls_name), val_s)],
            [Paragraph("3", val_s), Paragraph("Class at the Time of Leaving:", lbl_s), Paragraph(f"<b>{class_leaving}</b>", val_b)],
            [Paragraph("4", val_s), Paragraph("Date of Withdrawal / Leaving:", lbl_s), Paragraph(f"<b>{leaving_date}</b>", val_b)],
            [Paragraph("5", val_s), Paragraph("Medium of Instruction:", lbl_s), Paragraph("<b>English</b> (Entire curriculum conducted in English)", val_s)],
            [Paragraph("6", val_s), Paragraph("Academic Performance & Exam Result:", lbl_s), Paragraph(f"<b>{perf_val}</b>", val_b)],
            [Paragraph("7", val_s), Paragraph("Moral Character & General Conduct:", lbl_s), Paragraph(f"<b>{conduct_val}</b>", val_b)],
            [Paragraph("8", val_s), Paragraph("Attendance & Punctuality:", lbl_s), Paragraph("<b>Regular & Punctual (94.2% Attendance)</b>", val_s)],
            [Paragraph("9", val_s), Paragraph("Institutional Dues Clearance:", lbl_s), Paragraph("<font color='#059669'><b>ALL DUES PAID IN FULL UP TO DATE OF LEAVING</b></font>", val_b)],
            [Paragraph("10", val_s), Paragraph("Reason for Leaving Institution:", lbl_s), Paragraph(f"<i>{reason_leaving}</i>", val_s)],
            [Paragraph("11", val_s), Paragraph("Purpose for Issuance:", lbl_s), Paragraph(purpose_val, val_s)],
        ]
        t_part = Table(particulars, colWidths=[30, 210, 283])
        t_part.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_part)
        elements.append(Spacer(1, 10))

        cert_outro = """
        To the best of our knowledge and according to the institutional record, there is nothing on record against him/her. 
        He/she bears an unblemished character and is hereby cleared to seek admission in any recognized institution. 
        We wish him/her success in all future academic pursuits.
        """
        elements.append(Paragraph(cert_outro, body_s))
        elements.append(Spacer(1, 16))

        # Bottom Signatures & Seal
        sig_box = ParagraphStyle('SigSlc', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, alignment=1)
        seal_box = ParagraphStyle('SealSlc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Class Teacher Signature</b>", sig_box),
                Paragraph("__________________________<br/><b>Accountant (Dues Verified)</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL SCHOOL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal Signature</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[130, 130, 133, 130])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (2, 0), (2, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "School Leaving Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 1. CHARACTER CERTIFICATE (Matching Official Template)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_character_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('ChLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('ChVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('ChValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('ChBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "CHARACTER CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document_number", "CC-2026-0001"))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y")))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        dob = cls._val(data_dict, "dob", cls._val(data_dict, "date_of_birth", "-"))
        b_form = cls._val(data_dict, "b_form", "-")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", cls._val(data_dict, "apply_class", "-"))
        sec_name = cls._val(data_dict, "section", cls._val(data_dict, "apply_section", "-"))
        roll_no = cls._val(data_dict, "roll_no", adm_no)

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Date of Birth:", lbl_s), Paragraph(dob, val_s),
             Paragraph("B-Form / Reg No.:", lbl_s), Paragraph(b_form, val_s)],
            [Paragraph("Admission No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class / Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s)],
            [Paragraph("Roll No.:", lbl_s), Paragraph(roll_no, val_s),
             Paragraph("Academic Session:", lbl_s), Paragraph(cls._val(data_dict, "academic_session", "2025-2026"), val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[105, 155, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        conduct_val = cls._val(data_dict, "conduct", cls._val(data_dict, "character", "Good & Satisfactory"))
        purpose_val = cls._val(data_dict, "purpose", "Further Education & Academic Pursuits")

        cert_text = f"""
        This is to certify that <b>{stu_name}</b>, son/daughter of <b>{father_name}</b>, was a bona fide student 
        of <b>{inst_info.get('name', 'Universal Education System')}</b>.<br/><br/>
        During his/her period of study at this institution, his/her character, conduct, discipline, and behavior 
        were found to be <b>{conduct_val}</b>.<br/><br/>
        To the best of our knowledge, there is nothing on record that would render him/her unsuitable for further 
        education, employment, or other lawful pursuits.<br/><br/>
        This certificate is issued at the request of the student/parent/guardian for the purpose of <b>{purpose_val}</b>.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 14))

        # Particular Assessment Table
        ass_head = ParagraphStyle('AssH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        ass_data = [
            [Paragraph("<b>PARTICULAR</b>", ass_head), Paragraph("<b>ASSESSMENT</b>", ass_head)],
            [Paragraph("Character", val_s), Paragraph(cls._val(data_dict, "character", "Excellent"), val_b)],
            [Paragraph("Conduct", val_s), Paragraph(cls._val(data_dict, "conduct", "Exemplary"), val_b)],
            [Paragraph("Discipline", val_s), Paragraph(cls._val(data_dict, "discipline", "Very Good"), val_b)],
            [Paragraph("Attendance", val_s), Paragraph(cls._val(data_dict, "attendance", "Regular (94%)"), val_b)],
            [Paragraph("General Behavior", val_s), Paragraph(cls._val(data_dict, "general_behavior", "Polite, Respectful & Cooperative"), val_b)]
        ]
        t_ass = Table(ass_data, colWidths=[200, 323])
        t_ass.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_ass)
        elements.append(Spacer(1, 24))

        # Bottom Signatures
        sig_box = ParagraphStyle('SigB', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Class Teacher Signature</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL SCHOOL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal Signature</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Character Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 2. ENGLISH PROFICIENCY CERTIFICATE (Matching Official Template)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_english_proficiency_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('EnLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('EnVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('EnValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('EnBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=16, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "ENGLISH PROFICIENCY CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document_number", "ENG-2026-0001"))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y")))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        dob = cls._val(data_dict, "dob", cls._val(data_dict, "date_of_birth", "-"))
        b_form = cls._val(data_dict, "b_form", "-")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", cls._val(data_dict, "apply_class", "-"))
        sec_name = cls._val(data_dict, "section", cls._val(data_dict, "apply_section", "-"))
        roll_no = cls._val(data_dict, "roll_no", adm_no)

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Date of Birth:", lbl_s), Paragraph(dob, val_s),
             Paragraph("B-Form / Reg No.:", lbl_s), Paragraph(b_form, val_s)],
            [Paragraph("Admission No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class / Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s)],
            [Paragraph("Roll No.:", lbl_s), Paragraph(roll_no, val_s),
             Paragraph("Academic Session:", lbl_s), Paragraph(cls._val(data_dict, "academic_session", "2025-2026"), val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[105, 155, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 12))

        overall_prof = cls._val(data_dict, "overall_english_proficiency", "Proficient")

        cert_text = f"""
        This is to certify that <b>{stu_name}</b>, son/daughter of <b>{father_name}</b>, was a student 
        of <b>{inst_info.get('name', 'Universal Education System')}</b>.<br/><br/>
        Based on the student's academic performance, classroom participation, written and oral communication, 
        and demonstrated use of the English language during the period of study, the student's overall proficiency 
        in English was assessed as <b>{overall_prof}</b>.<br/><br/>
        The student demonstrated proficiency in the following areas:
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 10))

        # Skills Table
        ass_head = ParagraphStyle('AssH2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        skills_data = [
            [Paragraph("<b>ENGLISH LANGUAGE SKILLS</b>", ass_head), Paragraph("<b>PROFICIENCY LEVEL</b>", ass_head)],
            [Paragraph("Listening", val_s), Paragraph(cls._val(data_dict, "listening_level", "Excellent / C1"), val_b)],
            [Paragraph("Speaking", val_s), Paragraph(cls._val(data_dict, "speaking_level", "Fluent & Confident"), val_b)],
            [Paragraph("Reading", val_s), Paragraph(cls._val(data_dict, "reading_level", "Advanced"), val_b)],
            [Paragraph("Writing", val_s), Paragraph(cls._val(data_dict, "writing_level", "Competent & Structured"), val_b)],
            [Paragraph("Grammar", val_s), Paragraph(cls._val(data_dict, "grammar_level", "Proficient"), val_b)],
            [Paragraph("Vocabulary", val_s), Paragraph(cls._val(data_dict, "vocabulary_level", "Extensive"), val_b)],
        ]
        t_skills = Table(skills_data, colWidths=[200, 323])
        t_skills.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_skills)
        elements.append(Spacer(1, 10))

        # Summary Checklist & Details
        medium_inst = cls._val(data_dict, "medium_of_instruction", "English")
        overall_lvl = cls._val(data_dict, "overall_level", "Upper-Intermediate")

        lvl_boxes = []
        for opt in ["Beginner", "Elementary", "Intermediate", "Upper-Intermediate", "Advanced"]:
            mark = "[X]" if opt.lower() in overall_lvl.lower() else "[  ]"
            lvl_boxes.append(f"{mark} {opt}")
        boxes_str = "    ".join(lvl_boxes)

        summary_rows = [
            [Paragraph("<b>Overall English Proficiency:</b>", lbl_s), Paragraph(f"<b>{overall_prof}</b>", val_b)],
            [Paragraph("<b>Medium of Instruction:</b>", lbl_s), Paragraph(f"<b>{medium_inst}</b> (All academic curriculum taught in English)", val_s)],
            [Paragraph("<b>Overall Level:</b>", lbl_s), Paragraph(f"<b>{boxes_str}</b>", val_s)],
        ]
        t_summary = Table(summary_rows, colWidths=[150, 373])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 20))

        # Signatures
        sig_box = ParagraphStyle('SigB2', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealB2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Class Teacher Signature</b>", sig_box),
                Paragraph("__________________________<br/><b>Controller of Exams</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL SCHOOL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal Signature</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[130, 130, 133, 130])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (2, 0), (2, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "English Proficiency Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 3. OFFICIAL ACADEMIC TRANSCRIPT (Matching Official Template)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_academic_transcript(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('TrLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('TrVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('TrValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#0F172A'))
        th_s = ParagraphStyle('TrTh', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#FFFFFF'), alignment=1)

        elements.extend(cls.build_header(inst_info, "OFFICIAL ACADEMIC TRANSCRIPT"))

        serial_no = cls._val(data_dict, "serial_no", cls._val(data_dict, "document.number", "TRANS-2026-0001"))
        issue_date = cls._val(data_dict, "issue_date", cls._val(data_dict, "document.date_of_issue", datetime.now().strftime("%d-%m-%Y")))
        stu_name = cls._val(data_dict, "student_name", "Student Name")
        father_name = cls._val(data_dict, "father_name", "Father Name")
        dob = cls._val(data_dict, "dob", "-")
        adm_no = cls._val(data_dict, "admission_no", "-")
        exam_title = cls._val(data_dict, "exam_title", "Annual Examination 2026")
        session_val = cls._val(data_dict, "academic_session", "2025-2026")
        roll_no = cls._val(data_dict, "roll_no", adm_no)
        cls_name = cls._val(data_dict, "class", "-")
        sec_name = cls._val(data_dict, "section", "-")

        meta_rows = [
            [Paragraph("Serial No.:", lbl_s), Paragraph(f"<b>{serial_no}</b>", val_b),
             Paragraph("Issue Date:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Date of Birth:", lbl_s), Paragraph(dob, val_s),
             Paragraph("Admission No.:", lbl_s), Paragraph(adm_no, val_s)],
            [Paragraph("Examination:", lbl_s), Paragraph(f"<b>{exam_title}</b>", val_b),
             Paragraph("Session:", lbl_s), Paragraph(session_val, val_s)],
            [Paragraph("Roll No:", lbl_s), Paragraph(f"<b>{roll_no}</b>", val_b),
             Paragraph("Class / Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[100, 160, 100, 163])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 8))

        # Subjects Table
        marks_data = [
            [Paragraph("SR.", th_s), Paragraph("SUBJECTS", th_s), Paragraph("MAX MARKS", th_s),
             Paragraph("MIN MARKS", th_s), Paragraph("MARKS OBTAINED", th_s), Paragraph("GRADE", th_s), Paragraph("REMARKS", th_s)]
        ]

        # Extract subject records if available
        sub_list = []
        if "subjects" in data_dict and isinstance(data_dict["subjects"], list):
            sub_list = data_dict["subjects"]
        else:
            default_subjects = [
                ("English Literature & Comp.", 100, 40, 88, "A", "Excellent"),
                ("Mathematics", 100, 40, 92, "A1", "Outstanding"),
                ("General Science", 100, 40, 85, "A", "Very Good"),
                ("Urdu Literature", 100, 40, 82, "A", "Good"),
                ("Islamiyat / Ethics", 50, 20, 46, "A1", "Excellent"),
                ("Pakistan Studies / Social", 50, 20, 44, "A", "Good"),
                ("Computer Science", 100, 40, 94, "A1", "Outstanding"),
            ]
            for s, mx, mn, ob, gr, rem in default_subjects:
                sub_list.append({"name": s, "max": mx, "min": mn, "obtained": ob, "grade": gr, "remarks": rem})

        tot_max, tot_min, tot_obt = 0, 0, 0
        for idx, sub in enumerate(sub_list, 1):
            s_name = sub.get("name") or sub.get("title") or f"Subject {idx}"
            s_max = float(sub.get("max") or sub.get("total_marks") or 100)
            s_min = float(sub.get("min") or sub.get("passing_marks") or (s_max * 0.4))
            s_obt = float(sub.get("obtained") or sub.get("obtained_marks") or 0)
            s_grd = sub.get("grade") or ("A1" if s_obt >= s_max * 0.9 else "A" if s_obt >= s_max * 0.8 else "B" if s_obt >= s_max * 0.7 else "C" if s_obt >= s_max * 0.6 else "D" if s_obt >= s_max * 0.5 else "F")
            s_rem = sub.get("remarks") or ("Pass" if s_obt >= s_min else "Fail")

            tot_max += s_max
            tot_min += s_min
            tot_obt += s_obt

            marks_data.append([
                Paragraph(str(idx), val_s),
                Paragraph(s_name, val_b),
                Paragraph(f"{s_max:.0f}", val_s),
                Paragraph(f"{s_min:.0f}", val_s),
                Paragraph(f"<b>{s_obt:.0f}</b>", val_b),
                Paragraph(f"<b>{s_grd}</b>", val_b),
                Paragraph(s_rem, val_s),
            ])

        # Grand Total Row
        pct = (tot_obt / tot_max * 100) if tot_max > 0 else 0
        ov_grd = "A1" if pct >= 90 else "A" if pct >= 80 else "B" if pct >= 70 else "C" if pct >= 60 else "D" if pct >= 50 else "F"
        marks_data.append([
            Paragraph("", val_s),
            Paragraph("<b>GRAND TOTAL</b>", val_b),
            Paragraph(f"<b>{tot_max:.0f}</b>", val_b),
            Paragraph(f"<b>{tot_min:.0f}</b>", val_b),
            Paragraph(f"<b>{tot_obt:.0f}</b>", ParagraphStyle('TotObt', parent=val_b, textColor=colors.HexColor('#059669'))),
            Paragraph(f"<b>{ov_grd}</b>", ParagraphStyle('TotGrd', parent=val_b, textColor=colors.HexColor('#1E3A8A'))),
            Paragraph("<b>PASSED</b>", ParagraphStyle('TotPass', parent=val_b, textColor=colors.HexColor('#059669'))),
        ])

        t_marks = Table(marks_data, colWidths=[28, 185, 60, 60, 70, 50, 70])
        t_marks.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (5, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 3.5),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
        ]))
        elements.append(t_marks)
        elements.append(Spacer(1, 8))

        # Side-by-Side: Performance Summary (Left) & Grading Scale (Right)
        sum_rows = [
            [Paragraph("<b>PERFORMANCE SUMMARY</b>", lbl_s), Paragraph("", lbl_s)],
            [Paragraph("Total Marks:", val_s), Paragraph(f"<b>{tot_max:.0f}</b>", val_b)],
            [Paragraph("Marks Obtained:", val_s), Paragraph(f"<b>{tot_obt:.0f}</b>", val_b)],
            [Paragraph("Percentage:", val_s), Paragraph(f"<b>{pct:.1f}%</b>", val_b)],
            [Paragraph("Overall Grade:", val_s), Paragraph(f"<b>{ov_grd}</b>", val_b)],
            [Paragraph("Attendance:", val_s), Paragraph("<b>93.5%</b>", val_s)],
            [Paragraph("Final Result / Status:", lbl_s), Paragraph("<font color='#059669'><b>PASSED / PROMOTED</b></font>", val_b)]
        ]
        t_sum = Table(sum_rows, colWidths=[120, 130])
        t_sum.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))

        scale_rows = [
            [Paragraph("<b>Grading Scale</b>", lbl_s), Paragraph("<b>Percentage</b>", lbl_s), Paragraph("<b>Remarks</b>", lbl_s)],
            [Paragraph("A1", val_b), Paragraph("90% - 100%", val_s), Paragraph("Outstanding", val_s)],
            [Paragraph("A", val_b), Paragraph("80% - 89%", val_s), Paragraph("Excellent", val_s)],
            [Paragraph("B", val_b), Paragraph("70% - 79%", val_s), Paragraph("Very Good", val_s)],
            [Paragraph("C", val_b), Paragraph("60% - 69%", val_s), Paragraph("Good", val_s)],
            [Paragraph("D", val_b), Paragraph("50% - 59%", val_s), Paragraph("Satisfactory", val_s)],
            [Paragraph("F", val_b), Paragraph("Below 50%", val_s), Paragraph("Fail", val_s)],
        ]
        t_scale = Table(scale_rows, colWidths=[55, 95, 103])
        t_scale.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))

        combo_table = Table([[t_sum, t_scale]], colWidths=[260, 263])
        combo_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(combo_table)
        elements.append(Spacer(1, 16))

        # Bottom Signatures & Seal
        sig_box = ParagraphStyle('SigTr', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, alignment=1)
        seal_box = ParagraphStyle('SealTr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Class Teacher Signature</b>", sig_box),
                Paragraph("__________________________<br/><b>Controller of Exams</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL SCHOOL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal Signature</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[130, 130, 133, 130])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (2, 0), (2, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Academic Transcript generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 4. STUDENT ID CARD (Front & Back - Matching Official Template)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_student_id_card(cls, data_dict, output_path):
        # Standard CR-80 Landscape Dimensions (85.6mm x 54mm = 242.65pt x 153.07pt)
        id_size = (242.65, 153.07)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=id_size,
            leftMargin=7,
            rightMargin=7,
            topMargin=6,
            bottomMargin=6
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "idcard")
        styles = getSampleStyleSheet()

        inst_name_s = ParagraphStyle('IdName', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.2, leading=8.5, textColor=colors.HexColor('#1E3A8A'), alignment=1)
        inst_sub_s = ParagraphStyle('IdSub', parent=styles['Normal'], fontName='Helvetica', fontSize=4.8, leading=6, textColor=colors.HexColor('#64748B'), alignment=1)
        bar_s = ParagraphStyle('IdBar', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=5.8, leading=7, textColor=colors.HexColor('#FFFFFF'), alignment=1)
        
        name_b = ParagraphStyle('IdStuName', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, leading=8.5, textColor=colors.HexColor('#0F172A'))
        lbl_s = ParagraphStyle('IdLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=5.5, leading=7, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('IdVal', parent=styles['Normal'], fontName='Helvetica', fontSize=5.5, leading=7, textColor=colors.HexColor('#334155'))
        val_b = ParagraphStyle('IdValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=5.5, leading=7, textColor=colors.HexColor('#0F172A'))
        foot_s = ParagraphStyle('IdFoot', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=4.5, leading=5.5, textColor=colors.HexColor('#FFFFFF'), alignment=1)

        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name")).upper()
        father_name = cls._val(data_dict, "father_name", "-")
        cls_name = cls._val(data_dict, "class", cls._val(data_dict, "apply_class", "-"))
        sec_name = cls._val(data_dict, "section", cls._val(data_dict, "apply_section", "-"))
        roll_no = cls._val(data_dict, "roll_no", "-")
        stu_id = cls._val(data_dict, "student_id", roll_no)
        inst_phone = inst_info.get("phone", "03119228389")

        # ── PAGE 1: FRONT SIDE ──
        elements.append(Paragraph(inst_info.get("name", "UNIVERSITY PUBLIC SCHOOL AND COLLEGE").upper(), inst_name_s))
        sub_contact = f"{inst_info.get('address', 'Mardan')} &bull; Ph: {inst_phone}"
        elements.append(Paragraph(sub_contact, inst_sub_s))
        elements.append(Spacer(1, 2))

        # Navy Ribbon Bar
        ribbon = Table([[Paragraph("S T U D E N T &nbsp;&nbsp; I D E N T I T Y &nbsp;&nbsp; C A R D", bar_s)]], colWidths=[228])
        ribbon.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1E3A8A')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(ribbon)
        elements.append(Spacer(1, 2.5))

        # Photo handling
        photo_flowable = None
        raw_photo = cls._val(data_dict, "student_photo", "")
        resolved_photo = cls.resolve_image_path(raw_photo)
        if resolved_photo and os.path.exists(resolved_photo) and os.path.isfile(resolved_photo):
            try:
                photo_flowable = Image(resolved_photo, width=54, height=58)
            except Exception:
                photo_flowable = None
        if not photo_flowable:
            photo_flowable = Paragraph("<br/><br/><b>STUDENT<br/>PHOTO</b>", ParagraphStyle('PhBox', parent=styles['Normal'], fontSize=5.5, leading=7, alignment=1, textColor=colors.HexColor('#94A3B8')))

        details_rows = [
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", name_b)],
            [Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Class & Sec:", lbl_s), Paragraph(f"Class {cls_name} - {sec_name}", val_s)],
            [Paragraph("Roll Number:", lbl_s), Paragraph(f"<b>{roll_no}</b>", val_b)],
            [Paragraph("Student ID:", lbl_s), Paragraph(f"<b>{stu_id}</b>", val_b)],
        ]
        t_details = Table(details_rows, colWidths=[60, 104])
        t_details.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 0.8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        t_photo = Table([[photo_flowable]], colWidths=[58], rowHeights=[58])
        t_photo.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))

        t_front_body = Table([[t_details, t_photo]], colWidths=[166, 62])
        t_front_body.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(t_front_body)
        elements.append(Spacer(1, 2))

        inst_short = inst_info.get("name", "UPSCM")[:22].upper()
        strip_table = Table([[Paragraph(f"OFFICIAL STUDENT IDENTIFICATION &bull; PROPERTY OF {inst_short}", foot_s)]], colWidths=[228])
        strip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0F172A')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ]))
        elements.append(strip_table)

        # ── PAGE 2: BACK SIDE ──
        elements.append(PageBreak())

        elements.append(Paragraph(inst_info.get("name", "UNIVERSITY PUBLIC SCHOOL AND COLLEGE").upper(), inst_name_s))
        back_sub = f"Helpline: {inst_phone} &bull; {inst_info.get('email', 'admin@school.edu')}"
        elements.append(Paragraph(back_sub, inst_sub_s))
        elements.append(Spacer(1, 2))

        rules_p = Paragraph(
            "<b>TERMS & INSTRUCTIONS:</b><br/>"
            "1. This card is non-transferable and must be worn during school hours.<br/>"
            "2. If found, please return to the school administration office.",
            ParagraphStyle('Rules', parent=styles['Normal'], fontName='Helvetica', fontSize=4.8, leading=6, textColor=colors.HexColor('#334155'))
        )
        t_rules = Table([[rules_p]], colWidths=[228])
        t_rules.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_rules)
        elements.append(Spacer(1, 2))

        issue_d = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", datetime.now().strftime("%Y-%m-%d")))
        valid_until = cls._val(data_dict, "valid_until", "31-03-2027")
        em_contact = cls._val(data_dict, "emergency_contact", cls._val(data_dict, "emergency_contact_number", cls._val(data_dict, "phone", "-")))
        blood_grp = cls._val(data_dict, "blood_group", "-")
        parent_g = cls._val(data_dict, "guardian_name", father_name)

        back_details = [
            [Paragraph("Date of Issue:", lbl_s), Paragraph(issue_d, val_s)],
            [Paragraph("Valid Until:", lbl_s), Paragraph(f"<b>{valid_until}</b>", val_b)],
            [Paragraph("Blood Group:", lbl_s), Paragraph(f"<font color='#DC2626'><b>{blood_grp}</b></font>", val_b)],
            [Paragraph("Emergency Contact:", lbl_s), Paragraph(em_contact, val_s)],
            [Paragraph("Parent / Guardian:", lbl_s), Paragraph(parent_g, val_s)],
        ]
        t_back_det = Table(back_details, colWidths=[66, 86])
        t_back_det.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 0.8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        seal_sign = [
            [Paragraph("OFFICIAL<br/>SCHOOL SEAL", ParagraphStyle('SealMini', parent=styles['Normal'], fontSize=5, leading=6, textColor=colors.HexColor('#94A3B8'), alignment=1))],
            [Paragraph("___________________<br/><b>Authorized Sign</b>", ParagraphStyle('AuthS', parent=styles['Normal'], fontSize=4.8, leading=6, alignment=1, textColor=colors.HexColor('#1E3A8A')))]
        ]
        t_seal_sign = Table(seal_sign, colWidths=[72], rowHeights=[30, 24])
        t_seal_sign.setStyle(TableStyle([
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F8FAFC')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 1),
        ]))

        t_back_body = Table([[t_back_det, t_seal_sign]], colWidths=[154, 74])
        t_back_body.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(t_back_body)
        elements.append(Spacer(1, 2))

        ret_addr = f"RETURN ADDRESS: {inst_info.get('address', 'CAMPUS OFFICE')[:50].upper()}"
        back_strip = Table([[Paragraph(ret_addr, foot_s)]], colWidths=[228])
        back_strip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1E3A8A')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
        ]))
        elements.append(back_strip)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Student ID Card generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 5. ADMISSION APPLICATION FORM (Balanced 3-Page Institutional Dossier)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_admission_form(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=30,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('AdmLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('AdmVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('AdmValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        sec_h = ParagraphStyle('AdmSecH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1E3A8A'))
        rule_s = ParagraphStyle('AdmRule', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10.5, textColor=colors.HexColor('#1E293B'))

        app_no = cls._val(data_dict, "application_no", "ADM-2026-0001")
        session_val = cls._val(data_dict, "academic_session", "2025-2026")
        adm_date = cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))

        # ══════════════════════════════════════════════════════════════════════
        # PAGE 1: STUDENT BIODATA, PARENT PARTICULARS & ADMISSION DETAILS
        # ══════════════════════════════════════════════════════════════════════
        elements.extend(cls.build_header(inst_info, "ADMISSION APPLICATION FORM"))

        meta_p1 = [
            [Paragraph("Academic Session:", lbl_s), Paragraph(f"<b>{session_val}</b>", val_b),
             Paragraph("Application / Reg No.:", lbl_s), Paragraph(f"<b>{app_no}</b>", val_b),
             Paragraph("Submission Date:", lbl_s), Paragraph(f"<b>{adm_date}</b>", val_b)]
        ]
        t_meta_p1 = Table(meta_p1, colWidths=[90, 85, 95, 95, 80, 78])
        t_meta_p1.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta_p1)
        elements.append(Spacer(1, 8))

        # Photo Flowable with strict file verification
        photo_flowable = None
        photo_candidates = ["student_photo", "student.photo", "photo", "photo_path", "picture", "image"]
        photo_path = ""
        for pc in photo_candidates:
            pv = cls._val(data_dict, pc, "")
            if pv and os.path.exists(pv) and os.path.isfile(pv):
                photo_path = pv
                break

        if photo_path:
            try:
                photo_flowable = Image(photo_path, width=78, height=96)
            except Exception:
                photo_flowable = None

        if not photo_flowable:
            photo_flowable = Paragraph(
                "<br/><br/>AFFIX RECENT<br/>PASSPORT-SIZE<br/>PHOTOGRAPH<br/>HERE",
                ParagraphStyle('PhAdm1', parent=styles['Normal'], fontSize=6.5, leading=9, alignment=1, textColor=colors.HexColor('#94A3B8'))
            )

        # 1. Student Information Table
        elements.append(Paragraph("1. STUDENT IDENTIFICATION & BIODATA", sec_h))
        elements.append(Spacer(1, 3))

        gender_val = cls._val(data_dict, "gender", "Male")
        g_male = "[X]" if "male" in gender_val.lower() and "female" not in gender_val.lower() else "[  ]"
        g_female = "[X]" if "female" in gender_val.lower() else "[  ]"

        stu_rows = [
            [Paragraph("Student's Full Name:", lbl_s), Paragraph(f"<b>{cls._val(data_dict, 'student_name')}</b>", val_b),
             Paragraph("Date of Birth:", lbl_s), Paragraph(cls._val(data_dict, 'dob'), val_s)],
            [Paragraph("Gender:", lbl_s), Paragraph(f"{g_male} Male &nbsp;&nbsp; {g_female} Female", val_s),
             Paragraph("B-Form / CRC No.:", lbl_s), Paragraph(cls._val(data_dict, 'b_form'), val_b)],
            [Paragraph("Nationality:", lbl_s), Paragraph(cls._val(data_dict, 'nationality', 'Pakistani'), val_s),
             Paragraph("Religion:", lbl_s), Paragraph(cls._val(data_dict, 'religion', 'Islam'), val_s)],
            [Paragraph("Blood Group:", lbl_s), Paragraph(cls._val(data_dict, 'blood_group'), val_s),
             Paragraph("Place of Birth:", lbl_s), Paragraph(cls._val(data_dict, 'place_of_birth', '-'), val_s)],
        ]
        t_stu = Table(stu_rows, colWidths=[110, 115, 100, 115])
        t_stu.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))

        combo_s1 = [[t_stu, photo_flowable]]
        t_combo_s1 = Table(combo_s1, colWidths=[440, 83])
        t_combo_s1.setStyle(TableStyle([
            ('BOX', (1, 0), (1, 0), 0.75, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(t_combo_s1)
        elements.append(Spacer(1, 8))

        # 2. Parent / Guardian Information
        elements.append(Paragraph("2. PARENT & GUARDIAN PARTICULARS", sec_h))
        elements.append(Spacer(1, 3))
        parent_rows = [
            [Paragraph("Father's Full Name:", lbl_s), Paragraph(cls._val(data_dict, 'father_name'), val_b),
             Paragraph("Father's CNIC:", lbl_s), Paragraph(cls._val(data_dict, 'father_cnic'), val_b)],
            [Paragraph("Mother's Name:", lbl_s), Paragraph(cls._val(data_dict, 'mother_name'), val_s),
             Paragraph("Mother's CNIC:", lbl_s), Paragraph(cls._val(data_dict, 'mother_cnic'), val_s)],
            [Paragraph("Guardian Name (if any):", lbl_s), Paragraph(cls._val(data_dict, 'guardian_name'), val_s),
             Paragraph("Guardian Relationship:", lbl_s), Paragraph(cls._val(data_dict, 'relationship', '-'), val_s)],
            [Paragraph("Guardian Occupation:", lbl_s), Paragraph(cls._val(data_dict, 'occupation', '-'), val_s),
             Paragraph("Monthly Family Income:", lbl_s), Paragraph(cls._val(data_dict, 'monthly_income', '-'), val_s)],
        ]
        t_parent = Table(parent_rows, colWidths=[130, 131, 130, 132])
        t_parent.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_parent)
        elements.append(Spacer(1, 8))

        # 3. Contact Information
        elements.append(Paragraph("3. RESIDENTIAL & CONTACT DETAILS", sec_h))
        elements.append(Spacer(1, 3))
        contact_rows = [
            [Paragraph("Residential Address:", lbl_s), Paragraph(cls._val(data_dict, 'address'), val_s),
             Paragraph("City:", lbl_s), Paragraph(cls._val(data_dict, 'city', 'Mardan'), val_s)],
            [Paragraph("District:", lbl_s), Paragraph(cls._val(data_dict, 'district', 'Mardan'), val_s),
             Paragraph("Primary Mobile (Parent):", lbl_s), Paragraph(cls._val(data_dict, 'mobile_no'), val_b)],
            [Paragraph("Alternative Phone No.:", lbl_s), Paragraph(cls._val(data_dict, 'alt_contact'), val_s),
             Paragraph("Official Email Address:", lbl_s), Paragraph(cls._val(data_dict, 'email'), val_s)],
        ]
        t_contact = Table(contact_rows, colWidths=[130, 131, 130, 132])
        t_contact.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_contact)
        elements.append(Spacer(1, 8))

        # 4. Admission Details
        elements.append(Paragraph("4. ADMISSION CLASSIFICATION & PROGRAM ENROLLMENT", sec_h))
        elements.append(Spacer(1, 3))
        adm_type_val = cls._val(data_dict, 'admission_type', 'New Admission')
        t_new = "[X]" if "new" in adm_type_val.lower() else "[  ]"
        t_trf = "[X]" if "trans" in adm_type_val.lower() else "[  ]"
        t_read = "[X]" if "re-" in adm_type_val.lower() else "[  ]"

        adm_det_rows = [
            [Paragraph("Applying for Class:", lbl_s), Paragraph(f"<b>{cls._val(data_dict, 'apply_class')}</b>", val_b),
             Paragraph("Section Allotted:", lbl_s), Paragraph(cls._val(data_dict, 'apply_section'), val_b)],
            [Paragraph("Admission Type:", lbl_s), Paragraph(f"{t_new} New &nbsp; {t_trf} Transfer &nbsp; {t_read} Re-Admission", val_s),
             Paragraph("Previous School:", lbl_s), Paragraph(cls._val(data_dict, 'prev_school'), val_s)],
            [Paragraph("Previous Class Passed:", lbl_s), Paragraph(cls._val(data_dict, 'prev_class'), val_s),
             Paragraph("Previous School Address:", lbl_s), Paragraph(cls._val(data_dict, 'prev_school_address', '-'), val_s)],
        ]
        t_adm_det = Table(adm_det_rows, colWidths=[130, 131, 130, 132])
        t_adm_det.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_adm_det)

        # ══════════════════════════════════════════════════════════════════════
        # PAGE 2: ACADEMIC RECORD, SIBLINGS, MEDICAL, CHECKLIST & UNDERTAKING
        # ══════════════════════════════════════════════════════════════════════
        elements.append(PageBreak())
        elements.extend(cls.build_header(inst_info, "ADMISSION APPLICATION FORM — PAGE 2 OF 3"))

        # 5. Previous Academic Record
        elements.append(Paragraph("5. PREVIOUS ACADEMIC & INSTITUTIONAL RECORD", sec_h))
        elements.append(Spacer(1, 3))
        prev_acad = [
            [Paragraph("<b>Examination / Level</b>", lbl_s), Paragraph("<b>School / Board</b>", lbl_s), Paragraph("<b>Academic Session</b>", lbl_s), Paragraph("<b>Result / Marks / Grade</b>", lbl_s)],
            [Paragraph(cls._val(data_dict, 'prev_class', 'Previous Grade'), val_s),
             Paragraph(cls._val(data_dict, 'prev_class_school', cls._val(data_dict, 'prev_school')), val_s),
             Paragraph(cls._val(data_dict, 'prev_class_session', '2024-2025'), val_s),
             Paragraph(cls._val(data_dict, 'prev_class_grade', '-'), val_b)],
            [Paragraph("Board / Final Examination", val_s),
             Paragraph(cls._val(data_dict, 'prev_exam_school', cls._val(data_dict, 'prev_school')), val_s),
             Paragraph(cls._val(data_dict, 'prev_exam_session', '2024-2025'), val_s),
             Paragraph(cls._val(data_dict, 'prev_exam_grade', '-'), val_b)],
            [Paragraph("Transfer Certificate No.:", lbl_s), Paragraph(cls._val(data_dict, 'transfer_cert_no'), val_s),
             Paragraph("TC Date of Issue:", lbl_s), Paragraph(cls._val(data_dict, 'transfer_cert_date'), val_s)]
        ]
        t_prev = Table(prev_acad, colWidths=[130, 163, 110, 120])
        t_prev.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_prev)
        elements.append(Spacer(1, 8))

        # 6. Sibling Information (Authoritative Binding)
        elements.append(Paragraph("6. SIBLING ENROLLMENT PARTICULARS", sec_h))
        elements.append(Spacer(1, 3))

        sib_studying = cls._val(data_dict, 'sibling_studying', 'No')
        is_sib = "yes" in sib_studying.lower()
        s_chk_yes = "[X]" if is_sib else "[  ]"
        s_chk_no = "[  ]" if is_sib else "[X]"
        s_name = cls._val(data_dict, 'sibling_name', '-') if is_sib else "None"
        s_cls = cls._val(data_dict, 'sibling_class', '-') if is_sib else "None"
        s_roll = cls._val(data_dict, 'sibling_roll', '-') if is_sib else "None"

        sib_rows = [
            [Paragraph("Does applicant have any sibling currently studying here?", lbl_s),
             Paragraph(f"{s_chk_yes} Yes &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {s_chk_no} No", val_b),
             Paragraph("Sibling System Roll/ID:", lbl_s), Paragraph(s_roll, val_b)],
            [Paragraph("Sibling Full Name:", lbl_s), Paragraph(s_name, val_b),
             Paragraph("Sibling Class & Section:", lbl_s), Paragraph(s_cls, val_b)],
        ]
        t_sib = Table(sib_rows, colWidths=[140, 121, 130, 132])
        t_sib.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sib)
        elements.append(Spacer(1, 8))

        # 7. Medical & Emergency Information
        elements.append(Paragraph("7. MEDICAL & EMERGENCY NOTIFICATION", sec_h))
        elements.append(Spacer(1, 3))
        med_rows = [
            [Paragraph("Emergency Contact Person:", lbl_s), Paragraph(cls._val(data_dict, 'emergency_person'), val_b),
             Paragraph("Relationship:", lbl_s), Paragraph(cls._val(data_dict, 'emergency_relationship'), val_s)],
            [Paragraph("Emergency Contact Number:", lbl_s), Paragraph(cls._val(data_dict, 'emergency_contact'), val_b),
             Paragraph("Medical Conditions / Allergies:", lbl_s), Paragraph(cls._val(data_dict, 'medical_info', 'None recorded'), val_s)],
        ]
        t_med = Table(med_rows, colWidths=[130, 131, 130, 132])
        t_med.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_med)
        elements.append(Spacer(1, 8))

        # 8. Documents Checklist Table
        elements.append(Paragraph("8. VERIFIED DOCUMENTS CHECKLIST", sec_h))
        elements.append(Spacer(1, 3))
        chk_data = [
            [Paragraph("<b>Document Description</b>", lbl_s), Paragraph("<b>Verification Status</b>", lbl_s),
             Paragraph("<b>Document Description</b>", lbl_s), Paragraph("<b>Verification Status</b>", lbl_s)],
            [Paragraph("Student B-Form / Birth Certificate", val_s), Paragraph("[X] Verified Copy Attached", val_b),
             Paragraph("Previous School Result Card", val_s), Paragraph("[X] Verified Copy Attached", val_b)],
            [Paragraph("Father / Guardian CNIC Copy", val_s), Paragraph("[X] Verified Copy Attached", val_b),
             Paragraph("Transfer Certificate (Original)", val_s), Paragraph("[X] Verified & Stamped", val_b)],
            [Paragraph("Recent Passport-Size Photos (4)", val_s), Paragraph("[X] Attached & Received", val_b),
             Paragraph("Character Certificate (Original)", val_s), Paragraph("[X] Verified on Record", val_b)],
        ]
        t_chk = Table(chk_data, colWidths=[150, 111, 150, 112])
        t_chk.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_chk)
        elements.append(Spacer(1, 8))

        # 9. Declaration by Parent / Guardian
        elements.append(Paragraph("9. STATUTORY UNDERTAKING & DECLARATION BY PARENT / GUARDIAN", sec_h))
        elements.append(Spacer(1, 3))
        dec_text = f"""
        I hereby solemnly declare that all particulars entered in this Application Form are true, correct, and complete to the best of my knowledge and belief. 
        I agree to strictly abide by the rules, code of discipline, academic standards, uniform code, and fee schedules established by 
        <b>{inst_info.get('name', 'Universal Education System')}</b>. I acknowledge that fees once paid are non-refundable and I undertake to clear 
        all recurring educational dues on or before the due date. The administration reserves full right to cancel admission in case of fraudulent records.
        """
        elements.append(Paragraph(dec_text, rule_s))
        elements.append(Spacer(1, 8))

        dec_sig_rows = [
            [
                Paragraph(f"Parent/Guardian Name: <b>{cls._val(data_dict, 'declaration_parent_name', cls._val(data_dict, 'father_name'))}</b>", val_s),
                Paragraph("Parent/Guardian Signature: _______________________", val_s),
                Paragraph(f"Date: <b>{cls._val(data_dict, 'declaration_date', adm_date)}</b>", val_s)
            ]
        ]
        t_dec_sig = Table(dec_sig_rows, colWidths=[200, 223, 100])
        t_dec_sig.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_dec_sig)

        # ══════════════════════════════════════════════════════════════════════
        # PAGE 3: OFFICIAL ADMINISTRATIVE SCRUTINY, FEE SCHEDULE & AUTHORIZATION
        # ══════════════════════════════════════════════════════════════════════
        elements.append(PageBreak())
        elements.extend(cls.build_header(inst_info, "ADMISSION APPLICATION FORM — PAGE 3 OF 3"))

        elements.append(Paragraph("10. ADMINISTRATIVE SCRUTINY & ENROLLMENT DECISION", sec_h))
        elements.append(Spacer(1, 3))

        adm_status_raw = cls._val(data_dict, "admission_fee_status", "Pending")
        adm_fee_num = cls._val(data_dict, "admission_fee", "0")
        billing_cycle_val = cls._val(data_dict, "billing_cycle", "Monthly Fee")

        if "paid" in adm_status_raw.lower():
            adm_badge = "<font color='#059669'><b>[PAID IN FULL — CLEARED AT ADMISSION ENROLLMENT]</b></font>"
        else:
            adm_badge = "<font color='#DC2626'><b>[PENDING — BILLED ON INITIAL ADMISSION VOUCHER]</b></font>"

        office_data = [
            [Paragraph("Admission Assessment / Test:", lbl_s), Paragraph("[  ] Required &nbsp;&nbsp; [X] Exempted / Passed", val_b),
             Paragraph("Evaluation Grade / Merit:", lbl_s), Paragraph("Eligible / Standard Merit", val_b)],
            [Paragraph("Enrollment Status Decision:", lbl_s), Paragraph("<font color='#059669'><b>[X] Approved & Enrolled</b></font>", val_b),
             Paragraph("Allotted Class & Section:", lbl_s), Paragraph(f"<b>{cls._val(data_dict, 'apply_class')} - {cls._val(data_dict, 'apply_section')}</b>", val_b)],
            [Paragraph("Permanent Student System ID:", lbl_s), Paragraph(f"<b>{cls._val(data_dict, 'roll_no')}</b>", val_b),
             Paragraph("Institutional Admission No.:", lbl_s), Paragraph(f"<b>{app_no}</b>", val_b)],
        ]
        t_office = Table(office_data, colWidths=[140, 121, 130, 132])
        t_office.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_office)
        elements.append(Spacer(1, 8))

        # 11. Official Fee Structure & Clearance Table
        elements.append(Paragraph("11. APPROVED FEE STRUCTURE & BILLING SCHEDULE", sec_h))
        elements.append(Spacer(1, 3))
        fee_rows = [
            [Paragraph("Selected Fee Plan / Cycle:", lbl_s), Paragraph(f"<b>{billing_cycle_val}</b>", val_b),
             Paragraph("Initial Voucher Reference:", lbl_s), Paragraph(f"<b>VOUCH-{app_no}</b>", val_b)],
            [Paragraph("One-Time Admission Fee:", lbl_s), Paragraph(f"<b>Rs. {adm_fee_num}</b>", val_b),
             Paragraph("Admission Fee Clearance:", lbl_s), Paragraph(adm_badge, val_b)],
            [Paragraph("Base Monthly Tuition Rate:", lbl_s), Paragraph(f"Rs. {cls._val(data_dict, 'monthly_fee', '0')}", val_s),
             Paragraph("Approved Monthly Discount:", lbl_s), Paragraph(f"Rs. {cls._val(data_dict, 'discount', '0')}", val_s)],
            [Paragraph("6-Month Package Rate:", lbl_s), Paragraph(f"Rs. {cls._val(data_dict, 'six_month_fee', '0')}", val_s),
             Paragraph("Annual Package Rate:", lbl_s), Paragraph(f"Rs. {cls._val(data_dict, 'annual_fee', '0')}", val_s)],
        ]
        t_fees = Table(fee_rows, colWidths=[140, 121, 130, 132])
        t_fees.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_fees)
        elements.append(Spacer(1, 8))

        # 12. Institutional Rules & Attendance Undertaking
        elements.append(Paragraph("12. INSTITUTIONAL CODE, ATTENDANCE & EXAMINATION POLICIES", sec_h))
        elements.append(Spacer(1, 3))
        policy_text = f"""
        <b>1. Attendance Requirement:</b> A minimum of 75% attendance in each academic term is strictly mandatory for eligibility in term exams and board registrations.<br/>
        <b>2. Fee Deadlines:</b> Institutional vouchers must be honored by the designated due date. Consecutive arrears may result in temporary suspension of LMS and student portal access.<br/>
        <b>3. Code of Conduct:</b> Zero tolerance for indiscipline, vandalism, or unauthorized absenteeism. Students must uphold the dignity and values of <b>{inst_info.get('name', 'UPSCM')}</b> at all times.<br/>
        <b>4. Official Withdrawal:</b> Notice of withdrawal must be submitted at least 30 days in advance to process the School Leaving Certificate (SLC) and security refunds.
        """
        elements.append(Table([[Paragraph(policy_text, rule_s)]], colWidths=[523], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(Spacer(1, 8))

        # 13. Three-Tier Departmental Scrutiny Record
        elements.append(Paragraph("13. THREE-TIER DEPARTMENTAL CLEARANCE RECORD", sec_h))
        elements.append(Spacer(1, 3))
        scrutiny_rows = [
            [Paragraph("<b>Branch / Department</b>", lbl_s), Paragraph("<b>Verification Officer</b>", lbl_s), Paragraph("<b>Clearance Status</b>", lbl_s), Paragraph("<b>Signature & Date</b>", lbl_s)],
            [Paragraph("Academic & Enrollment Scrutiny", val_s), Paragraph("Registrar / Academic Head", val_s), Paragraph("<font color='#059669'><b>[X] Cleared</b></font>", val_b), Paragraph("___________________", val_s)],
            [Paragraph("Accounts & Finance Counter", val_s), Paragraph("Bursar / Cashier", val_s), Paragraph("<font color='#059669'><b>[X] Cleared</b></font>", val_b), Paragraph("___________________", val_s)],
            [Paragraph("Administrative Secretariat", val_s), Paragraph("Superintendent", val_s), Paragraph("<font color='#059669'><b>[X] Cleared</b></font>", val_b), Paragraph("___________________", val_s)],
        ]
        t_scrutiny = Table(scrutiny_rows, colWidths=[150, 130, 110, 133])
        t_scrutiny.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_scrutiny)
        elements.append(Spacer(1, 14))

        # 14. Final Authorization & Official Seals
        sig_box = ParagraphStyle('SigOff', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, alignment=1)
        seal_box = ParagraphStyle('SealOff', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#475569'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Admission Officer</b>", sig_box),
                Paragraph("__________________________<br/><b>Account Officer</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL EMBOSSED<br/>SCHOOL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal's Endorsement</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[130, 130, 133, 130])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (2, 0), (2, 0), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Balanced 3-Page Admission Application Form generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 6. FEE PAYMENT RECEIPT & FEE VOUCHER (With Watermark & Double Frame)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_fee_receipt(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#374151'))
        val_style = ParagraphStyle('Val', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#111827'))
        val_bold = ParagraphStyle('ValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#111827'))

        elements.extend(cls.build_header(inst_info, "OFFICIAL FEE PAYMENT RECEIPT / VOUCHER"))

        receipt_no = cls._val(data_dict, "receipt_number", cls._val(data_dict, "voucher_number", "REC-2026-0001"))
        stu_name = cls._val(data_dict, "student_name", "Student Name")
        stu_id = cls._val(data_dict, "student_id", "-")
        cls_name = cls._val(data_dict, "class", "-")
        sec_name = cls._val(data_dict, "section", "-")
        fee_month = cls._val(data_dict, "fee_month", datetime.now().strftime("%B %Y"))
        pay_date = cls._val(data_dict, "payment_date", datetime.now().strftime("%Y-%m-%d"))
        pay_method = cls._val(data_dict, "payment_method", "Cash Counter")

        meta_data = [
            [Paragraph("Receipt / Voucher No:", lbl_style), Paragraph(f"<b>{receipt_no}</b>", val_bold),
             Paragraph("Date:", lbl_style), Paragraph(str(pay_date), val_style)],
            [Paragraph("Student Name:", lbl_style), Paragraph(str(stu_name), val_bold),
             Paragraph("Student ID:", lbl_style), Paragraph(str(stu_id), val_style)],
            [Paragraph("Class / Section:", lbl_style), Paragraph(f"{cls_name} - {sec_name}", val_style),
             Paragraph("Fee Coverage Period:", lbl_style), Paragraph(str(fee_month), val_bold)],
            [Paragraph("Payment Method:", lbl_style), Paragraph(str(pay_method), val_style),
             Paragraph("Status:", lbl_style), Paragraph("<font color='#059669'><b>OFFICIAL CLEARANCE</b></font>", val_bold)]
        ]
        meta_table = Table(meta_data, colWidths=[120, 145, 115, 143])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # Items Breakdown Table
        items_data = [
            [Paragraph("<b>Fee Particulars / Category</b>", lbl_style),
             Paragraph("<b>Gross Fee (Rs)</b>", lbl_style),
             Paragraph("<b>Discount (Rs)</b>", lbl_style),
             Paragraph("<b>Net Amount Paid (Rs)</b>", lbl_style)]
        ]

        found_items = False
        for i in range(1, 15):
            cat_key = f"fee.item_{i}_category"
            if cat_key in data_dict and data_dict[cat_key]:
                found_items = True
                desc = data_dict.get(f"fee.item_{i}_description", "") or data_dict[cat_key]
                amt = data_dict.get(f"fee.item_{i}_amount", "0")
                disc = data_dict.get(f"fee.item_{i}_discount", "0")
                paid = data_dict.get(f"fee.item_{i}_paid", "0")
                items_data.append([
                    Paragraph(f"{data_dict[cat_key]} <font color='#6B7280' size='7.5'>({desc})</font>", val_style),
                    Paragraph(str(amt), val_style),
                    Paragraph(str(disc), val_style),
                    Paragraph(f"<b>{paid}</b>", val_bold)
                ])

        if not found_items:
            tot = cls._val(data_dict, "current_fee", cls._val(data_dict, "total_amount", "0"))
            disc = cls._val(data_dict, "total_discount", "0")
            paid = cls._val(data_dict, "amount_received", cls._val(data_dict, "paid_amount", tot))
            items_data.append([
                Paragraph(f"Tuition & Enrolled Billing Charges ({fee_month})", val_style),
                Paragraph(str(tot), val_style),
                Paragraph(str(disc), val_style),
                Paragraph(f"<b>{paid}</b>", val_bold)
            ])

        tot_paying = cls._val(data_dict, "amount_received", cls._val(data_dict, "paid_amount", "0"))
        tot_rem = cls._val(data_dict, "total_remaining_balance", cls._val(data_dict, "remaining_balance", "0"))

        items_data.append([
            Paragraph("<b>Total Amount Paid:</b>", ParagraphStyle('TotL', parent=lbl_style, fontSize=9.5, textColor=colors.HexColor('#059669'))),
            Paragraph("", val_style), Paragraph("", val_style),
            Paragraph(f"<b>Rs. {tot_paying}</b>", ParagraphStyle('TotV', parent=val_bold, fontSize=9.5, textColor=colors.HexColor('#059669')))
        ])
        items_data.append([
            Paragraph("<b>Remaining Dues:</b>", ParagraphStyle('RemL', parent=lbl_style, fontSize=8.5, textColor=colors.HexColor('#DC2626'))),
            Paragraph("", val_style), Paragraph("", val_style),
            Paragraph(f"<b>Rs. {tot_rem}</b>", ParagraphStyle('RemV', parent=val_bold, fontSize=8.5, textColor=colors.HexColor('#DC2626')))
        ])

        items_table = Table(items_data, colWidths=[243, 90, 90, 100])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#4F46E5')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(items_table)
        elements.extend(cls.build_footer())

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Fee Receipt / Voucher generated successfully."

    @classmethod
    def generate_fee_voucher(cls, data_dict, output_path):
        return cls.generate_fee_receipt(data_dict, output_path)

    # ──────────────────────────────────────────────────────────────────────────
    # 7. EXAMINATION ADMIT CARD / ROLL NO SLIP
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_exam_admit_card(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('AdmLbl2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#334155'))
        val_s = ParagraphStyle('AdmVal2', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('AdmValB2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))

        elements.extend(cls.build_header(inst_info, "OFFICIAL EXAMINATION ROLL NO SLIP / ADMIT CARD"))

        photo_flowable = None
        photo_path = cls._val(data_dict, "student_photo", "")
        if photo_path and os.path.exists(photo_path) and os.path.isfile(photo_path):
            try:
                photo_flowable = Image(photo_path, width=75, height=92)
            except Exception:
                photo_flowable = None
        if not photo_flowable:
            photo_flowable = Paragraph(
                "<br/><br/><b>STUDENT<br/>PHOTO</b>",
                ParagraphStyle('PhAdm2', parent=styles['Normal'], alignment=1, fontSize=7, textColor=colors.HexColor('#94A3B8'))
            )

        stu_rows = [
            [Paragraph("Candidate Name:", lbl_s), Paragraph(f"<b>{cls._val(data_dict, 'student_name')}</b>", val_b),
             Paragraph("Roll Number:", lbl_s), Paragraph(f"<b>{cls._val(data_dict, 'roll_no')}</b>", val_b)],
            [Paragraph("Father's Name:", lbl_s), Paragraph(cls._val(data_dict, 'father_name'), val_s),
             Paragraph("Class & Section:", lbl_s), Paragraph(f"{cls._val(data_dict, 'apply_class')} - {cls._val(data_dict, 'apply_section')}", val_s)],
            [Paragraph("B-Form / CNIC:", lbl_s), Paragraph(cls._val(data_dict, 'b_form'), val_s),
             Paragraph("Academic Session:", lbl_s), Paragraph(cls._val(data_dict, 'academic_session', 'Annual Session'), val_s)],
            [Paragraph("Exam Center / Room:", lbl_s), Paragraph("Main Campus Examination Hall", val_s),
             Paragraph("Admit Card Status:", lbl_s), Paragraph("<font color='#059669'><b>ELIGIBLE / APPROVED</b></font>", val_b)]
        ]
        t_stu = Table(stu_rows, colWidths=[95, 140, 95, 103])
        t_stu.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))

        combo = [[t_stu, photo_flowable]]
        t_combo = Table(combo, colWidths=[433, 90])
        t_combo.setStyle(TableStyle([
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#94A3B8')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(t_combo)
        elements.append(Spacer(1, 10))

        # Date Sheet
        elements.append(Paragraph("<b>EXAMINATION SCHEDULE & SUBJECT INVENTORY</b>", ParagraphStyle('SchT', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1E3A8A'))))
        elements.append(Spacer(1, 3))

        sched_data = [
            [Paragraph("<b>Date / Day</b>", lbl_s), Paragraph("<b>Subject Title</b>", lbl_s), Paragraph("<b>Time Slot</b>", lbl_s), Paragraph("<b>Room No</b>", lbl_s), Paragraph("<b>Invigilator Initial</b>", lbl_s)],
            [Paragraph("Day 1 (09:00 AM)", val_s), Paragraph("English Literature & Comp.", val_b), Paragraph("09:00 AM - 12:00 PM", val_s), Paragraph("Hall A", val_s), Paragraph("", val_s)],
            [Paragraph("Day 2 (09:00 AM)", val_s), Paragraph("Mathematics / Calculus", val_b), Paragraph("09:00 AM - 12:00 PM", val_s), Paragraph("Hall A", val_s), Paragraph("", val_s)],
            [Paragraph("Day 3 (09:00 AM)", val_s), Paragraph("General Science / Physics", val_b), Paragraph("09:00 AM - 12:00 PM", val_s), Paragraph("Hall A", val_s), Paragraph("", val_s)],
            [Paragraph("Day 4 (09:00 AM)", val_s), Paragraph("Urdu / Regional Language", val_b), Paragraph("09:00 AM - 12:00 PM", val_s), Paragraph("Hall A", val_s), Paragraph("", val_s)],
            [Paragraph("Day 5 (09:00 AM)", val_s), Paragraph("Islamiat / Ethics & Social Studies", val_b), Paragraph("09:00 AM - 12:00 PM", val_s), Paragraph("Hall A", val_s), Paragraph("", val_s)]
        ]
        t_sch = Table(sched_data, colWidths=[95, 160, 115, 60, 93])
        t_sch.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(t_sch)
        elements.append(Spacer(1, 8))

        inst_text = """
        <b>Important Candidate Instructions:</b><br/>
        1. Candidates must arrive at the examination hall at least 20 minutes prior to scheduled paper commencement.<br/>
        2. Carrying smart phones, watches, bags, and unauthorized study notes inside the hall is strictly prohibited.<br/>
        3. This official Admit Card must be displayed on the student desk throughout the examination duration.
        """
        elements.append(Paragraph(inst_text, ParagraphStyle('InstP', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10, textColor=colors.HexColor('#334155'))))
        elements.append(Spacer(1, 14))

        sig_data = [
            [
                Paragraph("__________________________<br/><b>Candidate Signature</b>", lbl_s),
                Paragraph("__________________________<br/><b>Class Teacher / Incharge</b>", lbl_s),
                Paragraph("__________________________<br/><b>Controller of Examinations</b>", lbl_s)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[174, 174, 175])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(sig_table)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Examination Admit Card generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 8. STAFF SALARY SLIP
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_salary_slip(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        elements.extend(cls.build_header(inst_info, "STAFF SALARY DISBURSEMENT SLIP"))

        styles = getSampleStyleSheet()
        lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#374151'))
        val_style = ParagraphStyle('Val', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#111827'))
        val_bold = ParagraphStyle('ValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#111827'))

        def _parse_num(k_list):
            for k in k_list:
                if k in data_dict and data_dict[k] is not None:
                    val_s = str(data_dict[k]).replace(",", "").replace("Rs.", "").replace("PKR", "").strip()
                    try:
                        return float(val_s)
                    except (ValueError, TypeError):
                        pass
            return 0.0

        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "-")))
        emp_id = cls._val(data_dict, "employee.emp_id", cls._val(data_dict, "employee.id", cls._val(data_dict, "employee_id", cls._val(data_dict, "emp_id", "-"))))
        desig = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "-"))
        dept = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "-"))
        sal_month = cls._val(data_dict, "payroll.month", cls._val(data_dict, "salary.month", cls._val(data_dict, "month", cls._val(data_dict, "pay_month", datetime.now().strftime("%B %Y")))))
        pay_date = cls._val(data_dict, "payroll.payment_date", cls._val(data_dict, "salary.payment_date", cls._val(data_dict, "payment_date", datetime.now().strftime("%Y-%m-%d"))))
        receipt_no = cls._val(data_dict, "payroll.receipt_no", cls._val(data_dict, "receipt_no", cls._val(data_dict, "receipt_number", "-")))

        basic = _parse_num(["payroll.basic", "salary.basic", "basic_salary", "basic"])
        allowances = _parse_num(["payroll.allowances", "salary.allowances", "allowances", "house_allowance"])
        bonus = _parse_num(["payroll.bonus", "salary.bonus", "bonus"])
        overtime = _parse_num(["payroll.overtime", "salary.overtime", "overtime"])
        gross_salary = _parse_num(["payroll.gross", "salary.gross", "gross_salary", "gross"])
        if gross_salary <= 0:
            gross_salary = basic + allowances + bonus + overtime

        deductions = _parse_num(["payroll.deductions", "salary.deductions", "deductions"])
        advance = _parse_num(["payroll.advance", "salary.advance", "advance"])
        tax = _parse_num(["payroll.tax", "salary.tax", "tax_deduction", "tax"])
        tot_deductions = deductions + advance + tax

        net_salary = _parse_num(["payroll.net_salary", "payroll.net", "salary.net", "net_salary", "net"])
        if net_salary <= 0:
            net_salary = max(0.0, gross_salary - tot_deductions)

        meta_data = [
            [Paragraph("Employee Name:", lbl_style), Paragraph(str(emp_name), val_bold),
             Paragraph("Employee ID:", lbl_style), Paragraph(str(emp_id), val_style)],
            [Paragraph("Designation:", lbl_style), Paragraph(str(desig), val_bold),
             Paragraph("Department:", lbl_style), Paragraph(str(dept), val_bold)],
            [Paragraph("Salary Month:", lbl_style), Paragraph(str(sal_month), val_bold),
             Paragraph("Disbursement Date:", lbl_style), Paragraph(str(pay_date), val_style)],
            [Paragraph("Slip / Receipt Ref:", lbl_style), Paragraph(str(receipt_no), val_style),
             Paragraph("Disbursement Status:", lbl_style), Paragraph("<font color='#059669'><b>PAID & VERIFIED</b></font>", val_bold)]
        ]
        meta_table = Table(meta_data, colWidths=[95, 175, 95, 175])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        breakup_data = [
            [Paragraph("<b>Earnings Component</b>", lbl_style), Paragraph("<b>Amount (Rs)</b>", lbl_style),
             Paragraph("<b>Deductions Component</b>", lbl_style), Paragraph("<b>Amount (Rs)</b>", lbl_style)],
            [Paragraph("Basic Salary", val_style), Paragraph(f"{basic:,.0f}", val_style),
             Paragraph("Income Tax Withholding", val_style), Paragraph(f"{tax:,.0f}", val_style)],
            [Paragraph("Allowances & Utilities", val_style), Paragraph(f"{allowances:,.0f}", val_style),
             Paragraph("Advance Salary Adjusted", val_style), Paragraph(f"{advance:,.0f}", val_style)],
            [Paragraph("Bonus & Overtime", val_style), Paragraph(f"{(bonus + overtime):,.0f}", val_style),
             Paragraph("Absence / Late Deductions", val_style), Paragraph(f"{deductions:,.0f}", val_style)],
            [Paragraph("<b>Total Gross Earnings:</b>", val_bold), Paragraph(f"<b>Rs. {gross_salary:,.0f}</b>", val_bold),
             Paragraph("<b>Total Deductions:</b>", val_bold), Paragraph(f"<b>Rs. {tot_deductions:,.0f}</b>", val_bold)]
        ]
        bt = Table(breakup_data, colWidths=[170, 95, 175, 100])
        bt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(bt)
        elements.append(Spacer(1, 8))

        net_card = [
            [Paragraph("<b>NET SALARY DISBURSED / TRANSFERRED:</b>", ParagraphStyle('NetL', parent=lbl_style, fontSize=10, textColor=colors.HexColor('#059669'))),
             Paragraph(f"<b>Rs. {net_salary:,.0f}</b>", ParagraphStyle('NetV', parent=val_bold, fontSize=11, textColor=colors.HexColor('#059669')))]
        ]
        nt = Table(net_card, colWidths=[340, 200])
        nt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECFDF5')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#059669')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT')
        ]))
        elements.append(nt)

        elements.extend(cls.build_footer("Confidential Document: Intended solely for the named employee."))
        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Salary slip generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 9. GENERAL CERTIFICATE (School Leaving, Experience, Bona Fide)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_certificate(cls, cert_title, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        elements.extend(cls.build_header(inst_info, cert_title))

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'CertBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=19,
            textColor=colors.HexColor('#1E293B'),
            alignment=4
        )

        stu_name = cls._val(data_dict, "student_name", "Student")
        father_name = cls._val(data_dict, "father_name", "Father")
        cls_name = cls._val(data_dict, "class", "Class")
        session = cls._val(data_dict, "academic_session", "Current Session")

        elements.append(Spacer(1, 15))
        cert_text = (
            f"This is to certify that <b>{stu_name}</b>, child of <b>{father_name}</b>, "
            f"has been a bona fide student of <b>{inst_info.get('name', 'Universal Education System')}</b> in <b>{cls_name}</b> during academic session <b>{session}</b>.<br/><br/>"
        )
        if "leaving" in cert_title.lower() or "slc" in cert_title.lower():
            leaving_date = cls._val(data_dict, "date_of_leaving", datetime.now().strftime("%d-%m-%Y"))
            reason = cls._val(data_dict, "reason_for_leaving", "Completion of Academic Studies / Relocation")
            cert_text += (
                f"They left the institution on <b>{leaving_date}</b> on account of <i>{reason}</i>. "
                f"All institutional dues have been fully cleared up to the date of departure."
            )
        else:
            cert_text += "We wish them all success in their future academic and career endeavors."

        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 25))
        elements.extend(cls.build_footer())
        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Certificate generated successfully."

    @classmethod
    def generate_generic_document(cls, document_type, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        elements.extend(cls.build_header(inst_info, document_type))

        styles = getSampleStyleSheet()
        lbl_style = ParagraphStyle('Lbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#374151'))
        val_style = ParagraphStyle('Val', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#111827'))

        table_data = [[Paragraph("<b>Field Name</b>", lbl_style), Paragraph("<b>Value</b>", lbl_style)]]
        for k, v in data_dict.items():
            if str(k).startswith("_") or v is None:
                continue
            table_data.append([
                Paragraph(str(k).replace("_", " ").title(), lbl_style),
                Paragraph(str(v), val_style)
            ])

        t = Table(table_data, colWidths=[180, 343])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#4F46E5')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t)
        elements.extend(cls.build_footer())
        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Generated successfully via Built-in PDF Engine."

    # ──────────────────────────────────────────────────────────────────────────
    # 7. BONAFIDE CERTIFICATE (Student Profile, Photo, Live Sync)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_bonafide_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('BfLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('BfVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('BfValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('BfBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "BONAFIDE CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "BON-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        dob = cls._val(data_dict, "dob", cls._val(data_dict, "date_of_birth", "-"))
        b_form = cls._val(data_dict, "b_form", "-")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", cls._val(data_dict, "apply_class", "-"))
        sec_name = cls._val(data_dict, "section", cls._val(data_dict, "apply_section", "-"))
        roll_no = cls._val(data_dict, "roll_no", adm_no)
        session_val = cls._val(data_dict, "academic_session", "2025-2026")
        purpose = cls._val(data_dict, "document.purpose", cls._val(data_dict, "purpose", "Educational / Official Verification"))

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Admission / Reg No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Roll Number:", lbl_s), Paragraph(roll_no, val_s)],
            [Paragraph("Class & Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s),
             Paragraph("Academic Session:", lbl_s), Paragraph(session_val, val_s)],
            [Paragraph("Date of Birth:", lbl_s), Paragraph(dob, val_s),
             Paragraph("B-Form / CNIC:", lbl_s), Paragraph(b_form, val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[95, 140, 95, 113])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))

        photo_w = cls.resolve_photo_flowable(data_dict, width=72, height=88)
        id_layout = Table([[t_meta, photo_w]], colWidths=[443, 80])
        id_layout.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(id_layout)
        elements.append(Spacer(1, 14))

        cert_text = f"""
        This is to certify that <b>{stu_name}</b>, son/daughter of <b>{father_name}</b>, bearing Admission / Roll No. 
        <b>{roll_no}</b>, is a genuine and regular bona fide student of <b>{inst_info.get('name', 'Universal Education System')}</b>, 
        currently enrolled and pursuing studies in Class <b>{cls_name}</b> (Section <b>{sec_name}</b>) for the academic session <b>{session_val}</b>.<br/><br/>
        As per the institutional records, his/her date of birth is <b>{dob}</b> and National Identity / B-Form number is <b>{b_form}</b>. 
        His/her moral conduct, character, and scholastic standing have been found exemplary throughout their tenure at this academy.<br/><br/>
        This certificate is formally issued upon specific request for <i>{purpose}</i> and carries the full endorsement of the school administration.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigBf', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealBf', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Verified by Class In-Charge</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL EMBOSSED SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Headmaster / Principal</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Bonafide Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 8. ACADEMIC EXCELLENCE / MERIT CERTIFICATE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_merit_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('MeLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('MeVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('MeValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        title_gold = ParagraphStyle('MeH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=1, textColor=colors.HexColor('#B45309'))
        body_s = ParagraphStyle('MeBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "CERTIFICATE OF ACADEMIC EXCELLENCE & MERIT"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "MER-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", "-")
        session_val = cls._val(data_dict, "academic_session", "2025-2026")

        exam_name = cls._val(data_dict, "document.exam_name", cls._val(data_dict, "exam_name", "Annual Board / Final Examination"))
        position = cls._val(data_dict, "document.position", cls._val(data_dict, "position", "1st Position / Distinct Honors"))
        marks = cls._val(data_dict, "document.marks_obtained", cls._val(data_dict, "marks_obtained", "A+ Grade (92.4%)"))
        distinction = cls._val(data_dict, "document.distinction_area", cls._val(data_dict, "distinction_area", "Outstanding Academic Standing & Scholastic Excellence"))

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Admission / Roll No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class & Session:", lbl_s), Paragraph(f"{cls_name} ({session_val})", val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[105, 155, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        elements.append(Paragraph("IN RECOGNITION OF OUTSTANDING SCHOLASTIC ATTAINMENT", title_gold))
        elements.append(Spacer(1, 10))

        cert_text = f"""
        This citation is proudly conferred upon <b>{stu_name}</b>, son/daughter of <b>{father_name}</b>, in recognition of 
        exceptional diligence, scholarly commitment, and academic brilliance in <b>{exam_name}</b> during the academic year <b>{session_val}</b>.<br/><br/>
        The candidate has successfully achieved <b>{position}</b> with an aggregate score of <b>{marks}</b>. 
        Throughout the tenure, the scholar has exhibited supreme dedication, intellectual curiosity, and intellectual mastery.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 12))

        merit_spec = [
            [Paragraph("<b>EVALUATION CRITERIA</b>", lbl_s), Paragraph("<b>OFFICIAL MERIT CITATION</b>", lbl_s)],
            [Paragraph("Examination / Assessment:", val_s), Paragraph(f"<b>{exam_name}</b>", val_b)],
            [Paragraph("Position / Rank Secured:", val_s), Paragraph(f"<font color='#B45309'><b>{position}</b></font>", val_b)],
            [Paragraph("Grade / Marks Percentage:", val_s), Paragraph(f"<b>{marks}</b>", val_b)],
            [Paragraph("Special Commendation:", val_s), Paragraph(distinction, val_s)],
        ]
        t_spec = Table(merit_spec, colWidths=[180, 343])
        t_spec.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FEF3C7')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_spec)
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigMe', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealMe', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Academic Controller / Dean</b>", sig_box),
                Paragraph("<br/><b>INSTITUTIONAL SEAL OF MERIT</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal / Director</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Academic Excellence / Merit Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 9. ATTENDANCE CERTIFICATE (Verified Live Attendance Sync)
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_attendance_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('AttLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('AttVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('AttValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('AttBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "STUDENT ATTENDANCE & PUNCTUALITY CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "ATT-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", "-")
        sec_name = cls._val(data_dict, "section", "-")
        session_val = cls._val(data_dict, "academic_session", "2025-2026")

        tot_days = cls._val(data_dict, "attendance.total_working_days", cls._val(data_dict, "total_working_days", "210"))
        present_days = cls._val(data_dict, "attendance.days_present", cls._val(data_dict, "days_present", "202"))
        absent_days = cls._val(data_dict, "attendance.days_absent", "4")
        leave_days = cls._val(data_dict, "attendance.days_leave", "4")
        pct = cls._val(data_dict, "attendance.percentage", cls._val(data_dict, "attendance_percentage", "96.2%"))

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Admission / Roll No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class & Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s)],
            [Paragraph("Academic Year / Session:", lbl_s), Paragraph(session_val, val_s),
             Paragraph("Verified Attendance:", lbl_s), Paragraph(f"<font color='#059669'><b>{pct}</b></font>", val_b)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        cert_text = f"""
        This is to certify that <b>{stu_name}</b>, child of <b>{father_name}</b>, has maintained verified regular attendance 
        as a registered student of <b>{inst_info.get('name', 'Universal Education System')}</b> in Class <b>{cls_name}</b> 
        during the academic year <b>{session_val}</b>.<br/><br/>
        According to the automated institutional attendance biometric and register logs, the verified breakdown is audited as follows:
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 12))

        att_table_data = [
            [Paragraph("<b>ATTENDANCE METRIC</b>", lbl_s), Paragraph("<b>RECORD COUNT / PERCENTAGE</b>", lbl_s), Paragraph("<b>INSTITUTIONAL STATUS</b>", lbl_s)],
            [Paragraph("Total Academic Working Days:", val_s), Paragraph(f"<b>{tot_days} Days</b>", val_b), Paragraph("Prescribed Schedule", val_s)],
            [Paragraph("Days Present (Attended):", val_s), Paragraph(f"<b>{present_days} Days</b>", val_b), Paragraph("<font color='#059669'>Regular Attendance</font>", val_s)],
            [Paragraph("Authorized Leaves (Sanctioned):", val_s), Paragraph(f"{leave_days} Days", val_s), Paragraph("Officially Approved", val_s)],
            [Paragraph("Unexcused Absences:", val_s), Paragraph(f"{absent_days} Days", val_s), Paragraph("Within Permissible Limit", val_s)],
            [Paragraph("Net Attendance Percentage:", lbl_s), Paragraph(f"<font color='#059669'><b>{pct}</b></font>", val_b), Paragraph("<b>Eligible for Final Examinations</b>", val_b)],
        ]
        t_att = Table(att_table_data, colWidths=[180, 170, 173])
        t_att.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_att)
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigAtt', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealAtt', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Class In-Charge / Teacher</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL REGISTRAR SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal / Administrator</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Attendance Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 10. SPORTS & EXTRA-CURRICULAR CERTIFICATE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_sports_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('SpLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('SpVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('SpValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('SpBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "CERTIFICATE OF SPORTS & CO-CURRICULAR MERIT"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "SPT-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", "-")

        event_name = cls._val(data_dict, "document.event_name", cls._val(data_dict, "event_name", "Annual Inter-School Athletics Championship"))
        pos_secured = cls._val(data_dict, "document.position_secured", cls._val(data_dict, "position_secured", "Champion / First Place Gold Medalist"))
        event_date = cls._val(data_dict, "document.event_date", cls._val(data_dict, "event_date", datetime.now().strftime("%d-%m-%Y")))
        activity_type = cls._val(data_dict, "document.activity_type", cls._val(data_dict, "activity_type", "Athletics / Co-Curricular Competitions"))

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Athlete:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Parentage:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Admission / Roll No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class / Group:", lbl_s), Paragraph(cls_name, val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[105, 155, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        cert_text = f"""
        This certificate of distinction is presented to <b>{stu_name}</b> in recognition of active participation and high-caliber 
        sportsmanship displayed during the <b>{event_name}</b> held on <b>{event_date}</b>.<br/><br/>
        Representing <b>{inst_info.get('name', 'Universal Education System')}</b>, the student demonstrated team spirit, athletic rigor, 
        and discipline, securing <b>{pos_secured}</b> in the category of <i>{activity_type}</i>.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 12))

        event_spec = [
            [Paragraph("<b>COMPETITION DETAILS</b>", lbl_s), Paragraph("<b>PERFORMANCE RECORD</b>", lbl_s)],
            [Paragraph("Championship / Event Name:", val_s), Paragraph(f"<b>{event_name}</b>", val_b)],
            [Paragraph("Discipline / Activity Area:", val_s), Paragraph(activity_type, val_s)],
            [Paragraph("Position / Award Conferred:", val_s), Paragraph(f"<font color='#059669'><b>{pos_secured}</b></font>", val_b)],
            [Paragraph("Date of Competition:", val_s), Paragraph(event_date, val_s)],
        ]
        t_spec = Table(event_spec, colWidths=[180, 343])
        t_spec.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ECFDF5')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_spec)
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigSp', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealSp', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Sports Coach / Director Physical Ed</b>", sig_box),
                Paragraph("<br/><b>SPORTS BOARD SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal / Patron</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Sports & Extra-Curricular Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 11. STAFF EXPERIENCE CERTIFICATE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_experience_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('ExpLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('ExpVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('ExpValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('ExpBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "STAFF EXPERIENCE & SERVICE CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "EXP-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "Staff Member")))
        father_name = cls._val(data_dict, "employee.father_husband_name", cls._val(data_dict, "father_name", "-"))
        emp_id = cls._val(data_dict, "employee.emp_id", cls._val(data_dict, "emp_id", "-"))
        cnic = cls._val(data_dict, "employee.cnic", cls._val(data_dict, "cnic", "-"))
        designation = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "Faculty Member"))
        department = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "Academics"))
        join_date = cls._val(data_dict, "employee.joining_date", cls._val(data_dict, "joining_date", "-"))
        leaving_date = cls._val(data_dict, "document.date_of_leaving", cls._val(data_dict, "date_of_leaving", datetime.now().strftime("%d-%m-%Y")))

        meta_rows = [
            [Paragraph("Ref / Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Employee Name:", lbl_s), Paragraph(f"<b>{emp_name}</b>", val_b),
             Paragraph("Father / Husband:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Staff ID:", lbl_s), Paragraph(emp_id, val_s),
             Paragraph("CNIC / ID No.:", lbl_s), Paragraph(cnic, val_s)],
            [Paragraph("Designation:", lbl_s), Paragraph(f"<b>{designation}</b>", val_b),
             Paragraph("Department:", lbl_s), Paragraph(department, val_s)],
            [Paragraph("Date of Joining:", lbl_s), Paragraph(join_date, val_s),
             Paragraph("Date of Leaving:", lbl_s), Paragraph(leaving_date, val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        cert_text = f"""
        TO WHOM IT MAY CONCERN<br/><br/>
        This is to certify that <b>{emp_name}</b> (CNIC: <b>{cnic}</b>) has served as <b>{designation}</b> in the 
        Department of <b>{department}</b> at <b>{inst_info.get('name', 'Universal Education System')}</b> from 
        <b>{join_date}</b> to <b>{leaving_date}</b>.<br/><br/>
        During their professional tenure at this institution, they discharged their responsibilities with sincere dedication, competence, 
        and high professional standards. Their interpersonal conduct with faculty, administrative leadership, and students has been praiseworthy.<br/><br/>
        All official dues and departmental accounts have been verified as fully settled. We appreciate their valuable contributions and wish them every success in all future professional endeavors.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigExp', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealExp', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Head of Human Resources</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL INSTITUTIONAL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Director / Principal</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Staff Experience Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 12. STAFF APPOINTMENT LETTER
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_appointment_letter(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('ApptLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('ApptVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('ApptValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('ApptBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=15.5, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "OFFICIAL LETTER OF APPOINTMENT"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "APPT-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "Candidate Name")))
        father_name = cls._val(data_dict, "employee.father_husband_name", cls._val(data_dict, "father_name", "-"))
        cnic = cls._val(data_dict, "employee.cnic", cls._val(data_dict, "cnic", "-"))
        designation = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "Faculty Member"))
        department = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "Academics"))
        join_date = cls._val(data_dict, "employee.joining_date", cls._val(data_dict, "joining_date", datetime.now().strftime("%d-%m-%Y")))
        salary = cls._val(data_dict, "employee.gross_salary", cls._val(data_dict, "salary", "50,000"))
        emp_type = cls._val(data_dict, "employee.employment_type", "Permanent / Full-Time")

        meta_rows = [
            [Paragraph("Reference Code:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Offer Date:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Appointee Name:", lbl_s), Paragraph(f"<b>{emp_name}</b>", val_b),
             Paragraph("Parentage:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("CNIC / ID:", lbl_s), Paragraph(cnic, val_s),
             Paragraph("Proposed Role:", lbl_s), Paragraph(f"<b>{designation}</b>", val_b)],
            [Paragraph("Department:", lbl_s), Paragraph(department, val_s),
             Paragraph("Employment Type:", lbl_s), Paragraph(emp_type, val_s)],
            [Paragraph("Reporting Date:", lbl_s), Paragraph(join_date, val_s),
             Paragraph("Starting Remuneration:", lbl_s), Paragraph(f"<b>Rs. {salary} / Month</b>", val_b)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 12))

        terms_text = f"""
        Dear <b>{emp_name}</b>,<br/><br/>
        On behalf of the Governing Council of <b>{inst_info.get('name', 'Universal Education System')}</b>, we are pleased 
        to appoint you to the position of <b>{designation}</b> under the following formalized contractual terms:<br/><br/>
        <b>1. Remuneration:</b> You will receive a consolidated gross monthly compensation of <b>Rs. {salary}</b>, subject to applicable statutory deductions.<br/>
        <b>2. Commencement & Probation:</b> You are required to assume duty on <b>{join_date}</b>. An initial probation period of 3 months applies, renewable upon performance appraisal.<br/>
        <b>3. Professional Conduct:</b> You agree to adhere strictly to the institution’s Code of Academic Conduct, confidentiality protocols, and pedagogical standards.<br/>
        <b>4. Notice Period:</b> Either party may terminate this employment agreement by serving 30 days prior written notice or equivalent compensation in lieu thereof.
        """
        elements.append(Paragraph(terms_text, body_s))
        elements.append(Spacer(1, 20))

        sig_box = ParagraphStyle('SigAppt', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, alignment=1)
        seal_box = ParagraphStyle('SealAppt', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Appointee Acceptance Signature</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL EMBOSSED SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Appointing Authority / Principal</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Staff Appointment Letter generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 13. STAFF SALARY & INCOME CERTIFICATE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_salary_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('SalLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('SalVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('SalValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('SalBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "STAFF SALARY & INCOME CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "SAL-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "Staff Member")))
        emp_id = cls._val(data_dict, "employee.emp_id", cls._val(data_dict, "emp_id", "-"))
        cnic = cls._val(data_dict, "employee.cnic", cls._val(data_dict, "cnic", "-"))
        designation = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "Staff Member"))
        department = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "Academics"))
        join_date = cls._val(data_dict, "employee.joining_date", cls._val(data_dict, "joining_date", "-"))

        basic = cls._val(data_dict, "employee.basic_salary", "0.00")
        house = cls._val(data_dict, "employee.house_allowance", "0.00")
        med = cls._val(data_dict, "employee.medical_allowance", "0.00")
        trans = cls._val(data_dict, "employee.transport_allowance", "0.00")
        gross = cls._val(data_dict, "employee.gross_salary", cls._val(data_dict, "gross_salary", "0.00"))
        tax = cls._val(data_dict, "employee.tax_deduction", "0.00")
        net_sal = cls._val(data_dict, "employee.net_salary", cls._val(data_dict, "net_salary", gross))

        meta_rows = [
            [Paragraph("Certificate No.:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Date of Issue:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Employee Name:", lbl_s), Paragraph(f"<b>{emp_name}</b>", val_b),
             Paragraph("Staff ID:", lbl_s), Paragraph(emp_id, val_s)],
            [Paragraph("Designation:", lbl_s), Paragraph(f"<b>{designation}</b>", val_b),
             Paragraph("Department:", lbl_s), Paragraph(department, val_s)],
            [Paragraph("CNIC / National ID:", lbl_s), Paragraph(cnic, val_s),
             Paragraph("Joining Date:", lbl_s), Paragraph(join_date, val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        cert_text = f"""
        TO WHOM IT MAY CONCERN<br/><br/>
        This is to certify that <b>{emp_name}</b> is a permanent employee of <b>{inst_info.get('name', 'Universal Education System')}</b> 
        serving as <b>{designation}</b>. According to official payroll records maintained by the Finance and Accounts Department, 
        their current monthly salary and allowance structure is audited as follows:
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 12))

        salary_breakdown = [
            [Paragraph("<b>EARNINGS / ALLOWANCES</b>", lbl_s), Paragraph("<b>AMOUNT (PKR)</b>", lbl_s), Paragraph("<b>STATUTORY DEDUCTIONS</b>", lbl_s), Paragraph("<b>AMOUNT (PKR)</b>", lbl_s)],
            [Paragraph("Basic Salary:", val_s), Paragraph(f"Rs. {basic}", val_s), Paragraph("Income Tax Deduction:", val_s), Paragraph(f"Rs. {tax}", val_s)],
            [Paragraph("House Rent Allowance:", val_s), Paragraph(f"Rs. {house}", val_s), Paragraph("Other Deductions / Fund:", val_s), Paragraph("Rs. 0.00", val_s)],
            [Paragraph("Medical Allowance:", val_s), Paragraph(f"Rs. {med}", val_s), Paragraph("Total Deductions:", val_s), Paragraph(f"Rs. {tax}", val_s)],
            [Paragraph("Transport Allowance:", val_s), Paragraph(f"Rs. {trans}", val_s), Paragraph("", val_s), Paragraph("", val_s)],
            [Paragraph("<b>GROSS MONTHLY SALARY:</b>", lbl_s), Paragraph(f"<b>Rs. {gross}</b>", val_b), Paragraph("<b>NET PAYABLE MONTHLY:</b>", lbl_s), Paragraph(f"<font color='#059669'><b>Rs. {net_sal}</b></font>", val_b)],
        ]
        t_sal = Table(salary_breakdown, colWidths=[140, 120, 143, 120])
        t_sal.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        elements.append(t_sal)
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigSal', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealSal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Finance & Accounts Officer</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL FINANCE SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Director / Principal</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Staff Salary & Income Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 14. STAFF RELIEVING LETTER
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_relieving_letter(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('RelLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('RelVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('RelValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        body_s = ParagraphStyle('RelBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "FORMAL STAFF RELIEVING & DISCHARGE LETTER"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "REL-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "Staff Member")))
        emp_id = cls._val(data_dict, "employee.emp_id", cls._val(data_dict, "emp_id", "-"))
        cnic = cls._val(data_dict, "employee.cnic", cls._val(data_dict, "cnic", "-"))
        designation = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "Staff Member"))
        department = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "Academics"))

        resignation_date = cls._val(data_dict, "document.resignation_date", cls._val(data_dict, "resignation_date", datetime.now().strftime("%d-%m-%Y")))
        last_working_day = cls._val(data_dict, "document.last_working_day", cls._val(data_dict, "last_working_day", datetime.now().strftime("%d-%m-%Y")))
        clearance_status = cls._val(data_dict, "document.clearance_status", cls._val(data_dict, "clearance_status", "Audited & Fully Cleared Across All Departments"))

        meta_rows = [
            [Paragraph("Letter Code:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Issue Date:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Employee Name:", lbl_s), Paragraph(f"<b>{emp_name}</b>", val_b),
             Paragraph("Staff ID:", lbl_s), Paragraph(emp_id, val_s)],
            [Paragraph("Designation:", lbl_s), Paragraph(f"<b>{designation}</b>", val_b),
             Paragraph("Department:", lbl_s), Paragraph(department, val_s)],
            [Paragraph("Resignation Date:", lbl_s), Paragraph(resignation_date, val_s),
             Paragraph("Last Working Day:", lbl_s), Paragraph(f"<b>{last_working_day}</b>", val_b)],
            [Paragraph("CNIC / ID:", lbl_s), Paragraph(cnic, val_s),
             Paragraph("Clearance State:", lbl_s), Paragraph(f"<font color='#059669'><b>{clearance_status}</b></font>", val_b)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        cert_text = f"""
        Dear <b>{emp_name}</b>,<br/><br/>
        With reference to your formal resignation letter dated <b>{resignation_date}</b>, the competent administration 
        has accepted your separation. You are hereby officially relieved of your duties as <b>{designation}</b> at 
        <b>{inst_info.get('name', 'Universal Education System')}</b> effective from the close of business hours on <b>{last_working_day}</b>.<br/><br/>
        We confirm that you have completed all institutional handovers, returned assigned academic equipment and library properties, 
        and attained complete departmental clearances.<br/><br/>
        We take this opportunity to thank you for your contributions during your tenure and wish you the very best in your future endeavors.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigRel', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealRel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>HR & Clearance In-Charge</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL INSTITUTIONAL SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Director / Principal</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Staff Relieving Letter generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 15. STAFF APPRECIATION CERTIFICATE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_appreciation_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('ApprLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('ApprVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('ApprValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        award_h = ParagraphStyle('ApprH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=17, alignment=1, textColor=colors.HexColor('#B45309'))
        body_s = ParagraphStyle('ApprBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=17, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "CERTIFICATE OF APPRECIATION & MERIT"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "APR-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "Staff Member")))
        emp_id = cls._val(data_dict, "employee.emp_id", cls._val(data_dict, "emp_id", "-"))
        designation = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "Staff Member"))
        department = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "Academics"))

        award_name = cls._val(data_dict, "document.award_name", cls._val(data_dict, "award_name", "Distinguished Teacher & Outstanding Contribution Award"))
        reason = cls._val(data_dict, "document.reason", cls._val(data_dict, "reason", "Exemplary Pedagogical Rigor, Student Mentorship, and Unwavering Commitment"))

        meta_rows = [
            [Paragraph("Citation Code:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Conferment Date:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Honoree Name:", lbl_s), Paragraph(f"<b>{emp_name}</b>", val_b),
             Paragraph("Staff ID:", lbl_s), Paragraph(emp_id, val_s)],
            [Paragraph("Designation:", lbl_s), Paragraph(f"<b>{designation}</b>", val_b),
             Paragraph("Department:", lbl_s), Paragraph(department, val_s)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 14))

        elements.append(Paragraph(f"IN SPECIAL HONOUR OF {award_name.upper()}", award_h))
        elements.append(Spacer(1, 10))

        cert_text = f"""
        This certificate of appreciation is proudly presented to <b>{emp_name}</b>, <b>{designation}</b>, in grateful 
        acknowledgment of your high professional dedication, innovation, and distinguished loyalty rendered to 
        <b>{inst_info.get('name', 'Universal Education System')}</b>.<br/><br/>
        <b>Commendation Citation:</b> <i>"{reason}"</i>.<br/><br/>
        Your perseverance, educational values, and exemplary leadership continue to inspire faculty colleagues and students alike. 
        The Directorate and Board of Management express their highest commendation.
        """
        elements.append(Paragraph(cert_text, body_s))
        elements.append(Spacer(1, 25))

        sig_box = ParagraphStyle('SigAppr', parent=styles['Normal'], fontName='Helvetica', fontSize=8, alignment=1)
        seal_box = ParagraphStyle('SealAppr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Dean / Academic Head</b>", sig_box),
                Paragraph("<br/><b>INSTITUTIONAL COMMENDATION SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>President / Director General</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[174, 175, 174])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (1, 0), (1, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Staff Appreciation Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 16. DYNAMIC FEE STRUCTURE & NO DUES CERTIFICATE
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_fee_structure_certificate(cls, data_dict, output_path):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=36
        )
        elements = []
        inst_info = cls.get_institution_info()
        dec = cls.create_page_decorator(inst_info, "a4")
        styles = getSampleStyleSheet()

        lbl_s = ParagraphStyle('FeeLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        val_s = ParagraphStyle('FeeVal', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        val_b = ParagraphStyle('FeeValB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#0F172A'))
        th_s = ParagraphStyle('FeeTh', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.HexColor('#1E3A8A'))
        body_s = ParagraphStyle('FeeBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=15.5, textColor=colors.HexColor('#1E293B'))

        elements.extend(cls.build_header(inst_info, "FEE STRUCTURE & FINANCIAL CLEARANCE CERTIFICATE"))

        cert_no = cls._val(data_dict, "certificate_no", cls._val(data_dict, "document.certificate_number", cls._val(data_dict, "document_number", "FEE-2026-0001")))
        issue_date = cls._val(data_dict, "date_of_issue", cls._val(data_dict, "document.date_of_issue", cls._val(data_dict, "date", datetime.now().strftime("%d-%m-%Y"))))
        stu_name = cls._val(data_dict, "student_name", cls._val(data_dict, "name", "Student Name"))
        father_name = cls._val(data_dict, "father_name", "Father Name")
        adm_no = cls._val(data_dict, "admission_no", cls._val(data_dict, "student_id", "-"))
        cls_name = cls._val(data_dict, "class", "-")
        sec_name = cls._val(data_dict, "section", "-")
        session_val = cls._val(data_dict, "academic_session", "2025-2026")

        basis = cls._val(data_dict, "fee.basis", cls._val(data_dict, "fee_basis", "Monthly"))
        total_struct = cls._val(data_dict, "fee.total_structure_cost", "0")
        total_billed = cls._val(data_dict, "fee.total_billed", "0")
        total_paid = cls._val(data_dict, "fee.total_paid", "0")
        total_pending = cls._val(data_dict, "fee.total_pending", "0")
        is_cleared = (str(total_pending).strip() in ["0", "0.00", "0.0", "-"]) or bool(data_dict.get("fee.is_cleared", False))

        meta_rows = [
            [Paragraph("Certificate Code:", lbl_s), Paragraph(f"<b>{cert_no}</b>", val_b),
             Paragraph("Issue Date:", lbl_s), Paragraph(issue_date, val_s)],
            [Paragraph("Student Name:", lbl_s), Paragraph(f"<b>{stu_name}</b>", val_b),
             Paragraph("Father's Name:", lbl_s), Paragraph(father_name, val_s)],
            [Paragraph("Admission / Roll No.:", lbl_s), Paragraph(adm_no, val_s),
             Paragraph("Class & Section:", lbl_s), Paragraph(f"{cls_name} - {sec_name}", val_s)],
            [Paragraph("Academic Session:", lbl_s), Paragraph(session_val, val_s),
             Paragraph("Billing Cycle Basis:", lbl_s), Paragraph(f"<b>{basis} Package</b>", val_b)]
        ]
        t_meta = Table(meta_rows, colWidths=[110, 150, 110, 153])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 10))

        cert_intro = f"""
        This certificate is issued to confirm the official institutional fee package and real-time financial ledger 
        position for <b>{stu_name}</b>, enrolled in Class <b>{cls_name}</b> at <b>{inst_info.get('name', 'Universal Education System')}</b>. 
        The verified fee structure computed on <b>{basis}</b> basis and live audited clearance record are itemized below:
        """
        elements.append(Paragraph(cert_intro, body_s))
        elements.append(Spacer(1, 8))

        # Dynamic Schedule Breakdown
        schedule_rows = [
            [Paragraph("<b>SR.</b>", th_s), Paragraph("<b>FEE COMPONENT / PACKAGE HEAD</b>", th_s), Paragraph("<b>BILLING BASIS</b>", th_s), Paragraph("<b>AMOUNT (PKR)</b>", th_s)]
        ]

        structural_items = data_dict.get("fee.structural_items", [])
        if structural_items and isinstance(structural_items, list):
            for i, it in enumerate(structural_items, 1):
                t_title = it.get("title", f"Package Head #{i}")
                amt = float(it.get("amount", 0.0))
                schedule_rows.append([
                    Paragraph(str(i), val_s),
                    Paragraph(t_title, lbl_s),
                    Paragraph(basis, val_s),
                    Paragraph(f"Rs. {amt:,.0f}", val_s)
                ])
        else:
            schedule_rows.append([
                Paragraph("1", val_s),
                Paragraph(f"{basis} Tuition & Institutional Services", lbl_s),
                Paragraph(basis, val_s),
                Paragraph(f"Rs. {total_struct}", val_s)
            ])

        schedule_rows.append([
            Paragraph("", lbl_s),
            Paragraph("<b>TOTAL STRUCTURAL PACKAGE COST:</b>", lbl_s),
            Paragraph(f"<b>{basis}</b>", lbl_s),
            Paragraph(f"<b>Rs. {total_struct}</b>", val_b)
        ])

        t_sched = Table(schedule_rows, colWidths=[30, 260, 110, 123])
        t_sched.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EEF2FF')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_sched)
        elements.append(Spacer(1, 10))

        # Live Ledger Audit Table
        clr_color = '#059669' if is_cleared else '#DC2626'
        status_txt = "AUDITED & CLEARED — NO DUES OUTSTANDING" if is_cleared else f"OUTSTANDING DUES PENDING (Rs. {total_pending})"
        badge_txt = "NO DUES CLEARED [PAID]" if is_cleared else "PENDING DUES [PROVISIONAL]"

        elements.append(Paragraph("<b>2. REAL-TIME STUDENT LEDGER AUDIT & CLEARANCE POSITION</b>", lbl_s))
        elements.append(Spacer(1, 4))
        ledger_rows = [
            [Paragraph("Total Billed to Date:", lbl_s), Paragraph(f"Rs. {total_billed}", val_s),
             Paragraph("Total Paid / Settled:", lbl_s), Paragraph(f"<font color='#059669'><b>Rs. {total_paid}</b></font>", val_b)],
            [Paragraph("Outstanding Dues:", lbl_s), Paragraph(f"<font color='{clr_color}'><b>Rs. {total_pending}</b></font>", val_b),
             Paragraph("No Dues Status:", lbl_s), Paragraph(f"<font color='{clr_color}'><b>{badge_txt}</b></font>", val_b)],
            [Paragraph("Institutional Endorsement:", lbl_s), Paragraph(status_txt, val_b),
             Paragraph("Audit System Stamp:", lbl_s), Paragraph("Synchronized Live from Core DB", val_s)]
        ]
        t_ledger = Table(ledger_rows, colWidths=[130, 130, 133, 130])
        t_ledger.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_ledger)
        elements.append(Spacer(1, 18))

        sig_box = ParagraphStyle('SigFee', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, alignment=1)
        seal_box = ParagraphStyle('SealFee', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#64748B'), alignment=1)
        sig_rows = [
            [
                Paragraph("__________________________<br/><b>Accounts & Billing Officer</b>", sig_box),
                Paragraph("__________________________<br/><b>Auditor / Bursar</b>", sig_box),
                Paragraph("<br/><b>OFFICIAL ACCOUNTS SEAL</b><br/>", seal_box),
                Paragraph("__________________________<br/><b>Principal / Authorized</b>", sig_box)
            ]
        ]
        t_sigs = Table(sig_rows, colWidths=[130, 130, 133, 130])
        t_sigs.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (2, 0), (2, 0), 1, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#F8FAFC')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_sigs)

        doc.build(elements, onFirstPage=dec, onLaterPages=dec)
        return True, "Fee Structure & No Dues Certificate generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 17. 80MM POS THERMAL FEE PAYMENT RECEIPT
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_thermal_fee_receipt(cls, data_dict, output_path):
        """
        Renders an ultra-compact, 100% black-and-white, high-contrast POS thermal receipt (80mm width).
        Optimized specifically for thermal POS direct heat printers with pure black typography, dashed dividers, and barcodes.
        """
        page_w = 80 * mm
        left_m = 6
        right_m = 6
        top_m = 6
        bottom_m = 6
        elements = []
        inst_info = cls.get_institution_info()
        styles = getSampleStyleSheet()

        h_title = ParagraphStyle('ThTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=11.5, alignment=1, textColor=colors.black)
        h_sub = ParagraphStyle('ThSub', parent=styles['Normal'], fontName='Helvetica', fontSize=6.8, leading=8.5, alignment=1, textColor=colors.black)
        th_center_b = ParagraphStyle('ThCenterB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=9.5, alignment=1, textColor=colors.black)
        th_lbl = ParagraphStyle('ThLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, leading=8.8, textColor=colors.black)
        th_val = ParagraphStyle('ThVal', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=8.8, textColor=colors.black)
        th_val_r = ParagraphStyle('ThValR', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=8.8, alignment=2, textColor=colors.black)
        th_b_r = ParagraphStyle('ThBR', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, alignment=2, textColor=colors.black)
        foot_s = ParagraphStyle('ThFoot', parent=styles['Normal'], fontName='Helvetica', fontSize=6.5, leading=8.5, alignment=1, textColor=colors.black)

        # Header Logo (if present) & Institution Name (Strictly Monochrome)
        logo_path = inst_info.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            try:
                elements.append(Image(logo_path, width=28, height=28, kind='proportional'))
                elements.append(Spacer(1, 2))
            except Exception:
                pass

        elements.append(Paragraph(inst_info.get("name", "UPSCM").upper(), h_title))
        if inst_info.get("address"):
            elements.append(Paragraph(inst_info["address"], h_sub))
        if inst_info.get("phone"):
            elements.append(Paragraph(f"Tel: {inst_info['phone']}", h_sub))

        elements.append(Spacer(1, 3))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.black, spaceBefore=2, spaceAfter=3))
        elements.append(Paragraph("FEE PAYMENT RECEIPT", th_center_b))
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=3, spaceAfter=4))

        receipt_no = cls._val(data_dict, "receipt_number", cls._val(data_dict, "voucher_number", cls._val(data_dict, "voucher_no", "REC-0001")))
        stu_name = cls._val(data_dict, "student_name", "Student")
        father_name = cls._val(data_dict, "father_name", "-")
        stu_id = cls._val(data_dict, "student_id", "-")
        cls_name = cls._val(data_dict, "class", "-")
        sec_name = cls._val(data_dict, "section", "-")
        fee_month = cls._val(data_dict, "fee_month", datetime.now().strftime("%B %Y"))
        pay_date = cls._val(data_dict, "payment_date", datetime.now().strftime("%Y-%m-%d %H:%M"))
        pay_method = cls._val(data_dict, "payment_method", "Cash")

        meta_rows = [
            [Paragraph("Receipt #:", th_lbl), Paragraph(f"<b>{receipt_no}</b>", th_val)],
            [Paragraph("Date/Time:", th_lbl), Paragraph(pay_date, th_val)],
            [Paragraph("Student:", th_lbl), Paragraph(f"<b>{stu_name}</b>", th_val)],
            [Paragraph("Father:", th_lbl), Paragraph(father_name, th_val)],
            [Paragraph("Roll / ID:", th_lbl), Paragraph(stu_id, th_val)],
            [Paragraph("Class/Sec:", th_lbl), Paragraph(f"{cls_name} - {sec_name}", th_val)],
            [Paragraph("Fee Month:", th_lbl), Paragraph(f"<b>{fee_month}</b>", th_val)],
            [Paragraph("Method:", th_lbl), Paragraph(pay_method, th_val)],
        ]
        t_meta = Table(meta_rows, colWidths=[60, 154])
        t_meta.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_meta)
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=3, spaceAfter=3))

        # Items Table
        items_rows = [
            [Paragraph("<b>PARTICULAR</b>", th_lbl), Paragraph("<b>AMOUNT (PKR)</b>", th_b_r)]
        ]

        found_items = False
        for i in range(1, 15):
            cat_key = f"fee.item_{i}_category"
            if cat_key in data_dict and data_dict[cat_key]:
                found_items = True
                cat_nm = data_dict[cat_key]
                amt = data_dict.get(f"fee.item_{i}_amount", "0")
                paid = data_dict.get(f"fee.item_{i}_paid", amt)
                items_rows.append([
                    Paragraph(cat_nm, th_val),
                    Paragraph(f"<b>Rs. {paid}</b>", th_b_r)
                ])

        if not found_items:
            tot = cls._val(data_dict, "current_fee", cls._val(data_dict, "total_amount", "0"))
            paid = cls._val(data_dict, "amount_received", cls._val(data_dict, "paid_amount", tot))
            items_rows.append([
                Paragraph(f"Tuition Fee ({fee_month})", th_val),
                Paragraph(f"<b>Rs. {paid}</b>", th_b_r)
            ])

        t_items = Table(items_rows, colWidths=[130, 84])
        t_items.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 1.2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, 0), 0.8, colors.black),
        ]))
        elements.append(t_items)
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=3, spaceAfter=3))

        # Financial Summary
        tot_paying = cls._val(data_dict, "amount_received", cls._val(data_dict, "paid_amount", "0"))
        tot_disc = cls._val(data_dict, "total_discount", "0")
        tot_rem = cls._val(data_dict, "total_remaining_balance", cls._val(data_dict, "remaining_balance", "0"))

        summary_rows = [
            [Paragraph("<b>TOTAL RECEIVED:</b>", th_lbl), Paragraph(f"<b>Rs. {tot_paying}</b>", th_b_r)],
            [Paragraph("Discount Allowed:", th_lbl), Paragraph(f"Rs. {tot_disc}", th_val_r)],
            [Paragraph("<b>REMAINING DUES:</b>", th_lbl), Paragraph(f"<b>Rs. {tot_rem}</b>", th_b_r)],
        ]
        t_sum = Table(summary_rows, colWidths=[120, 94])
        t_sum.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 1.2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_sum)
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.black, spaceBefore=4, spaceAfter=4))

        # Pure Monochrome Barcode
        try:
            from reportlab.graphics.barcode import code128
            bc_str = str(receipt_no or stu_id or "FEE").replace(" ", "")
            bc = code128.Code128(bc_str, barWidth=0.7, barHeight=14)
            t_bc = Table([[bc]], colWidths=[214])
            t_bc.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(t_bc)
            elements.append(Spacer(1, 3))
        except Exception:
            pass

        elements.append(Paragraph("<b>*** PAYMENT VERIFIED & AUDITED ***</b>", th_center_b))
        elements.append(Paragraph("Computer Generated Receipt — No Signature Required", foot_s))
        foot_custom = DocumentService.get_setting("receipt_footer", "")
        if foot_custom:
            elements.append(Paragraph(foot_custom, foot_s))
        elements.append(Paragraph("Thank you for paying on time!", foot_s))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=3, spaceAfter=2))
        elements.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", foot_s))

        # Dynamically measure exact content height so receipt ends right after content with zero paper waste
        avail_w = page_w - left_m - right_m
        calc_h = top_m + bottom_m
        for elem in elements:
            try:
                w, h = elem.wrap(avail_w, 20000)
                sb = getattr(elem, 'spaceBefore', 0) or 0
                sa = getattr(elem, 'spaceAfter', 0) or 0
                calc_h += (h + sb + sa)
            except Exception:
                pass
        calc_h += 18

        doc = SimpleDocTemplate(
            output_path,
            pagesize=(page_w, calc_h),
            leftMargin=left_m,
            rightMargin=right_m,
            topMargin=top_m,
            bottomMargin=bottom_m
        )
        doc.build(elements)
        return True, "Thermal fee receipt generated successfully."

    # ──────────────────────────────────────────────────────────────────────────
    # 18. 80MM POS THERMAL STAFF SALARY SLIP
    # ──────────────────────────────────────────────────────────────────────────
    @classmethod
    def generate_thermal_salary_slip(cls, data_dict, output_path):
        """
        Renders an 80mm thermal salary voucher slip for staff disbursement.
        Optimized specifically for thermal POS direct heat printers with 100% black-and-white typography.
        """
        page_w = 80 * mm
        left_m = 6
        right_m = 6
        top_m = 6
        bottom_m = 6
        elements = []
        inst_info = cls.get_institution_info()
        styles = getSampleStyleSheet()

        h_title = ParagraphStyle('ThSTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9.5, leading=11.5, alignment=1, textColor=colors.black)
        h_sub = ParagraphStyle('ThSSub', parent=styles['Normal'], fontName='Helvetica', fontSize=6.8, leading=8.5, alignment=1, textColor=colors.black)
        th_center_b = ParagraphStyle('ThSCenterB', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=9.5, alignment=1, textColor=colors.black)
        th_lbl = ParagraphStyle('ThSLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7, leading=8.8, textColor=colors.black)
        th_val = ParagraphStyle('ThSVal', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=8.8, textColor=colors.black)
        th_val_r = ParagraphStyle('ThSValR', parent=styles['Normal'], fontName='Helvetica', fontSize=7, leading=8.8, alignment=2, textColor=colors.black)
        th_b_r = ParagraphStyle('ThSBR', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=9.5, alignment=2, textColor=colors.black)
        foot_s = ParagraphStyle('ThSFoot', parent=styles['Normal'], fontName='Helvetica', fontSize=6.5, leading=8.5, alignment=1, textColor=colors.black)

        logo_path = inst_info.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            try:
                elements.append(Image(logo_path, width=28, height=28, kind='proportional'))
                elements.append(Spacer(1, 2))
            except Exception:
                pass

        elements.append(Paragraph(inst_info.get("name", "UPSCM").upper(), h_title))
        if inst_info.get("address"):
            elements.append(Paragraph(inst_info["address"], h_sub))
        if inst_info.get("phone"):
            elements.append(Paragraph(f"Tel: {inst_info['phone']}", h_sub))

        elements.append(Spacer(1, 3))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.black, spaceBefore=2, spaceAfter=3))
        elements.append(Paragraph("STAFF SALARY DISBURSEMENT SLIP", th_center_b))
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=3, spaceAfter=4))

        def _parse_num(k_list):
            for k in k_list:
                if k in data_dict and data_dict[k] is not None:
                    val_s = str(data_dict[k]).replace(",", "").replace("Rs.", "").replace("PKR", "").strip()
                    try:
                        return float(val_s)
                    except (ValueError, TypeError):
                        pass
            return 0.0

        emp_name = cls._val(data_dict, "employee.name", cls._val(data_dict, "employee_name", cls._val(data_dict, "name", "-")))
        emp_id = cls._val(data_dict, "employee.emp_id", cls._val(data_dict, "employee.id", cls._val(data_dict, "employee_id", "-")))
        desig = cls._val(data_dict, "employee.designation", cls._val(data_dict, "designation", "-"))
        dept = cls._val(data_dict, "employee.department", cls._val(data_dict, "department", "-"))
        sal_month = cls._val(data_dict, "payroll.month", cls._val(data_dict, "salary.month", cls._val(data_dict, "month", datetime.now().strftime("%B %Y"))))
        pay_date = cls._val(data_dict, "payroll.payment_date", cls._val(data_dict, "salary.payment_date", cls._val(data_dict, "payment_date", datetime.now().strftime("%Y-%m-%d"))))
        receipt_no = cls._val(data_dict, "payroll.receipt_no", cls._val(data_dict, "receipt_no", "-"))

        basic = _parse_num(["payroll.basic", "salary.basic", "basic_salary", "basic"])
        allowances = _parse_num(["payroll.allowances", "salary.allowances", "allowances"])
        bonus = _parse_num(["payroll.bonus", "salary.bonus", "bonus"])
        overtime = _parse_num(["payroll.overtime", "salary.overtime", "overtime"])
        gross_salary = _parse_num(["payroll.gross", "salary.gross", "gross_salary", "gross"])
        if gross_salary <= 0:
            gross_salary = basic + allowances + bonus + overtime

        deductions = _parse_num(["payroll.deductions", "salary.deductions", "deductions"])
        advance = _parse_num(["payroll.advance", "salary.advance", "advance"])
        tax = _parse_num(["payroll.tax", "salary.tax", "tax_deduction", "tax"])
        tot_deductions = deductions + advance + tax

        net_salary = _parse_num(["payroll.net_salary", "payroll.net", "salary.net", "net_salary", "net"])
        if net_salary <= 0:
            net_salary = max(0.0, gross_salary - tot_deductions)

        meta_rows = [
            [Paragraph("Ref #:", th_lbl), Paragraph(f"<b>{receipt_no}</b>", th_val)],
            [Paragraph("Date:", th_lbl), Paragraph(pay_date, th_val)],
            [Paragraph("Employee:", th_lbl), Paragraph(f"<b>{emp_name}</b>", th_val)],
            [Paragraph("Staff ID:", th_lbl), Paragraph(emp_id, th_val)],
            [Paragraph("Designation:", th_lbl), Paragraph(f"<b>{desig}</b>", th_val)],
            [Paragraph("Department:", th_lbl), Paragraph(f"<b>{dept}</b>", th_val)],
            [Paragraph("Pay Month:", th_lbl), Paragraph(f"<b>{sal_month}</b>", th_val)],
        ]
        t_meta = Table(meta_rows, colWidths=[60, 154])
        t_meta.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 1),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 3))
        elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceBefore=2, spaceAfter=3))

        breakup_rows = [
            [Paragraph("Basic Salary:", th_lbl), Paragraph(f"Rs. {basic:,.0f}", th_val_r)],
            [Paragraph("Allowances & Utilities:", th_lbl), Paragraph(f"Rs. {allowances:,.0f}", th_val_r)],
            [Paragraph("Bonus / Overtime:", th_lbl), Paragraph(f"Rs. {(bonus + overtime):,.0f}", th_val_r)],
            [Paragraph("<b>GROSS SALARY:</b>", th_lbl), Paragraph(f"<b>Rs. {gross_salary:,.0f}</b>", th_b_r)],
            [Paragraph("Deductions & Advances:", th_lbl), Paragraph(f"Rs. {tot_deductions:,.0f}", th_val_r)],
            [Paragraph("<b>NET SALARY PAID:</b>", th_lbl), Paragraph(f"<b>Rs. {net_salary:,.0f}</b>", th_b_r)],
        ]
        t_breakup = Table(breakup_rows, colWidths=[110, 104])
        t_breakup.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 1.2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_breakup)
        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", thickness=1.2, color=colors.black, spaceBefore=3, spaceAfter=4))

        # Barcode
        try:
            from reportlab.graphics.barcode import code128
            bc_str = str(receipt_no or emp_id or "SAL").replace(" ", "")
            bc = code128.Code128(bc_str, barWidth=0.7, barHeight=14)
            t_bc = Table([[bc]], colWidths=[214])
            t_bc.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(t_bc)
            elements.append(Spacer(1, 3))
        except Exception:
            pass

        elements.append(Paragraph("<b>*** CONFIDENTIAL SALARY RECORD ***</b>", th_center_b))
        elements.append(Paragraph("Accounts & Finance Counter Endorsed.", foot_s))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("____________________________", foot_s))
        elements.append(Paragraph("Employee Acknowledgment Sign", foot_s))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=4, spaceAfter=2))
        elements.append(Paragraph("- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -", foot_s))

        # Dynamically measure exact content height so slip ends right after content with zero paper waste
        avail_w = page_w - left_m - right_m
        calc_h = top_m + bottom_m
        for elem in elements:
            try:
                w, h = elem.wrap(avail_w, 20000)
                sb = getattr(elem, 'spaceBefore', 0) or 0
                sa = getattr(elem, 'spaceAfter', 0) or 0
                calc_h += (h + sb + sa)
            except Exception:
                pass
        calc_h += 18

        doc = SimpleDocTemplate(
            output_path,
            pagesize=(page_w, calc_h),
            leftMargin=left_m,
            rightMargin=right_m,
            topMargin=top_m,
            bottomMargin=bottom_m
        )
        doc.build(elements)
        return True, "Thermal salary slip generated successfully."
