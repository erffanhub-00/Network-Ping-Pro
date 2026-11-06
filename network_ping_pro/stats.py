"""Statistics and the custom diagnostic Score.

The Score is a heuristic for comparing results WITHIN this tool.
It is NOT an industry-standard network benchmark.
"""

from typing import Any, Dict, List, Optional

from .models import PingResult, StageStats


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
        """Mean/min/max, jitter and percentiles of a sample list.

        Jitter here is the mean absolute difference between consecutive
        samples. That is NOT the RFC 3550 interarrival jitter; it is a
        simple stability indicator for these measurements.
        """
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
        """Per-stage stats (DNS / connect / TTFB / total).

        Stages with a single sample (e.g. DNS, measured once) report
        that sample as avg/min/max/p50/p95/p99. Percentiles of one
        value carry no extra information; check `samples` to see how
        many measurements back the numbers.
        """
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

        final = (latency * 0.40 + loss * 0.35 + jitter * 0.25) * p95_penalty * app_penalty
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
