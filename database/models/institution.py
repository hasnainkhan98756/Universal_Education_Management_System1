from sqlalchemy import Column, Integer, String, Boolean
from database.models.base import Base

class InstitutionSettings(Base):
    """
    The Single Source of Truth for all universal institution settings.
    Expanded to support Academic, Financial, Printing, and Visual configurations.
    """
    __tablename__ = 'institution_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_setup_complete = Column(Boolean, default=False)
    
    # 1. General Settings
    institution_type = Column(String(50), nullable=True) 
    name = Column(String(200), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    principal_name = Column(String(100), nullable=True)
    currency = Column(String(20), default="PKR")
    date_format = Column(String(50), default="DD-MM-YYYY")
    time_format = Column(String(50), default="12-Hour")
    
    # 2. Appearance & Branding
    app_title = Column(String(200), nullable=True)
    dashboard_title = Column(String(200), default="Dashboard") 
    logo_path = Column(String(500), nullable=True)
    app_icon_path = Column(String(500), nullable=True)         
    theme_mode = Column(String(50), default="Light") # Light, Dark, System
    primary_color = Column(String(50), default="#1D4ED8")

    # 3. Academic Settings
    current_academic_session = Column(String(50), nullable=True)
    session_start_date = Column(String(50), nullable=True)
    session_end_date = Column(String(50), nullable=True)

    # 4. Fee & Finance Settings
    receipt_prefix = Column(String(20), default="REC-")
    receipt_number_format = Column(String(50), default="YYYYMM-####")
    default_fine_rule = Column(String(200), nullable=True)
    
    # 5. Printing Settings
    default_printer = Column(String(200), nullable=True)
    show_print_preview = Column(Boolean, default=True)
    default_paper_size = Column(String(50), default="A4")

    # 6. Backup & Restore Settings (Preserved and Untouched)
    local_backup_enabled = Column(Boolean, default=False)
    backup_location = Column(String(500), nullable=True)
    auto_backup_enabled = Column(Boolean, default=False)
    auto_backup_time = Column(String(10), default="02:00")
    backup_on_exit = Column(Boolean, default=False)
    retention_days = Column(Integer, default=30)
    last_backup_datetime = Column(String(100), nullable=True)