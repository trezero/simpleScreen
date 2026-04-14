"""
Local session management for simpleScreen.

On Windows  → launches a WSL screen session (preferred) or a tmux session.
On Linux/Mac → launches a screen session directly.
"""

import os
import subprocess
import sys
from pathlib import Path


def connect_local_session(session: dict):
    """Attach to (or create) a local screen/tmux session."""
    name = session['name']
    path = session.get('remote_path') or '~'
    wsl_distro = session.get('wsl_distro')

    print(f'\n  Connecting to local session: {name}')
    print('  Press Ctrl-Q to detach (session keeps running locally).\n')

    if os.name == 'nt':
        _connect_windows(name, path, wsl_distro=wsl_distro)
    else:
        _connect_unix(name, path)


def _connect_windows(name: str, path: str, wsl_distro: str = None):
    """
    On Windows, prefer running screen inside WSL.
    Falls back to a plain cmd/PowerShell window if WSL is unavailable.
    """
    # Check WSL availability
    wsl_check = subprocess.run(
        ['wsl', '--status'],
        capture_output=True, text=True
    )

    if wsl_check.returncode == 0:
        # Use WSL screen session; target a specific distro if one was recorded
        inner = f"cd {path} && screen -xRR {name}"
        wsl_cmd = ['wsl']
        if wsl_distro:
            wsl_cmd += ['-d', wsl_distro]
        wsl_cmd += ['--', 'bash', '-c', inner]
        subprocess.run(wsl_cmd)
    else:
        # No WSL — try tmux (Git Bash / MSYS2 users may have it)
        tmux_check = subprocess.run(['tmux', '-V'], capture_output=True)
        if tmux_check.returncode == 0:
            _connect_tmux(name, path)
        else:
            print('  WSL not found and tmux not available.')
            print('  Install WSL: wsl --install')
            print('  Or install tmux via Git Bash / Scoop / Chocolatey.')
            sys.exit(1)


def _connect_unix(name: str, path: str):
    """On Linux/Mac use screen directly."""
    screen_cmd = f"cd {path} && screen -xRR {name}"
    subprocess.run(['bash', '-c', screen_cmd])


def _connect_tmux(name: str, path: str):
    """
    Attach to an existing tmux session or create a new one.
    Used as fallback on Windows when WSL is unavailable.
    """
    # Check if session exists
    check = subprocess.run(
        ['tmux', 'has-session', '-t', name],
        capture_output=True
    )
    if check.returncode == 0:
        subprocess.run(['tmux', 'attach-session', '-t', name])
    else:
        subprocess.run([
            'tmux', 'new-session',
            '-s', name,
            '-c', path,
        ])
