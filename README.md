# Network Ping Pro

A practical CLI network diagnostic tool for testing **latency, packet loss, jitter, DNS resolution, TCP connectivity, and HTTP performance**.

Network Ping Pro is designed to run real network tests directly from your local machine using **ICMP, TCP, and HTTP**.

> **Version:** 1.0.0
> **Author:** Erffan
> **License:** MIT

---

## 🌐 Website

🔗 **Project Website:**
https://website-erffan.erffanhub.workers.dev/

---

## ✨ Features

* ICMP ping testing
* TCP connection testing
* HTTP/HTTPS performance testing
* IPv4 and IPv6 support
* DNS resolution timing
* Connection timing
* HTTP TTFB measurement
* Total HTTP request timing
* Average / minimum / maximum latency
* Jitter calculation
* P50 / P95 / P99 percentiles
* Packet loss calculation
* Custom diagnostic score
* Automatic grade
* HTTP status code detection
* HTTP status distribution
* Multiple concurrent workers
* Configurable timeout and request count
* HTTP/SOCKS4/SOCKS5 proxy support
* CSV export
* JSON export
* Quiet / script-friendly mode
* Colored terminal output
* Progress display
* Target file support
* Graceful cancellation with `Ctrl+C`

---

## 📊 What It Measures

### ICMP

Measures traditional network ping latency and packet loss.

```text
DNS → ICMP Ping → Statistics
```

### TCP

Measures the time required to establish a TCP connection to a specific port.

```text
DNS → TCP Connect → Statistics
```

The TCP test connects directly to the IP address resolved during the DNS stage.

### HTTP

Measures real HTTP/HTTPS requests using `curl`.

```text
DNS → HTTP Request
          ├── Connect
          ├── TTFB
          └── Total
```

For HTTP, DNS is measured separately because `curl` performs its own DNS resolution internally.

---

## 📈 Statistics

Network Ping Pro calculates:

| Metric | Description                                    |
| ------ | ---------------------------------------------- |
| Avg    | Average latency                                |
| Min    | Minimum latency                                |
| Max    | Maximum latency                                |
| Jitter | Average difference between consecutive samples |
| P50    | 50th percentile                                |
| P95    | 95th percentile                                |
| P99    | 99th percentile                                |
| Loss   | Percentage of failed attempts                  |

For HTTP requests, additional stage measurements are available:

* DNS
* TCP/TLS connection time reported by curl
* TTFB
* Total request time

---

## 🎯 Score

The tool includes a **custom diagnostic score from 0 to 100**.

The score considers:

* Latency
* Packet loss
* Jitter
* P95 tail latency
* HTTP application status

The score is a **heuristic created specifically for this tool**.

It is **not an industry-standard network benchmark** and should not be compared directly with scores from other applications.

---

## 🏆 Ranking

Results are ranked by the custom diagnostic score.

```text
Rank is by custom diagnostic Score
```

Ranking does **not** represent an official network-quality standard.

---

## 🚀 Installation

### Requirements

* Python 3.9+
* `curl` for HTTP testing
* Operating system with `ping` for ICMP testing

The Python project uses only the Python standard library.

### Clone

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

### Run

```bash
python network_ping_pro.py google.com
```

---

## 📦 Dependencies

Python dependencies:

```text
None
```

All Python modules used by the project are included in the Python standard library.

For HTTP testing, install **curl** separately.

Check curl:

```bash
curl --version
```

If curl is unavailable, ICMP and TCP modes can still be used.

---

## 🖥️ Basic Usage

### ICMP

```bash
python network_ping_pro.py google.com
```

Multiple targets:

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

---

### TCP

Test TCP port 443:

```bash
python network_ping_pro.py -m TCP google.com:443
```

Multiple targets:

```bash
python network_ping_pro.py -m TCP google.com:443 github.com:443
```

You can also use a target without a port:

```bash
python network_ping_pro.py -m TCP google.com
```

The default TCP port is `443`.

---

### HTTP / HTTPS

