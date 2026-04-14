"""
SSH management for simpleScreen.

Responsibilities:
  - Generate SSH key pairs per session
  - Copy the public key to a remote host using a one-time password (paramiko)
  - Enumerate WSL distributions on a remote Windows host via SSH
  - Push the simpleScreen .screenrc template to remote systems
  - Install screen on remote Linux / WSL if missing
  - Build and launch the final interactive SSH command (system ssh for TTY)
"""

import os
import re
import subprocess
import sys
from pathlib import Path


# ── Key storage ───────────────────────────────────────────────────────────────

def get_key_dir() -> Path:
    if os.name == 'nt':
        base = Path(os.environ.get('APPDATA', Path.home())) / 'simpleScreen' / 'keys'
    else:
        base = Path.home() / '.simpleScreen' / 'keys'
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_screenrc_template_path() -> Path:
    return Path(__file__).parent.parent / 'templates' / 'screenrc'


# ── Key generation ────────────────────────────────────────────────────────────

def generate_ssh_key(session_name: str) -> tuple[str, str]:
    """
    Generate an ed25519 SSH key pair named after the session.
    Returns (private_key_path, public_key_path).
    Does nothing if the key already exists.
    """
    safe = re.sub(r'[^\w\-]', '_', session_name)
    key_path = get_key_dir() / f'ss_{safe}'
    pub_path = Path(str(key_path) + '.pub')

    if key_path.exists():
        return str(key_path), str(pub_path)

    result = subprocess.run(
        [
            'ssh-keygen', '-t', 'ed25519',
            '-f', str(key_path),
            '-N', '',               # no passphrase on the key itself
            '-C', f'simpleScreen_{session_name}',
        ],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f'ssh-keygen failed: {result.stderr.strip()}')

    if os.name != 'nt':
        os.chmod(key_path, 0o600)

    return str(key_path), str(pub_path)


# ── Key copying ───────────────────────────────────────────────────────────────

def copy_public_key(host: str, port: int, username: str, password: str,
                    pub_key_path: str, os_type: str) -> bool:
    """
    Copy a public key to the remote host using paramiko + password auth.
    Works for Linux, WSL (via Windows host), and Windows OpenSSH.
    Returns True on success.
    """
    try:
        import paramiko
    except ImportError:
        print('  paramiko is not installed — run: pip install paramiko')
        return False

    with open(pub_key_path, 'r') as f:
        pub_key = f.read().strip()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, port=port, username=username,
                       password=password, timeout=15)

        if os_type == 'linux':
            # Standard Linux SSH server — use POSIX shell commands.
            cmds = [
                'mkdir -p ~/.ssh && chmod 700 ~/.ssh',
                f'echo "{pub_key}" >> ~/.ssh/authorized_keys',
                'chmod 600 ~/.ssh/authorized_keys',
                'sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys',
            ]
        else:
            # 'wsl' and 'windows' both land on the Windows OpenSSH server.
            # Windows cmd.exe does not understand mkdir -p / chmod, so we
            # must use PowerShell.  Also, Windows requires the key in
            # administrators_authorized_keys for users in the Administrators
            # group — write to both locations so either case is covered.
            ps_key = pub_key.replace("'", "''")   # escape PS single quotes
            cmds = [
                # Ensure the .ssh directory exists
                'powershell -Command "New-Item -ItemType Directory -Force '
                '-Path \\"$env:USERPROFILE\\.ssh\\" | Out-Null"',

                # Write to the per-user authorized_keys
                f'powershell -Command "Add-Content -Path '
                f'\\"$env:USERPROFILE\\.ssh\\authorized_keys\\" -Value \'{ps_key}\'"',

                # Write to the administrators_authorized_keys if it exists
                # (required when the Windows user is in the Administrators group)
                f'powershell -Command "if (Test-Path '
                f'\\"C:\\ProgramData\\ssh\\administrators_authorized_keys\\") '
                f'{{ Add-Content -Path '
                f'\\"C:\\ProgramData\\ssh\\administrators_authorized_keys\\" '
                f'-Value \'{ps_key}\' }}"',
            ]

        failed = []
        for cmd in cmds:
            _, stdout, stderr = client.exec_command(cmd)
            rc = stdout.channel.recv_exit_status()
            if rc != 0:
                failed.append(stderr.read().decode('utf-8', errors='ignore').strip())

        if failed:
            # Non-fatal — the key may still have been written; warn but continue.
            print(f'  Warning during key copy: {"; ".join(f for f in failed if f)}')

        return True

    except Exception as e:
        print(f'  Could not copy key: {e}')
        return False
    finally:
        client.close()


