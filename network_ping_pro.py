#!/usr/bin/env python3
# ============================================================
# Network Ping Pro - CLI Edition
# Version: 1.0.0
# Author: Erffan
# License: MIT
# ============================================================
#
# NOTE on measurements:
#   - DNS resolution is measured SEPARATELY from the connection.
#     For HTTP, curl performs its own DNS resolution internally.
#   - For TCP, the connection is made to the IP resolved in the DNS stage,
#     so DNS timing and TCP connect timing belong to the same attempt.
#   - "Score" is a CUSTOM heuristic metric for comparing results
#     within this tool. It is NOT an industry-standard benchmark.
#   - "Rank" is by custom Score, not by a standard network metric.
# ============================================================

import argparse
import csv
import json
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, quote

__version__ = "1.0.0"
__author__ = "Erffan"
__license__ = "MIT"


# ============================================================
# ANSI COLORS
# ============================================================

class Color:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

    @classmethod
    def enable_windows_ansi(cls):
        """Enable ANSI on Windows 10+ without clobbering other console flags."""
        if platform.system().lower() != 'windows':
            return
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                raise OSError("GetConsoleMode failed")
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            cls.disable()

    @classmethod
    def disable(cls):
        for attr in dir(cls):
            if attr.isupper() and isinstance(getattr(cls, attr), str):
                setattr(cls, attr, '')


# ============================================================
# DATA MODELS
# ============================================================

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


# ============================================================
# STATISTICS ENGINE
# ============================================================

class StatisticsEngine:

    @staticmethod
    def percentiles(times: List[float]) -> Dict[str, Optional[float]]:
        if not times:
            return {'p50': None, 'p95': None, 'p99': None}

        s = sorted(times)
        n = len(s)

        def pct(p: float) -> float:
            if n == 1:
                return s[0]
            rank = (n - 1) * p / 100.0
            lo = int(rank)
            hi = min(lo + 1, n - 1)
            w = rank - lo
            return s[lo] * (1 - w) + s[hi] * w

        return {
            'p50': round(pct(50), 1),
            'p95': round(pct(95), 1),
            'p99': round(pct(99), 1),
        }

    @staticmethod
    def basic_stats(times: List[float]) -> Dict[str, Any]:
        if not times:
            return {}
        out = {
            'avg': round(sum(times) / len(times), 1),
            'min': round(min(times), 1),
            'max': round(max(times), 1),
        }
        if len(times) > 1:
            jitter_vals = [abs(times[i] - times[i - 1]) for i in range(1, len(times))]
            out['jitter'] = round(sum(jitter_vals) / len(jitter_vals), 1)
        else:
            out['jitter'] = 0.0
        out.update(StatisticsEngine.percentiles(times))
        return out

    @staticmethod
    def stage_stats(samples: List[float]) -> StageStats:
        if not samples:
            return StageStats()
        st = StatisticsEngine.basic_stats(samples)
        return StageStats(
            avg=st.get('avg'), min=st.get('min'), max=st.get('max'),
            p50=st.get('p50'), p95=st.get('p95'), p99=st.get('p99'),
            samples=len(samples),
        )

    @staticmethod
    def calculate_score(r: PingResult) -> float:
        """
        Custom diagnostic score (0-100).

        This is a heuristic designed for comparing results WITHIN this tool.
        It is NOT an industry-standard network benchmark.
        """
        if not r.test_success:
            return 0.0

        if r.avg is None:
            latency = 0
        elif r.avg <= 10:
            latency = 100
        elif r.avg <= 25:
            latency = 90
        elif r.avg <= 50:
            latency = 80
        elif r.avg <= 100:
            latency = 65
        elif r.avg <= 200:
            latency = 45
        elif r.avg <= 500:
            latency = 25
        else:
            latency = 10

        if r.packet_loss == 0:
            loss = 100
        elif r.packet_loss <= 1:
            loss = 95
        elif r.packet_loss <= 5:
            loss = 75
        elif r.packet_loss <= 10:
            loss = 50
        elif r.packet_loss <= 20:
            loss = 25
        else:
            loss = 5

        if r.jitter is None:
            jitter = 50
        elif r.jitter <= 2:
            jitter = 100
        elif r.jitter <= 5:
            jitter = 85
        elif r.jitter <= 10:
            jitter = 65
        elif r.jitter <= 20:
            jitter = 40
        else:
            jitter = 15

        p95_penalty = 1.0
        if r.p95 and r.avg:
            ratio = r.p95 / r.avg
            if ratio > 3:
                p95_penalty = 0.70
            elif ratio > 2:
                p95_penalty = 0.85

        app_penalty = 1.0
        if r.application_ok is False and r.http_status:
            if 400 <= r.http_status < 500:
                app_penalty = 0.70
            elif 500 <= r.http_status < 600:
                app_penalty = 0.40

        final = (latency * 0.35 + loss * 0.30 + jitter * 0.25) * p95_penalty * app_penalty
        return round(max(0.0, min(100.0, final)), 1)

    @staticmethod
    def get_grade(score: float) -> str:
        if score >= 90:
            return 'Excellent'
        elif score >= 80:
            return 'Very Good'
        elif score >= 70:
            return 'Good'
        elif score >= 60:
            return 'Fair'
        else:
            return 'Poor'


