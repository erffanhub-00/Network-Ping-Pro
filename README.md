# 🌐 Network Ping Pro

<div align="center">

![Python](https://img.shields.io/badge/Python-3.7+-blue?style=for-the-badge&logo=python)
![Tkinter](https://img.shields.io/badge/Tkinter-GUI-green?style=for-the-badge&logo=tk)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-2.0.0-red?style=for-the-badge)

**Professional Network Diagnostic Tool - ICMP / TCP / HTTP**

[English](#-english) • [فارسی](#-فارسی)

</div>

---

# 🇬🇧 English

## 📖 Overview

**Network Ping Pro** is a powerful, user-friendly network diagnostic tool that tests connectivity and latency using multiple protocols. Built with Python and Tkinter, it provides comprehensive network analysis with real-time results, scoring, and export capabilities.

### Why Network Ping Pro?

| Feature | Benefit |
|---------|---------|
| **Multi-Protocol** | Test with ICMP, TCP, or HTTP |
| **Proxy Support** | Works with HTTP, HTTPS, SOCKS4, SOCKS5 |
| **Real-time Results** | Live progress and detailed statistics |
| **Smart Scoring** | 0-100 quality score with grades |
| **Export Options** | CSV and JSON export |
| **User-Friendly** | Simple GUI with copy/paste support |

---

## ✨ Features

### 🔍 Testing Methods
- **ICMP** - Standard ping (fastest, no proxy)
- **TCP** - Real TCP connection test (supports proxy)
- **HTTP** - Real HTTP/HTTPS request (supports proxy)

### 📊 Comprehensive Statistics
- **Basic:** Min, Max, Average
- **Advanced:** Jitter, P50, P95, P99
- **Network:** Packet Loss, DNS Resolution Time
- **Protocol Specific:** TCP Connect Time, HTTP Status Code

### 🎯 Smart Scoring System
- **Score:** 0-100 quality score
- **Grade:** Excellent / Very Good / Good / Fair / Poor
- **Multi-factor:** Latency, Packet Loss, Jitter, P95 Penalty

### 🌐 Proxy Support
- HTTP / HTTPS Proxy
- SOCKS4 / SOCKS5 Proxy
- Authentication Support
- v2ray/Hiddify Preset

### 📈 Export & Logging
- **CSV Export** - Spreadsheet compatible
- **JSON Export** - Machine readable
- **Live Log** - Real-time activity log
- **Log Export** - Save diagnostic logs

### 🖥️ User Interface
- Clean, modern design
- Copy/Paste support (Ctrl+A, Ctrl+C, Ctrl+V)
- Right-click context menu
- Progress tracking
- Responsive layout

---

## 🚀 Installation

### Prerequisites

```bash
# Python 3.7 or higher
python --version

# Required for HTTP method
curl --version
```

### Quick Install

```bash
# Clone the repository
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro

# Run the application
python network_ping_pro.py
```

### One-File Version

```bash
# Download the single file
curl -O https://raw.githubusercontent.com/erffanhub-00/network-ping-pro/main/network_ping_pro.py

# Run it
python network_ping_pro.py
```

### Create Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "NetworkPingPro" network_ping_pro.py
```

---

## 📝 Usage

### Basic Usage

1. **Enter Targets**
   ```
   google.com
   github.com:443
   https://example.com/test
   ```

2. **Select Method**
   - `ICMP` - Standard ping
   - `TCP` - Connection test
   - `HTTP` - HTTP/HTTPS request

3. **Configure Settings**
   - `Pings`: Number of tests (1-50)
   - `Timeout`: Max wait time (1-10s)
   - `Workers`: Concurrent tests (1-20)

4. **Start Test** - Click "Start Test"

### Target Formats

| Format | Example | Method |
|--------|---------|--------|
| Domain | `google.com` | All Methods |
| Domain:Port | `google.com:443` | TCP |
| URL | `https://example.com/test` | HTTP |
| IPv6 | `[::1]:8080` | All Methods |
| IPv4 | `8.8.8.8` | All Methods |

### Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select all targets |
| `Ctrl+V` | Paste from clipboard |
| `Ctrl+C` | Copy from log |
| `Right-click` | Context menu |

---

## 🔒 Proxy Setup

### Enable Proxy

1. Check **"Use Proxy"**
2. Select proxy type:
   - `http` / `https` - HTTP proxy
   - `socks4` / `socks5` - SOCKS proxy
3. Enter **Host** and **Port**
4. Click **"v2ray/Hiddify Preset"** for quick setup

### Proxy Presets

| Service | Type | Host | Port |
|---------|------|------|------|
| v2ray | SOCKS5 | 127.0.0.1 | 10808 |
| Hiddify | SOCKS5 | 127.0.0.1 | 10808 |
| Hiddify (HTTP) | HTTP | 127.0.0.1 | 10809 |

---

## 📊 Results Explained

### Score & Grade

| Score | Grade | Meaning |
|-------|-------|---------|
| 90-100 | Excellent | Perfect connection |
| 80-89 | Very Good | Great connection |
| 70-79 | Good | Acceptable |
| 60-69 | Fair | Needs improvement |
| <60 | Poor | Unstable connection |

### Statistics

| Metric | Description |
|--------|-------------|
| **Avg** | Average response time (ms) |
| **Min/Max** | Fastest/slowest response |
| **Jitter** | Variation between responses |
| **P50** | 50% of responses under this value |
| **P95** | 95% of responses under this value |
| **P99** | 99% of responses under this value |
| **Loss** | Percentage of lost packets |

### Status Codes

| Status | Meaning |
|--------|---------|
| **OK** | Test successful |
| **Timeout** | No response within timeout |
| **Refused** | Connection refused (TCP) |
| **DNS Error** | DNS resolution failed |
| **Unreachable** | Host unreachable |
| **HTTP Code** | HTTP status code (200, 404, etc.) |

---

## 🛠️ Requirements

| Component | Requirement |
|-----------|-------------|
| **ICMP** | Built-in ping command |
| **TCP** | Python socket library |
| **HTTP** | curl installed |
| **Proxy** | curl for HTTP/HTTPS |
| **OS** | Windows/Linux/macOS |

### Install curl (Windows)

```powershell
# Download from: https://curl.se/windows/
# Or use winget
winget install curl
```

---

## 📁 Project Structure

```
network-ping-pro/
├── network_ping_pro.py   # Main application
├── README.md             # This file
├── LICENSE               # MIT License
└── requirements.txt      # Python dependencies
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 👨‍💻 Author

### Erffan

<div align="center">

[![Telegram](https://img.shields.io/badge/Telegram-erffan__hub-blue?style=for-the-badge&logo=telegram)](https://t.me/erffan_hub)
[![Twitter](https://img.shields.io/badge/Twitter-@Erffanhub__00-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/Erffanhub_00)
[![Gist](https://img.shields.io/badge/Gist-Profile-000000?style=for-the-badge&logo=github)](https://gist.github.com/erffanhub-00)
[![GitHub](https://img.shields.io/badge/GitHub-Profile-000000?style=for-the-badge&logo=github)](https://github.com/erffanhub-00)

</div>





---

# 🇮🇷 فارسی

## 📖 معرفی

**Network Ping Pro** یک ابزار قدرتمند و کاربرپسند برای تشخیص شبکه است که اتصال و تأخیر را با استفاده از چندین پروتکل مختلف تست می‌کند. این برنامه با پایتون و Tkinter ساخته شده و تحلیل جامع شبکه را با نتایج لحظه‌ای، امتیازدهی و قابلیت خروجی ارائه می‌دهد.

### چرا Network Ping Pro؟

| ویژگی | مزیت |
|-------|------|
| **چند-پروتکلی** | تست با ICMP، TCP یا HTTP |
| **پشتیبانی از پروکسی** | کار با HTTP، HTTPS، SOCKS4، SOCKS5 |
| **نتایج لحظه‌ای** | پیشرفت زنده و آمار دقیق |
| **امتیازدهی هوشمند** | امتیاز کیفیت ۰ تا ۱۰۰ با درجه‌بندی |
| **خروجی‌های مختلف** | خروجی CSV و JSON |
| **کاربرپسند** | رابط گرافیکی ساده با پشتیبانی از کپی/پیست |

---

## ✨ قابلیت‌ها

### 🔍 روش‌های تست
- **ICMP** - پینگ استاندارد (سریع‌ترین، بدون پروکسی)
- **TCP** - تست اتصال TCP واقعی (پشتیبانی از پروکسی)
- **HTTP** - درخواست HTTP/HTTPS واقعی (پشتیبانی از پروکسی)

### 📊 آمار جامع
- **پایه:** حداقل، حداکثر، میانگین
- **پیشرفته:** جیتر، P50، P95، P99
- **شبکه:** درصد از دست رفتن بسته، زمان Resolution DNS
- **مخصوص پروتکل:** زمان اتصال TCP، کد وضعیت HTTP

### 🎯 سیستم امتیازدهی هوشمند
- **امتیاز:** کیفیت ۰ تا ۱۰۰
- **درجه:** عالی / خیلی خوب / خوب / متوسط / ضعیف
- **چندعاملی:** تأخیر، از دست رفتگی، جیتر، جریمه P95

### 🌐 پشتیبانی از پروکسی
- پروکسی HTTP / HTTPS
- پروکسی SOCKS4 / SOCKS5
- پشتیبانی از احراز هویت
- تنظیم سریع v2ray/Hiddify

### 📈 خروجی و لاگ
- **خروجی CSV** - سازگار با صفحات گسترده
- **خروجی JSON** - قابل خواندن توسط ماشین
- **لاگ زنده** - لاگ فعالیت لحظه‌ای
- **ذخیره لاگ** - ذخیره لاگ‌های تشخیصی

### 🖥️ رابط کاربری
- طراحی تمیز و مدرن
- پشتیبانی از کپی/پیست (Ctrl+A، Ctrl+C، Ctrl+V)
- منوی راست‌کلیک
- نمایش پیشرفت
- واکنش‌گرا

---

## 🚀 نصب

### پیش‌نیازها

```bash
# پایتون ۳.۷ یا بالاتر
python --version

# برای روش HTTP نیاز است
curl --version
```

### نصب سریع

```bash
# کلون کردن مخزن
git clone https://github.com/erffanhub-00/network-ping-pro.git
cd network-ping-pro

# اجرای برنامه
python network_ping_pro.py
```

### نسخه تک‌فایل

```bash
# دانلود فایل
curl -O https://raw.githubusercontent.com/erffanhub-00/network-ping-pro/main/network_ping_pro.py

# اجرا
python network_ping_pro.py
```

### ساخت فایل اجرایی

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "NetworkPingPro" network_ping_pro.py
```

فایل اجرایی در پوشه `dist` قرار می‌گیرد.

---

## 📝 نحوه استفاده

### استفاده اولیه

1. **وارد کردن مقصدها**
   ```
   google.com
   github.com:443
   https://example.com/test
   ```

2. **انتخاب روش**
   - `ICMP` - پینگ استاندارد
   - `TCP` - تست اتصال
   - `HTTP` - درخواست HTTP/HTTPS

3. **تنظیمات**
   - `تعداد پینگ`: تعداد تست‌ها (۱ تا ۵۰)
   - `زمان انتظار`: حداکثر زمان انتظار (۱ تا ۱۰ ثانیه)
   - `تعداد همزمان`: تست‌های همزمان (۱ تا ۲۰)

4. **شروع تست** - کلیک روی "شروع تست"

### فرمت‌های مقصد

| فرمت | مثال | روش |
|------|------|-----|
| دامنه | `google.com` | همه روش‌ها |
| دامنه:پورت | `google.com:443` | TCP |
| URL | `https://example.com/test` | HTTP |
| IPv6 | `[::1]:8080` | همه روش‌ها |
| IPv4 | `8.8.8.8` | همه روش‌ها |

### میانبرهای صفحه‌کلید

| میانبر | عملکرد |
|--------|---------|
| `Ctrl+A` | انتخاب همه مقصدها |
| `Ctrl+V` | چسباندن از کلیپ‌بورد |
| `Ctrl+C` | کپی از لاگ |
| `راست‌کلیک` | منوی زمینه |

---

## 🔒 تنظیمات پروکسی

### فعال کردن پروکسی

1. تیک **"استفاده از پروکسی"** را بزنید
2. نوع پروکسی را انتخاب کنید:
   - `http` / `https` - پروکسی HTTP
   - `socks4` / `socks5` - پروکسی SOCKS
3. **میزبان** و **پورت** را وارد کنید
4. برای تنظیم سریع کلیک روی **"تنظیم v2ray/Hiddify"**

### تنظیمات سریع پروکسی

| سرویس | نوع | میزبان | پورت |
|-------|------|--------|------|
| v2ray | SOCKS5 | 127.0.0.1 | 10808 |
| Hiddify | SOCKS5 | 127.0.0.1 | 10808 |
| Hiddify (HTTP) | HTTP | 127.0.0.1 | 10809 |

---

## 📊 توضیح نتایج

### امتیاز و درجه

| امتیاز | درجه | معنی |
|--------|------|------|
| ۹۰-۱۰۰ | عالی | اتصال عالی |
| ۸۰-۸۹ | خیلی خوب | اتصال عالی |
| ۷۰-۷۹ | خوب | قابل قبول |
| ۶۰-۶۹ | متوسط | نیاز به بهبود |
| <۶۰ | ضعیف | اتصال ناپایدار |

### آمار

| معیار | توضیح |
|-------|-------|
| **میانگین** | میانگین زمان پاسخ (ms) |
| **حداقل/حداکثر** | سریع‌ترین/کندترین پاسخ |
| **جیتر** | تغییرات بین پاسخ‌ها |
| **P50** | ۵۰٪ پاسخ‌ها کمتر از این مقدار |
| **P95** | ۹۵٪ پاسخ‌ها کمتر از این مقدار |
| **P99** | ۹۹٪ پاسخ‌ها کمتر از این مقدار |
| **از دست رفته** | درصد بسته‌های از دست رفته |

### کدهای وضعیت

| وضعیت | معنی |
|-------|------|
| **OK** | تست موفق |
| **Timeout** | بدون پاسخ در زمان تعیین شده |
| **Refused** | اتصال رد شد (TCP) |
| **DNS Error** | خطا در Resolution DNS |
| **Unreachable** | میزبان در دسترس نیست |
| **HTTP Code** | کد وضعیت HTTP (۲۰۰، ۴۰۴ و...) |

---

## 🛠️ نیازمندی‌ها

| جزء | نیازمندی |
|-----|----------|
| **ICMP** | دستور ping داخلی |
| **TCP** | کتابخانه socket پایتون |
| **HTTP** | curl نصب شده |
| **پروکسی** | curl برای HTTP/HTTPS |
| **سیستم‌عامل** | Windows/Linux/macOS |

### نصب curl (ویندوز)

```powershell
# دانلود از: https://curl.se/windows/
# یا استفاده از winget
winget install curl
```

---

## 📁 ساختار پروژه

```
network-ping-pro/
├── network_ping_pro.py   # برنامه اصلی
├── README.md             # این فایل
├── LICENSE               # مجوز MIT
└── requirements.txt      # وابستگی‌های پایتون
```

---

## 🤝 مشارکت

۱. مخزن را Fork کنید
۲. شاخه ویژگی خود را ایجاد کنید (`git checkout -b feature/AmazingFeature`)
۳. تغییرات خود را Commit کنید (`git commit -m 'Add some AmazingFeature'`)
۴. به شاخه Push کنید (`git push origin feature/AmazingFeature`)
۵. یک Pull Request باز کنید

---


## 👨‍💻 توسعه‌دهنده

### Erffan

<div align="center">

[![Telegram](https://img.shields.io/badge/Telegram-erffan__hub-blue?style=for-the-badge&logo=telegram)](https://t.me/erffan_hub)
[![Twitter](https://img.shields.io/badge/Twitter-@Erffanhub__00-000000?style=for-the-badge&logo=x&logoColor=white)](https://x.com/Erffanhub_00)
[![Gist](https://img.shields.io/badge/Gist-Profile-000000?style=for-the-badge&logo=github)](https://gist.github.com/erffanhub-00)
[![GitHub](https://img.shields.io/badge/GitHub-Profile-000000?style=for-the-badge&logo=github)](https://github.com/erffanhub-00)

</div>


---
