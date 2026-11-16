"""
calendar_view.py
================
School Calendar View — Phase 3 implementation.

Displays a QCalendarWidget backed by the `calendar_events` table
(model: database.models.calendar.CalendarEvent).

Features
--------
* Full interactive QCalendarWidget
* Dates with events are highlighted in type-specific colours
* Side panel lists events for the selected date
* "Add Event" dialog persists new events to the database
* 100% theme-aware via ThemeManager.tokens() — zero hard-coded palette
* Subscribes to app_state settings changes so theme switches update live
"""

from __future__ import annotations

import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QCalendarWidget, QDialog, QFormLayout, QLineEdit, QComboBox,
    QTextEdit, QDialogButtonBox, QScrollArea, QSizePolicy, QDateEdit,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QSpinBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QTextCharFormat

from database.connection import get_session
from core.theme_manager import ThemeManager
from core.state_manager import app_state
from core.icon_manager import icon_mgr
from core.calendar_service import CalendarService
from ui.components.stitch_widgets import (
    PageHeader, ModernButton, ModernCard, StatusBadge, style_modern_table
)

# ---------------------------------------------------------------------------
# Event-type to accent colour mapping (consistent across light/dark mode)
# ---------------------------------------------------------------------------
_TYPE_COLORS: Dict[str, str] = {
    "Holiday":          "#EF4444",
    "Summer Vacation":  "#F97316",
    "Winter Vacation":  "#06B6D4",
    "Exam":             "#8B5CF6",
    "Sports Day":       "#10B981",
    "Event":            "#3B82F6",
    "Meeting":          "#6366F1",
    "Reminder":         "#EC4899",
    "General":          "#F59E0B",
}
_EVENT_TYPES = list(_TYPE_COLORS.keys())