```bash
python network_ping_pro.py -m HTTP https://google.com
```

Custom path:

```bash
python network_ping_pro.py -m HTTP https://example.com/api
```

Query parameters:

```bash
python network_ping_pro.py -m HTTP "https://example.com/search?q=test"
```

HTTP defaults to HTTPS when no scheme is specified.

```bash
python network_ping_pro.py -m HTTP google.com
```

---

## ⚙️ Options

```text
-m, --method
```

Testing method:

```text
ICMP
TCP
HTTP
```

Default:

```text
ICMP
```

---

```text
-c, --count
```

Number of tests per target.

Default:

```text
10
```

Example:

```bash
python network_ping_pro.py -c 20 google.com
```

Allowed range:

```text
1 - 200
```

---

```text
-t, --timeout
```

Timeout per test in seconds.

Default:

```text
3.0
```

Example:

```bash
python network_ping_pro.py -t 5 google.com
```

Allowed range:

```text
1 - 30 seconds
```

---

```text
-w, --workers
```

Number of concurrent workers.

Default:

```text
10
```

Example:

```bash
python network_ping_pro.py -w 20 google.com github.com
```

Allowed range:

```text
1 - 50
```

---

## 🌐 Proxy

Proxy support is available for **HTTP testing only**.

Supported proxy types:

* HTTP
* HTTPS
* SOCKS4
* SOCKS5

### SOCKS5

```bash
python network_ping_pro.py \
  -m HTTP \
  --proxy socks5://127.0.0.1:10808 \
  https://google.com
```

### HTTP Proxy

```bash
python network_ping_pro.py \
  -m HTTP \
  --proxy http://127.0.0.1:8080 \
  https://example.com
```

### Proxy Authentication

```bash
python network_ping_pro.py \
  -m HTTP \
  --proxy socks5://127.0.0.1:10808 \
  --proxy-user username \
  --proxy-pass password \
  https://example.com
```

> Proxy configuration does not affect ICMP or TCP tests.

---

## 📄 Target File

Targets can be loaded from a file.

Example `targets.txt`:

```text
google.com
github.com
cloudflare.com
https://example.com
```

Run:

```bash
python network_ping_pro.py -f targets.txt
```

Comments are supported:

```text
# Main websites
google.com
github.com

# Cloudflare
cloudflare.com
```

---

## 📤 Export

### CSV

```bash
python network_ping_pro.py \
  -o results.csv \
  google.com github.com
```

### JSON

```bash
python network_ping_pro.py \
  --json results.json \
  google.com github.com
```

### Both

```bash
python network_ping_pro.py \
  -o results.csv \
  --json results.json \
  google.com github.com
```

The JSON export contains detailed result objects including:

* DNS statistics
* Connection statistics
* TTFB
* Total HTTP timing
* HTTP status distribution
* latency statistics
* packet loss
* score
* grade
* resolved IP
* IP family
* errors

---

## 🤫 Quiet Mode

Quiet mode produces one line per target and is useful for scripts.

```bash
python network_ping_pro.py -q google.com github.com
```

Example:

```text
OK    google.com                               score= 92.4 avg=  18.2ms loss=   0% OK
OK    github.com                               score= 87.1 avg=  31.5ms loss=   0% OK
```

Failed targets:

```text
FAIL  example.com                              Timeout  Connection timeout
```

---

## 🎨 Disable Colors

```bash
python network_ping_pro.py --no-color google.com
```

Useful when redirecting output to files or processing output from scripts.

---

## ⏱️ Example

```bash
python network_ping_pro.py \
  -m ICMP \
  -c 20 \
  -t 3 \
  -w 10 \
  google.com github.com cloudflare.com
```

TCP:

```bash
python network_ping_pro.py \
  -m TCP \
  -c 10 \
  -t 3 \
  google.com:443 github.com:443
```

HTTP:

```bash
python network_ping_pro.py \
  -m HTTP \
  -c 10 \
  -t 5 \
  https://google.com \
  https://github.com
```

