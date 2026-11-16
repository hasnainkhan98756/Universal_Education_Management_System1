import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, 
                               QTabWidget, QMessageBox, QFrame, QAbstractItemView, QGridLayout, QSizePolicy, QScrollArea,
                               QDialog, QTextEdit, QMenu, QAbstractSpinBox, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, QDate, QTimer, QSize
from PySide6.QtGui import QFont, QColor


from core.fee_service import FeeService
from core.academic_service import AcademicService
from core.pdf_service import PDFGenerationService
from core.state_manager import app_state
from core.data_resolver import DataResolverService
from core.document_service import DocumentService
from database.connection import DB_DIR, get_session
from database.models.fee import FeeVoucher
from core.icon_manager import IconManager
from ui.components.stitch_widgets import (
    PageHeader, MetricCard, ModernCard, ModernButton, TableActionButton, TableTextButton,
    TableDropdownButton, create_table_actions_cell, StatusBadge, SearchInput,
    style_modern_table, style_modern_tabs
)
from ui.components.loading_widgets import show_print_loading

class FeeLedgerDetailDialog(QDialog):
    """Clean, high-clarity transaction detail modal for Fee Ledger entries."""
    def __init__(self, parent=None, entry=None, student=None):
        super().__init__(parent)
        self.entry = entry or {}
        self.student = student
        ref_title = self.entry.get('ref_no', 'N/A')
        self.setWindowTitle(f"Transaction Detail — {ref_title}")
        self.setMinimumWidth(540)
        self.resize(560, 480)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header Card
        hdr_frame = QFrame()
        hdr_frame.setObjectName("dlg_hdr_frame")
        hdr_frame.setStyleSheet("QFrame#dlg_hdr_frame { background-color: rgba(99, 102, 241, 0.08); border: 1.5px solid rgba(99, 102, 241, 0.3); border-radius: 8px; }")
        hdr_lay = QVBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(14, 10, 14, 10)
        hdr_lay.setSpacing(4)

        t_type = self.entry.get("type", "Charge")
        type_color = "#DC2626" if t_type == "Charge" else "#059669"
        badge_text = f"● {t_type.upper()} ({'DEBIT' if t_type == 'Charge' else 'CREDIT'})"

        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(f"color: {type_color}; font-weight: bold; font-size: 13px; background: transparent;")
        hdr_lay.addWidget(lbl_badge)

        if self.student:
            stu_name = f"{getattr(self.student, 'first_name', '')} {getattr(self.student, 'last_name', '') or ''}".strip()
            stu_id = getattr(self.student, 'student_id', 'N/A')
            cls_name = self.student.academic_class.name if getattr(self.student, 'academic_class', None) else "No Class"
            lbl_stu = QLabel(f"Student: {stu_name} | ID: {stu_id} | Class: {cls_name}")
            lbl_stu.setStyleSheet("font-size: 12px; color: #1E293B; font-weight: 600; background: transparent;")
            hdr_lay.addWidget(lbl_stu)

        layout.addWidget(hdr_frame)

        # Details Grid Form
        form_frame = QFrame()
        form_frame.setObjectName("dlg_form_frame")
        form_frame.setStyleSheet("QFrame#dlg_form_frame { background-color: rgba(241, 245, 249, 0.6); border: 1px solid #CBD5E1; border-radius: 8px; }")
        form_lay = QGridLayout(form_frame)
        form_lay.setContentsMargins(14, 12, 14, 12)
        form_lay.setSpacing(8)

        def _val_lbl(text, bold=False, color=None):
            lbl = QLabel(str(text))
            style = "font-size: 12px; background: transparent;"
            if bold: style += " font-weight: bold;"
            if color: style += f" color: {color};"
            lbl.setStyleSheet(style)
            return lbl

        def _key_lbl(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #64748B; background: transparent;")
            return lbl

        form_lay.addWidget(_key_lbl("Date:"), 0, 0)
        form_lay.addWidget(_val_lbl(self.entry.get("date", "-")), 0, 1)

        form_lay.addWidget(_key_lbl("Reference / Receipt:"), 0, 2)
        form_lay.addWidget(_val_lbl(self.entry.get("ref_no", "-"), bold=True), 0, 3)

        form_lay.addWidget(_key_lbl("Fee Category:"), 1, 0)
        form_lay.addWidget(_val_lbl(self.entry.get("category", "-"), bold=True, color="#4F46E5"), 1, 1)

        form_lay.addWidget(_key_lbl("Running Balance:"), 1, 2)
        bal_val = self.entry.get("balance", 0.0)
        form_lay.addWidget(_val_lbl(f"Rs. {bal_val:,.0f}", bold=True, color="#EF4444" if bal_val > 0 else "#059669"), 1, 3)

        dr_val = self.entry.get("debit", 0.0)
        cr_val = self.entry.get("credit", 0.0)
        disc_val = self.entry.get("discount", 0.0)

        form_lay.addWidget(_key_lbl("Debit (Billed):"), 2, 0)
        form_lay.addWidget(_val_lbl(f"Rs. {dr_val:,.0f}" if dr_val > 0 else "-", bold=dr_val > 0, color="#DC2626" if dr_val > 0 else None), 2, 1)

        form_lay.addWidget(_key_lbl("Credit (Paid):"), 2, 2)
        form_lay.addWidget(_val_lbl(f"Rs. {cr_val:,.0f}" if cr_val > 0 else "-", bold=cr_val > 0, color="#059669" if cr_val > 0 else None), 2, 3)

        if disc_val > 0:
            form_lay.addWidget(_key_lbl("Discount Allocated:"), 3, 0)
            form_lay.addWidget(_val_lbl(f"Rs. {disc_val:,.0f}", bold=True, color="#D97706"), 3, 1)

        layout.addWidget(form_frame)

        # Full Description Block
        lbl_desc_title = QLabel("Full Description & Transaction Details:")
        lbl_desc_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 4px;")
        layout.addWidget(lbl_desc_title)

        txt_desc = QTextEdit()
        txt_desc.setReadOnly(True)
        txt_desc.setPlainText(self.entry.get("description", "No description provided."))
        txt_desc.setMaximumHeight(85)
        txt_desc.setStyleSheet("background-color: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 6px; font-size: 12px; padding: 6px; color: #1E293B;")
        layout.addWidget(txt_desc)

        # Action Buttons
        btn_bar = QHBoxLayout()
        ref_no = self.entry.get("ref_no", "")
        # Check if receipt PDF exists
        receipt_pdf = os.path.join(os.path.dirname(DB_DIR), "generated_docs", "Fee_Receipts", f"{ref_no}.pdf")
        if os.path.exists(receipt_pdf):
            btn_pdf = ModernButton("Open / Print Fee Receipt PDF", icon_name="printer", variant="primary")
            btn_pdf.clicked.connect(lambda: os.startfile(receipt_pdf))
            btn_bar.addWidget(btn_pdf)

        btn_bar.addStretch()
        btn_close = ModernButton("Close", icon_name="x", variant="secondary")
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)

        layout.addLayout(btn_bar)

