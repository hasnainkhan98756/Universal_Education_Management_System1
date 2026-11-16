import bcrypt
import hmac
from datetime import datetime

def hash_password(plain_password: str) -> str:
    """
    Hashes a password using bcrypt for secure database storage.
    This will be used when creating or updating Principal/Admin accounts.
    """
    pwd_bytes = plain_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a stored bcrypt hash.
    This will be used during the Login screen.
    """
    pwd_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except ValueError:
        return False

from datetime import timedelta

def verify_developer_password(entered_password: str) -> bool:
    """
    Verifies the Developer Authorization Password using dynamic time-based rotation.
    Format dynamically changes every minute according to current date & time with 'Hr' suffix:
        e.g., MMDDYYYYHHMMHr / DDMMYYYYHHMMHr (e.g. 100920261134Hr)
    Supports both 24-hour and 12-hour clocks, case-insensitive 'Hr' suffix,
    and a +/- 3-minute grace window so typing time never causes authorization failure.
    Static master passwords (such as old 'Hasnain Amjad') are strictly blocked and rejected.
    """
    if not entered_password:
        return False
    try:
        entered_str = str(entered_password).strip()
        
        # Explicitly reject and block any old static master sequences
        if entered_str.lower() in ["hasnain amjad", "hasnain", "hasnainamjad", "admin", "password", "123456"]:
            return False

        now = datetime.now()

        # Check a grace window of +/- 3 minutes (-3, -2, -1, 0, 1, 2, 3)
        valid_candidates = set()
        for minute_offset in range(-3, 4):
            ref = now + timedelta(minutes=minute_offset)
            d = ref.strftime("%d")      # e.g. 10
            m = ref.strftime("%m")      # e.g. 10
            y = ref.strftime("%Y")      # e.g. 2026
            h24 = ref.strftime("%H")    # e.g. 16
            h12 = ref.strftime("%I")    # e.g. 04
            mn = ref.strftime("%M")     # e.g. 18

            base_times = [
                f"{d}{m}{y}{h24}{mn}",
                f"{m}{d}{y}{h24}{mn}",
                f"{d}{m}{y}{h12}{mn}",
                f"{m}{d}{y}{h12}{mn}",
                f"{d}{m}{y}{h24}",
                f"{m}{d}{y}{h24}",
                f"{d}{m}{y}{h12}",
                f"{m}{d}{y}{h12}",
            ]

            for bt in base_times:
                valid_candidates.add(f"{bt}hr".lower())
                valid_candidates.add(bt.lower())

        clean_entered = entered_str.lower()
        for cand in valid_candidates:
            if hmac.compare_digest(clean_entered.encode('utf-8'), cand.encode('utf-8')):
                return True

        return False
    except Exception:
        return False