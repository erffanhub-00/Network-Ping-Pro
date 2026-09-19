# Network Ping Pro — Usage Guide

This document explains how to use **Network Ping Pro**, including test methods, targets, files, options, metrics, exports, and practical examples.

---

# 1. Basic Usage

The simplest command is:

```bash
python network_ping_pro.py google.com
```

Linux/macOS:

```bash
python3 network_ping_pro.py google.com
```

The program tests the target and reports the network results.

---

# 2. Multiple Targets

You can test several targets in one command:

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

This is useful when comparing different services or networks.

Example targets:

```text
google.com
github.com
cloudflare.com
githubusercontent.com
1.1.1.1
8.8.8.8
```

---

# 3. ICMP Testing

ICMP is the traditional ping method.

```bash
python network_ping_pro.py google.com
```

You can also explicitly select ICMP if your version supports the method option:

```bash
python network_ping_pro.py -m ICMP google.com
```

ICMP testing is useful for measuring:

* Latency
* Packet loss
* Network stability
* Basic reachability

---

# 4. TCP Testing

TCP testing checks whether a TCP connection can be established to a specific host and port.

Example:

```bash
python network_ping_pro.py -m TCP google.com:443
```

Common ports:

| Port | Typical Service |
| ---: | --------------- |
|   80 | HTTP            |
|  443 | HTTPS           |
|   22 | SSH             |
|   25 | SMTP            |
|   53 | DNS             |

Examples:

```bash
python network_ping_pro.py -m TCP google.com:443
```

```bash
python network_ping_pro.py -m TCP github.com:443
```

```bash
python network_ping_pro.py -m TCP example.com:80
```

TCP testing is useful when ICMP is blocked but the actual service is reachable.

---

# 5. HTTP Testing

HTTP testing measures the response of a web URL.

Example:

```bash
python network_ping_pro.py -m HTTP https://google.com
```

Another example:

```bash
python network_ping_pro.py -m HTTP https://github.com
```

HTTP testing is useful for measuring the actual response of a web service rather than simply testing ICMP connectivity.

### Requirement

HTTP testing requires:

```text
curl
```

Check:

```bash
curl --version
```

---

# 6. Test Targets from a File

Create:

```text
targets.txt
```

Example:

```text
google.com
github.com
cloudflare.com
1.1.1.1
8.8.8.8
```

Run:

```bash
python network_ping_pro.py -f targets.txt
```

This is useful when you have many targets.

---

# 7. Test Count

If your installed version exposes a count option, use it to control how many tests are performed for each target.

Example:

```bash
python network_ping_pro.py google.com --count 20
```

A larger number of tests provides more samples for latency and jitter calculations.

---

# 8. Timeout

A timeout determines how long the program waits for a response.

Example:

```bash
python network_ping_pro.py google.com --timeout 5
```

A shorter timeout is useful for quick diagnostics.

A longer timeout can help when testing slow or unstable connections.

---

# 9. Concurrent Testing

Network Ping Pro can perform tests concurrently when supported by the installed version.

This is useful when testing many targets.

Example:

```bash
python network_ping_pro.py google.com github.com cloudflare.com --workers 5
```

The number of workers controls how many tests can run at the same time.

---

# 10. Metrics

Network Ping Pro can calculate several network metrics.

## Average

Average latency across successful tests.

Example:

```text
Average: 24.5 ms
```

Lower latency generally means a faster response time.

---

## Minimum

The fastest successful response.

```text
Min: 19.2 ms
```

---

## Maximum

The slowest successful response.

```text
Max: 41.8 ms
```

---

## Jitter

Jitter describes variation in latency.

For example:

```text
20 ms
21 ms
20 ms
22 ms
21 ms
```

has relatively stable latency.

A result such as:

```text
15 ms
80 ms
20 ms
150 ms
18 ms
```

has much higher variation.

Jitter can be important for:

* Voice calls
* Video calls
* Online games
* Real-time applications

---

# 11. Packet Loss

Packet loss shows how many tests failed to receive a response.

Example:

```text
Sent: 20
Received: 19
Loss: 5%
```

A high packet-loss percentage can indicate an unstable connection, filtering, congestion, or other network conditions.

---

# 12. P95 Latency

P95 means the 95th percentile latency.

It answers a practical question:

> What latency were 95% of successful measurements at or below?

Example:

```text
Average: 25 ms
P95:     41 ms
```

This can reveal occasional slow responses that the average may hide.

---

# 13. P99 Latency

P99 is the 99th percentile latency.

It focuses on the slowest part of the successful measurements.

Example:

```text
Average: 25 ms
P95:     41 ms
P99:     70 ms
```

P99 can be useful when investigating occasional latency spikes.

---

# 14. Score / Grade

