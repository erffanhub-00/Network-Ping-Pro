"""Network Ping Pro — network diagnostic tool (CLI).

Tests latency, jitter and packet loss via ICMP, TCP or HTTP, with a
custom diagnostic Score, CSV/JSON export and proxy support for HTTP.

Public API is re-exported here so `from network_ping_pro import X`
keeps working; the implementation lives in the submodules.
"""

from .color import Color
from .dns import DNSResolver
from .engine import PingEngine
from .models import PingResult, StageStats
from .render import Renderer
from .runner import PingRunner
from .stats import StatisticsEngine
from .targets import TargetParser
from .version import __author__, __license__, __version__
from .cli import build_parser, clamp_args, load_targets_from_file, main

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "Color",
    "StageStats",
    "PingResult",
    "StatisticsEngine",
    "DNSResolver",
    "PingEngine",
    "TargetParser",
    "Renderer",
    "PingRunner",
    "build_parser",
    "clamp_args",
    "load_targets_from_file",
    "main",
]
