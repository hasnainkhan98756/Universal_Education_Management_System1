import os
import urllib.parse
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTabWidget, QMessageBox, QFrame, QAbstractItemView, 
    QGridLayout, QFormLayout, QLineEdit, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QColor, QDesktopServices

from core.communication_service import CommunicationService
from core.academic_service import AcademicService
from core.state_manager import app_state
from core.theme_manager import ThemeManager
from core.icon_manager import icon_mgr
from ui.components.stitch_widgets import (
    PageHeader, MetricCard, ModernButton, ModernCard, StatusBadge,
    style_modern_table, style_modern_tabs
)

class CommunicationView(QWidget):
    def __init__(self):
        super().__init__()
        t = ThemeManager.tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        btn_refresh = ModernButton("Live Refresh Queue", icon_name="rotate-cw", variant="secondary")
        btn_refresh.clicked.connect(self.refresh_all)

        header = PageHeader(
            title="Messages & Communications",
            subtitle="Unified multi-channel broadcasts, automated gateways, and communication audits",
            icon_name="mail",
            actions=[btn_refresh]
        )
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_dashboard_tab(), "Dashboard & Audit")
        self.tabs.setTabIcon(0, icon_mgr.get_icon("bar-chart-2", color=t["text_secondary"]))

        self.tabs.addTab(self.create_campaign_tab(), "Multi-Channel Broadcasts")
        self.tabs.setTabIcon(1, icon_mgr.get_icon("send", color=t["text_secondary"]))

        self.tabs.addTab(self.create_templates_tab(), "Smart Templates")
        self.tabs.setTabIcon(2, icon_mgr.get_icon("file-text", color=t["text_secondary"]))

        self.tabs.addTab(self.create_gateway_tab(), "Gateways (Email/SMS)")
        self.tabs.setTabIcon(3, icon_mgr.get_icon("settings", color=t["text_secondary"]))

        main_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.refresh_all)
        self.refresh_all()

    def showEvent(self, event):
        self.refresh_all()
        super().showEvent(event)

    def _table(self):
        tbl = QTableWidget()
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setDefaultSectionSize(38)
        tbl.setAlternatingRowColors(True)
        style_modern_table(tbl)
        return tbl

    def refresh_all(self):
        self.load_dashboard()
        self.load_templates()
        self.load_gateways()

    # ==========================================
    # TAB 1: DASHBOARD & AUDIT LOG
    # ==========================================
    def create_dashboard_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(14)
        
        grid = QHBoxLayout()
        grid.setSpacing(14)
        self.lbl_wa = MetricCard("WhatsApp (Free)", "0", "Opened in WA", "message-square", "#10B981")
        self.lbl_sms = MetricCard("SMS (Free App)", "0", "Opened in SMS", "send", "#0D9488")
        self.lbl_email = MetricCard("Emails Delivered", "0", "Auto Delivered", "mail", "#2563EB")
        self.lbl_queued = MetricCard("Pending in Queue", "0", "Outbox Queue", "clock", "#D97706")
        self.lbl_failed = MetricCard("Failed / Issues", "0", "Delivery Issues", "alert-triangle", "#DC2626")
        grid.addWidget(self.lbl_wa)
        grid.addWidget(self.lbl_sms)
        grid.addWidget(self.lbl_email)
        grid.addWidget(self.lbl_queued)
        grid.addWidget(self.lbl_failed)
        lay.addLayout(grid)

        tbl_card = ModernCard()
        tbl_lay = QVBoxLayout(tbl_card)
        tbl_lay.setContentsMargins(16, 14, 16, 14)
        tbl_lay.setSpacing(10)

        t_lbl = QLabel("Universal Communication Audit Log (Immutable History)")
        t_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        tbl_lay.addWidget(t_lbl)

        self.tbl_log = self._table()
        self.tbl_log.setColumnCount(7)
        self.tbl_log.setHorizontalHeaderLabels(["Date & Time", "Recipient", "Contact", "Channel", "Segments", "Status", "Source Module"])
        tbl_lay.addWidget(self.tbl_log)
        lay.addWidget(tbl_card)

        return page

    def load_dashboard(self):
        stats = CommunicationService.get_dashboard_stats()
        self.lbl_wa.value_label.setText(str(stats.get("sent_wa", 0)))
        self.lbl_sms.value_label.setText(str(stats.get("sent_sms", 0)))
        self.lbl_email.value_label.setText(str(stats.get("sent_email", 0)))
        self.lbl_queued.value_label.setText(str(stats.get("queued", 0)))
        self.lbl_failed.value_label.setText(str(stats.get("failed", 0)))
        
        self.tbl_log.setRowCount(len(stats["logs"]))
        for r, log in enumerate(stats["logs"]):
            self.tbl_log.setItem(r, 0, QTableWidgetItem(log.created_at))
            self.tbl_log.setItem(r, 1, QTableWidgetItem(log.recipient_name))
            self.tbl_log.setItem(r, 2, QTableWidgetItem(log.recipient_contact))
            self.tbl_log.setItem(r, 3, QTableWidgetItem(log.channel))
            self.tbl_log.setItem(r, 4, QTableWidgetItem(str(log.segments)))
            
            # Status Badge
            badge_variant = "neutral"
            if log.status in ["Sent", "Opened in App", "Opened in SMS App"]:
                badge_variant = "success"
            elif log.status == "Failed":
                badge_variant = "danger"
            else:
                badge_variant = "warning"
            badge = StatusBadge(log.status, variant=badge_variant)
            
            badge_container = QWidget()
            badge_container.setStyleSheet("background: transparent;")
            b_lay = QHBoxLayout(badge_container)
            b_lay.setContentsMargins(0, 0, 0, 0)
            b_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_lay.addWidget(badge)
            self.tbl_log.setCellWidget(r, 5, badge_container)
            
            self.tbl_log.setItem(r, 6, QTableWidgetItem(log.source_module or "Manual"))

    # ==========================================
    # TAB 2: BROADCASTS & MULTI-CHANNEL
    # ==========================================
    def create_campaign_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(14)
        
        filter_card = ModernCard()
        fc_lay = QVBoxLayout(filter_card)
        fc_lay.setContentsMargins(16, 12, 16, 12)
        fc_lay.setSpacing(10)

        ctrl1 = QHBoxLayout()
        ctrl1.setSpacing(12)
        lbl_mod = QLabel("Live Integration Source:")
        lbl_mod.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.cb_module = QComboBox()
        self.cb_module.addItems(["Fee Defaulters (Phase 5 Live Integration)", "Timetable Updates (Phase 15)", "General Announcement"])
        self.cb_module.currentIndexChanged.connect(self.clear_audience_grid)

        lbl_cls = QLabel("Target Class:")
        lbl_cls.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.cb_class = QComboBox()
        self.cb_class.currentIndexChanged.connect(self.clear_audience_grid)
        
        ctrl1.addWidget(lbl_mod)
        ctrl1.addWidget(self.cb_module, 2)
        ctrl1.addWidget(lbl_cls)
        ctrl1.addWidget(self.cb_class, 1)
        ctrl1.addStretch()
        fc_lay.addLayout(ctrl1)

        ctrl2 = QHBoxLayout()
        ctrl2.setSpacing(12)
        lbl_chan = QLabel("Communication Channel:")
        lbl_chan.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.cb_channel = QComboBox()
        self.cb_channel.addItems(["WhatsApp (Manual App)", "Email (Auto API)", "SMS (Auto API)"])
        self.cb_channel.currentIndexChanged.connect(self.toggle_queue_button_visibility)
        
        lbl_tpl = QLabel("Template:")
        lbl_tpl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.cb_template = QComboBox()
        
        btn_fetch = ModernButton("Load Target Audience", icon_name="users", variant="primary")
        btn_fetch.clicked.connect(self.fetch_audience)

        ctrl2.addWidget(lbl_chan)
        ctrl2.addWidget(self.cb_channel, 1)
        ctrl2.addWidget(lbl_tpl)
        ctrl2.addWidget(self.cb_template, 2)
        ctrl2.addWidget(btn_fetch)
        ctrl2.addStretch()
        fc_lay.addLayout(ctrl2)
        lay.addWidget(filter_card)

        tbl_card = ModernCard()
        tbl_lay = QVBoxLayout(tbl_card)
        tbl_lay.setContentsMargins(16, 14, 16, 14)
        tbl_lay.setSpacing(12)

        self.tbl_audience = self._table()
        self.tbl_audience.setColumnCount(5)
        self.tbl_audience.setHorizontalHeaderLabels(["Student Name", "Class", "Resolved Contact", "Dynamic Data Passed", "Action"])
        tbl_lay.addWidget(self.tbl_audience)

        self.btn_queue = ModernButton("Confirm & Prepare Broadcast", icon_name="send", variant="primary")
        self.btn_queue.setFixedHeight(38)
        self.btn_queue.clicked.connect(self.queue_campaign)
        self.btn_queue.setEnabled(False)
        tbl_lay.addWidget(self.btn_queue)

        lay.addWidget(tbl_card)

        self.current_audience_data = []
        return page

    def toggle_queue_button_visibility(self):
        chan = self.cb_channel.currentText()
        if chan == "WhatsApp (Manual App)":
            self.btn_queue.hide()
        else:
            self.btn_queue.show()
        self.clear_audience_grid()

    def clear_audience_grid(self):
        self.tbl_audience.setRowCount(0)
        self.current_audience_data = []
        self.btn_queue.setEnabled(False)
        self.btn_queue.setText("Confirm & Prepare Broadcast")

    def fetch_audience(self):
        mod = self.cb_module.currentText()
        cid = self.cb_class.currentData() or "All"
        chan = self.cb_channel.currentText()
        
        data = CommunicationService.fetch_audience_data(mod, cid)
        self.tbl_audience.setRowCount(len(data))
        self.current_audience_data = data
        
        valid = 0
        missing = 0
        for r, d in enumerate(data):
            stu = d["student"]
            self.tbl_audience.setItem(r, 0, QTableWidgetItem(f"{stu.first_name} {stu.last_name or ''}"))
            self.tbl_audience.setItem(r, 1, QTableWidgetItem(stu.academic_class.name if stu.academic_class else "N/A"))
            
            contact = CommunicationService.resolve_contact(stu, chan)
            if contact:
                valid += 1
                c_item = QTableWidgetItem(contact)
                c_item.setForeground(QColor("#10B981"))
                
                widget = QWidget()
                widget.setStyleSheet("background: transparent;")
                w_lay = QHBoxLayout(widget)
                w_lay.setContentsMargins(2, 2, 2, 2)
                w_lay.setSpacing(6)
                w_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

                if "WhatsApp" in chan:
                    btn_wa = ModernButton("Send WhatsApp (Free)", icon_name="message-square", variant="success")
                    btn_wa.setFixedHeight(28)
                    btn_wa.clicked.connect(lambda checked=False, row=r, row_data=d, phone=contact: self.open_whatsapp_app(row, row_data, phone))
                    w_lay.addWidget(btn_wa)
                elif "SMS" in chan:
                    btn_sms_free = ModernButton("Open SMS App (Free)", icon_name="send", variant="primary")
                    btn_sms_free.setFixedHeight(28)
                    btn_sms_free.setToolTip("Opens your computer/phone SMS app or device messenger with prefilled text (100% Free of Cost)")
                    btn_sms_free.clicked.connect(lambda checked=False, row=r, row_data=d, phone=contact: self.open_sms_app(row, row_data, phone))
                    w_lay.addWidget(btn_sms_free)
                else:
                    self.tbl_audience.setItem(r, 4, QTableWidgetItem("Will Auto-Queue"))

                if "WhatsApp" in chan or "SMS" in chan:
                    self.tbl_audience.setCellWidget(r, 4, widget)

            else:
                missing += 1
                c_item = QTableWidgetItem(f"Missing {chan.split()[0]}")
                c_item.setForeground(QColor("#EF4444"))
                self.tbl_audience.setItem(r, 4, QTableWidgetItem("-"))
                
            self.tbl_audience.setItem(r, 2, c_item)
            
            # Dynamic variables button
            clean_vars = {k: v for k, v in d["vars"].items() if k not in ["{school_name}", "{date}"]}
            var_lines = [f"{k} = {v}" for k, v in clean_vars.items()]
            info_text = "\n".join(var_lines) if var_lines else "Standard: {student_name}, {class_name}, {father_name}"
            
            btn_view_data = ModernButton("View Variables", icon_name="eye", variant="secondary")
            btn_view_data.setFixedHeight(26)
            btn_view_data.clicked.connect(lambda checked=False, txt=info_text, sname=stu.first_name: QMessageBox.information(
                self, f"Dynamic Data for {sname}", f"The following variables will be injected:\n\n{txt}\n\n(+ generic {{school_name}} and {{date}})"
            ))
            
            v_widget = QWidget()
            v_widget.setStyleSheet("background: transparent;")
            v_lay = QHBoxLayout(v_widget)
            v_lay.setContentsMargins(2, 2, 2, 2)
            v_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v_lay.addWidget(btn_view_data)
            self.tbl_audience.setCellWidget(r, 3, v_widget)
        
        if valid > 0 and chan != "WhatsApp (Manual App)":
            self.btn_queue.setEnabled(True)
            self.btn_queue.show()
            self.btn_queue.setText(f"Confirm & Queue ({valid} Valid, {missing} Missing)")
        elif chan == "WhatsApp (Manual App)":
            self.btn_queue.hide()
        else:
            self.btn_queue.setEnabled(False)
            self.btn_queue.show()
            self.btn_queue.setText("No Valid Recipients Found")

    def open_whatsapp_app(self, row_index, row_data, raw_phone):
        tid = self.cb_template.currentData()
        if not tid: 
            QMessageBox.warning(self, "Select Template", "Please select a Message Template from the dropdown first!")
            return
            
        template = None
        for tpl in CommunicationService.get_templates():
            if tpl.id == tid:
                template = tpl
                break
        if not template:
            return

        student = row_data["student"]
        rendered_msg = CommunicationService.render_message(template.body, student, row_data["vars"])
        
        clean_phone = raw_phone.replace("+", "").replace(" ", "").replace("-", "")
        if clean_phone.startswith("03") and len(clean_phone) == 11:
            clean_phone = "92" + clean_phone[1:]
            
        encoded_msg = urllib.parse.quote(rendered_msg)
        url = QUrl(f"https://wa.me/{clean_phone}?text={encoded_msg}")
        QDesktopServices.openUrl(url)
        
        stu_name = f"{student.first_name} {student.last_name or ''}".strip()
        CommunicationService.log_manual_whatsapp_send(stu_name, raw_phone, template.subject, rendered_msg, row_data["source_module"], row_data["source_id"])
        
        btn = self.tbl_audience.cellWidget(row_index, 4).layout().itemAt(0).widget()
        btn.setText("Opened in WhatsApp")

    def open_sms_app(self, row_index, row_data, raw_phone):
        tid = self.cb_template.currentData()
        if not tid: 
            QMessageBox.warning(self, "Select Template", "Please select a Message Template from the dropdown first!")
            return
            
        template = None
        for tpl in CommunicationService.get_templates():
            if tpl.id == tid:
                template = tpl
                break
        if not template:
            return

        student = row_data["student"]
        rendered_msg = CommunicationService.render_message(template.body, student, row_data["vars"])
        
        clean_phone = raw_phone.replace(" ", "").replace("-", "")
            
        encoded_msg = urllib.parse.quote(rendered_msg)
        # Windows & mobile SMS URL scheme
        url = QUrl(f"sms:{clean_phone}?body={encoded_msg}")
        QDesktopServices.openUrl(url)
        
        stu_name = f"{student.first_name} {student.last_name or ''}".strip()
        CommunicationService.log_manual_sms_send(stu_name, raw_phone, template.subject or "SMS Notification", rendered_msg, row_data["source_module"], row_data["source_id"])
        
        btn = self.tbl_audience.cellWidget(row_index, 4).layout().itemAt(0).widget()
        btn.setText("Opened in SMS App")

    def queue_campaign(self):
        tid = self.cb_template.currentData()
        if not tid:
            QMessageBox.warning(self, "Error", "Select a Template first.")
            return
        
        reply = QMessageBox.question(self, "Confirm Broadcast", "You are about to push this campaign to the Outbox Queue. Continue?")
        if reply == QMessageBox.StandardButton.Yes:
            chan = self.cb_channel.currentText()
            success, msg = CommunicationService.queue_bulk_messages(self.current_audience_data, tid, chan, False)
            if success:
                QMessageBox.information(self, "Campaign Queued", msg)
                self.clear_audience_grid()
                self.load_dashboard()
            else:
                QMessageBox.critical(self, "Error", msg)

    # ==========================================
    # TAB 3: SMART TEMPLATES 
    # ==========================================
    def create_templates_tab(self):
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(14)
        
        form_card = ModernCard()
        fl = QFormLayout(form_card)
        fl.setContentsMargins(18, 16, 18, 16)
        fl.setSpacing(12)

        self.t_id = None
        self.t_name = QLineEdit()
        self.t_name.setMinimumHeight(32)
        self.t_cat = QComboBox()
        self.t_cat.setMinimumHeight(32)
        self.t_cat.addItems(["Fees", "Attendance", "Exams", "Timetable", "General"])
        self.t_chan = QComboBox()
        self.t_chan.setMinimumHeight(32)
        self.t_chan.addItems(["WhatsApp (Manual App)", "Email", "SMS"])
        self.t_body = QTextEdit()
        self.t_body.setMinimumHeight(120)
        self.t_body.textChanged.connect(self.update_char_count)
        
        self.lbl_helper_vars = QLabel()
        self.lbl_helper_vars.setWordWrap(True)
        self.lbl_helper_vars.setStyleSheet("color: #059669; font-size: 12px; font-style: italic; margin-bottom: 5px;")
        self.t_cat.currentTextChanged.connect(self.update_template_helpers)
        
        self.lbl_count = QLabel("Chars: 0 | Segments: 0")
        self.lbl_count.setStyleSheet("color: #64748B; font-weight: bold; font-size: 11px;")
        
        fl.addRow("Template Name:", self.t_name)
        fl.addRow("Category:", self.t_cat)
        fl.addRow("", self.lbl_helper_vars)
        fl.addRow("Target Channel:", self.t_chan)
        fl.addRow("Body:", self.t_body)
        fl.addRow("", self.lbl_count)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_save = ModernButton("Save Template", icon_name="check", variant="primary")
        btn_save.setFixedHeight(34)
        btn_save.clicked.connect(self.save_template)
        btn_clear = ModernButton("Cancel", variant="secondary")
        btn_clear.setFixedHeight(34)
        btn_clear.clicked.connect(self.clear_template_form)
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_clear)
        fl.addRow("", btn_box)
        
        tbl_card = ModernCard()
        tbl_lay = QVBoxLayout(tbl_card)
        tbl_lay.setContentsMargins(16, 14, 16, 14)

        self.tbl_tpl = self._table()
        self.tbl_tpl.setColumnCount(4)
        self.tbl_tpl.setHorizontalHeaderLabels(["Name", "Category", "Channel", "Actions"])
        self.tbl_tpl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tbl_tpl.setColumnWidth(3, 160)
        tbl_lay.addWidget(self.tbl_tpl)
        
        lay.addWidget(form_card, stretch=4)
        lay.addWidget(tbl_card, stretch=6)
        
        self.update_template_helpers()
        return page

    def update_template_helpers(self):
        cat = self.t_cat.currentText()
        if cat == "Fees":
            txt = "Supported: {student_name}, {father_name}, {class_name}, {fee_amount}, {outstanding_amount}, {fee_month}, {school_name}, {date}"
        elif cat == "Timetable":
            txt = "Supported: {student_name}, {father_name}, {class_name}, {subject_name}, {teacher_name}, {day}, {school_name}, {date}"
        elif cat == "Attendance":
            txt = "Supported: {student_name}, {father_name}, {class_name}, {attendance_date}, {school_name}, {date}"
        elif cat == "Exams":
            txt = "Supported: {student_name}, {father_name}, {class_name}, {exam_name}, {percentage}, {grade}, {school_name}, {date}"
        else:
            txt = "Supported: {student_name}, {father_name}, {class_name}, {school_name}, {date}"
        self.lbl_helper_vars.setText(txt)

    def update_char_count(self):
        text = self.t_body.toPlainText()
        chars, segs = CommunicationService.calculate_segments(text)
        self.lbl_count.setText(f"Chars: {chars} | Segments: {segs}")
        if segs > 1:
            self.lbl_count.setStyleSheet("color: #D97706; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_count.setStyleSheet("color: #64748B; font-weight: bold; font-size: 11px;")

    def save_template(self):
        CommunicationService.save_template(self.t_id, self.t_name.text(), self.t_chan.currentText(), self.t_cat.currentText(), None, self.t_body.toPlainText())
        self.load_templates()
        self.clear_template_form()

    def clear_template_form(self):
        self.t_id = None
        self.t_name.clear()
        self.t_body.clear()

    def edit_template(self, t_id, name, cat, chan, body):
        self.t_id = t_id
        self.t_name.setText(name)
        self.t_cat.setCurrentText(cat)
        self.t_chan.setCurrentText(chan)
        self.t_body.setText(body)

    def delete_template(self, t_id):
        if QMessageBox.question(self, "Confirm", "Delete this template? Historical messages will not be affected.") == QMessageBox.StandardButton.Yes:
            CommunicationService.delete_template(t_id)
            self.load_templates()

    def load_templates(self):
        tpls = CommunicationService.get_templates()
        self.tbl_tpl.setRowCount(len(tpls))
        self.cb_template.blockSignals(True)
        self.cb_template.clear()
        
        for r, t in enumerate(tpls):
            self.tbl_tpl.setItem(r, 0, QTableWidgetItem(t.name))
            self.tbl_tpl.setItem(r, 1, QTableWidgetItem(t.category))
            self.tbl_tpl.setItem(r, 2, QTableWidgetItem(t.channel))
            self.cb_template.addItem(f"{t.name} ({t.channel})", t.id)
            
            act = QWidget()
            act.setStyleSheet("background: transparent;")
            l = QHBoxLayout(act)
            l.setContentsMargins(4, 2, 4, 2)
            l.setSpacing(6)
            btn_e = ModernButton("Edit", icon_name="pencil", variant="secondary")
            btn_e.setFixedHeight(24)
            btn_e.clicked.connect(lambda checked=False, tid=t.id, nm=t.name, c=t.category, ch=t.channel, b=t.body: self.edit_template(tid, nm, c, ch, b))
            btn_d = ModernButton("Delete", icon_name="trash-2", variant="danger")
            btn_d.setFixedHeight(24)
            btn_d.clicked.connect(lambda checked=False, tid=t.id: self.delete_template(tid))
            l.addWidget(btn_e)
            l.addWidget(btn_d)
            self.tbl_tpl.setCellWidget(r, 3, act)
            
        self.cb_template.blockSignals(False)
        self.cb_class.clear()
        self.cb_class.addItem("All Classes", "All")
        for c in AcademicService.get_classes():
            self.cb_class.addItem(c.name, c.id)

    # ==========================================
    # TAB 4: GATEWAYS (Email/SMS Only)
    # ==========================================
    def create_gateway_tab(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setSpacing(14)
        
        form_card = ModernCard()
        fl = QFormLayout(form_card)
        fl.setContentsMargins(18, 16, 18, 16)
        fl.setSpacing(12)

        hdr_lbl = QLabel("Configure Auto-Gateways for Email & SMS (WhatsApp operates via Web/App)")
        hdr_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        fl.addRow(hdr_lbl)

        self.g_chan = QComboBox()
        self.g_chan.setMinimumHeight(32)
        self.g_chan.addItems(["Email", "SMS"])
        self.g_name = QLineEdit()
        self.g_name.setMinimumHeight(32)
        self.g_name.setPlaceholderText("e.g. Gmail SMTP, Twilio")
        self.g_host = QLineEdit()
        self.g_host.setMinimumHeight(32)
        self.g_host.setPlaceholderText("SMTP Host (e.g. smtp.gmail.com) / API URL")
        self.g_user = QLineEdit()
        self.g_user.setMinimumHeight(32)
        self.g_user.setPlaceholderText("Email Address / API User")
        self.g_pass = QLineEdit()
        self.g_pass.setMinimumHeight(32)
        self.g_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.g_pass.setPlaceholderText("App Password / API Secret")
        self.g_sender = QLineEdit()
        self.g_sender.setMinimumHeight(32)
        self.g_sender.setPlaceholderText("Sender Name (e.g. School Admin)")
        self.g_active = QCheckBox("Set as Primary Active Provider for this Channel")
        
        fl.addRow("Channel:", self.g_chan)
        fl.addRow("Provider Name:", self.g_name)
        fl.addRow("API Endpoint / SMTP Host:", self.g_host)
        fl.addRow("API User / SMTP Login:", self.g_user)
        fl.addRow("Access Token / API Secret:", self.g_pass)
        fl.addRow("Business ID / Sender ID:", self.g_sender)
        fl.addRow("", self.g_active)
        
        btn_save = ModernButton("Securely Save Gateway", icon_name="shield", variant="primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.save_provider)
        fl.addRow("", btn_save)
        lay.addWidget(form_card)
        
        tbl_card = ModernCard()
        tbl_lay = QVBoxLayout(tbl_card)
        tbl_lay.setContentsMargins(16, 14, 16, 14)

        self.tbl_prov = self._table()
        self.tbl_prov.setColumnCount(4)
        self.tbl_prov.setHorizontalHeaderLabels(["Provider Name", "Channel", "Business/Sender ID", "Status"])
        tbl_lay.addWidget(self.tbl_prov)
        lay.addWidget(tbl_card)

        return page

    def save_provider(self):
        CommunicationService.save_provider(None, self.g_name.text(), self.g_chan.currentText(), self.g_host.text(), self.g_user.text(), self.g_pass.text(), self.g_sender.text(), 587, True, self.g_active.isChecked())
        self.load_gateways()
        self.g_name.clear()
        self.g_host.clear()
        self.g_user.clear()
        self.g_pass.clear()
        self.g_sender.clear()

    def load_gateways(self):
        provs = CommunicationService.get_providers()
        self.tbl_prov.setRowCount(len(provs))
        for r, p in enumerate(provs):
            self.tbl_prov.setItem(r, 0, QTableWidgetItem(p.name))
            self.tbl_prov.setItem(r, 1, QTableWidgetItem(p.channel))
            self.tbl_prov.setItem(r, 2, QTableWidgetItem(p.sender_id))
            
            badge = StatusBadge("Active" if p.is_active else "Inactive", variant="success" if p.is_active else "neutral")
            badge_container = QWidget()
            badge_container.setStyleSheet("background: transparent;")
            b_lay = QHBoxLayout(badge_container)
            b_lay.setContentsMargins(0, 0, 0, 0)
            b_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_lay.addWidget(badge)
            self.tbl_prov.setCellWidget(r, 3, badge_container)