# ── Shared connect helper ─────────────────────────────────────────────────────

def _connect(client, host: str, port: int, username: str,
             key_path: str = None, password: str = None):
    """
    Connect a paramiko SSHClient, trying key auth first then password.
    Raises paramiko.AuthenticationException if both fail.
    """
    import paramiko

    if key_path and Path(key_path).exists():
        try:
            client.connect(host, port=port, username=username,
                           key_filename=key_path, timeout=15)
            return
        except paramiko.AuthenticationException:
            pass   # key didn't work — fall through to password

    if password:
        client.connect(host, port=port, username=username,
                       password=password, timeout=15)
        return

    raise paramiko.AuthenticationException(
        'No valid credentials: key auth failed and no password provided.'
    )


# ── WSL enumeration ───────────────────────────────────────────────────────────

def enumerate_wsl_distros(host: str, port: int, username: str,
                           key_path: str = None, password: str = None) -> list[str]:
    """
    SSH to a Windows host and return a list of installed WSL distribution names.
    Returns an empty list if enumeration fails or no distros are found.
    """
    try:
        import paramiko
    except ImportError:
        return []

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        _connect(client, host, port, username, key_path, password)

        # Run via PowerShell to get consistent UTF-8 output
        cmd = 'powershell -Command "wsl --list --verbose 2>&1 | Out-String"'
        _, stdout, _ = client.exec_command(cmd)
        raw = stdout.read()

        return _parse_wsl_list(raw)

    except Exception as e:
        print(f'  Could not enumerate WSL distributions: {e}')
        return []
    finally:
        client.close()


def _parse_wsl_list(raw: bytes) -> list[str]:
    """Parse the output of 'wsl --list --verbose' into distro name strings."""
    distros = []
    # Windows may encode output as UTF-16 LE; try several encodings
    for enc in ('utf-8', 'utf-16-le', 'latin-1'):
        try:
            text = raw.decode(enc)
            # Strip BOM / null bytes
            text = text.replace('\x00', '').lstrip('\ufeff')
            for line in text.splitlines():
                line = line.strip().lstrip('*').strip()
                if not line:
                    continue
                # Skip header / separator lines
                if line.upper().startswith('NAME') or set(line) <= {'-', ' '}:
                    continue
                name = line.split()[0]
                if name:
                    distros.append(name)
            if distros:
                return distros
        except (UnicodeDecodeError, ValueError):
            continue
    return distros


# ── First-time remote setup ───────────────────────────────────────────────────

