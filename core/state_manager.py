from database.connection import get_session
from database.models.institution import InstitutionSettings
from database.models.users import User
from core.security import verify_password, hash_password

class AppStateManager:
    """
    Manages the global state, current user session, and live settings synchronization.
    This acts as the Central Settings Service for the entire application.
    """
    def __init__(self):
        self.current_user_role = None
        self.current_username = None
        
        # Single Source of Truth for settings
        self.settings = {}
        # List of UI functions to trigger when settings change
        self.settings_callbacks = [] 

    def subscribe_settings_change(self, callback):
        """UI components use this to listen for settings updates."""
        if callback not in self.settings_callbacks:
            self.settings_callbacks.append(callback)

    def subscribe(self, callback):
        """Convenience alias for live-sync subscription."""
        self.subscribe_settings_change(callback)

    def subscribe_data_changed(self, callback):
        """UI components use this to listen for database/entity changes for live synchronization."""
        self.subscribe_settings_change(callback)

    def trigger_settings_change(self):
        """Broadcasts update to all subscribed UI components (Live Synchronization)."""
        self.load_settings()

    def notify_data_changed(self):
        """Broadcasts data update notification to all subscribed views (Live DB Synchronization)."""
        for cb in self.settings_callbacks:
            try:
                cb()
            except Exception:
                pass

    def load_settings(self):
        """Loads all settings from DB and triggers UI/Service updates immediately."""
        session = get_session()
        try:
            db_set = session.query(InstitutionSettings).first()
            if db_set:
                self.settings = {
                    # General
                    "institution_type": db_set.institution_type or "",
                    "institution_name": db_set.name or "Unnamed Institution",
                    "address": db_set.address or "",
                    "phone": db_set.phone or "",
                    "email": db_set.email or "",
                    "principal_name": db_set.principal_name or "",
                    "currency": db_set.currency or "PKR",
                    "date_format": db_set.date_format or "DD-MM-YYYY",
                    "time_format": db_set.time_format or "12-Hour",
                    
                    # Branding
                    "app_title": db_set.app_title or "Universal Education",
                    "dashboard_title": db_set.dashboard_title or "Dashboard",
                    "logo_path": db_set.logo_path or "",
                    "app_icon_path": db_set.app_icon_path or "",
                    "theme_mode": db_set.theme_mode or "Light",
                    "primary_color": db_set.primary_color or "#1D4ED8",
                    
                    # Academic
                    "session": db_set.current_academic_session or "N/A",
                    "session_start": db_set.session_start_date or "",
                    "session_end": db_set.session_end_date or "",
                    
                    # Finance
                    "receipt_prefix": db_set.receipt_prefix or "REC-",
                    "receipt_number_format": db_set.receipt_number_format or "YYYYMM-####",
                    "default_fine_rule": db_set.default_fine_rule or "",
                    
                    # Printing
                    "default_printer": db_set.default_printer or "",
                    "show_print_preview": db_set.show_print_preview,
                    "default_paper_size": db_set.default_paper_size or "A4",
                    
                    # Backup (Preserved)
                    "local_backup_enabled": db_set.local_backup_enabled or False,
                    "backup_location": db_set.backup_location or "",
                    "auto_backup_enabled": db_set.auto_backup_enabled or False,
                    "auto_backup_time": db_set.auto_backup_time or "02:00",
                    "backup_on_exit": db_set.backup_on_exit or False,
                    "retention_days": db_set.retention_days or 30,
                    "last_backup_datetime": db_set.last_backup_datetime or "Never"
                }
            else:
                self.settings = {"app_title": "Universal Education", "dashboard_title": "Dashboard", "institution_name": "Setup Required", "session": ""}
        finally:
            session.close()
            
        # Broadcast the update to all subscribed UI components (Live Synchronization)
        for cb in self.settings_callbacks:
            try:
                cb()
            except RuntimeError:
                # Handle cases where a UI component was deleted/closed but not unsubscribed
                pass

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)

    def is_first_time_setup_needed(self) -> bool:
        session = get_session()
        try:
            settings_row = session.query(InstitutionSettings).first()
            if not settings_row:
                settings_row = InstitutionSettings(is_setup_complete=False)
                session.add(settings_row)
                session.commit()
                return True
            return not settings_row.is_setup_complete
        except Exception as e:
            print(f"Error checking setup state: {e}")
            return True
        finally:
            session.close()

    def login(self, username, password) -> tuple[bool, str]:
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user: return False, "Username not found."
            if not user.is_active: return False, "This account has been disabled."
            if verify_password(password, user.password_hash):
                self.current_username = user.username
                self.current_user_role = user.role
                return True, "Success"
            return False, "Incorrect password."
        finally:
            session.close()

    def change_password(self, role_name, old_password, new_password) -> tuple[bool, str]:
        session = get_session()
        try:
            user = session.query(User).filter_by(role=role_name).first()
            if not user: return False, f"{role_name} account not found."
            
            if not verify_password(old_password, user.password_hash):
                return False, "The current password you entered is incorrect."
            
            user.password_hash = hash_password(new_password)
            session.commit()
            return True, f"{role_name} password updated successfully."
        except Exception as e:
            session.rollback()
            return False, f"Database error: {str(e)}"
        finally:
            session.close()

    def logout(self):
        self.current_user_role = None
        self.current_username = None
        self.settings_callbacks.clear()  # Clear stale UI callbacks from closed MainWindow

# Global instance
app_state = AppStateManager()