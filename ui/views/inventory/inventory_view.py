import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget, QDialog, QFormLayout, QSpinBox,
    QDoubleSpinBox, QMessageBox, QFrame, QScrollArea, QTextEdit,
    QCheckBox, QFileDialog, QGridLayout, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from core.theme_manager import ThemeManager
from core.state_manager import app_state
from core.inventory_service import InventoryService
from core.analytics_service import AnalyticsService
from database.connection import get_session
from database.models.student import Student
from database.models.hr import Employee
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, MetricCard, StatusBadge,
    ModernButton, TableActionButton, TableTextButton, TableDropdownButton, create_table_actions_cell,
    SearchInput, style_modern_table, style_modern_tabs
)

class InventoryLedgerDetailDialog(QDialog):
    """Detailed modal dialog for an unclipped, full view of inventory movement transactions & notes."""
    def __init__(self, parent=None, tx=None):
        super().__init__(parent)
        self.tx = tx
        self.inventory_view_parent = parent
        t = ThemeManager.tokens()
        ref = tx.reference_no if tx and tx.reference_no else "N/A"
        self.setWindowTitle(f"Stock Movement Details — {ref}")
        self.setMinimumWidth(560)
        self.resize(580, 500)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header Badge Card
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg_card']};
                border: 1.5px solid {t['border']};
                border-radius: 8px;
            }}
        """)
        hdr_lay = QVBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(14, 12, 14, 12)
        hdr_lay.setSpacing(4)

        t_type = tx.transaction_type if tx else "MOVEMENT"
        if t_type in ["PURCHASE", "OPENING_STOCK", "RETURN"]:
            type_color = "#059669" # Emerald
            badge_text = f"● {t_type} (Stock In)"
        elif t_type in ["ISSUE", "DAMAGE", "LOSS"]:
            type_color = "#DC2626" # Red
            badge_text = f"● {t_type} (Stock Out)"
        else:
            type_color = "#7C3AED" # Purple
            badge_text = f"● {t_type} (Adjustment)"

        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet(f"color: {type_color}; font-weight: bold; font-size: 14px; background: transparent;")
        hdr_lay.addWidget(lbl_badge)

        it_name = tx.item.name if tx and tx.item else f"Item #{tx.item_id if tx else '?'}"
        it_sku = tx.item.sku if tx and tx.item else "-"
        lbl_item = QLabel(f"{it_name}  |  SKU: {it_sku}")
        lbl_item.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {t['text_primary']}; background: transparent;")
        hdr_lay.addWidget(lbl_item)
        layout.addWidget(hdr_frame)

        # Details Grid Form
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg_card']};
                border: 1px solid {t['border']};
                border-radius: 8px;
            }}
        """)
        form_lay = QGridLayout(form_frame)
        form_lay.setContentsMargins(14, 12, 14, 12)
        form_lay.setSpacing(8)

        def _val_lbl(text, bold=False, color=None):
            lbl = QLabel(str(text))
            style = "font-size: 12px; background: transparent;"
            if bold: style += " font-weight: bold;"
            if color: style += f" color: {color};"
            else: style += f" color: {t['text_primary']};"
            lbl.setStyleSheet(style)
            return lbl

        def _key_lbl(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {t['text_secondary']}; background: transparent;")
            return lbl

        form_lay.addWidget(_key_lbl("Date:"), 0, 0)
        form_lay.addWidget(_val_lbl(tx.transaction_date if tx else "-"), 0, 1)

        form_lay.addWidget(_key_lbl("Reference / Ref #:"), 0, 2)
        form_lay.addWidget(_val_lbl(tx.reference_no if tx else "-", bold=True), 0, 3)

        cat_name = tx.item.category.name if tx and tx.item and tx.item.category else "Uncategorized"
        form_lay.addWidget(_key_lbl("Category:"), 1, 0)
        form_lay.addWidget(_val_lbl(cat_name, bold=True, color="#4F46E5"), 1, 1)

        unit_str = tx.item.unit if tx and tx.item else "units"
        qty_val = tx.quantity if tx else 0.0
        form_lay.addWidget(_key_lbl("Quantity Moved:"), 1, 2)
        form_lay.addWidget(_val_lbl(f"{qty_val:+.1f} {unit_str}", bold=True, color=type_color), 1, 3)

        unit_price = tx.unit_price if tx else 0.0
        form_lay.addWidget(_key_lbl("Unit Price:"), 2, 0)
        form_lay.addWidget(_val_lbl(f"Rs. {unit_price:,.2f}"), 2, 1)

        tot_amt = tx.total_amount if tx else 0.0
        form_lay.addWidget(_key_lbl("Total Value:"), 2, 2)
        form_lay.addWidget(_val_lbl(f"Rs. {tot_amt:,.2f}", bold=True), 2, 3)

        ent_type = tx.entity_type if tx and tx.entity_type else "General"
        form_lay.addWidget(_key_lbl("Target Entity / Dept:"), 3, 0)
        form_lay.addWidget(_val_lbl(ent_type), 3, 1)

        created_ts = tx.created_at if tx and tx.created_at else "-"
        form_lay.addWidget(_key_lbl("Timestamp:"), 3, 2)
        form_lay.addWidget(_val_lbl(created_ts), 3, 3)

        layout.addWidget(form_frame)

        # Full Notes Block
        lbl_notes_title = QLabel("Full Description & Audit Notes:")
        lbl_notes_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {t['text_primary']}; margin-top: 4px;")
        layout.addWidget(lbl_notes_title)

        notes_content = tx.notes if tx and tx.notes else "No specific notes recorded for this transaction."
        txt_notes = QTextEdit()
        txt_notes.setReadOnly(True)
        txt_notes.setPlainText(notes_content)
        txt_notes.setMinimumHeight(100)
        txt_notes.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['input_border']};
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                line-height: 1.4;
            }}
        """)
        layout.addWidget(txt_notes)

        # Bottom Action Buttons
        btn_bar = QHBoxLayout()
        btn_copy = ModernButton("Copy Notes", icon_name="copy", variant="secondary")
        btn_copy.setFixedHeight(32)
        btn_copy.clicked.connect(lambda checked=False: QApplication.clipboard().setText(notes_content))
        btn_bar.addWidget(btn_copy)

        btn_bar.addStretch()
        
        # ==================================================
        # RETURN BUTTON LOGIC (WITH DOUBLE-RETURN PROTECTION)
        # ==================================================
        if t_type == "ISSUE":
            is_returned = "[RETURNED" in notes_content
            
            if is_returned:
                # Agar return ho chuka hai, button lock kar do
                btn_return = ModernButton("✓ Item Already Returned", variant="secondary")
                btn_return.setFixedHeight(32)
                btn_return.setEnabled(False)
                btn_return.setStyleSheet("""
                    QPushButton {
                        background-color: #E2E8F0;
                        color: #64748B;
                        border-radius: 6px;
                        padding: 4px 15px;
                        font-weight: bold;
                        border: 1px solid #CBD5E1;
                    }
                """)
                btn_bar.addWidget(btn_return)
            else:
                # Agar return nahi hua, toh return ka option do
                btn_return = ModernButton("↺ Return Item to Stock", variant="primary")
                btn_return.setFixedHeight(32)
                btn_return.setStyleSheet("""
                    QPushButton {
                        background-color: #059669;
                        color: white;
                        border-radius: 6px;
                        padding: 4px 15px;
                        font-weight: bold;
                        border: none;
                    }
                    QPushButton:hover { background-color: #047857; }
                """)
                btn_return.clicked.connect(self._process_return)
                btn_bar.addWidget(btn_return)
        # ==================================================

        btn_close = ModernButton("Close", variant="secondary")
        btn_close.setFixedHeight(32)
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)
        layout.addLayout(btn_bar)

    def _process_return(self):
        qty_to_return = abs(self.tx.quantity)
        reply = QMessageBox.question(
            self, 'Confirm Return',
            f"Are you sure you want to return {qty_to_return:.1f} unit(s) of '{self.tx.item.name}' back to the store inventory?\n\nThis will increment the available stock and mark this issue as returned.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 1. Add stock back to inventory
            success, msg = InventoryService.record_adjustment(
                item_id=self.tx.item_id, 
                adjustment_type="RETURN", 
                quantity=qty_to_return, 
                reason=f"Returned back from: {self.tx.entity_type} (Ref Issue: {self.tx.reference_no})"
            )
            
            if success:
                # 2. MARK THE ORIGINAL ISSUE AS "RETURNED" IN DATABASE TO PREVENT DUPLICATES
                db = get_session()
                try:
                    from database.models.inventory import StockTransaction
                    original_tx = db.query(StockTransaction).filter_by(id=self.tx.id).first()
                    if original_tx:
                        timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')
                        new_note = f"\n\n[RETURNED on {timestamp}]"
                        original_tx.notes = (original_tx.notes or "") + new_note
                        db.commit()
                except Exception as e:
                    print("Error updating original transaction notes:", e)
                finally:
                    db.close()

                QMessageBox.information(self, "Success", f"Item successfully returned to stock.\n{msg}")
                self.accept()
                if self.inventory_view_parent:
                    self.inventory_view_parent.refresh_all()
            else:
                QMessageBox.critical(self, "Error", f"Failed to return item: {msg}")


class StockAdjustmentDialog(QDialog):
    """Modal dialog to update stock status (Damage, Loss, Adjustment, Return)."""
    def __init__(self, parent=None, item=None, default_type="DAMAGE"):
        super().__init__(parent)
        self.item = item
        self.inventory_view_parent = parent
        t = ThemeManager.tokens()
        it_name = item.name if item else "Item"
        self.setWindowTitle(f"Stock Status & Adjustment — {it_name}")
        self.setMinimumWidth(520)
        self.setModal(True)
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header Frame with Item Info
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t['bg_card']};
                border: 1.5px solid {t['border']};
                border-radius: 8px;
            }}
        """)
        h_lay = QVBoxLayout(hdr_frame)
        h_lay.setContentsMargins(14, 12, 14, 12)
        h_lay.setSpacing(4)

        it_sku = item.sku if item else "-"
        cat_name = item.category.name if item and item.category else "Uncategorized"
        unit = item.unit if item else "pcs"
        curr_stock = float(item.current_stock or 0.0) if item else 0.0

        lbl_title = QLabel(f"<b>{it_name}</b>  <span style='color: #64748B;'>({it_sku})</span>")
        lbl_title.setStyleSheet("font-size: 14px; color: #0F172A; background: transparent;")
        lbl_meta = QLabel(f"Category: <b>{cat_name}</b>  |  Current Available Stock: <b style='color: #2563EB;'>{curr_stock:.1f} {unit}</b>  |  Unit Cost: Rs. {item.unit_cost:,.2f}")
        lbl_meta.setStyleSheet("font-size: 12px; color: #475569; background: transparent;")
        h_lay.addWidget(lbl_title)
        h_lay.addWidget(lbl_meta)
        layout.addWidget(hdr_frame)

        # Form Layout
        form_frame = QFrame()
        form_frame.setStyleSheet(f"QFrame {{ background-color: {t['bg_card']}; border: 1px solid {t['border']}; border-radius: 8px; }}")
        f_lay = QFormLayout(form_frame)
        f_lay.setContentsMargins(14, 14, 14, 14)
        f_lay.setSpacing(10)

        self.cmb_status_type = QComboBox()
        self.cmb_status_type.addItems([
            "DAMAGE (Mark as Damaged / Write-off)",
            "LOSS (Mark as Lost / Missing)",
            "ADJUSTMENT (Audit Reconciliation / Surplus / Deficit)",
            "RETURN (Return to Stock / Vendor)"
        ])
        type_keys = ["DAMAGE", "LOSS", "ADJUSTMENT", "RETURN"]
        if default_type in type_keys:
            self.cmb_status_type.setCurrentIndex(type_keys.index(default_type))
        self.cmb_status_type.setMinimumHeight(32)
        self.cmb_status_type.currentIndexChanged.connect(self._on_type_changed)
        f_lay.addRow(QLabel("<b>Status / Adjustment Type:</b>"), self.cmb_status_type)

        self.spin_qty = QDoubleSpinBox()
        self.spin_qty.setRange(0.1, max(1.0, curr_stock) if default_type in ["DAMAGE", "LOSS"] else 100000.0)
        self.spin_qty.setValue(1.0)
        self.spin_qty.setDecimals(1)
        self.spin_qty.setSuffix(f" {unit}")
        self.spin_qty.setMinimumHeight(32)
        f_lay.addRow(QLabel("<b>Quantity:</b>"), self.spin_qty)

        self.txt_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.txt_date.setMinimumHeight(32)
        f_lay.addRow(QLabel("<b>Date:</b>"), self.txt_date)

        self.txt_reason = QLineEdit()
        self.txt_reason.setPlaceholderText("Detailed reason / audit remarks (e.g. Broken in lab, audit count reconciliation, etc.)...")
        self.txt_reason.setMinimumHeight(32)
        f_lay.addRow(QLabel("<b>Reason / Audit Notes:</b>"), self.txt_reason)

        layout.addWidget(form_frame)

        # Buttons
        btn_lay = QHBoxLayout()
        btn_submit = ModernButton("Confirm Status & Adjust Stock", icon_name="check", variant="primary")
        btn_submit.setFixedHeight(34)
        btn_submit.clicked.connect(self._submit_adjustment)
        btn_cancel = ModernButton("Cancel", icon_name="x", variant="secondary")
        btn_cancel.setFixedHeight(34)
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_submit)
        btn_lay.addWidget(btn_cancel)
        layout.addLayout(btn_lay)

    def _on_type_changed(self):
        txt = self.cmb_status_type.currentText()
        curr_stock = float(self.item.current_stock or 0.0) if self.item else 0.0
        if "DAMAGE" in txt or "LOSS" in txt:
            self.spin_qty.setRange(0.1, max(0.1, curr_stock))
            if curr_stock <= 0:
                self.spin_qty.setValue(0.0)
            elif self.spin_qty.value() > curr_stock:
                self.spin_qty.setValue(curr_stock)
        else:
            self.spin_qty.setRange(0.1, 100000.0)

    def _submit_adjustment(self):
        txt = self.cmb_status_type.currentText()
        if "DAMAGE" in txt:
            adj_type = "DAMAGE"
        elif "LOSS" in txt:
            adj_type = "LOSS"
        elif "RETURN" in txt:
            adj_type = "RETURN"
        else:
            adj_type = "ADJUSTMENT"

        qty = self.spin_qty.value()
        reason = self.txt_reason.text().strip()
        date_str = self.txt_date.text().strip()

        if qty <= 0:
            QMessageBox.warning(self, "Invalid Quantity", "Please specify a quantity greater than zero.")
            return

        if not reason:
            reason = f"Marked as {adj_type} via Store Inventory interface."

        success, msg = InventoryService.record_adjustment(
            item_id=self.item.id,
            adjustment_type=adj_type,
            quantity=qty,
            reason=reason,
            date_str=date_str
        )
        if success:
            QMessageBox.information(
                self,
                "Status Updated",
                f"Successfully marked '{self.item.name}' as {adj_type} ({qty:.1f} {self.item.unit}).\n\n"
                "Current stock updated, transaction logged in Movement Ledger, and automatically synchronized "
                "with the Principal's Master Audit Excel."
            )
            self.accept()
            if self.inventory_view_parent:
                self.inventory_view_parent.refresh_all()
        else:
            QMessageBox.critical(self, "Error", f"Failed to record status update: {msg}")


