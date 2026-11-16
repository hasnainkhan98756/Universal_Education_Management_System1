"""
core/icon_manager.py
====================
Centralized Professional Vector Icon Engine for School Management System.
Renders 100% vector SVG icons directly using PySide6.QtSvg.
Zero emojis used.
Provides consistent, crisp Lucide-family icons matching Google Stitch visual design.
"""

from typing import Dict, Optional
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt, QByteArray, QSize
from PySide6.QtSvg import QSvgRenderer

# ---------------------------------------------------------------------------
# Lucide SVG Paths (24x24 viewBox, stroke-width=2, round caps & joins)
# ---------------------------------------------------------------------------
LUCIDE_SVG_PATHS: Dict[str, str] = {
    # Navigation & Core
    "layout-dashboard": (
        '<rect width="7" height="9" x="3" y="3" rx="1"/>'
        '<rect width="7" height="5" x="14" y="3" rx="1"/>'
        '<rect width="7" height="9" x="14" y="12" rx="1"/>'
        '<rect width="7" height="5" x="3" y="16" rx="1"/>'
    ),
    "dashboard": (
        '<rect width="7" height="9" x="3" y="3" rx="1"/>'
        '<rect width="7" height="5" x="14" y="3" rx="1"/>'
        '<rect width="7" height="9" x="14" y="12" rx="1"/>'
        '<rect width="7" height="5" x="3" y="16" rx="1"/>'
    ),
    "school": (
        '<path d="m4 6 8-4 8 4"/>'
        '<path d="m18 10 4 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8l4-2"/>'
        '<path d="M14 22v-4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v4"/>'
        '<path d="M18 5v17"/><path d="M6 5v17"/><circle cx="12" cy="9" r="2"/>'
    ),
    "classes": (
        '<path d="m4 6 8-4 8 4"/>'
        '<path d="m18 10 4 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8l4-2"/>'
        '<path d="M14 22v-4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v4"/>'
        '<path d="M18 5v17"/><path d="M6 5v17"/><circle cx="12" cy="9" r="2"/>'
    ),
    "users-2": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "teachers": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
        '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
    ),
    "user-check": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<polyline points="16 11 18 13 22 9"/>'
    ),
    "students": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<polyline points="16 11 18 13 22 9"/>'
    ),
    "calendar-check": (
        '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
        '<line x1="16" x2="16" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="2" y2="6"/>'
        '<line x1="3" x2="21" y1="10" y2="10"/>'
        '<path d="m9 16 2 2 4-4"/>'
    ),
    "attendance": (
        '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
        '<line x1="16" x2="16" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="2" y2="6"/>'
        '<line x1="3" x2="21" y1="10" y2="10"/>'
        '<path d="m9 16 2 2 4-4"/>'
    ),
    "bus": (
        '<path d="M8 6v6"/><path d="M16 6v6"/><path d="M2 12h20"/><path d="M4 18h16"/>'
        '<path d="M3 6h18a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a1 1 0 0 1 1-1Z"/>'
        '<circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>'
    ),
    "transport": (
        '<path d="M8 6v6"/><path d="M16 6v6"/><path d="M2 12h20"/><path d="M4 18h16"/>'
        '<path d="M3 6h18a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a1 1 0 0 1 1-1Z"/>'
        '<circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>'
    ),
    "book-open": (
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    "library": (
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
    ),
    "coins": (
        '<circle cx="8" cy="8" r="6"/>'
        '<path d="M18.09 10.37A6 6 0 1 1 10.34 18"/>'
        '<path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>'
    ),
    "fee": (
        '<circle cx="8" cy="8" r="6"/>'
        '<path d="M18.09 10.37A6 6 0 1 1 10.34 18"/>'
        '<path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>'
    ),
    "calendar-days": (
        '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
        '<line x1="16" x2="16" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="2" y2="6"/>'
        '<line x1="3" x2="21" y1="10" y2="10"/>'
        '<path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/>'
        '<path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>'
    ),
    "calendar": (
        '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
        '<line x1="16" x2="16" y1="2" y2="6"/>'
        '<line x1="8" x2="8" y1="2" y2="6"/>'
        '<line x1="3" x2="21" y1="10" y2="10"/>'
        '<path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/>'
        '<path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>'
    ),
    "table": (
        '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/>'
        '<path d="M3 9h18"/><path d="M3 15h18"/>'
    ),
    "timetable": (
        '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/>'
        '<path d="M3 9h18"/><path d="M3 15h18"/>'
    ),
    "mail": (
        '<rect width="20" height="16" x="2" y="4" rx="2"/>'
        '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>'
    ),
    "messages": (
        '<rect width="20" height="16" x="2" y="4" rx="2"/>'
        '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>'
    ),
    "bar-chart-2": (
        '<line x1="18" x2="18" y1="20" y2="10"/>'
        '<line x1="12" x2="12" y1="20" y2="4"/>'
        '<line x1="6" x2="6" y1="20" y2="14"/>'
    ),
    "analytics": (
        '<line x1="18" x2="18" y1="20" y2="10"/>'
        '<line x1="12" x2="12" y1="20" y2="4"/>'
        '<line x1="6" x2="6" y1="20" y2="14"/>'
    ),
    "settings": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "log-out": (
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '<polyline points="16 17 21 12 16 7"/>'
        '<line x1="21" x2="9" y1="12" y2="12"/>'
    ),
    "logout": (
        '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
        '<polyline points="16 17 21 12 16 7"/>'
        '<line x1="21" x2="9" y1="12" y2="12"/>'
    ),
    "package": (
        '<path d="m7.5 4.27 9 5.15"/>'
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
        '<path d="m3.3 7 8.7 5 8.7-5"/>'
        '<path d="M12 22V12"/>'
    ),
    "inventory": (
        '<path d="m7.5 4.27 9 5.15"/>'
        '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'
        '<path d="m3.3 7 8.7 5 8.7-5"/>'
        '<path d="M12 22V12"/>'
    ),
    "file-text": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'
    ),
    "examinations": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'
    ),
    "folder": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
    ),
    "documents": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
    ),

    # Header & UI Actions
    "graduation-cap": (
        '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/>'
        '<path d="M6 12v5c3 3 9 3 12 0v-5"/>'
    ),
    "bell": (
        '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>'
        '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'
    ),
    "clock": (
        '<circle cx="12" cy="12" r="10"/>'
        '<polyline points="12 6 12 12 16 14"/>'
    ),
    "user": (
        '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>'
        '<circle cx="12" cy="7" r="4"/>'
    ),
    "chevron-down": (
        '<polyline points="6 9 12 15 18 9"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="8"/>'
        '<line x1="21" x2="16.65" y1="21" y2="16.65"/>'
    ),
    "menu": (
        '<line x1="4" x2="20" y1="12" y2="12"/>'
        '<line x1="4" x2="20" y1="6" y2="6"/>'
        '<line x1="4" x2="20" y1="18" y2="18"/>'
    ),
    "home": (
        '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
        '<polyline points="9 22 9 12 15 12 15 22"/>'
    ),

    # Financial & KPI Cards
    "wallet": (
        '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/>'
        '<path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>'
    ),
    "eye": (
        '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "eye-off": (
        '<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>'
        '<path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>'
        '<path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>'
        '<line x1="2" x2="22" y1="2" y2="22"/>'
    ),
    "shield-alert": (
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        '<line x1="12" x2="12" y1="8" y2="12"/>'
        '<line x1="12" x2="12.01" y1="16" y2="16"/>'
    ),
    "credit-card": (
        '<rect width="20" height="14" x="2" y="5" rx="2"/>'
        '<line x1="2" x2="22" y1="10" y2="10"/>'
    ),
    "receipt": (
        '<path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/>'
        '<path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>'
        '<path d="M12 17.5v-11"/>'
    ),
    "arrow-up-right": (
        '<line x1="7" x2="17" y1="17" y2="7"/>'
        '<polyline points="7 7 17 7 17 17"/>'
    ),
    "arrow-right": (
        '<line x1="5" x2="19" y1="12" y2="12"/>'
        '<polyline points="12 5 19 12 12 19"/>'
    ),
    "check-circle": (
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
        '<polyline points="22 4 12 14.01 9 11.01"/>'
    ),
    "user-x": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<line x1="17" x2="21" y1="8" y2="12"/>'
        '<line x1="21" x2="17" y1="8" y2="12"/>'
    ),
    "user-plus": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<line x1="19" x2="19" y1="8" y2="14"/>'
        '<line x1="22" x2="16" y1="11" y2="11"/>'
    ),
    "send": (
        '<path d="m22 2-7 20-4-9-9-4Z"/>'
        '<path d="M22 2 11 13"/>'
    ),
    "pie-chart": (
        '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>'
        '<path d="M22 12A10 10 0 0 0 12 2v10z"/>'
    ),
    "zap": (
        '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'
    ),
    "list-ordered": (
        '<line x1="10" x2="21" y1="6" y2="6"/>'
        '<line x1="10" x2="21" y1="12" y2="12"/>'
        '<line x1="10" x2="21" y1="18" y2="18"/>'
        '<path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/>'
    ),
    "refresh": (
        '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<path d="M3 3v5h5"/>'
        '<path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>'
        '<path d="M16 21h5v-5"/>'
    ),
    "rotate-cw": (
        '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<path d="M3 3v5h5"/>'
        '<path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>'
        '<path d="M16 21h5v-5"/>'
    ),
    "plus": (
        '<path d="M5 12h14"/><path d="M12 5v14"/>'
    ),
    "pencil": (
        '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>'
        '<path d="m15 5 4 4"/>'
    ),
    "trash-2": (
        '<path d="M3 6h18"/>'
        '<path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>'
        '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>'
        '<line x1="10" x2="10" y1="11" y2="17"/>'
        '<line x1="14" x2="14" y1="11" y2="17"/>'
    ),
    "filter": (
        '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>'
    ),
    "download": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" x2="12" y1="15" y2="3"/>'
    ),
    "upload": (
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="17 8 12 3 7 8"/>'
        '<line x1="12" x2="12" y1="3" y2="15"/>'
    ),
    "printer": (
        '<polyline points="6 9 6 2 18 2 18 9"/>'
        '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
        '<rect width="12" height="8" x="6" y="14"/>'
    ),
    "arrow-left": (
        '<line x1="19" x2="5" y1="12" y2="12"/>'
        '<polyline points="12 19 5 12 12 5"/>'
    ),
    "save": (
        '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
        '<polyline points="17 21 17 13 7 13 7 21"/>'
        '<polyline points="7 3 7 8 15 8"/>'
    ),
    "x": (
        '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
    ),
    "check": (
        '<polyline points="20 6 9 17 4 12"/>'
    ),
    "alert-triangle": (
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<line x1="12" x2="12" y1="9" y2="13"/>'
        '<line x1="12" x2="12.01" y1="17" y2="17"/>'
    ),
    "info": (
        '<circle cx="12" cy="12" r="10"/>'
        '<line x1="12" x2="12" y1="16" y2="12"/>'
        '<line x1="12" x2="12.01" y1="8" y2="8"/>'
    ),
    "copy": (
        '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>'
        '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>'
    ),
    "external-link": (
        '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
        '<polyline points="15 3 21 3 21 9"/>'
        '<line x1="10" x2="21" y1="14" y2="3"/>'
    ),
    "award": (
        '<circle cx="12" cy="8" r="7"/>'
        '<polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>'
    ),
    "phone": (
        '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>'
    ),
    "lock": (
        '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>'
        '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'
    ),
    "database": (
        '<ellipse cx="12" cy="5" rx="9" ry="3"/>'
        '<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>'
        '<path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>'
    ),
    "file-spreadsheet": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/><path d="M14 17h2"/>'
    ),
    "sliders": (
        '<line x1="4" x2="4" y1="21" y2="14"/>'
        '<line x1="4" x2="4" y1="10" y2="3"/>'
        '<line x1="12" x2="12" y1="21" y2="12"/>'
        '<line x1="12" x2="12" y1="8" y2="3"/>'
        '<line x1="20" x2="20" y1="21" y2="16"/>'
        '<line x1="20" x2="20" y1="12" y2="3"/>'
        '<line x1="1" x2="7" y1="14" y2="14"/>'
        '<line x1="9" x2="15" y1="8" y2="8"/>'
        '<line x1="17" x2="23" y1="16" y2="16"/>'
    ),
    "chevron-left": (
        '<polyline points="15 18 9 12 15 6"/>'
    ),
    "chevron-right": (
        '<polyline points="9 18 15 12 9 6"/>'
    ),
    "chevron-up": (
        '<polyline points="18 15 12 9 6 15"/>'
    ),
}

