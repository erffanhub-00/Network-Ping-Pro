"""Command-line interface: argument parsing, clamping, file loading, main()."""

import argparse
import os
import sys
from typing import List

from .color import Color
from .render import Renderer
from .runner import PingRunner
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='network-ping-pro',
        description=(
            'Network Ping Pro — Network Diagnostic Tool (CLI)\n'
            'Tests latency, jitter, and packet loss via ICMP, TCP, or HTTP.\n'
            'For HTTP, curl must be installed.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic ICMP test
  network-ping-pro google.com github.com

  # TCP on port 443
  network-ping-pro -m TCP google.com:443 github.com:443

  # HTTP through a SOCKS5 proxy (e.g. v2ray / Hiddify)
  network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 https://google.com

  # More pings, custom timeout, export CSV + JSON
  network-ping-pro -c 20 -t 5 -o out.csv --json out.json google.com

  # Read targets from a file
  network-ping-pro -f targets.txt

  # Quiet mode (one-line-per-target output, script-friendly)
  network-ping-pro -q google.com

Notes:
  • Proxy applies to HTTP method only. ICMP cannot traverse HTTP/SOCKS proxies.
  • DNS resolution is measured separately from the connection. For HTTP, curl
    resolves DNS internally, so DNS and HTTP timings are not part of the same
    connection. For TCP, the connection is made to the IP resolved in the DNS
    stage, so both belong to the same attempt.
  • "Score" is a custom heuristic for comparing results within this tool,
    not an industry-standard benchmark.
        """,
    )

    p.add_argument('targets', nargs='*', default=[],
                   help='Targets (host, host:port, URL, or [IPv6]:port)')
    p.add_argument('-f', '--file', metavar='FILE',
                   help='Read targets from a file (one per line, "#" for comments)')

    p.add_argument('-m', '--method', choices=['ICMP', 'TCP', 'HTTP'],
                   default='ICMP', help='Testing method (default: ICMP)')
    p.add_argument('-c', '--count', type=int, default=10,
                   help='Pings per target (1-200, default: 10)')
    p.add_argument('-t', '--timeout', type=float, default=3.0,
                   help='Timeout per ping in seconds (1-30, default: 3.0)')
    p.add_argument('-w', '--workers', type=int, default=10,
                   help='Concurrent workers (1-50, default: 10)')

    p.add_argument('--proxy', metavar='URL',
                   help='Proxy URL (http/https/socks4/socks5). Applies to '
                        'HTTP method only. Example: socks5://127.0.0.1:10808')
    p.add_argument('--proxy-user', help='Proxy username')
    p.add_argument('--proxy-pass',
                   help='Proxy password. Prefer the NPP_PROXY_PASS '
                        'environment variable: a password on the command '
                        'line is visible to other users via ps and shell history.')

    p.add_argument('-o', '--output-csv', metavar='FILE',
                   help='Export results to CSV')
    p.add_argument('--json', dest='output_json', metavar='FILE',
                   help='Export results to JSON')

    p.add_argument('--no-progress', action='store_true',
                   help='Disable the live progress line')
    p.add_argument('-q', '--quiet', action='store_true',
                   help='Quiet mode: one-line-per-target output, script-friendly')
    p.add_argument('--no-color', action='store_true',
                   help='Disable colored output')
    p.add_argument('-v', '--version', action='version',
                   version=f'Network Ping Pro {__version__}')

    return p


def clamp_args(args):
    for name, lo, hi in (('count', 1, 200), ('timeout', 1.0, 30.0),
                         ('workers', 1, 50)):
        value = getattr(args, name)
        clamped = max(lo, min(hi, value))
        if clamped != value:
            print(f"Warning: {name} clamped {value} -> {clamped}",
                  file=sys.stderr)
        setattr(args, name, clamped)
    return args


def load_targets_from_file(path: str) -> List[str]:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    out = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            out.append(line)
    return out


def main(argv=None) -> int:
    Color.enable_windows_ansi()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.no_color:
        Color.disable()

    # Proxy password from the environment, so it never has to appear
    # on the command line (visible via ps / shell history).
    if args.proxy_pass is None:
        args.proxy_pass = os.environ.get('NPP_PROXY_PASS')

    all_targets = list(args.targets)
    if args.file:
        try:
            all_targets.extend(load_targets_from_file(args.file))
        except Exception as e:
            print(f"{Color.RED}Failed to read file: {e}{Color.RESET}")
            return 2

    if not all_targets:
        parser.print_help()
        print(f"\n{Color.RED}Error: no targets specified.{Color.RESET}")
        return 2

    args.targets = '\n'.join(all_targets)
    args = clamp_args(args)

    if not args.quiet:
        Renderer.banner()
        print()

    try:
        runner = PingRunner(args)
        return runner.run()
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Interrupted by user.{Color.RESET}")
        return 130
