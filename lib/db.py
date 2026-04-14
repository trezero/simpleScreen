"""
SQLite-backed session profile storage for simpleScreen.
Database lives in %APPDATA%\\simpleScreen\\ on Windows or ~/.simpleScreen/ on Linux/Mac.
"""

import sqlite3
import os
from pathlib import Path


def get_data_dir() -> Path:
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA', Path.home())) / 'simpleScreen'
    else:
        base = Path.home() / '.simpleScreen'
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_db_path() -> Path:
    return get_data_dir() / 'sessions.db'


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    UNIQUE NOT NULL,
            type            TEXT    NOT NULL CHECK(type IN ('local', 'remote')),
            host            TEXT,
            port            INTEGER DEFAULT 22,
            os_type         TEXT    CHECK(os_type IN ('windows', 'wsl', 'linux', NULL)),
            username        TEXT,
            wsl_distro      TEXT,
            remote_path     TEXT,
            ssh_key_path    TEXT,
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_connected  DATETIME
        )
    ''')
    conn.commit()
    conn.close()


def save_session(session: dict) -> int:
    """Insert or replace a session profile. Returns the row id."""
    conn = get_connection()
    cursor = conn.execute('''
        INSERT OR REPLACE INTO sessions
            (name, type, host, port, os_type, username, wsl_distro, remote_path, ssh_key_path)
        VALUES
            (:name, :type, :host, :port, :os_type, :username, :wsl_distro, :remote_path, :ssh_key_path)
    ''', {
        'name':         session.get('name'),
        'type':         session.get('type'),
        'host':         session.get('host'),
        'port':         session.get('port', 22),
        'os_type':      session.get('os_type'),
        'username':     session.get('username'),
        'wsl_distro':   session.get('wsl_distro'),
        'remote_path':  session.get('remote_path'),
        'ssh_key_path': session.get('ssh_key_path'),
    })
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_session(name: str) -> dict | None:
    """Return a session profile by name, or None if not found."""
    conn = get_connection()
    row = conn.execute('SELECT * FROM sessions WHERE name = ?', (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_sessions() -> list[dict]:
    """Return all session profiles ordered by most recently connected."""
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM sessions ORDER BY last_connected DESC NULLS LAST, created_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_session(name: str) -> bool:
    """Delete a session profile. Returns True if a row was deleted."""
    conn = get_connection()
    cursor = conn.execute('DELETE FROM sessions WHERE name = ?', (name,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_last_connected(name: str):
    """Stamp the current time as last_connected for a session."""
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET last_connected = CURRENT_TIMESTAMP WHERE name = ?",
        (name,)
    )
    conn.commit()
    conn.close()
