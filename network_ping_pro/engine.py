"""Measurement engines: ICMP (system ping), TCP connect and HTTP (curl)."""

import platform
import re
import socket
import subprocess
import threading
import time
from collections import Counter
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse

from .dns import DNSResolver
from .models import PingResult, StageStats
from .stats import StatisticsEngine


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
    def proxy_display_url() -> Optional[str]:
        """Proxy URL without credentials, safe for logs."""
        if not PingEngine.PROXY_URL:
            return None
        parsed = urlparse(PingEngine.PROXY_URL)
        if not parsed.scheme or not parsed.hostname:
            return 'proxy (unparsable URL)'
        host = parsed.hostname
        if ':' in host and not host.startswith('['):
            host = f"[{host}]"
        port = f":{parsed.port}" if parsed.port else ''
        return f"{parsed.scheme}://{host}{port}"

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
            cmd = ['ping', '-n', str(count), '-w', str(w_ms), '--', host]
        elif system == 'darwin':
            w_ms = max(1, int(round(timeout * 1000)))
            cmd = ['ping', '-c', str(count), '-W', str(w_ms), '--', host]
        else:
            cmd = ['ping', '-c', str(count), '-W', f'{timeout:.2f}', '--', host]

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

            # Only reply lines (time=..ms) count as replies. The summary
            # line (rtt min/avg/max/mdev = ...) must not be counted:
            # its numbers are statistics, not individual pings.
            times: List[float] = []
            for m in re.findall(r'time[=<]\s*(\d+(?:[.,]\d+)?)\s*ms',
                                output, re.IGNORECASE):
                try:
                    v = float(m.replace(',', '.'))
                    if 0 <= v <= 10000:
                        times.append(v)
                except ValueError:
                    continue
            times = times[:count]

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
            # Same grade _finalize() assigns to any result with no
            # samples: the host answered, but no measurement exists,
            # so there is nothing to score. (Was 'Poor', which
            # disagreed with _finalize().)
            r.grade = 'Failed'
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
        last_curl_error: Optional[str] = None

        proxy_url = PingEngine._build_proxy_url()
        timeout_str = f'{timeout:.2f}'

        for _ in range(count):
            if stop_event.is_set():
                r.error = 'Cancelled'
                r.status = 'Cancelled'
                return r

            cmd = [
                'curl', '-s', '-L', '-o', PingEngine.NULL_DEVICE,
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
                    if stderr.strip():
                        last_curl_error = stderr.strip().splitlines()[-1][:100]
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
            if last_curl_error:
                r.error += f' ({last_curl_error})'
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
            # Representative status is the most common code, not the max:
            # a mix of 200 and 500 must not be reported as just 500.
            r.http_status = dist.most_common(1)[0][0]

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

            if len(unique) == 1:
                if r.application_ok:
                    r.status = 'OK'
                else:
                    txt = r.http_status_text or ''
                    r.status = f'HTTP {r.http_status} {txt}'.strip()
            elif all(200 <= c < 400 for c in unique):
                r.status = 'Mixed 2xx/3xx'
            else:
                parts = ', '.join(
                    f"{c}x{n}" for c, n in sorted(dist.items())
                )
                r.status = f'Mixed: {parts}'
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

        # A host starting with '-' must never reach a subprocess as an
        # option (option injection via a targets file).
        if not host or host.startswith('-'):
            return PingResult(target=host, method=method,
                              status='Error', error='Invalid host')

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
