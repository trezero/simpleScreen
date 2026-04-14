"""
Interactive filesystem browser for simpleScreen path selection.

Local sessions  → navigates the local filesystem.
Remote sessions → fetches listings via paramiko SSH exec, displays locally.

Curses UI (vim-style keys):
  j / Down Arrow   move cursor down
  k / Up Arrow     move cursor up
  Enter            descend into highlighted directory
  u  or  -         go up one level
  ~                jump to home directory
  g                jump to top of list
  G                jump to bottom of list
  .                toggle hidden files/directories
  Space  or  s     SELECT the current directory and return it
  q  or  Escape    cancel — return the path unchanged

Falls back to a simple numbered-list browser if curses is unavailable
(e.g. on Windows before windows-curses is installed).
"""

import os
import posixpath
from pathlib import Path


# ── Path helpers ──────────────────────────────────────────────────────────────
# Remote paths are always POSIX (Linux/WSL). pathlib.Path on Windows converts
# forward slashes to backslashes, which then breaks ls commands on the remote.
# Use posixpath for remote operations and pathlib only for local ones.

def _pjoin(base: str, name: str, remote: bool) -> str:
    """Join a path segment — POSIX join for remote, Path join for local."""
    return posixpath.join(base, name) if remote else str(Path(base) / name)


def _pparent(path: str, remote: bool) -> str:
    """Return the parent directory — POSIX dirname for remote, Path.parent for local."""
    if remote:
        parent = posixpath.dirname(path.rstrip('/'))
        return parent if parent else '/'
    p = Path(path).parent
    return str(p)

try:
    import curses
    _CURSES_OK = True
except ImportError:
    import os, subprocess, sys
    if os.name == 'nt':
        # windows-curses is not bundled with Python on Windows — install it now.
        print('  Installing windows-curses for the file browser...')
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--quiet', 'windows-curses'],
            check=False,
        )
        try:
            import curses
            _CURSES_OK = True
        except ImportError:
            _CURSES_OK = False
    else:
        _CURSES_OK = False


# ── Public API ────────────────────────────────────────────────────────────────

def browse_local(start: str = '~', title: str = 'Select directory') -> str:
    """
    Open an interactive browser of the local filesystem.
    Returns the selected path string, or `start` unchanged if cancelled.
    """
    resolved = str(Path(start).expanduser().resolve())

    if _CURSES_OK:
        try:
            result = curses.wrapper(_curses_ui, resolved, title, _list_local, None)
            return result if result is not None else resolved
        except Exception:
            pass  # fall through to simple browser

    return _simple_browser(resolved, title, _list_local, None)


def browse_remote(host: str, port: int, username: str,
                  start: str = '~',
                  title: str = 'Select remote directory',
                  key_path: str = None,
                  password: str = None,
                  os_type: str = 'linux',
                  wsl_distro: str = None) -> str:
    """
    Open an interactive browser of a remote filesystem.
    Directory listings are fetched via paramiko SSH exec.
    Returns the selected path string, or `start` unchanged on cancel/error.
    """
    try:
        import paramiko
    except ImportError:
        print('  paramiko not available — type the path manually.')
        return start

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_path and Path(key_path).exists():
            client.connect(host, port=port, username=username,
                           key_filename=key_path, timeout=10)
        elif password:
            client.connect(host, port=port, username=username,
                           password=password, timeout=10)
        else:
            print('  No credentials available for remote browsing.')
            return start
    except Exception as e:
        print(f'  Could not connect for directory browsing: {e}')
        return start

    context = {
        'client':     client,
        'os_type':    os_type,
        'wsl_distro': wsl_distro or '',
    }

    resolved_start = _resolve_remote_home(context, start)

    try:
        if _CURSES_OK:
            try:
                result = curses.wrapper(
                    _curses_ui, resolved_start, title, _list_remote, context
                )
                return result if result is not None else resolved_start
            except Exception:
                pass

        return _simple_browser(resolved_start, title, _list_remote, context)
    finally:
        client.close()


