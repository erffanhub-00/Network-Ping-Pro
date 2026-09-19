# Network Ping Pro — Installation Guide

Complete installation and first-run guide for **Windows, Linux, and macOS**.

This guide is written for both beginners and experienced users.

---

## Table of Contents

* [Requirements](#requirements)
* [Windows](#windows)
* [Linux](#linux)
* [macOS](#macos)
* [Download the Project](#download-the-project)
* [First Run](#first-run)
* [Common Problems](#common-problems)
* [Quick Reference](#quick-reference)

---

## Requirements

| Requirement | Purpose                  |
| ----------- | ------------------------ |
| Python 3.9+ | Running Network Ping Pro |
| ping        | ICMP testing             |
| curl        | HTTP testing             |
| Terminal    | Running commands         |
| Git         | Optional, for cloning    |

No Python packages are required unless the project's `requirements.txt` specifies otherwise.

---

# Windows

## Step 1 — Install Python

Go to:

https://www.python.org/downloads/

Download the latest supported Python version.

Run the installer.

### Important

On the first installer screen, enable:

```text
Add python.exe to PATH
```

Then select:

```text
Install Now
```

Wait for the installation to finish.

---

## Step 2 — Verify Python

Open Command Prompt:

1. Press `Win`
2. Type `cmd`
3. Press Enter

Run:

```cmd
python --version
```

You should see something similar to:

```text
Python 3.12.x
```

Python 3.9 or newer is required.

---

## Step 3 — Verify curl

For HTTP testing:

```cmd
curl --version
```

Modern Windows versions normally include curl.

If curl is unavailable, install it from:

https://curl.se/windows/

You can still use ICMP and TCP testing without curl.

---

## Step 4 — Download Network Ping Pro

### Option A — Git

If Git is installed:

```cmd
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

### Option B — ZIP

Open:

https://github.com/erffanhub-00/network-ping-pro

Select:

```text
Code → Download ZIP
```

Extract the ZIP.

Then open Command Prompt in the extracted folder.

Example:

```cmd
cd /d "D:\tools\network-ping-pro"
```

---

## Step 5 — Run the Program

```cmd
python network_ping_pro.py google.com
```

If everything is installed correctly, the program will start the network test.

---

# Linux

## Debian / Ubuntu

```bash
sudo apt update
sudo apt install python3 curl git
```

## Fedora / RHEL

```bash
sudo dnf install python3 curl git
```

## Arch Linux

```bash
sudo pacman -S python curl git
```

Clone the project:

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

Run:

```bash
python3 network_ping_pro.py google.com
```

---

# macOS

The easiest approach is Homebrew.

Install Homebrew if necessary:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install Python:

```bash
brew install python
```

Clone the project:

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

Run:

```bash
python3 network_ping_pro.py google.com
```

---

# Download the Project

There are two common ways.

## Git

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

## ZIP

Download:

https://github.com/erffanhub-00/network-ping-pro

Then:

```text
Code → Download ZIP
```

Extract the project and open a terminal inside its directory.

---

# First Run

Start with the simplest test:

### Windows

```cmd
python network_ping_pro.py google.com
```

### Linux / macOS

```bash
python3 network_ping_pro.py google.com
```

If the command works, Network Ping Pro is ready.

For all available commands:

```bash
python network_ping_pro.py --help
```

---

# Common Problems

## Python was not found

Run:

```cmd
where python
```

If nothing is returned, Python may not be installed or may not be in PATH.

### Solution 1 — Reinstall Python

Download Python from:

https://www.python.org/downloads/

During installation enable:

```text
Add python.exe to PATH
```

Then close and reopen Command Prompt.

Test:

```cmd
python --version
```

---

## Python opens Microsoft Store

Windows may have Python App Execution Aliases enabled.

Open:

```text
Settings
→ Apps
→ Advanced app settings
→ App execution aliases
```

Disable the Python aliases if they are intercepting the `python` command.

Open a new terminal and try:

```cmd
python --version
```

---

## Python works with `py` but not `python`

Try:

```cmd
py --version
```

If that works, you can run:

```cmd
py network_ping_pro.py google.com
```

---

## curl is missing

Check:

```bash
curl --version
```

If it is unavailable, install curl for your operating system.

HTTP testing requires curl.

ICMP and TCP testing do not require curl.

---

## Permission / Firewall problems

Some operating systems or security software may restrict network operations.

If ICMP testing does not work, try TCP:

```bash
python network_ping_pro.py -m TCP google.com:443
```

If TCP works while ICMP does not, the problem may be related to ICMP permissions or firewall rules.

---

## Colors do not appear correctly

If supported by your version, use:

```bash
python network_ping_pro.py --no-color google.com
```

You can also use Windows Terminal instead of the legacy Command Prompt.

---

## SyntaxError

Check your Python version:

```bash
python --version
```

or:

```bash
python3 --version
```

Network Ping Pro requires Python 3.9+.

---

# Quick Reference

## Windows

```cmd
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
python network_ping_pro.py google.com
```

## Linux / macOS

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
python3 network_ping_pro.py google.com
```

## Check Python

```bash
python --version
```

## Show Help

```bash
python network_ping_pro.py --help
```

---

# Need Help?

If the program does not work, open an issue:

https://github.com/erffanhub-00/network-ping-pro/issues

Include:

* Operating system
* Python version
* Exact command
* Complete error message
* Relevant terminal output
