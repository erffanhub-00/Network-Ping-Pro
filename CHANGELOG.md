# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - Unreleased

### Changed
- The single 1600-line `network_ping_pro.py` is now a package:
  `network_ping_pro/` with modules for colours (`color.py`), data
  models (`models.py`), statistics and scoring (`stats.py`), DNS
  (`dns.py`), the measurement engines (`engine.py`), target parsing
  (`targets.py`), rendering (`render.py`), the runner (`runner.py`)
  and the CLI (`cli.py`). The public API is unchanged — every name
  is still importable as `from network_ping_pro import X`.
- `network_ping_pro.py` is now a thin shim, so
  `python network_ping_pro.py ...` keeps working. The recommended
  ways to run the tool are the installed `network-ping-pro` command
  and `python -m network_ping_pro`.
- README, USAGE and INSTALL were rewritten: every flag is documented
  with its real default and limits, the Score formula and grade
  thresholds are explained, exit codes and the CSV/JSON columns are
  listed, and the proxy/quiet-mode sections describe the actual
  behaviour. INSTALL is now a short guide instead of 450 lines for a
  standard-library-only tool.

### Fixed
- TCP "connection refused" now gets grade `Failed` instead of `Poor`,
  matching what `_finalize()` assigns to any result with no samples.
- Jitter is now documented where it is defined: it is the mean
  absolute difference between consecutive samples, not RFC 3550
  interarrival jitter. The same note is in USAGE.md.
- Single-sample stage stats (e.g. DNS, measured once) are now
  documented: p50/p95/p99 repeat that one sample, and the `samples`
  field says how many measurements back the numbers.

### Added
- `test_package.py`: tests for the package layout, the public API
  re-exports, the `python -m` / shim entry points, the version
  matching `pyproject.toml`, and the documented stats behaviour.
- Real-network tests are now marked with `@pytest.mark.network`;
  the unused `slow` marker was removed from `pytest.ini`.
- `pip install -e ".[dev]"` now installs the test dependency
  (pytest) as well.

## [1.0.0] - 2026-11-06

### Fixed
- Score weights now sum to 1.00 (latency 0.40, loss 0.35, jitter 0.25),
  so a perfect run scores 100 and "Excellent >= 90" is reachable.
- Proxy password is never logged: logs show only `scheme://host:port`.
  `--proxy-pass` can be replaced by the `NPP_PROXY_PASS` env var.
- ICMP parsing counts only reply lines (`time=..ms`); the ping summary
  line (`rtt min/avg/max/mdev = ...`) is no longer counted as replies,
  and results are capped at the requested count.
- HTTP follows redirects (`curl -L`) and reports the most common status
  code instead of the max; mixed statuses are shown as `Mixed: 200x3, 500x1`.
  A curl failure now keeps the last curl error message.
- Hosts starting with `-` are rejected, so a targets file cannot inject
  ping options; `--` is passed before the host. Ports must be 1-65535
  and bracketed IPv6 addresses are validated.
- Quiet mode (`-q`) prints no banner and sends logs to stderr, so stdout
  stays one line per target.
- `clamp_args` warns on stderr when a value is clamped
  (e.g. `count clamped 999 -> 200`).
- A failed CSV/JSON export now makes the exit code 1.
- DNS timeout no longer races: the resolver thread hands its result over
  once, under a lock (the thread itself may still outlive the call,
  because `getaddrinfo` cannot be interrupted).
- Removed the 16 MB `screenshots/demo.gif` (repo was ~30 MB).
- Clone URLs in README/INSTALL fixed to the real repo name
  (`Network-Ping-Pro`).

### Added
- `pyproject.toml` with a `network-ping-pro` console entry point.
- GitHub Actions CI (tests on Ubuntu, Windows and macOS).
- Tests for the score cap, ICMP summary parsing, HTTP mixed statuses,
  proxy-password masking, invalid targets, clamp warnings and export
  failures.
