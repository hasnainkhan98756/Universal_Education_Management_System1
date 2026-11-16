import os
from datetime import datetime
from database.connection import get_session
from sqlalchemy import inspect, text
from database.models.institution import InstitutionSettings

try:
    from database.models.documents import DocumentHistory
except ImportError:
    DocumentHistory = None

class DocumentService:
    """Bulletproof Numbering, Settings, and Document Logging Engine."""

    @staticmethod
    def get_setting(key_str, default_val="", session=None):
        if session is not None:
            try:
                res = session.execute(text("SELECT setting_value FROM uems_dynamic_settings WHERE setting_key = :k"), {"k": key_str}).fetchone()
                if res and res[0] is not None:
                    return str(res[0])
                inst = session.query(InstitutionSettings).first()
                if inst and hasattr(inst, key_str):
                    val = getattr(inst, key_str)
                    if val is not None and str(val).strip() != "":
                        return str(val)
            except Exception:
                pass
        else:
            db = get_session()
            try:
                # 1. Check uems_dynamic_settings first (Primary Storage)
                res = db.execute(text("SELECT setting_value FROM uems_dynamic_settings WHERE setting_key = :k"), {"k": key_str}).fetchone()
                if res and res[0] is not None:
                    return str(res[0])

                # 2. Check InstitutionSettings table (Fallback)
                inst = db.query(InstitutionSettings).first()
                if inst and hasattr(inst, key_str):
                    val = getattr(inst, key_str)
                    if val is not None and str(val).strip() != "":
                        return str(val)
            except Exception:
                pass
            finally:
                db.close()

        # 3. Memory fallback
        try:
            from core.state_manager import app_state
            if hasattr(app_state, 'get_setting'):
                val = app_state.get_setting(key_str, None)
                if val is not None and str(val).strip() != "":
                    return str(val)
        except Exception: pass

        return default_val

    @staticmethod
    def _save_setting_to_db(key_str, value_str, session=None):
        if session is not None:
            try:
                session.execute(text("CREATE TABLE IF NOT EXISTS uems_dynamic_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)"))
                session.execute(text("INSERT OR REPLACE INTO uems_dynamic_settings (setting_key, setting_value) VALUES (:k, :v)"), {"k": key_str, "v": str(value_str)})
                inst = session.query(InstitutionSettings).first()
                if inst and hasattr(inst, key_str):
                    setattr(inst, key_str, str(value_str))
            except Exception as e:
                print(f"In-session setting save note: {e}")
            try:
                from core.state_manager import app_state
                if hasattr(app_state, 'set_setting'): app_state.set_setting(key_str, str(value_str))
                elif hasattr(app_state, 'update_setting'): app_state.update_setting(key_str, str(value_str))
                elif hasattr(app_state, 'settings') and isinstance(app_state.settings, dict): app_state.settings[key_str] = str(value_str)
                else: setattr(app_state, key_str, str(value_str))
            except Exception: pass
            return

        success = False
        db = get_session()
        try:
            db.execute(text("CREATE TABLE IF NOT EXISTS uems_dynamic_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)"))
            db.execute(text("INSERT OR REPLACE INTO uems_dynamic_settings (setting_key, setting_value) VALUES (:k, :v)"), {"k": key_str, "v": str(value_str)})
            inst = db.query(InstitutionSettings).first()
            if not inst:
                inst = InstitutionSettings()
                db.add(inst)
            if hasattr(inst, key_str):
                setattr(inst, key_str, str(value_str))
            db.commit()
            success = True
        except Exception as e:
            db.rollback()
            print(f"Dynamic Settings Table Error: {e}")
        finally:
            db.close()

        # --- STEP 3: Update Live App Memory ---
        if success:
            try:
                from core.state_manager import app_state
                if hasattr(app_state, 'set_setting'): app_state.set_setting(key_str, str(value_str))
                elif hasattr(app_state, 'update_setting'): app_state.update_setting(key_str, str(value_str))
                elif hasattr(app_state, 'settings') and isinstance(app_state.settings, dict): app_state.settings[key_str] = str(value_str)
                else: setattr(app_state, key_str, str(value_str))

                # Trigger asynchronous debounced auto-backup on configuration changes
                if not key_str.startswith("counter_") and key_str not in ["last_auto_backup_date"]:
                    try:
                        from core.backup_service import BackupService
                        BackupService.trigger_auto_backup_async("Settings Update")
                    except Exception:
                        pass
            except Exception: pass

    @staticmethod
    def save_setting(key_str, value_str, session=None):
        DocumentService._save_setting_to_db(key_str, value_str, session=session)

    @staticmethod
    def get_format(*args, **kwargs):
        doc_type = "Fee Voucher"
        default = ""
        if len(args) > 0: doc_type = args[0]
        elif "document_type" in kwargs: doc_type = kwargs["document_type"]
        elif "doc_type" in kwargs: doc_type = kwargs["doc_type"]
        elif "key" in kwargs: doc_type = kwargs["key"]

        if len(args) > 1: default = args[1]
        elif "default" in kwargs: default = kwargs["default"]

        doc_str = str(doc_type).strip()
        if doc_str.startswith("num_format_"): return DocumentService.get_setting(doc_str, default or "{YEAR}-{NUMBER}")

        clean = doc_str.lower().replace("_", " ").replace("-", " ")
        key_map = {
            "fee voucher": ("num_format_voucher", "VOUCH-{YEAR}-{NUMBER}"),
            "voucher": ("num_format_voucher", "VOUCH-{YEAR}-{NUMBER}"),
            "fee receipt": ("num_format_fee", "FEE-{YEAR}-{NUMBER}"),
            "fee payment": ("num_format_fee", "FEE-{YEAR}-{NUMBER}"),
            "receipt": ("num_format_fee", "FEE-{YEAR}-{NUMBER}"),
            "payment": ("num_format_fee", "FEE-{YEAR}-{NUMBER}"),
            "fee": ("num_format_fee", "FEE-{YEAR}-{NUMBER}"),
            "school leaving certificate": ("num_format_slc", "SLC-{YEAR}-{NUMBER}"),
            "school leaving": ("num_format_slc", "SLC-{YEAR}-{NUMBER}"),
            "slc": ("num_format_slc", "SLC-{YEAR}-{NUMBER}"),
            "character certificate": ("num_format_char", "CHAR-{YEAR}-{NUMBER}"),
            "character": ("num_format_char", "CHAR-{YEAR}-{NUMBER}"),
            "char": ("num_format_char", "CHAR-{YEAR}-{NUMBER}"),
            "english proficiency": ("num_format_eng", "ENG-{YEAR}-{NUMBER}"),
            "english": ("num_format_eng", "ENG-{YEAR}-{NUMBER}"),
            "eng": ("num_format_eng", "ENG-{YEAR}-{NUMBER}"),
            "student id card": ("num_format_id", "ID-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "student id": ("num_format_id", "ID-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "id card": ("num_format_id", "ID-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "id": ("num_format_id", "ID-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "admission form": ("num_format_adm", "ADM-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "admission": ("num_format_adm", "ADM-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "adm": ("num_format_adm", "ADM-{INSTITUTE}-{YEAR}-{NUMBER}"),
            "transcript": ("num_format_trans", "TRANS-{YEAR}-{NUMBER}"),
            "employee id": ("num_format_emp", "EMP-{YEAR}-{NUMBER}"),
            "salary slip": ("num_format_sal", "SAL-{YEAR}-{NUMBER}"),
            "bonafide certificate": ("num_format_bonafide", "BON-{YEAR}-{NUMBER}"),
            "bonafide": ("num_format_bonafide", "BON-{YEAR}-{NUMBER}"),
            "merit certificate": ("num_format_merit", "MERIT-{YEAR}-{NUMBER}"),
            "academic excellence": ("num_format_merit", "MERIT-{YEAR}-{NUMBER}"),
            "attendance certificate": ("num_format_attendance", "ATT-{YEAR}-{NUMBER}"),
            "sports certificate": ("num_format_sports", "SPORTS-{YEAR}-{NUMBER}"),
            "sports & extra curricular": ("num_format_sports", "SPORTS-{YEAR}-{NUMBER}"),
            "extra curricular": ("num_format_sports", "SPORTS-{YEAR}-{NUMBER}"),
            "experience certificate": ("num_format_exp", "EXP-{YEAR}-{NUMBER}"),
            "experience": ("num_format_exp", "EXP-{YEAR}-{NUMBER}"),
            "appointment letter": ("num_format_appt", "APPT-{YEAR}-{NUMBER}"),
            "appointment": ("num_format_appt", "APPT-{YEAR}-{NUMBER}"),
            "salary certificate": ("num_format_salcert", "SALCERT-{YEAR}-{NUMBER}"),
            "income certificate": ("num_format_salcert", "INC-{YEAR}-{NUMBER}"),
            "salary / income certificate": ("num_format_salcert", "INC-{YEAR}-{NUMBER}"),
            "relieving letter": ("num_format_rel", "REL-{YEAR}-{NUMBER}"),
            "relieving": ("num_format_rel", "REL-{YEAR}-{NUMBER}"),
            "appreciation certificate": ("num_format_appr", "APPR-{YEAR}-{NUMBER}"),
            "appreciation": ("num_format_appr", "APPR-{YEAR}-{NUMBER}"),
            "fee structure": ("num_format_feestr", "FSC-{YEAR}-{NUMBER}"),
            "fee structure & no dues certificate": ("num_format_feestr", "FSC-{YEAR}-{NUMBER}"),
            "no dues certificate": ("num_format_nodues", "NODUES-{YEAR}-{NUMBER}")
        }

        if clean in key_map:
            fmt_key, default_fmt = key_map[clean]
            return DocumentService.get_setting(fmt_key, default or default_fmt)

        for k, (fmt_key, default_fmt) in key_map.items():
            if k in clean or clean in k:
                return DocumentService.get_setting(fmt_key, default or default_fmt)

        fallback_key = f"num_format_{clean.replace(' ', '_')}"
        fallback_default = default or f"{clean[:3].upper()}-{{YEAR}}-{{NUMBER}}"
        return DocumentService.get_setting(fallback_key, fallback_default)

    @staticmethod
    def get_institution_branding():
        """Fetches the active institution name or code for document branding."""
        db = get_session()
        try:
            inst = db.query(InstitutionSettings).first()
            if inst:
                val = inst.app_title or inst.name
                if val and str(val).strip():
                    return str(val).strip()
        except Exception:
            pass
        finally:
            db.close()
        return DocumentService.get_setting("institution_name", "UEMS")

    @staticmethod
    def format_preview(format_string: str, number: int, inst_name: str = None, session_str: str = None) -> str:
        """
        Transforms any format pattern into a branded document identifier.
        Supports case-insensitive tokens:
          {INSTITUTE}, {INST}, {CODE} -> Institution name or branding code (e.g. UPSC)
          {SESSION}                  -> Active academic session (e.g. 2026)
          {YEAR}, {YYYY}             -> 4-digit current year (e.g. 2026)
          {YY}                       -> 2-digit current year (e.g. 26)
          {NUMBER}, {NUM}            -> 4-digit zero-padded sequence (e.g. 0001, 0021)
        """
        import re
        year = datetime.now().year
        if inst_name is None:
            inst_name = DocumentService.get_institution_branding()
        if session_str is None:
            session_str = DocumentService.get_setting("session", str(year))

        res = str(format_string)
        # {INSTITUTE} / {INST} / {CODE}
        res = re.sub(r'\{institute\}|\{inst\}|\{code\}', inst_name, res, flags=re.IGNORECASE)
        # {SESSION}
        res = re.sub(r'\{session\}', session_str, res, flags=re.IGNORECASE)
        # {YEAR} / {YYYY}
        res = re.sub(r'\{year\}|\{yyyy\}', str(year), res, flags=re.IGNORECASE)
        # {YY}
        res = re.sub(r'\{yy\}', str(year)[-2:], res, flags=re.IGNORECASE)
        # {NUMBER} / {NUM}
        if re.search(r'\{number\}|\{num\}', res, flags=re.IGNORECASE):
            res = re.sub(r'\{number\}|\{num\}', f"{number:04d}", res, flags=re.IGNORECASE)
        else:
            res = f"{res}-{number:04d}"
        return res

    @staticmethod
    def get_actual_next_counter(document_type):
        """
        Intelligently determines the next available number (1-based), scanning
        both the saved setting and historical database records to guarantee zero collisions.
        """
        import re
        db = get_session()
        doc_lower = str(document_type).lower()

        counter_key = "counter_id"
        table_cols = []
        if "voucher" in doc_lower:
            counter_key = "counter_voucher"
            table_cols = [("fee_vouchers", "voucher_no")]
        elif "fee" in doc_lower or "receipt" in doc_lower or "payment" in doc_lower:
            counter_key = "counter_fee"
            table_cols = [("fee_payments", "receipt_no")]
        elif "slc" in doc_lower or "leaving" in doc_lower:
            counter_key = "counter_slc"
            table_cols = [("document_history", "document_number")]
        elif "char" in doc_lower:
            counter_key = "counter_char"
            table_cols = [("document_history", "document_number")]
        elif "eng" in doc_lower:
            counter_key = "counter_eng"
            table_cols = [("document_history", "document_number")]
        elif "emp" in doc_lower:
            counter_key = "counter_emp"
            table_cols = [("employees", "emp_id")]
        elif "sal" in doc_lower or "slip" in doc_lower:
            counter_key = "counter_sal"
            table_cols = [("payroll_records", "receipt_no")]
        elif "adm" in doc_lower:
            counter_key = "counter_adm"
            table_cols = [("students", "admission_number")]
        elif "transcript" in doc_lower:
            counter_key = "counter_trans"
            table_cols = [("document_history", "document_number")]
        elif "id" in doc_lower:
            counter_key = "counter_id"
            table_cols = [("students", "student_id")]

        saved_cnt = int(DocumentService.get_setting(counter_key, "0"))
        max_seen = saved_cnt

        for tbl, col in table_cols:
            try:
                rows = db.execute(text(f"SELECT {col} FROM {tbl} WHERE {col} IS NOT NULL")).fetchall()
                for r in rows:
                    val = str(r[0])
                    digits = re.findall(r'\d+', val)
                    if digits:
                        num = int(digits[-1])
                        if num > max_seen:
                            max_seen = num
            except Exception:
                pass

        db.close()
        return max_seen + 1

    @staticmethod
    def get_counter(document_type_or_key="Fee"):
        clean = str(document_type_or_key).lower().replace(" ", "_")
        if not clean.startswith("counter_"): clean = f"counter_{clean}"
        return int(DocumentService.get_setting(clean, "0"))

    @staticmethod
    def increment_counter(document_type_or_key="Fee", step=1):
        clean = str(document_type_or_key).lower().replace(" ", "_")
        if not clean.startswith("counter_"): clean = f"counter_{clean}"
        curr = int(DocumentService.get_setting(clean, "0")) + step
        DocumentService._save_setting_to_db(clean, str(curr))
        return curr

    @staticmethod
    def set_counter(document_type_or_key="Fee", value=0):
        clean = str(document_type_or_key).lower().replace(" ", "_")
        if not clean.startswith("counter_"): clean = f"counter_{clean}"
        DocumentService._save_setting_to_db(clean, str(value))

    @staticmethod
    def get_next_number(document_type="Fee Voucher"):
        return DocumentService.generate_number(document_type)

    @staticmethod
    def generate_number(document_type, session=None):
        own_session = False
        db = session
        if db is None:
            db = get_session()
            own_session = True

        try:
            doc_lower = str(document_type).lower()

            check_targets = []
            if "voucher" in doc_lower:
                check_targets.append(("fee_vouchers", "voucher_no"))
            elif "fee" in doc_lower or "receipt" in doc_lower or "payment" in doc_lower:
                check_targets.append(("fee_payments", "receipt_no"))
            elif "admission" in doc_lower:
                check_targets.append(("students", "admission_number"))
            elif "id" in doc_lower and "emp" not in doc_lower:
                check_targets.append(("students", "student_id"))
            elif "emp" in doc_lower:
                check_targets.append(("employees", "emp_id"))
            elif "sal" in doc_lower or "slip" in doc_lower or "payroll" in doc_lower:
                check_targets.append(("payroll_records", "receipt_no"))
            else:
                check_targets.append(("document_history", "document_number"))

            format_string = DocumentService.get_format(document_type)

            counter_key = f"counter_{doc_lower.replace(' ', '_')}"
            if "voucher" in doc_lower: counter_key = "counter_voucher"
            elif "fee" in doc_lower or "receipt" in doc_lower or "payment" in doc_lower: counter_key = "counter_fee"
            elif "slc" in doc_lower or "leaving" in doc_lower: counter_key = "counter_slc"
            elif "char" in doc_lower: counter_key = "counter_char"
            elif "eng" in doc_lower: counter_key = "counter_eng"
            elif "emp" in doc_lower: counter_key = "counter_emp"
            elif "sal" in doc_lower or "slip" in doc_lower: counter_key = "counter_sal"
            elif "id" in doc_lower: counter_key = "counter_id"
            elif "adm" in doc_lower: counter_key = "counter_adm"
            elif "transcript" in doc_lower: counter_key = "counter_trans"

            current_counter = int(DocumentService.get_setting(counter_key, "0", session=db))
            inst_brand = DocumentService.get_institution_branding()
            inst_session = DocumentService.get_setting("session", str(datetime.now().year), session=db)

            while True:
                current_counter += 1
                final_number = DocumentService.format_preview(
                    format_string, current_counter, inst_brand, inst_session
                )

                collision = False
                for table_name, col_name in check_targets:
                    try:
                        res = db.execute(text(f"SELECT 1 FROM {table_name} WHERE {col_name} = :num"), {"num": final_number}).fetchone()
                        if res:
                            collision = True
                            break
                    except Exception:
                        pass

                if not collision:
                    break

            DocumentService._save_setting_to_db(counter_key, str(current_counter), session=db)
            if own_session:
                db.commit()
            return final_number
        finally:
            if own_session:
                db.close()

    @staticmethod
    def log_document(student_id=None, document_type="", document_number="", file_path="", employee_id=None):
        if DocumentHistory is None: return
        db = get_session()
        try:
            doc = DocumentHistory(
                student_id=student_id,
                employee_id=employee_id,
                document_type=document_type,
                document_number=document_number,
                file_path=file_path
            )
            db.add(doc)
            db.commit()
            try:
                from core.state_manager import app_state
                app_state.notify_data_changed()
            except Exception:
                pass
        except Exception as e:
            db.rollback()
            print(f"Error logging document history: {e}")
        finally:
            db.close()

    @staticmethod
    def get_student_documents(student_id):
        """Returns unified list of generated and uploaded documents for a student."""
        db = get_session()
        results = []
        try:
            from database.models.documents import DocumentHistory, ManagedDocument
            # 1. Generated Documents (Certificates, ID Cards, etc.)
            if DocumentHistory is not None:
                gen_docs = db.query(DocumentHistory).filter_by(student_id=student_id).order_by(DocumentHistory.id.desc()).all()
                for d in gen_docs:
                    results.append({
                        "id": d.id,
                        "type": "Generated",
                        "source": "generated",
                        "category": d.document_type,
                        "title": f"{d.document_type} ({d.document_number})",
                        "doc_number": d.document_number,
                        "date": str(d.created_at).split(" ")[0] if d.created_at else "-",
                        "file_path": d.file_path,
                        "raw_obj": d
                    })

            # 2. Uploaded Documents (Scans, B-Form, TC, Medical, etc.)
            up_docs = db.query(ManagedDocument).filter_by(entity_type="Student", entity_id=student_id, is_archived=0).order_by(ManagedDocument.id.desc()).all()
            for m in up_docs:
                results.append({
                    "id": m.id,
                    "type": "Uploaded",
                    "source": "uploaded",
                    "category": m.file_category,
                    "title": m.title,
                    "doc_number": m.original_filename,
                    "date": str(m.upload_date).split(" ")[0] if m.upload_date else "-",
                    "file_path": m.storage_path,
                    "raw_obj": m
                })
            return results
        except Exception as e:
            print(f"Error fetching student documents: {e}")
            return []
        finally:
            db.close()

    @staticmethod
    def get_employee_documents(employee_id):
        """Returns unified list of generated and uploaded documents for an employee/teacher."""
        db = get_session()
        results = []
        try:
            from database.models.documents import DocumentHistory, ManagedDocument
            # 1. Generated Documents (Salary Slips, Experience Certificates, etc.)
            if DocumentHistory is not None:
                gen_docs = db.query(DocumentHistory).filter_by(employee_id=employee_id).order_by(DocumentHistory.id.desc()).all()
                for d in gen_docs:
                    results.append({
                        "id": d.id,
                        "type": "Generated",
                        "source": "generated",
                        "category": d.document_type,
                        "title": f"{d.document_type} ({d.document_number})",
                        "doc_number": d.document_number,
                        "date": str(d.created_at).split(" ")[0] if d.created_at else "-",
                        "file_path": d.file_path,
                        "raw_obj": d
                    })

            # 2. Uploaded Documents (CNIC, Degree, Resume, Contract, etc.)
            up_docs = db.query(ManagedDocument).filter_by(entity_type="Employee", entity_id=employee_id, is_archived=0).order_by(ManagedDocument.id.desc()).all()
            for m in up_docs:
                results.append({
                    "id": m.id,
                    "type": "Uploaded",
                    "source": "uploaded",
                    "category": m.file_category,
                    "title": m.title,
                    "doc_number": m.original_filename,
                    "date": str(m.upload_date).split(" ")[0] if m.upload_date else "-",
                    "file_path": m.storage_path,
                    "raw_obj": m
                })
            return results
        except Exception as e:
            print(f"Error fetching employee documents: {e}")
            return []
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # CENTRALIZED MANAGED DOCUMENTS (ARCHIVE & UPLOADS)
    # ──────────────────────────────────────────────────────────────────────────
    @staticmethod
    def get_documents_storage_dir():
        from database.connection import DB_DIR
        base_dir = os.path.dirname(DB_DIR)
        doc_dir = os.path.join(base_dir, "documents")
        os.makedirs(doc_dir, exist_ok=True)
        return doc_dir

    @staticmethod
    def upload_managed_document(source_file_path, title, category="General",
                                entity_type=None, entity_id=None, description="",
                                tags="", uploaded_by="Admin"):
        """Safely stores a user-uploaded file into the institutional document repository and indexes it."""
        import shutil
        import uuid
        from database.models.documents import ManagedDocument
        from core.state_manager import app_state

        if not os.path.exists(source_file_path):
            return False, "Selected source file does not exist."

        title = title.strip()
        if not title:
            return False, "Document title is required."

        orig_name = os.path.basename(source_file_path)
        ext = os.path.splitext(orig_name)[1].lower()
        file_size = os.path.getsize(source_file_path)
        doc_uuid = uuid.uuid4().hex

        # Subdirectory by category
        storage_root = DocumentService.get_documents_storage_dir()
        cat_folder = os.path.join(storage_root, category.lower().replace(" ", "_"))
        os.makedirs(cat_folder, exist_ok=True)

        target_name = f"{doc_uuid}{ext}"
        dest_path = os.path.join(cat_folder, target_name)

        try:
            shutil.copy2(source_file_path, dest_path)
        except Exception as e:
            return False, f"Failed copying file: {str(e)}"

        db = get_session()
        try:
            doc = ManagedDocument(
                file_uuid=doc_uuid,
                title=title,
                original_filename=orig_name,
                file_category=category,
                entity_type=entity_type,
                entity_id=entity_id,
                file_size=file_size,
                file_extension=ext,
                storage_path=dest_path,
                description=description.strip() if description else None,
                tags=tags.strip() if tags else None,
                uploaded_by=uploaded_by,
                is_archived=0
            )
            db.add(doc)
            db.commit()
            app_state.notify_data_changed()
            return True, "Document uploaded and indexed successfully."
        except Exception as e:
            db.rollback()
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False, f"Database indexing failed: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def get_managed_documents(category=None, entity_type=None, entity_id=None, search=None, include_archived=False):
        from database.models.documents import ManagedDocument
        from sqlalchemy import or_

        db = get_session()
        try:
            q = db.query(ManagedDocument)
            if not include_archived:
                q = q.filter(ManagedDocument.is_archived == 0)
            if category and category != "All":
                q = q.filter(ManagedDocument.file_category == category)
            if entity_type:
                q = q.filter(ManagedDocument.entity_type == entity_type)
            if entity_id:
                q = q.filter(ManagedDocument.entity_id == entity_id)
            if search:
                term = f"%{search.strip()}%"
                q = q.filter(or_(
                    ManagedDocument.title.ilike(term),
                    ManagedDocument.original_filename.ilike(term),
                    ManagedDocument.tags.ilike(term),
                    ManagedDocument.description.ilike(term)
                ))
            return q.order_by(ManagedDocument.id.desc()).all()
        finally:
            db.close()

    @staticmethod
    def archive_managed_document(doc_id):
        from database.models.documents import ManagedDocument
        from core.state_manager import app_state
        db = get_session()
        try:
            doc = db.query(ManagedDocument).filter_by(id=doc_id).first()
            if not doc:
                return False, "Document not found."
            doc.is_archived = 1
            db.commit()
            app_state.notify_data_changed()
            return True, "Document archived."
        except Exception as e:
            db.rollback()
            return False, f"Error archiving document: {str(e)}"
        finally:
            db.close()

    @staticmethod
    def get_all_generated_documents(search=None, doc_type=None, limit=300):
        from database.models.documents import DocumentHistory
        from sqlalchemy import or_, cast, String
        db = get_session()
        try:
            q = db.query(DocumentHistory)
            if doc_type and doc_type not in ["All", "All Document Types"]:
                q = q.filter(DocumentHistory.document_type == doc_type)
            if search:
                term = f"%{search.strip()}%"
                q = q.filter(or_(
                    DocumentHistory.document_number.ilike(term),
                    DocumentHistory.document_type.ilike(term),
                    cast(DocumentHistory.student_id, String).ilike(term)
                ))
            return q.order_by(DocumentHistory.id.desc()).limit(limit).all()
        finally:
            db.close()