---

## 🔬 HTTP Status Handling

HTTP connectivity and application status are treated separately.

For example:

```text
HTTP 200 → Network reachable + application OK
HTTP 404 → Network reachable + application response, but application status is not OK
HTTP 500 → Network reachable + server-side HTTP error
```

This prevents an HTTP `404` or `500` from being incorrectly interpreted as a network connectivity failure.

The tool also records the distribution of HTTP status codes when multiple requests return different statuses.

Example:

```text
200×8, 500×2
```

---

## 🌍 IPv4 / IPv6

The DNS resolver detects both:

```text
IPv4
IPv6
```

TCP connections use the IP address selected during the DNS stage.

IPv6 targets can be written using brackets:

```bash
python network_ping_pro.py -m TCP "[2001:db8::1]:443"
```

---

## 🧠 Architecture

The project is intentionally divided into separate components:

```text
Network Ping Pro
│
├── Color
│   └── Terminal colors / Windows ANSI
│
├── StageStats
│   └── Stage measurements
│
├── PingResult
│   └── Test result model
│
├── StatisticsEngine
│   ├── Average
│   ├── Min / Max
│   ├── Jitter
│   ├── P50
│   ├── P95
│   ├── P99
│   └── Custom Score
│
├── DNSResolver
│   └── DNS resolution
│
├── PingEngine
│   ├── ICMP
│   ├── TCP
│   └── HTTP
│
├── TargetParser
│   └── Host / URL / IPv6 parsing
│
├── Renderer
│   └── CLI output
│
├── PingRunner
│   ├── Concurrency
│   ├── Ranking
│   └── Export
│
└── CLI
    └── Argument parsing
```

---

## ⚠️ Measurement Notes

### DNS

DNS resolution is measured separately.

The resolver uses Python's:

```python
socket.getaddrinfo()
```

The timeout is a caller-side timeout guard. The underlying operating-system resolver may continue running in the background if it does not return within the configured timeout.

### HTTP

HTTP uses `curl`.

The DNS measurement is separate from the actual curl connection because curl performs its own DNS resolution.

Therefore:

```text
DNS timing ≠ necessarily curl's DNS timing
```

### TCP

TCP connects directly to the IP selected during the DNS stage.

Therefore the measured flow is:

```text
DNS → resolved IP → TCP connection
```

### ICMP

ICMP relies on the operating system's `ping` command.

Its output parsing can vary between operating systems and localized environments.

---

## 🛑 Cancellation

Press:

```text
Ctrl+C
```

to request cancellation.

Running subprocesses are terminated where possible and the program exits gracefully.

---

## 🔧 Supported Targets

Examples:

```text
google.com
google.com:443
https://google.com
https://example.com/api
https://example.com/search?q=test
[::1]
[::1]:443
```

---

## 📋 Exit Codes

|  Code | Meaning                                     |
| ----: | ------------------------------------------- |
|   `0` | All tests successful                        |
|   `1` | One or more tests failed                    |
|   `2` | Invalid arguments / configuration / targets |
| `130` | Interrupted by user                         |

---

## 📜 License

This project is licensed under the **MIT License**.

See [LICENSE](LICENSE) for details.

---

## 👤 Me

[![Telegram](https://img.shields.io/badge/Telegram-erffan__hub-blue?style=for-the-badge\&logo=telegram)](https://t.me/erffan_hub)
[![Twitter](https://img.shields.io/badge/Twitter-@Erffanhub__00-000000?style=for-the-badge\&logo=x\&logoColor=white)](https://x.com/Erffanhub_00)
[![Gist](https://img.shields.io/badge/Gist-Profile-000000?style=for-the-badge\&logo=github)](https://gist.github.com/erffanhub-00)
[![Github](https://img.shields.io/badge/Github-Profile-000000?style=for-the-badge\&logo=github)](https://github.com/erffanhub-00)

---

**Network Ping Pro** — A simple, practical CLI tool for real network diagnostics.
