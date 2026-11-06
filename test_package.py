#!/usr/bin/env python3
# ============================================================
# Tests for the package layout (1.1.0) and the documented
# behaviour of single-sample stats / jitter / refused TCP.
# Run with: pytest -v
# ============================================================

import re
import subprocess
import sys
from pathlib import Path

import pytest

import network_ping_pro as npp
from network_ping_pro import (
    Color,
    DNSResolver,
    PingEngine,
    PingResult,
    PingRunner,
    Renderer,
    StageStats,
    StatisticsEngine,
    TargetParser,
    build_parser,
    clamp_args,
    load_targets_from_file,
    main,
)

REPO_ROOT = Path(__file__).resolve().parent


# ============================================================
# 1. Package layout: every public name lives in its submodule
#    and is re-exported from the package root.
# ============================================================

class TestPackageLayout:
    @pytest.mark.parametrize("name", [
        "Color", "StageStats", "PingResult", "StatisticsEngine",
        "DNSResolver", "PingEngine", "TargetParser", "Renderer",
        "PingRunner", "build_parser", "clamp_args",
        "load_targets_from_file", "main",
    ])
    def test_name_reexported(self, name):
        assert hasattr(npp, name)

    def test_color_lives_in_color_module(self):
        from network_ping_pro.color import Color as Color2
        assert Color2 is Color

    def test_stats_lives_in_stats_module(self):
        from network_ping_pro.stats import StatisticsEngine as SE2
        assert SE2 is StatisticsEngine

    def test_engine_lives_in_engine_module(self):
        from network_ping_pro.engine import PingEngine as PE2
        assert PE2 is PingEngine

    def test_dns_lives_in_dns_module(self):
        from network_ping_pro.dns import DNSResolver as DR2
        assert DR2 is DNSResolver

    def test_targets_lives_in_targets_module(self):
        from network_ping_pro.targets import TargetParser as TP2
        assert TP2 is TargetParser

    def test_render_lives_in_render_module(self):
        from network_ping_pro.render import Renderer as R2
        assert R2 is Renderer

    def test_runner_lives_in_runner_module(self):
        from network_ping_pro.runner import PingRunner as PR2
        assert PR2 is PingRunner

    def test_cli_lives_in_cli_module(self):
        from network_ping_pro.cli import build_parser as bp2, main as main2
        assert bp2 is build_parser
        assert main2 is main

    def test_models_live_in_models_module(self):
        from network_ping_pro.models import PingResult as PR, StageStats as SS
        assert PR is PingResult
        assert SS is StageStats

    def test_version_is_single_source(self):
        from network_ping_pro.version import __version__
        assert npp.__version__ == __version__
        assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)

    def test_pyproject_version_matches_package(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        assert m, "pyproject.toml has no version"
        assert m.group(1) == npp.__version__


# ============================================================
# 2. Entry points: console script target, -m, and the shim file
# ============================================================

class TestEntryPoints:
    def test_module_run_help(self):
        proc = subprocess.run(
            [sys.executable, "-m", "network_ping_pro", "--help"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0
        assert "network-ping-pro" in proc.stdout.lower() or \
            "Network Ping Pro" in proc.stdout

    def test_module_run_version(self):
        proc = subprocess.run(
            [sys.executable, "-m", "network_ping_pro", "--version"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0
        assert npp.__version__ in proc.stdout

    def test_shim_file_still_runs(self):
        proc = subprocess.run(
            [sys.executable, "network_ping_pro.py", "--version"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0
        assert npp.__version__ in proc.stdout

    def test_cli_main_is_console_script_target(self):
        from network_ping_pro.cli import main as cli_main
        assert cli_main is main


# ============================================================
# 3. Documented behaviour: single-sample stage stats, jitter
# ============================================================

class TestDocumentedStatsBehaviour:
    def test_single_sample_stage_repeats_value(self):
        # Percentiles of a single value are that value; `samples`
        # tells the reader how many measurements back the numbers.
        st = StatisticsEngine.stage_stats([12.5])
        assert st.samples == 1
        assert st.avg == 12.5
        assert st.p50 == 12.5
        assert st.p95 == 12.5
        assert st.p99 == 12.5

    def test_jitter_is_mean_abs_successive_difference(self):
        # Documented definition (NOT RFC 3550 jitter).
        st = StatisticsEngine.basic_stats([10.0, 20.0, 10.0])
        assert st["jitter"] == 10.0

    def test_jitter_zero_for_constant_samples(self):
        st = StatisticsEngine.basic_stats([10.0, 10.0, 10.0])
        assert st["jitter"] == 0.0
