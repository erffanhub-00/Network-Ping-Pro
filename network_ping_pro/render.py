"""Terminal rendering: banner, progress line, results table, chart, summary."""

import re
import sys
from typing import List, Optional

from .color import Color
from .models import PingResult
from .version import __author__, __version__


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