class InventoryView(QWidget):
    """Enterprise Inventory and Store Management Interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_txs = []
        self.init_ui()
        self.refresh_all()
        app_state.subscribe(self.refresh_all)

    def init_ui(self):
        t = ThemeManager.tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(14)

        header = PageHeader(
            title="Inventory & Store Management",
            subtitle="Manage multi-category stock catalog, purchase orders, distributions, and audit trails",
            icon_name="package",
        )
        btn_export_master = ModernButton("Export Master Audit", icon_name="download", variant="secondary")
        btn_export_master.clicked.connect(self._export_master_excel)
        header.add_action_widget(btn_export_master)

        btn_refresh = ModernButton("Refresh", icon_name="refresh-cw", variant="secondary")
        btn_refresh.clicked.connect(self.refresh_all)
        header.add_action_widget(btn_refresh)

        main_layout.addWidget(header)

        # Tab Widget
        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)

        # 1. Overview & Alerts Tab
        self.tab_overview = QWidget()
        self._init_overview_tab()
        self.tabs.addTab(self.tab_overview, "Stock Overview && Alerts")
        self.tabs.setTabIcon(0, get_icon("bar-chart-2", color="#475569"))

        # 2. Items Catalog Tab
        self.tab_catalog = QWidget()
        self._init_catalog_tab()
        self.tabs.addTab(self.tab_catalog, "Item Catalog")
        self.tabs.setTabIcon(1, get_icon("package", color="#475569"))

        # 3. Stock In / Purchases Tab
        self.tab_purchases = QWidget()
        self._init_purchases_tab()
        self.tabs.addTab(self.tab_purchases, "Stock In / Purchases")
        self.tabs.setTabIcon(2, get_icon("download", color="#475569"))

        # 4. Stock Out / Issues Tab
        self.tab_issues = QWidget()
        self._init_issues_tab()
        self.tabs.addTab(self.tab_issues, "Stock Out / Issues")
        self.tabs.setTabIcon(3, get_icon("upload", color="#475569"))

        # 5. Ledger Tab
        self.tab_ledger = QWidget()
        self._init_ledger_tab()
        self.tabs.addTab(self.tab_ledger, "Movement Ledger")
        self.tabs.setTabIcon(4, get_icon("file-text", color="#475569"))

        # 6. Suppliers Tab
        self.tab_suppliers = QWidget()
        self._init_suppliers_tab()
        self.tabs.addTab(self.tab_suppliers, "Suppliers")
        self.tabs.setTabIcon(5, get_icon("truck", color="#475569"))

        main_layout.addWidget(self.tabs)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 1: OVERVIEW & ALERTS
    # ──────────────────────────────────────────────────────────────────────────
    def _init_overview_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_overview)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Stat KPI Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self.kpi_items = self._create_kpi_card("Total Items", "0", "#3B82F6")
        self.kpi_units = self._create_kpi_card("Total Units", "0", "#10B981")
        self.kpi_val = self._create_kpi_card("Total Asset Value", "Rs. 0.00", "#6366F1")
        self.kpi_alerts = self._create_kpi_card("Low Stock Alerts", "0", "#EF4444")

        cards_row.addWidget(self.kpi_items)
        cards_row.addWidget(self.kpi_units)
        cards_row.addWidget(self.kpi_val)
        cards_row.addWidget(self.kpi_alerts)
        layout.addLayout(cards_row)

        # Section Header for Low Stock
        sec_hdr = QLabel("Low Stock & Reorder Alerts")
        sec_hdr.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        sec_hdr.setStyleSheet(f"color: {t['text_primary']}; margin-top: 6px;")
        layout.addWidget(sec_hdr)

        self.tbl_low_stock = QTableWidget()
        self.tbl_low_stock.setColumnCount(7)
        self.tbl_low_stock.setHorizontalHeaderLabels([
            "SKU", "Item Name", "Category", "Current Stock", "Min Alert", "Unit Cost", "Action"
        ])
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_low_stock.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tbl_low_stock.setColumnWidth(6, 110)
        self.tbl_low_stock.verticalHeader().setDefaultSectionSize(48)
        self.tbl_low_stock.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_low_stock.setAlternatingRowColors(True)
        style_modern_table(self.tbl_low_stock)
        layout.addWidget(self.tbl_low_stock)

    def _create_kpi_card(self, title, default_val, accent_color, icon_str=None):
        icon_map = {
            "Total Items": "package",
            "Total Units": "hash",
            "Total Asset Value": "wallet",
            "Low Stock Alerts": "alert-triangle",
        }
        icon_name = icon_map.get(title, "info")
        card = MetricCard(title=title, value=default_val, icon_name=icon_name, accent_color=accent_color)
        card.lbl_val.setObjectName("val_lbl")
        return card

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 2: CATALOG
    # ──────────────────────────────────────────────────────────────────────────
    def _init_catalog_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_catalog)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Filter & Action Row
        f_row = QHBoxLayout()
        f_row.setSpacing(8)

        self.txt_catalog_search = SearchInput(placeholder="Search by Item Name, SKU, Barcode, or Location...")
        self.txt_catalog_search.textChanged.connect(self._refresh_catalog)
        f_row.addWidget(self.txt_catalog_search, 3)

        self.cmb_catalog_cat = QComboBox()
        self.cmb_catalog_cat.setMinimumHeight(32)
        self.cmb_catalog_cat.currentIndexChanged.connect(self._refresh_catalog)
        f_row.addWidget(self.cmb_catalog_cat, 2)

        btn_add_item = ModernButton("Add New Item", icon_name="plus", variant="primary")
        btn_add_item.clicked.connect(self._on_add_item)
        f_row.addWidget(btn_add_item)

        btn_add_cat = ModernButton("Categories", icon_name="folder", variant="secondary")
        btn_add_cat.clicked.connect(self._on_manage_categories)
        f_row.addWidget(btn_add_cat)

        btn_mark_status = ModernButton("Mark Status / Adjust", icon_name="shield-alert", variant="secondary")
        btn_mark_status.clicked.connect(self._on_toolbar_mark_status)
        f_row.addWidget(btn_mark_status)

        layout.addLayout(f_row)

        # Catalog Table
        self.tbl_catalog = QTableWidget()
        self.tbl_catalog.setColumnCount(9)
        self.tbl_catalog.setHorizontalHeaderLabels([
            "ID", "SKU", "Item Name", "Category", "Unit", "Unit Cost", "Current Stock", "Min Alert", "Actions"
        ])
        self.tbl_catalog.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_catalog.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tbl_catalog.setColumnWidth(0, 45)
        self.tbl_catalog.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.tbl_catalog.setColumnWidth(8, 155)
        self.tbl_catalog.verticalHeader().setDefaultSectionSize(48)
        self.tbl_catalog.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_catalog.setAlternatingRowColors(True)
        self.tbl_catalog.cellDoubleClicked.connect(self._on_catalog_cell_double_clicked)
        style_modern_table(self.tbl_catalog)
        layout.addWidget(self.tbl_catalog)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 3: PURCHASES / STOCK IN
    # ──────────────────────────────────────────────────────────────────────────
    def _init_purchases_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_purchases)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Purchase Form Frame
        box = QFrame()
        box.setStyleSheet(f"QFrame {{ background-color: {t['bg_card']}; border: 1px solid {t['border']}; border-radius: 8px; }}")
        b_lay = QVBoxLayout(box)
        b_lay.setContentsMargins(14, 12, 14, 12)
        b_lay.setSpacing(10)

        # Top row: Supplier & Date
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        row1.addWidget(QLabel("Supplier:"))
        self.cmb_purchase_supplier = QComboBox()
        self.cmb_purchase_supplier.setMinimumHeight(32)
        row1.addWidget(self.cmb_purchase_supplier, 2)

        row1.addWidget(QLabel("Date:"))
        self.txt_purchase_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.txt_purchase_date.setMinimumHeight(32)
        row1.addWidget(self.txt_purchase_date, 1)

        self.chk_auto_expense = QCheckBox("Auto-Log in Institutional Expenses")
        self.chk_auto_expense.setChecked(True)
        row1.addWidget(self.chk_auto_expense, 2)

        b_lay.addLayout(row1)

        # Line items table
        b_lay.addWidget(QLabel("**Purchase Items:**"))
        self.tbl_purchase_items = QTableWidget()
        self.tbl_purchase_items.setColumnCount(5)
        self.tbl_purchase_items.setHorizontalHeaderLabels(["Item", "Quantity", "Unit Cost (Rs.)", "Subtotal", "Remove"])
        self.tbl_purchase_items.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_purchase_items.verticalHeader().setDefaultSectionSize(28)
        self.tbl_purchase_items.setMaximumHeight(200)
        style_modern_table(self.tbl_purchase_items)
        b_lay.addWidget(self.tbl_purchase_items)

        # Add line item button row
        btn_row = QHBoxLayout()
        btn_add_line = ModernButton("Add Item Row", icon_name="plus", variant="secondary")
        btn_add_line.clicked.connect(self._add_purchase_row)
        btn_row.addWidget(btn_add_line)
        btn_row.addStretch()

        self.lbl_purchase_total = QLabel("Total: Rs. 0.00")
        self.lbl_purchase_total.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_purchase_total.setStyleSheet(f"color: {t['accent']};")
        btn_row.addWidget(self.lbl_purchase_total)
        b_lay.addLayout(btn_row)

        # Notes & Submit
        row3 = QHBoxLayout()
        self.txt_purchase_notes = QLineEdit()
        self.txt_purchase_notes.setPlaceholderText("Optional purchase order notes, invoice #, or remarks...")
        self.txt_purchase_notes.setMinimumHeight(32)
        row3.addWidget(self.txt_purchase_notes, 3)

        btn_submit_purchase = ModernButton("Complete Stock In / Save Purchase", icon_name="save", variant="primary")
        btn_submit_purchase.clicked.connect(self._on_submit_purchase)
        row3.addWidget(btn_submit_purchase, 1)
        b_lay.addLayout(row3)

        layout.addWidget(box)
        layout.addStretch()

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 4: ISSUES / STOCK OUT
    # ──────────────────────────────────────────────────────────────────────────
    def _init_issues_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_issues)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        box = QFrame()
        box.setStyleSheet(f"QFrame {{ background-color: {t['bg_card']}; border: 1px solid {t['border']}; border-radius: 8px; }}")
        b_lay = QVBoxLayout(box)
        b_lay.setContentsMargins(14, 12, 14, 12)
        b_lay.setSpacing(10)

        r1 = QHBoxLayout()
        r1.setSpacing(10)

        r1.addWidget(QLabel("Issue To:"))
        self.cmb_issue_type = QComboBox()
        self.cmb_issue_type.addItems(["Student", "Employee", "Department"])
        self.cmb_issue_type.setMinimumHeight(32)
        self.cmb_issue_type.currentIndexChanged.connect(self._on_issue_type_changed)
        r1.addWidget(self.cmb_issue_type, 1)

        self.cmb_issue_recipient = QComboBox()
        self.cmb_issue_recipient.setMinimumHeight(32)
        r1.addWidget(self.cmb_issue_recipient, 2)

        r1.addWidget(QLabel("Date:"))
        self.txt_issue_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.txt_issue_date.setMinimumHeight(32)
        r1.addWidget(self.txt_issue_date, 1)

        b_lay.addLayout(r1)

        b_lay.addWidget(QLabel("**Items to Issue:**"))
        self.tbl_issue_items = QTableWidget()
        self.tbl_issue_items.setColumnCount(4)
        self.tbl_issue_items.setHorizontalHeaderLabels(["Item", "Current Stock", "Issue Quantity", "Remove"])
        self.tbl_issue_items.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_issue_items.verticalHeader().setDefaultSectionSize(28)
        self.tbl_issue_items.setMaximumHeight(200)
        style_modern_table(self.tbl_issue_items)
        b_lay.addWidget(self.tbl_issue_items)

        btn_row = QHBoxLayout()
        btn_add_issue_line = ModernButton("Add Item Row", icon_name="plus", variant="secondary")
        btn_add_issue_line.clicked.connect(self._add_issue_row)
        btn_row.addWidget(btn_add_issue_line)
        btn_row.addStretch()
        b_lay.addLayout(btn_row)

        r3 = QHBoxLayout()
        self.txt_issue_purpose = QLineEdit()
        self.txt_issue_purpose.setPlaceholderText("Purpose / Remarks (e.g. Lab Kit, Uniform issuance, Office Stationery)...")
        self.txt_issue_purpose.setMinimumHeight(32)
        r3.addWidget(self.txt_issue_purpose, 3)

        btn_submit_issue = ModernButton("Issue Items & Decrement Stock", icon_name="upload", variant="primary")
        btn_submit_issue.clicked.connect(self._on_submit_issue)
        r3.addWidget(btn_submit_issue, 1)
        b_lay.addLayout(r3)

        layout.addWidget(box)
        layout.addStretch()

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 5: LEDGER / AUDIT HISTORY
    # ──────────────────────────────────────────────────────────────────────────
    def _init_ledger_tab(self):
        layout = QVBoxLayout(self.tab_ledger)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        f_row = QHBoxLayout()
        
        self.txt_ledger_search = SearchInput(placeholder="Search by Ref #, Date or Notes...")
        self.txt_ledger_search.textChanged.connect(self._refresh_ledger)
        f_row.addWidget(self.txt_ledger_search, 2)
        
        self.cmb_ledger_type = QComboBox()
        self.cmb_ledger_type.addItems(["All", "PURCHASE", "ISSUE", "RETURN", "DAMAGE", "LOSS", "ADJUSTMENT", "OPENING_STOCK"])
        self.cmb_ledger_type.setMinimumHeight(32)
        self.cmb_ledger_type.currentIndexChanged.connect(self._refresh_ledger)
        f_row.addWidget(QLabel("Filter Type:"))
        f_row.addWidget(self.cmb_ledger_type, 1)
        
        layout.addLayout(f_row)

        self.tbl_ledger = QTableWidget()
        self.tbl_ledger.setColumnCount(8)
        self.tbl_ledger.setHorizontalHeaderLabels([
            "Date", "Ref #", "Item", "Type", "Qty", "Unit Price", "Total (Rs.)", "Notes (Click for Details)"
        ])
        self.tbl_ledger.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_ledger.verticalHeader().setDefaultSectionSize(36)
        self.tbl_ledger.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_ledger.setAlternatingRowColors(True)
        self.tbl_ledger.cellClicked.connect(self._on_ledger_cell_clicked)
        self.tbl_ledger.itemDoubleClicked.connect(self._on_ledger_row_double_clicked)
        style_modern_table(self.tbl_ledger)
        layout.addWidget(self.tbl_ledger)

    # ──────────────────────────────────────────────────────────────────────────
    # TAB 6: SUPPLIERS
    # ──────────────────────────────────────────────────────────────────────────
    def _init_suppliers_tab(self):
        t = ThemeManager.tokens()
        layout = QVBoxLayout(self.tab_suppliers)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        f_row = QHBoxLayout()
        btn_add_supplier = ModernButton("Add Supplier", icon_name="plus", variant="primary")
        btn_add_supplier.clicked.connect(self._on_add_supplier)
        f_row.addWidget(btn_add_supplier)
        f_row.addStretch()
        layout.addLayout(f_row)

        self.tbl_suppliers = QTableWidget()
        self.tbl_suppliers.setColumnCount(6)
        self.tbl_suppliers.setHorizontalHeaderLabels([
            "ID", "Supplier Name", "Contact Person", "Phone", "Email", "Status"
        ])
        self.tbl_suppliers.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_suppliers.verticalHeader().setDefaultSectionSize(36)
        self.tbl_suppliers.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_suppliers.setAlternatingRowColors(True)
        style_modern_table(self.tbl_suppliers)
        layout.addWidget(self.tbl_suppliers)

    # ──────────────────────────────────────────────────────────────────────────
    # REFRESH LOGIC
    # ──────────────────────────────────────────────────────────────────────────
    def refresh_all(self):
        self._refresh_kpis()
        self._refresh_low_stock()
        self._refresh_catalog()
        self._refresh_suppliers()
        self._refresh_ledger()
        self._populate_dropdowns()

    def _refresh_kpis(self):
        stats = InventoryService.get_inventory_valuation()
        self.kpi_items.findChild(QLabel, "val_lbl").setText(str(stats.get("total_items", 0)))
        self.kpi_units.findChild(QLabel, "val_lbl").setText(f"{stats.get('total_units', 0):,.1f}")
        self.kpi_val.findChild(QLabel, "val_lbl").setText(f"Rs. {stats.get('total_valuation', 0):,.2f}")
        self.kpi_alerts.findChild(QLabel, "val_lbl").setText(str(stats.get("low_stock_count", 0)))

    def _refresh_low_stock(self):
        for child in self.tbl_low_stock.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_low_stock.clearContents()

        low_items = InventoryService.get_low_stock_items()
        self.tbl_low_stock.setRowCount(len(low_items))
        for r, it in enumerate(low_items):
            self.tbl_low_stock.setItem(r, 0, QTableWidgetItem(it.sku))
            self.tbl_low_stock.setItem(r, 1, QTableWidgetItem(it.name))
            cat_name = it.category.name if it.category else "Uncategorized"
            self.tbl_low_stock.setItem(r, 2, QTableWidgetItem(cat_name))
            
            stock_item = QTableWidgetItem(f"{it.current_stock:.1f} {it.unit}")
            stock_item.setForeground(QColor("#EF4444"))
            self.tbl_low_stock.setItem(r, 3, stock_item)
            
            self.tbl_low_stock.setItem(r, 4, QTableWidgetItem(f"{it.min_stock_alert:.1f}"))
            self.tbl_low_stock.setItem(r, 5, QTableWidgetItem(f"Rs. {it.unit_cost:.2f}"))

            btn_restock = TableTextButton("Restock", icon_name="plus", variant="primary")
            btn_restock.clicked.connect(lambda _, item=it: self._jump_to_purchase(item))
            self.tbl_low_stock.setCellWidget(r, 6, create_table_actions_cell([btn_restock]))
            self.tbl_low_stock.setRowHeight(r, 48)

    def _jump_to_purchase(self, item):
        self.tabs.setCurrentIndex(2)  # Go to Stock In tab
        self._add_purchase_row(item.id)

    def _refresh_catalog(self):
        for child in self.tbl_catalog.viewport().findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()
        self.tbl_catalog.clearContents()

        search = self.txt_catalog_search.text()
        cat_id = self.cmb_catalog_cat.currentData()
        items = InventoryService.get_items(category_id=cat_id, search=search)
        self.tbl_catalog.setRowCount(len(items))
        for r, it in enumerate(items):
            self.tbl_catalog.setItem(r, 0, QTableWidgetItem(str(it.id)))
            self.tbl_catalog.setItem(r, 1, QTableWidgetItem(it.sku))
            self.tbl_catalog.setItem(r, 2, QTableWidgetItem(it.name))
            cat_name = it.category.name if it.category else "—"
            self.tbl_catalog.setItem(r, 3, QTableWidgetItem(cat_name))
            self.tbl_catalog.setItem(r, 4, QTableWidgetItem(it.unit))
            self.tbl_catalog.setItem(r, 5, QTableWidgetItem(f"Rs. {it.unit_cost:.2f}"))
            
            st_item = QTableWidgetItem(f"{it.current_stock:.1f}")
            if it.current_stock <= it.min_stock_alert:
                st_item.setForeground(QColor("#EF4444"))
            self.tbl_catalog.setItem(r, 6, st_item)

            btn_actions = TableDropdownButton("Status / Adjust", icon_name="sliders", variant="secondary", height=28)
            btn_actions.add_menu_action("Mark as Damaged...", lambda checked=False, item_obj=it: self._open_stock_adjustment(item_obj, "DAMAGE"), icon_name="alert-triangle", icon_color="#DC2626")
            btn_actions.add_menu_action("Mark as Lost...", lambda checked=False, item_obj=it: self._open_stock_adjustment(item_obj, "LOSS"), icon_name="shield-alert", icon_color="#DC2626")
            btn_actions.add_menu_action("Audit Stock Adjustment...", lambda checked=False, item_obj=it: self._open_stock_adjustment(item_obj, "ADJUSTMENT"), icon_name="refresh-cw", icon_color="#7C3AED")
            btn_actions.add_menu_action("Return to Stock / Vendor...", lambda checked=False, item_obj=it: self._open_stock_adjustment(item_obj, "RETURN"), icon_name="arrow-down-left", icon_color="#059669")
            btn_actions.add_menu_action("Edit Item Details...", lambda checked=False, item_obj=it: self._on_edit_item(item_obj), icon_name="pencil", icon_color="#2563EB")
            self.tbl_catalog.setCellWidget(r, 8, create_table_actions_cell([btn_actions]))
            self.tbl_catalog.setRowHeight(r, 48)

    def _open_stock_adjustment(self, item, default_type="DAMAGE"):
        dlg = StockAdjustmentDialog(parent=self, item=item, default_type=default_type)
        dlg.exec()

    def _on_catalog_cell_double_clicked(self, row, col):
        if row >= 0:
            item_id_w = self.tbl_catalog.item(row, 0)
            if item_id_w:
                try:
                    item_id = int(item_id_w.text())
                    item_obj = InventoryService.get_item(item_id)
                    if item_obj:
                        self._open_stock_adjustment(item_obj, "DAMAGE")
                except Exception as e:
                    print(f"Error opening item adjustment: {e}")

    def _on_toolbar_mark_status(self):
        row = self.tbl_catalog.currentRow()
        if row >= 0:
            item_id_w = self.tbl_catalog.item(row, 0)
            if item_id_w:
                try:
                    item_obj = InventoryService.get_item(int(item_id_w.text()))
                    if item_obj:
                        self._open_stock_adjustment(item_obj, "DAMAGE")
                        return
                except Exception:
                    pass
        items = InventoryService.get_items()
        if items:
            self._open_stock_adjustment(items[0], "DAMAGE")
        else:
            QMessageBox.information(self, "No Items", "No inventory items exist to update.")

    def _refresh_ledger(self):
        type_filter = self.cmb_ledger_type.currentText()
        search_query = self.txt_ledger_search.text().lower().strip()
        txs = InventoryService.get_transactions(type_filter=type_filter)
        
        # Apply local search filtering for Ref# or Notes
        filtered_txs = []
        for tx in txs:
            if not search_query:
                filtered_txs.append(tx)
                continue
            
            ref = str(tx.reference_no).lower() if tx.reference_no else ""
            notes = str(tx.notes).lower() if tx.notes else ""
            date_str = str(tx.transaction_date).lower() if tx.transaction_date else ""
            
            if search_query in ref or search_query in notes or search_query in date_str:
                filtered_txs.append(tx)
                
        self._current_txs = filtered_txs
        self.tbl_ledger.setRowCount(len(filtered_txs))
        for r, tx in enumerate(filtered_txs):
            self.tbl_ledger.setItem(r, 0, QTableWidgetItem(tx.transaction_date or ""))
            self.tbl_ledger.setItem(r, 1, QTableWidgetItem(tx.reference_no or ""))
            it_name = tx.item.name if tx.item else f"Item #{tx.item_id}"
            self.tbl_ledger.setItem(r, 2, QTableWidgetItem(it_name))
            
            type_item = QTableWidgetItem(tx.transaction_type)
            if tx.transaction_type in ["PURCHASE", "RETURN", "OPENING_STOCK"]:
                type_item.setForeground(QColor("#10B981"))
            elif tx.transaction_type in ["ISSUE", "DAMAGE", "LOSS"]:
                type_item.setForeground(QColor("#EF4444"))
            else:
                type_item.setForeground(QColor("#8B5CF6"))
            self.tbl_ledger.setItem(r, 3, type_item)

            self.tbl_ledger.setItem(r, 4, QTableWidgetItem(f"{tx.quantity:+.1f}"))
            self.tbl_ledger.setItem(r, 5, QTableWidgetItem(f"Rs. {tx.unit_price:.2f}"))
            self.tbl_ledger.setItem(r, 6, QTableWidgetItem(f"Rs. {tx.total_amount:.2f}"))

            notes_str = tx.notes or "—"
            notes_item = QTableWidgetItem(notes_str)
            notes_item.setForeground(QColor("#2563EB"))
            notes_item.setToolTip("Click to view full transaction notes and complete audit details")
            self.tbl_ledger.setItem(r, 7, notes_item)

    def _on_ledger_cell_clicked(self, row, col):
        if col == 7 and 0 <= row < len(self._current_txs):
            self._show_ledger_detail(row)

    def _on_ledger_row_double_clicked(self, item):
        row = item.row()
        if 0 <= row < len(self._current_txs):
            self._show_ledger_detail(row)

    def _show_ledger_detail(self, row):
        if 0 <= row < len(self._current_txs):
            tx = self._current_txs[row]
            dlg = InventoryLedgerDetailDialog(parent=self, tx=tx)
            dlg.exec()

    def _export_master_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Reconciled Master Audit Excel (For Institute Owner)",
            "UEMS_Master_Reconciliation_Audit.xlsx",
            "Excel Files (*.xlsx)"
        )
        if path:
            success, msg = AnalyticsService.export_master_excel(path)
            if success:
                QMessageBox.information(
                    self,
                    "Master Audit Exported",
                    f"Authoritative Master Audit Workbook saved successfully:\n\n{path}\n\n"
                    "Includes 18 synchronized sheets covering Institution Summary, Fee Revenues, Expenses, Payroll, "
                    "Complete Store Inventory Catalog, Stock Movement Ledger, and Purchase Order Audits."
                )
            else:
                QMessageBox.critical(self, "Export Failed", f"Could not generate workbook: {msg}")

    def _refresh_suppliers(self):
        sups = InventoryService.get_suppliers()
        self.tbl_suppliers.setRowCount(len(sups))
        for r, s in enumerate(sups):
            self.tbl_suppliers.setItem(r, 0, QTableWidgetItem(str(s.id)))
            self.tbl_suppliers.setItem(r, 1, QTableWidgetItem(s.name))
            self.tbl_suppliers.setItem(r, 2, QTableWidgetItem(s.contact_person or "—"))
            self.tbl_suppliers.setItem(r, 3, QTableWidgetItem(s.phone or "—"))
            self.tbl_suppliers.setItem(r, 4, QTableWidgetItem(s.email or "—"))
            self.tbl_suppliers.setItem(r, 5, QTableWidgetItem(s.status))

    def _populate_dropdowns(self):
        # Populate Category filters
        cats = InventoryService.get_categories()
        cur_cat = self.cmb_catalog_cat.currentData()
        self.cmb_catalog_cat.blockSignals(True)
        self.cmb_catalog_cat.clear()
        self.cmb_catalog_cat.addItem("All Categories", "All")
        for c in cats:
            self.cmb_catalog_cat.addItem(c.name, c.id)
        idx = self.cmb_catalog_cat.findData(cur_cat)
        if idx >= 0:
            self.cmb_catalog_cat.setCurrentIndex(idx)
        self.cmb_catalog_cat.blockSignals(True)
        self.cmb_catalog_cat.blockSignals(False)

        # Populate Suppliers
        sups = InventoryService.get_suppliers()
        self.cmb_purchase_supplier.clear()
        for s in sups:
            self.cmb_purchase_supplier.addItem(s.name, s.id)

        # Populate Recipients
        self._on_issue_type_changed()

    def _on_issue_type_changed(self):
        itype = self.cmb_issue_type.currentText()
        self.cmb_issue_recipient.clear()
        db = get_session()
        try:
            if itype == "Student":
                students = db.query(Student).filter_by(status="Active").order_by(Student.first_name.asc()).all()
                for s in students:
                    s_name = f"{s.first_name} {s.last_name or ''}".strip()
                    id_tag = s.student_id or s.admission_number or str(s.id)
                    self.cmb_issue_recipient.addItem(f"{s_name} ({id_tag})", s.id)
            elif itype == "Employee":
                employees = db.query(Employee).filter_by(status="Active").order_by(Employee.first_name.asc()).all()
                if not employees:
                    employees = db.query(Employee).order_by(Employee.first_name.asc()).all()
                for e in employees:
                    e_name = f"{e.first_name} {e.last_name or ''}".strip()
                    desig = e.designation or e.emp_type or "Staff"
                    id_tag = e.emp_id or str(e.id)
                    self.cmb_issue_recipient.addItem(f"{e_name} ({desig} - {id_tag})", e.id)
            else:
                for dept in ["Science Lab", "Computer Lab", "Library", "Sports Department", "Admin Office", "Maintenance"]:
                    self.cmb_issue_recipient.addItem(dept, dept)
        except Exception as err:
            print(f"Error loading issue recipients: {err}")
        finally:
            db.close()

    # ──────────────────────────────────────────────────────────────────────────
    # PURCHASE & ISSUE ROW MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    def _add_purchase_row(self, preselect_item_id=None):
        r = self.tbl_purchase_items.rowCount()
        self.tbl_purchase_items.insertRow(r)

        items = InventoryService.get_items()
        cmb = QComboBox()
        cmb.setMinimumHeight(24)
        for it in items:
            cmb.addItem(f"{it.name} ({it.sku})", it.id)
        if preselect_item_id:
            idx = cmb.findData(preselect_item_id)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
        cmb.currentIndexChanged.connect(self._recalc_purchase_total)
        self.tbl_purchase_items.setCellWidget(r, 0, cmb)

        spin_qty = QDoubleSpinBox()
        spin_qty.setRange(1.0, 100000.0)
        spin_qty.setValue(1.0)
        spin_qty.setMinimumHeight(24)
        spin_qty.valueChanged.connect(self._recalc_purchase_total)
        self.tbl_purchase_items.setCellWidget(r, 1, spin_qty)

        spin_cost = QDoubleSpinBox()
        spin_cost.setRange(0.0, 1000000.0)
        spin_cost.setValue(0.0)
        spin_cost.setMinimumHeight(24)
        # Prefill cost if item selected
        if items and cmb.currentIndex() >= 0:
            it_obj = InventoryService.get_item(cmb.currentData())
            if it_obj:
                spin_cost.setValue(it_obj.unit_cost)
        spin_cost.valueChanged.connect(self._recalc_purchase_total)
        self.tbl_purchase_items.setCellWidget(r, 2, spin_cost)

        lbl_sub = QLabel("Rs. 0.00")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tbl_purchase_items.setCellWidget(r, 3, lbl_sub)

        btn_del = TableActionButton("trash-2", variant="delete", tooltip="Remove Row", size=28)
        btn_del.clicked.connect(lambda _, row=r: self._remove_purchase_row(row))
        self.tbl_purchase_items.setCellWidget(r, 4, create_table_actions_cell([btn_del]))
        self.tbl_purchase_items.setRowHeight(r, 44)

        self._recalc_purchase_total()

    def _remove_purchase_row(self, row):
        self.tbl_purchase_items.removeRow(row)
        self._recalc_purchase_total()

    def _recalc_purchase_total(self):
        total = 0.0
        for r in range(self.tbl_purchase_items.rowCount()):
            qty_widget = self.tbl_purchase_items.cellWidget(r, 1)
            cost_widget = self.tbl_purchase_items.cellWidget(r, 2)
            sub_widget = self.tbl_purchase_items.cellWidget(r, 3)
            if qty_widget and cost_widget:
                qty = qty_widget.value()
                cost = cost_widget.value()
                sub = qty * cost
                total += sub
                if sub_widget:
                    sub_widget.setText(f"Rs. {sub:,.2f}")
        self.lbl_purchase_total.setText(f"Total: Rs. {total:,.2f}")

    def _on_submit_purchase(self):
        sup_id = self.cmb_purchase_supplier.currentData()
        date_str = self.txt_purchase_date.text()
        notes = self.txt_purchase_notes.text()
        auto_exp = self.chk_auto_expense.isChecked()

        items_list = []
        for r in range(self.tbl_purchase_items.rowCount()):
            cmb = self.tbl_purchase_items.cellWidget(r, 0)
            qty_w = self.tbl_purchase_items.cellWidget(r, 1)
            cost_w = self.tbl_purchase_items.cellWidget(r, 2)
            if cmb and qty_w and cost_w:
                items_list.append({
                    "item_id": cmb.currentData(),
                    "quantity": qty_w.value(),
                    "unit_cost": cost_w.value()
                })

        if not items_list:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item row.")
            return

        success, msg = InventoryService.record_purchase(
            supplier_id=sup_id,
            invoice_date=date_str,
            items_list=items_list,
            notes=notes,
            auto_log_expense=auto_exp
        )
        if success:
            QMessageBox.information(self, "Stock In Success", msg)
            self.tbl_purchase_items.setRowCount(0)
            self.txt_purchase_notes.clear()
            self._recalc_purchase_total()
            self.refresh_all()
        else:
            QMessageBox.critical(self, "Error", msg)

    def _add_issue_row(self):
        r = self.tbl_issue_items.rowCount()
        self.tbl_issue_items.insertRow(r)

        items = InventoryService.get_items()
        cmb = QComboBox()
        cmb.setMinimumHeight(24)
        for it in items:
            cmb.addItem(f"{it.name} (Stock: {it.current_stock:.0f})", it.id)
        self.tbl_issue_items.setCellWidget(r, 0, cmb)

        lbl_stock = QLabel("0.0")
        lbl_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if items:
            lbl_stock.setText(f"{items[0].current_stock:.1f}")
        self.tbl_issue_items.setCellWidget(r, 1, lbl_stock)

        def update_stock_lbl(idx):
            it_id = cmb.itemData(idx)
            it_obj = InventoryService.get_item(it_id)
            if it_obj:
                lbl_stock.setText(f"{it_obj.current_stock:.1f}")
        cmb.currentIndexChanged.connect(update_stock_lbl)

        spin_qty = QDoubleSpinBox()
        spin_qty.setRange(1.0, 10000.0)
        spin_qty.setValue(1.0)
        spin_qty.setMinimumHeight(24)
        self.tbl_issue_items.setCellWidget(r, 2, spin_qty)

        btn_del = TableActionButton("trash-2", variant="delete", tooltip="Remove Row", size=28)
        btn_del.clicked.connect(lambda _, row=r: self.tbl_issue_items.removeRow(row))
        self.tbl_issue_items.setCellWidget(r, 3, create_table_actions_cell([btn_del]))
        self.tbl_issue_items.setRowHeight(r, 44)

    def _on_submit_issue(self):
        itype = self.cmb_issue_type.currentText()
        recip_id = self.cmb_issue_recipient.currentData()
        recip_name = self.cmb_issue_recipient.currentText()
        date_str = self.txt_issue_date.text()
        purpose = self.txt_issue_purpose.text()

        items_list = []
        for r in range(self.tbl_issue_items.rowCount()):
            cmb = self.tbl_issue_items.cellWidget(r, 0)
            qty_w = self.tbl_issue_items.cellWidget(r, 2)
            if cmb and qty_w:
                items_list.append({
                    "item_id": cmb.currentData(),
                    "quantity": qty_w.value(),
                    "notes": purpose
                })

        if not items_list:
            QMessageBox.warning(self, "Validation", "Please add at least one item row.")
            return

        success, msg = InventoryService.record_issue(
            issued_to_type=itype,
            issued_to_id=recip_id if isinstance(recip_id, int) else None,
            issued_to_name=recip_name,
            issue_date=date_str,
            items_list=items_list,
            purpose=purpose
        )
        if success:
            QMessageBox.information(self, "Issuance Success", msg)
            self.tbl_issue_items.setRowCount(0)
            self.txt_issue_purpose.clear()
            self.refresh_all()
        else:
            QMessageBox.critical(self, "Issuance Error", msg)

    # ──────────────────────────────────────────────────────────────────────────
    # DIALOGS (ITEM, CATEGORY, SUPPLIER)
    # ──────────────────────────────────────────────────────────────────────────
    def _on_add_item(self):
        self._show_item_dialog()

    def _on_edit_item(self, item):
        self._show_item_dialog(item)

    def _show_item_dialog(self, item=None):
        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Inventory Item" if not item else f"Edit Item: {item.name}")
        dlg.setMinimumWidth(420)
        dlg.setStyleSheet(f"QDialog {{ background-color: {t['dialog_bg']}; color: {t['text_primary']}; }}")

        form = QFormLayout(dlg)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(10)

        txt_name = QLineEdit(item.name if item else "")
        txt_name.setMinimumHeight(32)
        form.addRow("Item Name *:", txt_name)

        txt_sku = QLineEdit(item.sku if item else "")
        txt_sku.setPlaceholderText("Auto-generated if empty")
        txt_sku.setMinimumHeight(32)
        form.addRow("SKU / Item Code:", txt_sku)

        txt_barcode = QLineEdit(item.barcode or "" if item else "")
        txt_barcode.setMinimumHeight(32)
        form.addRow("Barcode:", txt_barcode)

        cmb_cat = QComboBox()
        cmb_cat.setMinimumHeight(32)
        cats = InventoryService.get_categories()
        for c in cats:
            cmb_cat.addItem(c.name, c.id)
        if item and item.category_id:
            idx = cmb_cat.findData(item.category_id)
            if idx >= 0:
                cmb_cat.setCurrentIndex(idx)
        form.addRow("Category:", cmb_cat)

        cmb_unit = QComboBox()
        cmb_unit.setMinimumHeight(32)
        cmb_unit.addItems(["pcs", "box", "packet", "kg", "meter", "set", "liter"])
        if item:
            cmb_unit.setCurrentText(item.unit)
        form.addRow("Unit of Measure:", cmb_unit)

        spin_cost = QDoubleSpinBox()
        spin_cost.setRange(0.0, 1000000.0)
        spin_cost.setValue(item.unit_cost if item else 0.0)
        spin_cost.setMinimumHeight(32)
        form.addRow("Cost Price (Rs.):", spin_cost)

        spin_sale = QDoubleSpinBox()
        spin_sale.setRange(0.0, 1000000.0)
        spin_sale.setValue(item.unit_sale if item else 0.0)
        spin_sale.setMinimumHeight(32)
        form.addRow("Sale / Charge Price (Rs.):", spin_sale)

        spin_stock = QDoubleSpinBox()
        spin_stock.setRange(0.0, 100000.0)
        spin_stock.setValue(item.current_stock if item else 0.0)
        spin_stock.setMinimumHeight(32)
        if item:
            spin_stock.setEnabled(False) # Modify stock via purchase/adjustments
        form.addRow("Current Stock:" if item else "Initial Stock:", spin_stock)

        spin_min = QDoubleSpinBox()
        spin_min.setRange(0.0, 10000.0)
        spin_min.setValue(item.min_stock_alert if item else 5.0)
        spin_min.setMinimumHeight(32)
        form.addRow("Low Stock Alert Level:", spin_min)

        txt_loc = QLineEdit(item.location or "" if item else "")
        txt_loc.setPlaceholderText("e.g. Shelf A-1, Main Store")
        txt_loc.setMinimumHeight(32)
        form.addRow("Storage Location:", txt_loc)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("Save Item")
        btn_save.setMinimumHeight(32)
        btn_save.setStyleSheet(f"background-color: {t['accent']}; color: white; font-weight: bold; border-radius: 6px; padding: 4px 16px;")
        
        def save():
            name = txt_name.text().strip()
            if not name:
                QMessageBox.warning(dlg, "Error", "Item Name is required.")
                return
            success, msg = InventoryService.save_item(
                item_id=item.id if item else None,
                sku=txt_sku.text(),
                barcode=txt_barcode.text(),
                name=name,
                category_id=cmb_cat.currentData(),
                unit=cmb_unit.currentText(),
                unit_cost=spin_cost.value(),
                unit_sale=spin_sale.value(),
                current_stock=spin_stock.value(),
                min_stock_alert=spin_min.value(),
                location=txt_loc.text()
            )
            if success:
                dlg.accept()
                self.refresh_all()
            else:
                QMessageBox.critical(dlg, "Save Failed", msg)

        btn_save.clicked.connect(save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        form.addRow(btn_box)

        dlg.exec()

    def _on_manage_categories(self):
        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Manage Inventory Categories")
        dlg.setMinimumSize(460, 380)
        dlg.setStyleSheet(f"QDialog {{ background-color: {t['dialog_bg']}; color: {t['text_primary']}; }}")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        tbl = QTableWidget()
        tbl.setColumnCount(3)
        tbl.setHorizontalHeaderLabels(["Name", "Code", "Action"])
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        tbl.setColumnWidth(2, 60)
        tbl.verticalHeader().setDefaultSectionSize(44)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        def refresh_cat_table():
            for child in tbl.viewport().findChildren(QWidget):
                child.hide()
                child.setParent(None)
                child.deleteLater()
            tbl.clearContents()

            cats = InventoryService.get_categories()
            tbl.setRowCount(len(cats))
            for r, c in enumerate(cats):
                tbl.setItem(r, 0, QTableWidgetItem(c.name))
                tbl.setItem(r, 1, QTableWidgetItem(c.code or ""))
                btn_del = TableActionButton("trash-2", variant="delete", tooltip="Delete Category", size=28)
                btn_del.clicked.connect(lambda _, cat_id=c.id: delete_cat(cat_id))
                tbl.setCellWidget(r, 2, create_table_actions_cell([btn_del]))
                tbl.setRowHeight(r, 44)

        def delete_cat(cid):
            res, msg = InventoryService.delete_category(cid)
            if res:
                refresh_cat_table()
                self.refresh_all()
            else:
                QMessageBox.warning(dlg, "Notice", msg)

        refresh_cat_table()
        lay.addWidget(tbl)

        # Add row
        add_lay = QHBoxLayout()
        txt_n = QLineEdit()
        txt_n.setPlaceholderText("New Category Name...")
        txt_n.setMinimumHeight(28)
        txt_c = QLineEdit()
        txt_c.setPlaceholderText("Code...")
        txt_c.setMinimumHeight(28)
        btn_add = QPushButton("+ Add")
        btn_add.setMinimumHeight(28)
        btn_add.clicked.connect(lambda checked=False: on_add())

        def on_add():
            name = txt_n.text().strip()
            if not name:
                return
            res, msg = InventoryService.save_category(name=name, code=txt_c.text())
            if res:
                txt_n.clear()
                txt_c.clear()
                refresh_cat_table()
                self.refresh_all()
            else:
                QMessageBox.warning(dlg, "Error", msg)

        add_lay.addWidget(txt_n, 2)
        add_lay.addWidget(txt_c, 1)
        add_lay.addWidget(btn_add)
        lay.addLayout(add_lay)

        dlg.exec()

    def _on_add_supplier(self):
        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Add New Supplier")
        dlg.setMinimumWidth(380)
        dlg.setStyleSheet(f"QDialog {{ background-color: {t['dialog_bg']}; color: {t['text_primary']}; }}")

        form = QFormLayout(dlg)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(10)

        txt_name = QLineEdit()
        txt_name.setMinimumHeight(28)
        form.addRow("Supplier / Vendor Name *:", txt_name)

        txt_contact = QLineEdit()
        txt_contact.setMinimumHeight(28)
        form.addRow("Contact Person:", txt_contact)

        txt_phone = QLineEdit()
        txt_phone.setMinimumHeight(28)
        form.addRow("Phone Number:", txt_phone)

        txt_email = QLineEdit()
        txt_email.setMinimumHeight(28)
        form.addRow("Email Address:", txt_email)

        txt_addr = QLineEdit()
        txt_addr.setMinimumHeight(28)
        form.addRow("Address:", txt_addr)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("Save Supplier")
        btn_save.setMinimumHeight(28)
        btn_save.setStyleSheet(f"background-color: {t['accent']}; color: white; font-weight: bold; border-radius: 6px; padding: 4px 16px;")
        
        def save():
            name = txt_name.text().strip()
            if not name:
                QMessageBox.warning(dlg, "Error", "Supplier name is required.")
                return
            success, msg = InventoryService.save_supplier(
                name=name,
                contact_person=txt_contact.text(),
                phone=txt_phone.text(),
                email=txt_email.text(),
                address=txt_addr.text()
            )
            if success:
                dlg.accept()
                self.refresh_all()
            else:
                QMessageBox.critical(dlg, "Error", msg)

        btn_save.clicked.connect(save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(dlg.reject)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        form.addRow(btn_box)

        dlg.exec()