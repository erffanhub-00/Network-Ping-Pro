"""Allow `python -m network_ping_pro`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