# ============================================================
# DNS RESOLVER
# ============================================================

class DNSResolver:
    """
    DNS resolver with a timeout guard.

    Note: socket.getaddrinfo() cannot be interrupted mid-call. This
    function uses a daemon thread and joins with a timeout, so from the
    caller's perspective the resolution "gives up" after `timeout` seconds.
    """

    @staticmethod
    def resolve(host: str, timeout: float = 5.0
                ) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """
        Returns (ip, family, elapsed_ms, error).
        family is 'IPv4' or 'IPv6'.
        """
        result: Dict[str, Any] = {'ip': None, 'family': None, 'elapsed': None, 'error': None}

        def worker():
            try:
                start = time.perf_counter()
                infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                elapsed = (time.perf_counter() - start) * 1000
                result['elapsed'] = round(elapsed, 1)

                if not infos:
                    result['error'] = 'No addresses'
                    return

                chosen = None
                for info in infos:
                    if info[0] == socket.AF_INET:
                        chosen = info
                        break
                if chosen is None:
                    chosen = infos[0]

                result['ip'] = chosen[4][0]
                result['family'] = 'IPv4' if chosen[0] == socket.AF_INET else 'IPv6'
            except socket.gaierror as e:
                result['error'] = str(e)
            except Exception as e:
                result['error'] = str(e)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout)

        if t.is_alive():
            return None, None, None, f'DNS timeout after {timeout}s'

        return result['ip'], result['family'], result['elapsed'], result['error']


# ============================================================
# PING ENGINE
# ============================================================

