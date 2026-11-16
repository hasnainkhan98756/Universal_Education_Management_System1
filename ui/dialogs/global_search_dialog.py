from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QFrame, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor, QKeyEvent

from core.theme_manager import ThemeManager
from core.search_service import GlobalSearchService
from core.icon_manager import icon_mgr

class GlobalSearchDialog(QDialog):
    """Modern Spotlight-Style Global Search Dialog (Ctrl+K)."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(160)
        self._debounce_timer.timeout.connect(self._execute_search)

        self.init_ui()

    def init_ui(self):
        t = ThemeManager.tokens()
        self.setWindowTitle("Quick Global Search")
        self.setMinimumSize(600, 440)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['bg_surface']};
                border: 1.5px solid {t['border']};
                border-radius: 12px;
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # Header Search Input Row
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search students, faculty, fees, inventory, expenses, docs... (Esc to close)")
        self.txt_search.setMinimumHeight(40)
        self.txt_search.setFont(QFont("Segoe UI", 12))
        self.txt_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 2px solid {t['accent']};
                border-radius: 8px;
                padding: 6px 14px;
            }}
        """)
        self.txt_search.textChanged.connect(self._on_text_changed)
        lay.addWidget(self.txt_search)

        # Results List
        self.list_results = QListWidget()
        self.list_results.setStyleSheet(f"""
            QListWidget {{
                background-color: {t['bg_card']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                border-radius: 6px;
                padding: 6px 10px;
                margin: 2px 0;
            }}
            QListWidget::item:selected {{
                background-color: {t['accent']};
                color: white;
            }}
        """)
        self.list_results.itemActivated.connect(self._on_item_activated)
        self.list_results.itemClicked.connect(self._on_item_activated)
        self.list_results.itemDoubleClicked.connect(self._on_item_activated)
        lay.addWidget(self.list_results)

        # Footer shortcut hint
        hint_row = QHBoxLayout()
        hint = QLabel("↑/↓ Navigate • Click / Enter to Select • Esc to Close")
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color: {t['text_secondary']}; background: transparent; border: none;")
        hint_row.addWidget(hint)
        hint_row.addStretch()

        self.lbl_count = QLabel("0 results")
        self.lbl_count.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_count.setStyleSheet(f"color: {t['text_secondary']}; background: transparent; border: none;")
        hint_row.addWidget(self.lbl_count)
        lay.addLayout(hint_row)

        self.txt_search.setFocus()

    def _on_text_changed(self, text):
        self._debounce_timer.start()

    def _execute_search(self):
        query = self.txt_search.text().strip()
        self.list_results.clear()

        if len(query) < 2:
            self.lbl_count.setText("0 results")
            return

        results = GlobalSearchService.search_all(query)
        self.lbl_count.setText(f"{len(results)} result(s)")

        t = ThemeManager.tokens()
        for res in results:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, res)

            # Custom card widget with pointer cursor and click handler
            widget = QWidget()
            widget.setCursor(Qt.CursorShape.PointingHandCursor)
            widget.mousePressEvent = lambda e, it=item: self._on_item_activated(it)

            w_lay = QHBoxLayout(widget)
            w_lay.setContentsMargins(6, 4, 6, 4)
            w_lay.setSpacing(10)

            category_icons = {
                "Students": "graduation-cap",
                "Faculty & Staff": "users",
                "Fee Vouchers": "receipt",
                "Store Inventory": "package",
                "Expenses": "trending-down",
                "Documents": "file-text",
            }
            icon_name = category_icons.get(res.get("category"), "search")
            icon_lbl = QLabel()
            icon_lbl.setPixmap(icon_mgr.get_icon(icon_name, color="#2563EB").pixmap(18, 18))
            icon_lbl.setFixedSize(22, 22)
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            w_lay.addWidget(icon_lbl)

            col = QVBoxLayout()
            col.setSpacing(1)

            top_line = QHBoxLayout()
            title_lbl = QLabel(res.get("title", ""))
            title_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            title_lbl.setStyleSheet("background: transparent; border: none;")
            top_line.addWidget(title_lbl)

            cat_badge = QLabel(f" {res.get('category', '')} ")
            cat_badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            cat_badge.setStyleSheet(f"background-color: {t['border']}; color: {t['text_secondary']}; border-radius: 4px; padding: 2px 4px;")
            top_line.addSpacing(6)
            top_line.addWidget(cat_badge)
            top_line.addStretch()
            col.addLayout(top_line)

            sub_lbl = QLabel(res.get("subtitle", ""))
            sub_lbl.setFont(QFont("Segoe UI", 9))
            sub_lbl.setStyleSheet(f"color: {t['text_secondary']}; background: transparent; border: none;")
            col.addWidget(sub_lbl)

            w_lay.addLayout(col)
            w_lay.addStretch()

            item.setSizeHint(widget.sizeHint())
            self.list_results.addItem(item)
            self.list_results.setItemWidget(item, widget)

        if self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)

    def _on_item_activated(self, item):
        res = item.data(Qt.ItemDataRole.UserRole)
        if res and "page_index" in res:
            page_idx = res["page_index"]
            payload = res.get("payload")
            self.accept()
            if self.main_window and hasattr(self.main_window, "navigate_to_page"):
                self.main_window.navigate_to_page(page_idx, payload=payload)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key.Key_Down:
            cur = self.list_results.currentRow()
            if cur < self.list_results.count() - 1:
                self.list_results.setCurrentRow(cur + 1)
            event.accept()
            return
        elif key == Qt.Key.Key_Up:
            cur = self.list_results.currentRow()
            if cur > 0:
                self.list_results.setCurrentRow(cur - 1)
            event.accept()
            return
        elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            cur_item = self.list_results.currentItem()
            if cur_item:
                self._on_item_activated(cur_item)
                event.accept()
                return
        elif key == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
            return
        super().keyPressEvent(event)