class StudentFeeDossierDialog(QDialog):
    """Executive student fee dossier modal showing complete financial status and action shortcuts."""
    def __init__(self, parent=None, student=None, on_collect=None, on_ledger=None):
        super().__init__(parent)
        self.student = student
        self.on_collect = on_collect
        self.on_ledger = on_ledger
        
        stu_name = f"{getattr(self.student, 'first_name', '')} {getattr(self.student, 'last_name', '') or ''}".strip()
        stu_id = getattr(self.student, 'student_id', 'N/A')
        self.setWindowTitle(f"Student Fee Dossier — {stu_name} ({stu_id})")
        self.setMinimumSize(740, 560)
        self.resize(780, 580)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header Card
        hdr_frame = QFrame()
        hdr_frame.setObjectName("dossier_hdr")
        hdr_frame.setStyleSheet("QFrame#dossier_hdr { background-color: #EFF6FF; border: 1.5px solid #BFDBFE; border-radius: 8px; }")
        hdr_lay = QVBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(14, 12, 14, 12)
        hdr_lay.setSpacing(4)

        cls_name = self.student.academic_class.name if getattr(self.student, 'academic_class', None) else "No Class"
        sec_name = self.student.academic_section.name if getattr(self.student, 'academic_section', None) else ""
        roll = getattr(self.student, 'enrollment_number', None) or getattr(self.student, 'admission_number', None) or "-"
        father = getattr(self.student, 'father_name', '') or "-"
        phone = getattr(self.student, 'phone', '') or getattr(self.student, 'father_phone', '') or "-"

        lbl_name = QLabel(f"{stu_name}")
        lbl_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #1E3A8A; background: transparent;")
        hdr_lay.addWidget(lbl_name)

        lbl_meta = QLabel(f"Student ID: {stu_id}  |  Class: {cls_name} {sec_name}  |  Roll/Reg: {roll}  |  Father: {father}  |  Phone: {phone}")
        lbl_meta.setStyleSheet("font-size: 12px; color: #3B82F6; font-weight: 500; background: transparent;")
        hdr_lay.addWidget(lbl_meta)
        layout.addWidget(hdr_frame)

        # Fee Structure & Financial Balance Cards
        m_fee = getattr(self.student, 'monthly_fee', 0.0) or 0.0
        fee_6m = getattr(self.student, 'six_month_fee', 0.0) or 0.0
        fee_ann = getattr(self.student, 'annual_fee', 0.0) or 0.0

        pos = FeeService.get_student_category_position(self.student.id)
        tot_pending = pos.get("total_pending", 0.0)
        cat_dues = pos.get("category_dues", {})

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        def _make_stat_box(title, val_str, sub_str, color="#1E293B", bg="#F8FAFC", border="#E2E8F0"):
            bx = QFrame()
            bx.setStyleSheet(f"background-color: {bg}; border: 1px solid {border}; border-radius: 6px;")
            b_lay = QVBoxLayout(bx)
            b_lay.setContentsMargins(10, 8, 10, 8); b_lay.setSpacing(2)
            t_lbl = QLabel(title); t_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; background: transparent;")
            v_lbl = QLabel(val_str); v_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color}; background: transparent;")
            s_lbl = QLabel(sub_str); s_lbl.setStyleSheet("font-size: 10px; color: #94A3B8; background: transparent;")
            b_lay.addWidget(t_lbl); b_lay.addWidget(v_lbl); b_lay.addWidget(s_lbl)
            return bx

        cards_row.addWidget(_make_stat_box("Monthly Fee", f"Rs. {m_fee:,.0f}", "Standard rate"))
        cards_row.addWidget(_make_stat_box("6-Month Package", f"Rs. {fee_6m:,.0f}" if fee_6m > 0 else "Not Set", "Half-year term"))
        cards_row.addWidget(_make_stat_box("Annual Package", f"Rs. {fee_ann:,.0f}" if fee_ann > 0 else "Not Set", "Full-year term"))
        
        pend_color = "#DC2626" if tot_pending > 0 else "#059669"
        pend_bg = "#FEF2F2" if tot_pending > 0 else "#ECFDF5"
        pend_border = "#FECACA" if tot_pending > 0 else "#A7F3D0"
        cards_row.addWidget(_make_stat_box("Total Outstanding", f"Rs. {tot_pending:,.0f}", "All pending dues", color=pend_color, bg=pend_bg, border=pend_border))
        layout.addLayout(cards_row)

        if cat_dues:
            dues_txt = "  •  ".join([f"{k}: Rs. {v:,.0f}" for k, v in cat_dues.items() if v > 0])
            if dues_txt:
                lbl_dues = QLabel(f"<b>Pending Breakdown:</b> {dues_txt}")
                lbl_dues.setStyleSheet("font-size: 11px; color: #DC2626; background: #FFF1F2; border: 1px solid #FFE4E6; border-radius: 4px; padding: 4px 8px;")
                layout.addWidget(lbl_dues)

        # Tabbed detail: Pending Vouchers & Recent History
        sub_tabs = QTabWidget()
        style_modern_tabs(sub_tabs)

        # Tab 1: Unpaid Vouchers
        page_vouch = QWidget(); v_lay = QVBoxLayout(page_vouch); v_lay.setContentsMargins(4, 6, 4, 4)
        tbl_v = QTableWidget(); tbl_v.setColumnCount(6)
        tbl_v.setHorizontalHeaderLabels(["Voucher No.", "Fee Month", "Due Date", "Total Billed", "Paid", "Balance Due"])
        tbl_v.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl_v.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        style_modern_table(tbl_v)

        _, vouchers = FeeService.search_student_for_payment(self.student.student_id)
        tbl_v.setRowCount(len(vouchers))
        for r, v in enumerate(vouchers):
            v_no = getattr(v, 'voucher_no', None) or getattr(v, 'voucher_number', None) or f"VOU-{v.id}"
            tbl_v.setItem(r, 0, QTableWidgetItem(str(v_no)))
            tbl_v.setItem(r, 1, QTableWidgetItem(v.fee_month))
            tbl_v.setItem(r, 2, QTableWidgetItem(v.due_date or "-"))
            tbl_v.setItem(r, 3, QTableWidgetItem(f"Rs. {(v.total_amount or 0.0):,.0f}"))
            tbl_v.setItem(r, 4, QTableWidgetItem(f"Rs. {(v.paid_amount or 0.0):,.0f}"))
            rem = (v.total_amount or 0.0) - (v.paid_amount or 0.0)
            b_item = QTableWidgetItem(f"Rs. {rem:,.0f}")
            b_item.setForeground(QColor("#EF4444"))
            b_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tbl_v.setItem(r, 5, b_item)
            tbl_v.setRowHeight(r, 36)

        v_lay.addWidget(tbl_v)
        sub_tabs.addTab(page_vouch, f"Active / Unpaid Vouchers ({len(vouchers)})")

        # Tab 2: Recent Ledger Transactions
        page_ledg = QWidget(); l_lay = QVBoxLayout(page_ledg); l_lay.setContentsMargins(4, 6, 4, 4)
        tbl_l = QTableWidget(); tbl_l.setColumnCount(5)
        tbl_l.setHorizontalHeaderLabels(["Date", "Ref / Receipt", "Type", "Category", "Amount"])
        tbl_l.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl_l.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        style_modern_table(tbl_l)

        ledger_entries = FeeService.get_student_ledger(self.student.id)
        recent_entries = ledger_entries[-15:] if len(ledger_entries) > 15 else ledger_entries
        tbl_l.setRowCount(len(recent_entries))
        for r, e in enumerate(reversed(recent_entries)):
            tbl_l.setItem(r, 0, QTableWidgetItem(str(e.get("date", "-"))))
            tbl_l.setItem(r, 1, QTableWidgetItem(str(e.get("ref_no", "-"))))
            t_type = e.get("type", "Charge")
            t_item = QTableWidgetItem(t_type)
            t_item.setForeground(QColor("#DC2626" if t_type == "Charge" else "#059669"))
            t_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            tbl_l.setItem(r, 2, t_item)
            tbl_l.setItem(r, 3, QTableWidgetItem(str(e.get("category", "-"))))
            val = e.get("debit", 0.0) if t_type == "Charge" else e.get("credit", 0.0)
            tbl_l.setItem(r, 4, QTableWidgetItem(f"Rs. {val:,.0f}"))
            tbl_l.setRowHeight(r, 36)

        l_lay.addWidget(tbl_l)
        sub_tabs.addTab(page_ledg, f"Recent Transactions ({len(ledger_entries)})")

        layout.addWidget(sub_tabs)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_pay = ModernButton("💳 Open in Fee Collection", icon_name="credit-card", variant="success")
        btn_pay.clicked.connect(self._go_collect)
        btn_bar.addWidget(btn_pay)

        btn_ledg = ModernButton("📜 View Full Chronological Ledger", icon_name="receipt", variant="primary")
        btn_ledg.clicked.connect(self._go_ledger)
        btn_bar.addWidget(btn_ledg)

        btn_bar.addStretch()
        btn_close = ModernButton("Close", icon_name="x", variant="secondary")
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

    def _go_collect(self):
        self.accept()
        if self.on_collect and self.student:
            self.on_collect(self.student.student_id)

    def _go_ledger(self):
        self.accept()
        if self.on_ledger and self.student:
            self.on_ledger(self.student.student_id)

class FeeAllocationTable(QTableWidget):
    """QTableWidget that forwards mouse wheel events to parent scroll area when internal scroll is at bounds or unneeded."""
    def __init__(self, parent=None, outer_scroll=None):
        super().__init__(parent)
        self.outer_scroll = outer_scroll

    def wheelEvent(self, event):
        vbar = self.verticalScrollBar()
        if not vbar or not vbar.isVisible() or vbar.maximum() == 0:
            if self.outer_scroll:
                self.outer_scroll.wheelEvent(event)
                return
        delta = event.angleDelta().y()
        if (delta > 0 and vbar.value() == 0) or (delta < 0 and vbar.value() == vbar.maximum()):
            if self.outer_scroll:
                self.outer_scroll.wheelEvent(event)
                return
        super().wheelEvent(event)

