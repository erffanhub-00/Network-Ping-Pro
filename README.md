# Network Ping Pro

A lightweight and practical network diagnostic tool for testing **ICMP, TCP, and HTTP connectivity and latency** from your local machine.

> 🌐 **Project:** [Network Ping Pro](https://github.com/erffanhub-00/network-ping-pro)
> 📖 **Installation Guide:** [INSTALL.md](INSTALL.md)
> 📚 **Usage Guide:** [USAGE.md](USAGE.md)

Network Ping Pro is designed to provide useful network measurements without requiring a complicated monitoring platform or external service.

---

## ✦ Features

* ICMP ping testing
* TCP connection testing
* HTTP response testing
* Multiple target testing
* Targets loaded from a file
* Configurable test count
* Configurable timeout
* Concurrent testing
* Average latency
* Minimum latency
* Maximum latency
* Jitter calculation
* Packet loss measurement
* P95 latency
* P99 latency
* Network score / grade
* Detailed test results
* Colored terminal output
* No-color mode
* CSV / JSON export
* Proxy support for HTTP testing
* Local machine testing
* No external monitoring server required

For complete usage examples, see **[USAGE.md](USAGE.md)**.

---

## ✦ What Is Network Ping Pro?

Network Ping Pro is a command-line network diagnostic tool written in Python.

Instead of relying on a website to perform a network test, the tool runs tests **directly from your own computer**.

This makes it useful for checking:

* Internet connectivity
* Website accessibility
* Network latency
* TCP connectivity
* HTTP response time
* Packet loss
* Connection stability
* Differences between network targets

---

## ✦ Test Methods

### ICMP

Traditional ping testing.

```bash
python network_ping_pro.py google.com
```

Useful for measuring basic network latency and packet loss.

### TCP

Tests whether a TCP connection can be established to a specific port.

```bash
python network_ping_pro.py -m TCP google.com:443
```

Useful for checking services such as:

```text
443  HTTPS
80   HTTP
22   SSH
25   SMTP
53   DNS
```

### HTTP

Tests an HTTP/HTTPS URL and measures response time.

```bash
python network_ping_pro.py -m HTTP https://google.com
```

HTTP testing requires `curl`.

---

## ✦ Tech Stack

| Technology              | Purpose                  |
| ----------------------- | ------------------------ |
| Python 3.9+             | Core application         |
| ICMP / ping             | Network latency testing  |
| TCP sockets             | TCP connectivity testing |
| curl                    | HTTP testing             |
| Threading / concurrency | Parallel tests           |
| CSV / JSON              | Result export            |

---

## ✦ Installation

### Requirements

* Python **3.9+**
* `curl` for HTTP testing
* `ping` support for ICMP testing
* Windows, Linux, or macOS

### Quick Install

Clone the repository:

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

Run:

```bash
python network_ping_pro.py google.com
```

Linux/macOS:

```bash
python3 network_ping_pro.py google.com
```

### New to Python?

If you have never used Python before, or you get an error such as:

```text
Python was not found
```

read the complete installation guide:

➡️ **[INSTALL.md](INSTALL.md)**

---

## ✦ Quick Examples

### Basic ping

```bash
python network_ping_pro.py google.com
```

### Test multiple targets

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

### TCP test

```bash
python network_ping_pro.py -m TCP google.com:443
```

### HTTP test

```bash
python network_ping_pro.py -m HTTP https://google.com
```

### Targets from file

```bash
python network_ping_pro.py -f targets.txt
```

For more commands and examples:

➡️ **[USAGE.md](USAGE.md)**

---

## ✦ Project Structure

```text
network-ping-pro/
├── network_ping_pro.py
├── README.md
├── INSTALL.md
├── USAGE.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── targets.example.txt
└── screenshots/
    └── demo.png
```

---

## 🚀 Demo

Network Ping Pro running directly from the Windows Command Prompt:

![Network Ping Pro Demo](screenshots/demo.gif)

---

## ✦ Documentation

| Document                 | Description                     |
| ------------------------ | ------------------------------- |
| [README.md](README.md)   | Project overview                |
| [INSTALL.md](INSTALL.md) | Complete installation guide     |
| [USAGE.md](USAGE.md)     | Commands, options, and examples |
| [LICENSE](LICENSE)       | MIT License                     |

---

# فارسی | Persian

## ✦ Network Ping Pro چیست؟

**Network Ping Pro** یک ابزار خط فرمان برای بررسی وضعیت شبکه و اندازه‌گیری latency است که با Python نوشته شده است.

برنامه مستقیماً روی کامپیوتر شما اجرا می‌شود و برای تست‌های اصلی به یک سرویس مانیتورینگ خارجی نیاز ندارد.

با این ابزار می‌توانید موارد زیر را بررسی کنید:

* اتصال شبکه
* سرعت پاسخ شبکه
* Packet Loss
* پایداری اتصال
* اتصال TCP
* پاسخ HTTP/HTTPS
* Latency سرویس‌ها
* حداقل و حداکثر latency
* Average latency
* Jitter
* P95
* P99
* وضعیت چند مقصد به‌صورت هم‌زمان

---

## ✦ روش‌های تست

### ICMP

برای تست معمول ping:

```bash
python network_ping_pro.py google.com
```

### TCP

برای بررسی اتصال به یک پورت:

```bash
python network_ping_pro.py -m TCP google.com:443
```

### HTTP

برای بررسی زمان پاسخ HTTP:

```bash
python network_ping_pro.py -m HTTP https://google.com
```

---

## ✦ نصب سریع

ابتدا پروژه را دریافت کنید:

```bash
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro
```

سپس:

```bash
python network_ping_pro.py google.com
```

اگر Python را نصب نکرده‌اید یا با خطای `Python was not found` مواجه شدید، راهنمای کامل نصب را ببینید:

➡️ **[راهنمای نصب](INSTALL.md)**

---

## ✦ مثال‌های سریع

تست یک مقصد:

```bash
python network_ping_pro.py google.com
```

تست چند مقصد:

```bash
python network_ping_pro.py google.com github.com cloudflare.com
```

تست TCP:

```bash
python network_ping_pro.py -m TCP google.com:443
```

تست HTTP:

```bash
python network_ping_pro.py -m HTTP https://google.com
```

خواندن مقصدها از فایل:

```bash
python network_ping_pro.py -f targets.txt
```

برای مشاهده تمام قابلیت‌ها و مثال‌ها:

➡️ **[USAGE.md](USAGE.md)**

---

## ✦ فلسفه پروژه

هدف Network Ping Pro این است که یک ابزار نسبتاً ساده، سریع و کاربردی برای بررسی شبکه باشد؛ بدون اینکه کاربر مجبور باشد یک سیستم مانیتورینگ پیچیده راه‌اندازی کند.

---

## ✦ License

This project is licensed under the **MIT License**.

---

## ✦ Me

[![Telegram](https://img.shields.io/badge/Telegram-erffan__hub-blue?style=for-the-badge\&logo=telegram)](https://t.me/erffan_hub)
[![Twitter](https://img.shields.io/badge/Twitter-@Erffanhub__00-000000?style=for-the-badge\&logo=x\&logoColor=white)](https://x.com/Erffanhub_00)
[![Gist](https://img.shields.io/badge/Gist-Profile-000000?style=for-the-badge\&logo=github)](https://gist.github.com/erffanhub-00)
[![Github](https://img.shields.io/badge/Github-Profile-000000?style=for-the-badge\&logo=github)](https://github.com/erffanhub-00)
