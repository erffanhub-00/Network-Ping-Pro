#!/usr/bin/env python3
"""Backward-compatible entry point.

The implementation now lives in the `network_ping_pro` package; this
file only re-exports main() so `python network_ping_pro.py ...` keeps
working. Prefer the installed console script: `network-ping-pro ...`
"""

import sys

from network_ping_pro import main

if __name__ == "__main__":
    sys.exit(main())
