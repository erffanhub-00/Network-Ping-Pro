"""Data models: one test result and per-stage timing statistics."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StageStats:
    """Statistics for a single stage (DNS, Connect, TTFB, Total)."""
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    p50: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    samples: int = 0


@dataclass
class PingResult:
    """Complete result of a single ping test."""
    target: str
    method: str

    # --- Test outcome (three independent flags) ---
    reachable: bool = False
    test_success: bool = False
    application_ok: Optional[bool] = None

    # --- Raw samples ---
    times: List[float] = field(default_factory=list)
    attempts: int = 0
    successes: int = 0

    # --- Latency statistics (ms) ---
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    jitter: Optional[float] = None
    p50: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None

    # --- Loss ---
    packet_loss: float = 100.0

    # --- Status ---
    status: str = 'Failed'
    error: Optional[str] = None
    resolved_ip: Optional[str] = None
    ip_family: Optional[str] = None
    rank: Optional[int] = None

    # --- Scoring (custom heuristic, not a standard metric) ---
    score: Optional[float] = None
    grade: Optional[str] = None

    # --- Stage timings (all ms) ---
    dns: StageStats = field(default_factory=StageStats)
    connect: StageStats = field(default_factory=StageStats)
    ttfb: StageStats = field(default_factory=StageStats)
    total: StageStats = field(default_factory=StageStats)

    # --- HTTP specific ---
    http_status: Optional[int] = None
    http_status_text: Optional[str] = None
    http_status_distribution: Optional[Dict[int, int]] = None

    # --- Port ---
    port: Optional[int] = None
