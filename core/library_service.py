from datetime import date, datetime, timedelta
from sqlalchemy.orm import joinedload
from database.connection import get_session
from database.models.library import Book, BookIssue


class LibraryService:

    # ── Book CRUD ────────────────────────────────────────────────
    @staticmethod
    def generate_book_id():
        db = get_session()
        try:
            last = db.query(Book).order_by(Book.id.desc()).first()
            num  = (last.id + 1) if last else 1
            return f"LIB-{num:04d}"
        finally:
            db.close()

    @staticmethod
    def add_book(data: dict):
        db = get_session()
        try:
            book_id = LibraryService.generate_book_id()
            qty     = int(data.get("total_copies", 1))
            book = Book(
                book_id          = book_id,
                title            = data.get("title", "").strip(),
                author           = data.get("author", "").strip(),
                isbn             = data.get("isbn", "").strip(),
                category         = data.get("category", "General").strip(),
                publisher        = data.get("publisher", "").strip(),
                edition          = data.get("edition", "").strip(),
                total_copies     = qty,
                available_copies = qty,
                rack_number      = data.get("rack_number", "").strip(),
            )
            db.add(book)
            db.commit()
            return True, f"Book '{book.title}' added successfully ({book_id})."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_all_books():
        db = get_session()
        try:
            return db.query(Book).filter_by(is_active=True).order_by(Book.id.desc()).all()
        finally:
            db.close()

    @staticmethod
    def update_book(book_id_int: int, data: dict):
        db = get_session()
        try:
            book = db.query(Book).filter_by(id=book_id_int).first()
            if not book:
                return False, "Book not found."
            qty_diff = int(data.get("total_copies", book.total_copies)) - book.total_copies
            book.title            = data.get("title", book.title).strip()
            book.author           = data.get("author", book.author).strip()
            book.isbn             = data.get("isbn", book.isbn).strip()
            book.category         = data.get("category", book.category).strip()
            book.publisher        = data.get("publisher", book.publisher).strip()
            book.edition          = data.get("edition", book.edition).strip()
            book.total_copies     = int(data.get("total_copies", book.total_copies))
            book.available_copies = max(0, book.available_copies + qty_diff)
            book.rack_number      = data.get("rack_number", book.rack_number).strip()
            db.commit()
            return True, "Book updated successfully."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def delete_book(book_id_int: int):
        db = get_session()
        try:
            book = db.query(Book).filter_by(id=book_id_int).first()
            if not book:
                return False, "Book not found."
            if book.available_copies < book.total_copies:
                return False, "Cannot delete — copies are currently issued to students."
            book.is_active = False
            db.commit()
            return True, "Book removed from catalog."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    # ── Issue / Return ───────────────────────────────────────────
    @staticmethod
    def issue_book(book_db_id: int, student_db_id: int, student_name: str,
                   student_sys_id: str, due_days: int = 14, fine_per_day: float = 5.0):
        db = get_session()
        try:
            book = db.query(Book).filter_by(id=book_db_id).first()
            if not book:
                return False, "Book not found."
            if book.available_copies <= 0:
                return False, "No copies available for issue."
            # Check if student already has this book
            active_issue = db.query(BookIssue).filter_by(
                book_id=book_db_id, student_db_id=student_db_id, status="Issued"
            ).first()
            if active_issue:
                return False, "This student already has this book issued."
            today    = date.today()
            due_date = today + timedelta(days=due_days)
            issue = BookIssue(
                book_id        = book_db_id,
                student_db_id  = student_db_id,
                student_name   = student_name,
                student_sys_id = student_sys_id,
                issued_date    = today,
                due_date       = due_date,
                fine_per_day   = fine_per_day,
                status         = "Issued",
            )
            book.available_copies -= 1
            db.add(issue)
            db.commit()
            return True, f"Book issued to {student_name}. Due: {due_date.strftime('%d-%m-%Y')}."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def return_book(issue_id: int):
        db = get_session()
        try:
            issue = db.query(BookIssue).filter_by(id=issue_id).first()
            if not issue:
                return False, "Issue record not found."
            if issue.status == "Returned":
                return False, "This book is already returned."
            today = date.today()
            fine  = 0.0
            if today > issue.due_date:
                overdue_days = (today - issue.due_date).days
                fine = overdue_days * issue.fine_per_day
            issue.returned_date = today
            issue.fine_amount   = fine
            issue.status        = "Returned"
            book = db.query(Book).filter_by(id=issue.book_id).first()
            if book:
                book.available_copies = min(book.available_copies + 1, book.total_copies)
            db.commit()
            msg = f"Book returned successfully."
            if fine > 0:
                msg += f" Overdue fine: Rs. {fine:.0f}"
            return True, msg
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def get_active_issues():
        db = get_session()
        try:
            return db.query(BookIssue).options(joinedload(BookIssue.book)).filter(
                BookIssue.status.in_(["Issued", "Overdue"])
            ).order_by(BookIssue.issued_at.desc()).all()
        finally:
            db.close()

    @staticmethod
    def get_overdue_count():
        db = get_session()
        try:
            today = date.today()
            return db.query(BookIssue).filter(
                BookIssue.status == "Issued",
                BookIssue.due_date < today
            ).count()
        finally:
            db.close()

    @staticmethod
    def get_dashboard_stats():
        db = get_session()
        try:
            total_books   = db.query(Book).filter_by(is_active=True).count()
            total_issued  = db.query(BookIssue).filter_by(status="Issued").count()
            today         = date.today()
            overdue       = db.query(BookIssue).filter(
                BookIssue.status == "Issued",
                BookIssue.due_date < today
            ).count()
            return {
                "total_books": total_books,
                "total_issued": total_issued,
                "overdue": overdue,
            }
        finally:
            db.close()
