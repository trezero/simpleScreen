# simpleScreen

GNU `screen` is one of the most useful tools in Linux — start a long-running process, disconnect your laptop, come back a day later and pick up exactly where you left off. But the commands are hard to remember, and setting up a remote SSH + screen workflow from a Windows machine (especially into WSL on another Windows machine) is fiddly enough that most people give up.

**simpleScreen** fixes that. You answer a short wizard once per remote machine. After that, one command connects you, and one keypress (**`Ctrl-Q`**) safely disconnects while your work keeps running on the remote side.

```
simpleScreen personalFinanceAI_WSL230
```

No IP addresses, no SSH flags, no screen syntax, no remembering WSL distro names.

---

## Contents

- [Why this exists](#why-this-exists)
- [What you get](#what-you-get)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start — your first session](#quick-start--your-first-session)
- [All commands](#all-commands)
- [Session types](#session-types)
- [Scanning for existing sessions](#scanning-for-existing-sessions)
- [The file browser](#the-file-browser)
- [SSH key setup](#ssh-key-setup)
- [Key bindings inside a session](#key-bindings-inside-a-session)
- [Where data is stored](#where-data-is-stored)
- [How the WSL flow actually works](#how-the-wsl-flow-actually-works)
- [Troubleshooting](#troubleshooting)
- [Project structure](#project-structure)
- [Contributing](#contributing)

---

## Why this exists

If you've ever wanted to:

- Start a long Claude Code session on a beefy desktop, close your laptop, and come back to the output an hour later
- SSH into WSL on another Windows machine without manually discovering which distro is installed
- Avoid re-typing `ssh -t winadmin@172.16.1.230 "wsl -d Ubuntu-22.04 -- bash -c 'cd /home/winadmin/projects/foo && screen -xRR foo'"` every time
- Stop Googling "how do I detach a screen session again"
- Sit down at your desktop and pick up a session you started from your laptop — without SSH, using your local machine's WSL directly

…then this is for you.

---

## What you get

- **Named session profiles** stored in a local SQLite database — host, port, OS type, WSL distro, working directory, SSH key, all saved once
- **Automatic SSH key setup** — the wizard generates an ed25519 key per session and copies it to the remote machine (enters your password once, then never again)
- **Scan for existing sessions** — discover running screen sessions on any local or remote machine and import them into your profile list with a single command, no re-configuration required
- **Interactive file browser** for picking both local and remote paths — vim-style (`j`/`k` to navigate, `Enter` to descend, `Space` to select) — works over SSH so you can browse the actual remote filesystem, including inside WSL
- **Automatic WSL detection** on remote Windows hosts — the wizard runs `wsl --list` over SSH and shows you a menu
- **Automatic remote bootstrap** — installs `screen` via apt if missing, and pushes a preconfigured `.screenrc` that binds `Ctrl-Q` to detach
- **`Ctrl-Q` to detach** — no more "was it Ctrl-A D or Ctrl-A d?"
- **Works for remote Linux, remote WSL, remote Windows, and local sessions** (local uses WSL/screen on Windows, or native screen on Linux/macOS)
- **Isolated Python environment** — dependencies are installed into a self-contained virtual environment inside the install directory; your base Python is never touched
- **Cross-platform** — the same installer story works on Windows (via winget for Python) and Linux/macOS

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.8+ | Windows installer installs it via `winget` automatically if missing |
| OpenSSH client (`ssh` in `PATH`) | Built into Windows 10/11 (optional feature); standard on Linux/macOS |
| `ssh-keygen` | Bundled with OpenSSH |
| **Remote machine:** SSH server running | `sshd` on Linux; the **OpenSSH Server** feature enabled on Windows for WSL targets |
| **Remote WSL host:** WSL installed | Only needed if you're targeting a WSL distribution on a remote Windows machine |
| Remote: `sudo` / `apt-get` | Only used the first time you connect to a new Linux or WSL target — to install `screen` if it isn't already there |

The installers create a Python virtual environment and install `paramiko`, `keyring`, and `windows-curses` (Windows only) into it automatically. Your base Python installation is not modified.

---

## Installation

### Windows

```bat
git clone https://github.com/YOUR_USERNAME/simpleScreen
cd simpleScreen
install.bat
```

The installer will:
1. Check for Python 3; install via `winget install Python.Python.3.12` if missing
2. Create a virtual environment at `%APPDATA%\simpleScreen\venv`
3. `pip install` the Python dependencies (`paramiko`, `keyring`, `windows-curses`) into the venv
4. Copy the application to `%APPDATA%\simpleScreen\`
5. Add that directory to your user `PATH` via `setx`
6. Verify the OpenSSH client is available

After it finishes, **open a new terminal window** and type `simpleScreen`. (PATH changes only take effect in new shells.)

**Reinstalling / updating:** re-running `install.bat` is safe — if the venv already exists it is reused and packages are updated in place.

### Linux / macOS

```bash
git clone https://github.com/YOUR_USERNAME/simpleScreen
cd simpleScreen
chmod +x install.sh
./install.sh
```

The installer will:
1. Verify Python 3 is available (gives you the exact install command if not)
2. Create a virtual environment at `~/.local/share/simpleScreen/venv`
3. `pip install` the Python dependencies (`paramiko`, `keyring`) into the venv
4. Copy the application to `~/.local/share/simpleScreen/`
5. Create a launcher at `~/.local/bin/simpleScreen` that invokes the venv Python directly
6. Add `~/.local/bin` to your `PATH` in `~/.bashrc` or `~/.zshrc` if it isn't already there

Open a new terminal (or `source ~/.bashrc`) and type `simpleScreen`.

---

## Quick start — your first session

The most common workflow: remote WSL on another Windows machine.

```
$ simpleScreen new

  ====================================================
  Create New Session
  ====================================================

  Session name: personalFinanceAI_WSL230

  Session type:
    1. Remote (SSH connection to another machine)
    2. Local (on this machine)
  Choose (1-2): 1

  Known hosts detected — pick one or choose "Enter manually".
    1. 172.16.1.230
    2. Enter manually
  Host (1-2): 1

  SSH port [22]:

  Remote OS type:
    1. Linux
    2. WSL (on a remote Windows machine)
    3. Windows
  Choose (1-3): 2

  Username [jason]: winadmin

  Authentication method:
    1. SSH key (recommended — set up automatically)
    2. Password (stored in system keyring)
  Choose (1-2): 1

  Generating SSH key for 'personalFinanceAI_WSL230'...
  [OK] Key: C:\Users\jason\AppData\Roaming\simpleScreen\keys\ss_personalFinanceAI_WSL230

  To install the key on 172.16.1.230, your password is needed once.
  It will NOT be stored after this step.
  Password (temporary, for key copy): ●●●●●●●●

  Copying public key to remote host...
  [OK] Key copied — future connections will not require a password.

  Detecting WSL distributions on remote Windows host...
  [OK] Found 2 distribution(s):
    1. Ubuntu-22.04
    2. docker-desktop
  WSL distribution (1-2): 1

  Browse the remote filesystem to select your working directory.
  Space = select   Enter = open dir   u = up   q = cancel
       [ file browser opens — navigate to the right directory ]
  [OK] Selected: /home/winadmin/projects/personalFinanceAI

  ----------------------------------------------------
  Session Profile Summary
  ----------------------------------------------------
  Name       : personalFinanceAI_WSL230
  Type       : remote
  Host       : 172.16.1.230:22
  OS         : wsl
  Username   : winadmin
  WSL Distro : Ubuntu-22.04
  Path       : /home/winadmin/projects/personalFinanceAI
  Auth       : SSH key (C:\...\ss_personalFinanceAI_WSL230)
  ----------------------------------------------------

  Save this session? (Y/n): y

  Performing first-time remote setup...
  Checking if screen is installed in WSL...
  [OK] Remote setup complete.
  [OK] Session saved and ready.

  Connect now? (Y/n): y

  Connecting to personalFinanceAI_WSL230...
  Press Ctrl-Q to detach (session keeps running remotely).

  winadmin@WIN-AI-PC:/home/winadmin/projects/personalFinanceAI$
```

You are now inside a screen session running inside Ubuntu 22.04 on the remote Windows machine, in your project directory. Start a long-running process (`claude`, a build, a training job) and press **`Ctrl-Q`** when you need to leave. The process keeps running.

### Reconnect later

```
$ simpleScreen personalFinanceAI_WSL230
```

You land back in the exact same terminal state — same commands in scrollback, same process still running, same cursor position.

---

## All commands

| Command | Description |
|---|---|
| `simpleScreen` | Open the interactive session picker |
| `simpleScreen <name>` | Connect directly to a named session |
| `simpleScreen new` | Run the setup wizard to create a new session |
| `simpleScreen list` | Print a table of all saved sessions |
| `simpleScreen delete <name>` | Delete a session profile (asks for confirmation) |
| `simpleScreen edit <name>` | Re-run the wizard for an existing session (existing values prefilled as defaults) |
| `simpleScreen help` | Show usage |

### Interactive mode

Running `simpleScreen` with no arguments opens a numbered menu:

```
  ====================================================
  simpleScreen
  ====================================================

  1. personalFinanceAI_WSL230  (remote, 172.16.1.230)
  2. devServer                 (remote, 10.0.0.5)
  3. localDev                  (local)
  4. ── Create new session
  5. ── Scan for existing sessions
  6. ── List all sessions
  7. ── Exit

  Connect to session or choose an action (1-7):
```

---

## Session types

### Remote — Linux

Standard SSH connection. simpleScreen:
- Connects over SSH to the Linux host
- Runs `cd <path>; screen -xRR <name>` — `-xRR` attaches to an existing session (including one already attached elsewhere, for multi-display), or creates one if none exists
- Ctrl-Q detaches; the SSH connection closes but the screen session keeps running

### Remote — WSL (on another Windows machine)

The most common setup for cross-machine development. simpleScreen:
- Connects over SSH to the **Windows** host (the Windows OpenSSH Server feature must be enabled)
- Wraps the command in PowerShell: `powershell -NonInteractive -Command "wsl -d Ubuntu-22.04 -e bash -c 'cd <path>; screen -xRR <name>'"` — this routes through PowerShell because Windows `cmd.exe` (the default shell for OpenSSH Server) would otherwise interpret `;`, `|`, `>`, `&&` inside the command as operators
- Inside WSL, `screen -xRR` attaches (multi-display allowed) or creates the session
- When you detach, the SSH connection closes, but the screen session persists inside WSL — WSL keeps the distribution alive because a process (screen) is still running

> **Prerequisite:** The **OpenSSH Server** optional feature must be enabled on the remote Windows machine.
> *Settings → Apps → Optional Features → Add a feature → OpenSSH Server*

### Remote — Windows

Connects over SSH to a Windows machine and opens a PowerShell session in the chosen path. GNU screen isn't available natively on Windows, so this mode gives you a persistent PowerShell rather than a detachable screen session. Useful for Windows-native administration.

### Local

Creates or reconnects to a screen session on the current machine.

- **On Windows:** launches a WSL screen session (preferred). Falls back to `tmux` if WSL is not available.
- **On Linux/macOS:** uses GNU `screen` directly.

---

## Scanning for existing sessions

The **scan** feature lets you discover screen sessions already running on a machine and import them into your profile list — no wizard required. This is especially useful when you started a session from one machine (e.g. your laptop) and want to join it from another machine (e.g. sitting at the desktop where the WSL instance is actually running).

### How it works

From the main menu, choose **`── Scan for existing sessions`**, then:

1. **Local or Remote?**
   - *Local* — scans screen sessions running on this machine (WSL distro on Windows, native screen on Linux/macOS)
   - *Remote* — scans a machine reachable over SSH

2. **OS type** — WSL, Linux, or Windows *(Windows has no screen support; the scanner will tell you)*

3. **For WSL** — the scanner enumerates available distros (same auto-detection used by the wizard) and lets you choose one

4. **For Remote** — you provide a host, port, username, and authentication (SSH key or password); the scanner connects via paramiko, not the interactive `ssh` binary, so no TTY is needed

5. **Session list** — the scanner runs `screen -ls` on the target and displays the results:

```
  1. personalFinanceAI_WSL230         [Detached]  pid:12345
  2. devBuild                         [Attached]   pid:67890

  Enter numbers to import (e.g. 1  or  1,3  or  1-3), 'a' for all, 'q' to cancel:
  Selection: a
```

6. **Import** — selected sessions are saved as profiles in your local database. If a name already exists, you are offered the choice to overwrite, rename, or skip.

Once imported, the sessions appear in the main menu and can be connected to with `simpleScreen <name>` like any other profile.

### Example: picking up a laptop session at your desktop

```
$ simpleScreen
  ...
  4. ── Scan for existing sessions

  Scan location (1-2):
    1. Local (this machine)
    2. Remote (another machine via SSH)
  > 1

  Available WSL distributions:
    1. Ubuntu-22.04
    2. docker-desktop
  Choose WSL distro (1-2): 1

  Scanning for screen sessions...
  [OK] Found 1 screen session(s):

  1. personalFinanceAI_WSL230         [Attached]   pid:12345

  Selection: 1

  [OK] Imported 'personalFinanceAI_WSL230'  (screen: 12345.personalFinanceAI_WSL230)

  1 session(s) added. Connect with:
    simpleScreen personalFinanceAI_WSL230
```

The session shows as `[Attached]` because your laptop is still connected to it. Running `simpleScreen personalFinanceAI_WSL230` from the desktop attaches a second view of the same session — both screens stay in sync.

---

## The file browser

When the wizard asks you for a **Local path** or **Remote path**, it opens an interactive vim-style file browser instead of a plain text prompt.

### Navigation keys

| Key | Action |
|---|---|
| `j` or `↓` | Move cursor down |
| `k` or `↑` | Move cursor up |
| `Enter` | Descend into the highlighted directory |
| `Space` or `s` | **Select** the current directory (done) |
| `u` or `-` | Go up one level |
| `~` | Jump to home directory |
| `g` | Jump to top of list |
| `G` | Jump to bottom of list |
| `.` | Toggle hidden files on/off |
| `q` or `Esc` | Cancel (keep path unchanged) |

### Local vs remote browsing

- **Local paths** use a curses browser of your own filesystem
- **Remote paths** open a browser backed by paramiko SSH — directory listings are fetched via `ls -1p` on the remote machine and rendered locally. For WSL targets the listing command is wrapped as `wsl -d <distro> -- bash -c 'ls -1p ...'` so you're browsing the **WSL filesystem**, not the Windows filesystem

### Fallback

If the `curses` module isn't available (rare — it's auto-installed on Windows via `windows-curses`), simpleScreen drops back to a simple numbered-list browser (`0` = up, `1-N` = navigate into directory, `Enter` = select current).

---

## SSH key setup

simpleScreen generates **one ed25519 key pair per session** stored in:

| Platform | Location |
|---|---|
| Windows | `%APPDATA%\simpleScreen\keys\` |
| Linux/macOS | `~/.simpleScreen/keys/` |

Keys are named `ss_<session_name>` and `ss_<session_name>.pub`. Private keys are mode `600` on Linux/macOS.

### What happens during setup

1. `ssh-keygen -t ed25519` generates the key pair
2. You enter your password **once** so simpleScreen can use paramiko to connect and append the public key to:
   - `~/.ssh/authorized_keys` on the remote user's home (Linux / macOS targets)
   - `%USERPROFILE%\.ssh\authorized_keys` **and** `C:\ProgramData\ssh\administrators_authorized_keys` (Windows / WSL targets — the second location is required for users in the Administrators group; writing to both ensures the key works either way)
3. The password is discarded immediately — it is never written to disk or stored in any database
4. All future connections use the key file silently — no password prompt

### If automatic key copy fails

simpleScreen prints the path to the `.pub` file and pauses. You can manually copy the key's contents into `authorized_keys` on the remote system, then press Enter to continue.

### Password auth fallback

If you choose password auth instead of a key, the password is stored in the **OS keyring** — Windows Credential Manager on Windows, GNOME Secret Service / KWallet on Linux, Keychain on macOS. Passwords are never written to SQLite or the filesystem.

Additionally: if key auth fails at runtime (for example the key didn't quite install correctly), simpleScreen will transparently fall back to the stored password for `enumerate_wsl_distros`, `first_time_remote_setup`, and directory browsing — so you don't get stuck.

---

## Key bindings inside a session

simpleScreen pushes a custom `.screenrc` to every remote system on first connect (via base64-encoded transfer to avoid shell quoting issues).

| Key | Action |
|---|---|
| **`Ctrl-Q`** | **Detach** — leave the session running, return to your local terminal |
| `Ctrl-A d` | Detach (standard screen binding, always works — use if `Ctrl-Q` is intercepted by your terminal) |
| `Ctrl-A c` | Create a new window |
| `Ctrl-A n` / `p` | Next / previous window |
| `Ctrl-A "` | Show a list of all open windows |
| `Ctrl-A 0`–`9` | Switch directly to window number 0–9 |
| `Ctrl-A k` | Kill the current window |
| `Ctrl-A S` | Split the current region horizontally |
| `Ctrl-A Tab` | Move between split regions |
| `Ctrl-A Q` | Collapse to a single region |
| `Ctrl-A ?` | Show the full screen key-binding help |

The status bar at the bottom of the terminal shows the hostname, all open windows (active one highlighted), and the current date and time.

> The default screen escape key `Ctrl-A` is unchanged. `Ctrl-Q` is an **additional** binding (`bindkey "^Q" detach`) wired directly to detach for convenience.

---

## Where data is stored

### Virtual environment

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\simpleScreen\venv\` |
| Linux/macOS | `~/.local/share/simpleScreen/venv\` |

Contains the isolated Python interpreter and all dependencies (`paramiko`, `keyring`, `windows-curses`). Your base Python installation is never modified. To fully uninstall simpleScreen, delete the install directory — the venv goes with it.

### Session profiles (SQLite)

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\simpleScreen\sessions.db` |
| Linux/macOS | `~/.simpleScreen/sessions.db` |

Contains: session name, type (local / remote), host, port, OS type, WSL distro, remote path, SSH key path, creation timestamp, last-connected timestamp. You can inspect it with any SQLite browser. **Passwords are never stored here.**

### SSH keys

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\simpleScreen\keys\` |
| Linux/macOS | `~/.simpleScreen/keys/` |

Keep these safe — anyone with a private key can connect to the associated remote session.

### Passwords (when used)

Stored exclusively in the operating system keyring:

| Platform | Backend |
|---|---|
| Windows | Windows Credential Manager |
| Linux | GNOME Secret Service / KWallet |
| macOS | Keychain |

View or remove them through the system's native credential manager, or via `simpleScreen delete <name>` (which also clears the keyring entry).

---

## How the WSL flow actually works

The Windows → WSL case has several layers, each with its own quoting rules. Understanding the pipeline helps if you ever need to debug an odd behavior.

```
  Your local terminal
        ↓
  subprocess.run(['ssh', '-t', 'user@windows-host', '<remote_cmd>'])
        ↓
  Windows OpenSSH Server runs <remote_cmd> through cmd.exe
        ↓
  cmd.exe parses the command (here's where operators like |, >, &&, || are special)
        ↓
  powershell -NonInteractive -Command "<script>"
        ↓
  PowerShell parses the script — '...' single-quoted strings are FULLY literal
        ↓
  wsl.exe -d Ubuntu-22.04 -e bash -c 'cd <path>; screen -xRR <name>'
        ↓
  bash inside WSL executes the final command
```

The critical insight: **single quotes in `cmd.exe` are NOT string delimiters** — `|`, `>`, `&&`, and `||` inside single-quoted strings are still interpreted as operators by cmd.exe. That's why simpleScreen routes all WSL commands through PowerShell, where single quotes truly are literal.

For the `.screenrc` transfer, simpleScreen base64-encodes the file content and decodes it on the remote side (`echo <b64> | base64 -d > ~/.screenrc`). base64 output is only `A-Za-z0-9+/=`, so it's safe in every shell context — no escaping needed regardless of how many quoting layers the command passes through.

The same PowerShell-wrapping strategy is used by the session scanner when running `screen -ls` on a remote WSL target.

---

## Troubleshooting

### `simpleScreen` is not recognized after install

PATH changes take effect in **new** terminal windows only. Close your current terminal and open a fresh one.

### SSH connection refused or times out

- Verify the remote machine is reachable: `ping <host>`
- Confirm the SSH server is running:
  - Linux: `sudo systemctl status sshd`
  - Windows: *Services → OpenSSH SSH Server → Status* should be *Running*
- Check that port 22 (or your custom port) is not blocked by a firewall

### WSL distributions not detected

- The **Windows OpenSSH Server** must be enabled on the remote machine (not an SSH server running inside WSL)
- Verify WSL is installed on the remote Windows machine — connect manually and run `wsl --list --verbose`
- If auto-detection fails, simpleScreen will prompt you to type the distribution name manually (e.g. `Ubuntu-22.04`)

### Authentication failed after key copy

This usually means the key landed in the wrong `authorized_keys` on a Windows host. simpleScreen writes to both the per-user and the Administrators locations, but if both are protected by unusual permissions, the next best check is:

```powershell
# On the remote Windows machine, check both files exist and contain the key:
type $env:USERPROFILE\.ssh\authorized_keys
type C:\ProgramData\ssh\administrators_authorized_keys
```

Also verify the OpenSSH Server's config (`C:\ProgramData\ssh\sshd_config`) doesn't have `PubkeyAuthentication` set to `no`.

### Scan finds no sessions

- Confirm screen is installed in the target distro: connect manually and run `screen -ls`
- For local WSL scans, confirm the correct distro is selected — sessions in `Ubuntu-22.04` are not visible from `Ubuntu-20.04`
- For remote scans, verify your credentials have SSH access before trying to scan

### Browser shows an empty remote directory

All remote path handling uses forward slashes (POSIX). If you see a path like `\home\winadmin\projects`, an older version of simpleScreen is installed — re-run `install.bat` or `install.sh` to update.

### `screen` not found on remote after first-time setup

The auto-install uses `sudo apt-get`. If the remote system uses a different package manager, install manually:
- Fedora / RHEL: `sudo dnf install screen`
- Arch: `sudo pacman -S screen`
- Then re-run `simpleScreen edit <name>` to trigger the `.screenrc` push.

### Detaching with `Ctrl-Q` does not work

Some terminal emulators intercept `Ctrl-Q` for XON/XOFF flow control. Two fallbacks:
- Use the standard screen detach: **`Ctrl-A` then `d`** — always works
- Disable flow control in your terminal settings

### OpenSSH not found on Windows

Enable the OpenSSH Client optional feature:
*Settings → Apps → Optional Features → Add a feature → OpenSSH Client*

Or install via winget:
```
winget install Microsoft.OpenSSH.Beta
```

### `paramiko` or `windows-curses` import errors

Re-run the installer — it will reinstall all dependencies into the venv. Or install manually into the venv:

```
# Windows
%APPDATA%\simpleScreen\venv\Scripts\python.exe -m pip install paramiko keyring windows-curses

# Linux / macOS
~/.local/share/simpleScreen/venv/bin/python -m pip install paramiko keyring
```

---

## Project structure

```
simpleScreen/
│
├── install.bat              Windows installer
│                            Checks/installs Python via winget using the
│                            'py' launcher (System32), creates a venv at
│                            %APPDATA%\simpleScreen\venv, pip installs deps
│                            into it, copies files to %APPDATA%\simpleScreen\,
│                            updates PATH.
│
├── install.sh               Linux / macOS installer
│                            Creates a venv at
│                            ~/.local/share/simpleScreen/venv, pip installs
│                            deps, copies to ~/.local/share/simpleScreen/,
│                            creates launcher at ~/.local/bin/simpleScreen.
│
├── simpleScreen             Main Python script (Linux/macOS entry point)
│                            Handles all subcommands and dispatches to lib/.
│
├── simpleScreen.bat         Windows launcher
│                            Invokes the venv Python directly:
│                            %~dp0venv\Scripts\python.exe
│
├── requirements.txt         Python dependencies
│                            paramiko         — SSH connections and key management
│                            keyring          — OS keyring integration for passwords
│                            windows-curses   — Windows-only, for the file browser
│
├── lib/
│   ├── __init__.py
│   │
│   ├── db.py                SQLite session storage
│   │                        init_db, save_session, get_session, list_sessions,
│   │                        delete_session, update_last_connected
│   │
│   ├── credentials.py       OS keyring wrapper with graceful fallback
│   │                        save_password, get_password, delete_password
│   │
│   ├── ui.py                Terminal UI helpers
│   │                        menu, prompt, confirm, print_session_summary,
│   │                        print_sessions_table, header, info, warn, error
│   │
│   ├── filebrowser.py       Vim-style file browser (curses)
│   │                        browse_local   — local filesystem navigation
│   │                        browse_remote  — paramiko-backed remote filesystem
│   │                        Uses posixpath for remote paths.
│   │                        Auto-installs windows-curses on Windows if missing.
│   │
│   ├── ssh_manager.py       SSH operations
│   │                        generate_ssh_key  — ed25519 via ssh-keygen
│   │                        copy_public_key   — one-time password install
│   │                        enumerate_wsl_distros  — wsl --list via SSH
│   │                        first_time_remote_setup  — install screen,
│   │                                                   push .screenrc via base64
│   │                        connect_session   — builds ssh -t command;
│   │                                            WSL calls wrapped in PowerShell,
│   │                                            uses 'screen -xRR' for
│   │                                            attach-or-create (multi-display)
│   │                        _connect          — shared helper that tries
│   │                                            key auth then falls back
│   │                                            to password
│   │
│   ├── local_manager.py     Local session management
│   │                        Windows : WSL screen (wsl -d <distro> if set),
│   │                                  tmux fallback
│   │                        Linux/macOS : screen directly
│   │
│   ├── scanner.py           Scan-for-sessions wizard
│   │                        scan_for_sessions  — main entry point
│   │                        Local scan: enumerates WSL distros via wsl -l -q,
│   │                          runs screen -ls inside the chosen distro
│   │                        Remote scan: connects via paramiko, runs
│   │                          screen -ls (Linux) or PowerShell-wrapped
│   │                          WSL variant, same quoting strategy as
│   │                          ssh_manager
│   │                        Multi-select UI supports individual numbers,
│   │                          comma/space lists, ranges (1-3), and 'a' for all
│   │                        Imports selected sessions into SQLite as full
│   │                          profiles; handles name conflicts interactively
│   │
│   └── wizard.py            Interactive setup wizard
│                            create_new_session, _wizard_local, _wizard_remote
│                            Integrates with filebrowser for path prompts.
│                            _get_known_hosts parses ~/.ssh/known_hosts + config
│                            to suggest hosts during setup.
│
└── templates/
    └── screenrc             Pushed to remote systems on first connect
                             (via base64, avoiding any shell quoting).
                             Binds Ctrl-Q = detach, 10k scrollback,
                             status bar, UTF-8, autodetach on hangup.
```

---

## Contributing

Bug reports, feature requests, and pull requests are welcome.

Areas where contributions would be especially useful:

- **Non-apt package managers** — auto-install `screen` via `yum` / `dnf` / `pacman` / `brew` on first connect
- **More SSH config parsing** — read `Host` aliases from `~/.ssh/config` as session name suggestions
- **First-class tmux support** — tmux profiles as an alternative for users who prefer tmux to screen
- **Windows-native persistent sessions** — using ConPTY instead of screen for `os_type == 'windows'`
- **Session groups / tags** — for users managing many machines

### Development setup

```bash
git clone https://github.com/YOUR_USERNAME/simpleScreen
cd simpleScreen
pip install -r requirements.txt
python simpleScreen help
```

No build step — it's pure Python.

### Architecture principles

- **SSH over system `ssh` binary** (not paramiko) for the *interactive* session, so terminal emulation works correctly
- **paramiko** only for setup tasks: key copy, WSL enumeration, first-time remote bootstrap, directory browsing, and session scanning
- **base64 for file content transfer** — avoids the cmd.exe / PowerShell / bash quoting minefield
- **PowerShell wrapper for WSL invocation** — because cmd.exe treats `|`, `>`, `&&`, `||` as operators even inside single-quoted strings
- **posixpath for remote paths, pathlib for local paths** — never mix them
- **venv for dependency isolation** — the install directories are self-contained; the user's base Python is never modified
