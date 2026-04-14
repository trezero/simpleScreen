"""
Secure credential storage for simpleScreen.
Uses the system keyring (Windows Credential Manager on Windows,
Secret Service / Keychain on Linux/Mac) via the keyring library.
Falls back gracefully if the keyring backend is unavailable.
"""

SERVICE_NAME = 'simpleScreen'


def save_password(session_name: str, password: str) -> bool:
    """Store a password for a session. Returns True on success."""
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, session_name, password)
        return True
    except Exception as e:
        print(f"  Warning: could not save password to system keyring: {e}")
        print("  You will be prompted for the password each time you connect.")
        return False


def get_password(session_name: str) -> str | None:
    """Retrieve the stored password for a session, or None."""
    try:
        import keyring
        return keyring.get_password(SERVICE_NAME, session_name)
    except Exception:
        return None


def delete_password(session_name: str):
    """Remove the stored password for a session (silently ignores missing entries)."""
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, session_name)
    except Exception:
        pass
