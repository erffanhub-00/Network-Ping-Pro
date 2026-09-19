#!/usr/bin/env python3
# ============================================================
# Unit tests for Network Ping Pro
# Run with: pytest -v
# ============================================================

import argparse
import csv
import json
import os
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch, MagicMock

import pytest

# Import the module under test
import network_ping_pro as npp
from network_ping_pro import (
    Color,
    StageStats,
    PingResult,
    StatisticsEngine,
    DNSResolver,
    PingEngine,
    TargetParser,
    Renderer,
    PingRunner,
    build_parser,
    clamp_args,
    load_targets_from_file,
    main,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def stop_event():
    return threading.Event()


@pytest.fixture
def sample_times():
    return [10.0, 12.0, 11.0, 13.0, 14.0, 12.0, 11.0, 15.0, 13.0, 12.0]


@pytest.fixture
def good_result():
    r = PingResult(target='test.com', method='ICMP')
    r.reachable = True
    r.test_success = True
    r.times = [10.0, 12.0, 11.0]
    r.successes = 3
    r.attempts = 3
    r.status = 'OK'
    PingEngine._finalize(r)
    return r


# ============================================================
# 1. Color
# ============================================================

class TestColor:
    def test_color_constants_exist(self):
        assert Color.RESET == '\033[0m'
        assert Color.BOLD == '\033[1m'
        assert Color.GREEN == '\033[92m'
        assert Color.RED == '\033[91m'

    def test_disable(self):
        saved = Color.GREEN
        Color.disable()
        assert Color.GREEN == ''
        Color.GREEN = saved


# ============================================================
# 2. StageStats
# ============================================================

class TestStageStats:
    def test_default_values(self):
        s = StageStats()
        assert s.avg is None
        assert s.min is None
        assert s.max is None
        assert s.p50 is None
        assert s.p95 is None
        assert s.p99 is None
        assert s.samples == 0

    def test_custom_values(self):
        s = StageStats(avg=10.5, min=8.0, max=15.0, samples=5)
        assert s.avg == 10.5
        assert s.min == 8.0
        assert s.max == 15.0
        assert s.samples == 5


# ============================================================
# 3. PingResult
# ============================================================

class TestPingResult:
    def test_defaults(self):
        r = PingResult(target='example.com', method='ICMP')
        assert r.target == 'example.com'
        assert r.method == 'ICMP'
        assert r.reachable is False
        assert r.test_success is False
        assert r.application_ok is None
        assert r.times == []
        assert r.attempts == 0
        assert r.successes == 0
        assert r.packet_loss == 100.0
        assert r.status == 'Failed'

    def test_times_list_is_unique(self):
        r1 = PingResult(target='a.com', method='ICMP')
        r2 = PingResult(target='b.com', method='ICMP')
        r1.times.append(1.0)
        assert r2.times == []


# ============================================================
# 4. StatisticsEngine - percentiles
# ============================================================

class TestPercentiles:
    def test_empty(self):
        result = StatisticsEngine.percentiles([])
        assert result == {'p50': None, 'p95': None, 'p99': None}

    def test_single_value(self):
        result = StatisticsEngine.percentiles([42.0])
        assert result['p50'] == 42.0
        assert result['p95'] == 42.0
        assert result['p99'] == 42.0

    def test_p50_median(self):
        result = StatisticsEngine.percentiles([10.0, 20.0, 30.0])
        assert result['p50'] == 20.0

    def test_p95_in_range(self):
        times = list(range(1, 101))
        result = StatisticsEngine.percentiles([float(t) for t in times])
        assert 94.0 <= result['p95'] <= 96.0

    def test_p99_in_range(self):
        times = list(range(1, 101))
        result = StatisticsEngine.percentiles([float(t) for t in times])
        assert 98.0 <= result['p99'] <= 100.0

    def test_p50_with_two_values(self):
        result = StatisticsEngine.percentiles([10.0, 20.0])
        assert result['p50'] == 15.0


# ============================================================
# 5. StatisticsEngine - basic_stats
# ============================================================

class TestBasicStats:
    def test_empty(self):
        assert StatisticsEngine.basic_stats([]) == {}

    def test_single_value(self):
        st = StatisticsEngine.basic_stats([10.0])
        assert st['avg'] == 10.0
        assert st['min'] == 10.0
        assert st['max'] == 10.0
        assert st['jitter'] == 0.0

    def test_multiple_values(self):
        st = StatisticsEngine.basic_stats([10.0, 20.0, 30.0])
        assert st['avg'] == 20.0
        assert st['min'] == 10.0
        assert st['max'] == 30.0
        assert st['jitter'] == 10.0

    def test_jitter_uses_absolute_difference(self):
        st = StatisticsEngine.basic_stats([10.0, 5.0, 15.0])
        assert st['jitter'] == 7.5


# ============================================================
# 6. StatisticsEngine - stage_stats
# ============================================================

class TestStageStatsBuilder:
    def test_empty(self):
        s = StatisticsEngine.stage_stats([])
        assert s.samples == 0
        assert s.avg is None

    def test_with_samples(self):
        s = StatisticsEngine.stage_stats([10.0, 20.0, 30.0])
        assert s.samples == 3
        assert s.avg == 20.0
        assert s.min == 10.0
        assert s.max == 30.0


# ============================================================
# 7. StatisticsEngine - calculate_score
# ============================================================

class TestCalculateScore:
    def test_not_successful_returns_zero(self):
        r = PingResult(target='x', method='ICMP')
        r.test_success = False
        assert StatisticsEngine.calculate_score(r) == 0.0

    def test_perfect_score(self):
        r = PingResult(target='x', method='ICMP')
        r.test_success = True
        r.avg = 5.0
        r.packet_loss = 0.0
        r.jitter = 1.0
        r.p95 = 8.0
        score = StatisticsEngine.calculate_score(r)
        assert score >= 90.0

    def test_high_latency_low_score(self):
        # Score is a weighted sum: latency only contributes 35%.
        # With loss=0 and jitter=1, the score stays moderate even at high latency.
        r = PingResult(target='x', method='ICMP')
        r.test_success = True
        r.avg = 1000.0
        r.packet_loss = 0.0
        r.jitter = 1.0
        r.p95 = 1100.0
        score = StatisticsEngine.calculate_score(r)
        assert score < 70.0

    def test_full_loss_low_score(self):
        # Loss contributes 30%. A perfect latency + jitter still leaves
        # the score below ~70 even with 100% loss.
        r = PingResult(target='x', method='ICMP')
        r.test_success = True
        r.avg = 10.0
        r.packet_loss = 100.0
        r.jitter = 1.0
        r.p95 = 12.0
        score = StatisticsEngine.calculate_score(r)
        assert score < 70.0

        # Compare with a perfect-loss-free run
        r2 = PingResult(target='x', method='ICMP')
        r2.test_success = True
        r2.avg = 10.0
        r2.packet_loss = 0.0
        r2.jitter = 1.0
        r2.p95 = 12.0
        assert score < StatisticsEngine.calculate_score(r2)

    def test_http_500_penalty(self):
        r1 = PingResult(target='x', method='HTTP')
        r1.test_success = True
        r1.avg = 50.0
        r1.packet_loss = 0.0
        r1.jitter = 5.0
        r1.p95 = 60.0
        r1.http_status = 200
        r1.application_ok = True
        score_ok = StatisticsEngine.calculate_score(r1)

        r2 = PingResult(target='x', method='HTTP')
        r2.test_success = True
        r2.avg = 50.0
        r2.packet_loss = 0.0
        r2.jitter = 5.0
        r2.p95 = 60.0
        r2.http_status = 500
        r2.application_ok = False
        score_500 = StatisticsEngine.calculate_score(r2)

        assert score_500 < score_ok

    def test_score_bounded_0_100(self):
        r = PingResult(target='x', method='ICMP')
        r.test_success = True
        r.avg = 5.0
        r.packet_loss = 0.0
        r.jitter = 0.5
        r.p95 = 6.0
        score = StatisticsEngine.calculate_score(r)
        assert 0.0 <= score <= 100.0


# ============================================================
# 8. StatisticsEngine - get_grade
# ============================================================

class TestGetGrade:
    @pytest.mark.parametrize("score,expected", [
        (100.0, 'Excellent'),
        (95.0, 'Excellent'),
        (90.0, 'Excellent'),
        (89.9, 'Very Good'),
        (80.0, 'Very Good'),
        (79.9, 'Good'),
        (70.0, 'Good'),
        (69.9, 'Fair'),
        (60.0, 'Fair'),
        (59.9, 'Poor'),
        (0.0, 'Poor'),
    ])
    def test_grades(self, score, expected):
        assert StatisticsEngine.get_grade(score) == expected


# ============================================================
# 9. DNSResolver
# ============================================================

class TestDNSResolver:
    def test_localhost(self):
        ip, family, elapsed, error = DNSResolver.resolve('localhost', timeout=2)
        assert error is None
        assert ip is not None
        assert family in ('IPv4', 'IPv6')
        assert elapsed is not None
        assert elapsed >= 0

    def test_nonexistent_host(self):
        ip, family, elapsed, error = DNSResolver.resolve(
            'this-host-should-not-exist-12345.invalid', timeout=2
        )
        assert ip is None
        assert error is not None

    def test_ip_literal(self):
        ip, family, elapsed, error = DNSResolver.resolve('127.0.0.1', timeout=2)
        assert error is None
        assert ip == '127.0.0.1'
        assert family == 'IPv4'

    def test_timeout_returns_error(self):
        def slow_getaddrinfo(*args, **kwargs):
            time.sleep(5)
            return []

        with patch('socket.getaddrinfo', side_effect=slow_getaddrinfo):
            ip, family, elapsed, error = DNSResolver.resolve('example.com', timeout=0.3)
            assert ip is None
            assert 'timeout' in error.lower()


# ============================================================
# 10. PingEngine - proxy URL
# ============================================================

class TestProxyURL:
    def setup_method(self):
        PingEngine.clear_proxy()

    def teardown_method(self):
        PingEngine.clear_proxy()

    def test_no_proxy(self):
        assert PingEngine._build_proxy_url() is None

    def test_simple_proxy(self):
        PingEngine.set_proxy('socks5://127.0.0.1:10808')
        url = PingEngine._build_proxy_url()
        assert url == 'socks5://127.0.0.1:10808'

    def test_proxy_with_credentials(self):
        PingEngine.set_proxy('socks5://127.0.0.1:10808', 'user', 'pass')
        url = PingEngine._build_proxy_url()
        assert 'user:pass@' in url

    def test_proxy_credentials_url_encoded(self):
        PingEngine.set_proxy('http://127.0.0.1:8080', 'user@name', 'p@ss:word')
        url = PingEngine._build_proxy_url()
        assert 'user%40name' in url
        assert 'p%40ss%3Aword' in url

    def test_ipv6_proxy_wrapped(self):
        PingEngine.set_proxy('socks5://[::1]:1080')
        url = PingEngine._build_proxy_url()
        assert '[::1]' in url

    def test_clear_proxy(self):
        PingEngine.set_proxy('socks5://127.0.0.1:10808')
        PingEngine.clear_proxy()
        assert PingEngine._build_proxy_url() is None


# ============================================================
# 11. PingEngine - _finalize
# ============================================================

class TestFinalize:
    def test_empty_times_forces_failure(self):
        r = PingResult(target='x', method='ICMP')
        r.test_success = True
        r.status = 'OK'
        r.times = []
        PingEngine._finalize(r)
        assert r.test_success is False
        assert r.packet_loss == 100.0
        assert r.score == 0.0
        assert r.status == 'Failed'

    def test_with_times_sets_stats(self):
        r = PingResult(target='x', method='ICMP')
        r.times = [10.0, 20.0, 30.0]
        r.attempts = 3
        r.successes = 3
        r.test_success = True
        r.status = 'OK'
        PingEngine._finalize(r)
        assert r.avg == 20.0
        assert r.min == 10.0
        assert r.max == 30.0
        assert r.packet_loss == 0.0
        assert r.score is not None
        assert r.grade is not None
        assert r.status == 'OK'

    def test_partial_loss_sets_partial_status(self):
        r = PingResult(target='x', method='ICMP')
        r.times = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
        r.attempts = 10
        r.successes = 9
        r.test_success = True
        r.status = 'OK'
        PingEngine._finalize(r)
        assert r.packet_loss == 10.0
        assert r.status == 'Partial'

    def test_high_loss_sets_high_loss_status(self):
        r = PingResult(target='x', method='ICMP')
        r.times = [10.0, 20.0]
        r.attempts = 10
        r.successes = 2
        r.test_success = True
        r.status = 'OK'
        PingEngine._finalize(r)
        assert r.packet_loss == 80.0
        assert r.status == 'High Loss'


# ============================================================
# 12. PingEngine - ping_host dispatcher
# ============================================================

class TestPingHostDispatcher:
    def test_cancelled_stop_event(self, stop_event):
        stop_event.set()
        r = PingEngine.ping_host(
            {'host': 'example.com'}, 'ICMP', 1, 1, stop_event
        )
        assert r.status == 'Cancelled'
        assert r.test_success is False

    def test_unknown_method(self, stop_event):
        r = PingEngine.ping_host(
            {'host': 'example.com'}, 'BOGUS', 1, 1, stop_event
        )
        assert r.status == 'Error'
        assert r.error == 'Unknown method'


# ============================================================
# 13. TargetParser
# ============================================================

class TestTargetParser:
    def test_empty(self):
        assert TargetParser.parse_target('') is None
        assert TargetParser.parse_target('   ') is None

    def test_simple_host(self):
        p = TargetParser.parse_target('google.com')
        assert p['host'] == 'google.com'
        assert p['port'] is None
        assert p['scheme'] is None

    def test_host_with_port(self):
        p = TargetParser.parse_target('google.com:443')
        assert p['host'] == 'google.com'
        assert p['port'] == 443

    def test_https_url(self):
        p = TargetParser.parse_target('https://example.com/api')
        assert p['host'] == 'example.com'
        assert p['scheme'] == 'https'
        assert p['path'] == '/api'

    def test_url_with_query(self):
        p = TargetParser.parse_target('https://example.com/search?q=test&x=1')
        assert p['host'] == 'example.com'
        assert p['path'] == '/search'
        assert p['query'] == 'q=test&x=1'

    def test_ipv6_with_port(self):
        p = TargetParser.parse_target('[::1]:8080')
        assert p['host'] == '::1'
        assert p['port'] == 8080

    def test_ipv6_without_port(self):
        p = TargetParser.parse_target('[2001:db8::1]')
        assert p['host'] == '2001:db8::1'
        assert p['port'] is None

    def test_host_lowercased(self):
        p = TargetParser.parse_target('GOOGLE.COM')
        assert p['host'] == 'google.com'


class TestTargetParserSites:
    def test_empty(self):
        assert TargetParser.parse_sites('') == []

    def test_single(self):
        result = TargetParser.parse_sites('google.com')
        assert len(result) == 1

    def test_comma_separated(self):
        result = TargetParser.parse_sites('google.com,github.com')
        assert len(result) == 2

    def test_newline_separated(self):
        result = TargetParser.parse_sites('google.com\ngithub.com')
        assert len(result) == 2

    def test_deduplication(self):
        result = TargetParser.parse_sites('google.com,google.com')
        assert len(result) == 1

    def test_query_not_deduplicated(self):
        result = TargetParser.parse_sites('example.com/a?x=1,example.com/a?x=2')
        assert len(result) == 2

    def test_persian_comma(self):
        result = TargetParser.parse_sites('google.com،github.com')
        assert len(result) == 2

    def test_invalid_skipped(self):
        result = TargetParser.parse_sites('google.com,,,github.com')
        assert len(result) == 2


# ============================================================
# 14. Renderer
# ============================================================

class TestRendererHelpers:
    def test_visible_len_plain(self):
        assert Renderer.visible_len('hello') == 5

    def test_visible_len_with_ansi(self):
        assert Renderer.visible_len(f"{Color.RED}hello{Color.RESET}") == 5

    def test_pad_left(self):
        assert Renderer.pad('hi', 5, 'left') == 'hi   '

    def test_pad_right(self):
        assert Renderer.pad('hi', 5, 'right') == '   hi'

    def test_pad_center(self):
        assert Renderer.pad('hi', 6, 'center') == '  hi  '

    def test_pad_with_ansi(self):
        s = f"{Color.RED}hi{Color.RESET}"
        padded = Renderer.pad(s, 5)
        assert Renderer.visible_len(padded) == 5

    def test_truncate(self):
        assert Renderer.truncate('hello world', 5) == 'hell…'

    def test_truncate_no_change(self):
        assert Renderer.truncate('hi', 10) == 'hi'


class TestGradeColor:
    def test_excellent(self):
        assert Renderer.grade_color('Excellent') == Color.GREEN

    def test_poor(self):
        assert Renderer.grade_color('Poor') == Color.RED

    def test_unknown(self):
        assert Renderer.grade_color('Unknown') == Color.RESET


class TestStatusColor:
    def test_ok(self):
        assert Renderer.status_color('OK') == Color.GREEN

    def test_partial(self):
        assert Renderer.status_color('Partial') == Color.YELLOW

    def test_http_404(self):
        assert Renderer.status_color('HTTP 404 Not Found') == Color.MAGENTA

    def test_refused(self):
        assert Renderer.status_color('Refused') == Color.RED


# ============================================================
# 15. PingRunner - _rank
# ============================================================

class TestRank:
    def test_empty(self):
        assert PingRunner._rank([]) == []

    def test_only_successful_sorted_by_score(self):
        r1 = PingResult(target='a', method='ICMP')
        r1.test_success = True
        r1.times = [10.0]
        r1.score = 90.0

        r2 = PingResult(target='b', method='ICMP')
        r2.test_success = True
        r2.times = [20.0]
        r2.score = 50.0

        ranked = PingRunner._rank([r2, r1])
        assert ranked[0].target == 'a'
        assert ranked[1].target == 'b'
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_failed_at_end(self):
        r_ok = PingResult(target='ok', method='ICMP')
        r_ok.test_success = True
        r_ok.times = [10.0]
        r_ok.score = 90.0

        r_fail = PingResult(target='fail', method='ICMP')
        r_fail.test_success = False

        ranked = PingRunner._rank([r_fail, r_ok])
        assert ranked[0].target == 'ok'
        assert ranked[1].target == 'fail'
        assert ranked[1].rank is None

    def test_success_without_times_treated_as_failed(self):
        r = PingResult(target='x', method='TCP')
        r.test_success = True
        r.times = []

        ranked = PingRunner._rank([r])
        assert ranked[0].rank is None


# ============================================================
# 16. Argument parser
# ============================================================

class TestArgumentParser:
    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args(['google.com'])
        assert args.method == 'ICMP'
        assert args.count == 10
        assert args.timeout == 3.0
        assert args.workers == 10
        assert args.targets == ['google.com']

    def test_method_tcp(self):
        parser = build_parser()
        args = parser.parse_args(['-m', 'TCP', 'google.com:443'])
        assert args.method == 'TCP'

    def test_method_invalid(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['-m', 'INVALID', 'google.com'])

    def test_count(self):
        parser = build_parser()
        args = parser.parse_args(['-c', '20', 'google.com'])
        assert args.count == 20

    def test_timeout(self):
        parser = build_parser()
        args = parser.parse_args(['-t', '5.5', 'google.com'])
        assert args.timeout == 5.5

    def test_proxy(self):
        parser = build_parser()
        args = parser.parse_args([
            '--proxy', 'socks5://127.0.0.1:10808', 'google.com'
        ])
        assert args.proxy == 'socks5://127.0.0.1:10808'

    def test_quiet(self):
        parser = build_parser()
        args = parser.parse_args(['-q', 'google.com'])
        assert args.quiet is True


class TestClampArgs:
    def test_count_low(self):
        args = argparse.Namespace(count=0, timeout=3.0, workers=10)
        args = clamp_args(args)
        assert args.count == 1

    def test_count_high(self):
        args = argparse.Namespace(count=999, timeout=3.0, workers=10)
        args = clamp_args(args)
        assert args.count == 200

    def test_timeout_low(self):
        args = argparse.Namespace(count=10, timeout=0.1, workers=10)
        args = clamp_args(args)
        assert args.timeout == 1.0

    def test_timeout_high(self):
        args = argparse.Namespace(count=10, timeout=100.0, workers=10)
        args = clamp_args(args)
        assert args.timeout == 30.0

    def test_workers_low(self):
        args = argparse.Namespace(count=10, timeout=3.0, workers=0)
        args = clamp_args(args)
        assert args.workers == 1

    def test_workers_high(self):
        args = argparse.Namespace(count=10, timeout=3.0, workers=999)
        args = clamp_args(args)
        assert args.workers == 50


# ============================================================
# 17. File loading
# ============================================================

class TestLoadTargetsFromFile:
    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_targets_from_file('/tmp/does-not-exist-12345.txt')

    def test_basic(self, tmp_path):
        f = tmp_path / 'targets.txt'
        f.write_text('google.com\ngithub.com\n')
        result = load_targets_from_file(str(f))
        assert result == ['google.com', 'github.com']

    def test_with_comments(self, tmp_path):
        f = tmp_path / 'targets.txt'
        f.write_text('# comment\ngoogle.com\n\n# another\ngithub.com\n')
        result = load_targets_from_file(str(f))
        assert result == ['google.com', 'github.com']

    def test_empty_file(self, tmp_path):
        f = tmp_path / 'targets.txt'
        f.write_text('')
        assert load_targets_from_file(str(f)) == []


# ============================================================
# 18. Export functions
# ============================================================

class TestExport:
    def _make_runner(self):
        parser = build_parser()
        args = parser.parse_args(['google.com'])
        args = clamp_args(args)
        return PingRunner(args)

    def test_export_csv(self, tmp_path):
        runner = self._make_runner()
        r = PingResult(target='example.com', method='ICMP')
        r.test_success = True
        r.reachable = True
        r.times = [10.0, 20.0, 30.0]
        r.attempts = 3
        r.successes = 3
        r.status = 'OK'
        PingEngine._finalize(r)
        runner.results = [r]

        out = tmp_path / 'out.csv'
        runner._export_csv(str(out))
        assert out.exists()

        with open(out, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['Target'] == 'example.com'
        assert rows[0]['Method'] == 'ICMP'

    def test_export_json(self, tmp_path):
        runner = self._make_runner()
        r = PingResult(target='example.com', method='ICMP')
        r.test_success = True
        r.reachable = True
        r.times = [10.0, 20.0]
        r.attempts = 2
        r.successes = 2
        r.status = 'OK'
        PingEngine._finalize(r)
        runner.results = [r]

        out = tmp_path / 'out.json'
        runner._export_json(str(out))
        assert out.exists()

        with open(out, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['tool'] == 'Network Ping Pro'
        assert data['total'] == 1
        assert data['results'][0]['target'] == 'example.com'


# ============================================================
# 19. ping_tcp - mocked (regression for the r.times bug)
# ============================================================

class TestPingTcpMocked:
    def test_successful_connect_sets_times(self, stop_event):
        with patch.object(DNSResolver, 'resolve',
                          return_value=('127.0.0.1', 'IPv4', 1.0, None)):
            with patch('socket.socket') as mock_socket:
                mock_sock = MagicMock()
                mock_socket.return_value = mock_sock

                r = PingEngine.ping_tcp('example.com', 80, 1, 1, stop_event)

                assert r.test_success is True
                assert r.times
                assert r.avg is not None
                assert r.score is not None
                assert r.grade is not None

    def test_connection_refused_sets_reachable(self, stop_event):
        with patch.object(DNSResolver, 'resolve',
                          return_value=('127.0.0.1', 'IPv4', 1.0, None)):
            with patch('socket.socket') as mock_socket:
                mock_sock = MagicMock()
                mock_sock.connect.side_effect = ConnectionRefusedError()
                mock_socket.return_value = mock_sock

                r = PingEngine.ping_tcp('example.com', 80, 1, 1, stop_event)

                assert r.reachable is True
                assert r.test_success is False
                assert r.status == 'Refused'
                assert r.times == []

    def test_dns_failure(self, stop_event):
        with patch.object(DNSResolver, 'resolve',
                          return_value=(None, None, None, 'DNS failed')):
            r = PingEngine.ping_tcp('example.com', 80, 1, 1, stop_event)
            assert r.status == 'DNS Error'
            assert r.test_success is False
            assert 'DNS' in r.error


# ============================================================
# 20. ping_http - mocked
# ============================================================

class TestPingHttpMocked:
    def test_curl_not_installed(self, stop_event):
        with patch.object(DNSResolver, 'resolve',
                          return_value=('1.2.3.4', 'IPv4', 1.0, None)):
            with patch('subprocess.run', side_effect=FileNotFoundError):
                r = PingEngine.ping_http(
                    {'host': 'example.com', 'scheme': 'https',
                     'port': None, 'path': '/', 'query': ''},
                    1, 1, stop_event
                )
                assert r.status == 'Error'
                assert 'curl' in r.error.lower()

    def test_dns_failure(self, stop_event):
        with patch.object(DNSResolver, 'resolve',
                          return_value=(None, None, None, 'DNS failed')):
            r = PingEngine.ping_http(
                {'host': 'example.com', 'scheme': 'https',
                 'port': None, 'path': '/', 'query': ''},
                1, 1, stop_event
            )
            assert r.status == 'DNS Error'


# ============================================================
# 21. ping_icmp - mocked
# ============================================================

class TestPingIcmpMocked:
    def test_dns_failure(self, stop_event):
        with patch.object(DNSResolver, 'resolve',
                          return_value=(None, None, None, 'DNS failed')):
            r = PingEngine.ping_icmp('example.com', 1, 1, stop_event)
            assert r.status == 'DNS Error'
            assert r.test_success is False

    def test_successful_ping_parses_times(self, stop_event):
        fake_output = (
            "Pinging example.com [1.2.3.4] with 32 bytes of data:\n"
            "Reply from 1.2.3.4: time=10ms TTL=56\n"
            "Reply from 1.2.3.4: time=12ms TTL=56\n"
            "Reply from 1.2.3.4: time=11ms TTL=56\n"
        )

        with patch.object(DNSResolver, 'resolve',
                          return_value=('1.2.3.4', 'IPv4', 1.0, None)):
            with patch('subprocess.Popen') as mock_popen:
                proc = MagicMock()
                proc.poll.return_value = 0
                proc.communicate.return_value = (fake_output, '')
                mock_popen.return_value = proc

                r = PingEngine.ping_icmp('example.com', 3, 1, stop_event)
                assert r.test_success is True
                assert r.reachable is True
                assert r.times == [10.0, 12.0, 11.0]
                assert r.avg == 11.0


# ============================================================
# 22. main() integration (no targets)
# ============================================================

class TestMain:
    def test_no_targets_returns_2(self, capsys):
        rc = main([])
        assert rc == 2
        captured = capsys.readouterr()
        assert 'no targets specified' in captured.out.lower() or \
               'no targets specified' in captured.err.lower()

    def test_no_color_flag(self):
        parser = build_parser()
        args = parser.parse_args(['--no-color', 'google.com'])
        assert args.no_color is True


# ============================================================
# 23. End-to-end integration
# ============================================================

class TestEndToEndLocal:
    def test_icmp_localhost(self, stop_event):
        r = PingEngine.ping_icmp('127.0.0.1', 2, 2, stop_event)
        if r.test_success:
            assert r.times
            assert r.avg is not None
            assert r.score is not None

    def test_parser_full_flow(self):
        targets = TargetParser.parse_sites('example.com,example.org,example.net')
        assert len(targets) == 3

        results = []
        for i, t in enumerate(targets):
            r = PingResult(target=t['host'], method='ICMP')
            r.test_success = True
            r.reachable = True
            r.times = [10.0 + i, 11.0 + i, 12.0 + i]
            r.attempts = 3
            r.successes = 3
            r.status = 'OK'
            PingEngine._finalize(r)
            results.append(r)

        ranked = PingRunner._rank(results)
        assert all(r.rank is not None for r in ranked)
        assert ranked[0].rank == 1


# ============================================================
# 24. Regression: full pipeline with failed TCP
# ============================================================

class TestRegressionFailedTcp:
    """
    Regression test for the bug where test_success=True but r.times=[],
    leading to a crash in print_summary.
    """

    def test_no_crash_when_avg_is_none(self, capsys):
        bad = PingResult(target='bad.com', method='TCP:443')
        bad.reachable = True
        bad.test_success = True
        bad.times = []
        bad.avg = None
        bad.score = None
        bad.status = 'OK'

        PingEngine._finalize(bad)
        assert bad.test_success is False
        assert bad.status == 'Failed'

        good = PingResult(target='good.com', method='TCP:443')
        good.test_success = True
        good.reachable = True
        good.times = [10.0]
        good.attempts = 1
        good.successes = 1
        good.status = 'OK'
        PingEngine._finalize(good)

        Renderer.print_summary([bad, good], 1.0)
        captured = capsys.readouterr()
        assert 'SUMMARY' in captured.out


# ============================================================
# 25. Concurrency
# ============================================================

class TestPingAllConcurrency:
    def test_ping_all_with_mocked_engine(self):
        parser = build_parser()
        args = parser.parse_args(['-c', '1', '-w', '3', 'a.com', 'b.com', 'c.com'])
        args = clamp_args(args)
        runner = PingRunner(args)

        def fake_ping(target, method, count, timeout, stop_event):
            r = PingResult(target=target['host'], method=method)
            r.test_success = True
            r.reachable = True
            r.times = [10.0]
            r.attempts = 1
            r.successes = 1
            r.status = 'OK'
            PingEngine._finalize(r)
            return r

        with patch.object(PingEngine, 'ping_host', side_effect=fake_ping):
            results = runner._ping_all([
                {'host': 'a.com'}, {'host': 'b.com'}, {'host': 'c.com'}
            ])

        assert len(results) == 3
        assert all(r.test_success for r in results)