class GazettedHolidaysDialog(QDialog):
    """Worldwide Gazetted Holidays Dialog with multi-country selection and preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Worldwide Gazetted Holidays")
        self.setMinimumSize(820, 540)
        self._holidays: List[tuple] = []
        self._check_boxes: List[QCheckBox] = []
        self._build_ui()
        self._load_country_holidays()

    def _build_ui(self):
        t = ThemeManager.tokens()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['bg_surface']};
                color: {t['text_primary']};
                font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial, sans-serif;
            }}
            QLabel {{
                color: {t['text_primary']};
                font-weight: 600;
                font-size: 13px;
            }}
            QComboBox, QSpinBox {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Header banner
        info_banner = QFrame()
        info_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {t.get('accent_light', '#EFF6FF')};
                border: 1px solid #BFDBFE;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        ib_lay = QVBoxLayout(info_banner)
        ib_lay.setContentsMargins(10, 8, 10, 8)
        lbl_info = QLabel("<b>Worldwide Gazetted Holiday Sync</b><br><small style='color: #475569;'>Select your country/region calendar to preview and automatically import gazetted public holidays and vacations. Student attendance, staff attendance, calendar, and timetable modules will seamlessly link with these dates.</small>")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("background: transparent; border: none; font-size: 12px;")
        ib_lay.addWidget(lbl_info)
        layout.addWidget(info_banner)

        # Country & Year selectors
        filters_row = QHBoxLayout()
        filters_row.setSpacing(12)

        filters_row.addWidget(QLabel("Select Calendar:"))
        self.cb_country = QComboBox()
        self.cb_country.setMinimumWidth(280)
        for code, name in CalendarService.get_supported_countries():
            self.cb_country.addItem(name, code)
        self.cb_country.currentIndexChanged.connect(self._load_country_holidays)
        filters_row.addWidget(self.cb_country)

        filters_row.addWidget(QLabel("Year:"))
        self.sp_year = QSpinBox()
        self.sp_year.setRange(2020, 2035)
        self.sp_year.setValue(datetime.date.today().year)
        self.sp_year.valueChanged.connect(self._load_country_holidays)
        filters_row.addWidget(self.sp_year)

        filters_row.addStretch()

        btn_select_all = ModernButton("Select All", variant="secondary")
        btn_select_all.setFixedHeight(32)
        btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        filters_row.addWidget(btn_select_all)

        btn_deselect_all = ModernButton("Deselect All", variant="secondary")
        btn_deselect_all.setFixedHeight(32)
        btn_deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        filters_row.addWidget(btn_deselect_all)

        layout.addLayout(filters_row)

        # Preview Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Include", "Holiday / Event", "Type", "Dates", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 65)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 130)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 140)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(40)
        style_modern_table(self.table)
        layout.addWidget(self.table, 1)

        # Footer Actions
        footer = QHBoxLayout()
        self.lbl_count = QLabel("0 holidays found")
        self.lbl_count.setStyleSheet("color: #64748B; font-size: 12px; font-weight: 600;")
        footer.addWidget(self.lbl_count)
        footer.addStretch()

        btn_cancel = ModernButton("Cancel", variant="secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(btn_cancel)

        btn_import = ModernButton("Import Selected Holidays", icon_name="calendar", variant="primary")
        btn_import.setFixedHeight(36)
        btn_import.clicked.connect(self._import_selected)
        footer.addWidget(btn_import)

        layout.addLayout(footer)

    def _set_all_checked(self, checked: bool):
        for cb in self._check_boxes:
            cb.setChecked(checked)

    def _load_country_holidays(self):
        country_code = self.cb_country.currentData() or "pk"
        year = self.sp_year.value()
        self._holidays = CalendarService.get_gazetted_holidays_for_country(country_code, year)

        self.table.setRowCount(0)
        self._check_boxes.clear()

        self.table.setRowCount(len(self._holidays))
        for r, (title, etype, sdate, edate, desc) in enumerate(self._holidays):
            cb = QCheckBox()
            cb.setChecked(True)
            cb_container = QWidget()
            cb_lay = QHBoxLayout(cb_container)
            cb_lay.setContentsMargins(0, 0, 0, 0)
            cb_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_lay.addWidget(cb)
            self._check_boxes.append(cb)
            self.table.setCellWidget(r, 0, cb_container)

            t_item = QTableWidgetItem(title)
            t_item.setFont(QFont("Plus Jakarta Sans", 9, QFont.Weight.Bold))
            self.table.setItem(r, 1, t_item)

            badge = StatusBadge(etype, "warning" if "Vacation" in etype else "error" if "Holiday" in etype else "info")
            badge_container = QWidget()
            b_lay = QHBoxLayout(badge_container)
            b_lay.setContentsMargins(6, 4, 6, 4)
            b_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_lay.addWidget(badge)
            self.table.setCellWidget(r, 2, badge_container)

            date_str = f"{sdate} to {edate}" if sdate != edate else sdate
            d_item = QTableWidgetItem(date_str)
            d_item.setFont(QFont("Plus Jakarta Sans", 9))
            self.table.setItem(r, 3, d_item)

            desc_item = QTableWidgetItem(desc or "-")
            desc_item.setFont(QFont("Plus Jakarta Sans", 9))
            self.table.setItem(r, 4, desc_item)

        self.lbl_count.setText(f"{len(self._holidays)} official holidays and vacations generated for {year}")

    def _import_selected(self):
        selected_holidays = []
        for i, cb in enumerate(self._check_boxes):
            if cb.isChecked() and i < len(self._holidays):
                selected_holidays.append(self._holidays[i])

        if not selected_holidays:
            QMessageBox.warning(self, "No Holidays Selected", "Please select at least one holiday to import.")
            return

        cur_year = self.sp_year.value()
        session_name = app_state.get_setting("session", f"{cur_year}-{cur_year+1}") or f"{cur_year}-{cur_year+1}"
        success, added_count, msg = CalendarService.load_gazetted_holidays(selected_holidays, session_name)
        if success:
            QMessageBox.information(
                self,
                "Holidays Loaded Successfully",
                f"{msg}\n\nAll selected holidays are now active across Calendar, Student Attendance, Staff Attendance, and Timetable!"
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Import Error", f"Failed to import holidays: {msg}")


class DeclareHolidayDialog(QDialog):
    """
    Dedicated dialog for quickly declaring government-announced, district, or emergency holidays.
    Instantly marks the date in the Academic Calendar, links with Attendance (skipping
    attendance or defaulting to Holiday), and notifies all school modules.
    """
    PRESETS = [
        "Government Announced Public Holiday",
        "Heavy Rain / Flood Emergency Holiday",
        "Local District Administration Holiday",
        "Election / Polling Day Closure",
        "Severe Weather / Smog / Heatwave Holiday",
        "Official Mourning / Institutional Closure",
        "Special Public Holiday",
        "Custom Holiday...",
    ]

    def __init__(self, parent=None, default_date: Optional[datetime.date] = None):
        super().__init__(parent)
        self.setWindowTitle("Declare Official Holiday")
        self.setMinimumWidth(480)
        self.default_date = default_date or datetime.date.today()
        self._build_ui()

    def _build_ui(self):
        t = ThemeManager.tokens()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t['dialog_bg']};
                color: {t['text_primary']};
                font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial, sans-serif;
            }}
            QLabel {{
                color: {t['text_primary']};
                font-weight: 600;
                font-size: 13px;
            }}
            QLineEdit, QComboBox, QDateEdit, QTextEdit {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{
                border: 1.5px solid {t['accent']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # Informational Banner
        banner = QFrame()
        banner.setStyleSheet("""
            QFrame {
                background-color: #FEF3C7;
                border: 1.5px solid #F59E0B;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        b_lay = QVBoxLayout(banner)
        b_lay.setContentsMargins(8, 6, 8, 6)
        b_lbl = QLabel(
            "<b>Declare Public / Government Holiday</b><br>"
            "<small style='color: #92400E;'>"
            "When declared, this date will be highlighted in Red on the Academic Calendar. "
            "Daily attendance reminders on the Main Dashboard will be skipped, and student & "
            "staff attendance will default to <b>Holiday</b> (excluded from working days count)."
            "</small>"
        )
        b_lbl.setWordWrap(True)
        b_lbl.setStyleSheet("border: none; background: transparent; font-size: 12px;")
        b_lay.addWidget(b_lbl)
        layout.addWidget(banner)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.cb_preset = QComboBox()
        self.cb_preset.addItems(self.PRESETS)
        self.cb_preset.currentTextChanged.connect(self._on_preset_changed)
        form.addRow("Holiday Category:", self.cb_preset)

        self.txt_title = QLineEdit(self.PRESETS[0])
        self.txt_title.setPlaceholderText("Enter official title of the holiday...")
        form.addRow("Holiday Title *:", self.txt_title)

        # Date pickers
        d_row = QHBoxLayout()
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDisplayFormat("yyyy-MM-dd")
        self.dt_start.setDate(QDate(self.default_date.year, self.default_date.month, self.default_date.day))

        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDisplayFormat("yyyy-MM-dd")
        self.dt_end.setDate(QDate(self.default_date.year, self.default_date.month, self.default_date.day))

        d_row.addWidget(QLabel("From:"))
        d_row.addWidget(self.dt_start)
        d_row.addWidget(QLabel("To:"))
        d_row.addWidget(self.dt_end)
        form.addRow("Date Range *:", d_row)

        self.txt_desc = QTextEdit()
        self.txt_desc.setMaximumHeight(70)
        self.txt_desc.setPlaceholderText("Notification circular number or official notification remarks (optional)...")
        form.addRow("Notification / Circular:", self.txt_desc)

        layout.addLayout(form)

        # Action buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_save = ModernButton("Confirm & Mark Holiday", icon_name="check", variant="primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(self._save_holiday)
        btn_cancel = ModernButton("Cancel", icon_name="x", variant="secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _on_preset_changed(self, text: str):
        if text != "Custom Holiday...":
            self.txt_title.setText(text)
        else:
            self.txt_title.clear()
            self.txt_title.setFocus()

    def _save_holiday(self):
        title = self.txt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Title Required", "Please provide a title for the holiday.")
            return

        s_date = self.dt_start.date().toString("yyyy-MM-dd")
        e_date = self.dt_end.date().toString("yyyy-MM-dd")

        if s_date > e_date:
            QMessageBox.warning(self, "Invalid Date Range", "End date cannot be earlier than start date.")
            return

        desc = self.txt_desc.toPlainText().strip()
        cur_year = self.dt_start.date().year()
        session_name = app_state.get_setting("session", f"{cur_year}-{cur_year+1}") or f"{cur_year}-{cur_year+1}"

        success, msg = CalendarService.add_event(
            title=title,
            event_type="Holiday",
            start_date=s_date,
            end_date=e_date,
            description=desc,
            session_name=session_name
        )

        if success:
            QMessageBox.information(
                self,
                "Holiday Declared",
                f"Successfully marked '{title}' as a Holiday from {s_date} to {e_date}.\n\n"
                "• Academic Calendar updated with Red highlight.\n"
                "• Attendance reminder skipped for this date.\n"
                "• Attendance roll calls will default to Holiday without penalty."
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to declare holiday: {msg}")


class CalendarView(QWidget):
    """School Calendar View — shows QCalendarWidget with school events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: List[Dict[str, Any]] = []
        self._build_ui()
        self.refresh_data()
        app_state.subscribe_settings_change(self.refresh_data)
        app_state.subscribe_data_changed(self.refresh_data)

    def showEvent(self, event):
        self.refresh_data()
        super().showEvent(event)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        t = ThemeManager.tokens()
        self.setStyleSheet(f"background-color: {t['bg_surface']}; color: {t['text_primary']};")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header
        btn_seed = ModernButton("Load Gazetted Holidays", icon_name="calendar", variant="secondary")
        btn_seed.clicked.connect(self._open_gazetted_holidays_dialog)

        btn_holiday = ModernButton("Declare Holiday", icon_name="calendar-x", variant="warning")
        btn_holiday.clicked.connect(lambda: self._open_declare_holiday_dialog())

        btn_add = ModernButton("Add Event", icon_name="plus", variant="primary")
        btn_add.clicked.connect(self._show_add_event_dialog)

        header = PageHeader(
            title="Academic Calendar & Holidays",
            subtitle="Manage gazetted holidays, vacations, emergency closures, and school events",
            icon_name="calendar-days",
            actions=[btn_seed, btn_holiday, btn_add]
        )
        root.addWidget(header)

        # Body
        body = QHBoxLayout()
        body.setSpacing(16)

        # Calendar card
        cal_card = ModernCard()
        cal_lay = QVBoxLayout(cal_card)
        cal_lay.setContentsMargins(18, 18, 18, 18)
        cal_lay.setSpacing(0)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setMinimumSize(440, 340)
        self.calendar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: none;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {t['bg_card']};
                border-bottom: 1px solid {t['border_color']};
                min-height: 44px;
            }}
            QCalendarWidget QToolButton {{
                color: {t['text_primary']};
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px 10px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {t['bg_hover']};
            }}
            QCalendarWidget QMenu {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 6px;
            }}
            QCalendarWidget QSpinBox {{
                background-color: {t['bg_card']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 6px;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {t['text_primary']};
                background-color: {t['bg_card']};
                selection-background-color: {t['accent']};
                selection-color: #FFFFFF;
                font-size: 13px;
            }}
        """)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        self.calendar.activated.connect(self._on_calendar_activated)
        self.calendar.currentPageChanged.connect(lambda y, m: self._highlight_event_dates())
        cal_lay.addWidget(self.calendar)
        body.addWidget(cal_card, 3)

        # Events side panel
        events_card = ModernCard()
        events_card.setMinimumWidth(280)
        events_lay = QVBoxLayout(events_card)
        events_lay.setContentsMargins(18, 16, 18, 16)
        events_lay.setSpacing(12)

        ev_hdr = QHBoxLayout()
        self.lbl_events_title = QLabel("Events for Selected Date")
        self.lbl_events_title.setFont(QFont("Plus Jakarta Sans", 12, QFont.Weight.Bold))
        self.lbl_events_title.setStyleSheet("border: none; background: transparent;")
        ev_hdr.addWidget(self.lbl_events_title)
        ev_hdr.addStretch()
        events_lay.addLayout(ev_hdr)

        # Legend
        legend = QHBoxLayout()
        legend.setSpacing(8)
        for etype, color in list(_TYPE_COLORS.items())[:4]:
            dot = QLabel(f"• {etype}")
            dot.setFont(QFont("Plus Jakarta Sans", 9, QFont.Weight.Bold))
            dot.setStyleSheet(f"color: {color}; border: none; background: transparent;")
            legend.addWidget(dot)
        legend.addStretch()
        events_lay.addLayout(legend)

        self.events_scroll = QScrollArea()
        self.events_scroll.setWidgetResizable(True)
        self.events_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.events_scroll.setStyleSheet("background: transparent; border: none;")
        self.events_inner = QWidget()
        self.events_inner.setStyleSheet("background: transparent;")
        self.events_inner_lay = QVBoxLayout(self.events_inner)
        self.events_inner_lay.setContentsMargins(0, 0, 0, 0)
        self.events_inner_lay.setSpacing(8)
        self.events_inner_lay.addStretch()
        self.events_scroll.setWidget(self.events_inner)
        events_lay.addWidget(self.events_scroll)
        body.addWidget(events_card, 2)

        root.addLayout(body)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def refresh_data(self):
        self._events = self._load_events()
        self._highlight_event_dates()
        self._show_events_for_date(self.calendar.selectedDate())

    def _load_events(self) -> List[Dict[str, Any]]:
        db = get_session()
        try:
            from database.models.calendar import CalendarEvent
            rows = db.query(CalendarEvent).order_by(CalendarEvent.start_date).all()
            result = []
            for e in rows:
                sd = e.start_date
                ed = e.end_date or e.start_date
                if isinstance(sd, str):
                    try:
                        sd = datetime.date.fromisoformat(sd)
                    except ValueError:
                        sd = datetime.date.today()
                if isinstance(ed, str):
                    try:
                        ed = datetime.date.fromisoformat(ed)
                    except ValueError:
                        ed = sd
                result.append({
                    "id": e.id,
                    "title": e.title,
                    "event_type": e.event_type or "General",
                    "start_date": sd,
                    "end_date": ed,
                    "description": e.description or "",
                    "color": getattr(e, "color", None) or _TYPE_COLORS.get(e.event_type, "#3B82F6"),
                })
            return result
        except Exception as exc:
            print(f"[CalendarView] Error loading events: {exc}")
            return []
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Calendar date highlights
    # ------------------------------------------------------------------
    def _highlight_event_dates(self):
        # Reset current month formatting
        cur_year = self.calendar.yearShown()
        cur_month = self.calendar.monthShown()

        # Build day-to-color mapping
        day_colors: Dict[datetime.date, str] = {}
        for ev in self._events:
            sd = ev["start_date"]
            ed = ev["end_date"]
            col = ev["color"]
            d = sd
            one_day = datetime.timedelta(days=1)
            while d <= ed:
                day_colors[d] = col
                d += one_day

        default_fmt = QTextCharFormat()
        t = ThemeManager.tokens()
        default_fmt.setForeground(QColor(t["text_primary"]))
        default_fmt.setBackground(QColor("transparent"))

        for day in range(1, 32):
            try:
                dt = datetime.date(cur_year, cur_month, day)
                qd = QDate(cur_year, cur_month, day)
            except ValueError:
                continue

            is_sunday = (dt.weekday() == 6)

            if dt in day_colors:
                c = QColor(day_colors[dt])
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(c.red(), c.green(), c.blue(), 45))
                fmt.setForeground(c)
                fmt.setFontWeight(QFont.Weight.Bold)
                self.calendar.setDateTextFormat(qd, fmt)
            elif is_sunday:
                # Official weekly Sunday off across entire calendar
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(239, 68, 68, 25))
                fmt.setForeground(QColor("#DC2626"))
                fmt.setFontWeight(QFont.Weight.Bold)
                self.calendar.setDateTextFormat(qd, fmt)
            else:
                self.calendar.setDateTextFormat(qd, default_fmt)

    # ------------------------------------------------------------------
    # Selection change handler
    # ------------------------------------------------------------------
    def _on_date_selected(self):
        qd = self.calendar.selectedDate()
        self._show_events_for_date(qd)

    def _on_calendar_activated(self, qdate: QDate):
        sel_dt = datetime.date(qdate.year(), qdate.month(), qdate.day())
        self._open_declare_holiday_dialog(sel_dt)

    def _open_declare_holiday_dialog(self, default_date: Optional[datetime.date] = None):
        if default_date is None:
            qd = self.calendar.selectedDate()
            default_date = datetime.date(qd.year(), qd.month(), qd.day())
        dlg = DeclareHolidayDialog(self, default_date=default_date)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()

    def _show_events_for_date(self, qdate: QDate):
        sel_dt = datetime.date(qdate.year(), qdate.month(), qdate.day())
        self.lbl_events_title.setText(f"Events on {sel_dt.strftime('%d %b %Y')}")

        # Clear existing event cards
        while self.events_inner_lay.count() > 1:
            item = self.events_inner_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Find matching events
        matching = [
            ev for ev in self._events
            if ev["start_date"] <= sel_dt <= ev["end_date"]
        ]

        t = ThemeManager.tokens()
        is_sunday = (sel_dt.weekday() == 6)
        card_idx = 0

        # Quick action button at top of the date side panel
        holiday_events = [ev for ev in matching if (ev.get("event_type") or "").lower() in ["holiday", "summer vacation", "winter vacation"]]

        btn_action_box = QWidget()
        btn_act_lay = QHBoxLayout(btn_action_box)
        btn_act_lay.setContentsMargins(0, 0, 0, 4)

        if holiday_events:
            btn_quick_act = ModernButton("Reopen School / Remove Holiday", icon_name="refresh-cw", variant="secondary")
            btn_quick_act.setFixedHeight(30)
            btn_quick_act.setToolTip("Deletes the holiday declaration, returning this day to an open working day.")
            btn_quick_act.clicked.connect(lambda _, eid=holiday_events[0]["id"]: self._delete_event(eid))
            btn_act_lay.addWidget(btn_quick_act)
            self.events_inner_lay.insertWidget(card_idx, btn_action_box)
            card_idx += 1
        elif not is_sunday:
            btn_quick_act = ModernButton(f"Mark as Holiday ({sel_dt.strftime('%d %b')})", icon_name="calendar-x", variant="warning")
            btn_quick_act.setFixedHeight(30)
            btn_quick_act.setToolTip("Click to declare this date as an official holiday (govt notice, emergency, rain, etc.).")
            btn_quick_act.clicked.connect(lambda: self._open_declare_holiday_dialog(sel_dt))
            btn_act_lay.addWidget(btn_quick_act)
            self.events_inner_lay.insertWidget(card_idx, btn_action_box)
            card_idx += 1

        # If Sunday, display prominent Weekly Holiday card
        if is_sunday:
            sun_card = QFrame()
            sun_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['bg_card']};
                    border: 1px solid #FCA5A5;
                    border-left: 4px solid #DC2626;
                    border-radius: 8px;
                }}
            """)
            scl = QVBoxLayout(sun_card)
            scl.setContentsMargins(12, 10, 12, 10)
            scl.setSpacing(4)

            s_top = QHBoxLayout()
            s_title = QLabel("Sunday (Weekly Holiday)")
            s_title.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
            s_title.setStyleSheet("color: #DC2626; background: transparent; border: none;")
            s_top.addWidget(s_title, 1)

            badge = StatusBadge("Weekly Off", "error")
            s_top.addWidget(badge)
            scl.addLayout(s_top)

            s_sub = QLabel("Official institutional day off across entire school calendar.")
            s_sub.setFont(QFont("Plus Jakarta Sans", 10))
            s_sub.setWordWrap(True)
            s_sub.setStyleSheet("color: #64748B; background: transparent; border: none;")
            scl.addWidget(s_sub)

            self.events_inner_lay.insertWidget(card_idx, sun_card)
            card_idx += 1

        if not matching and not is_sunday:
            no_ev = QLabel("No other events scheduled for this date.")
            no_ev.setFont(QFont("Plus Jakarta Sans", 11))
            no_ev.setStyleSheet("color: #94A3B8; font-style: italic; border: none; background: transparent; padding: 12px 0;")
            self.events_inner_lay.insertWidget(card_idx, no_ev)
            return

        for ev in matching:
            color = ev["color"]
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {t['bg_card']};
                    border: 1px solid {t['border_color']};
                    border-left: 4px solid {color};
                    border-radius: 8px;
                }}
            """)
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(4)

            card_top = QHBoxLayout()
            title_lbl = QLabel(ev['title'])
            title_lbl.setFont(QFont("Plus Jakarta Sans", 11, QFont.Weight.Bold))
            title_lbl.setStyleSheet(f"color: {t['text_primary']}; background: transparent; border: none;")
            title_lbl.setWordWrap(True)
            card_top.addWidget(title_lbl, 1)

            btn_del = QPushButton()
            btn_del.setIcon(icon_mgr.get_icon("trash-2", color="#EF4444"))
            btn_del.setToolTip("Delete this event")
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setFixedSize(26, 26)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #FEE2E2;
                }
            """)
            btn_del.clicked.connect(lambda _, eid=ev["id"]: self._delete_event(eid))
            card_top.addWidget(btn_del)
            cl.addLayout(card_top)

            type_lbl = QLabel(ev["event_type"])
            type_lbl.setFont(QFont("Plus Jakarta Sans", 10, QFont.Weight.Bold))
            type_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
            cl.addWidget(type_lbl)

            sd = ev["start_date"]
            ed = ev["end_date"]
            if ed and ed != sd:
                date_str = f"{sd.strftime('%d %b')} – {ed.strftime('%d %b %Y')}"
            else:
                date_str = sd.strftime("%d %b %Y")
            date_lbl = QLabel(date_str)
            date_lbl.setFont(QFont("Plus Jakarta Sans", 10))
            date_lbl.setStyleSheet("color: #64748B; background: transparent; border: none;")
            cl.addWidget(date_lbl)

            if ev["description"]:
                desc_lbl = QLabel(ev["description"])
                desc_lbl.setFont(QFont("Plus Jakarta Sans", 10))
                desc_lbl.setWordWrap(True)
                desc_lbl.setStyleSheet("color: #475569; background: transparent; border: none;")
                cl.addWidget(desc_lbl)

            self.events_inner_lay.insertWidget(card_idx, card)
            card_idx += 1

    # ------------------------------------------------------------------
    # Add Event dialog
    # ------------------------------------------------------------------
    def _show_add_event_dialog(self):
        t = ThemeManager.tokens()
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Academic Event")
        dlg.setMinimumWidth(460)
        dlg.setStyleSheet(f"""
            QDialog {{
                background-color: {t['dialog_bg']};
                color: {t['text_primary']};
                font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial, sans-serif;
            }}
            QLabel {{
                color: {t['text_primary']};
                font-weight: 600;
                font-size: 13px;
            }}
            QLineEdit, QComboBox, QDateEdit, QTextEdit {{
                background-color: {t['input_bg']};
                color: {t['text_primary']};
                border: 1px solid {t['border_color']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {{
                border: 1.5px solid {t['accent']};
            }}
        """)

        form = QFormLayout(dlg)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        inp_title = QLineEdit()
        inp_title.setPlaceholderText("e.g. Winter Break, Final Exams...")

        combo_type = QComboBox()
        combo_type.addItems(_EVENT_TYPES)

        sel = self.calendar.selectedDate()
        inp_start = QDateEdit()
        inp_start.setCalendarPopup(True)
        inp_start.setDisplayFormat("yyyy-MM-dd")
        inp_start.setDate(sel)

        inp_end = QDateEdit()
        inp_end.setCalendarPopup(True)
        inp_end.setDisplayFormat("yyyy-MM-dd")
        inp_end.setDate(sel)

        inp_desc = QTextEdit()
        inp_desc.setMaximumHeight(80)
        inp_desc.setPlaceholderText("Optional description...")

        form.addRow("Title *:", inp_title)
        form.addRow("Type:", combo_type)
        form.addRow("Start Date *:", inp_start)
        form.addRow("End Date:", inp_end)
        form.addRow("Description:", inp_desc)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_save = ModernButton("Save Event", icon_name="check", variant="primary")
        btn_save.setFixedHeight(36)
        btn_save.clicked.connect(dlg.accept)

        btn_cancel = ModernButton("Cancel", variant="secondary")
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(dlg.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        form.addRow("", btn_box)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        title = inp_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation Error", "Event title cannot be empty.")
            return

        etype = combo_type.currentText()
        qs = inp_start.date()
        qe = inp_end.date()
        sdate = datetime.date(qs.year(), qs.month(), qs.day())
        edate = datetime.date(qe.year(), qe.month(), qe.day())

        if edate < sdate:
            edate = sdate

        desc = inp_desc.toPlainText().strip()
        color = _TYPE_COLORS.get(etype, "#3B82F6")

        # Persist to database
        cur_year = datetime.date.today().year
        session_name = app_state.get_setting("session", f"{cur_year}-{cur_year+1}") or f"{cur_year}-{cur_year+1}"

        db = get_session()
        try:
            from database.models.calendar import CalendarEvent
            new_event = CalendarEvent(
                academic_session=session_name,
                title=title,
                event_type=etype,
                start_date=sdate.isoformat(),
                end_date=edate.isoformat(),
                description=desc,
            )
            db.add(new_event)
            db.commit()
            app_state.notify_data_changed()
            self.refresh_data()
        except Exception as exc:
            db.rollback()
            QMessageBox.critical(self, "Save Error", f"Could not save event:\n{exc}")
            print(f"[CalendarView] Error saving event: {exc}")
        finally:
            db.close()

    def _open_gazetted_holidays_dialog(self):
        dlg = GazettedHolidaysDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()

    def _load_standard_pakistan_holidays(self):
        """Pre-populates national gazetted holidays and vacations for the active year."""
        cur_year = datetime.date.today().year
        session_name = app_state.get_setting("session", f"{cur_year}-{cur_year+1}") or f"{cur_year}-{cur_year+1}"

        standard_holidays = [
            ("Kashmir Solidarity Day", "Holiday", f"{cur_year}-02-05", f"{cur_year}-02-05", "National public holiday in solidarity with Kashmir."),
            ("Pakistan Day", "Holiday", f"{cur_year}-03-23", f"{cur_year}-03-23", "Commemoration of the Lahore Resolution."),
            ("Eid-ul-Fitr Holidays", "Holiday", f"{cur_year}-03-30", f"{cur_year}-04-01", "Official Eid-ul-Fitr public holidays."),
            ("Labour Day", "Holiday", f"{cur_year}-05-01", f"{cur_year}-05-01", "International Workers' Day."),
            ("Summer Vacations", "Summer Vacation", f"{cur_year}-06-01", f"{cur_year}-08-14", "Annual school summer vacation."),
            ("Eid-ul-Adha Holidays", "Holiday", f"{cur_year}-06-06", f"{cur_year}-06-08", "Feast of the Sacrifice public holidays."),
            ("Ashura (9th & 10th Moharram)", "Holiday", f"{cur_year}-07-06", f"{cur_year}-07-07", "Martyrdom of Hazrat Imam Hussain (R.A)."),
            ("Independence Day", "Holiday", f"{cur_year}-08-14", f"{cur_year}-08-14", "National Independence Day of Pakistan."),
            ("Eid Milad-un-Nabi", "Holiday", f"{cur_year}-09-05", f"{cur_year}-09-05", "Birthday of Prophet Muhammad (PBUH)."),
            ("Iqbal Day", "Holiday", f"{cur_year}-11-09", f"{cur_year}-11-09", "Birth anniversary of Allama Muhammad Iqbal."),
            ("Quaid-e-Azam Day / Christmas", "Holiday", f"{cur_year}-12-25", f"{cur_year}-12-25", "Birth anniversary of Quaid-e-Azam Muhammad Ali Jinnah and Christmas."),
            ("Winter Vacations", "Winter Vacation", f"{cur_year}-12-24", f"{cur_year}-12-31", "Annual school winter break.")
        ]

        db = get_session()
        added_count = 0
        try:
            from database.models.calendar import CalendarEvent
            for title, etype, sdate, edate, desc in standard_holidays:
                exists = db.query(CalendarEvent).filter(
                    CalendarEvent.title == title,
                    CalendarEvent.start_date == sdate
                ).first()
                if not exists:
                    ev = CalendarEvent(
                        academic_session=session_name,
                        title=title,
                        event_type=etype,
                        start_date=sdate,
                        end_date=edate,
                        description=desc
                    )
                    db.add(ev)
                    added_count += 1
            db.commit()
            app_state.notify_data_changed()
            self.refresh_data()
            QMessageBox.information(
                self,
                "Gazetted Holidays Loaded",
                f"Successfully synced {added_count} standard gazetted holidays and vacation periods for {cur_year} into the Academic Calendar!"
            )
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to load holidays: {e}")
        finally:
            db.close()

    def _delete_event(self, event_id):
        """Allows deleting an event from the calendar."""
        reply = QMessageBox.question(
            self,
            "Delete Event",
            "Are you sure you want to remove this event from the academic calendar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            db = get_session()
            try:
                from database.models.calendar import CalendarEvent
                ev = db.query(CalendarEvent).filter_by(id=event_id).first()
                if ev:
                    db.delete(ev)
                    db.commit()
                    app_state.notify_data_changed()
                    self.refresh_data()
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Error", f"Could not delete event: {e}")
            finally:
                db.close()
