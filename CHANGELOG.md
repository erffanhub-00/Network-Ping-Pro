# Changelog

## Unreleased

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
