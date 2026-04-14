"""
Session scanner for simpleScreen.

Scans a local or remote machine for existing GNU screen sessions
and imports selected sessions into the local profile database.
"""

import os
import re
import subprocess
from pathlib import Path

from lib import db, credentials, ui, ssh_manager


def scan_for_sessions():
    """Main entry point for the scan-for-sessions wizard."""
    ui.header('Scan for Existing Sessions')

    source_choice = ui.menu(
        ['Local (this machine)', 'Remote (another machine via SSH)'],
        prompt='Scan location'
    )

    if source_choice == 1:
        _scan_local()
    else:
        _scan_remote()


# ── Local scan ────────────────────────────────────────────────────────────────

def _scan_local():
    """Scan the local machine for screen sessions."""
    if os.name == 'nt':
        # On Windows the only option is WSL
        os_type = 'wsl'
        distros = _get_local_wsl_distros()
        if not distros:
            ui.warn('No WSL distributions found.')
            ui.info('Install WSL: wsl --install')
            return
        print()
        if len(distros) == 1:
            wsl_distro = distros[0]
            ui.info(f'Using WSL distro: {wsl_distro}')
        else:
            ui.info('Available WSL distributions:')
            wsl_distro = distros[ui.menu(distros, prompt='Choose WSL distro') - 1]
    else:
        # Linux / macOS — offer Linux or WSL
        print()
        os_map = {1: 'linux', 2: 'wsl'}
        os_choice = ui.menu(['Linux (native screen)', 'WSL'], prompt='OS type')
        os_type = os_map[os_choice]
        wsl_distro = None
        if os_type == 'wsl':
            distros = _get_local_wsl_distros()
            if not distros:
                ui.warn('No WSL distributions found.')
                return
            wsl_distro = distros[ui.menu(distros, prompt='WSL distro') - 1]

    print()
    ui.info('Scanning for screen sessions...')
    sessions = _get_screen_sessions_local(os_type, wsl_distro)

    if not sessions:
        ui.info('No active screen sessions found.')
        return

    ui.success(f'Found {len(sessions)} screen session(s):')
    selected = _multi_select_sessions(sessions)
    if not selected:
        ui.info('No sessions selected.')
        return

    _import_local_sessions(selected, os_type, wsl_distro)


# ── Remote scan ───────────────────────────────────────────────────────────────

def _scan_remote():
    """Scan a remote machine for screen sessions via SSH."""
    import getpass
    from lib.wizard import _get_known_hosts

    # Host
    known = _get_known_hosts()
    if known:
        print()
        ui.info('Known hosts detected — pick one or choose "Enter manually".')
        options = known[:9] + ['Enter manually']
        choice = ui.menu(options, prompt='Host')
        host = known[choice - 1] if choice <= len(known) else ui.prompt('IP address or hostname')
    else:
        host = ui.prompt('IP address or hostname')

    port_str = ui.prompt('SSH port', default='22')
    port = int(port_str) if port_str.isdigit() else 22

    # OS type
    print()
    os_map = {1: 'linux', 2: 'wsl', 3: 'windows'}
    os_choice = ui.menu(
        ['Linux', 'WSL (on a remote Windows machine)', 'Windows'],
        prompt='Remote OS type'
    )
    os_type = os_map[os_choice]

    if os_type == 'windows':
        ui.warn('Windows does not support GNU screen — no sessions to scan.')
        return

    # Username
    username = ui.prompt('Username', default=getpass.getuser())

    # Auth
    print()
    auth_choice = ui.menu(
        ['SSH key', 'Password'],
        prompt='Authentication method'
    )

    key_path = None
    password = None

    if auth_choice == 1:
        existing_key = _find_key_for_host(host)
        if existing_key:
            ui.info(f'Found existing simpleScreen key: {existing_key}')
            if ui.confirm('Use this key?'):
                key_path = existing_key
        if not key_path:
            default_key = str(Path.home() / '.ssh' / 'id_ed25519')
            key_path = ui.prompt('Path to SSH private key', default=default_key)
    else:
        password = ui.prompt('Password', secret=True)

    # WSL distro (remote)
    wsl_distro = None
    if os_type == 'wsl':
        print()
        ui.info('Detecting WSL distributions on remote host...')
        distros = ssh_manager.enumerate_wsl_distros(
            host, port, username,
            key_path=key_path,
            password=password,
        )
        if distros:
            ui.success(f'Found {len(distros)} distribution(s):')
            wsl_distro = distros[ui.menu(distros, prompt='WSL distribution') - 1]
        else:
            ui.warn('Could not auto-detect WSL distributions.')
            wsl_distro = ui.prompt('WSL distribution name', default='Ubuntu')

    # Scan
    print()
    ui.info('Scanning for screen sessions...')
    sessions = _get_screen_sessions_remote(
        host, port, username,
        os_type=os_type,
        wsl_distro=wsl_distro,
        key_path=key_path,
        password=password,
    )

    if not sessions:
        ui.info('No active screen sessions found.')
        return

    ui.success(f'Found {len(sessions)} screen session(s):')
    selected = _multi_select_sessions(sessions)
    if not selected:
        ui.info('No sessions selected.')
        return

    _import_remote_sessions(
        selected,
        host=host, port=port, username=username,
        os_type=os_type, wsl_distro=wsl_distro,
        key_path=key_path, password=password,
    )


