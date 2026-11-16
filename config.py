import os
import sys
from pathlib import Path

# ---------------------------------------------------------
# PATH RESOLUTION FOR DEVELOPMENT AND PYINSTALLER (EXE)
# ---------------------------------------------------------
def get_base_path():
    """
    Get the absolute path to the executable or script.
    This is critical for PyInstaller compatibility.
    """
    if getattr(sys, 'frozen', False):
        # If the application is run as a PyInstaller bundle
        return Path(sys.executable).parent
    else:
        # If the application is run from a normal Python script
        return Path(__file__).resolve().parent

# Core application paths
BASE_DIR = get_base_path()
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
IMAGES_DIR = ASSETS_DIR / "images"

# ---------------------------------------------------------
# SAFE USER DATA DIRECTORY (Protects client data during updates)
# ---------------------------------------------------------
# We create a folder called 'user_data' right next to the app/exe.
USER_DATA_DIR = BASE_DIR / "user_data"

# Sub-directories for user data
DB_DIR = USER_DATA_DIR / "database"
BACKUPS_DIR = USER_DATA_DIR / "backups"
GENERATED_DIR = USER_DATA_DIR / "generated_pdfs"
TEMPLATES_DIR = USER_DATA_DIR / "pdf_templates"
BRANDING_DIR = USER_DATA_DIR / "branding"
PHOTOS_DIR = USER_DATA_DIR / "student_photos"
DOCS_DIR = USER_DATA_DIR / "generated_docs"

# Database file path
DATABASE_FILE = DB_DIR / "school_management.db"

# ---------------------------------------------------------
# DIRECTORY INITIALIZATION
# ---------------------------------------------------------
def initialize_directories():
    """
    Ensure all required user data folders exist before the app starts.
    """
    directories = [
        USER_DATA_DIR, DB_DIR, BACKUPS_DIR, GENERATED_DIR,
        TEMPLATES_DIR, BRANDING_DIR, PHOTOS_DIR, DOCS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        
    print("System directories initialized successfully.")

# ---------------------------------------------------------
# APPLICATION METADATA DEFAULT SETTINGS
# ---------------------------------------------------------
APP_DEFAULT_NAME = "Universal Education Management System"
APP_VERSION = "1.0.0"

# Developer secure hash will be handled in core/security.py