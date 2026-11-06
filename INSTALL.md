# Network Ping Pro — Installation Guide

## Requirements

| Requirement | Purpose | Notes |
| ----------- | ------- | ----- |
| Python 3.9+ | Runs the tool | Check with `python --version` / `python3 --version` |
| `curl` | HTTP method only | Preinstalled on Windows 10+ and macOS |
| `ping` | ICMP method only | System `ping` command |
| git (optional) | Cloning the repo | Or download the ZIP from GitHub |

The tool has **no runtime Python dependencies** — it uses only the
standard library. `pytest` is needed only to run the tests.

---

## 1. Install Python

### Windows

Download the installer from [python.org/downloads](https://www.python.org/downloads/)
and check **"Add Python to PATH"** during installation. Then verify:

```powershell
python --version
```

If `python` opens the Microsoft Store instead, either use the `py`
launcher (`py --version`) or reinstall Python with the PATH option
checked.

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install python3 python3-pip curl git
```

### Fedora / RHEL

```bash
sudo dnf install python3 python3-pip curl git
```

### Arch Linux

```bash
sudo pacman -S python python-pip curl git
```

### macOS

Python and curl are preinstalled. If you want a newer Python, use
[Homebrew](https://brew.sh/):

```bash
brew install python curl git
```

Verify on any system:

```bash
python3 --version   # should be 3.9 or newer
curl --version      # needed for HTTP tests
```

---

## 2. Get the project

```bash
git clone https://github.com/erffanhub-00/Network-Ping-Pro.git
cd Network-Ping-Pro
```

Or download the ZIP from
[github.com/erffanhub-00/Network-Ping-Pro](https://github.com/erffanhub-00/Network-Ping-Pro)
and extract it.

---

## 3. Install the command

From the project directory:

```bash
pip install .
```

This installs the `network-ping-pro` command. For development
(editable install + pytest):

```bash
pip install -e ".[dev]"
```

On Linux/macOS you may need `pip3` instead of `pip`, or
`python3 -m pip install .` if `pip` is not on your PATH.

To run without installing, use the repository directory directly:

```bash
python -m network_ping_pro google.com
# or
python network_ping_pro.py google.com
```

---

## 4. Verify

```bash
network-ping-pro --version
network-ping-pro google.com
```

You should see a results table. If the target is unreachable from
your network, you will see a `DNS Error` or `Timeout` row instead —
that is a network result, not an install problem.

Run the test suite (needs the dev install):

```bash
python -m pytest -q
```

---

## Common problems

**`Python was not found` (Windows)**
Python is not on PATH. Reinstall with "Add Python to PATH" checked,
or use the `py` launcher: `py -m pip install .` and then
`py -m network_ping_pro google.com`.

**`pip: command not found`**
Use `python -m pip install .` (Windows) or `python3 -m pip install .`
(Linux/macOS). On Debian/Ubuntu, `sudo apt install python3-pip`.

**`curl not installed` when testing HTTP**
Windows 10+ and macOS have curl preinstalled. On Debian/Ubuntu:
`sudo apt install curl`. ICMP and TCP tests do not need curl.

**ICMP fails with "Operation not permitted" (Linux containers)**
The system `ping` needs raw-socket permission, which restricted
containers may block. TCP mode does not need it:
`network-ping-pro -m TCP google.com:443`.

**Colours look broken / escape codes in output**
Use `--no-color`, or `-q` for script-friendly output.

**`SyntaxError` when running**
You are using Python 2 or a Python older than 3.9. Check with
`python --version` and install Python 3.9+.

---

## Quick reference

```bash
# Windows
git clone https://github.com/erffanhub-00/Network-Ping-Pro.git
cd Network-Ping-Pro
pip install .
network-ping-pro google.com

# Linux / macOS
git clone https://github.com/erffanhub-00/Network-Ping-Pro.git
cd Network-Ping-Pro
pip install .
network-ping-pro google.com
```

See [USAGE.md](USAGE.md) for all commands and options.
