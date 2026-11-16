import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTabWidget, QMessageBox, QFrame, QAbstractItemView, 
    QGridLayout, QFormLayout, QLineEdit, QDateEdit, QDoubleSpinBox, QFileDialog, QScrollArea,
    QDialog, QTextEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from core.analytics_service import AnalyticsService
from core.state_manager import app_state
from core.theme_manager import ThemeManager
from core.icon_manager import icon_mgr
from ui.views.analytics.audit_dialog import AuditDiagnosticDialog
from ui.components.stitch_widgets import (
    PageHeader, MetricCard, ModernButton, ModernCard, StatusBadge,
    TableActionButton, TableTextButton, create_table_actions_cell,
    style_modern_table, style_modern_tabs
)

# ── Vendor & Expense Detail Dialog ─────────────────────────────────────────────
class VendorDetailDialog(QDialog):
    """Modern modal dialog showing full, un-truncated vendor and expense details."""
    def __init__(self, exp_data: dict, parent=None):
        super().__init__(parent)
        self.exp_data = exp_data
        self.setWindowTitle("Vendor & Expense Details")
        self.setMinimumSize(540, 500)
        t = ThemeManager.tokens()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['dialog_bg']};
                color: {t['text_primary']};
                font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial, sans-serif;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header with vector icon and title
        header_lay = QHBoxLayout()
        header_lay.setSpacing(14)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon_mgr.get_icon("building-2", color="#2563EB").pixmap(28, 28))
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: #EFF6FF; border-radius: 12px; border: 1px solid #DBEAFE;")

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        vendor_name = exp_data.get("vendor_payee") or "No Vendor Specified"
        v_title = QLabel(vendor_name)
        v_title.setFont(QFont("Plus Jakarta Sans", 16, QFont.Weight.Bold))
        v_title.setStyleSheet(f"color: {t['text_primary']}; font-weight: bold; background: transparent;")
        
        v_sub = QLabel(f"Category: {exp_data.get('category', '-')} • Date: {exp_data.get('expense_date', '-')}")
        v_sub.setFont(QFont("Plus Jakarta Sans", 11))
        v_sub.setStyleSheet("color: #64748B; background: transparent;")
        title_col.addWidget(v_title)
        title_col.addWidget(v_sub)

        header_lay.addWidget(icon_lbl)
        header_lay.addLayout(title_col)
        header_lay.addStretch()
        layout.addLayout(header_lay)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: #E2E8F0; border: none;")
        layout.addWidget(div)

        # Key details grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)

        def _row(grid_layout, r, label, val_text, is_bold=False, color=t["text_primary"]):
            lbl = QLabel(label)
            lbl.setFont(QFont("Plus Jakarta Sans", 10, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
            val = QLabel(val_text)
            val.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold if is_bold else QFont.Weight.Normal))
            val.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid_layout.addWidget(lbl, r, 0)
            grid_layout.addWidget(val, r, 1)

        amount_str = f"Rs. {exp_data.get('amount', 0):,.0f}"
        _row(grid, 0, "Vendor / Payee:", vendor_name, is_bold=True)
        _row(grid, 1, "Amount Paid:", amount_str, is_bold=True, color="#2563EB")
        _row(grid, 2, "Payment Method:", str(exp_data.get("payment_method") or "Cash"))
        _row(grid, 3, "Receipt / Ref #:", str(exp_data.get("reference_no") or "-"), is_bold=True)
        _row(grid, 4, "Academic Session:", str(exp_data.get("academic_session") or "-"))
        if exp_data.get("created_at"):
            _row(grid, 5, "Recorded At:", str(exp_data.get("created_at")))
        layout.addLayout(grid)

        # Full Description Box
        desc_lbl = QLabel("Full Description / Details:")
        desc_lbl.setFont(QFont("Plus Jakarta Sans", 10, QFont.Weight.Bold))
        desc_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
        layout.addWidget(desc_lbl)

        desc_box = QTextEdit()
        desc_box.setReadOnly(True)
        desc_box.setPlainText(exp_data.get("description") or "No additional description entered.")
        desc_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                line-height: 1.4;
            }}
        """)
        desc_box.setMinimumHeight(90)
        layout.addWidget(desc_box)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        btn_edit = ModernButton("Edit in Form", icon_name="pencil", variant="primary")
        btn_edit.setFixedHeight(36)
        btn_edit.clicked.connect(self._on_edit_clicked)

        btn_close = ModernButton("Close", variant="secondary")
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(btn_edit)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _on_edit_clicked(self):
        parent = self.parent()
        if parent and hasattr(parent, "populate_expense_form"):
            parent.populate_expense_form(self.exp_data)
        self.accept()


class AnalyticsView(QWidget):
    """Phase 17: Modern Executive Analytics & Financial Intelligence."""
    def __init__(self):
        super().__init__()
        t = ThemeManager.tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        btn_audit = ModernButton("Run Audit Diagnostic", icon_name="shield-check", variant="success")
        btn_audit.clicked.connect(self._run_audit_diagnostic)

        btn_refresh = ModernButton("Refresh Data", icon_name="rotate-cw", variant="secondary")
        btn_refresh.clicked.connect(self.refresh_all)

        header = PageHeader(
            title="Analytics & Financial Intelligence",
            subtitle="Executive KPIs, operations expense management, and institutional audit reports",
            icon_name="bar-chart-2",
            actions=[btn_audit, btn_refresh]
        )
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        self.tabs.addTab(self.create_executive_tab(), "Overview")
        self.tabs.setTabIcon(0, icon_mgr.get_icon("trending-up", color=t["text_secondary"]))

        self.tabs.addTab(self.create_expense_tab(), "Expense Management")
        self.tabs.setTabIcon(1, icon_mgr.get_icon("receipt", color=t["text_secondary"]))

        self.tabs.addTab(self.create_export_tab(), "Reports & Export")
        self.tabs.setTabIcon(2, icon_mgr.get_icon("file-spreadsheet", color=t["text_secondary"]))

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
        tbl.verticalHeader().setDefaultSectionSize(42)
        tbl.setAlternatingRowColors(True)
        style_modern_table(tbl)
        return tbl

    def refresh_all(self):
        self.load_executive_kpis()
        self.load_expenses()

    # ==========================================
    # TAB 1: OVERVIEW
    # ==========================================
    def create_executive_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 20)
        lay.setSpacing(20)
        
        grid_fin = QHBoxLayout()
        grid_fin.setSpacing(14)
        self.lbl_rev = MetricCard("Total Revenue", "Rs. 0", "Collected", "dollar-sign", "#2563EB", "#EFF6FF")
        self.lbl_exp = MetricCard("Total Expenses", "Rs. 0", "Paid out", "trending-down", "#DC2626", "#FEF2F2")
        self.lbl_prof = MetricCard("Net Profit", "Rs. 0", "Overall", "building-2", "#10B981", "#ECFDF5")
        self.lbl_out = MetricCard("Outstanding", "Rs. 0", "Receivable", "alert-triangle", "#D97706", "#FFFBEB")
        
        grid_fin.addWidget(self.lbl_rev)
        grid_fin.addWidget(self.lbl_exp)
        grid_fin.addWidget(self.lbl_prof)
        grid_fin.addWidget(self.lbl_out)
        lay.addLayout(grid_fin)
        
        chart_box = ModernCard()
        chart_lay = QVBoxLayout(chart_box)
        chart_lay.setContentsMargins(24, 20, 24, 24)
        chart_lay.setSpacing(14)
        
        lbl_title = QLabel("Financial Ratio Overview")
        lbl_title.setFont(QFont("Plus Jakarta Sans", 14, QFont.Weight.Bold))
        chart_lay.addWidget(lbl_title)
        
        rev_head = QHBoxLayout()
        lbl_r1 = QLabel("Collected Revenue")
        lbl_r1.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
        self.lbl_r2 = QLabel("0")
        self.lbl_r2.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
        rev_head.addWidget(lbl_r1)
        rev_head.addStretch()
        rev_head.addWidget(self.lbl_r2)
        chart_lay.addLayout(rev_head)
        
        self.bar_rev = QFrame()
        self.bar_rev.setFixedHeight(12)
        self.bar_rev.setStyleSheet("background: #2563EB; border-radius: 6px;")
        chart_lay.addWidget(self.bar_rev)

        exp_head = QHBoxLayout()
        lbl_e1 = QLabel("Total Expenses")
        lbl_e1.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
        self.lbl_e2 = QLabel("0")
        self.lbl_e2.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
        exp_head.addWidget(lbl_e1)
        exp_head.addStretch()
        exp_head.addWidget(self.lbl_e2)
        chart_lay.addLayout(exp_head)
        
        self.bar_exp = QFrame()
        self.bar_exp.setFixedHeight(12)
        self.bar_exp.setStyleSheet("background: #EF4444; border-radius: 6px;")
        chart_lay.addWidget(self.bar_exp)
        lay.addWidget(chart_box)

        grid_aca = QHBoxLayout()
        grid_aca.setSpacing(14)
        self.lbl_stu = MetricCard("Total Students", "0", "Active", "graduation-cap", "#2563EB", "#EFF6FF")
        self.lbl_tch = MetricCard("Total Teachers", "0", "Active", "users", "#7C3AED", "#F5F3FF")
        self.lbl_stf = MetricCard("Support Staff", "0", "Active", "user-check", "#EC4899", "#FDF2F8")
        self.lbl_msg = MetricCard("Comms Sent", "0", "Delivered", "message-square", "#14B8A6", "#F0FDFA")
        
        grid_aca.addWidget(self.lbl_stu)
        grid_aca.addWidget(self.lbl_tch)
        grid_aca.addWidget(self.lbl_stf)
        grid_aca.addWidget(self.lbl_msg)
        lay.addLayout(grid_aca)
        
        lay.addStretch()
        scroll.setWidget(page)
        return scroll

    def load_executive_kpis(self):
        kpis = AnalyticsService.get_executive_kpis()
        
        self.lbl_rev.value_label.setText(f"Rs. {kpis['total_revenue']:,.0f}")
        self.lbl_exp.value_label.setText(f"Rs. {kpis['total_operating_expenses']:,.0f}")
        self.lbl_out.value_label.setText(f"Rs. {kpis['outstanding_fees']:,.0f}")
        
        prof = kpis['net_operating_surplus']
        if prof < 0:
            self.lbl_prof.value_label.setText(f"-Rs. {abs(prof):,.0f}")
            self.lbl_prof.value_label.setStyleSheet("color: #DC2626; font-size: 20px; font-weight: 800; border: none; background: transparent;")
        else:
            self.lbl_prof.value_label.setText(f"Rs. {prof:,.0f}")
            self.lbl_prof.value_label.setStyleSheet("color: #10B981; font-size: 20px; font-weight: 800; border: none; background: transparent;")

        if hasattr(self.lbl_exp, "sub_label"):
            self.lbl_exp.sub_label.setText(f"Ops: Rs. {kpis.get('total_operating_expenses', 0):,.0f} | Store: Rs. {kpis.get('total_store_purchases', 0):,.0f}")
            self.lbl_exp.sub_label.show()
        if hasattr(self.lbl_prof, "sub_label"):
            self.lbl_prof.sub_label.setText(f"Cash Flow: Rs. {kpis.get('net_cash_surplus', 0):,.0f}")
            self.lbl_prof.sub_label.show()

        self.lbl_exp.setToolTip(
            f"Operational Utility Bills: Rs. {kpis.get('total_operating_bills', 0):,.0f}\n"
            f"Staff Salaries Paid: Rs. {kpis.get('total_salary_expense', 0):,.0f}\n"
            f"Total Operating Expenses: Rs. {kpis.get('total_operating_expenses', 0):,.0f}\n"
            f"Store Capital Purchases: Rs. {kpis.get('total_store_purchases', 0):,.0f}\n"
            f"Total Cash Outflows: Rs. {kpis.get('total_cash_outflows', 0):,.0f}"
        )
        self.lbl_prof.setToolTip(
            f"Net Operating Surplus: Rs. {kpis.get('net_operating_surplus', 0):,.0f}\n"
            f"Net Cash Flow Surplus: Rs. {kpis.get('net_cash_surplus', 0):,.0f}"
        )

        max_val = max(kpis['total_revenue'], kpis['total_operating_expenses'], 1) 
        rev_pct = int((kpis['total_revenue'] / max_val) * 100)
        exp_pct = int((kpis['total_operating_expenses'] / max_val) * 100)
        
        self.bar_rev.setFixedWidth(max(10, int(800 * (rev_pct / 100))))
        self.bar_exp.setFixedWidth(max(10, int(800 * (exp_pct / 100))))
        
        self.lbl_r2.setText(f"Rs. {kpis['total_revenue']:,.0f}")
        self.lbl_e2.setText(f"Rs. {kpis['total_operating_expenses']:,.0f} (Operating)")

        self.lbl_stu.value_label.setText(str(kpis['total_students']))
        self.lbl_tch.value_label.setText(str(kpis['active_teachers']))
        self.lbl_stf.value_label.setText(str(kpis['active_staff']))
        self.lbl_msg.value_label.setText(str(kpis['messages_sent']))

    # ==========================================
    # TAB 2: EXPENSE MANAGEMENT
    # ==========================================
    def create_expense_tab(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 14)
        lay.setSpacing(16)
        
        form_card = ModernCard()
        fl = QFormLayout(form_card)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.setSpacing(12)
        
        lbl_title = QLabel("Log Operations Expense")
        lbl_title.setFont(QFont("Plus Jakarta Sans", 13, QFont.Weight.Bold))
        lbl_title.setStyleSheet("border: none; background: transparent; margin-bottom: 4px;")
        fl.addRow(lbl_title)

        def _lbl(txt):
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-weight: 600; font-size: 13px; border: none; background: transparent;")
            return lbl

        self.e_id = None
        self.e_date = QDateEdit(QDate.currentDate())
        self.e_date.setCalendarPopup(True)
        self.e_date.setMinimumHeight(34)

        self.e_cat = QComboBox()
        self.e_cat.setMinimumHeight(34)
        self.e_cat.addItems([
            "Electricity", "Internet/Comm", "Building Maintenance", "Inventory Purchases",
            "Transportation & Fuel", "Events/Marketing", "IT/Software", "Stationery",
            "Lab & Sports Equipment", "Taxes & Levies", "Other"
        ])

        self.e_amount = QDoubleSpinBox()
        self.e_amount.setRange(0, 10000000)
        self.e_amount.setPrefix("Rs. ")
        self.e_amount.setMinimumHeight(34)

        self.e_method = QComboBox()
        self.e_method.addItems(["Cash", "Bank Transfer", "Cheque"])
        self.e_method.setMinimumHeight(34)

        self.e_vendor = QLineEdit()
        self.e_vendor.setMinimumHeight(34)
        self.e_vendor.setPlaceholderText("Vendor or payee name...")

        self.e_ref = QLineEdit()
        self.e_ref.setMinimumHeight(34)
        self.e_ref.setPlaceholderText("Receipt or voucher ref...")

        self.e_desc = QLineEdit()
        self.e_desc.setMinimumHeight(34)
        self.e_desc.setPlaceholderText("Optional notes...")
        
        fl.addRow(_lbl("Expense Date:"), self.e_date)
        fl.addRow(_lbl("Category:"), self.e_cat)
        fl.addRow(_lbl("Amount:"), self.e_amount)
        fl.addRow(_lbl("Payment Method:"), self.e_method)
        fl.addRow(_lbl("Vendor/Payee:"), self.e_vendor)
        fl.addRow(_lbl("Receipt #:"), self.e_ref)
        fl.addRow(_lbl("Description:"), self.e_desc)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_save = ModernButton("Save Expense", icon_name="check", variant="primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self.save_expense)

        btn_clear = ModernButton("Cancel", variant="secondary")
        btn_clear.setFixedHeight(36)
        btn_clear.clicked.connect(self.clear_expense_form)

        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_clear)
        fl.addRow("", btn_box)
        
        table_card = ModernCard()
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(16, 14, 16, 14)
        
        self.tbl_exp = self._table()
        self.tbl_exp.setColumnCount(5)
        self.tbl_exp.setHorizontalHeaderLabels(["Date", "Category", "Amount", "Vendor / Details", "Action"])
        self.tbl_exp.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.tbl_exp.setColumnWidth(4, 110)
        self.tbl_exp.verticalHeader().setDefaultSectionSize(48)
        self.tbl_exp.cellClicked.connect(self._on_table_cell_clicked)
        self.tbl_exp.cellDoubleClicked.connect(self._on_table_cell_clicked)
        
        tl.addWidget(self.tbl_exp)
        
        lay.addWidget(form_card, stretch=3)
        lay.addWidget(table_card, stretch=7)
        return page

    def _on_table_cell_clicked(self, row, col):
        if col == 4:  # Action column with Delete button
            return
        item = self.tbl_exp.item(row, 3)
        if item:
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                dlg = VendorDetailDialog(data, self)
                dlg.exec()

    def populate_expense_form(self, data):
        self.e_id = data.get("id")
        d_str = data.get("expense_date")
        if d_str:
            qdate = QDate.fromString(str(d_str), "yyyy-MM-dd")
            if qdate.isValid():
                self.e_date.setDate(qdate)

        cat = data.get("category")
        if cat:
            idx = self.e_cat.findText(cat)
            if idx >= 0:
                self.e_cat.setCurrentIndex(idx)

        self.e_amount.setValue(float(data.get("amount") or 0))

        method = data.get("payment_method")
        if method:
            idx = self.e_method.findText(method)
            if idx >= 0:
                self.e_method.setCurrentIndex(idx)

        self.e_vendor.setText(str(data.get("vendor_payee") or ""))
        self.e_ref.setText(str(data.get("reference_no") or ""))
        self.e_desc.setText(str(data.get("description") or ""))

    def save_expense(self):
        if self.e_amount.value() <= 0:
            QMessageBox.warning(self, "Error", "Amount must be greater than zero.")
            return
        success, msg = AnalyticsService.save_expense(
            self.e_id, self.e_date.date().toString("yyyy-MM-dd"), self.e_cat.currentText(), self.e_amount.value(),
            self.e_method.currentText(), self.e_vendor.text(), self.e_ref.text(), self.e_desc.text()
        )
        if success:
            self.load_expenses()
            self.clear_expense_form()
            self.load_executive_kpis()
        else:
            QMessageBox.critical(self, "Error", msg)

    def clear_expense_form(self):
        self.e_id = None
        self.e_amount.setValue(0)
        self.e_vendor.clear()
        self.e_ref.clear()
        self.e_desc.clear()

    def load_expenses(self):
        for child in self.tbl_exp.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_exp.clearContents()

        session_name = app_state.get_setting("session", "Default")
        recs = AnalyticsService.get_expenses(session_name)
        self.tbl_exp.setRowCount(len(recs))
        for r, e in enumerate(recs):
            d_item = QTableWidgetItem(str(e.expense_date))
            self.tbl_exp.setItem(r, 0, d_item)

            c_item = QTableWidgetItem(e.category)
            self.tbl_exp.setItem(r, 1, c_item)
            
            amt_item = QTableWidgetItem(f"Rs. {e.amount:,.0f}")
            amt_item.setFont(QFont("Plus Jakarta Sans", 10, QFont.Weight.Bold))
            self.tbl_exp.setItem(r, 2, amt_item)
            
            e_data = {
                "id": e.id,
                "expense_date": str(e.expense_date),
                "category": str(e.category or ""),
                "amount": float(e.amount or 0.0),
                "payment_method": str(e.payment_method or "Cash"),
                "vendor_payee": str(e.vendor_payee or ""),
                "reference_no": str(e.reference_no or ""),
                "description": str(e.description or ""),
                "academic_session": str(e.academic_session or ""),
                "created_at": str(getattr(e, "created_at", "") or ""),
            }

            detail = f"{e.vendor_payee or '-'}\n(Ref: {e.reference_no or '-'} | {e.description or '-'})"
            det_item = QTableWidgetItem(detail)
            det_item.setData(Qt.ItemDataRole.UserRole, e_data)
            det_item.setToolTip("Click to view full vendor and expense details")
            self.tbl_exp.setItem(r, 3, det_item)
            
            btn_void = TableTextButton("Delete", icon_name="trash-2", variant="danger")
            btn_void.clicked.connect(lambda checked=False, eid=e.id: self.void_expense(eid))
            self.tbl_exp.setCellWidget(r, 4, create_table_actions_cell([btn_void]))
            self.tbl_exp.setRowHeight(r, 48)

    def void_expense(self, eid):
        if QMessageBox.question(self, "Confirm", "Delete this expense permanently? It will be removed from Profit/Loss calculations.") == QMessageBox.StandardButton.Yes:
            AnalyticsService.void_expense(eid)
            self.load_expenses()
            self.load_executive_kpis()

    def _run_audit_diagnostic(self):
        diag = AuditDiagnosticDialog(parent=self)
        diag.exec()

    # ==========================================
    # TAB 3: EXPORTS
    # ==========================================
    def create_export_tab(self):
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 14, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        card = ModernCard()
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(32, 28, 32, 32)
        c_lay.setSpacing(14)

        lbl_title = QLabel("Executive Data Export & Reconciled Audit")
        lbl_title.setFont(QFont("Plus Jakarta Sans", 16, QFont.Weight.Bold))
        c_lay.addWidget(lbl_title)
        
        lbl_sub = QLabel("Generate audited external reports combining Finance, HR, Academics, Store Inventory, and Communication ledgers.")
        lbl_sub.setStyleSheet("font-size: 13px; color: #64748B;")
        c_lay.addWidget(lbl_sub)
        c_lay.addSpacing(10)
        
        btn_box = QHBoxLayout()
        btn_box.setSpacing(16)

        btn_excel = ModernButton("Download Master Excel Workbook", icon_name="file-spreadsheet", variant="primary")
        btn_excel.setFixedHeight(44)
        btn_excel.clicked.connect(self.export_excel)
        btn_box.addWidget(btn_excel)

        btn_audit = ModernButton("Run Financial Audit Diagnostic", icon_name="shield-check", variant="success")
        btn_audit.setFixedHeight(44)
        btn_audit.clicked.connect(self._run_audit_diagnostic)
        btn_box.addWidget(btn_audit)

        btn_box.addStretch()
        c_lay.addLayout(btn_box)
        lay.addWidget(card)
        
        return page

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Master Analytics", "UEMS_Master_Reconciled_Report.xlsx", "Excel Files (*.xlsx)")
        if path:
            success, msg = AnalyticsService.export_master_excel(path)
            if success:
                QMessageBox.information(self, "Exported", f"Master Report Saved to:\n{path}")
            else:
                QMessageBox.critical(self, "Error", msg)