# ── screen -ls runners ────────────────────────────────────────────────────────

def _get_screen_sessions_local(os_type: str, wsl_distro: str = None) -> list[dict]:
    """Run 'screen -ls' locally (optionally inside a WSL distro)."""
    try:
        if os_type == 'wsl':
            wsl_args = ['wsl']
            if wsl_distro:
                wsl_args += ['-d', wsl_distro]
            wsl_args += ['--', 'bash', '-c', 'screen -ls']
            result = subprocess.run(wsl_args, capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run(['screen', '-ls'], capture_output=True, text=True, timeout=10)

        return _parse_screen_ls(result.stdout + result.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        ui.warn(f'Could not run screen -ls: {e}')
        return []


def _get_screen_sessions_remote(host: str, port: int, username: str,
                                 os_type: str, wsl_distro: str = None,
                                 key_path: str = None, password: str = None) -> list[dict]:
    """SSH to a remote host and run 'screen -ls', returning parsed sessions."""
    try:
        import paramiko
    except ImportError:
        ui.warn('paramiko is not installed — run: pip install paramiko')
        return []

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh_manager._connect(client, host, port, username, key_path, password)

        if os_type == 'linux':
            cmd = 'screen -ls'
        elif os_type == 'wsl':
            # Route through PowerShell so cmd.exe doesn't mangle the bash command
            cmd = (f"powershell -NonInteractive -Command "
                   f"\"wsl -d {wsl_distro} -e bash -c 'screen -ls'\"")
        else:
            return []

        _, stdout, stderr = client.exec_command(cmd)
        output = (stdout.read().decode('utf-8', errors='ignore') +
                  stderr.read().decode('utf-8', errors='ignore'))
        return _parse_screen_ls(output)

    except Exception as e:
        ui.warn(f'Could not connect to scan for sessions: {e}')
        return []
    finally:
        client.close()


# ── screen -ls parser ─────────────────────────────────────────────────────────

def _parse_screen_ls(output: str) -> list[dict]:
    """
    Parse 'screen -ls' output into a list of dicts.

    Each dict has:
      name      — the screen session name (the part after the dot in pid.name)
      full_name — the complete pid.name identifier
      status    — 'Detached', 'Attached', or 'Dead'

    Example input:
        There are screens on:
                12345.mySession    (01/01/2026 12:00:00)    (Detached)
                67890.other        (01/01/2026 13:00:00)    (Attached)
        2 Sockets in /run/screen/S-user.
    """
    sessions = []
    for line in output.splitlines():
        line = line.strip()
        # Match: pid.name  (date)  (status)
        # Use \S+ for the name to capture any non-whitespace characters.
        m = re.match(
            r'^(\d+\.(\S+))\s+\(.*?\)\s+\((Detached|Attached|Dead)\)',
            line
        )
        if m:
            sessions.append({
                'full_name': m.group(1),
                'name':      m.group(2),
                'status':    m.group(3),
            })
    return sessions


# ── Multi-select UI ───────────────────────────────────────────────────────────

def _multi_select_sessions(sessions: list[dict]) -> list[dict]:
    """
    Show the list of found screen sessions and let the user pick which to import.
    Accepts: individual numbers (1), comma/space lists (1,3), ranges (1-3),
             'a' for all, 'q' or empty to cancel.
    """
    print()
    for i, s in enumerate(sessions, 1):
        pid = s['full_name'].split('.')[0]
        print(f'  {i}. {s["name"]:<32} [{s["status"]}]  pid:{pid}')
    print()
    ui.info("Enter numbers to import (e.g. 1  or  1,3  or  1-3), 'a' for all, 'q' to cancel:")

    while True:
        raw = input('  Selection: ').strip().lower()
        if raw in ('q', ''):
            return []
        if raw == 'a':
            return sessions

        selected = set()
        valid = True
        for part in re.split(r'[,\s]+', raw):
            part = part.strip()
            if not part:
                continue
            range_m = re.match(r'^(\d+)-(\d+)$', part)
            if range_m:
                start, end = int(range_m.group(1)), int(range_m.group(2))
                if 1 <= start <= end <= len(sessions):
                    selected.update(range(start, end + 1))
                else:
                    ui.warn(f'Invalid range: {part}')
                    valid = False
                    break
            elif part.isdigit():
                idx = int(part)
                if 1 <= idx <= len(sessions):
                    selected.add(idx)
                else:
                    ui.warn(f'Invalid number: {idx}  (must be 1-{len(sessions)})')
                    valid = False
                    break
            else:
                ui.warn(f'Unrecognised input: {part!r}')
                valid = False
                break

        if valid and selected:
            return [sessions[i - 1] for i in sorted(selected)]
        if valid:
            ui.info('Nothing selected — try again or enter q to cancel.')


# ── Import helpers ────────────────────────────────────────────────────────────

def _import_local_sessions(sessions: list[dict], os_type: str, wsl_distro: str = None):
    """Save selected screen sessions as local simpleScreen profiles."""
    imported = []
    for s in sessions:
        name = _resolve_profile_name(s['name'])
        if name is None:
            ui.info(f"Skipped '{s['name']}'.")
            continue

        db.save_session({
            'name':         name,
            'type':         'local',
            'host':         None,
            'port':         None,
            'os_type':      os_type,
            'username':     None,
            'wsl_distro':   wsl_distro,
            'remote_path':  '~',
            'ssh_key_path': None,
        })
        ui.success(f"Imported '{name}'  (screen: {s['full_name']})")
        imported.append(name)

    if imported:
        print()
        ui.info(f'{len(imported)} session(s) added. Connect with:')
        for name in imported:
            ui.info(f'  simpleScreen {name}')


def _import_remote_sessions(sessions: list[dict], host: str, port: int,
                             username: str, os_type: str, wsl_distro: str = None,
                             key_path: str = None, password: str = None):
    """Save selected screen sessions as remote simpleScreen profiles."""
    imported = []
    for s in sessions:
        name = _resolve_profile_name(s['name'])
        if name is None:
            ui.info(f"Skipped '{s['name']}'.")
            continue

        db.save_session({
            'name':         name,
            'type':         'remote',
            'host':         host,
            'port':         port,
            'os_type':      os_type,
            'username':     username,
            'wsl_distro':   wsl_distro,
            'remote_path':  '~',
            'ssh_key_path': key_path,
        })
        if password:
            credentials.save_password(name, password)
        ui.success(f"Imported '{name}'  (screen: {s['full_name']})")
        imported.append(name)

    if imported:
        print()
        ui.info(f'{len(imported)} session(s) added. Connect with:')
        for name in imported:
            ui.info(f'  simpleScreen {name}')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_profile_name(screen_name: str) -> str | None:
    """
    Determine the profile name to use for an imported session.
    Sanitizes the screen name, then handles conflicts with existing profiles.
    Returns the chosen name, or None to skip.
    """
    safe = re.sub(r'[^\w\-]', '_', screen_name)

    existing = db.get_session(safe)
    if existing:
        print()
        ui.warn(f"A session named '{safe}' already exists.")
        choice = ui.menu(
            [f"Overwrite '{safe}'", 'Enter a new name', 'Skip this session'],
            prompt='Action'
        )
        if choice == 1:
            return safe
        elif choice == 2:
            while True:
                new_name = ui.prompt('New profile name')
                if re.match(r'^[\w\-]+$', new_name):
                    return new_name
                ui.warn('Name must contain only letters, numbers, underscores, or dashes.')
        else:
            return None

    return safe


def _find_key_for_host(host: str) -> str | None:
    """
    Look up existing simpleScreen session profiles for this host and return
    the SSH key path if one exists and the file is present.
    """
    for s in db.list_sessions():
        if s.get('host') == host and s.get('ssh_key_path'):
            key = s['ssh_key_path']
            if Path(key).exists():
                return key
    return None


def _get_local_wsl_distros() -> list[str]:
    """Return installed WSL distribution names using 'wsl -l -q'."""
    try:
        result = subprocess.run(
            ['wsl', '-l', '-q'],
            capture_output=True, timeout=10
        )
        raw = result.stdout
        for enc in ('utf-8', 'utf-16-le', 'latin-1'):
            try:
                text = raw.decode(enc).replace('\x00', '').lstrip('\ufeff')
                distros = [
                    line.strip().lstrip('*').strip()
                    for line in text.splitlines()
                ]
                distros = [d for d in distros if d]
                if distros:
                    return distros
            except (UnicodeDecodeError, ValueError):
                continue
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return []
