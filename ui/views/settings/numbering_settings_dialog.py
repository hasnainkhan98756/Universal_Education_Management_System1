import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QGridLayout, QMessageBox, QSpinBox,
    QScrollArea, QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.document_service import DocumentService
from core.state_manager import app_state
from core.theme_manager import ThemeManager

class NumberingSettingsDialog(QDialog):
    """
    Centralized Institutional Settings UI for Document Numbering & Sequences.
    Supports dynamic institution branding tokens ({INSTITUTE}, {YEAR}, {SESSION}, {NUMBER}),
    live preview calculation, collision avoidance, and full vertical responsiveness.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Document Numbering & Sequences")
        self.resize(880, 580)
        self.setMinimumSize(760, 460)

        t = ThemeManager.tokens()
        self.setStyleSheet(f"""
            QDialog {{ background-color: {t.get('bg_surface', '#F8FAFC')}; color: {t.get('text_primary', '#0F172A')}; }}
            QLabel {{ color: {t.get('text_primary', '#0F172A')}; font-size: 12px; }}
            QLineEdit, QSpinBox {{
                background-color: {t.get('input_bg', '#FFFFFF')};
                color: {t.get('text_primary', '#0F172A')};
                padding: 6px 10px;
                border: 1.5px solid {t.get('input_border', '#CBD5E1')};
                border-radius: 6px;
                font-size: 13px;
                min-height: 24px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 2px solid {t.get('accent', '#2563EB')};
            }}
        """)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(20, 16, 20, 16)
        main_lay.setSpacing(12)

        # ── Header Banner ──────────────────────────────────────────────────────
        inst_brand = DocumentService.get_institution_branding()
        header_card = QFrame()
        header_card.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('bg_card', '#FFFFFF')};
                border: 1px solid {t.get('border', '#E2E8F0')};
                border-radius: 10px;
                padding: 10px 14px;
            }}
        """)
        hc_lay = QVBoxLayout(header_card)
        hc_lay.setContentsMargins(8, 6, 8, 6)
        hc_lay.setSpacing(4)

        lbl_title = QLabel("<b>Document Numbering & Sequence Engine</b>")
        lbl_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #1E293B; background: transparent; border: none;")

        lbl_desc = QLabel(
            "Customize document sequence patterns with your institute branding. "
            "Numbers increment automatically and prevent collisions with historical records."
        )
        lbl_desc.setStyleSheet("color: #64748B; font-size: 11px; background: transparent; border: none;")

        lbl_tokens = QLabel(
            f"<b>Branding Tokens:</b> "
            f"<code style='color: #2563EB;'>{{INSTITUTE}}</code> (Active: <b>{inst_brand}</b>) &nbsp;•&nbsp; "
            f"<code style='color: #2563EB;'>{{YEAR}}</code> (e.g. 2026) &nbsp;•&nbsp; "
            f"<code style='color: #2563EB;'>{{SESSION}}</code> &nbsp;•&nbsp; "
            f"<code style='color: #2563EB;'>{{NUMBER}}</code> (Sequence Counter)<br>"
            f"<i>You can also directly write your own custom prefix like <b>UPSC-{{YEAR}}-{{NUMBER}}</b> or <b>DPS/{{NUMBER}}</b>.</i>"
        )
        lbl_tokens.setStyleSheet("color: #334155; font-size: 11px; margin-top: 4px; background: transparent; border: none;")

        hc_lay.addWidget(lbl_title)
        hc_lay.addWidget(lbl_desc)
        hc_lay.addWidget(lbl_tokens)
        main_lay.addWidget(header_card)

        # ── Scrollable Document Type Grid ─────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_lay = QVBoxLayout(scroll_content)
        scroll_lay.setContentsMargins(0, 4, 0, 4)
        scroll_lay.setSpacing(8)

        grid_container = QFrame()
        grid_container.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('bg_card', '#FFFFFF')};
                border: 1px solid {t.get('border', '#E2E8F0')};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        grid = QGridLayout(grid_container)
        grid.setSpacing(10)
        grid.setContentsMargins(12, 12, 12, 12)

        # Table Column Headers
        h0 = QLabel("<b>Document Type</b>")
        h1 = QLabel("<b>Format Pattern</b> <i>({INSTITUTE}, {YEAR}, {NUMBER})</i>")
        h2 = QLabel("<b>Next #</b>")
        h3 = QLabel("<b>Live Preview</b>")

        for h in (h0, h1, h2, h3):
            h.setStyleSheet("color: #475569; font-size: 12px; font-weight: bold; background: transparent; border: none;")

        grid.addWidget(h0, 0, 0)
        grid.addWidget(h1, 0, 1)
        grid.addWidget(h2, 0, 2)
        grid.addWidget(h3, 0, 3)

        self.inputs = {}
        self.counters = {}
        self.previews = {}

        # 10 Document Formats supported across the system
        self.fields = [
            ("School Leaving Cert.", "num_format_slc", "SLC-{YEAR}-{NUMBER}", "counter_slc", "SLC"),
            ("Character Certificate", "num_format_char", "CHAR-{YEAR}-{NUMBER}", "counter_char", "Character Certificate"),
            ("English Proficiency", "num_format_eng", "ENG-{YEAR}-{NUMBER}", "counter_eng", "English Proficiency"),
            ("Fee Voucher", "num_format_voucher", "VOUCH-{YEAR}-{NUMBER}", "counter_voucher", "Fee Voucher"),
            ("Fee Receipt / Payment", "num_format_fee", "FEE-{YEAR}-{NUMBER}", "counter_fee", "Fee Receipt"),
            ("Student ID Card", "num_format_id", "ID-{INSTITUTE}-{YEAR}-{NUMBER}", "counter_id", "Student ID"),
            ("Admission Form", "num_format_adm", "ADM-{INSTITUTE}-{YEAR}-{NUMBER}", "counter_adm", "Admission Form"),
            ("Exam Transcript", "num_format_trans", "TRANS-{YEAR}-{NUMBER}", "counter_trans", "Transcript"),
            ("Employee / Staff ID", "num_format_emp", "EMP-{YEAR}-{NUMBER}", "counter_emp", "Employee ID"),
            ("Staff Salary Slip", "num_format_sal", "SAL-{YEAR}-{NUMBER}", "counter_sal", "Salary Slip")
        ]

        row = 1
        for label_text, fmt_key, default_fmt, cnt_key, doc_type in self.fields:
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            lbl.setStyleSheet("color: #1E293B; background: transparent; border: none;")

            inp_fmt = QLineEdit()
            current_val = DocumentService.get_setting(fmt_key, default_fmt)
            inp_fmt.setText(current_val)
            inp_fmt.setPlaceholderText(default_fmt)

            inp_cnt = QSpinBox()
            inp_cnt.setRange(1, 9999999)
            inp_cnt.setFixedWidth(100)
            
            # Intelligent Next Number auto-detection
            next_num = DocumentService.get_actual_next_counter(doc_type)
            inp_cnt.setValue(next_num)

            # Live Preview Label
            lbl_preview = QLabel()
            lbl_preview.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            lbl_preview.setStyleSheet(
                "background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
                "border-radius: 6px; padding: 4px 10px;"
            )
            lbl_preview.setMinimumWidth(160)

            grid.addWidget(lbl, row, 0)
            grid.addWidget(inp_fmt, row, 1)
            grid.addWidget(inp_cnt, row, 2)
            grid.addWidget(lbl_preview, row, 3)

            self.inputs[fmt_key] = inp_fmt
            self.counters[cnt_key] = inp_cnt
            self.previews[fmt_key] = (lbl_preview, inp_fmt, inp_cnt, doc_type)

            # Live preview triggers
            inp_fmt.textChanged.connect(lambda _, k=fmt_key: self._update_preview(k))
            inp_cnt.valueChanged.connect(lambda _, k=fmt_key: self._update_preview(k))
            self._update_preview(fmt_key)

            row += 1

        scroll_lay.addWidget(grid_container)
        scroll.setWidget(scroll_content)
        main_lay.addWidget(scroll, 1)

        # ── Fixed Bottom Button Bar (Guaranteed visible on all screens) ────────
        btn_bar = QFrame()
        btn_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('bg_card', '#FFFFFF')};
                border-top: 1px solid {t.get('border', '#E2E8F0')};
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        bb_lay = QHBoxLayout(btn_bar)
        bb_lay.setContentsMargins(8, 6, 8, 6)
        bb_lay.setSpacing(10)

        btn_defaults = QPushButton("Reset to Recommended Defaults")
        btn_defaults.setFont(QFont("Segoe UI", 10))
        btn_defaults.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_defaults.setStyleSheet(
            "QPushButton { background: transparent; color: #64748B; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 6px 14px; font-weight: 500; } "
            "QPushButton:hover { background: #F1F5F9; color: #1E293B; border-color: #94A3B8; }"
        )
        btn_defaults.clicked.connect(self._reset_defaults)
        bb_lay.addWidget(btn_defaults)

        bb_lay.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton { background: transparent; color: #64748B; border: 1px solid #CBD5E1; "
            "border-radius: 6px; padding: 8px 18px; font-weight: 600; min-height: 32px; } "
            "QPushButton:hover { background: #FEE2E2; color: #DC2626; border-color: #FCA5A5; }"
        )
        btn_cancel.clicked.connect(self.reject)
        bb_lay.addWidget(btn_cancel)

        btn_save = QPushButton("Save Sequences && Counters")
        btn_save.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(
            "QPushButton { background-color: #059669; color: white; border: none; "
            "border-radius: 6px; padding: 8px 22px; font-weight: bold; min-height: 32px; } "
            "QPushButton:hover { background-color: #047857; } "
            "QPushButton:pressed { background-color: #065F46; }"
        )
        btn_save.clicked.connect(self.save_settings)
        bb_lay.addWidget(btn_save)

        main_lay.addWidget(btn_bar)

    def _update_preview(self, fmt_key: str):
        if fmt_key not in self.previews:
            return
        lbl_preview, inp_fmt, inp_cnt, _ = self.previews[fmt_key]
        fmt_text = inp_fmt.text().strip()
        cnt_val = inp_cnt.value()
        try:
            preview_str = DocumentService.format_preview(fmt_text, cnt_val)
            lbl_preview.setText(preview_str)
        except Exception:
            lbl_preview.setText(f"{fmt_text} ({cnt_val})")

    def _reset_defaults(self):
        confirm = QMessageBox.question(
            self,
            "Reset Defaults",
            "Reset all document format patterns to recommended institutional templates?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            for _, fmt_key, default_fmt, cnt_key, doc_type in self.fields:
                if fmt_key in self.inputs:
                    self.inputs[fmt_key].setText(default_fmt)
                    self._update_preview(fmt_key)

    def save_settings(self):
        for fmt_key, inp in self.inputs.items():
            val = inp.text().strip()
            if not val:
                QMessageBox.warning(self, "Invalid Format", "Document format patterns cannot be empty.")
                inp.setFocus()
                return
            if not re.search(r'\{number\}|\{num\}', val, re.IGNORECASE):
                confirm = QMessageBox.question(
                    self,
                    "Missing Number Token",
                    f"Format '{val}' does not include '{{NUMBER}}'.\n"
                    "The system will automatically append sequence numbers at the end.\n\n"
                    "Do you want to keep this pattern?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    inp.setFocus()
                    return

            DocumentService._save_setting_to_db(fmt_key, val)

        for cnt_key, sp in self.counters.items():
            # Counter stored in DB is last used number, so next generated will be sp.value()
            DocumentService._save_setting_to_db(cnt_key, str(sp.value() - 1))

        try:
            app_state.notify_data_changed()
        except Exception:
            pass

        QMessageBox.information(
            self,
            "Settings Saved",
            "Document formats, branding sequences, and sequence counters saved permanently."
        )
        self.accept()