import os
import json
from database.connection import get_session, DB_DIR
from database.models.pdf_templates import PDFTemplateMapping
from core.document_service import DocumentService
from core.builtin_pdf_generator import BuiltinPDFGenerator
import pymupdf as fitz

class PDFGenerationService:
    @staticmethod
    def generate_document(document_type, data_dict, output_path):
        """
        Renders document via Built-in Engine or Custom PDF Template depending on Settings.
        When Custom PDF Templates is OFF (or if template is missing), generates clean
        built-in A4 ReportLab documents with institution branding.
        """
        
        # SMART PATH RESOLVER
        if not os.path.isabs(output_path) and not os.path.dirname(output_path):
            target_dir = os.path.join(os.path.dirname(DB_DIR), "generated_docs", document_type.replace(" ", "_"))
            output_path = os.path.join(target_dir, output_path)

        dir_name = os.path.dirname(output_path)
        if dir_name:
            try:
                os.makedirs(dir_name, exist_ok=True)
            except Exception as e:
                return False, f"Failed to create directory for PDF: {e}"

        # Check Settings toggle: Custom PDF Templates [ON / OFF]
        custom_enabled = DocumentService.get_setting("custom_pdf_enabled", "0")
        if str(custom_enabled).strip() != "1":
            return BuiltinPDFGenerator.generate(document_type, data_dict, output_path)

        db = get_session()
        try:
            mapping_record = db.query(PDFTemplateMapping).filter_by(document_type=document_type).first()
            if not mapping_record or not mapping_record.template_path or not os.path.exists(mapping_record.template_path):
                # Graceful fallback to built-in generator so operations never fail
                return BuiltinPDFGenerator.generate(document_type, data_dict, output_path)

            doc = fitz.open(mapping_record.template_path)

            try:
                mappings = json.loads(mapping_record.mapping_data)
            except (json.JSONDecodeError, ValueError, TypeError):
                mappings = {}

            active_mappings = mappings.get("mappings", mappings)
            missing_images = []

            # Build robust multi-key normalized dictionary for mapping
            clean_data = {}
            for k, v in data_dict.items():
                k_clean = str(k).lower().strip().replace(" ", "_")
                clean_data[k_clean] = v
                k_norm = k_clean.replace(".", "_")
                clean_data[k_norm] = v
                for prefix in ("student_", "fee_", "academic_", "institution_", "parent_"):
                    if k_norm.startswith(prefix):
                        clean_data[k_norm[len(prefix):]] = v

            for key, field_info in active_mappings.items():
                try:
                    field_type = field_info.get('type', 'text')
                    page_num = int(field_info.get('page', 1)) - 1
                    raw_x = float(field_info.get('x', 0))
                    raw_y = float(field_info.get('y', 0))
                    w = float(field_info.get('width', 180))
                    h = float(field_info.get('height', 24))
                    size = int(field_info.get('size', 11))
                    is_pct = field_info.get('is_percentage', False)
                except (KeyError, TypeError, ValueError):
                    continue

                mapped_key_clean = str(key).lower().strip().replace(" ", "_")
                base_key = mapped_key_clean.split('_copy')[0].replace(".", "_")
                raw_value = clean_data.get(base_key)
                if raw_value is None:
                    for prefix in ("student_", "fee_", "academic_", "institution_"):
                        if f"{prefix}{base_key}" in clean_data:
                            raw_value = clean_data[f"{prefix}{base_key}"]
                            break

                value_str = "" if raw_value is None else str(raw_value).strip()

                if page_num >= 0 and page_num < len(doc):
                    page = doc[page_num]
                    page_rect = page.rect

                    # Calculate Exact Coordinates safely using percentages
                    if is_pct:
                        abs_x = (raw_x / 100.0) * page_rect.width
                        abs_y = (raw_y / 100.0) * page_rect.height
                        abs_w = (w / 100.0) * page_rect.width
                        abs_h = (h / 100.0) * page_rect.height
                    else:
                        abs_x, abs_y, abs_w, abs_h = raw_x, raw_y, w, h

                    # Ensure coordinates stay within page boundaries
                    abs_x = max(0, min(abs_x, page_rect.width - 10))
                    abs_y = max(0, min(abs_y, page_rect.height - 10))

                    # Check if key implies image OR value is an existing image path on disk or URL
                    resolved_img_path = BuiltinPDFGenerator.resolve_image_path(value_str)
                    is_image_file = bool(resolved_img_path and os.path.exists(resolved_img_path))

                    is_image_field = (
                        field_type == "image" or 
                        any(term in base_key for term in ["photo", "logo", "signature", "picture", "image", "pic", "avatar", "seal", "stamp"]) or
                        is_image_file or
                        value_str.lower().startswith(("http://", "https://"))
                    )

                    # 1. IMAGE FIELD PIPELINE
                    if is_image_field:
                        if not resolved_img_path or not os.path.exists(resolved_img_path):
                            missing_images.append(base_key)
                            continue # Safely skip. DO NOT print the path as text.
                            
                        img_box = fitz.Rect(abs_x, abs_y, abs_x + abs_w, abs_y + abs_h)
                        try:
                            # keep_proportion=True ensures faces are not distorted (matches object-fit: cover / contain)
                            page.insert_image(img_box, filename=resolved_img_path, keep_proportion=True)
                        except Exception as e:
                            print(f"Failed to load image '{resolved_img_path}': {e}")
                            missing_images.append(base_key)

                    # 2. TEXT FIELD PIPELINE (Strictly skips image file paths)
                    elif value_str and not is_image_file:
                        # Generous bounding box prevents text from being clipped
                        text_box = fitz.Rect(abs_x, abs_y, abs_x + max(abs_w, 220), abs_y + max(abs_h, 25))
                        page.insert_textbox(
                            text_box,
                            value_str,
                            fontsize=size,
                            fontname="helv",
                            color=(0, 0, 0),
                            overlay=True
                        )

            doc.save(output_path)
            doc.close()
            
            if missing_images:
                warning_msg = (
                    "Generated successfully, but with warnings.\n\n"
                    "The following image fields are unavailable (missing photo or invalid path):\n"
                    f"{', '.join(missing_images)}\n\n"
                    "Please upload/select a valid image in the student's profile or settings to display it."
                )
                return True, warning_msg
                
            return True, "Generated successfully."
            
        except Exception as e:
            return False, f"PDF Engine Error: {str(e)}"
        finally:
            db.close()