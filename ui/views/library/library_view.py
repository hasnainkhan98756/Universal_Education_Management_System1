from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QFrame, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.library_service import LibraryService
from core.student_service import StudentService
from database.connection import get_session
from database.models.student import Student
from core.icon_manager import get_icon
from ui.components.stitch_widgets import (
    PageHeader, ModernCard, MetricCard, StatusBadge,
    ModernButton, TableActionButton, TableTextButton, create_table_actions_cell,
    SearchInput, style_modern_table, style_modern_tabs
)


def _styled_btn(text, obj_name="btn_primary"):
    b = QPushButton(text)
    b.setObjectName(obj_name)
    return b



class AddBookDialog(QDialog):
    def __init__(self, parent=None, book=None):
        super().__init__(parent)
        self.setWindowTitle("Add Book" if not book else "Edit Book")
        self.setMinimumWidth(420)
        self.book = book
        lay = QVBoxLayout(self)
        form = QFormLayout(); form.setSpacing(12)

        self.inp_title     = QLineEdit(); self.inp_title.setPlaceholderText("Required")
        self.inp_author    = QLineEdit()
        self.inp_isbn      = QLineEdit()
        self.inp_category  = QComboBox()
        self.inp_category.addItems(["General","Science","Mathematics","Literature",
                                    "History","Islamic","Computer","Reference","Other"])
        self.inp_category.setEditable(True)
        self.inp_publisher = QLineEdit()
        self.inp_edition   = QLineEdit()
        self.sp_copies     = QSpinBox(); self.sp_copies.setRange(1, 9999); self.sp_copies.setValue(1)
        self.inp_rack      = QLineEdit()

        # Styles removed to support dark mode

        form.addRow("<b>Title:</b>",     self.inp_title)
        form.addRow("<b>Author:</b>",    self.inp_author)
        form.addRow("<b>ISBN:</b>",      self.inp_isbn)
        form.addRow("<b>Category:</b>",  self.inp_category)
        form.addRow("<b>Publisher:</b>", self.inp_publisher)
        form.addRow("<b>Edition:</b>",   self.inp_edition)
        form.addRow("<b>Copies:</b>",    self.sp_copies)
        form.addRow("<b>Rack No:</b>",   self.inp_rack)
        lay.addLayout(form)

        if book:
            self.inp_title.setText(book.title)
            self.inp_author.setText(book.author)
            self.inp_isbn.setText(book.isbn)
            self.inp_category.setCurrentText(book.category)
            self.inp_publisher.setText(book.publisher)
            self.inp_edition.setText(book.edition)
            self.sp_copies.setValue(book.total_copies)
            self.inp_rack.setText(book.rack_number)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_data(self):
        return {
            "title":        self.inp_title.text(),
            "author":       self.inp_author.text(),
            "isbn":         self.inp_isbn.text(),
            "category":     self.inp_category.currentText(),
            "publisher":    self.inp_publisher.text(),
            "edition":      self.inp_edition.text(),
            "total_copies": self.sp_copies.value(),
            "rack_number":  self.inp_rack.text(),
        }


