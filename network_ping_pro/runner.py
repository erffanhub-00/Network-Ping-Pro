"""Orchestration: run targets concurrently, rank results, export CSV/JSON."""

import csv
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from .color import Color
from .engine import PingEngine
from .models import PingResult
from .render import Renderer
from .targets import TargetParser
from .version import __version__


class PingRunner:

    def __init__(self, args):
        self.args = args
        self.stop_event = threading.Event()
        self.results: List[PingResult] = []

    def _log(self, msg: str, color: str = Color.RESET):
        ts = datetime.now().strftime('%H:%M:%S')
        # In quiet mode stdout is machine-readable output; logs go to stderr.
        stream = sys.stderr if getattr(self.args, 'quiet', False) else sys.stdout
        print(f"{Color.GRAY}[{ts}]{Color.RESET} {color}{msg}{Color.RESET}", file=stream)

    def run(self) -> int:
        started = time.time()
        targets = TargetParser.parse_sites(self.args.targets)
        if not targets:
            self._log("No valid targets found.", Color.RED)
            return 2

        for bad in TargetParser.last_skipped:
            self._log(f"Skipped invalid target: {bad}", Color.YELLOW)

        if self.args.proxy:
            try:
                parsed = urlparse(self.args.proxy)
                if parsed.scheme not in ('http', 'https', 'socks4', 'socks5'):
                    raise ValueError(f"unsupported scheme: {parsed.scheme}")
                if not parsed.hostname or not parsed.port:
                    raise ValueError("host or port missing")
                PingEngine.set_proxy(self.args.proxy,
                                     self.args.proxy_user, self.args.proxy_pass)
                # Log the proxy without credentials: a password in the
                # URL must never end up in the terminal or a log file.
                self._log(f"Proxy enabled (HTTP method only): "
                          f"{PingEngine.proxy_display_url()}", Color.CYAN)
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

        export_ok = True
        if self.args.output_csv:
            export_ok = self._export_csv(self.args.output_csv) and export_ok
        if self.args.output_json:
            export_ok = self._export_json(self.args.output_json) and export_ok

        if not export_ok:
            return 1

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

    def _export_csv(self, path: str) -> bool:
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
            return True
        except Exception as e:
            self._log(f"CSV export failed: {e}", Color.RED)
            return False

    def _export_json(self, path: str) -> bool:
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
            return True
        except Exception as e:
            self._log(f"JSON export failed: {e}", Color.RED)
            return False
