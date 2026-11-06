# Network Ping Pro

A command-line network diagnostic tool for testing **ICMP, TCP and HTTP
connectivity and latency** from your own machine — no monitoring server,
no account, no external service.

> 📖 **Installation:** [INSTALL.md](INSTALL.md)
> 📚 **Full usage reference:** [USAGE.md](USAGE.md)
> 📝 **Changelog:** [CHANGELOG.md](CHANGELOG.md)

```bash
network-ping-pro google.com github.com
network-ping-pro -m TCP google.com:443
network-ping-pro -m HTTP https://example.com
```

---

## What it measures

For each target the tool reports:

| Metric | Meaning |
| ------ | ------- |
| Avg / Min / Max | Latency in milliseconds across the samples |
| Jitter | Mean absolute difference between consecutive samples (see note below) |
| P50 / P95 / P99 | Latency percentiles |
| Packet loss | Share of failed samples, in percent |
| Score (0–100) | Custom diagnostic score for comparing results *within this tool* |
| Grade | Excellent / Very Good / Good / Fair / Poor / Failed |
| Status | OK, Partial, High Loss, Refused, Timeout, DNS Error, … |

Three outcome flags are tracked independently: **reachable** (the host
answered at all), **test_success** (usable measurements were collected)
and **application_ok** (HTTP only: the status code was 2xx/3xx).

### Methods

| Method | How it works | Needs |
| ------ | ------------ | ----- |
| ICMP (default) | Runs the system `ping` command | `ping` |
| TCP | Opens a TCP connection to `host:port` (default 443) | — |
| HTTP | Runs `curl` and reads its timing variables | `curl` |

DNS resolution is measured **separately** from the connection: for TCP
the connection is made to the IP resolved in the DNS stage, so both
belong to the same attempt; for HTTP, curl resolves DNS internally.

### The Score, honestly

The Score is a **custom heuristic**, not an industry-standard benchmark.
It exists so you can rank targets against each other in one run.

```
Score = (latency × 0.40 + loss × 0.35 + jitter × 0.25)
        × p95 penalty × application penalty
```

- Latency, loss and jitter are each converted to a 0–100 sub-score
  (e.g. avg ≤ 10 ms → 100, 0% loss → 100, jitter ≤ 2 ms → 100).
- If p95 is more than 2× the average, the score is penalised
  (×0.85, or ×0.70 above 3×).
- For HTTP, a 4xx status penalises ×0.70 and a 5xx ×0.40.
- Grades: ≥ 90 Excellent, ≥ 80 Very Good, ≥ 70 Good, ≥ 60 Fair,
  otherwise Poor; a result with no measurements is Failed.

Jitter here is the **mean absolute difference between consecutive
samples** — a simple stability indicator, not the RFC 3550 interarrival
jitter. Stage stats with a single sample (DNS is measured once) repeat
that sample as avg/min/max/p50/p95/p99; the `samples` field in the
JSON/CSV output says how many measurements back the numbers.

---

## Installation

Requires **Python 3.9+**. HTTP testing additionally needs `curl`;
ICMP testing needs the system `ping` command.

```bash
git clone https://github.com/erffanhub-00/Network-Ping-Pro.git
cd Network-Ping-Pro

pip install .            # installs the `network-ping-pro` command
# or, for development:
pip install -e ".[dev]"  # editable install + pytest
```

No runtime Python dependencies — the tool uses only the standard
library. Full install instructions (including Python setup per OS)
are in [INSTALL.md](INSTALL.md).

Verify the install:

```bash
network-ping-pro --version
```

Without installing, run it from the repository directory:

```bash
python -m network_ping_pro google.com
# or
python network_ping_pro.py google.com
```

---

## Quick examples

```bash
# Basic ICMP test (10 pings per target by default)
network-ping-pro google.com github.com cloudflare.com

# TCP connect test on port 443
network-ping-pro -m TCP google.com:443 github.com:443

# HTTP test (follows redirects, reports the most common status)
network-ping-pro -m HTTP https://example.com https://www.wikipedia.org

# Targets from a file (one per line, '#' for comments)
network-ping-pro -f targets.txt

# More samples, longer timeout, export results
network-ping-pro -c 20 -t 5 -o results.csv --json results.json google.com

# Quiet mode: one line per target on stdout, logs on stderr
network-ping-pro -q google.com

# HTTP through a SOCKS5 proxy (HTTP method only)
network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 https://example.com
```

