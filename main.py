import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer
from sqlalchemy import text  

import database.models.academic
import database.models.hr
import database.models.timetable
import database.models.communication  
import database.models.analytics # Phase 17: Analytics & Expense DB Import

from database.connection import init_db, get_session
from core.state_manager import app_state
from ui.components.dialogs import DeveloperAuthDialog
from ui.setup_wizard import SetupWizard
from ui.login_window import LoginWindow
from core.backup_service import BackupService
from core.communication_service import CommunicationService  

def safe_db_upgrade():
    db = get_session()
    try: db.execute(text("ALTER TABLE comm_message_log ADD COLUMN fallback_allowed BOOLEAN DEFAULT 0"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE comm_message_log ADD COLUMN segments INTEGER DEFAULT 1"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE comm_templates ADD COLUMN language VARCHAR(50) DEFAULT 'English'"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE comm_templates ADD COLUMN created_at VARCHAR(50)"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE students ADD COLUMN six_month_fee FLOAT DEFAULT 0.0"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE students ADD COLUMN annual_fee FLOAT DEFAULT 0.0"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE students ADD COLUMN admission_fee FLOAT DEFAULT 0.0"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE students ADD COLUMN admission_fee_paid BOOLEAN DEFAULT 0"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE students ADD COLUMN billing_cycle VARCHAR(50) DEFAULT 'Monthly'"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE fee_vouchers ADD COLUMN fee_type VARCHAR(50) DEFAULT 'Monthly'"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE fee_vouchers ADD COLUMN coverage_start_date VARCHAR(20)"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE fee_vouchers ADD COLUMN coverage_end_date VARCHAR(20)"))
    except Exception: pass
    try: db.execute(text("ALTER TABLE fee_vouchers ADD COLUMN coverage_months TEXT"))
    except Exception: pass
    db.commit()
    db.close()

def main():
    from PySide6.QtCore import Qt
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    def on_initialization_finished():
        # Store timers on `app` to prevent Python garbage collection from stopping them
        app._auto_backup_timer = QTimer()
        app._auto_backup_timer.timeout.connect(BackupService.check_daily_auto_backup)
        app._auto_backup_timer.start(600000)
        
        app._comm_queue_timer = QTimer()
        app._comm_queue_timer.timeout.connect(CommunicationService.process_queue_batch)
        app._comm_queue_timer.start(10000)
        
        app.aboutToQuit.connect(BackupService.run_exit_backup)
        # Defer non-critical startup tasks until after the window is fully rendered
        QTimer.singleShot(1500, BackupService.check_daily_auto_backup)
        QTimer.singleShot(3000, lambda: BackupService.trigger_auto_backup_async("Application Launch"))
        
        if app_state.is_first_time_setup_needed():
            auth_dialog = DeveloperAuthDialog()
            if auth_dialog.exec() == DeveloperAuthDialog.DialogCode.Accepted:
                app._window = SetupWizard()
                app._window.show()
            else:
                sys.exit(0)
        else:
            app._window = LoginWindow()
            app._window.show()

    # Launch elegant startup screen with custom institute branding
    from ui.splash_screen import AppSplashScreen
    splash = AppSplashScreen()
    splash.show()
    splash.start_initialization(on_initialization_finished)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()