"""
Interactive setup wizard for simpleScreen.

Walks the user through creating a new session profile:
  1. Session name
  2. Local or Remote
  3. (Remote) Host, port, OS type, username
  4. (Remote) SSH key setup or password
  5. (WSL)    Enumerate and choose WSL distro
  6. Remote path
  7. First-time remote setup (install screen, push .screenrc)
  8. Save to database
"""

import re
from pathlib import Path

from lib import db, credentials, ui, ssh_manager, filebrowser


def create_new_session(prefill: dict = None) -> dict | None:
    """
    Run the full creation wizard.
    Pass `prefill` (an existing session dict) to pre-populate defaults when editing.
    Returns the saved session dict, or None if the user cancelled.
    """
    p = prefill or {}

    ui.header('Create New Session')

    # ── 1. Session name ───────────────────────────────────────────────────────
    while True:
        name = ui.prompt('Session name', default=p.get('name'))
        if not re.match(r'^[\w\-]+$', name):
            ui.warn('Name must contain only letters, numbers, underscores, or dashes.')
            continue
        existing = db.get_session(name)
        if existing and existing['name'] != p.get('name'):
            if not ui.confirm(f"Session '{name}' already exists. Overwrite?",
                              default_yes=False):
                continue
        break

    # ── 2. Session type ───────────────────────────────────────────────────────
    print()
    type_choice = ui.menu(
        ['Remote (SSH connection to another machine)', 'Local (on this machine)'],
        prompt='Session type'
    )

    if type_choice == 2:
        return _wizard_local(name, p)
    else:
        return _wizard_remote(name, p)


# ── Local wizard ──────────────────────────────────────────────────────────────

def _wizard_local(name: str, p: dict) -> dict | None:
    print()
    ui.info('Browse to your local working directory.')
    ui.info('Space = select   Enter = open dir   u = up   q = cancel')
    path = filebrowser.browse_local(
        start=p.get('remote_path', '~'),
        title='Select local path',
    )
    ui.success(f'Selected: {path}')

    session = {
        'name':         name,
        'type':         'local',
        'host':         None,
        'port':         None,
        'os_type':      None,
        'username':     None,
        'wsl_distro':   None,
        'remote_path':  path,
        'ssh_key_path': None,
    }

    ui.print_session_summary(session)

    if not ui.confirm('Save this session?'):
        return None

    db.save_session(session)
    ui.success(f"Session '{name}' saved.")
    return session


# ── Remote wizard ─────────────────────────────────────────────────────────────