All options are documented in [USAGE.md](USAGE.md).

---

## Output and exit codes

By default the tool prints a results table, a latency chart and a
summary. `-q` prints one line per target (`OK` / `FAIL`) and is meant
for scripts. CSV (`-o`) and JSON (`--json`) exports carry the same
results, including per-stage timings and the HTTP status distribution.

| Exit code | Meaning |
| --------- | ------- |
| 0 | All targets tested successfully |
| 1 | At least one target failed, or a CSV/JSON export failed |
| 2 | Usage error (no targets, invalid proxy, unreadable targets file) |
| 130 | Interrupted with Ctrl+C |

---

## Proxy

Proxy applies to the **HTTP method only** (ICMP cannot go through a
proxy; TCP does not route through one).

```bash
network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 \
    --proxy-user USER https://example.com
```

- The password is never printed in logs or terminal output; logs show
  only `scheme://host:port`.
- Prefer the environment variable over the flag — a password on the
  command line is visible to other users via `ps` and shell history:

```bash
export NPP_PROXY_PASS='secret'
network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 https://example.com
```

---

## Project structure

```text
Network-Ping-Pro/
├── network_ping_pro/          # the package
│   ├── __init__.py            # public API re-exports
│   ├── __main__.py            # `python -m network_ping_pro`
│   ├── cli.py                 # argument parsing, main()
│   ├── color.py               # terminal colours
│   ├── dns.py                 # DNS resolver with timeout
│   ├── engine.py              # ICMP / TCP / HTTP measurement
│   ├── models.py              # PingResult, StageStats
│   ├── render.py              # table, chart, summary output
│   ├── runner.py              # concurrency, ranking, CSV/JSON export
│   ├── stats.py               # percentiles, jitter, Score
│   ├── targets.py             # target parsing and validation
│   └── version.py             # single source of truth for the version
├── network_ping_pro.py        # thin shim: `python network_ping_pro.py ...`
├── test_network_ping_pro.py   # unit + integration tests
├── test_package.py            # package layout and entry-point tests
├── pyproject.toml             # install metadata, `network-ping-pro` script
├── targets.example.txt        # example targets file
├── README.md
├── INSTALL.md
├── USAGE.md
├── CHANGELOG.md
└── LICENSE
```

Run the tests:

```bash
pip install -e ".[dev]"
python -m pytest -q
```

---

## فارسی | Persian

**Network Ping Pro** ابزار خط فرمان برای تست شبکه با Python است؛
روی کامپیوتر خودت اجرا می‌شود و به سرویس مانیتورینگ خارجی نیاز ندارد.

```bash
pip install .
network-ping-pro google.com
```

سه روش تست دارد: **ICMP** (پینگ معمولی)، **TCP** (اتصال به پورت،
مثل ۴۴۳) و **HTTP** (با curl، با دنبال‌کردن ریدایرکت). برای هر مقصد
میانگین/حداقل/حداکثر latency، جیتر، P95/P99، درصد Packet Loss و یک
Score صفر تا صد گزارش می‌شود. Score یک معیار سفارشی برای مقایسه
نتیجه‌ها داخل همین ابزار است، نه یک بنچمارک استاندارد. خروجی CSV و
JSON، حالت quiet برای اسکریپت، و پروکسی برای HTTP هم پشتیبانی می‌شود.
راهنمای کامل نصب در [INSTALL.md](INSTALL.md) و راهنمای استفاده در
[USAGE.md](USAGE.md) است.

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE).

---

## Me

[![Telegram](https://img.shields.io/badge/Telegram-erffan__hub-blue?style=for-the-badge\&logo=telegram)](https://t.me/erffan_hub)
[![Twitter](https://img.shields.io/badge/Twitter-@Erffanhub__00-000000?style=for-the-badge\&logo=x\&logoColor=white)](https://x.com/Erffanhub_00)
[![Gist](https://img.shields.io/badge/Gist-Profile-000000?style=for-the-badge\&logo=github)](https://gist.github.com/erffanhub-00)
[![Github](https://img.shields.io/badge/Github-Profile-000000?style=for-the-badge\&logo=github)](https://github.com/erffanhub-00)