# ── Shared curses UI ──────────────────────────────────────────────────────────

def _curses_ui(stdscr, start: str, title: str, list_fn, context):
    """
    Curses frontend shared by local and remote browsers.
    list_fn(path, context) must return list of (name: str, is_dir: bool).
    Returns the selected path string or None if cancelled.
    """
    curses.curs_set(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # selected row
        curses.init_pair(2, curses.COLOR_CYAN,  -1)                  # directory
        curses.init_pair(3, curses.COLOR_GREEN, -1)                  # header text

    current     = start
    cursor      = 0
    scroll      = 0
    show_hidden = False
    status_msg  = ''
    entries     = []

    while True:
        # ── Fetch entries ────────────────────────────────────────────────────
        try:
            raw = list_fn(current, context)
            entries = raw if show_hidden else [e for e in raw if not e[0].startswith('.')]
        except Exception as exc:
            entries = []
            status_msg = str(exc)

        stdscr.erase()
        h, w = stdscr.getmaxyx()

        # ── Header ──────────────────────────────────────────────────────────
        hattr = (curses.color_pair(3) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD
        _put(stdscr, 0, 0, f' {title} ', hattr, w)
        _put(stdscr, 1, 0, f' {current} ', 0, w)
        _put(stdscr, 2, 0,
             ' j/k:move  Enter:open  Space:select dir  u:up  .:hidden  ~:home  q:cancel ',
             0, w)
        _put(stdscr, 3, 0, '─' * (w - 1), 0, w)

        # ── Entry list ───────────────────────────────────────────────────────
        list_top = 4
        visible  = max(1, h - list_top - 1)

        cursor = max(0, min(cursor, len(entries) - 1 if entries else 0))
        if cursor < scroll:
            scroll = cursor
        if cursor >= scroll + visible:
            scroll = cursor - visible + 1

        for i, (name, is_dir) in enumerate(entries[scroll: scroll + visible]):
            row = list_top + i
            idx = scroll + i
            line = f'  {"/" if is_dir else " "} {name}'

            if idx == cursor:
                attr = curses.color_pair(1) if curses.has_colors() else curses.A_REVERSE
                _put(stdscr, row, 0, line.ljust(min(w - 1, 80)), attr, w)
            elif is_dir:
                attr = curses.color_pair(2) if curses.has_colors() else 0
                _put(stdscr, row, 0, line, attr, w)
            else:
                _put(stdscr, row, 0, line, 0, w)

        # ── Status bar ───────────────────────────────────────────────────────
        if status_msg:
            bar = f' Error: {status_msg} '
        elif entries:
            bar = f' [{cursor + 1}/{len(entries)}]   Press Space to select this directory '
        else:
            bar = ' (empty directory) '
        _put(stdscr, h - 1, 0, bar[: w - 1], 0, w)

        stdscr.refresh()
        status_msg = ''

        # ── Key handling ─────────────────────────────────────────────────────
        key = stdscr.getch()

        if key in (ord('q'), 27):                       # cancel
            return None

        elif key in (ord(' '), ord('s')):               # select current dir
            return current

        elif key in (ord('j'), curses.KEY_DOWN):
            if entries:
                cursor = min(cursor + 1, len(entries) - 1)

        elif key in (ord('k'), curses.KEY_UP):
            cursor = max(cursor - 1, 0)

        elif key == ord('g'):
            cursor = 0

        elif key == ord('G'):
            cursor = max(0, len(entries) - 1)

        elif key in (ord('u'), ord('-'), curses.KEY_BACKSPACE, 127):
            parent = _pparent(current, context is not None)
            if parent != current:
                current = parent
                cursor = 0
                scroll = 0

        elif key == ord('~'):
            if context is None:                         # local
                current = str(Path.home())
            else:                                       # remote: re-resolve ~
                current = _resolve_remote_home(context, '~')
            cursor = 0
            scroll = 0

        elif key == ord('.'):
            show_hidden = not show_hidden
            cursor = 0
            scroll = 0

        elif key in (curses.KEY_ENTER, 10, 13):         # descend into dir
            if entries and cursor < len(entries):
                name, is_dir = entries[cursor]
                if is_dir:
                    current = _pjoin(current, name, context is not None)
                    cursor = 0
                    scroll = 0


def _put(stdscr, row: int, col: int, text: str, attr: int, width: int):
    """Safe addstr that never raises on the terminal's last cell."""
    try:
        stdscr.addstr(row, col, text[: width - 1], attr)
    except curses.error:
        pass


# ── Directory listing ─────────────────────────────────────────────────────────

def _list_local(path: str, _context) -> list[tuple[str, bool]]:
    """Return sorted (name, is_dir) entries for a local directory."""
    entries = []
    for item in sorted(Path(path).iterdir(),
                       key=lambda p: (not p.is_dir(), p.name.lower())):
        entries.append((item.name, item.is_dir()))
    return entries


def _list_remote(path: str, context: dict) -> list[tuple[str, bool]]:
    """
    Return sorted (name, is_dir) entries for a remote directory.
    Uses 'ls -1p' (POSIX: appends / to dirs) via SSH exec.
    For WSL targets the command is wrapped in 'wsl -d <distro> -- bash -c ...'.
    """
    client   = context['client']
    os_type  = context.get('os_type', 'linux')
    distro   = context.get('wsl_distro', '')

    inner = f"ls -1p '{path}' 2>/dev/null"
    cmd   = f"wsl -d {distro} -- bash -c \"{inner}\"" if os_type == 'wsl' else inner

    _, stdout, _ = client.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='ignore')

    entries = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line in ('./', '../', '.', '..'):
            continue
        is_dir = line.endswith('/')
        name   = line.rstrip('/')
        if name:
            entries.append((name, is_dir))

    entries.sort(key=lambda e: (not e[1], e[0].lower()))
    return entries


def _resolve_remote_home(context: dict, path: str) -> str:
    """Expand ~ on the remote (runs inside WSL for WSL targets)."""
    if '~' not in path:
        return path

    client  = context['client']
    os_type = context.get('os_type', 'linux')
    distro  = context.get('wsl_distro', '')

    inner = f'echo {path}'
    cmd   = f"wsl -d {distro} -- bash -c \"{inner}\"" if os_type == 'wsl' else inner

    _, stdout, _ = client.exec_command(cmd)
    result = stdout.read().decode('utf-8', errors='ignore').strip()
    return result if result else path


# ── Simple fallback browser ───────────────────────────────────────────────────

def _simple_browser(start: str, title: str, list_fn, context) -> str:
    """
    Non-curses fallback. Shows a numbered list of sub-directories.
    Type a number to navigate, or press Enter to select the current directory.
    """
    current = start

    while True:
        print(f'\n  {title}')
        print(f'  Current : {current}')
        print()

        try:
            all_entries = list_fn(current, context)
            dirs = [e for e in all_entries if e[1]]
        except Exception as exc:
            dirs = []
            print(f'  (could not list directory: {exc})')

        print('    0.  ..  (go up one level)')
        for i, (name, _) in enumerate(dirs[:24], 1):
            print(f'  {i:>3}.  {name}/')
        if len(dirs) > 24:
            print(f'       ... and {len(dirs) - 24} more')

        print()
        print('  Number → navigate   Path → jump directly   Enter → SELECT this directory')
        raw = input('  > ').strip()

        if raw == '':
            return current

        if raw == '0':
            parent = _pparent(current, context is not None)
            if parent != current:
                current = parent
            continue

        try:
            idx = int(raw) - 1
            if 0 <= idx < len(dirs):
                current = _pjoin(current, dirs[idx][0], context is not None)
            continue
        except ValueError:
            pass

        # Treat as a literal path or partial name
        candidate = Path(raw).expanduser()
        if candidate.is_dir():
            current = str(candidate.resolve())
        else:
            print(f'  Not a directory: {raw}')