def _wizard_remote(name: str, p: dict) -> dict | None:

    # ── Host ─────────────────────────────────────────────────────────────────
    known = _get_known_hosts()
    if known:
        print()
        ui.info('Known hosts detected — pick one or choose "Enter manually".')
        options = known[:9] + ['Enter manually']
        choice = ui.menu(options, prompt='Host')
        host = known[choice - 1] if choice <= len(known) else ui.prompt(
            'IP address or hostname', default=p.get('host')
        )
    else:
        host = ui.prompt('IP address or hostname', default=p.get('host'))

    port_str = ui.prompt('SSH port', default=str(p.get('port', 22)))
    port = int(port_str) if port_str.isdigit() else 22

    # ── OS type ───────────────────────────────────────────────────────────────
    print()
    os_map = {1: 'linux', 2: 'wsl', 3: 'windows'}
    default_os_idx = {'linux': 1, 'wsl': 2, 'windows': 3}.get(p.get('os_type'), 1)
    os_choice = ui.menu(
        ['Linux', 'WSL (on a remote Windows machine)', 'Windows'],
        prompt=f'Remote OS type [{default_os_idx}]'
    )
    os_type = os_map[os_choice]

    # ── Username ──────────────────────────────────────────────────────────────
    import getpass
    default_user = p.get('username') or getpass.getuser()
    username = ui.prompt('Username', default=default_user)

    # ── Authentication ────────────────────────────────────────────────────────
    print()
    ui.info('Authentication method:')
    auth_choice = ui.menu(
        [
            'SSH key (recommended — set up automatically)',
            'Password (stored in system keyring)',
        ],
        prompt='Auth method'
    )

    key_path   = None
    password   = None
    temp_pass  = None   # used only during key copy; never persisted

    if auth_choice == 1:
        # Generate key if needed
        print()
        ui.info(f"Generating SSH key for '{name}'...")
        priv, pub = ssh_manager.generate_ssh_key(name)
        key_path = priv
        ui.success(f'Key: {priv}')

        # We need the user's password once to copy the key
        print()
        ui.info(f'To install the key on {host}, your password is needed once.')
        ui.info('It will NOT be stored after this step.')
        temp_pass = ui.prompt('Password (temporary, for key copy)', secret=True)

        print()
        ui.info('Copying public key to remote host...')
        ok = ssh_manager.copy_public_key(host, port, username, temp_pass, pub, os_type)
        if ok:
            ui.success('Key copied — future connections will not require a password.')
        else:
            ui.warn('Automatic key copy failed.')
            ui.info(f'Manual option: append the content of  {pub}')
            ui.info('to ~/.ssh/authorized_keys on the remote system,')
            ui.info('then press Enter to continue.')
            input('  Press Enter when ready (or Ctrl-C to cancel)...')
    else:
        password = ui.prompt('Password', secret=True)

    # ── WSL distro ────────────────────────────────────────────────────────────
    wsl_distro = None
    if os_type == 'wsl':
        print()
        ui.info('Detecting WSL distributions on remote Windows host...')
        distros = ssh_manager.enumerate_wsl_distros(
            host, port, username,
            key_path=key_path,
            password=temp_pass or password,
        )

        if distros:
            ui.success(f'Found {len(distros)} distribution(s):')
            wsl_distro = distros[ui.menu(distros, prompt='WSL distribution') - 1]
        else:
            ui.warn('Could not auto-detect WSL distributions.')
            wsl_distro = ui.prompt(
                'WSL distribution name',
                default=p.get('wsl_distro', 'Ubuntu')
            )

    # ── Remote path ───────────────────────────────────────────────────────────
    print()
    ui.info('Browse the remote filesystem to select your working directory.')
    ui.info('Space = select   Enter = open dir   u = up   q = cancel')
    remote_path = filebrowser.browse_remote(
        host=host,
        port=port,
        username=username,
        start=p.get('remote_path', '~'),
        title=f'Remote path on {host}',
        key_path=key_path,
        password=temp_pass or password,
        os_type=os_type,
        wsl_distro=wsl_distro,
    )
    ui.success(f'Selected: {remote_path}')

    # ── Build session dict ────────────────────────────────────────────────────
    session = {
        'name':         name,
        'type':         'remote',
        'host':         host,
        'port':         port,
        'os_type':      os_type,
        'username':     username,
        'wsl_distro':   wsl_distro,
        'remote_path':  remote_path,
        'ssh_key_path': key_path,
    }

    # Persist password if using password auth
    if password:
        credentials.save_password(name, password)

    # ── Summary & confirm ─────────────────────────────────────────────────────
    ui.print_session_summary(session)

    if not ui.confirm('Save this session?'):
        return None

    # ── First-time remote setup ───────────────────────────────────────────────
    print()
    ui.info('Performing first-time remote setup...')
    ssh_manager.first_time_remote_setup(
        host, port, username, os_type,
        wsl_distro=wsl_distro,
        key_path=key_path,
        password=temp_pass or password,
    )

    db.save_session(session)
    ui.success(f"Session '{name}' saved and ready.")
    return session


# ── Known-hosts helper ────────────────────────────────────────────────────────

def _get_known_hosts() -> list[str]:
    """
    Parse ~/.ssh/known_hosts and ~/.ssh/config for host suggestions.
    Returns a sorted, deduplicated list of hostnames / IP addresses.
    """
    hosts: set[str] = set()

    known_hosts_file = Path.home() / '.ssh' / 'known_hosts'
    if known_hosts_file.exists():
        try:
            with open(known_hosts_file, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    entry = line.split()[0].split(',')[0]
                    # Skip hashed entries (|1|...)
                    if entry.startswith('|'):
                        continue
                    # Strip [host]:port notation
                    if entry.startswith('['):
                        entry = entry[1:entry.index(']')]
                    hosts.add(entry)
        except Exception:
            pass

    ssh_config_file = Path.home() / '.ssh' / 'config'
    if ssh_config_file.exists():
        try:
            with open(ssh_config_file, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line.lower().startswith('hostname '):
                        hosts.add(line.split(None, 1)[1].strip())
        except Exception:
            pass

    return sorted(hosts)