class PingEngine:
    """
    Proxy notes:
      - Proxy applies to HTTP method only.
      - ICMP is a raw protocol and cannot traverse HTTP/SOCKS proxies.
      - TCP currently does not route through proxy (would require SOCKS handshake).
    """

    PROXY_URL: Optional[str] = None
    PROXY_USER: Optional[str] = None
    PROXY_PASS: Optional[str] = None

    NULL_DEVICE = 'NUL' if platform.system().lower() == 'windows' else '/dev/null'

    @staticmethod
    def set_proxy(url: str, user: Optional[str] = None, password: Optional[str] = None):
        PingEngine.PROXY_URL = url
        PingEngine.PROXY_USER = user
        PingEngine.PROXY_PASS = password

    @staticmethod
    def clear_proxy():
        PingEngine.PROXY_URL = None
        PingEngine.PROXY_USER = None
        PingEngine.PROXY_PASS = None

    @staticmethod
    def _build_proxy_url() -> Optional[str]:
        """Build curl-compatible proxy URL. Handles IPv6 and URL-encodes credentials."""
        if not PingEngine.PROXY_URL:
            return None

        parsed = urlparse(PingEngine.PROXY_URL)
        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port
        if not scheme or not host or not port:
            return PingEngine.PROXY_URL

        if ':' in host and not host.startswith('['):
            host_part = f"[{host}]"
        else:
            host_part = host

        auth = ''
        if PingEngine.PROXY_USER and PingEngine.PROXY_PASS:
            user = quote(PingEngine.PROXY_USER, safe='')
            pw = quote(PingEngine.PROXY_PASS, safe='')
            auth = f"{user}:{pw}@"

        return f"{scheme}://{auth}{host_part}:{port}"

    @staticmethod
    def _finalize(r: PingResult):
        """Compute stats, score, grade, and set default status."""
        if not r.times:
            r.packet_loss = 100.0
            r.test_success = False
            r.score = 0.0
            if r.grade is None:
                r.grade = 'Failed'
            if r.status == 'OK':
                r.status = 'Failed'
            return

        st = StatisticsEngine.basic_stats(r.times)
        r.avg = st.get('avg')
        r.min = st.get('min')
        r.max = st.get('max')
        r.jitter = st.get('jitter')
        r.p50 = st.get('p50')
        r.p95 = st.get('p95')
        r.p99 = st.get('p99')

        if r.attempts > 0:
            r.packet_loss = round(
                ((r.attempts - r.successes) / r.attempts) * 100.0, 1
            )

        r.score = StatisticsEngine.calculate_score(r)
        r.grade = StatisticsEngine.get_grade(r.score)

        if r.status in ('OK', '') or r.status is None:
            if r.packet_loss == 0:
                r.status = 'OK'
            elif r.packet_loss < 20:
                r.status = 'Partial'
            else:
                r.status = 'High Loss'

    # ------------------------------------------------------------------
    # ICMP
    # ------------------------------------------------------------------
    @staticmethod
    def ping_icmp(host: str, count: int, timeout: float,
                  stop_event: threading.Event) -> PingResult:
        r = PingResult(target=host, method='ICMP')
        r.attempts = count

        ip, family, dns_ms, dns_err = DNSResolver.resolve(host, timeout)
        if dns_ms is not None:
            r.dns = StageStats(avg=dns_ms, min=dns_ms, max=dns_ms,
                               p50=dns_ms, p95=dns_ms, p99=dns_ms, samples=1)
        if dns_err:
            r.error = f'DNS: {dns_err}'
            r.status = 'DNS Error'
            return r
        r.resolved_ip = ip
        r.ip_family = family

        system = platform.system().lower()
        if system == 'windows':
            w_ms = max(1, int(round(timeout * 1000)))
            cmd = ['ping', '-n', str(count), '-w', str(w_ms), host]
        elif system == 'darwin':
            w_ms = max(1, int(round(timeout * 1000)))
            cmd = ['ping', '-c', str(count), '-W', str(w_ms), host]
        else:
            cmd = ['ping', '-c', str(count), '-W', f'{timeout:.2f}', host]

        process = None
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            start = time.time()
            overall = count * timeout + 10

            while process.poll() is None:
                if stop_event.is_set():
                    process.kill()
                    process.wait()
                    r.error = 'Cancelled'
                    r.status = 'Cancelled'
                    return r
                if time.time() - start > overall:
                    process.kill()
                    process.wait()
                    r.error = 'Timeout'
                    r.status = 'Timeout'
                    return r
                time.sleep(0.05)

            stdout, stderr = process.communicate()
            output = stdout + stderr

            times: List[float] = []
            for pattern in (
                r'time[=<]\s*(\d+(?:[.,]\d+)?)\s*ms',
                r'(\d+(?:[.,]\d+)?)\s*ms',
            ):
                for m in re.findall(pattern, output, re.IGNORECASE):
                    try:
                        v = float(m.replace(',', '.'))
                        if 0 <= v <= 10000:
                            times.append(v)
                    except ValueError:
                        continue
                if times:
                    break

            if not times:
                lower = output.lower()
                if 'unreachable' in lower:
                    r.error, r.status = 'Host unreachable', 'Unreachable'
                elif 'could not find host' in lower or 'unknown host' in lower:
                    r.error, r.status = 'DNS resolution failed', 'DNS Error'
                elif 'timed out' in lower or 'timeout' in lower:
                    r.error, r.status = 'Request timeout', 'Timeout'
                else:
                    r.error, r.status = 'No response', 'No Response'
                return r

            r.reachable = True
            r.test_success = True
            r.times = times
            r.successes = len(times)
            r.status = 'OK'
            PingEngine._finalize(r)
            return r

        except Exception as e:
            if process:
                try:
                    process.kill()
                except Exception:
                    pass
            r.error = str(e)[:80]
            r.status = 'Error'
            return r

    # ------------------------------------------------------------------
    # TCP
    # ------------------------------------------------------------------
    @staticmethod
    def ping_tcp(host: str, port: int, count: int, timeout: float,
                 stop_event: threading.Event) -> PingResult:
        r = PingResult(target=host, method=f'TCP:{port}')
        r.port = port
        r.attempts = count

        ip, family, dns_ms, dns_err = DNSResolver.resolve(host, timeout)
        if dns_ms is not None:
            r.dns = StageStats(avg=dns_ms, min=dns_ms, max=dns_ms,
                               p50=dns_ms, p95=dns_ms, p99=dns_ms, samples=1)
        if dns_err:
            r.error = f'DNS: {dns_err}'
            r.status = 'DNS Error'
            return r
        r.resolved_ip = ip
        r.ip_family = family

        af = socket.AF_INET6 if family == 'IPv6' else socket.AF_INET

        times: List[float] = []
        connect_samples: List[float] = []
        refused = 0
        timeouts = 0
        errors = 0

        for _ in range(count):
            if stop_event.is_set():
                r.error = 'Cancelled'
                r.status = 'Cancelled'
                return r

            try:
                start = time.perf_counter()
                sock = socket.socket(af, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                try:
                    if family == 'IPv6':
                        sock.connect((ip, port, 0, 0))
                    else:
                        sock.connect((ip, port))
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                    connect_samples.append(elapsed)
                    r.successes += 1
                except ConnectionRefusedError:
                    refused += 1
                except socket.timeout:
                    timeouts += 1
                except socket.gaierror:
                    errors += 1
                except OSError:
                    errors += 1
                finally:
                    try:
                        sock.close()
                    except Exception:
                        pass
            except Exception:
                errors += 1
                continue

        if times:
            r.reachable = True
            r.test_success = True
            r.times = times
            r.successes = len(times)
            r.status = 'OK'
            r.connect = StatisticsEngine.stage_stats(connect_samples)
            PingEngine._finalize(r)
            return r

        if refused > 0:
            r.reachable = True
            r.test_success = False
            r.status = 'Refused'
            r.error = 'Port closed (host reachable)'
            r.packet_loss = 100.0
            r.score = 0.0
            r.grade = 'Poor'
            return r

        if timeouts > 0:
            r.status = 'Timeout'
            r.error = 'Connection timeout'
        elif errors > 0:
            r.status = 'Error'
            r.error = 'Connection error'
        else:
            r.status = 'Failed'
            r.error = 'No TCP connection'

        return r

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------
    @staticmethod
    def ping_http(target: Dict[str, Any], count: int, timeout: float,
                  stop_event: threading.Event) -> PingResult:
        host = target['host']
        scheme = target.get('scheme') or 'https'
        port = target.get('port')
        path = target.get('path') or '/'
        query = target.get('query') or ''

        r = PingResult(target=host, method='HTTP')
        r.port = port
        r.attempts = count

        ip, family, dns_ms, dns_err = DNSResolver.resolve(host, timeout)
        if dns_ms is not None:
            r.dns = StageStats(avg=dns_ms, min=dns_ms, max=dns_ms,
                               p50=dns_ms, p95=dns_ms, p99=dns_ms, samples=1)
        if dns_err:
            r.error = f'DNS: {dns_err}'
            r.status = 'DNS Error'
            return r
        r.resolved_ip = ip
        r.ip_family = family

        try:
            subprocess.run(['curl', '--version'],
                           capture_output=True, timeout=2, check=True)
        except Exception:
            r.error = 'curl not installed (required for HTTP)'
            r.status = 'Error'
            return r

        url = f"{scheme}://{host}"
        if port:
            url += f":{port}"
        url += path
        if query:
            url += f"?{query}"

        curl_fmt = '%{time_total}|%{http_code}|%{time_connect}|%{time_starttransfer}'

        total_samples: List[float] = []
        connect_samples: List[float] = []
        ttfb_samples: List[float] = []
        status_codes: List[int] = []

        proxy_url = PingEngine._build_proxy_url()
        timeout_str = f'{timeout:.2f}'

        for _ in range(count):
            if stop_event.is_set():
                r.error = 'Cancelled'
                r.status = 'Cancelled'
                return r

            cmd = [
                'curl', '-s', '-o', PingEngine.NULL_DEVICE,
                '-w', curl_fmt,
                '--connect-timeout', timeout_str,
                '--max-time', timeout_str,
            ]
            if proxy_url:
                cmd.extend(['-x', proxy_url])
            cmd.append(url)

            process = None
            try:
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                start = time.time()
                overall = timeout + 5
                while process.poll() is None:
                    if stop_event.is_set():
                        process.kill()
                        process.wait()
                        r.error = 'Cancelled'
                        r.status = 'Cancelled'
                        return r
                    if time.time() - start > overall:
                        process.kill()
                        process.wait()
                        break
                    time.sleep(0.05)

                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    continue

                if not stdout:
                    continue

                parts = stdout.strip().split('|')
                if len(parts) != 4:
                    continue

                try:
                    total_s = float(parts[0])
                    code = int(parts[1])
                    connect_s = float(parts[2]) if parts[2] else 0.0
                    ttfb_s = float(parts[3]) if parts[3] else 0.0
                except ValueError:
                    continue

                if code <= 0:
                    continue

                total_ms = total_s * 1000.0
                if not (0 < total_ms <= 60000):
                    continue

                total_samples.append(total_ms)
                r.successes += 1
                status_codes.append(code)

                if connect_s > 0:
                    connect_samples.append(connect_s * 1000.0)
                if ttfb_s > 0:
                    ttfb_samples.append(ttfb_s * 1000.0)

            except Exception:
                if process:
                    try:
                        process.kill()
                    except Exception:
                        pass
                continue

        if not total_samples:
            r.error = 'No HTTP response'
            r.status = 'Failed'
            return r

        r.reachable = True
        r.test_success = True
        r.times = total_samples

        r.connect = StatisticsEngine.stage_stats(connect_samples)
        r.ttfb = StatisticsEngine.stage_stats(ttfb_samples)
        r.total = StatisticsEngine.stage_stats(total_samples)

        if status_codes:
            dist = Counter(status_codes)
            r.http_status_distribution = dict(dist)

            unique = list(dist.keys())
            if len(unique) == 1:
                r.http_status = unique[0]
            else:
                r.http_status = max(unique)

            r.http_status_text = {
                200: 'OK', 201: 'Created', 204: 'No Content',
                301: 'Moved Permanently', 302: 'Found',
                304: 'Not Modified', 400: 'Bad Request',
                401: 'Unauthorized', 403: 'Forbidden',
                404: 'Not Found', 429: 'Too Many Requests',
                500: 'Internal Server Error', 502: 'Bad Gateway',
                503: 'Service Unavailable', 504: 'Gateway Timeout',
            }.get(r.http_status, '')

            r.application_ok = 200 <= r.http_status < 400

            if r.application_ok and len(unique) == 1:
                r.status = 'OK'
            elif r.application_ok:
                r.status = 'Mixed 2xx/3xx'
            elif 400 <= r.http_status < 600:
                txt = r.http_status_text or ''
                r.status = f'HTTP {r.http_status} {txt}'.strip()
            else:
                r.status = f'HTTP {r.http_status}'
        else:
            r.status = 'OK'

        PingEngine._finalize(r)
        return r

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------
    @staticmethod
    def ping_host(target: Dict[str, Any], method: str, count: int, timeout: float,
                  stop_event: threading.Event) -> PingResult:
        host = target['host']
        if stop_event.is_set():
            return PingResult(target=host, method=method, status='Cancelled')

        if method == 'ICMP':
            return PingEngine.ping_icmp(host, count, timeout, stop_event)
        elif method == 'TCP':
            port = target.get('port', 443)
            return PingEngine.ping_tcp(host, port, count, timeout, stop_event)
        elif method == 'HTTP':
            return PingEngine.ping_http(target, count, timeout, stop_event)

        r = PingResult(target=host, method=method)
        r.error = 'Unknown method'
        r.status = 'Error'
        return r


# ============================================================
# TARGET PARSER
# ============================================================

class TargetParser:

    @staticmethod
    def parse_target(value: str) -> Optional[Dict[str, Any]]:
        try:
            value = value.strip()
            if not value:
                return None

            if value.startswith('['):
                m = re.match(r'\[([0-9a-fA-F:]+)\](?::(\d+))?$', value)
                if m:
                    return {
                        'host': m.group(1),
                        'port': int(m.group(2)) if m.group(2) else None,
                        'scheme': None,
                        'path': '/',
                        'query': '',
                        'raw': value,
                    }
                return None

            parsed = urlparse(value if '://' in value else '//' + value)
            host = parsed.hostname
            if not host:
                return None

            return {
                'host': host.lower(),
                'port': parsed.port,
                'scheme': parsed.scheme or None,
                'path': parsed.path or '/',
                'query': parsed.query or '',
                'raw': value,
            }
        except Exception:
            return None

    @staticmethod
    def parse_sites(text: str) -> List[Dict[str, Any]]:
        seen = set()
        out: List[Dict[str, Any]] = []
        for chunk in text.replace('،', ',').replace('\n', ',').split(','):
            parsed = TargetParser.parse_target(chunk)
            if not parsed:
                continue
            key = (
                parsed['scheme'],
                parsed['host'],
                parsed['port'],
                parsed['path'],
                parsed['query'],
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(parsed)
        return out


# ============================================================
# PRETTY RENDERING
# ============================================================

class Renderer:

    @staticmethod
    def visible_len(s: str) -> int:
        return len(re.sub(r'\033\[[0-9;]*m', '', s))

    @staticmethod
    def pad(s: str, width: int, align: str = 'left') -> str:
        n = Renderer.visible_len(s)
        pad = max(0, width - n)
        if align == 'right':
            return ' ' * pad + s
        if align == 'center':
            left = pad // 2
            right = pad - left
            return ' ' * left + s + ' ' * right
        return s + ' ' * pad

    @staticmethod
    def truncate(s: str, width: int) -> str:
        if len(s) <= width:
            return s
        if width <= 1:
            return s[:width]
        return s[:width - 1] + '…'

    @staticmethod
    def banner():
        title = f"Network Ping Pro v{__version__}"
        sub = "Network Diagnostic Tool (CLI)"
        author = f"Author: {__author__}"
        width = max(len(title), len(sub), len(author)) + 4

        top = '╔' + '═' * width + '╗'
        bot = '╚' + '═' * width + '╝'

        def line(text):
            pad = width - len(text) - 2
            return '║ ' + text + ' ' * pad + ' ║'

        print(f"{Color.BOLD}{Color.CYAN}{top}")
        print(f"{Color.BOLD}{Color.CYAN}{line(title)}")
        print(f"{Color.RESET}{Color.CYAN}{line(sub)}")
        print(f"{Color.RESET}{Color.GRAY}{line(author)}")
        print(f"{Color.CYAN}{bot}{Color.RESET}")

    @staticmethod
    def progress(current: int, total: int, target: str, status: str):
        bar_len = 22
        filled = int(bar_len * current / total) if total else 0
        bar = '█' * filled + '░' * (bar_len - filled)
        sys.stdout.write(
            f"\r  {Color.CYAN}[{bar}]{Color.RESET} "
            f"{current:>{len(str(total))}}/{total}  "
            f"{Renderer.truncate(target, 28):<28} "
            f"{Color.DIM}{Renderer.truncate(status, 18):<18}{Color.RESET}"
        )
        sys.stdout.flush()

    @staticmethod
    def clear_line():
        sys.stdout.write('\r' + ' ' * 110 + '\r')
        sys.stdout.flush()

    @staticmethod
    def grade_color(grade: Optional[str]) -> str:
        if grade == 'Excellent':
            return Color.GREEN
        if grade == 'Very Good':
            return Color.CYAN
        if grade == 'Good':
            return Color.YELLOW
        if grade == 'Fair':
            return Color.MAGENTA
        if grade in ('Poor', 'Failed'):
            return Color.RED
        return Color.RESET

    @staticmethod
    def status_color(status: str) -> str:
        if status == 'OK':
            return Color.GREEN
        if status in ('Partial', 'High Loss'):
            return Color.YELLOW
        if status.startswith('HTTP 4') or status.startswith('HTTP 5'):
            return Color.MAGENTA
        if status == 'Cancelled':
            return Color.GRAY
        return Color.RED

    @staticmethod
    def latency_bar(value: Optional[float], max_value: float, width: int = 24) -> str:
        if value is None or max_value <= 0:
            return Color.DIM + '░' * width + Color.RESET
        ratio = min(value / max_value, 1.0)
        filled = int(round(ratio * width))
        filled = max(1 if value > 0 else 0, filled)
        bar = '█' * filled + '░' * (width - filled)
        if value <= 50:
            c = Color.GREEN
        elif value <= 100:
            c = Color.CYAN
        elif value <= 200:
            c = Color.YELLOW
        elif value <= 500:
            c = Color.MAGENTA
        else:
            c = Color.RED
        return f"{c}{bar}{Color.RESET}"

    @staticmethod
    def print_results_table(results: List[PingResult]):
        if not results:
            return

        cols = [
            ('#',        3,  'right'),
            ('Target',  28,  'left'),
            ('Method',   9,  'left'),
            ('Score',    5,  'right'),
            ('Grade',   10,  'left'),
            ('Avg ms',   8,  'right'),
            ('Min',      7,  'right'),
            ('Max',      7,  'right'),
            ('Jitter',   7,  'right'),
            ('P95',      7,  'right'),
            ('Loss',     6,  'right'),
            ('Status',  20,  'left'),
        ]

        head = '  '.join(
            Renderer.pad(f"{Color.BOLD}{name}{Color.RESET}", w, a)
            for name, w, a in cols
        )
        total_w = sum(w for _, w, _ in cols) + 2 * (len(cols) - 1)

        print()
        print(f"{Color.BOLD}{Color.BLUE}╭{'─' * total_w}╮{Color.RESET}")
        print(f"{Color.BOLD}{Color.BLUE}│{Color.RESET} {head} {Color.BOLD}{Color.BLUE}│{Color.RESET}")
        print(f"{Color.BOLD}{Color.BLUE}├{'─' * total_w}┤{Color.RESET}")

        for r in results:
            rank = str(r.rank) if r.rank else '·'

            if r.test_success and r.times:
                score = f"{r.score:.1f}" if r.score is not None else "0.0"
                grade = r.grade or "Unknown"
                avg = f"{r.avg:.1f}" if r.avg is not None else "—"
                mn = f"{r.min:.1f}" if r.min is not None else "—"
                mx = f"{r.max:.1f}" if r.max is not None else "—"
                jit = f"{r.jitter:.1f}" if r.jitter is not None else "—"
                p95 = f"{r.p95:.1f}" if r.p95 is not None else "—"
                loss = f"{r.packet_loss:.0f}%"
                status = r.status or "OK"
            else:
                score = "0.0"
                grade = "Failed"
                avg = mn = mx = jit = p95 = "—"
                loss = "100%"
                status = r.status or "Failed"

            gc = Renderer.grade_color(grade)
            sc = Renderer.status_color(status)
            target_trunc = Renderer.truncate(r.target, 28)

            row_cells = [
                Renderer.pad(f"{Color.DIM}{rank}{Color.RESET}", 3, 'right'),
                Renderer.pad(target_trunc, 28, 'left'),
                Renderer.pad(f"{Color.DIM}{r.method}{Color.RESET}", 9, 'left'),
                Renderer.pad(f"{Color.BOLD}{score}{Color.RESET}", 5, 'right'),
                Renderer.pad(f"{gc}{grade}{Color.RESET}", 10, 'left'),
                Renderer.pad(avg, 8, 'right'),
                Renderer.pad(mn, 7, 'right'),
                Renderer.pad(mx, 7, 'right'),
                Renderer.pad(jit, 7, 'right'),
                Renderer.pad(p95, 7, 'right'),
                Renderer.pad(loss, 6, 'right'),
                Renderer.pad(f"{sc}{status}{Color.RESET}", 20, 'left'),
            ]
            print(f"{Color.BLUE}│{Color.RESET} " + '  '.join(row_cells) + f" {Color.BLUE}│{Color.RESET}")

        print(f"{Color.BOLD}{Color.BLUE}╰{'─' * total_w}╯{Color.RESET}")
        print(f"  {Color.DIM}Rank is by custom diagnostic Score (higher = better).{Color.RESET}")

    @staticmethod
    def print_latency_chart(results: List[PingResult]):
        ok = [r for r in results if r.test_success and r.avg is not None]
        if len(ok) < 2:
            return

        ok_sorted = sorted(ok, key=lambda x: x.avg)
        max_avg = max(r.avg for r in ok_sorted)

        print()
        print(f"{Color.BOLD}{Color.CYAN}  Average Latency{Color.RESET} "
              f"{Color.DIM}(sorted, ms){Color.RESET}")
        print(f"{Color.GRAY}  {'─' * 66}{Color.RESET}")

        name_w = min(28, max(len(r.target) for r in ok_sorted))
        for r in ok_sorted:
            name = Renderer.truncate(r.target, name_w).ljust(name_w)
            bar = Renderer.latency_bar(r.avg, max_avg, 24)
            value = f"{r.avg:>7.1f} ms"
            print(f"  {name}  {bar}  {value}")

    @staticmethod
    def print_summary(results: List[PingResult], elapsed: float):
        total = len(results)
        net_ok = [r for r in results if r.reachable]
        test_ok = [r for r in results if r.test_success and r.times]
        failed = [r for r in results if not (r.test_success and r.times)]

        print()
        print(f"{Color.BOLD}{Color.CYAN}  ╭────────────────────── SUMMARY ──────────────────────╮{Color.RESET}")

        def row(label: str, value: str, value_color: str = Color.RESET):
            label_pad = Renderer.pad(label, 22, 'left')
            print(f"  {Color.CYAN}│{Color.RESET} {label_pad} {value_color}{value}{Color.RESET}")

        row("Total targets", str(total))
        row("Network reachable", f"{len(net_ok)}/{total}",
            Color.GREEN if len(net_ok) == total else Color.YELLOW)
        row("Test successful", f"{len(test_ok)}/{total}",
            Color.GREEN if len(test_ok) == total else Color.YELLOW)
        row("Failed", str(len(failed)),
            Color.RED if failed else Color.GREEN)
        row("Total time", f"{elapsed:.2f}s")

        latency_ok = [r for r in test_ok if r.avg is not None]
        score_ok = [r for r in test_ok if r.score is not None]

        if latency_ok or score_ok:
            print(f"  {Color.CYAN}├──────────────────────────────────────────────────────┤{Color.RESET}")

        if latency_ok:
            lowest = min(latency_ok, key=lambda r: r.avg)
            highest = max(latency_ok, key=lambda r: r.avg)
            row("Lowest latency", f"{lowest.target}  ({lowest.avg:.1f} ms)", Color.GREEN)
            row("Highest latency", f"{highest.target}  ({highest.avg:.1f} ms)", Color.YELLOW)

        if score_ok:
            best = max(score_ok, key=lambda r: r.score)
            grade = best.grade or "Unknown"
            row("Highest score",
                f"{best.target}  ({best.score:.1f} — {grade})",
                Color.CYAN)

        mixed = [r for r in test_ok
                 if r.http_status_distribution and len(r.http_status_distribution) > 1]
        if mixed:
            print(f"  {Color.CYAN}├──────────────────────────────────────────────────────┤{Color.RESET}")
            print(f"  {Color.CYAN}│{Color.RESET} {Color.MAGENTA}Mixed HTTP statuses:{Color.RESET}")
            for r in mixed[:8]:
                parts = ', '.join(
                    f"{code}×{cnt}"
                    for code, cnt in sorted(r.http_status_distribution.items())
                )
                line = f"    • {Renderer.truncate(r.target, 24):<24} {parts}"
                print(f"  {Color.CYAN}│{Color.RESET} {line}")

        if failed:
            print(f"  {Color.CYAN}├──────────────────────────────────────────────────────┤{Color.RESET}")
            print(f"  {Color.CYAN}│{Color.RESET} {Color.RED}Failures:{Color.RESET}")
            for r in failed[:8]:
                err = r.error or 'no details'
                line = (
                    f"    • {Renderer.truncate(r.target, 24):<24} "
                    f"[{r.status}]  {Color.DIM}{Renderer.truncate(err, 28)}{Color.RESET}"
                )
                print(f"  {Color.CYAN}│{Color.RESET} {line}")
            if len(failed) > 8:
                print(f"  {Color.CYAN}│{Color.RESET}     ... and {len(failed) - 8} more")

        print(f"  {Color.BOLD}{Color.CYAN}╰──────────────────────────────────────────────────────╯{Color.RESET}")
        print(f"  {Color.DIM}Note: \"Score\" is a custom heuristic for comparing results "
              f"within this tool, not a standard network benchmark.{Color.RESET}")
        print(f"  {Color.DIM}Note: DNS resolution is measured separately from the "
              f"connection; for HTTP, curl resolves DNS internally.{Color.RESET}")


# ============================================================
# RUNNER
# ============================================================

class PingRunner:

    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.results: List[PingResult] = []

    def _log(self, msg: str, color: str = Color.RESET):
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"{Color.GRAY}[{ts}]{Color.RESET} {color}{msg}{Color.RESET}")

    def run(self) -> int:
        started = time.time()
        targets = TargetParser.parse_sites(self.args.targets)
        if not targets:
            self._log("No valid targets found.", Color.RED)
            return 2

        if self.args.proxy:
            try:
                parsed = urlparse(self.args.proxy)
                if parsed.scheme not in ('http', 'https', 'socks4', 'socks5'):
                    raise ValueError(f"unsupported scheme: {parsed.scheme}")
                if not parsed.hostname or not parsed.port:
                    raise ValueError("host or port missing")
                PingEngine.set_proxy(self.args.proxy,
                                     self.args.proxy_user, self.args.proxy_pass)
                self._log(f"Proxy enabled (HTTP method only): {self.args.proxy}",
                          Color.CYAN)
            except Exception as e:
                self._log(f"Invalid proxy: {e}", Color.RED)
                return 2

        self._log(
            f"Starting: {len(targets)} targets • "
            f"{self.args.count} pings • "
            f"method={self.args.method} • "
            f"timeout={self.args.timeout}s • "
            f"workers={self.args.workers}",
            Color.BOLD,
        )

        if not self.args.no_progress and not self.args.quiet:
            print()

        results = self._ping_all(targets)
        results = self._rank(results)
        self.results = results

        elapsed = time.time() - started

        if not self.args.quiet:
            Renderer.clear_line()
            Renderer.print_results_table(results)
            Renderer.print_latency_chart(results)
            Renderer.print_summary(results, elapsed)
        else:
            for r in results:
                if r.test_success and r.times:
                    avg = r.avg if r.avg is not None else 0.0
                    score = r.score if r.score is not None else 0.0
                    print(f"OK    {r.target:<40} "
                          f"score={score:>5.1f} avg={avg:>7.1f}ms "
                          f"loss={r.packet_loss:>4.0f}% {r.status}")
                else:
                    print(f"FAIL  {r.target:<40} {r.status}  {r.error or ''}")

        if self.args.output_csv:
            self._export_csv(self.args.output_csv)
        if self.args.output_json:
            self._export_json(self.args.output_json)

        def is_real_success(r):
            return r.test_success and bool(r.times)

        if all(is_real_success(r) for r in results):
            return 0
        return 1

    def _ping_all(self, targets) -> List[PingResult]:
        results: List[PingResult] = []
        total = len(targets)
        completed = 0
        lock = threading.Lock()

        def ping_one(target):
            return PingEngine.ping_host(
                target, self.args.method, self.args.count,
                self.args.timeout, self.stop_event,
            )

        try:
            with ThreadPoolExecutor(max_workers=min(self.args.workers, total)) as ex:
                futures = {ex.submit(ping_one, t): t for t in targets}
                for fut in as_completed(futures):
                    if self.stop_event.is_set():
                        ex.shutdown(wait=False, cancel_futures=True)
                        break

                    target = futures[fut]
                    try:
                        r = fut.result()
                        r.target = target['host']
                    except Exception as e:
                        r = PingResult(
                            target=target['host'], method=self.args.method,
                            status='Error', error=str(e)[:80],
                        )

                    with lock:
                        results.append(r)
                        completed += 1
                        if not self.args.no_progress and not self.args.quiet:
                            Renderer.progress(
                                completed, total, target['host'], r.status,
                            )
        except KeyboardInterrupt:
            self._log("\nInterrupted by user. Stopping...", Color.YELLOW)
            self.stop_event.set()

        return results

    @staticmethod
    def _rank(results: List[PingResult]) -> List[PingResult]:
        successful = [r for r in results if r.test_success and r.times]
        successful.sort(
            key=lambda x: x.score if x.score is not None else 0,
            reverse=True,
        )
        for i, r in enumerate(successful, 1):
            r.rank = i

        failed = [r for r in results if not (r.test_success and r.times)]
        failed.sort(key=lambda x: (not x.reachable, x.target))
        return successful + failed

    def _export_csv(self, path: str):
        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow([
                    'Rank', 'Target', 'Method',
                    'Reachable', 'TestSuccess', 'ApplicationOK',
                    'Score', 'Grade',
                    'Avg', 'Min', 'Max', 'Jitter',
                    'P50', 'P95', 'P99',
                    'Loss %', 'Status', 'Error',
                    'Resolved IP', 'Family',
                    'DNS avg', 'Connect avg', 'TTFB avg', 'Total avg',
                    'HTTP status', 'HTTP distribution',
                ])
                for r in self.results:
                    dist_str = ''
                    if r.http_status_distribution:
                        dist_str = ';'.join(
                            f"{code}:{cnt}"
                            for code, cnt in sorted(r.http_status_distribution.items())
                        )
                    w.writerow([
                        r.rank if r.rank else '',
                        r.target, r.method,
                        r.reachable, r.test_success,
                        r.application_ok if r.application_ok is not None else '',
                        r.score if r.score is not None else '',
                        r.grade or '',
                        r.avg, r.min, r.max, r.jitter,
                        r.p50, r.p95, r.p99,
                        r.packet_loss,
                        r.status, r.error or '',
                        r.resolved_ip or '', r.ip_family or '',
                        r.dns.avg if r.dns.avg is not None else '',
                        r.connect.avg if r.connect.avg is not None else '',
                        r.ttfb.avg if r.ttfb.avg is not None else '',
                        r.total.avg if r.total.avg is not None else '',
                        r.http_status if r.http_status else '',
                        dist_str,
                    ])
            self._log(f"CSV → {path}", Color.GREEN)
        except Exception as e:
            self._log(f"CSV export failed: {e}", Color.RED)

    def _export_json(self, path: str):
        try:
            data = {
                'tool': 'Network Ping Pro',
                'version': __version__,
                'timestamp': datetime.now().isoformat(),
                'method': self.args.method,
                'count': self.args.count,
                'timeout': self.args.timeout,
                'total': len(self.results),
                'results': [asdict(r) for r in self.results],
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._log(f"JSON → {path}", Color.GREEN)
        except Exception as e:
            self._log(f"JSON export failed: {e}", Color.RED)


# ============================================================
# ARGUMENT PARSER
# ============================================================

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
    p.add_argument('--proxy-pass', help='Proxy password')

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
    args.count = max(1, min(200, args.count))
    args.timeout = max(1.0, min(30.0, args.timeout))
    args.workers = max(1, min(50, args.workers))
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


# ============================================================
# MAIN
# ============================================================

def main(argv=None) -> int:
    Color.enable_windows_ansi()

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.no_color:
        Color.disable()

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

    Renderer.banner()
    print()

    try:
        runner = PingRunner(args)
        return runner.run()
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Interrupted by user.{Color.RESET}")
        return 130


if __name__ == '__main__':
    sys.exit(main())