Depending on the version and configuration, Network Ping Pro may calculate an overall network score or grade from the collected measurements.

Treat this as a simplified diagnostic indicator rather than an official measurement of internet quality.

The raw metrics such as:

* Average
* Min
* Max
* Jitter
* P95
* P99
* Packet Loss

are more useful when performing detailed analysis.

---

# 15. Export Results

Network Ping Pro supports result exporting when the corresponding export options are available in your version.

Typical formats include:

```text
CSV
JSON
```

CSV is useful for:

* Excel
* Google Sheets
* Data analysis

JSON is useful for:

* Scripts
* APIs
* Automation
* Further processing

Use:

```bash
python network_ping_pro.py --help
```

to see the exact export arguments supported by your installed version.

---

# 16. Proxy

HTTP tests can support proxy configuration when proxy options are available.

This can be useful when your network requires traffic to pass through a proxy server.

Always check:

```bash
python network_ping_pro.py --help
```

for the exact proxy arguments supported by your version.

---

# 17. No-Color Mode

If your version supports disabling terminal colors:

```bash
python network_ping_pro.py --no-color google.com
```

This is useful when:

* Redirecting output to a file
* Using terminals with poor color support
* Copying output
* Running automated scripts

---

# 18. Help

The most important command for discovering the options supported by your exact version is:

```bash
python network_ping_pro.py --help
```

It should show:

* Available commands
* Test methods
* Options
* Defaults
* Input formats

Always use `--help` if an option documented elsewhere does not work.

---

# 19. Practical Examples

## Check Google

```bash
python network_ping_pro.py google.com
```

## Check several services

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

## Check HTTPS with TCP

```bash
python network_ping_pro.py -m TCP google.com:443
```

## Check HTTP response

```bash
python network_ping_pro.py -m HTTP https://google.com
```

## Check many targets from a file

```bash
python network_ping_pro.py -f targets.txt
```

## Run more samples

```bash
python network_ping_pro.py google.com --count 20
```

## Increase timeout

```bash
python network_ping_pro.py google.com --timeout 5
```

## Test multiple targets concurrently

```bash
python network_ping_pro.py google.com github.com cloudflare.com --workers 5
```

## Disable terminal colors

```bash
python network_ping_pro.py --no-color google.com
```

---

# 20. Recommended Diagnostic Workflow

When troubleshooting a network problem, start simple.

### Step 1 — ICMP

```bash
python network_ping_pro.py google.com
```

If this works, basic connectivity is available.

### Step 2 — TCP

```bash
python network_ping_pro.py -m TCP google.com:443
```

This checks connectivity to HTTPS through TCP.

### Step 3 — HTTP

```bash
python network_ping_pro.py -m HTTP https://google.com
```

This checks the actual web service.

### Step 4 — Multiple Targets

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

Comparing several destinations can help identify whether a problem affects one destination or the wider connection.

---

# 21. Example targets.txt

```text
google.com
github.com
cloudflare.com
1.1.1.1
8.8.8.8
```

Run:

```bash
python network_ping_pro.py -f targets.txt
```

---

# 22. Understanding the Results

A typical diagnostic result may contain measurements such as:

```text
Average
Minimum
Maximum
Jitter
P95
P99
Packet Loss
```

Do not rely on one number alone.

For example:

```text
Average: 25 ms
Max:     120 ms
Jitter:  18 ms
Loss:    0%
```

The average looks reasonable, but the high maximum and jitter indicate that some requests experienced significant delay.

---

# 23. Troubleshooting with Network Ping Pro

## ICMP fails but TCP works

Possible causes include:

* ICMP filtering
* Firewall rules
* Destination configuration

Try:

```bash
python network_ping_pro.py -m TCP google.com:443
```

---

## TCP works but HTTP fails

Possible causes include:

* HTTP-specific filtering
* Proxy configuration
* TLS issues
* Application-level problems
* curl configuration

Check:

```bash
curl --version
```

---

## High packet loss

Check multiple targets:

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

If several independent targets show loss, the issue may be closer to your local network or internet connection.

If only one target is affected, the problem may be specific to that destination or path.

---

## High jitter

Run more samples:

```bash
python network_ping_pro.py google.com --count 20
```

Then compare:

* Average
* Maximum
* Jitter
* P95
* P99

---

# 24. Automation

Because Network Ping Pro is a command-line application, it can be used by:

* Windows batch scripts
* PowerShell
* Bash
* Cron jobs
* CI/CD systems
* Monitoring scripts
* Python automation
* Other command-line tools

For automation, JSON or CSV output can be particularly useful when supported by the installed version.

---

# 25. Find Every Option Supported by Your Version

The definitive reference is always:

```bash
python network_ping_pro.py --help
```

This is important because command-line options may change between versions.

---

## License

Network Ping Pro is released under the MIT License.
