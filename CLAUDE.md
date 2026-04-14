# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development setup

No build step — pure Python.

```bash
pip install -r requirements.txt
python simpleScreen help
```

Run directly:
```bash
python simpleScreen                # interactive picker
python simpleScreen new            # setup wizard
python simpleScreen list           # list sessions
python simpleScreen <name>         # connect to a session
python simpleScreen delete <name>
python simpleScreen edit <name>
```

On Windows, `simpleScreen.bat` is the thin launcher that prefers `py -3` over `python`.

## Architecture

The entry point (`simpleScreen`) handles CLI argument dispatch and calls into `lib/`. The flow for every connection is:

1. `db.init_db()` — ensures the SQLite DB exists
2. `wizard.create_new_session()` — interactive setup, saved to SQLite
3. `_connect_session()` — dispatches to `local_manager` or `ssh_manager` based on `session['type']`

### lib/ modules

- **`db.py`** — SQLite session storage at `%APPDATA%\simpleScreen\sessions.db` (Windows) or `~/.simpleScreen/sessions.db`. Schema: name, type, host, port, os\_type, wsl\_distro, path, ssh\_key\_path, created\_at, last\_connected. Passwords are never stored here.
- **`credentials.py`** — OS keyring wrapper (`save_password`, `get_password`, `delete_password`). Windows: Credential Manager; Linux: GNOME Secret Service / KWallet; macOS: Keychain.
- **`ssh_manager.py`** — All SSH operations. Uses `paramiko` only for setup tasks (key copy, WSL enumeration, first-time bootstrap, directory browsing); uses the system `ssh` binary for the interactive session itself so terminal emulation works correctly. `connect_session` builds the full `ssh -t` command.
- **`local_manager.py`** — Local sessions: WSL + screen on Windows, native screen on Linux/macOS, tmux fallback.
- **`wizard.py`** — Multi-step interactive wizard (`create_new_session`, `_wizard_local`, `_wizard_remote`). Reads `~/.ssh/known_hosts` and `~/.ssh/config` to pre-populate host suggestions.
- **`filebrowser.py`** — Vim-style curses file browser. `browse_local` uses the local filesystem; `browse_remote` fetches listings via paramiko (`ls -1p`, WSL-wrapped for WSL targets). Uses `posixpath` for all remote paths. Auto-installs `windows-curses` on Windows if missing. Falls back to a numbered list if curses is unavailable.
- **`ui.py`** — Terminal UI primitives: `menu`, `prompt`, `confirm`, `header`, `info`, `warn`, `error`, `success`, `print_session_summary`, `print_sessions_table`.

### Key architectural rules

- **`ssh` binary** for interactive sessions; **paramiko** only for non-interactive setup operations.
- **PowerShell wrapper for WSL commands**: Windows OpenSSH Server's default shell is `cmd.exe`, which treats `|`, `>`, `&&`, `||` as operators even inside single-quoted strings. All WSL invocations are wrapped as `powershell -NonInteractive -Command "wsl -d <distro> -e bash -c '...'"` to make single quotes truly literal.
- **base64 for file transfers** (e.g. pushing `.screenrc`): avoids the cmd.exe / PowerShell / bash multi-layer quoting minefield — base64 output is only `A-Za-z0-9+/=`.
- **`posixpath` for remote paths, `pathlib` for local paths** — never mix them.
- **`screen -xRR`** for attach-or-create with multi-display support.

### SSH key locations

- Windows: `%APPDATA%\simpleScreen\keys\ss_<session_name>`
- Linux/macOS: `~/.simpleScreen/keys/ss_<session_name>`

On Windows hosts, `copy_public_key` writes to both `%USERPROFILE%\.ssh\authorized_keys` and `C:\ProgramData\ssh\administrators_authorized_keys` (required for Administrators group users).

### templates/screenrc

Pushed to remote systems via base64 on first connect. Configures: `Ctrl-Q` = detach, 10k scrollback, status bar, UTF-8, autodetach on hangup.
