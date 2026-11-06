# Network Ping Pro — Usage Guide

Complete reference for the `network-ping-pro` command. For installation
see [INSTALL.md](INSTALL.md); for a short overview see [README.md](README.md).

## Contents

1. [Basic usage](#1-basic-usage)
2. [Targets](#2-targets)
3. [Methods: ICMP, TCP, HTTP](#3-methods-icmp-tcp-http)
4. [Options reference](#4-options-reference)
5. [Metrics explained](#5-metrics-explained)
6. [Score and grade](#6-score-and-grade)
7. [Reading the output](#7-reading-the-output)
8. [CSV and JSON export](#8-csv-and-json-export)
9. [Quiet mode and scripting](#9-quiet-mode-and-scripting)
10. [Proxy](#10-proxy)
11. [Exit codes](#11-exit-codes)
12. [Practical examples](#12-practical-examples)
13. [Recommended diagnostic workflow](#13-recommended-diagnostic-workflow)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Basic usage

```bash
network-ping-pro <target> [target ...] [options]
```

A target is a hostname, `host:port`, a URL, or `[IPv6]:port`.
If you run from the repository without installing, use
`python -m network_ping_pro` (or `python network_ping_pro.py`)
in place of `network-ping-pro`.

```bash
network-ping-pro google.com
network-ping-pro google.com github.com cloudflare.com
network-ping-pro -m TCP google.com:443
network-ping-pro -m HTTP https://example.com
```

With no targets the tool prints help and exits with code 2.

---

## 2. Targets

| Form | Example | Used for |
| ---- | ------- | -------- |
| Hostname | `google.com` | ICMP, TCP (port 443), HTTP (https) |
| Host + port | `google.com:443`, `1.1.1.1:53` | TCP, or HTTP on that port |
| URL | `https://example.com/api?q=1` | HTTP (scheme, path and query kept) |
| IPv6 | `[2606:4700:4700::1111]:443` | TCP / HTTP |

Targets can also come from a file:

```bash
network-ping-pro -f targets.txt
```

`targets.txt` — one target per line, `#` for comments, commas and
Persian commas (،) also work as separators:

```text
# my targets
google.com
github.com
1.1.1.1:443
https://example.com
```

Rules:

- Duplicate targets are tested once.
- Invalid targets (e.g. `-n`, `host:0`, `host:65536`, `[:::]`) are
  skipped and reported as `Skipped invalid target: ...`.
- A host starting with `-` is always rejected, so a targets file can
  never inject options into the `ping` command.

---

## 3. Methods: ICMP, TCP, HTTP

### ICMP (default)

```bash
network-ping-pro google.com
```

Runs the system `ping` command and parses only the reply lines
(`time=..ms`). The summary line (`rtt min/avg/max/mdev = ...`) is
statistics, not replies, and is never counted as a ping. Results are
capped at the requested count.

### TCP

```bash
network-ping-pro -m TCP google.com:443
network-ping-pro -m TCP 1.1.1.1:53 8.8.8.8:53
```

Opens a TCP connection to each target and measures connect time.
Useful for checking whether a service port is open, e.g. 443 (HTTPS),
80 (HTTP), 22 (SSH), 53 (DNS). The default port is 443.

A refused connection means the host is reachable but the port is
closed: the result is `reachable = true`, `test_success = false`,
status `Refused`, grade `Failed`.

### HTTP

```bash
network-ping-pro -m HTTP https://example.com
```

Runs `curl` (must be installed) and measures total time, connect time
and time-to-first-byte. Redirects are followed (`curl -L`), and the
reported status is the **most common** status code across the samples,
not the highest — a mix of 200 and 500 is reported as
`Mixed: 200x3, 500x1` with the full distribution in the export.

`application_ok` is true when the reported status is 2xx or 3xx.
A curl failure keeps the last curl error message
(e.g. `No HTTP response (curl: (6) Could not resolve host: ...)`).

DNS for HTTP is resolved by curl itself, so the separately measured
DNS stage and the HTTP timings are not part of the same connection.

---

## 4. Options reference

| Option | Default | Limits | Meaning |
| ------ | ------- | ------ | ------- |
| `targets` | — | — | Hosts, `host:port`, URLs, `[IPv6]:port` |
| `-f`, `--file FILE` | — | — | Read targets from a file |
| `-m`, `--method` | `ICMP` | `ICMP` / `TCP` / `HTTP` | Test method |
| `-c`, `--count N` | `10` | 1–200 | Pings per target |
| `-t`, `--timeout SEC` | `3.0` | 1–30 | Timeout per ping, seconds |
| `-w`, `--workers N` | `10` | 1–50 | Concurrent workers |
| `--proxy URL` | — | http/https/socks4/socks5 | Proxy for HTTP only |
| `--proxy-user USER` | — | — | Proxy username |
| `--proxy-pass PASS` | `$NPP_PROXY_PASS` | — | Proxy password (prefer the env var) |
| `-o`, `--output-csv FILE` | — | — | Export results to CSV |
| `--json FILE` | — | — | Export results to JSON |
| `--no-progress` | off | — | Disable the live progress line |
| `-q`, `--quiet` | off | — | One line per target; logs go to stderr |
| `--no-color` | off | — | Disable coloured output |
| `-v`, `--version` | — | — | Print version and exit |
| `-h`, `--help` | — | — | Print help and exit |

Values outside the limits are **clamped with a warning on stderr**,
e.g. `Warning: count clamped 999 -> 200` — never silently.

---

## 5. Metrics explained

All times are in milliseconds.

| Metric | Meaning |
| ------ | ------- |
| Avg | Mean of the samples |
| Min / Max | Fastest / slowest sample |
| Jitter | **Mean absolute difference between consecutive samples.** A simple stability indicator — not the RFC 3550 interarrival jitter |
| P50 / P95 / P99 | Percentiles (linear interpolation between samples) |
| Packet loss | `(attempts − successes) / attempts × 100` |
| DNS avg | Time of the separate DNS resolution stage |
| Connect avg | TCP connect time, or curl `time_connect` for HTTP |
| TTFB avg | Time to first byte (HTTP only) |
| Total avg | Total request time (HTTP only) |

**Single-sample stages.** DNS is measured once, so its stage stats
repeat that one sample as avg/min/max/p50/p95/p99. Percentiles of a
single value carry no extra information — check the `samples` field
in the JSON/CSV output to see how many measurements back the numbers.

**What counts as a failure.** Each sample either produces a time or
it does not. `attempts` is the requested count; `successes` is the
number of samples with a time. Packet loss is computed from those two
numbers, not from the ping program's own summary.

---

## 6. Score and grade

The Score is a **custom heuristic** for comparing results within this
tool. It is **not** an industry-standard benchmark.

```
Score = (latency × 0.40 + loss × 0.35 + jitter × 0.25)
        × p95 penalty × application penalty
```

Sub-scores (each 0–100):

Latency sub-score:

| avg (ms) | ≤ 10 | ≤ 25 | ≤ 50 | ≤ 100 | ≤ 200 | ≤ 500 | > 500 |
| -------- | ---- | ---- | ---- | ----- | ----- | ----- | ----- |
| score | 100 | 90 | 80 | 65 | 45 | 25 | 10 |

Loss sub-score:

| loss (%) | 0 | ≤ 1 | ≤ 5 | ≤ 10 | ≤ 20 | > 20 |
| -------- | - | --- | --- | ---- | ---- | ---- |
| score | 100 | 95 | 75 | 50 | 25 | 5 |

Jitter sub-score:

| jitter (ms) | ≤ 2 | ≤ 5 | ≤ 10 | ≤ 20 | > 20 |
| ----------- | --- | --- | ---- | ---- | ---- |
| score | 100 | 85 | 65 | 40 | 15 |

Penalties:

- **p95 penalty:** p95 more than 2× the average → ×0.85; more than
  3× → ×0.70.
- **Application penalty (HTTP only):** 4xx status → ×0.70;
  5xx status → ×0.40. It applies only when `application_ok` is false.
- A result with no successful samples scores **0.0**.

Grades:

| Score | Grade |
| ----- | ----- |
| ≥ 90 | Excellent |
| ≥ 80 | Very Good |
| ≥ 70 | Good |
| ≥ 60 | Fair |
| < 60 | Poor |
| no measurements | Failed |

---

## 7. Reading the output

Default output is a results table, a latency chart and a summary:

```text
  #  Target        Method     Score  Grade       Avg ms  Loss  Status
  1  google.com    ICMP        96.5  Excellent     12.3    0%  OK
  2  github.com    ICMP        88.0  Very Good     24.1    0%  OK
```

- **Rank** is by Score (higher = better). Failed results are listed
  after the successful ones, unranked.
- The summary lists total/reachable/successful/failed counts, the
  lowest and highest latency, the highest score, mixed HTTP statuses
  and the first failures with their errors.
- The footer repeats the two honesty notes: the Score is a custom
  heuristic, and DNS is measured separately from the connection.

Status values you may see: `OK`, `Partial` (< 20% loss),
`High Loss` (≥ 20% loss), `Refused` (TCP port closed, host reachable),
`Timeout`, `DNS Error`, `Unreachable`, `No Response`, `Cancelled`,
`Error`, `Failed`, and HTTP statuses such as `HTTP 404 Not Found`
or `Mixed: 200x3, 500x1`.

---

## 8. CSV and JSON export

```bash
network-ping-pro -o results.csv --json results.json google.com
```

### CSV columns

```text
Rank, Target, Method, Reachable, TestSuccess, ApplicationOK,
Score, Grade, Avg, Min, Max, Jitter, P50, P95, P99, Loss %,
Status, Error, Resolved IP, Family,
DNS avg, Connect avg, TTFB avg, Total avg,
HTTP status, HTTP distribution
```

`HTTP distribution` is a `code:count;code:count` list, e.g. `200:3;500:1`.

### JSON structure

```json
{
  "tool": "Network Ping Pro",
  "version": "1.1.0",
  "timestamp": "2026-11-06T18:00:00",
  "method": "ICMP",
  "count": 10,
  "timeout": 3.0,
  "total": 2,
  "results": [
    {
      "target": "google.com",
      "method": "ICMP",
      "reachable": true,
      "test_success": true,
      "application_ok": null,
      "times": [12.1, 11.8],
      "attempts": 10,
      "successes": 10,
      "avg": 12.0, "min": 11.8, "max": 12.1,
      "jitter": 0.3, "p50": 12.0, "p95": 12.1, "p99": 12.1,
      "packet_loss": 0.0,
      "status": "OK",
      "error": null,
      "resolved_ip": "142.250.72.14",
      "ip_family": "IPv4",
      "rank": 1,
      "score": 96.5,
      "grade": "Excellent",
      "dns": {"avg": 8.2, "min": 8.2, "max": 8.2,
              "p50": 8.2, "p95": 8.2, "p99": 8.2, "samples": 1},
      "connect": {"avg": null, "samples": 0},
      "ttfb": {"avg": null, "samples": 0},
      "total": {"avg": null, "samples": 0},
      "http_status": null,
      "http_status_text": null,
      "http_status_distribution": null,
      "port": null
    }
  ]
}
```

A failed export is not silent: the command exits with code 1.

---

## 9. Quiet mode and scripting

```bash
network-ping-pro -q google.com github.com
```

Quiet mode prints **no banner** and sends all logs to **stderr**, so
stdout stays one line per target and is safe to parse:

```text
OK    google.com                               score= 96.5 avg=   12.3ms loss=   0% OK
FAIL  bad.example                              DNS Error  DNS: Name or service not known
```

Useful patterns:

```bash
# Fail a CI step if any target fails (exit code 1)
network-ping-pro -q google.com || echo "network problem"

# Only the failures
network-ping-pro -q google.com bad.example | grep '^FAIL'

# Machine-readable results for a script
network-ping-pro -q -o /tmp/out.csv google.com
```

---

## 10. Proxy

Proxy applies to the **HTTP method only**. ICMP cannot traverse a
proxy; TCP does not route through one.

```bash
# SOCKS5 proxy (e.g. v2ray / Hiddify)
network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 https://example.com

# With a username (password via env var, see below)
network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 \
    --proxy-user USER https://example.com

# HTTP proxy
network-ping-pro -m HTTP --proxy http://127.0.0.1:8080 https://example.com
```

**Password safety.** The password is never printed in logs or
terminal output — logs show only `scheme://host:port`. Prefer the
environment variable over `--proxy-pass`: a password on the command
line is visible to other users via `ps` and shell history.

```bash
export NPP_PROXY_PASS='secret'
network-ping-pro -m HTTP --proxy socks5://127.0.0.1:10808 https://example.com
```

A password can also be embedded in the proxy URL
(`socks5://user:pass@host:port`); it is URL-encoded before being
passed to curl and is never logged.

---

## 11. Exit codes

| Code | Meaning |
| ---- | ------- |
| 0 | All targets tested successfully |
| 1 | At least one target failed, or a CSV/JSON export failed |
| 2 | Usage error: no targets, invalid proxy, unreadable targets file |
| 130 | Interrupted with Ctrl+C |

---

## 12. Practical examples

```bash
# Check Google
network-ping-pro google.com

# Check several services at once
network-ping-pro google.com github.com cloudflare.com

# Check HTTPS with TCP (is port 443 open?)
network-ping-pro -m TCP google.com:443 github.com:443

# Check HTTP response time and status
network-ping-pro -m HTTP https://example.com https://www.wikipedia.org

# Test many targets from a file
network-ping-pro -f targets.txt

# Run more samples for a stable average
network-ping-pro -c 50 google.com

# Increase timeout for slow networks
network-ping-pro -t 10 google.com

# Test multiple targets concurrently (default: 10 workers)
network-ping-pro -w 20 google.com github.com cloudflare.com

# Disable terminal colours (e.g. for a log file)
network-ping-pro --no-color google.com

# Full run: 20 samples, exports, quiet
network-ping-pro -q -c 20 -o results.csv --json results.json google.com
```

---

## 13. Recommended diagnostic workflow

1. **ICMP first** — is the host reachable at all, and what is the
   baseline latency and loss?
   ```bash
   network-ping-pro google.com
   ```
2. **TCP next** — is the service port open?
   ```bash
   network-ping-pro -m TCP google.com:443
   ```
   A `Refused` here with ICMP working means the host is up but the
   service is down or firewalled.
3. **HTTP last** — does the application answer, and with what status?
   ```bash
   network-ping-pro -m HTTP https://google.com
   ```
   A 200 with high latency is a network problem; a 5xx with low
   latency is an application problem.
4. **Compare targets** — run several at once and read the ranking:
   ```bash
   network-ping-pro google.com github.com cloudflare.com
   ```

---

## 14. Troubleshooting

**`curl not installed (required for HTTP)`**
Install curl: Windows 10+ has it preinstalled; on Debian/Ubuntu
`sudo apt install curl`; on macOS it is preinstalled.

**ICMP fails with "Operation not permitted" (Linux)**
The tool runs the system `ping` command; in restricted containers
raw sockets may be blocked. TCP mode works without that permission:
`network-ping-pro -m TCP google.com:443`.

**`DNS Error` for every target**
Check your DNS settings. The tool resolves names with the system
resolver; a VPN or proxy that only handles browser traffic will not
help the CLI.

**`No targets specified` / exit code 2**
You passed no targets, or every line of your targets file was a
comment/blank. Invalid entries are reported as
`Skipped invalid target: ...` on stderr.

**Colours look broken / escape codes in a log file**
Use `--no-color`, or `-q` for script output.

**A value was clamped**
`count` is limited to 1–200, `timeout` to 1–30 s and `workers` to
1–50. Out-of-range values are clamped with a warning on stderr,
e.g. `Warning: count clamped 999 -> 200`.

**A run is slow**
Each target takes up to `count × timeout` seconds in the worst case;
targets run concurrently (`-w`, default 10). Lower `-c` or `-t`
for a quick check.