class IssueBookDialog(QDialog):
    def __init__(self, books, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Issue Book to Student")
        self.setMinimumWidth(440)
        lay = QVBoxLayout(self); form = QFormLayout(); form.setSpacing(12)

        self.combo_book = QComboBox()
        for b in books:
            self.combo_book.addItem(f"{b.book_id} - {b.title} (Avail: {b.available_copies})", b.id)

        self.inp_student = SearchInput(placeholder="Type Student ID or Name...")
        self.btn_search  = ModernButton("Search", icon_name="search", variant="secondary")
        self.lbl_student = QLabel("No student selected.")

        self.selected_student = None
        self.btn_search.clicked.connect(self._search_student)

        s_row = QHBoxLayout(); s_row.addWidget(self.inp_student); s_row.addWidget(self.btn_search)

        self.sp_days     = QSpinBox(); self.sp_days.setRange(1,60); self.sp_days.setValue(14)
        self.sp_fine     = QDoubleSpinBox(); self.sp_fine.setRange(0,1000); self.sp_fine.setValue(5.0)

        form.addRow("<b>Book:</b>",             self.combo_book)
        form.addRow("<b>Search Student:</b>",   s_row)
        form.addRow("",                          self.lbl_student)
        form.addRow("<b>Due Days:</b>",          self.sp_days)
        form.addRow("<b>Fine/Day (Rs.):</b>",   self.sp_fine)
        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _search_student(self):
        q = self.inp_student.text().strip()
        if not q: return
        db = get_session()
        try:
            stu = db.query(Student).filter(
                (Student.student_id == q) |
                (Student.first_name.ilike(f"%{q}%"))
            ).filter_by(status="Active").first()
            if stu:
                self.selected_student = stu
                self.lbl_student.setText(
                    f"Selected: {stu.first_name} {stu.last_name or ''} ({stu.student_id})"
                )
                self.lbl_student.setStyleSheet("color:#16A34A;font-weight:bold;background:transparent;border:none;")
            else:
                self.selected_student = None
                self.lbl_student.setText("Student not found.")
                self.lbl_student.setStyleSheet("color:#DC2626;background:transparent;border:none;")
        finally:
            db.close()


class LibraryView(QWidget):
    def __init__(self):
        super().__init__()
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(14)

        header = PageHeader(
            title="Library Management",
            subtitle="Track book catalog, issue/return cycles, and overdue borrowings",
            icon_name="book-open",
        )
        main.addWidget(header)

        # Stats bar
        self.stats_bar = QHBoxLayout()
        self.stats_bar.setSpacing(14)
        self.lbl_total    = MetricCard(title="Total Books", value="0", icon_name="book-open", accent_color="#1D4ED8")
        self.lbl_issued   = MetricCard(title="Currently Issued", value="0", icon_name="book", accent_color="#F59E0B")
        self.lbl_overdue  = MetricCard(title="Overdue", value="0", icon_name="alert-circle", accent_color="#DC2626")
        
        self.lbl_total._value_lbl = self.lbl_total.lbl_val
        self.lbl_issued._value_lbl = self.lbl_issued.lbl_val
        self.lbl_overdue._value_lbl = self.lbl_overdue.lbl_val

        self.stats_bar.addWidget(self.lbl_total)
        self.stats_bar.addWidget(self.lbl_issued)
        self.stats_bar.addWidget(self.lbl_overdue)
        main.addLayout(self.stats_bar)

        # Tabs
        self.tabs = QTabWidget()
        style_modern_tabs(self.tabs)
        self.tabs.addTab(self._build_books_tab(),   "Book Catalog")
        self.tabs.setTabIcon(0, get_icon("book-open", color="#475569"))
        self.tabs.addTab(self._build_issue_tab(),   "Issue / Return")
        self.tabs.setTabIcon(1, get_icon("calendar-check", color="#475569"))
        main.addWidget(self.tabs)

        self.refresh_all()

    def _stat_card(self, label, value, color):
        frame = MetricCard(title=label, value=value, icon_name="book-open", accent_color=color)
        frame._value_lbl = frame.lbl_val
        return frame

    def _build_books_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(10,10,10,10)
        lay.setSpacing(10)
        bar = QHBoxLayout()
        self.inp_search_book = SearchInput(placeholder="Search by title, author, or book ID...")
        self.inp_search_book.textChanged.connect(self.filter_books)
        btn_add = ModernButton("Add Book", icon_name="plus", variant="primary")
        btn_add.clicked.connect(self.add_book)
        bar.addWidget(self.inp_search_book); bar.addStretch(); bar.addWidget(btn_add)
        lay.addLayout(bar)

        self.tbl_books = QTableWidget()
        self.tbl_books.setColumnCount(9)
        self.tbl_books.setHorizontalHeaderLabels([
            "Book ID","Title","Author","Category","ISBN",
            "Total","Available","Rack","Actions"
        ])
        self.tbl_books.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_books.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.tbl_books.setColumnWidth(8, 110)
        self.tbl_books.verticalHeader().setDefaultSectionSize(48)
        self.tbl_books.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_books.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        style_modern_table(self.tbl_books)
        lay.addWidget(self.tbl_books)
        return w

    def _build_issue_tab(self):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(10,10,10,10)
        lay.setSpacing(10)
        bar = QHBoxLayout()
        self.combo_issue_filter = QComboBox()
        self.combo_issue_filter.addItems(["All Active Issues","Overdue Only"])
        self.combo_issue_filter.currentIndexChanged.connect(self.refresh_issues)
        btn_issue = ModernButton("Issue Book", icon_name="plus", variant="primary")
        btn_issue.clicked.connect(self.issue_book)
        bar.addWidget(QLabel("Filter:")); bar.addWidget(self.combo_issue_filter)
        bar.addStretch(); bar.addWidget(btn_issue)
        lay.addLayout(bar)

        self.tbl_issues = QTableWidget()
        self.tbl_issues.setColumnCount(8)
        self.tbl_issues.setHorizontalHeaderLabels([
            "Issue ID","Book","Student ID","Student Name",
            "Issued","Due","Status","Return"
        ])
        self.tbl_issues.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_issues.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.tbl_issues.setColumnWidth(7, 110)
        self.tbl_issues.verticalHeader().setDefaultSectionSize(48)
        self.tbl_issues.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_issues.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        style_modern_table(self.tbl_issues)
        lay.addWidget(self.tbl_issues)
        return w

    # ── Refresh ───────────────────────────────────────────────────
    def refresh_all(self):
        self.refresh_books()
        self.refresh_issues()
        self._update_stats()

    def _update_stats(self):
        s = LibraryService.get_dashboard_stats()
        self.lbl_total._value_lbl.setText(str(s["total_books"]))
        self.lbl_issued._value_lbl.setText(str(s["total_issued"]))
        self.lbl_overdue._value_lbl.setText(str(s["overdue"]))

    def refresh_books(self):
        self._all_books = LibraryService.get_all_books()
        self._populate_books(self._all_books)

    def filter_books(self):
        q = self.inp_search_book.text().lower()
        filtered = [b for b in self._all_books
                    if q in b.title.lower() or q in b.author.lower() or q in b.book_id.lower()]
        self._populate_books(filtered)

    def _populate_books(self, books):
        for r in range(self.tbl_books.rowCount()):
            w = self.tbl_books.cellWidget(r, 8)
            if w:
                self.tbl_books.removeCellWidget(r, 8)
                w.deleteLater()
        self.tbl_books.clearContents()
        self.tbl_books.setRowCount(0)

        self.tbl_books.setRowCount(len(books))
        for r, b in enumerate(books):
            items = [b.book_id, b.title, b.author, b.category, b.isbn,
                     str(b.total_copies), str(b.available_copies), b.rack_number]
            for c, val in enumerate(items):
                item = QTableWidgetItem(val)
                if c == 6:
                    item.setForeground(Qt.GlobalColor.darkGreen if b.available_copies > 0 else Qt.GlobalColor.red)
                self.tbl_books.setItem(r, c, item)

            btn_e = TableActionButton("pencil", variant="edit", tooltip="Edit Book", size=30)
            btn_d = TableActionButton("trash-2", variant="delete", tooltip="Delete Book", size=30)
            btn_e.clicked.connect(lambda _, bid=b.id: self.edit_book(bid))
            btn_d.clicked.connect(lambda _, bid=b.id: self.delete_book(bid))

            act_w = create_table_actions_cell([btn_e, btn_d])
            self.tbl_books.setCellWidget(r, 8, act_w)
            self.tbl_books.setRowHeight(r, 48)

    def refresh_issues(self):
        for r in range(self.tbl_issues.rowCount()):
            w = self.tbl_issues.cellWidget(r, 7)
            if w:
                self.tbl_issues.removeCellWidget(r, 7)
                w.deleteLater()
        self.tbl_issues.clearContents()
        self.tbl_issues.setRowCount(0)

        issues = LibraryService.get_active_issues()
        today  = date.today()
        if self.combo_issue_filter.currentIndex() == 1:
            issues = [i for i in issues if i.due_date < today]
        self.tbl_issues.setRowCount(len(issues))
        for r, iss in enumerate(issues):
            is_overdue = iss.due_date < today and iss.status == "Issued"
            status_text = "Overdue" if is_overdue else iss.status
            book_title = ""
            try:
                book_title = iss.book.title if iss.book else ""
            except Exception:
                book_title = ""
            items = [
                str(iss.id),
                book_title,
                iss.student_sys_id,
                iss.student_name,
                str(iss.issued_date),
                str(iss.due_date),
                status_text,
            ]
            for c, val in enumerate(items):
                item = QTableWidgetItem(val)
                if c == 6 and is_overdue:
                    item.setForeground(Qt.GlobalColor.red)
                self.tbl_issues.setItem(r, c, item)

            btn_ret = TableTextButton("Return", icon_name="check", variant="success")
            btn_ret.clicked.connect(lambda _, iid=iss.id: self.return_book(iid))
            act_w = create_table_actions_cell([btn_ret])
            self.tbl_issues.setCellWidget(r, 7, act_w)
            self.tbl_issues.setRowHeight(r, 48)

    # ── Actions ───────────────────────────────────────────────────
    def add_book(self):
        dlg = AddBookDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = LibraryService.add_book(dlg.get_data())
            if ok:
                QMessageBox.information(self, "Success", msg)
                self.refresh_all()
            else:
                QMessageBox.critical(self, "Error", msg)

    def edit_book(self, book_id):
        books = LibraryService.get_all_books()
        book  = next((b for b in books if b.id == book_id), None)
        if not book: return
        dlg = AddBookDialog(self, book=book)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ok, msg = LibraryService.update_book(book_id, dlg.get_data())
            if ok: QMessageBox.information(self, "Success", msg); self.refresh_all()
            else:  QMessageBox.critical(self, "Error", msg)

    def delete_book(self, book_id):
        reply = QMessageBox.question(self, "Confirm", "Remove this book from catalog?")
        if reply == QMessageBox.StandardButton.Yes:
            ok, msg = LibraryService.delete_book(book_id)
            if ok: QMessageBox.information(self, "Done", msg); self.refresh_all()
            else:  QMessageBox.critical(self, "Error", msg)

    def issue_book(self):
        books = [b for b in LibraryService.get_all_books() if b.available_copies > 0]
        if not books:
            QMessageBox.warning(self, "No Books", "No books available for issue."); return
        dlg = IssueBookDialog(books, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if not dlg.selected_student:
                QMessageBox.warning(self, "Error", "Please search and select a student first."); return
            book_id  = dlg.combo_book.currentData()
            stu      = dlg.selected_student
            ok, msg  = LibraryService.issue_book(
                book_id, stu.id,
                f"{stu.first_name} {stu.last_name or ''}".strip(),
                stu.student_id,
                dlg.sp_days.value(), dlg.sp_fine.value()
            )
            if ok: QMessageBox.information(self, "Issued", msg); self.refresh_all()
            else:  QMessageBox.critical(self, "Error", msg)

    def return_book(self, issue_id):
        ok, msg = LibraryService.return_book(issue_id)
        if ok: QMessageBox.information(self, "Returned", msg); self.refresh_all()
        else:  QMessageBox.critical(self, "Error", msg)

    def showEvent(self, event):
        self.refresh_all()
        super().showEvent(event)
