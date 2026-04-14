"""
Terminal UI helpers for simpleScreen.
Provides menus, prompts, tables, and summary formatting.
"""

import os
import getpass


# ── Formatting helpers ────────────────────────────────────────────────────────

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def header(title: str = 'simpleScreen'):
    print()
    print('=' * 52)
    print(f'  {title}')
    print('=' * 52)
    print()


def divider():
    print('-' * 52)


# ── Input helpers ─────────────────────────────────────────────────────────────

def menu(options: list[str], prompt: str = 'Choose') -> int:
    """
    Display a numbered list and return the 1-based index of the user's choice.
    Loops until a valid number is entered.
    """
    for i, opt in enumerate(options, 1):
        print(f'  {i}. {opt}')
    print()
    while True:
        try:
            raw = input(f'  {prompt} (1-{len(options)}): ').strip()
            idx = int(raw)
            if 1 <= idx <= len(options):
                return idx
        except (ValueError, KeyboardInterrupt):
            pass
        print(f'  Please enter a number between 1 and {len(options)}.')


def prompt(label: str, default: str = None, required: bool = True,
           secret: bool = False) -> str:
    """
    Prompt the user for a value.
    - default  : shown in brackets; returned if the user presses Enter
    - required : re-prompts if empty and no default
    - secret   : masks input (password fields)
    """
    display = f'  {label}'
    if default:
        display += f' [{default}]'
    display += ': '

    while True:
        value = getpass.getpass(display) if secret else input(display).strip()

        if not value and default is not None:
            return default
        if value:
            return value
        if not required:
            return ''
        print('  This field is required.')


def confirm(question: str, default_yes: bool = True) -> bool:
    """Ask a yes/no question. Returns True for yes."""
    hint = '(Y/n)' if default_yes else '(y/N)'
    raw = input(f'  {question} {hint}: ').strip().lower()
    if not raw:
        return default_yes
    return raw in ('y', 'yes')


# ── Display helpers ───────────────────────────────────────────────────────────

def print_session_summary(session: dict):
    """Print a formatted session profile summary."""
    print()
    divider()
    print('  Session Profile Summary')
    divider()
    print(f"  Name       : {session['name']}")
    print(f"  Type       : {session['type']}")
    if session['type'] == 'remote':
        host = session.get('host', '')
        port = session.get('port', 22)
        print(f"  Host       : {host}:{port}")
        print(f"  OS         : {session.get('os_type', '')}")
        print(f"  Username   : {session.get('username', '')}")
        if session.get('wsl_distro'):
            print(f"  WSL Distro : {session['wsl_distro']}")
        print(f"  Path       : {session.get('remote_path', '~')}")
        key = session.get('ssh_key_path')
        auth = f'SSH key ({key})' if key else 'Password (stored in system keyring)'
        print(f"  Auth       : {auth}")
    else:
        print(f"  Path       : {session.get('remote_path', '~')}")
    divider()
    print()


def print_sessions_table(sessions: list[dict]):
    """Print all sessions as a formatted table."""
    if not sessions:
        print('  No sessions saved yet.')
        print("  Run 'simpleScreen new' to create one.\n")
        return

    col_name = 28
    col_type = 8
    col_host = 22
    col_last = 16

    header_line = (
        f"  {'NAME':<{col_name}} {'TYPE':<{col_type}} "
        f"{'HOST':<{col_host}} {'LAST CONNECTED':<{col_last}}"
    )
    print(header_line)
    print('  ' + '-' * (col_name + col_type + col_host + col_last + 6))

    for s in sessions:
        name = s['name'][:col_name - 1]
        stype = s['type']
        host = (s.get('host') or 'local')[:col_host - 1]
        last = s.get('last_connected') or 'Never'
        # Normalise ISO datetime: "2024-01-15T10:30:00" → "2024-01-15 10:30"
        if last != 'Never' and ('T' in last or ' ' in last):
            last = last.replace('T', ' ')[:16]
        print(
            f"  {name:<{col_name}} {stype:<{col_type}} "
            f"{host:<{col_host}} {last:<{col_last}}"
        )
    print()


def info(msg: str):
    print(f'  {msg}')


def success(msg: str):
    print(f'  [OK] {msg}')


def warn(msg: str):
    print(f'  [!!] {msg}')


def error(msg: str):
    print(f'  [ERROR] {msg}')