def first_time_remote_setup(host: str, port: int, username: str,
                             os_type: str, wsl_distro: str = None,
                             key_path: str = None, password: str = None) -> bool:
    """
    On the remote system:
      1. Ensure screen is installed (apt-get if missing).
      2. Push the simpleScreen .screenrc template to ~/.screenrc.
    Returns True on success.
    """
    try:
        import paramiko
    except ImportError:
        print('  paramiko not installed — skipping remote setup.')
        return False

    import base64

    screenrc_path = get_screenrc_template_path()
    with open(screenrc_path, 'r') as f:
        screenrc_content = f.read()

    # Encode the screenrc as base64 so no shell quoting is needed when
    # transferring the file.  base64 output is A-Za-z0-9+/= only — safe
    # in every shell context.
    screenrc_b64 = base64.b64encode(screenrc_content.encode('utf-8')).decode('ascii')

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        _connect(client, host, port, username, key_path, password)

        def run(cmd: str) -> int:
            _, stdout, _ = client.exec_command(cmd)
            return stdout.channel.recv_exit_status()

        if os_type == 'wsl':
            # All WSL commands are wrapped in PowerShell so they bypass cmd.exe.
            # In PowerShell, single-quoted strings '...' are fully literal — the
            # operators |, >, &&, || inside them reach bash unchanged.
            def wsl(bash_cmd: str) -> int:
                ps = f"powershell -NonInteractive -Command \"wsl -d {wsl_distro} -e bash -c '{bash_cmd}'\""
                return run(ps)

            print('  Checking if screen is installed in WSL...')
            if wsl('which screen') != 0:
                print('  Installing screen in WSL (this may take a moment)...')
                wsl('sudo apt-get update -q && sudo apt-get install -y screen')

            # Write .screenrc via base64 decode — no quoting issues
            wsl(f'echo {screenrc_b64} | base64 -d > ~/.screenrc')

        elif os_type == 'linux':
            # Linux SSH server runs bash natively — no cmd.exe layer.
            print('  Checking if screen is installed...')
            if run('which screen') != 0:
                print('  Installing screen...')
                run('sudo apt-get update -q && sudo apt-get install -y screen')

            run(f'echo {screenrc_b64} | base64 -d > ~/.screenrc')

        elif os_type == 'windows':
            # Nothing to do — Windows sessions use tmux via WSL or just PowerShell
            pass

        print('  Remote setup complete.')
        return True

    except Exception as e:
        print(f'  Remote setup failed: {e}')
        return False
    finally:
        client.close()


# ── Session connection ────────────────────────────────────────────────────────

def connect_session(session: dict, password: str = None):
    """
    Launch an interactive SSH session.
    Uses the system 'ssh' binary with -t for proper TTY allocation so
    GNU screen renders correctly.
    """
    host      = session['host']
    port      = session.get('port', 22)
    username  = session['username']
    os_type   = session['os_type']
    distro    = session.get('wsl_distro', '')
    path      = session.get('remote_path') or '~'
    name      = session['name']
    key_path  = session.get('ssh_key_path')

    # ── Build the remote command string ──────────────────────────────────────
    if os_type == 'linux':
        # screen -R: reattach if a session exists, otherwise create a new one.
        remote_cmd = f'cd {path}; screen -R {name}'

    elif os_type == 'wsl':
        # Route through PowerShell so cmd.exe on the Windows SSH server never
        # sees the bash operators (;, |, >, &&).  PowerShell single-quoted
        # strings are fully literal, so the bash command arrives intact.
        # screen -R handles both attach-existing and create-new in one flag.
        bash_cmd = f'cd {path}; screen -R {name}'
        remote_cmd = f"powershell -NonInteractive -Command \"wsl -d {distro} -e bash -c '{bash_cmd}'\""

    elif os_type == 'windows':
        # Windows: connect to a PowerShell session and navigate to the path.
        # screen isn't available natively; the user gets a persistent PowerShell.
        remote_cmd = f'powershell -NoExit -Command "Set-Location \'{path}\'"'

    else:
        remote_cmd = ''

    # ── Assemble ssh command ──────────────────────────────────────────────────
    cmd = [
        'ssh',
        '-t',                           # force TTY (required for screen)
        '-p', str(port),
        '-o', 'StrictHostKeyChecking=accept-new',
        '-o', 'ServerAliveInterval=60',
        '-o', 'ServerAliveCountMax=3',
    ]

    if key_path and Path(key_path).exists():
        cmd += ['-i', key_path]

    cmd.append(f'{username}@{host}')

    if remote_cmd:
        cmd.append(remote_cmd)

    print(f'\n  Connecting to {name}...')
    if os_type != 'windows':
        print('  Press Ctrl-Q to detach (session keeps running remotely).')
    print()

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print("  Error: 'ssh' command not found.")
        if os.name == 'nt':
            print('  Enable OpenSSH: Settings → Apps → Optional Features → OpenSSH Client')
        sys.exit(1)
