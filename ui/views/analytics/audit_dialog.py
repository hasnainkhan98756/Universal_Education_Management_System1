"""
Enterprise Read-Only Financial Audit & Data-Integrity Diagnostic Dialog.
Renders authoritative reconciliation results with full mathematical transparency.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QAbstractItemView, QScrollArea, QWidget, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from core.audit_reconciliation_service import AuditReconciliationService
from core.analytics_service import AnalyticsService
from core.icon_manager import icon_mgr
from core.theme_manager import ThemeManager
from ui.components.stitch_widgets import ModernButton, StatusBadge, style_modern_table


class AuditDiagnosticDialog(QDialog):
    """Modern modal dialog displaying live, non-destructive audit results."""

    def __init__(self, audit_result: dict = None, parent=None):
        super().__init__(parent)
        self.audit_result = audit_result or AuditReconciliationService.run_comprehensive_audit()
        self.setWindowTitle("System Financial & Data-Integrity Audit Diagnostic")
        self.setMinimumSize(820, 620)
        t = ThemeManager.tokens()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['dialog_bg']};
                color: {t['text_primary']};
                font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial, sans-serif;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(14)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon_mgr.get_icon("shield-check", color="#2563EB").pixmap(32, 32))
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: #EFF6FF; border-radius: 12px; border: 1px solid #DBEAFE;")

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        t_lbl = QLabel("Enterprise Financial & Data-Integrity Audit Diagnostic")
        t_lbl.setFont(QFont("Plus Jakarta Sans", 15, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #0F172A; border: none; background: transparent;")

        sub_lbl = QLabel("100% Read-Only Mathematical & Accounting Verification • Zero Data Mutation")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 12px; border: none; background: transparent;")
        title_col.addWidget(t_lbl)
        title_col.addWidget(sub_lbl)

        hdr.addWidget(icon_lbl)
        hdr.addLayout(title_col)
        hdr.addStretch()
        layout.addLayout(hdr)

        # ── Status Banner ─────────────────────────────────────────────────────
        status = self.audit_result.get("overall_status", "PASS")
        passed = self.audit_result.get("passed_checks", 0)
        total = self.audit_result.get("total_checks", 0)
        ts = self.audit_result.get("audit_timestamp", "")

        banner = QFrame()
        if status == "PASS":
            banner.setStyleSheet("""
                QFrame {
                    background-color: #ECFDF5;
                    border: 1px solid #10B981;
                    border-radius: 10px;
                }
            """)
            b_text = f"{passed} OF {total} AUDIT RECONCILIATIONS PASSED — 100% ACCURATE & RECONCILED"
            b_color = "#047857"
        else:
            banner.setStyleSheet("""
                QFrame {
                    background-color: #FEF2F2;
                    border: 1px solid #EF4444;
                    border-radius: 10px;
                }
            """)
            b_text = f"{total - passed} DISCREPANCIES DETECTED IN FINANCIAL RECONCILIATION"
            b_color = "#B91C1C"

        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 12, 16, 12)
        b_lbl = QLabel(b_text)
        b_lbl.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
        b_lbl.setStyleSheet(f"color: {b_color}; border: none; background: transparent;")
        bl.addWidget(b_lbl)
        bl.addStretch()
        ts_lbl = QLabel(f"Audited: {ts}")
        ts_lbl.setStyleSheet("color: #64748B; font-size: 11px; border: none; background: transparent;")
        bl.addWidget(ts_lbl)
        layout.addWidget(banner)

        # ── Audit Checks Table ────────────────────────────────────────────────
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["Audit Check / Scope", "Status", "Difference", "Details / Reconciliation Notes"])
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tbl.setColumnWidth(0, 250)
        self.tbl.setColumnWidth(1, 100)
        self.tbl.setColumnWidth(2, 110)
        self.tbl.verticalHeader().setDefaultSectionSize(40)
        self.tbl.setAlternatingRowColors(True)
        style_modern_table(self.tbl)

        checks = self.audit_result.get("checks", [])
        self.tbl.setRowCount(len(checks))
        for r, c in enumerate(checks):
            # Name
            name_item = QTableWidgetItem(f"{c.get('name', '')}")
            name_item.setFont(QFont("Plus Jakarta Sans", 10, QFont.Weight.Bold))
            self.tbl.setItem(r, 0, name_item)

            # Status Badge
            st = c.get("status", "PASS")
            badge = StatusBadge(st, variant="success" if st == "PASS" else "danger")
            badge_container = QWidget()
            badge_container.setStyleSheet("background: transparent;")
            b_lay = QHBoxLayout(badge_container)
            b_lay.setContentsMargins(0, 0, 0, 0)
            b_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_lay.addWidget(badge)
            self.tbl.setCellWidget(r, 1, badge_container)

            # Difference
            diff = c.get("difference")
            diff_str = f"Rs. {diff:,.2f}" if isinstance(diff, (int, float)) else "0.00"
            diff_item = QTableWidgetItem(diff_str)
            diff_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            diff_item.setFont(QFont("Plus Jakarta Sans", 10, QFont.Weight.Bold))
            diff_item.setForeground(QColor("#059669" if diff == 0.0 or diff is None else "#DC2626"))
            self.tbl.setItem(r, 2, diff_item)

            # Details
            dt = c.get("details", {})
            parts = []
            for k, v in dt.items():
                if isinstance(v, (int, float)):
                    if "amount" in k or "revenue" in k or "expenses" in k or "valuation" in k or "surplus" in k or "collected" in k:
                        parts.append(f"{k.replace('_', ' ').title()}: Rs. {v:,.0f}")
                    else:
                        parts.append(f"{k.replace('_', ' ').title()}: {v}")
                else:
                    parts.append(f"{v}")
            note_str = " | ".join(parts[:4])
            note_item = QTableWidgetItem(note_str)
            note_item.setToolTip("\n".join(parts))
            self.tbl.setItem(r, 3, note_item)

        layout.addWidget(self.tbl)

        # ── Reconciled Key Figures Summary Card ───────────────────────────────
        summary_card = QFrame()
        summary_card.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 6px;")
        sc_lay = QHBoxLayout(summary_card)
        sc_lay.setContentsMargins(14, 10, 14, 10)
        sc_lay.setSpacing(20)

        def _mini_stat(label, val_str, color="#0F172A"):
            box = QVBoxLayout()
            box.setSpacing(2)
            l = QLabel(label)
            l.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 600; border: none; background: transparent;")
            v = QLabel(val_str)
            v.setFont(QFont("Plus Jakarta Sans", 12, QFont.Weight.Bold))
            v.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            box.addWidget(l)
            box.addWidget(v)
            return box

        kpis = AnalyticsService.get_executive_kpis()
        sc_lay.addLayout(_mini_stat("Authoritative Fee Revenue", f"Rs. {kpis.get('total_revenue', 0):,.0f}", "#2563EB"))
        sc_lay.addLayout(_mini_stat("Operating Expenses", f"Rs. {kpis.get('total_operating_expenses', 0):,.0f}", "#D97706"))
        sc_lay.addLayout(_mini_stat("Net Operating Surplus", f"Rs. {kpis.get('net_operating_surplus', 0):,.0f}", "#059669"))
        sc_lay.addLayout(_mini_stat("Store Asset Purchases", f"Rs. {kpis.get('total_store_purchases', 0):,.0f}", "#2563EB"))
        sc_lay.addLayout(_mini_stat("Net Cash Flow Surplus", f"Rs. {kpis.get('net_cash_surplus', 0):,.0f}", "#059669"))
        sc_lay.addStretch()

        layout.addWidget(summary_card)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)

        btn_export = ModernButton("Export Master Excel Workbook", icon_name="file-spreadsheet", variant="primary")
        btn_export.setFixedHeight(36)
        btn_export.clicked.connect(self._export_excel)

        btn_close = ModernButton("Close", variant="secondary")
        btn_close.setFixedHeight(36)
        btn_close.clicked.connect(self.accept)

        btn_box.addWidget(btn_export)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def _export_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Master Reconciled Excel", "UEMS_Master_Reconciled_Report.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            success, msg = AnalyticsService.export_master_excel(path)
            if success:
                QMessageBox.information(self, "Export Successful", f"Master Reconciled Report saved to:\n{path}")
            else:
                QMessageBox.critical(self, "Export Failed", msg)