class FeeView(QWidget):
    def __init__(self):
        super().__init__()
        self.current_student = None
        self.current_student_total_pending = 0.0
        self.current_vouchers = []
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        self.header = PageHeader(
            title="Fee & Financial Management",
            subtitle="Student fee collection, automated vouchers, chronological ledgers, and revenue accounting",
            icon_name="wallet",
            icon_color="#2563EB",
            badge_bg="#EFF6FF"
        )
        main_layout.addWidget(self.header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_dashboard_tab(), IconManager.get("bar-chart-2", "#2563EB", 16), "Financial Analytics")
        self.tabs.addTab(self.create_collect_tab(), IconManager.get("credit-card", "#2563EB", 16), "Collect Payment")
        self.tabs.addTab(self.create_ledger_tab(), IconManager.get("receipt", "#2563EB", 16), "Student Ledger")
        self.tabs.addTab(self.create_pending_tab(), IconManager.get("alert-triangle", "#2563EB", 16), "Pending Defaulters")
        self.tabs.addTab(self.create_history_tab(), IconManager.get("coins", "#2563EB", 16), "Payment History")
        self.tabs.addTab(self.create_generate_tab(), IconManager.get("settings", "#2563EB", 16), "Auto Generation")

        main_layout.addWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        app_state.subscribe_settings_change(self.load_academic_dropdowns)
        app_state.subscribe_data_changed(self.refresh_data)
        self.load_academic_dropdowns()
        self.refresh_all()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_data()

    def refresh_data(self):
        self.load_academic_dropdowns()
        self.refresh_all()

    def _lbl(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        return lbl

    def _input(self):
        inp = QLineEdit()
        inp.setMinimumHeight(32)
        return inp

    def _combo(self, items=None):
        cb = QComboBox()
        if items: cb.addItems(items)
        cb.setMinimumHeight(32)
        return cb

    def _spinbox(self):
        sb = QDoubleSpinBox()
        sb.setRange(0, 1000000)
        sb.setMinimumHeight(32)
        return sb

    def _table(self):
        tbl = QTableWidget()
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        style_modern_table(tbl)
        return tbl

    # =========================================================================
    # TAB 0: FINANCIAL ANALYTICS
    # =========================================================================
    def create_dashboard_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 8, 0, 0)
        grid = QGridLayout(); grid.setSpacing(14)
        self.card_today = MetricCard("Today's Collection", "Rs. 0", "Daily revenue inflow", icon_name="coins", icon_color="#10B981", badge_bg="#ECFDF5")
        self.card_month = MetricCard("This Month's Collection", "Rs. 0", "Monthly total inflow", icon_name="wallet", icon_color="#2563EB", badge_bg="#EFF6FF")
        self.card_pending = MetricCard("Total Pending Fees", "Rs. 0", "Outstanding dues across school", icon_name="alert-triangle", icon_color="#EF4444", badge_bg="#FEF2F2")
        self.card_tuition = MetricCard("Tuition Collected", "Rs. 0", "Tuition revenue collected", icon_name="graduation-cap", icon_color="#8B5CF6", badge_bg="#F5F3FF")
        self.card_transport = MetricCard("Transport Collected", "Rs. 0", "Fleet & transit fees", icon_name="bus", icon_color="#F59E0B", badge_bg="#FFFBEB")
        
        grid.addWidget(self.card_today, 0, 0)
        grid.addWidget(self.card_month, 0, 1)
        grid.addWidget(self.card_pending, 0, 2)
        grid.addWidget(self.card_tuition, 1, 0)
        grid.addWidget(self.card_transport, 1, 1)
        
        layout.addLayout(grid); layout.addStretch()
        return page

    def _stat_card(self, title, init_val, color_hex):
        return MetricCard(title, init_val, icon_name="wallet", icon_color=color_hex)

    # =========================================================================
    # TAB 1: COLLECT PAYMENT (MULTI-CATEGORY & PARTIAL PAYMENT ROWS)
    # =========================================================================
    def create_collect_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        page = QWidget()
        page.setObjectName("collect_page")
        page.setStyleSheet("QWidget#collect_page { background: transparent; }")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 16, 12)
        layout.setSpacing(10)

        # 1. Search Bar
        search_lay = QHBoxLayout()
        search_lay.setSpacing(10)
        self.inp_search = SearchInput("Scan or enter Student ID, Name, Phone...")
        self.inp_search.returnPressed.connect(self.search_student)
        self.inp_search.textChanged.connect(self._on_search_text_changed)
        btn_search = ModernButton("Search", icon_name="search", variant="primary")
        btn_search.clicked.connect(self.search_student)
        search_lay.addWidget(self.inp_search); search_lay.addWidget(btn_search)
        layout.addLayout(search_lay)

        # Real-Time Multi-Student Dues Suggestion Dropdown
        self.search_results_container = QFrame()
        self.search_results_container.setObjectName("fee_search_results")
        self.search_results_container.setStyleSheet("""
            QFrame#fee_search_results {
                background-color: #FFFFFF;
                border: 1.5px solid #3B82F6;
                border-radius: 8px;
            }
        """)
        self.search_results_container.hide()
        src_lay = QVBoxLayout(self.search_results_container)
        src_lay.setContentsMargins(6, 6, 6, 6)
        src_lay.setSpacing(4)

        self.lbl_search_header = QLabel("Students matching your search (Prioritizing Pending Fees):")
        self.lbl_search_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #2563EB; padding: 2px 4px;")
        src_lay.addWidget(self.lbl_search_header)

        self.search_results_list = QListWidget()
        self.search_results_list.setMaximumHeight(210)
        self.search_results_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
            }
            QListWidget::item {
                border-bottom: 1px solid #F1F5F9;
                padding: 3px 6px;
            }
            QListWidget::item:hover {
                background-color: #EFF6FF;
            }
            QListWidget::item:selected {
                background-color: #DBEAFE;
            }
        """)
        self.search_results_list.itemClicked.connect(self._on_search_item_clicked)
        src_lay.addWidget(self.search_results_list)
        layout.addWidget(self.search_results_container)

        self._search_suggest_timer = QTimer(self)
        self._search_suggest_timer.setSingleShot(True)
        self._search_suggest_timer.setInterval(180)
        self._search_suggest_timer.timeout.connect(self._populate_search_suggestions)

        # 2. Student Info & Category Position Card
        self.frame_stu_info = ModernCard()
        self.frame_stu_info.setObjectName("frame_stu_info")
        self.frame_stu_info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.frame_stu_info.setMinimumHeight(74)
        stu_lay = QVBoxLayout(self.frame_stu_info)
        stu_lay.setContentsMargins(14, 10, 14, 10)
        stu_lay.setSpacing(4)
        self.lbl_stu_info = QLabel("Search a student to view their current fee position and vouchers.")
        self.lbl_stu_info.setStyleSheet("font-weight: 700; font-size: 13px; color: #0F172A; border: none; background: transparent;")
        self.lbl_category_dues = QLabel("")
        self.lbl_category_dues.setStyleSheet("font-size: 11px; color: #2563EB; font-weight: 600; border: none; background: transparent;")
        self.lbl_previous_dues = QLabel("Previous Dues: Rs. 0 | Current Fee: Rs. 0 | Total Payable: Rs. 0")
        self.lbl_previous_dues.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 12px; border: none; background: transparent;")
        stu_lay.addWidget(self.lbl_stu_info)
        stu_lay.addWidget(self.lbl_category_dues)
        stu_lay.addWidget(self.lbl_previous_dues)
        layout.addWidget(self.frame_stu_info)

        # 3. Voucher Selector
        v_box = QHBoxLayout()
        v_box.setSpacing(10)
        v_box.addWidget(self._lbl("Select Pending Voucher:"))
        self.combo_vouchers = self._combo()
        self.combo_vouchers.currentIndexChanged.connect(self.on_voucher_selected)
        v_box.addWidget(self.combo_vouchers, stretch=2)
        layout.addLayout(v_box)

        # 4. Itemized Payment Rows Table
        lbl_tbl = QLabel("Fee Categories & Payment Allocation:")
        lbl_tbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(lbl_tbl)

        self.tbl_items = FeeAllocationTable(outer_scroll=scroll)
        self.tbl_items.setColumnCount(9)
        self.tbl_items.setHorizontalHeaderLabels([
            "Category", "Description", "Original Due (Rs)", "Discount (Rs)", 
            "Already Paid (Rs)", "Net Due (Rs)", "Paying Now (Rs)", "Remaining (Rs)", "Action"
        ])
        self.tbl_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_items.setColumnWidth(0, 135)
        self.tbl_items.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in [2, 3, 4, 5, 6, 7]:
            self.tbl_items.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            self.tbl_items.setColumnWidth(c, 105)
        self.tbl_items.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        style_modern_table(self.tbl_items)
        self.tbl_items.setMinimumHeight(260)
        self.tbl_items.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        layout.addWidget(self.tbl_items)

        # Table Action Buttons (Add Row / Clear Empty / Auto-Fill)
        tbl_btn_lay = QHBoxLayout()
        tbl_btn_lay.setSpacing(10)
        btn_add_row = ModernButton("Add Fee Category Row", icon_name="plus", variant="secondary")
        btn_add_row.clicked.connect(self.add_category_row)
        
        btn_clear_empty = ModernButton("Clear Empty Rows", icon_name="trash-2", variant="secondary")
        btn_clear_empty.clicked.connect(self.clear_empty_rows)

        btn_autofill = ModernButton("Auto-Fill Full Payment", icon_name="zap", variant="success")
        btn_autofill.clicked.connect(self.autofill_full_payment)
        
        tbl_btn_lay.addWidget(btn_add_row)
        tbl_btn_lay.addWidget(btn_clear_empty)
        tbl_btn_lay.addWidget(btn_autofill)
        tbl_btn_lay.addStretch()
        layout.addLayout(tbl_btn_lay)

        # 5. Form & Totals Summary
        summary_frame = ModernCard()
        summary_frame.setObjectName("summary_frame")
        sum_lay = QHBoxLayout(summary_frame)
        sum_lay.setContentsMargins(14, 10, 14, 10)
        self.lbl_total_net = QLabel("Total Net: Rs. 0")
        self.lbl_total_net.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_total_paying = QLabel("Total Paying: Rs. 0")
        self.lbl_total_paying.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_total_paying.setStyleSheet("color: #10B981;")
        self.lbl_total_rem = QLabel("Remaining: Rs. 0")
        self.lbl_total_rem.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_total_rem.setStyleSheet("color: #EF4444;")
        sum_lay.addWidget(self.lbl_total_net)
        sum_lay.addStretch()
        sum_lay.addWidget(self.lbl_total_paying)
        sum_lay.addStretch()
        sum_lay.addWidget(self.lbl_total_rem)
        layout.addWidget(summary_frame)

        # Payment options
        opt_lay = QHBoxLayout()
        opt_lay.setSpacing(10)
        opt_lay.addWidget(self._lbl("Payment Method:"))
        self.pay_method = self._combo(["Cash", "Bank Transfer", "Online", "Cheque"])
        opt_lay.addWidget(self.pay_method)
        opt_lay.addWidget(self._lbl("Notes / Remarks:"))
        self.pay_notes = self._input()
        self.pay_notes.setPlaceholderText("Optional transaction reference or remarks...")
        opt_lay.addWidget(self.pay_notes, stretch=2)
        opt_lay.addWidget(self._lbl("Print Format:"))
        self.combo_receipt_format = self._combo(["A4 Detailed Receipt", "POS Thermal Receipt (80mm)"])
        # Inherit default setting if set to thermal
        paper_setting = DocumentService.get_setting("paper_size", "A4 Size (Standard)")
        if "thermal" in paper_setting.lower() or "pos" in paper_setting.lower() or "80mm" in paper_setting.lower():
            self.combo_receipt_format.setCurrentIndex(1)
        opt_lay.addWidget(self.combo_receipt_format)
        layout.addLayout(opt_lay)

        # 6. Unified Submit Button (Pay & Print Receipt)
        btn_pay_lay = QHBoxLayout()
        self.btn_pay = ModernButton("Collect Fee & Print Receipt ▾", icon_name="credit-card", variant="success")
        self.btn_pay.setFixedHeight(42)
        pay_menu = QMenu(self.btn_pay)
        pay_menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 4px;
                font-size: 13px;
                font-weight: 600;
                color: #1E293B;
            }
            QMenu::item {
                padding: 8px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #EFF6FF;
                color: #2563EB;
            }
        """)
        a_a4 = pay_menu.addAction(IconManager.get("file-text", color="#2563EB", size=15), "Collect & Print A4 Detailed Receipt")
        a_a4.triggered.connect(lambda: self.process_payment(force_thermal=False))
        a_th = pay_menu.addAction(IconManager.get("printer", color="#059669", size=15), "Collect & Print POS Thermal Receipt (80mm)")
        a_th.triggered.connect(lambda: self.process_payment(force_thermal=True))
        self.btn_pay.setMenu(pay_menu)
        self.btn_pay_thermal = self.btn_pay  # Keep reference alias for backward compatibility
        btn_pay_lay.addWidget(self.btn_pay)
        layout.addLayout(btn_pay_lay)
        layout.addSpacing(30)

        scroll.setWidget(page)
        return scroll

    # =========================================================================
    # TAB 2: STUDENT FEE LEDGER
    # =========================================================================
    def create_ledger_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Search Bar
        top_lay = QHBoxLayout()
        top_lay.setSpacing(10)
        self.inp_ledger_search = SearchInput("Enter Student ID or Name to view audit ledger...")
        self.inp_ledger_search.returnPressed.connect(self.search_ledger)
        btn_search = ModernButton("View Ledger", icon_name="search", variant="primary")
        btn_search.clicked.connect(self.search_ledger)
        top_lay.addWidget(self.inp_ledger_search, stretch=2)
        top_lay.addWidget(btn_search)
        layout.addLayout(top_lay)

        self.lbl_ledger_header = QLabel("Search a student to view their chronological transaction ledger.")
        self.lbl_ledger_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563EB;")
        layout.addWidget(self.lbl_ledger_header)

        self.tbl_ledger = self._table()
        self.tbl_ledger.setColumnCount(9)
        self.tbl_ledger.setHorizontalHeaderLabels([
            "Date", "Ref / Receipt No", "Type", "Category", "Description (Click for Details)", 
            "Debit (Billed)", "Credit (Paid)", "Discount", "Running Balance"
        ])
        for c, w in [(0, 95), (1, 140), (2, 85), (3, 110), (5, 95), (6, 95), (7, 85), (8, 115)]:
            self.tbl_ledger.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeMode.Interactive)
            self.tbl_ledger.setColumnWidth(c, w)
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tbl_ledger.cellClicked.connect(self.on_ledger_cell_clicked)
        self.tbl_ledger.cellDoubleClicked.connect(self.on_ledger_cell_clicked)
        layout.addWidget(self.tbl_ledger)
        return page

    def search_ledger(self):
        txt = self.inp_ledger_search.text().strip()
        if not txt: return
        student, _ = FeeService.search_student_for_payment(txt)
        if not student:
            QMessageBox.warning(self, "Not Found", "No student found matching that search."); return

        self.current_ledger_student = student
        cls_name = student.academic_class.name if student.academic_class else "No Class"
        sec_name = student.academic_section.name if student.academic_section else ""
        self.lbl_ledger_header.setText(f"Chronological Fee Ledger: {student.first_name} {student.last_name or ''} (ID: {student.student_id}) | Class: {cls_name} {sec_name}")

        ledger_entries = FeeService.get_student_ledger(student.id)
        self.current_ledger_entries = ledger_entries
        self.tbl_ledger.setRowCount(len(ledger_entries))

        for row, entry in enumerate(ledger_entries):
            self.tbl_ledger.setItem(row, 0, QTableWidgetItem(str(entry.get("date", ""))))
            self.tbl_ledger.setItem(row, 1, QTableWidgetItem(str(entry.get("ref_no", ""))))
            
            type_item = QTableWidgetItem(entry.get("type", ""))
            if entry.get("type") == "Charge":
                type_item.setForeground(QColor("#DC2626"))
            else:
                type_item.setForeground(QColor("#059669"))
            type_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tbl_ledger.setItem(row, 2, type_item)

            self.tbl_ledger.setItem(row, 3, QTableWidgetItem(str(entry.get("category", ""))))

            desc_text = str(entry.get("description", ""))
            desc_item = QTableWidgetItem(desc_text)
            desc_item.setToolTip(f"Click to view full transaction details:\n\n{desc_text}")
            desc_item.setForeground(QColor("#2563EB"))
            self.tbl_ledger.setItem(row, 4, desc_item)

            dr_val = entry.get("debit", 0.0)
            dr_item = QTableWidgetItem(f"Rs. {dr_val:,.0f}" if dr_val > 0 else "-")
            self.tbl_ledger.setItem(row, 5, dr_item)

            cr_val = entry.get("credit", 0.0)
            cr_item = QTableWidgetItem(f"Rs. {cr_val:,.0f}" if cr_val > 0 else "-")
            if cr_val > 0: cr_item.setForeground(QColor("#059669"))
            self.tbl_ledger.setItem(row, 6, cr_item)

            disc_val = entry.get("discount", 0.0)
            disc_item = QTableWidgetItem(f"Rs. {disc_val:,.0f}" if disc_val > 0 else "-")
            self.tbl_ledger.setItem(row, 7, disc_item)

            bal_val = entry.get("balance", 0.0)
            bal_item = QTableWidgetItem(f"Rs. {bal_val:,.0f}")
            bal_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if bal_val > 0: bal_item.setForeground(QColor("#EF4444"))
            self.tbl_ledger.setItem(row, 8, bal_item)

    def on_ledger_cell_clicked(self, row, col):
        if not hasattr(self, 'current_ledger_entries') or not self.current_ledger_entries:
            return
        if 0 <= row < len(self.current_ledger_entries):
            entry = self.current_ledger_entries[row]
            dialog = FeeLedgerDetailDialog(self, entry, getattr(self, 'current_ledger_student', None))
            dialog.exec()

    # =========================================================================
    # TAB 3: PENDING DEFAULTERS
    # =========================================================================
    def create_pending_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        self.search_pending = SearchInput("Search Defaulters by Name or ID...")
        
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_pending_list)
        self.search_pending.textChanged.connect(lambda _: self._search_timer.start())

        self.filter_class_pending = self._combo(["All Classes"])
        self.filter_class_pending.currentIndexChanged.connect(self.refresh_pending_list)

        top_row.addWidget(self.search_pending, stretch=2)
        top_row.addWidget(QLabel("Filter by Class:"), stretch=0)
        top_row.addWidget(self.filter_class_pending, stretch=1)
        layout.addLayout(top_row)

        self.tbl_pending = self._table()
        self.tbl_pending.setColumnCount(7)
        self.tbl_pending.setHorizontalHeaderLabels(["Student ID", "Name", "Class", "Fee Month", "Total Pending", "Status", "Action"])
        self.tbl_pending.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_pending.setColumnWidth(0, 150)
        self.tbl_pending.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_pending.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl_pending.setColumnWidth(2, 110)
        self.tbl_pending.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tbl_pending.setColumnWidth(3, 140)
        self.tbl_pending.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tbl_pending.setColumnWidth(4, 150)
        self.tbl_pending.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.tbl_pending.setColumnWidth(5, 100)
        self.tbl_pending.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_pending.setColumnWidth(6, 150)
        self.tbl_pending.verticalHeader().setDefaultSectionSize(48)
        self.tbl_pending.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_pending.cellClicked.connect(self.on_pending_cell_clicked)
        self.tbl_pending.cellDoubleClicked.connect(self.on_pending_cell_clicked)
        layout.addWidget(self.tbl_pending)
        return page

    # =========================================================================
    # TAB 4: PAYMENT HISTORY
    # =========================================================================
    def create_history_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        info = QLabel("Showing the last 100 payments processed. Click any student to view their fee dossier."); info.setStyleSheet("color: #6B7280; font-size: 12px; margin-bottom: 4px;")
        layout.addWidget(info)
        self.tbl_history = self._table()
        self.tbl_history.setColumnCount(7)
        self.tbl_history.setHorizontalHeaderLabels(["Receipt No.", "Date", "Student", "Month Paid", "Amount Collected", "Method", "Action"])
        self.tbl_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl_history.setColumnWidth(0, 185)
        self.tbl_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.tbl_history.setColumnWidth(1, 110)
        self.tbl_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tbl_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.tbl_history.setColumnWidth(3, 175)
        self.tbl_history.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.tbl_history.setColumnWidth(4, 150)
        self.tbl_history.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.tbl_history.setColumnWidth(5, 100)
        self.tbl_history.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_history.setColumnWidth(6, 170)
        self.tbl_history.verticalHeader().setDefaultSectionSize(48)
        self.tbl_history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_history.cellClicked.connect(self.on_history_cell_clicked)
        self.tbl_history.cellDoubleClicked.connect(self.on_history_cell_clicked)
        layout.addWidget(self.tbl_history)
        return page

    # =========================================================================
    # TAB 5: AUTO GENERATION
    # =========================================================================
    def create_generate_tab(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        info = QLabel("<b>Smart Multi-Term Fee Generation Engine</b><br>Generates fee vouchers for all active students. "
                      "Supports standard Monthly billing, 6-Month packages, and Annual packages.<br>"
                      "Students covered by active 6-Month or Annual packages are automatically protected from duplicate monthly billing.")
        info.setStyleSheet("font-size: 13px; line-height: 1.4;")
        layout.addWidget(info)
        form = QFormLayout()
        form.setSpacing(8)
        self.gen_term = self._combo(["Monthly Billing", "6-Month Package", "Annual Package"])
        self.gen_month = self._combo(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        self.gen_month.setCurrentIndex(max(0, QDate.currentDate().month() - 1))
        self.gen_year = self._input(); self.gen_year.setText(str(QDate.currentDate().year()))
        form.addRow(self._lbl("Billing Term:"), self.gen_term)
        form.addRow(self._lbl("Select Month / Start Month:"), self.gen_month)
        form.addRow(self._lbl("Select Year:"), self.gen_year)
        layout.addLayout(form)
        btn_gen = ModernButton("Generate Vouchers for Active Students", icon_name="zap", variant="primary")
        btn_gen.setFixedHeight(38)
        btn_gen.clicked.connect(self.run_generation)
        layout.addWidget(btn_gen); layout.addStretch()
        return page

    # =========================================================================
    # LOGIC & EVENT HANDLERS
    # =========================================================================
    def on_tab_changed(self, index):
        if index == 0: self.refresh_analytics()
        elif index == 3: self.refresh_pending_list()
        elif index == 4: self.refresh_history_list()

    def refresh_all(self):
        self.refresh_analytics(); self.refresh_pending_list(); self.refresh_history_list()

    def load_academic_dropdowns(self):
        active_session = app_state.get_setting("session", "Default")
        self.classes = AcademicService.get_classes(session_filter=active_session)
        self.filter_class_pending.blockSignals(True); self.filter_class_pending.clear(); self.filter_class_pending.addItem("All Classes", "All")
        for c in self.classes: self.filter_class_pending.addItem(c.name, c.id)
        self.filter_class_pending.blockSignals(False)

    def jump_to_payment(self, student_id):
        self.tabs.setCurrentIndex(1)
        self.inp_search.setText(student_id)
        self.search_student()

    def _on_search_text_changed(self, text):
        txt = (text or "").strip()
        if len(txt) == 0:
            if hasattr(self, "search_results_container"):
                self.search_results_container.hide()
            return
        if hasattr(self, "_search_suggest_timer"):
            self._search_suggest_timer.start(180)

    def _populate_search_suggestions(self):
        txt = self.inp_search.text().strip()
        if len(txt) == 0:
            self.search_results_container.hide()
            return

        matches = FeeService.search_students_with_dues(txt, limit=12)
        if not matches:
            self.search_results_container.hide()
            return

        self.search_results_list.clear()
        for m in matches:
            item = QListWidgetItem(self.search_results_list)
            item.setData(Qt.ItemDataRole.UserRole, m["student_id"])
            item.setSizeHint(QSize(0, 44))

            row_w = QWidget()
            row_w.setStyleSheet("background: transparent;")
            r_lay = QHBoxLayout(row_w)
            r_lay.setContentsMargins(6, 2, 6, 2)
            r_lay.setSpacing(10)

            # Left Info
            s_name = m["name"]
            s_id = m["student_id"]
            c_name = m["class_name"]
            f_name = f" | Father: {m['father_name']}" if m["father_name"] else ""
            lbl_info = QLabel(f"<b>{s_name}</b> <span style='color:#64748B;'>({s_id})</span>  •  Class {c_name}{f_name}")
            lbl_info.setStyleSheet("font-size: 12px; color: #0F172A; background: transparent;")
            r_lay.addWidget(lbl_info, 1)

            # Right Pending Fee Badge
            if m["has_dues"]:
                p_text = f"● Pending: Rs. {int(m['pending_dues']):,} ({m['pending_vouchers_count']} voucher{'s' if m['pending_vouchers_count'] > 1 else ''})"
                lbl_badge = QLabel(p_text)
                lbl_badge.setStyleSheet(
                    "background-color: #FEF2F2; color: #DC2626; font-weight: bold; font-size: 11px; "
                    "border: 1px solid #FECACA; border-radius: 6px; padding: 2px 8px;"
                )
            else:
                lbl_badge = QLabel("✓ Dues Cleared")
                lbl_badge.setStyleSheet(
                    "background-color: #ECFDF5; color: #059669; font-weight: bold; font-size: 11px; "
                    "border: 1px solid #A7F3D0; border-radius: 6px; padding: 2px 8px;"
                )
            r_lay.addWidget(lbl_badge)

            self.search_results_list.setItemWidget(item, row_w)

        self.search_results_container.show()

    def _on_search_item_clicked(self, item):
        if not item: return
        student_id = item.data(Qt.ItemDataRole.UserRole)
        self.select_searched_student(student_id)

    def select_searched_student(self, student_id):
        if hasattr(self, "search_results_container"):
            self.search_results_container.hide()
        self.inp_search.blockSignals(True)
        self.inp_search.setText(str(student_id))
        self.inp_search.blockSignals(False)
        self.load_student(student_id)

    def search_student(self):
        if hasattr(self, "search_results_container") and self.search_results_container.isVisible() and self.search_results_list.count() > 0:
            cur_item = self.search_results_list.currentItem() or self.search_results_list.item(0)
            if cur_item:
                self.select_searched_student(cur_item.data(Qt.ItemDataRole.UserRole))
                return
        txt = self.inp_search.text().strip()
        if txt:
            if hasattr(self, "search_results_container"):
                self.search_results_container.hide()
            self.load_student(txt)

    def load_student(self, search_text):
        txt = str(search_text).strip()
        if not txt: return
        student, vouchers = FeeService.search_student_for_payment(txt)
        if not student:
            QMessageBox.warning(self, "Not Found", "No student found matching that search."); return

        self.current_student = student
        self.current_vouchers = vouchers

        base_fee = student.monthly_fee or 0.0
        cls_name = student.academic_class.name if student.academic_class else "No Class"
        name_str = f"{student.first_name} {student.last_name or ''}".strip()
        fee_6m = getattr(student, 'six_month_fee', 0.0) or 0.0
        fee_ann = getattr(student, 'annual_fee', 0.0) or 0.0
        self.lbl_stu_info.setText(
            f"{name_str} (ID: {student.student_id}) | Class: {cls_name} | "
            f"Monthly: Rs. {base_fee:,.0f} | 6-Month: Rs. {fee_6m:,.0f} | Annual: Rs. {fee_ann:,.0f}"
        )

        # Authoritative category dues position
        pos = FeeService.get_student_category_position(student.id)
        cat_dues_str = "  |  ".join([f"{cat}: Rs. {val:,.0f}" for cat, val in pos.get("category_dues", {}).items()])
        if cat_dues_str:
            self.lbl_category_dues.setText(f"Breakdown: {cat_dues_str}")
        else:
            self.lbl_category_dues.setText("All previous categories are fully cleared!")

        self.combo_vouchers.blockSignals(True)
        self.combo_vouchers.clear()

        if vouchers:
            self.current_student_total_pending = sum([(v.total_amount - (v.paid_amount or 0.0)) for v in vouchers])
            for v in vouchers:
                rem = v.total_amount - (v.paid_amount or 0.0)
                self.combo_vouchers.addItem(f"{v.fee_month} | Outstanding: Rs. {rem:,.0f}", v.id)
                self.combo_vouchers.setItemData(self.combo_vouchers.count()-1, rem, Qt.ItemDataRole.UserRole + 1)
            
            first_rem = vouchers[0].total_amount - (vouchers[0].paid_amount or 0.0)
            prev_dues = self.current_student_total_pending - first_rem
            self.lbl_previous_dues.setText(f"Previous Dues: Rs. {prev_dues:,.0f}  |  Current Fee: Rs. {first_rem:,.0f}  |  Total Payable: Rs. {self.current_student_total_pending:,.0f}")
        else:
            self.current_student_total_pending = 0.0
            self.combo_vouchers.addItem("No Pending Fees for this student!", None)
            self.lbl_previous_dues.setText("Previous Dues: Rs. 0 | Current Fee: Rs. 0 | Total Payable: Rs. 0")

        self.combo_vouchers.blockSignals(False)
        self.on_voucher_selected()

    def on_voucher_selected(self):
        self.tbl_items.setRowCount(0)
        vid = self.combo_vouchers.currentData()
        if not vid:
            self.recalc_totals()
            return

        db = get_session()
        try:
            v = db.query(FeeVoucher).filter_by(id=vid).first()
            if not v: return
            
            items = v.effective_items
            for item in items:
                rem = item.remaining_balance
                if rem > 0:
                    self.add_item_row(
                        category=item.category,
                        description=item.description,
                        orig_due=item.amount,
                        discount=item.discount,
                        paying_now=rem,
                        voucher_item_id=item.id,
                        paid_earlier=item.paid_amount or 0.0
                    )
        finally:
            db.close()

        if vid and self.current_vouchers:
            cur_v = next((v for v in self.current_vouchers if v.id == vid), None)
            if cur_v:
                cur_rem = max(0.0, float(cur_v.total_amount or 0.0) - float(cur_v.paid_amount or 0.0))
                other_dues = max(0.0, self.current_student_total_pending - cur_rem)
                self.lbl_previous_dues.setText(
                    f"Previous Dues: Rs. {other_dues:,.0f}  |  Current Fee: Rs. {cur_rem:,.0f}  |  Total Payable: Rs. {self.current_student_total_pending:,.0f}"
                )

        self.recalc_totals()

    def add_category_row(self):
        used_cats = set()
        for r in range(self.tbl_items.rowCount()):
            w = self.tbl_items.cellWidget(r, 0)
            if w: used_cats.add(w.currentText())
        
        all_cats = FeeService.get_supported_categories()
        chosen = "Fine"
        for c in all_cats:
            if c not in used_cats and c != "Tuition Fee":
                chosen = c
                break
        self.add_item_row(category=chosen, description=f"{chosen} charge", orig_due=0.0, discount=0.0, paying_now=0.0, paid_earlier=0.0)

    def clear_empty_rows(self):
        rows_to_remove = []
        for r in range(self.tbl_items.rowCount()):
            sp_orig = self.tbl_items.cellWidget(r, 2)
            sp_pay = self.tbl_items.cellWidget(r, 6)
            if sp_orig and sp_pay:
                if sp_orig.value() == 0 and sp_pay.value() == 0:
                    rows_to_remove.append(r)
        
        if len(rows_to_remove) == self.tbl_items.rowCount():
            rows_to_remove = rows_to_remove[1:]
        
        for r in reversed(rows_to_remove):
            self.tbl_items.removeRow(r)
        
        self.recalc_totals()

    def add_item_row(self, category="Tuition Fee", description="", orig_due=0.0, discount=0.0, paying_now=0.0, voucher_item_id=None, paid_earlier=0.0):
        row = self.tbl_items.rowCount()
        self.tbl_items.insertRow(row)

        # 0. Category ComboBox
        cb_cat = QComboBox()
        cb_cat.addItems(FeeService.get_supported_categories())
        cb_cat.setCurrentText(category)
        cb_cat.setProperty("voucher_item_id", voucher_item_id)
        cb_cat.setProperty("initial_discount", float(discount or 0.0))
        cb_cat.setProperty("paid_earlier", float(paid_earlier or 0.0))
        cb_cat.currentIndexChanged.connect(self.recalc_totals)
        self.tbl_items.setCellWidget(row, 0, cb_cat)

        # 1. Description
        inp_desc = QLineEdit(description or f"{category} charge")
        self.tbl_items.setCellWidget(row, 1, inp_desc)

        # 2. Original Due
        sp_orig = QDoubleSpinBox()
        sp_orig.setRange(0, 10000000)
        sp_orig.setDecimals(0)
        sp_orig.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        sp_orig.setAlignment(Qt.AlignmentFlag.AlignRight)
        sp_orig.setValue(orig_due)
        sp_orig.valueChanged.connect(self.recalc_totals)
        self.tbl_items.setCellWidget(row, 2, sp_orig)

        # 3. Discount
        sp_disc = QDoubleSpinBox()
        sp_disc.setRange(0, 10000000)
        sp_disc.setDecimals(0)
        sp_disc.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        sp_disc.setAlignment(Qt.AlignmentFlag.AlignRight)
        sp_disc.setValue(discount)
        sp_disc.valueChanged.connect(self.recalc_totals)
        self.tbl_items.setCellWidget(row, 3, sp_disc)

        # 4. Already Paid (Label)
        lbl_paid = QLabel(f"Rs. {paid_earlier:,.0f}")
        lbl_paid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_paid.setFont(QFont("Segoe UI", 10))
        lbl_paid.setStyleSheet("color: #64748B;")
        self.tbl_items.setCellWidget(row, 4, lbl_paid)

        # 5. Net Due (Label)
        lbl_net = QLabel("0")
        lbl_net.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_net.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.tbl_items.setCellWidget(row, 5, lbl_net)

        # 6. Paying Now
        sp_pay = QDoubleSpinBox()
        sp_pay.setRange(0, 10000000)
        sp_pay.setDecimals(0)
        sp_pay.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        sp_pay.setAlignment(Qt.AlignmentFlag.AlignRight)
        sp_pay.setValue(paying_now)
        sp_pay.valueChanged.connect(self.recalc_totals)
        self.tbl_items.setCellWidget(row, 6, sp_pay)

        # 7. Remaining (Label)
        lbl_rem = QLabel("0")
        lbl_rem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_rem.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_rem.setStyleSheet("color: #DC2626;")
        self.tbl_items.setCellWidget(row, 7, lbl_rem)

        # 8. Action (Remove button)
        btn_del = ModernButton("", icon_name="trash-2", variant="danger")
        btn_del.setFixedSize(28, 28)
        btn_del.setToolTip("Remove this fee row")
        btn_del.clicked.connect(self.remove_item_row)
        self.tbl_items.setCellWidget(row, 8, btn_del)

        self.recalc_totals()

    def remove_item_row(self, btn=None):
        if not btn or isinstance(btn, bool):
            btn = self.sender()
        if not btn:
            return
        
        target_row = -1
        for r in range(self.tbl_items.rowCount()):
            if self.tbl_items.cellWidget(r, 8) == btn:
                target_row = r
                break
        
        if target_row >= 0:
            if self.tbl_items.rowCount() > 1:
                self.tbl_items.removeRow(target_row)
                self.recalc_totals()
            else:
                QMessageBox.information(self, "Note", "At least one fee row is required for collection.")

    def autofill_full_payment(self):
        for r in range(self.tbl_items.rowCount()):
            cb_cat = self.tbl_items.cellWidget(r, 0)
            sp_orig = self.tbl_items.cellWidget(r, 2)
            sp_disc = self.tbl_items.cellWidget(r, 3)
            sp_pay = self.tbl_items.cellWidget(r, 6)
            if cb_cat and sp_orig and sp_disc and sp_pay:
                paid_earlier = float(cb_cat.property("paid_earlier") or 0.0)
                net_due = max(0.0, sp_orig.value() - sp_disc.value() - paid_earlier)
                sp_pay.setValue(net_due)
        self.recalc_totals()

    def recalc_totals(self):
        tot_net = 0.0
        tot_pay = 0.0
        tot_rem = 0.0

        for r in range(self.tbl_items.rowCount()):
            cb_cat = self.tbl_items.cellWidget(r, 0)
            sp_orig = self.tbl_items.cellWidget(r, 2)
            sp_disc = self.tbl_items.cellWidget(r, 3)
            lbl_paid = self.tbl_items.cellWidget(r, 4)
            lbl_net = self.tbl_items.cellWidget(r, 5)
            sp_pay = self.tbl_items.cellWidget(r, 6)
            lbl_rem = self.tbl_items.cellWidget(r, 7)

            if cb_cat and sp_orig and sp_disc and lbl_net and sp_pay and lbl_rem:
                paid_earlier = float(cb_cat.property("paid_earlier") or 0.0)
                orig = sp_orig.value()
                disc = sp_disc.value()
                net_due = max(0.0, orig - disc - paid_earlier)
                pay = min(net_due, sp_pay.value())
                rem = max(0.0, net_due - pay)

                lbl_net.setText(f"Rs. {net_due:,.0f}")
                lbl_rem.setText(f"Rs. {rem:,.0f}")

                tot_net += net_due
                tot_pay += pay
                tot_rem += rem

        self.lbl_total_net.setText(f"Total Net: Rs. {tot_net:,.0f}")
        self.lbl_total_paying.setText(f"Total Paying: Rs. {tot_pay:,.0f}")
        self.lbl_total_rem.setText(f"Remaining Balance: Rs. {tot_rem:,.0f}")

    def process_payment(self, force_thermal=False):
        vid = self.combo_vouchers.currentData()
        if not vid:
            QMessageBox.warning(self, "Select Voucher", "Please select a pending voucher."); return

        # Extract allocations from rows
        allocations = []
        total_paying = 0.0
        total_discount = 0.0

        for r in range(self.tbl_items.rowCount()):
            cb_cat = self.tbl_items.cellWidget(r, 0)
            inp_desc = self.tbl_items.cellWidget(r, 1)
            sp_orig = self.tbl_items.cellWidget(r, 2)
            sp_disc = self.tbl_items.cellWidget(r, 3)
            sp_pay = self.tbl_items.cellWidget(r, 6)

            if cb_cat and sp_pay:
                p_val = sp_pay.value()
                v_item_id = cb_cat.property("voucher_item_id")
                initial_disc = float(cb_cat.property("initial_discount") or 0.0)
                cur_disc = sp_disc.value() if sp_disc else 0.0
                d_val = max(0.0, cur_disc - initial_disc) if v_item_id else cur_disc

                if p_val > 0 or d_val > 0:
                    allocations.append({
                        "voucher_item_id": v_item_id,
                        "category": cb_cat.currentText(),
                        "description": inp_desc.text().strip() if inp_desc else "",
                        "amount": sp_orig.value() if sp_orig else p_val,
                        "discount": d_val,
                        "paid_now": p_val
                    })
                    total_paying += p_val
                    total_discount += d_val

        if total_paying <= 0:
            QMessageBox.warning(self, "Invalid Amount", "Total paying amount must be greater than zero."); return

        # Disable button to prevent double-click duplicate payments
        self.btn_pay.setEnabled(False)
        self.btn_pay_thermal.setEnabled(False)
        self.btn_pay.setText("Processing Transaction & Generating Receipt...")

        try:
            success, msg, receipt_data = FeeService.process_payment(
                voucher_id=vid,
                amount_paid=total_paying,
                fine=0.0,
                discount=total_discount,
                method=self.pay_method.currentText(),
                allocations=allocations,
                notes=self.pay_notes.text().strip()
            )

            if success:
                # Check chosen format
                is_thermal = force_thermal or (hasattr(self, 'combo_receipt_format') and "thermal" in self.combo_receipt_format.currentText().lower())
                doc_type = "Thermal Fee Receipt" if is_thermal else "Fee Receipt"
                receipt_no = receipt_data["receipt_number"]

                try:
                    resolved = DataResolverService.get_fee_receipt_data(receipt_data.get("_payment_id", 0))
                    if resolved:
                        receipt_data.update(resolved)
                except Exception as e:
                    print(f"Data resolver notice: {e}")

                output_dir = os.path.join(os.path.dirname(DB_DIR), "generated_docs", "Fee_Receipts")
                os.makedirs(output_dir, exist_ok=True)
                file_prefix = f"Thermal_{receipt_no}" if is_thermal else receipt_no
                out_path = os.path.join(output_dir, f"{file_prefix}.pdf")

                with show_print_loading(self, title="Printing Fee Receipt...", subtitle=f"Generating {'80mm Thermal' if is_thermal else 'A4'} Receipt #{receipt_no}"):
                    pdf_success, pdf_msg = PDFGenerationService.generate_document(doc_type, receipt_data, out_path)
                    if pdf_success:
                        try: os.startfile(out_path)
                        except: pass
                        DocumentService.log_document(receipt_data.get("student_id", ""), doc_type, receipt_no, out_path)

                info_msg = msg
                if pdf_success:
                    info_msg += f"\n\nFee Receipt ({'80mm Thermal' if is_thermal else 'A4 Standard'}) generated:\n{out_path}"
                else:
                    info_msg += f"\n\n(PDF Generator Note: {pdf_msg})"

                QMessageBox.information(self, "Payment Successful", info_msg)
                
                # Reset Form
                self.inp_search.clear()
                self.lbl_stu_info.setText("Search a student to view their current fee position and vouchers.")
                self.lbl_category_dues.setText("")
                self.lbl_previous_dues.setText("Previous Dues: Rs. 0 | Current Fee: Rs. 0 | Total Payable: Rs. 0")
                self.combo_vouchers.clear()
                self.tbl_items.setRowCount(0)
                self.recalc_totals()
                self.refresh_all()
            else:
                QMessageBox.critical(self, "Payment Failed", msg)
        finally:
            self.btn_pay.setEnabled(True)
            self.btn_pay.setText("Collect Fee & Print Receipt ▾")
            if hasattr(self, 'btn_pay_thermal'):
                self.btn_pay_thermal.setEnabled(True)

    def prompt_issue_multiterm_voucher(self):
        if not hasattr(self, 'current_student') or not self.current_student:
            QMessageBox.warning(self, "No Student Selected", "Please search and select a student first.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Issue Multi-Term Voucher — {self.current_student.first_name}")
        dlg.setMinimumWidth(400)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(12)
        lay.addWidget(QLabel("<h3>Generate Multi-Term Package Voucher</h3><p style='color:#6B7280;'>Voucher will be added to this student's pending list immediately.</p>"))
        
        f = QFormLayout()
        cb_term = QComboBox(); cb_term.addItems(["6-Month", "Annual"])
        cb_month = QComboBox(); cb_month.addItems(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        cb_month.setCurrentIndex(max(0, QDate.currentDate().month() - 1))
        inp_yr = QLineEdit(str(QDate.currentDate().year()))
        
        f.addRow("Term Package:", cb_term)
        f.addRow("Start Month:", cb_month)
        f.addRow("Year:", inp_yr)
        lay.addLayout(f)
        
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel"); btn_cancel.clicked.connect(dlg.reject)
        btn_confirm = QPushButton("Generate Voucher"); btn_confirm.setObjectName("btn_primary")
        
        def on_confirm():
            t = cb_term.currentText()
            m = cb_month.currentText()
            y = inp_yr.text().strip()
            success, msg, v_id = FeeService.generate_multi_term_voucher(self.current_student.id, t, m, y)
            if success:
                QMessageBox.information(dlg, "Success", msg)
                dlg.accept()
                self.search_student()
            else:
                QMessageBox.critical(dlg, "Error", msg)
                
        btn_confirm.clicked.connect(on_confirm)
        btn_box.addStretch(); btn_box.addWidget(btn_cancel); btn_box.addWidget(btn_confirm)
        lay.addLayout(btn_box)
        dlg.exec()

    def run_generation(self):
        term = self.gen_term.currentText()
        if "6-Month" in term:
            start_m = self.gen_month.currentText()
            yr = self.gen_year.text().strip()
            reply = QMessageBox.question(self, "Confirm 6-Month Fee Generation", 
                f"Generate 6-Month fee vouchers starting from {start_m} {yr} for all active students?\n"
                "Individual 6-Month package fee rates from student profiles will be applied.")
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = FeeService.generate_bulk_multi_term_fees("6-Month", start_m, yr)
                if success:
                    QMessageBox.information(self, "Success", msg)
                    self.refresh_all()
                else:
                    QMessageBox.critical(self, "Error", msg)
        elif "Annual" in term:
            start_m = self.gen_month.currentText()
            yr = self.gen_year.text().strip()
            reply = QMessageBox.question(self, "Confirm Annual Fee Generation", 
                f"Generate Annual fee vouchers for {yr} for all active students?\n"
                "Individual Annual package fee rates from student profiles will be applied.")
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = FeeService.generate_bulk_multi_term_fees("Annual", start_m, yr)
                if success:
                    QMessageBox.information(self, "Success", msg)
                    self.refresh_all()
                else:
                    QMessageBox.critical(self, "Error", msg)
        else:
            month_str = f"{self.gen_month.currentText()} {self.gen_year.text()}"
            reply = QMessageBox.question(self, "Confirm Monthly Fee Generation", 
                f"Generate fees for {month_str}?\n"
                "Active students covered by 6-Month or Annual packages will be automatically protected from duplicate billing.")
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = FeeService.generate_monthly_fees(month_str, f"10 {month_str}")
                if success: 
                    QMessageBox.information(self, "Success", msg)
                    self.refresh_all()
                else: 
                    QMessageBox.critical(self, "Error", msg)

    def refresh_analytics(self):
        stats = FeeService.get_financial_analytics()
        self.card_today.value_label.setText(f"Rs. {stats['today_collection']:,.0f}")
        self.card_month.value_label.setText(f"Rs. {stats['monthly_collection']:,.0f}")
        self.card_pending.value_label.setText(f"Rs. {stats['total_pending']:,.0f}")
        
        cat_map = stats.get("category_totals", {})
        self.card_tuition.value_label.setText(f"Rs. {cat_map.get('Tuition Fee', 0.0):,.0f}")
        self.card_transport.value_label.setText(f"Rs. {cat_map.get('Transport Fee', 0.0):,.0f}")

    def refresh_pending_list(self):
        cls_id = self.filter_class_pending.currentData()
        search_str = self.search_pending.text().lower()
        vouchers = FeeService.get_all_pending_vouchers(class_id=cls_id)

        filtered_vouchers = []
        matched = 0
        for v in vouchers:
            s_name = f"{v.student.first_name} {v.student.last_name or ''}".strip().lower()
            s_id = v.student.student_id.lower()
            if search_str in s_name or search_str in s_id:
                filtered_vouchers.append(v)
                matched += 1
                if matched >= 200:
                    break

        for child in self.tbl_pending.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_pending.clearContents()

        self.tbl_pending.setRowCount(len(filtered_vouchers))
        for row, v in enumerate(filtered_vouchers):
            stu_name = f"{v.student.first_name} {v.student.last_name or ''}".strip()
            cls_name = v.student.academic_class.name if v.student.academic_class else "N/A"
            rem = (v.total_amount or 0.0) - (v.paid_amount or 0.0)

            id_item = QTableWidgetItem(v.student.student_id)
            id_item.setForeground(QColor("#2563EB"))
            id_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            id_item.setToolTip("Click to view complete student fee dossier")
            self.tbl_pending.setItem(row, 0, id_item)

            name_item = QTableWidgetItem(stu_name)
            name_item.setForeground(QColor("#1E293B"))
            name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            name_item.setToolTip("Click to view complete student fee dossier")
            self.tbl_pending.setItem(row, 1, name_item)

            self.tbl_pending.setItem(row, 2, QTableWidgetItem(cls_name))
            self.tbl_pending.setItem(row, 3, QTableWidgetItem(v.fee_month))

            rem_item = QTableWidgetItem(f"Rs. {rem:,.0f}")
            rem_item.setForeground(QColor("#EF4444"))
            rem_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tbl_pending.setItem(row, 4, rem_item)
            self.tbl_pending.setItem(row, 5, QTableWidgetItem(v.status))

            btn_pay = TableTextButton("Pay Now", icon_name="credit-card", variant="success")
            btn_pay.clicked.connect(lambda checked=False, s=v.student.student_id: self.jump_to_payment(s))
            self.tbl_pending.setCellWidget(row, 6, create_table_actions_cell([btn_pay]))
            self.tbl_pending.setRowHeight(row, 48)

    def refresh_history_list(self):
        for child in self.tbl_history.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_history.clearContents()

        payments = FeeService.get_payment_history(limit=100)
        self.tbl_history.setRowCount(len(payments))
        for row, p in enumerate(payments):
            stu_name = f"{p.voucher.student.first_name} {p.voucher.student.last_name or ''}".strip()
            stu_id = p.voucher.student.student_id
            self.tbl_history.setItem(row, 0, QTableWidgetItem(p.receipt_no))
            self.tbl_history.setItem(row, 1, QTableWidgetItem(p.payment_date))

            stu_item = QTableWidgetItem(f"{stu_name} ({stu_id})")
            stu_item.setForeground(QColor("#2563EB"))
            stu_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            stu_item.setData(Qt.ItemDataRole.UserRole, stu_id)
            stu_item.setToolTip("Click to view complete student fee dossier & transactions")
            self.tbl_history.setItem(row, 2, stu_item)

            self.tbl_history.setItem(row, 3, QTableWidgetItem(p.voucher.fee_month))
            amt_item = QTableWidgetItem(f"Rs. {p.amount_paid:,.0f}")
            amt_item.setForeground(QColor("#10B981"))
            amt_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.tbl_history.setItem(row, 4, amt_item)
            self.tbl_history.setItem(row, 5, QTableWidgetItem(p.payment_method))

            btn_rcpt = TableDropdownButton("Receipt", icon_name="printer", variant="secondary", height=28)
            receipt_dir = os.path.join(os.path.dirname(DB_DIR), "generated_docs", "Fee_Receipts")
            a4_file = os.path.join(receipt_dir, f"{p.receipt_no}.pdf")
            thermal_file = os.path.join(receipt_dir, f"Thermal_{p.receipt_no}.pdf")

            btn_rcpt.add_menu_action(
                "A4 Detailed Receipt",
                lambda checked=False, f=a4_file, r=p.receipt_no, p_obj=p: self._open_receipt_pdf(f, r, is_thermal=False, payment=p_obj),
                icon_name="file-text", icon_color="#2563EB"
            )
            btn_rcpt.add_menu_action(
                "Thermal Receipt (80mm)",
                lambda checked=False, f=thermal_file, r=p.receipt_no, p_obj=p: self._open_receipt_pdf(f, r, is_thermal=True, payment=p_obj),
                icon_name="printer", icon_color="#059669"
            )

            self.tbl_history.setCellWidget(row, 6, create_table_actions_cell([btn_rcpt]))
            self.tbl_history.setRowHeight(row, 48)

    def on_history_cell_clicked(self, row, col):
        if col == 2:
            item = self.tbl_history.item(row, col)
            if item:
                stu_id = item.data(Qt.ItemDataRole.UserRole)
                if stu_id:
                    self.show_student_fee_details(stu_id)

    def on_pending_cell_clicked(self, row, col):
        if col in (0, 1):
            item = self.tbl_pending.item(row, 0)
            if item:
                stu_id = item.text().strip()
                if stu_id:
                    self.show_student_fee_details(stu_id)

    def show_student_fee_details(self, student_id_or_obj):
        if not student_id_or_obj:
            return
        if isinstance(student_id_or_obj, str):
            student, _ = FeeService.search_student_for_payment(student_id_or_obj)
        else:
            student = student_id_or_obj
        if not student:
            QMessageBox.information(self, "Not Found", "Student details could not be loaded.")
            return

        dlg = StudentFeeDossierDialog(
            parent=self,
            student=student,
            on_collect=lambda s_id: self.jump_to_payment(s_id),
            on_ledger=lambda s_id: self.jump_to_ledger(s_id)
        )
        dlg.exec()

    def jump_to_ledger(self, student_id):
        self.tabs.setCurrentIndex(2)
        self.inp_ledger_search.setText(student_id)
        self.search_ledger()

    def _open_receipt_pdf(self, file_path, receipt_no, is_thermal=False, payment=None):
        with show_print_loading(self, title=f"Loading {'Thermal' if is_thermal else 'A4'} Receipt...", subtitle=f"Receipt #{receipt_no}"):
            if not os.path.exists(file_path) and is_thermal and payment:
                # Generate thermal receipt dynamically on the fly
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    v = payment.voucher
                    stu = v.student if v else None
                    data_dict = {
                        "receipt_no": payment.receipt_no,
                        "student.id": stu.student_id if stu else "",
                        "student.name": f"{stu.first_name} {stu.last_name or ''}".strip() if stu else "Student",
                        "student.admission_no": getattr(stu, 'admission_number', '') if stu else "",
                        "academic.class_name": stu.academic_class.name if stu and stu.academic_class else "-",
                        "fee.month_year": v.fee_month if v else "",
                        "amount_received": str(int(payment.amount_paid or 0)),
                        "total_discount": "0",
                        "total_remaining_balance": str(int(max(0, (v.total_amount or 0) - (v.paid_amount or 0)))) if v else "0",
                        "paid_date": payment.payment_date or datetime.now().strftime("%Y-%m-%d"),
                        "payment_mode": payment.payment_method or "Cash",
                    }
                    if v and hasattr(v, 'items') and v.items:
                        for i, itm in enumerate(v.items):
                            data_dict[f"fee.item_{i}_title"] = getattr(itm, 'category_name', 'Fee')
                            data_dict[f"fee.item_{i}_paid"] = str(int(getattr(itm, 'amount', 0) or 0))
                    else:
                        data_dict["fee.item_0_title"] = f"Tuition Fee ({data_dict['fee.month_year']})"
                        data_dict["fee.item_0_paid"] = str(int(payment.amount_paid or 0))

                    from core.builtin_pdf_generator import BuiltinPDFGenerator
                    BuiltinPDFGenerator.generate_thermal_fee_receipt(data_dict, file_path)
                except Exception as gen_err:
                    print(f"Error auto-generating thermal receipt: {gen_err}")

            if os.path.exists(file_path):
                try:
                    os.startfile(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not open PDF: {e}")
            else:
                QMessageBox.information(self, "Info", f"Receipt {receipt_no} PDF file was not found on disk at:\n{file_path}")