# Aliases for convenience
LUCIDE_SVG_PATHS["profit"] = LUCIDE_SVG_PATHS["coins"]
LUCIDE_SVG_PATHS["loss"] = LUCIDE_SVG_PATHS["shield-alert"]
LUCIDE_SVG_PATHS["expenses"] = LUCIDE_SVG_PATHS["credit-card"]
LUCIDE_SVG_PATHS["dues"] = LUCIDE_SVG_PATHS["receipt"]
LUCIDE_SVG_PATHS["notification"] = LUCIDE_SVG_PATHS["bell"]
LUCIDE_SVG_PATHS["profile"] = LUCIDE_SVG_PATHS["user"]
LUCIDE_SVG_PATHS["edit"] = LUCIDE_SVG_PATHS["pencil"]
LUCIDE_SVG_PATHS["delete"] = LUCIDE_SVG_PATHS["trash-2"]
LUCIDE_SVG_PATHS["trash"] = LUCIDE_SVG_PATHS["trash-2"]
LUCIDE_SVG_PATHS["print"] = LUCIDE_SVG_PATHS["printer"]
LUCIDE_SVG_PATHS["excel"] = LUCIDE_SVG_PATHS["file-spreadsheet"]
LUCIDE_SVG_PATHS["close"] = LUCIDE_SVG_PATHS["x"]
LUCIDE_SVG_PATHS["warning"] = LUCIDE_SVG_PATHS["alert-triangle"]
LUCIDE_SVG_PATHS["add"] = LUCIDE_SVG_PATHS["plus"]


