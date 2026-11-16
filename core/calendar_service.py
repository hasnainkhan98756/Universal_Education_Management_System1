from __future__ import annotations

import datetime
from typing import List, Dict, Any, Optional
from database.connection import get_session
from database.models.calendar import CalendarEvent
from core.state_manager import app_state

class CalendarService:
    """
    Centralized service for managing institutional academic calendar events,
    worldwide gazetted public holidays, Sunday off-days, and attendance linkage.
    """

    # -------------------------------------------------------------------------
    # SUNDAY & HOLIDAY EVALUATION
    # -------------------------------------------------------------------------
    @staticmethod
    def is_sunday(target_date: datetime.date | str) -> bool:
        """Checks if a given date string (YYYY-MM-DD) or date object is a Sunday."""
        if isinstance(target_date, str):
            try:
                target_date = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
            except Exception:
                return False
        return target_date.weekday() == 6

    @staticmethod
    def get_holiday_or_event(date_str: str | datetime.date, session_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Checks if a given date falls on a Gazetted Holiday, Vacation, School Closure, or Sunday.
        Returns a dict describing the off-day / holiday event, or None if it's a regular open day.
        """
        if isinstance(date_str, datetime.date):
            d_obj = date_str
            d_str = date_str.strftime("%Y-%m-%d")
        else:
            d_str = str(date_str).strip()
            try:
                d_obj = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
            except Exception:
                d_obj = None

        db = get_session()
        try:
            # 1. First check if there is an explicit CalendarEvent in the database
            events = db.query(CalendarEvent).filter(
                (CalendarEvent.start_date <= d_str) &
                (CalendarEvent.end_date >= d_str)
            ).all()

            matching_events = []
            for ev in events:
                etype = (ev.event_type or "").lower()
                # Check for explicit Working/Open Day override if institution decided to open
                if any(k in etype for k in ["working day", "open day", "regular day"]):
                    return None

                if any(k in etype for k in ["holiday", "vacation", "closure", "gazetted", "break"]):
                    matching_events.append(ev)

            if matching_events:
                # Prioritize specific holiday over long vacation block
                matching_events.sort(key=lambda e: 0 if "holiday" in (e.event_type or "").lower() else 1)
                best_ev = matching_events[0]
                combined_title = " & ".join(dict.fromkeys(e.title for e in matching_events))
                return {
                    "id": best_ev.id,
                    "title": combined_title,
                    "event_type": best_ev.event_type or "Holiday",
                    "start_date": best_ev.start_date,
                    "end_date": best_ev.end_date,
                    "description": best_ev.description or "",
                    "is_sunday": False,
                    "can_override": True
                }

            # 2. Check if the day is Sunday (Global Institutional Off-Day)
            if d_obj and d_obj.weekday() == 6:
                return {
                    "id": None,
                    "title": "Sunday (Weekly Holiday)",
                    "event_type": "Weekly Off",
                    "start_date": d_str,
                    "end_date": d_str,
                    "description": "Weekly institution off-day across the entire school calendar.",
                    "is_sunday": True,
                    "can_override": True
                }

            return None
        except Exception as e:
            print(f"[CalendarService] Error checking holiday for {date_str}: {e}")
            if d_obj and d_obj.weekday() == 6:
                return {
                    "id": None,
                    "title": "Sunday (Weekly Holiday)",
                    "event_type": "Weekly Off",
                    "start_date": d_str,
                    "end_date": d_str,
                    "description": "Weekly institution off-day.",
                    "is_sunday": True,
                    "can_override": True
                }
            return None
        finally:
            db.close()

    # -------------------------------------------------------------------------
    # CALENDAR EVENT PERSISTENCE
    # -------------------------------------------------------------------------
    @staticmethod
    def get_all_events(session_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches all stored calendar events ordered by start date."""
        db = get_session()
        try:
            q = db.query(CalendarEvent)
            if session_name and session_name not in ["All", "Default", ""]:
                q = q.filter(CalendarEvent.academic_session == session_name)
            rows = q.order_by(CalendarEvent.start_date).all()
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
                })
            return result
        finally:
            db.close()

    @staticmethod
    def add_event(title: str, event_type: str, start_date: str, end_date: str, description: str = "", session_name: Optional[str] = None) -> tuple[bool, str]:
        """Creates a new calendar event and notifies the global state."""
        if not session_name:
            cur_y = datetime.date.today().year
            session_name = app_state.get_setting("session", f"{cur_y}-{cur_y+1}") or f"{cur_y}-{cur_y+1}"

        db = get_session()
        try:
            new_event = CalendarEvent(
                academic_session=session_name,
                title=title.strip(),
                event_type=event_type,
                start_date=start_date,
                end_date=end_date or start_date,
                description=description.strip()
            )
            db.add(new_event)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as ex:
                print(f"Error broadcasting after adding calendar event: {ex}")
            return True, "Event added successfully to the Academic Calendar."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def delete_event(event_id: int) -> tuple[bool, str]:
        """Deletes a calendar event by ID and broadcasts updates."""
        db = get_session()
        try:
            ev = db.query(CalendarEvent).filter_by(id=event_id).first()
            if not ev:
                return False, "Event not found."
            db.delete(ev)
            db.commit()
            try:
                app_state.notify_data_changed()
            except Exception as ex:
                print(f"Error broadcasting after deleting calendar event: {ex}")
            return True, "Event deleted successfully."
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    @staticmethod
    def load_gazetted_holidays(holiday_tuples: List[tuple], session_name: Optional[str] = None) -> tuple[bool, int, str]:
        """
        Loads a list of (title, event_type, start_date, end_date, description) tuples into CalendarEvent.
        Avoids duplicates and notifies all views live.
        """
        if not session_name:
            cur_y = datetime.date.today().year
            session_name = app_state.get_setting("session", f"{cur_y}-{cur_y+1}") or f"{cur_y}-{cur_y+1}"

        db = get_session()
        added_count = 0
        try:
            for title, etype, sdate, edate, desc in holiday_tuples:
                existing = db.query(CalendarEvent).filter(
                    CalendarEvent.title == title,
                    CalendarEvent.start_date == sdate
                ).first()
                if not existing:
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
            try:
                app_state.notify_data_changed()
            except Exception as ex:
                print(f"Error broadcasting after loading gazetted holidays: {ex}")
            return True, added_count, f"Successfully loaded {added_count} gazetted holiday(s)."
        except Exception as e:
            db.rollback()
            return False, 0, f"Failed to load holidays: {str(e)}"
        finally:
            db.close()

    # -------------------------------------------------------------------------
    # WORLDWIDE GAZETTED PUBLIC HOLIDAY DATASETS
    # -------------------------------------------------------------------------
    @staticmethod
    def get_supported_countries() -> List[tuple]:
        """Available country calendars for the Gazetted Holidays loader."""
        return [
            ("pk", "Pakistan (Official Gazetted Holidays & Vacations)"),
            ("islamic", "Islamic / Hijri Religious Holidays (Universal)"),
            ("us", "United States (Federal Public Holidays)"),
            ("uk", "United Kingdom (National Bank Holidays)"),
            ("in", "India (National Gazetted Holidays)"),
            ("sa", "Saudi Arabia (Official Public Holidays)"),
            ("ae", "United Arab Emirates (UAE Public Holidays)"),
            ("intl", "International / Academic (UN & Global Education Days)")
        ]

    @staticmethod
    def get_gazetted_holidays_for_country(country_code: str, year: int) -> List[tuple]:
        """
        Generates official gazetted holidays for a specific country and year.
        Each item is a tuple: (Title, Event Type, Start Date, End Date, Description).
        """
        y = int(year)
        
        # Approximate shifts for lunar Islamic holidays (relative to 2026 anchor)
        # 2026: Eid-ul-Fitr ~ Mar 20, Eid-ul-Adha ~ May 27, Ashura ~ Jun 25, Milad ~ Aug 25
        # Lunar year is ~10.87 days shorter than solar year
        delta_years = y - 2026
        lunar_shift_days = int(delta_years * -10.875)

        def _shift_lunar(base_m: int, base_d: int, length_days: int = 1):
            try:
                base_dt = datetime.date(2026, base_m, base_d) + datetime.timedelta(days=lunar_shift_days + (delta_years * 365))
                end_dt = base_dt + datetime.timedelta(days=length_days - 1)
                return base_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
            except Exception:
                return f"{y}-{base_m:02d}-{base_d:02d}", f"{y}-{base_m:02d}-{base_d:02d}"

        # 1. PAKISTAN
        if country_code == "pk":
            fitr_s, fitr_e = _shift_lunar(3, 20, 3)
            adha_s, adha_e = _shift_lunar(5, 27, 3)
            ashura_s, ashura_e = _shift_lunar(6, 25, 2)
            milad_s, milad_e = _shift_lunar(8, 25, 1)

            return [
                ("Kashmir Solidarity Day", "Holiday", f"{y}-02-05", f"{y}-02-05", "National public holiday in solidarity with Kashmir."),
                ("Pakistan Day", "Holiday", f"{y}-03-23", f"{y}-03-23", "Commemoration of the historic 1940 Lahore Resolution."),
                ("Eid-ul-Fitr Holidays", "Holiday", fitr_s, fitr_e, "Official 3-day Eid-ul-Fitr public holidays."),
                ("Labour Day", "Holiday", f"{y}-05-01", f"{y}-05-01", "International Workers' Day public holiday."),
                ("Eid-ul-Adha Holidays", "Holiday", adha_s, adha_e, "Official 3-day Feast of the Sacrifice public holidays."),
                ("Summer Vacations", "Summer Vacation", f"{y}-06-01", f"{y}-08-14", "Official institutional summer vacation break."),
                ("Ashura (9th & 10th Muharram)", "Holiday", ashura_s, ashura_e, "Martyrdom of Hazrat Imam Hussain (R.A)."),
                ("Independence Day of Pakistan", "Holiday", f"{y}-08-14", f"{y}-08-14", "National Independence Day of Pakistan (14th August)."),
                ("Eid Milad-un-Nabi", "Holiday", milad_s, milad_e, "12 Rabi-ul-Awwal — Birth anniversary of Prophet Muhammad (PBUH)."),
                ("Iqbal Day", "Holiday", f"{y}-11-09", f"{y}-11-09", "Birth anniversary of Allama Muhammad Iqbal, national poet of Pakistan."),
                ("Quaid-e-Azam Day / Christmas", "Holiday", f"{y}-12-25", f"{y}-12-25", "Birth anniversary of Quaid-e-Azam Muhammad Ali Jinnah and Christmas."),
                ("Winter Vacations", "Winter Vacation", f"{y}-12-24", f"{y}-12-31", "Official institutional winter vacation break.")
            ]

        # 2. ISLAMIC RELIGIOUS HOLIDAYS (UNIVERSAL)
        elif country_code == "islamic":
            fitr_s, fitr_e = _shift_lunar(3, 20, 3)
            adha_s, adha_e = _shift_lunar(5, 27, 3)
            arafah_s, arafah_e = _shift_lunar(5, 26, 1)
            ashura_s, ashura_e = _shift_lunar(6, 25, 2)
            milad_s, milad_e = _shift_lunar(8, 25, 1)
            hijri_new_s, hijri_new_e = _shift_lunar(6, 16, 1)
            miraj_s, miraj_e = _shift_lunar(1, 16, 1)
            barat_s, barat_e = _shift_lunar(2, 3, 1)

            return [
                ("Shab-e-Miraj (The Night Journey)", "Holiday", miraj_s, miraj_e, "27 Rajab — The miraculous ascension of Prophet Muhammad (PBUH)."),
                ("Shab-e-Barat (Night of Forgiveness)", "Holiday", barat_s, barat_e, "15 Sha'ban — Night of salvation and prayers."),
                ("Eid-ul-Fitr Celebrations", "Holiday", fitr_s, fitr_e, "1st to 3rd Shawwal — Islamic festival following Ramadan."),
                ("Day of Arafah (Hajj Day)", "Holiday", arafah_s, arafah_e, "9th Dhul-Hijjah — The climactic day of the Hajj pilgrimage."),
                ("Eid-ul-Adha Celebrations", "Holiday", adha_s, adha_e, "10th to 12th Dhul-Hijjah — Feast of sacrifice honoring Prophet Ibrahim (A.S)."),
                ("Islamic New Year (1st Muharram)", "Holiday", hijri_new_s, hijri_new_e, "First day of the new Hijri lunar calendar."),
                ("Ashura (10th Muharram)", "Holiday", ashura_s, ashura_e, "Sacred observance of the martyrdom of Imam Hussain (R.A)."),
                ("Eid Milad-un-Nabi", "Holiday", milad_s, milad_e, "12th Rabi-al-Awwal — Mawlid an-Nabi celebration.")
            ]

        # 3. UNITED STATES
        elif country_code == "us":
            def _nth_weekday(year: int, month: int, weekday: int, n: int):
                first = datetime.date(year, month, 1)
                offset = (weekday - first.weekday()) % 7
                target = first + datetime.timedelta(days=offset + (n - 1) * 7)
                return target.strftime("%Y-%m-%d")

            def _last_weekday(year: int, month: int, weekday: int):
                if month == 12:
                    next_month = datetime.date(year + 1, 1, 1)
                else:
                    next_month = datetime.date(year, month + 1, 1)
                last_day = next_month - datetime.timedelta(days=1)
                offset = (last_day.weekday() - weekday) % 7
                return (last_day - datetime.timedelta(days=offset)).strftime("%Y-%m-%d")

            mlk = _nth_weekday(y, 1, 0, 3)     # 3rd Mon Jan
            pres = _nth_weekday(y, 2, 0, 3)    # 3rd Mon Feb
            mem = _last_weekday(y, 5, 0)       # Last Mon May
            labor = _nth_weekday(y, 9, 0, 1)   # 1st Mon Sep
            columb = _nth_weekday(y, 10, 0, 2) # 2nd Mon Oct
            thx = _nth_weekday(y, 11, 3, 4)    # 4th Thu Nov

            return [
                ("New Year's Day", "Holiday", f"{y}-01-01", f"{y}-01-01", "Federal public holiday celebrating the first day of the year."),
                ("Martin Luther King Jr. Day", "Holiday", mlk, mlk, "Honoring civil rights leader Dr. Martin Luther King Jr."),
                ("Presidents' Day (Washington's Birthday)", "Holiday", pres, pres, "Honoring all US presidents including George Washington."),
                ("Memorial Day", "Holiday", mem, mem, "Honoring fallen US military personnel."),
                ("Juneteenth National Independence Day", "Holiday", f"{y}-06-19", f"{y}-06-19", "Commemorating the emancipation of enslaved African Americans."),
                ("Independence Day", "Holiday", f"{y}-07-04", f"{y}-07-04", "Commemorating the Declaration of Independence (4th July)."),
                ("Labor Day", "Holiday", labor, labor, "Honoring the American labor movement and contributions of workers."),
                ("Columbus Day / Indigenous Peoples' Day", "Holiday", columb, columb, "Federal holiday honoring cultural heritage."),
                ("Veterans Day", "Holiday", f"{y}-11-11", f"{y}-11-11", "Honoring all military veterans who served in the US Armed Forces."),
                ("Thanksgiving Day", "Holiday", thx, thx, "National day of giving thanks for the harvest and preceding year."),
                ("Christmas Day", "Holiday", f"{y}-12-25", f"{y}-12-25", "Christian holiday celebrating the birth of Jesus Christ.")
            ]

        # 4. UNITED KINGDOM
        elif country_code == "uk":
            # Early May Bank Holiday (1st Mon) & Spring Bank Holiday (Last Mon)
            def _first_mon(month: int):
                f = datetime.date(y, month, 1)
                return (f + datetime.timedelta(days=(0 - f.weekday()) % 7)).strftime("%Y-%m-%d")

            def _last_mon(month: int):
                nxt = datetime.date(y, month + 1, 1) if month < 12 else datetime.date(y + 1, 1, 1)
                last = nxt - datetime.timedelta(days=1)
                return (last - datetime.timedelta(days=(last.weekday() - 0) % 7)).strftime("%Y-%m-%d")

            may1 = _first_mon(5)
            may_late = _last_mon(5)
            aug_late = _last_mon(8)

            return [
                ("New Year's Day", "Holiday", f"{y}-01-01", f"{y}-01-01", "Official UK Bank Holiday celebrating the New Year."),
                ("Good Friday", "Holiday", f"{y}-04-03", f"{y}-04-03", "Christian holiday commemorating the crucifixion of Jesus Christ."),
                ("Easter Monday", "Holiday", f"{y}-04-06", f"{y}-04-06", "Official UK Bank Holiday following Easter Sunday."),
                ("Early May Bank Holiday", "Holiday", may1, may1, "May Day public bank holiday."),
                ("Spring Bank Holiday", "Holiday", may_late, may_late, "Official Spring late May bank holiday."),
                ("Summer Bank Holiday", "Holiday", aug_late, aug_late, "Late summer bank holiday across England and Wales."),
                ("Christmas Day", "Holiday", f"{y}-12-25", f"{y}-12-25", "National public holiday celebrating Christmas."),
                ("Boxing Day", "Holiday", f"{y}-12-26", f"{y}-12-26", "UK public holiday following Christmas Day.")
            ]

        # 5. INDIA
        elif country_code == "in":
            fitr_s, _ = _shift_lunar(3, 20, 1)
            adha_s, _ = _shift_lunar(5, 27, 1)
            return [
                ("Republic Day", "Holiday", f"{y}-01-26", f"{y}-01-26", "Honoring the date on which the Constitution of India came into effect."),
                ("Holi (Festival of Colours)", "Holiday", f"{y}-03-04", f"{y}-03-04", "Celebration of spring, love, and new life."),
                ("Eid-ul-Fitr", "Holiday", fitr_s, fitr_s, "Islamic gazetted holiday celebrating the conclusion of Ramadan."),
                ("Independence Day", "Holiday", f"{y}-08-15", f"{y}-08-15", "Commemorating national independence from British rule in 1947."),
                ("Eid-ul-Adha (Bakrid)", "Holiday", adha_s, adha_s, "Islamic gazetted holiday honoring the sacrifice of Prophet Ibrahim."),
                ("Mahatma Gandhi Jayanti", "Holiday", f"{y}-10-02", f"{y}-10-02", "National holiday commemorating the birth of Mahatma Gandhi."),
                ("Dussehra (Vijayadashami)", "Holiday", f"{y}-10-20", f"{y}-10-20", "Celebration of the victory of good over evil."),
                ("Diwali (Deepavali)", "Holiday", f"{y}-11-08", f"{y}-11-08", "Festival of lights celebrated across India."),
                ("Christmas Day", "Holiday", f"{y}-12-25", f"{y}-12-25", "Gazetted holiday celebrating Christmas.")
            ]

        # 6. SAUDI ARABIA
        elif country_code == "sa":
            fitr_s, fitr_e = _shift_lunar(3, 19, 4)
            adha_s, adha_e = _shift_lunar(5, 26, 4)
            return [
                ("Saudi Founding Day", "Holiday", f"{y}-02-22", f"{y}-02-22", "Commemorating the founding of the First Saudi State in 1727."),
                ("Saudi Flag Day", "Holiday", f"{y}-03-11", f"{y}-03-11", "Annual national celebration of the Saudi National Flag."),
                ("Eid-ul-Fitr Public Holidays", "Holiday", fitr_s, fitr_e, "Official 4-day nationwide Eid-ul-Fitr holiday in Saudi Arabia."),
                ("Arafah & Eid-ul-Adha Holidays", "Holiday", adha_s, adha_e, "Official 4-day Arafah and Eid-ul-Adha national holiday."),
                ("Summer School Vacation", "Summer Vacation", f"{y}-06-15", f"{y}-08-15", "Annual Kingdom-wide school summer vacation period."),
                ("Saudi National Day", "Holiday", f"{y}-09-23", f"{y}-09-23", "Commemorating the unification of the Kingdom of Saudi Arabia."),
                ("Mid-Year Academic Break", "Winter Vacation", f"{y}-12-25", f"{y}-12-31", "Mid-year academic school break across the Kingdom.")
            ]

        # 7. UNITED ARAB EMIRATES
        elif country_code == "ae":
            fitr_s, fitr_e = _shift_lunar(3, 19, 4)
            adha_s, adha_e = _shift_lunar(5, 26, 4)
            hijri_s, hijri_e = _shift_lunar(6, 16, 1)
            milad_s, milad_e = _shift_lunar(8, 25, 1)
            return [
                ("New Year's Day", "Holiday", f"{y}-01-01", f"{y}-01-01", "Official federal holiday for New Year."),
                ("Eid-ul-Fitr Public Holidays", "Holiday", fitr_s, fitr_e, "Official multi-day Eid-ul-Fitr UAE national holiday."),
                ("Arafah & Eid-ul-Adha Holidays", "Holiday", adha_s, adha_e, "Official 4-day public and private sector UAE holiday."),
                ("Islamic New Year", "Holiday", hijri_s, hijri_e, "Official public holiday celebrating the Hijri New Year."),
                ("Prophet Muhammad's Birthday", "Holiday", milad_s, milad_e, "National holiday for 12 Rabi-al-Awwal."),
                ("Commemoration Day", "Holiday", f"{y}-12-01", f"{y}-12-01", "Honoring the sacrifices of UAE martyrs."),
                ("UAE National Day Celebrations", "Holiday", f"{y}-12-02", f"{y}-12-03", "Celebration of the union of the seven emirates in 1971.")
            ]

        # 8. INTERNATIONAL / ACADEMIC
        else:
            return [
                ("International Day of Education", "Event", f"{y}-01-24", f"{y}-01-24", "UN observance celebrating the role of education for peace and development."),
                ("International Mother Language Day", "Event", f"{y}-02-21", f"{y}-02-21", "Promoting linguistic and cultural diversity and multilingualism."),
                ("World Book and Copyright Day", "Event", f"{y}-04-23", f"{y}-04-23", "Promoting reading, publishing, and copyright awareness in schools."),
                ("International Workers' Day", "Holiday", f"{y}-05-01", f"{y}-05-01", "Worldwide celebration of the labor movement."),
                ("World Environment Day", "Event", f"{y}-06-05", f"{y}-06-05", "Encouraging institutional awareness and action for the protection of the environment."),
                ("International Youth Day", "Event", f"{y}-08-12", f"{y}-08-12", "Commemorating youth achievements and engagement in schools."),
                ("International Literacy Day", "Event", f"{y}-09-08", f"{y}-09-08", "Highlighting the importance of literacy to individuals, communities, and societies."),
                ("World Teachers' Day", "Event", f"{y}-10-05", f"{y}-10-05", "Celebrating the vital contribution of teachers and educators worldwide."),
                ("Universal Children's Day", "Event", f"{y}-11-20", f"{y}-11-20", "Promoting international togetherness and awareness among children."),
                ("Human Rights Day", "Event", f"{y}-12-10", f"{y}-12-10", "Commemorating the adoption of the Universal Declaration of Human Rights.")
            ]