class IconManager:
    """Centralized Lucide vector icon generator with caching."""

    _pixmap_cache: Dict[str, QPixmap] = {}
    _icon_cache: Dict[str, QIcon] = {}

    @staticmethod
    def _build_svg_xml(name: str, color: str = "#64748B", stroke_width: float = 2.0) -> Optional[str]:
        raw_paths = LUCIDE_SVG_PATHS.get(name.lower().strip())
        if not raw_paths:
            # Fallback to circle icon if name not found
            raw_paths = '<circle cx="12" cy="12" r="9"/>'

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width}" '
            f'stroke-linecap="round" stroke-linejoin="round">'
            f'{raw_paths}'
            f'</svg>'
        )
        return svg

    @classmethod
    def get_pixmap(cls, name: str, color: str = "#64748B", size: int = 20, stroke_width: float = 2.0) -> QPixmap:
        """Renders a Lucide icon as an antialiased QPixmap with the requested color and size."""
        cache_key = f"{name.lower()}_{color}_{size}_{stroke_width}"
        if cache_key in cls._pixmap_cache:
            return cls._pixmap_cache[cache_key]

        svg_xml = cls._build_svg_xml(name, color=color, stroke_width=stroke_width)
        renderer = QSvgRenderer(QByteArray(svg_xml.encode("utf-8")))

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()

        cls._pixmap_cache[cache_key] = pixmap
        return pixmap

    @classmethod
    def get_icon(cls, name: str, color: str = "#64748B", size: int = 20, stroke_width: float = 2.0) -> QIcon:
        """Returns a QIcon for the requested Lucide icon name."""
        cache_key = f"icon_{name.lower()}_{color}_{size}_{stroke_width}"
        if cache_key in cls._icon_cache:
            return cls._icon_cache[cache_key]

        pixmap = cls.get_pixmap(name, color=color, size=size, stroke_width=stroke_width)
        icon = QIcon(pixmap)
        cls._icon_cache[cache_key] = icon
        return icon

    @classmethod
    def get(cls, name: str, color: str = "#64748B", size: int = 20) -> QIcon:
        """Shorthand alias matching the prompt specification: IconManager.get("dashboard")"""
        return cls.get_icon(name, color=color, size=size)


# Convenient singleton / alias for direct module imports
icon_mgr = IconManager
get_icon = IconManager.get_icon
get_pixmap = IconManager.get_pixmap
