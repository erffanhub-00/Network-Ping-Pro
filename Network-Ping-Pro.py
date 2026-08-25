# ============================================================
# Network Ping Pro - Professional Network Diagnostic Tool
# Version: 1.0.0
# Author: Erffan
# License: MIT
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import re
import platform
import statistics
import time
import threading
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import csv
import webbrowser
from urllib.parse import urlparse
from queue import Queue
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import os
import warnings
warnings.filterwarnings("ignore")


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class PingResult:
    """Complete result of a single ping test"""
    target: str
    success: bool
    method: str
    times: List[float] = field(default_factory=list)
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    jitter: Optional[float] = None
    p50: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None
    packet_loss: float = 100.0
    status: str = 'Failed'
    error: Optional[str] = None
    resolved_ip: Optional[str] = None
    rank: Optional[int] = None
    score: Optional[float] = None
    grade: Optional[str] = None
    dns_time: Optional[float] = None
    connect_time: Optional[float] = None
    http_status: Optional[int] = None
    tls_time: Optional[float] = None
    ttfb: Optional[float] = None
    total_time: Optional[float] = None
    port: Optional[int] = None


# ============================================================
# STATISTICS ENGINE
# ============================================================

class StatisticsEngine:
    """Professional statistics calculations"""
    
    @staticmethod
    def calculate_percentiles(times: List[float]) -> Dict[str, Optional[float]]:
        """Calculate P50, P95, P99 using proper statistics"""
        if not times:
            return {'p50': None, 'p95': None, 'p99': None}
        
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        def percentile(p: float) -> Optional[float]:
            if n == 0:
                return None
            if n == 1:
                return sorted_times[0]
            
            # Linear interpolation between closest ranks
            rank = (n - 1) * p / 100
            lower = int(rank)
            upper = lower + 1
            if upper >= n:
                return sorted_times[-1]
            weight = rank - lower
            return sorted_times[lower] * (1 - weight) + sorted_times[upper] * weight
        
        return {
            'p50': round(percentile(50), 1) if n >= 2 else None,
            'p95': round(percentile(95), 1) if n >= 5 else None,
            'p99': round(percentile(99), 1) if n >= 10 else None
        }
    
    @staticmethod
    def calculate_stats(times: List[float]) -> Dict[str, Any]:
        """Calculate all basic statistics"""
        if not times:
            return {}
        
        result = {
            'avg': round(sum(times) / len(times), 1),
            'min': round(min(times), 1),
            'max': round(max(times), 1),
        }
        
        if len(times) > 1:
            jitter_values = [abs(times[i] - times[i-1]) for i in range(1, len(times))]
            result['jitter'] = round(sum(jitter_values) / len(jitter_values), 1)
        else:
            result['jitter'] = 0.0
        
        percentiles = StatisticsEngine.calculate_percentiles(times)
        result.update(percentiles)
        
        return result
    
    @staticmethod
    def calculate_score(result: PingResult) -> float:
        """Multi-factor scoring: 0-100"""
        if not result.success:
            return 0.0
        
        # Base score from latency (lower is better)
        if result.avg is None:
            latency_score = 0
        elif result.avg <= 10:
            latency_score = 100
        elif result.avg <= 25:
            latency_score = 90
        elif result.avg <= 50:
            latency_score = 80
        elif result.avg <= 100:
            latency_score = 65
        elif result.avg <= 200:
            latency_score = 45
        elif result.avg <= 500:
            latency_score = 25
        else:
            latency_score = 10
        
        # Packet loss penalty
        if result.packet_loss == 0:
            loss_score = 100
        elif result.packet_loss <= 1:
            loss_score = 95
        elif result.packet_loss <= 5:
            loss_score = 75
        elif result.packet_loss <= 10:
            loss_score = 50
        elif result.packet_loss <= 20:
            loss_score = 25
        else:
            loss_score = 5
        
        # Jitter penalty
        if result.jitter is None:
            jitter_score = 50
        elif result.jitter <= 2:
            jitter_score = 100
        elif result.jitter <= 5:
            jitter_score = 85
        elif result.jitter <= 10:
            jitter_score = 65
        elif result.jitter <= 20:
            jitter_score = 40
        else:
            jitter_score = 15
        
        # P95 penalty
        p95_penalty = 1.0
        if result.p95 and result.avg:
            p95_ratio = result.p95 / result.avg
            if p95_ratio > 3:
                p95_penalty = 0.70
            elif p95_ratio > 2:
                p95_penalty = 0.85
        
        # HTTP status penalty (if applicable)
        http_penalty = 1.0
        if result.http_status:
            if 200 <= result.http_status < 400:
                http_penalty = 1.0
            elif 400 <= result.http_status < 500:
                http_penalty = 0.70
            elif 500 <= result.http_status < 600:
                http_penalty = 0.40
        
        final_score = (latency_score * 0.35 + loss_score * 0.30 + jitter_score * 0.25) * p95_penalty * http_penalty
        return round(max(0, min(100, final_score)), 1)
    
    @staticmethod
    def get_grade(score: float) -> str:
        if score >= 90:
            return 'Excellent'
        elif score >= 80:
            return 'Very Good'
        elif score >= 70:
            return 'Good'
        elif score >= 60:
            return 'Fair'
        else:
            return 'Poor'


# ============================================================
# DNS RESOLVER
# ============================================================

class DNSResolver:
    """DNS resolution with timing"""
    
    @staticmethod
    def resolve(host: str, timeout: int = 5) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """Resolve host to IP with timing"""
        try:
            start = time.perf_counter()
            addrs = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            elapsed = (time.perf_counter() - start) * 1000
            
            if not addrs:
                return None, elapsed, None
            
            # Get first IPv4 address if available, otherwise first address
            ip = None
            for addr in addrs:
                if addr[0] == socket.AF_INET:
                    ip = addr[4][0]
                    break
            if not ip:
                ip = addrs[0][4][0]
            
            return ip, round(elapsed, 1), None
            
        except socket.gaierror as e:
            return None, None, str(e)
        except Exception as e:
            return None, None, str(e)


# ============================================================
# PING ENGINE
# ============================================================

class PingEngine:
    """Complete ping engine with all methods"""
    
    # Proxy settings
    PROXY_TYPE = None
    PROXY_HOST = None
    PROXY_PORT = None
    PROXY_USER = None
    PROXY_PASS = None
    
    # Windows compatibility
    NULL_DEVICE = 'nul' if platform.system().lower() == 'windows' else '/dev/null'
    
    @staticmethod
    def set_proxy(proxy_type: str, host: str, port: int, user: str = None, password: str = None):
        PingEngine.PROXY_TYPE = proxy_type
        PingEngine.PROXY_HOST = host
        PingEngine.PROXY_PORT = port
        PingEngine.PROXY_USER = user
        PingEngine.PROXY_PASS = password
    
    @staticmethod
    def clear_proxy():
        PingEngine.PROXY_TYPE = None
        PingEngine.PROXY_HOST = None
        PingEngine.PROXY_PORT = None
        PingEngine.PROXY_USER = None
        PingEngine.PROXY_PASS = None
    
    @staticmethod
    def get_system():
        return platform.system().lower()
    
    @staticmethod
    def ping_icmp(host: str, count: int, timeout: int, stop_event: threading.Event) -> PingResult:
        """Standard ICMP ping with proper packet loss"""
        result = PingResult(target=host, success=False, method='ICMP')
        process = None
        
        try:
            # DNS resolution
            ip, dns_time, dns_error = DNSResolver.resolve(host, timeout)
            result.dns_time = dns_time
            
            if dns_error:
                result.error = f'DNS Error: {dns_error}'
                result.status = 'DNS Error'
                return result
            
            result.resolved_ip = ip
            
            # Build ping command
            system = PingEngine.get_system()
            if system == 'windows':
                cmd = ['ping', '-n', str(count), '-w', str(int(timeout * 1000)), host]
            elif system == 'darwin':
                cmd = ['ping', '-c', str(count), '-W', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
            
            # Run with Popen for proper stop
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            start_time = time.time()
            process_timeout = count * timeout + 10
            
            while process.poll() is None:
                if stop_event.is_set():
                    process.kill()
                    process.wait()
                    result.error = 'Cancelled'
                    result.status = 'Cancelled'
                    return result
                
                if time.time() - start_time > process_timeout:
                    process.kill()
                    process.wait()
                    result.error = 'Timeout'
                    result.status = 'Timeout'
                    return result
                
                time.sleep(0.05)
            
            stdout, stderr = process.communicate()
            output = stdout + stderr
            
            # Parse times
            times = []
            pattern = r'time[=<]\s*(\d+(?:[.,]\d+)?)\s*ms'
            matches = re.findall(pattern, output, re.IGNORECASE)
            
            if matches:
                for t in matches:
                    try:
                        val = float(t.replace(',', '.'))
                        if 0 <= val <= 10000:
                            times.append(val)
                    except ValueError:
                        continue
            
            if not times:
                pattern2 = r'(\d+(?:[.,]\d+)?)\s*ms'
                matches2 = re.findall(pattern2, output, re.IGNORECASE)
                if matches2:
                    for t in matches2:
                        try:
                            val = float(t.replace(',', '.'))
                            if 0 <= val <= 10000:
                                times.append(val)
                        except ValueError:
                            continue
            
            if not times:
                error_lower = output.lower()
                if "unreachable" in error_lower:
                    result.error = 'Host unreachable'
                    result.status = 'Unreachable'
                elif "could not find host" in error_lower or "unknown host" in error_lower:
                    result.error = 'DNS resolution failed'
                    result.status = 'DNS Error'
                elif "timed out" in error_lower or "timeout" in error_lower:
                    result.error = 'Request timeout'
                    result.status = 'Timeout'
                else:
                    result.error = 'No response'
                    result.status = 'No Response'
                return result
            
            result.success = True
            result.times = times
            
            # Calculate packet loss
            packet_loss = ((count - len(times)) / count) * 100
            result.packet_loss = round(min(packet_loss, 100.0), 1)
            result.status = 'OK' if result.packet_loss < 20 else 'High Loss'
            
            # Statistics
            stats = StatisticsEngine.calculate_stats(times)
            result.avg = stats.get('avg')
            result.min = stats.get('min')
            result.max = stats.get('max')
            result.jitter = stats.get('jitter')
            result.p50 = stats.get('p50')
            result.p95 = stats.get('p95')
            result.p99 = stats.get('p99')
            
            # Score
            result.score = StatisticsEngine.calculate_score(result)
            result.grade = StatisticsEngine.get_grade(result.score)
            
            return result
            
        except Exception as e:
            if process:
                try:
                    process.kill()
                except:
                    pass
            result.error = str(e)[:50]
            result.status = 'Error'
            return result
    
    @staticmethod
    def ping_tcp(host: str, port: int, count: int, timeout: int, stop_event: threading.Event) -> PingResult:
        """Real TCP connection test"""
        result = PingResult(target=host, success=False, method=f'TCP:{port}')
        result.port = port
        
        # DNS resolution
        ip, dns_time, dns_error = DNSResolver.resolve(host, timeout)
        result.dns_time = dns_time
        
        if dns_error:
            result.error = f'DNS Error: {dns_error}'
            result.status = 'DNS Error'
            return result
        
        result.resolved_ip = ip
        
        times = []
        successful = 0
        max_attempts = min(count, 20)
        
        for i in range(max_attempts):
            if stop_event.is_set():
                result.error = 'Cancelled'
                result.status = 'Cancelled'
                return result
            
            try:
                start = time.perf_counter()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                
                try:
                    sock.connect((host, port))
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                    successful += 1
                    sock.close()
                    
                except socket.timeout:
                    sock.close()
                    continue
                    
                except ConnectionRefusedError:
                    sock.close()
                    # Host is reachable but port is closed
                    result.error = 'Port closed (host reachable)'
                    result.status = 'Refused'
                    result.success = True
                    result.packet_loss = 100.0
                    result.score = 0
                    result.grade = 'Poor'
                    return result
                    
                except socket.gaierror:
                    sock.close()
                    result.error = 'DNS resolution failed'
                    result.status = 'DNS Error'
                    return result
                    
                except OSError as e:
                    sock.close()
                    if "timed out" in str(e).lower():
                        continue
                    continue
                    
                except Exception:
                    sock.close()
                    continue
                    
            except Exception:
                continue
        
        if not times:
            result.error = 'No TCP connection'
            result.status = 'Failed'
            return result
        
        result.success = True
        result.times = times
        
        packet_loss = ((max_attempts - successful) / max_attempts) * 100
        result.packet_loss = round(packet_loss, 1)
        result.status = 'OK' if result.packet_loss < 20 else 'High Loss'
        
        stats = StatisticsEngine.calculate_stats(times)
        result.avg = stats.get('avg')
        result.min = stats.get('min')
        result.max = stats.get('max')
        result.jitter = stats.get('jitter')
        result.p50 = stats.get('p50')
        result.p95 = stats.get('p95')
        result.p99 = stats.get('p99')
        
        result.connect_time = result.avg
        
        result.score = StatisticsEngine.calculate_score(result)
        result.grade = StatisticsEngine.get_grade(result.score)
        
        return result
    
    @staticmethod
    def ping_http(target_info: Dict[str, Any], count: int, timeout: int, stop_event: threading.Event) -> PingResult:
        """Real HTTP/HTTPS test with curl"""
        host = target_info['host']
        scheme = target_info.get('scheme', 'https')
        port = target_info.get('port')
        path = target_info.get('path', '/')
        query = target_info.get('query', '')
        
        result = PingResult(target=host, success=False, method='HTTP')
        result.port = port
        
        # DNS resolution
        ip, dns_time, dns_error = DNSResolver.resolve(host, timeout)
        result.dns_time = dns_time
        
        if dns_error:
            result.error = f'DNS Error: {dns_error}'
            result.status = 'DNS Error'
            return result
        
        result.resolved_ip = ip
        
        # Check curl
        try:
            subprocess.run(['curl', '--version'], capture_output=True, timeout=1)
        except:
            result.error = 'curl not installed (required for HTTP)'
            result.status = 'Error'
            return result
        
        # Build URL
        url = f"{scheme}://{host}"
        if port:
            url += f":{port}"
        url += path
        if query:
            url += f"?{query}"
        
        times = []
        successful = 0
        max_attempts = min(count, 20)
        status_codes = []
        
        for i in range(max_attempts):
            if stop_event.is_set():
                result.error = 'Cancelled'
                result.status = 'Cancelled'
                return result
            
            # curl command with Windows compatibility
            cmd = [
                'curl', '-s', '-o', PingEngine.NULL_DEVICE,
                '-w', '%{time_total}%%%{http_code}%%%{time_connect}%%%{time_starttransfer}',
                '--connect-timeout', str(timeout),
                '--max-time', str(timeout)
            ]
            
            # Add proxy if configured
            if PingEngine.PROXY_TYPE and PingEngine.PROXY_HOST and PingEngine.PROXY_PORT:
                proxy_url = f"{PingEngine.PROXY_TYPE}://{PingEngine.PROXY_HOST}:{PingEngine.PROXY_PORT}"
                if PingEngine.PROXY_USER and PingEngine.PROXY_PASS:
                    # URL encode credentials
                    user = PingEngine.PROXY_USER.replace('@', '%40').replace(':', '%3A')
                    passwd = PingEngine.PROXY_PASS.replace('@', '%40').replace(':', '%3A')
                    proxy_url = f"{PingEngine.PROXY_TYPE}://{user}:{passwd}@{PingEngine.PROXY_HOST}:{PingEngine.PROXY_PORT}"
                cmd.extend(['-x', proxy_url])
            
            cmd.append(url)
            
            process = None
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                start_time = time.time()
                process_timeout = timeout + 5
                
                while process.poll() is None:
                    if stop_event.is_set():
                        process.kill()
                        process.wait()
                        result.error = 'Cancelled'
                        result.status = 'Cancelled'
                        return result
                    
                    if time.time() - start_time > process_timeout:
                        process.kill()
                        process.wait()
                        break
                    
                    time.sleep(0.05)
                
                stdout, stderr = process.communicate()
                
                if stdout:
                    parts = stdout.strip().split('%%%')
                    if len(parts) == 4:
                        try:
                            total_time = float(parts[0]) * 1000
                            http_code = int(parts[1])
                            connect_time = float(parts[2]) * 1000 if parts[2] else None
                            ttfb = float(parts[3]) * 1000 if parts[3] else None
                            
                            if 0 <= total_time <= 10000:
                                times.append(total_time)
                                successful += 1
                                status_codes.append(http_code)
                                result.connect_time = connect_time
                                result.ttfb = ttfb
                        except ValueError:
                            continue
                            
            except Exception:
                if process:
                    try:
                        process.kill()
                    except:
                        pass
                continue
        
        if not times:
            result.error = 'No HTTP response'
            result.status = 'Failed'
            return result
        
        result.success = True
        result.times = times
        result.http_status = status_codes[-1] if status_codes else None
        
        packet_loss = ((max_attempts - successful) / max_attempts) * 100
        result.packet_loss = round(packet_loss, 1)
        
        # Determine status based on HTTP status code
        if result.http_status:
            if 200 <= result.http_status < 400:
                result.status = 'OK'
            elif 400 <= result.http_status < 500:
                result.status = f'Client Error {result.http_status}'
            elif 500 <= result.http_status < 600:
                result.status = f'Server Error {result.http_status}'
            else:
                result.status = f'HTTP {result.http_status}'
        else:
            result.status = 'OK' if result.packet_loss < 20 else 'High Loss'
        
        stats = StatisticsEngine.calculate_stats(times)
        result.avg = stats.get('avg')
        result.min = stats.get('min')
        result.max = stats.get('max')
        result.jitter = stats.get('jitter')
        result.p50 = stats.get('p50')
        result.p95 = stats.get('p95')
        result.p99 = stats.get('p99')
        result.total_time = result.avg
        
        result.score = StatisticsEngine.calculate_score(result)
        result.grade = StatisticsEngine.get_grade(result.score)
        
        return result
    
    @staticmethod
    def ping_host(target: Dict[str, Any], method: str, count: int, timeout: int, stop_event: threading.Event) -> PingResult:
        """Ping host using selected method"""
        host = target['host']
        
        if stop_event.is_set():
            return PingResult(target=host, success=False, method='Cancelled', status='Cancelled')
        
        if method == 'ICMP':
            return PingEngine.ping_icmp(host, count, timeout, stop_event)
        elif method == 'TCP':
            port = target.get('port', 443)
            return PingEngine.ping_tcp(host, port, count, timeout, stop_event)
        elif method == 'HTTP':
            return PingEngine.ping_http(target, count, timeout, stop_event)
        else:
            result = PingResult(target=host, success=False, method='Unknown')
            result.error = 'Unknown method'
            result.status = 'Error'
            return result


# ============================================================
# TARGET PARSER
# ============================================================

class TargetParser:
    """Complete target parser with IPv6 support"""
    
    @staticmethod
    def parse_target(value: str) -> Optional[Dict[str, Any]]:
        try:
            value = value.strip()
            if not value:
                return None
            
            # Handle IPv6 addresses
            if value.startswith('['):
                # IPv6 with port: [::1]:8080
                match = re.match(r'\[([0-9a-f:]+)\](?::(\d+))?', value)
                if match:
                    host = match.group(1)
                    port = int(match.group(2)) if match.group(2) else None
                    return {
                        'host': host,
                        'port': port,
                        'scheme': None,
                        'path': '/',
                        'query': '',
                        'raw': value
                    }
            
            # Add scheme if missing
            if '://' not in value:
                parsed = urlparse('//' + value)
            else:
                parsed = urlparse(value)
            
            host = parsed.hostname
            if not host:
                return None
            
            return {
                'host': host.lower(),
                'port': parsed.port,
                'scheme': parsed.scheme or None,
                'path': parsed.path or '/',
                'query': parsed.query or '',
                'raw': value
            }
        except:
            return None
    
    @staticmethod
    def parse_sites(text: str) -> List[Dict[str, Any]]:
        sites = []
        for s in text.replace('،', ',').replace('\n', ',').split(','):
            parsed = TargetParser.parse_target(s)
            if parsed:
                sites.append(parsed)
        
        # Remove duplicates
        seen = set()
        unique_sites = []
        for site in sites:
            key = (site['scheme'], site['host'], site['port'], site['path'])
            if key not in seen:
                seen.add(key)
                unique_sites.append(site)
        
        return unique_sites


# ============================================================
# MAIN APPLICATION
# ============================================================

class NetworkPingPro:
    """Main application class"""
    
    VERSION = "2.0.0"
    AUTHOR = "Erffan"
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"Network Ping Pro v{self.VERSION}")
        self.root.geometry("1500x950")
        self.root.minsize(1100, 700)
        self.root.configure(bg='white')
        
        self.running = False
        self.stop_event = threading.Event()
        self.results: List[PingResult] = []
        self.log_lines = []
        self.log_queue = Queue()
        self.max_log_lines = 3000
        self.current_test_thread = None
        
        self.setup_ui()
        self.root.after(200, self.process_log_queue)
        
        self.log_info("=" * 50)
        self.log_info(f"Network Ping Pro v{self.VERSION} Started")
        self.log_info(f"System: {platform.system()} {platform.release()}")
        self.log_info("=" * 50)
    
    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = tk.Frame(main_frame, bg='white')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            header_frame,
            text="Network Ping Pro",
            font=('Segoe UI', 20, 'bold'),
            fg='black',
            bg='white'
        ).pack(side=tk.LEFT)
        
        btn_frame = tk.Frame(header_frame, bg='white')
        btn_frame.pack(side=tk.RIGHT)
        
        for text, cmd, color in [
            ("Help", self.show_help, '#2ecc71'),
            ("About", self.show_about, '#3498db')
        ]:
            btn = tk.Button(
                btn_frame,
                text=text,
                command=cmd,
                font=('Segoe UI', 10, 'bold'),
                bg=color,
                fg='white',
                relief=tk.FLAT,
                cursor='hand2',
                padx=15,
                pady=5
            )
            btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Input Panel
        self._setup_input_panel(main_frame)
        self._setup_results_table(main_frame)
        self._setup_footer(main_frame)
    
    def _setup_input_panel(self, parent):
        top_panels = tk.Frame(parent, bg='white')
        top_panels.pack(fill=tk.BOTH, expand=True)
        
        left_panel = tk.Frame(top_panels, bg='white')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        input_card = tk.Frame(left_panel, bg='#f8f8f8', relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor='#dddddd')
        input_card.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        input_inner = tk.Frame(input_card, bg='#f8f8f8')
        input_inner.pack(padx=12, pady=10, fill=tk.BOTH, expand=True)
        
        # Targets
        label_frame = tk.Frame(input_inner, bg='#f8f8f8')
        label_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(label_frame, text="Targets (one per line or comma separated)", font=('Segoe UI', 10, 'bold'), fg='black', bg='#f8f8f8').pack(side=tk.LEFT)
        
        paste_btn = tk.Button(label_frame, text="Paste", command=self.paste_from_clipboard, font=('Segoe UI', 9, 'bold'), bg='#3498db', fg='white', relief=tk.FLAT, cursor='hand2', padx=12, pady=2)
        paste_btn.pack(side=tk.RIGHT)
        
        self.sites_text = scrolledtext.ScrolledText(input_inner, height=4, font=('Consolas', 10), bg='white', fg='black', relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor='#cccccc')
        self.sites_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.sites_text.bind('<Control-a>', self.select_all)
        self.sites_text.bind('<Control-v>', self.paste_text)
        self.sites_text.bind('<Button-3>', self.right_click_menu)
        
        # Settings Row 1
        settings_frame1 = tk.Frame(input_inner, bg='#f8f8f8')
        settings_frame1.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(settings_frame1, text="Method:", font=('Segoe UI', 9), fg='black', bg='#f8f8f8').pack(side=tk.LEFT, padx=(0, 5))
        self.method_var = tk.StringVar(value='ICMP')
        method_combo = ttk.Combobox(settings_frame1, textvariable=self.method_var, values=['ICMP', 'TCP', 'HTTP'], state='readonly', width=10, font=('Segoe UI', 9))
        method_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(settings_frame1, text="Pings:", font=('Segoe UI', 9), fg='black', bg='#f8f8f8').pack(side=tk.LEFT, padx=(0, 5))
        self.count_var = tk.StringVar(value='10')
        count_spin = tk.Spinbox(settings_frame1, from_=1, to=50, textvariable=self.count_var, width=5, font=('Segoe UI', 9), bg='white', fg='black', relief=tk.FLAT, bd=1)
        count_spin.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(settings_frame1, text="Timeout (s):", font=('Segoe UI', 9), fg='black', bg='#f8f8f8').pack(side=tk.LEFT, padx=(0, 5))
        self.timeout_var = tk.StringVar(value='3')
        timeout_spin = tk.Spinbox(settings_frame1, from_=1, to=10, textvariable=self.timeout_var, width=4, font=('Segoe UI', 9), bg='white', fg='black', relief=tk.FLAT, bd=1)
        timeout_spin.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(settings_frame1, text="Workers:", font=('Segoe UI', 9), fg='black', bg='#f8f8f8').pack(side=tk.LEFT, padx=(0, 5))
        self.concurrent_var = tk.StringVar(value='10')
        concurrent_spin = tk.Spinbox(settings_frame1, from_=1, to=20, textvariable=self.concurrent_var, width=4, font=('Segoe UI', 9), bg='white', fg='black', relief=tk.FLAT, bd=1)
        concurrent_spin.pack(side=tk.LEFT)
        
        # Settings Row 2 - Proxy
        settings_frame2 = tk.Frame(input_inner, bg='#f8f8f8')
        settings_frame2.pack(fill=tk.X, pady=(5, 0))
        
        self.proxy_var = tk.BooleanVar(value=False)
        proxy_check = tk.Checkbutton(settings_frame2, text="Use Proxy", variable=self.proxy_var, 
                                     command=self.toggle_proxy, font=('Segoe UI', 9), bg='#f8f8f8', fg='black')
        proxy_check.pack(side=tk.LEFT, padx=(0, 10))
        
        self.proxy_type_var = tk.StringVar(value='socks5')
        proxy_type_combo = ttk.Combobox(settings_frame2, textvariable=self.proxy_type_var, 
                                        values=['http', 'https', 'socks5', 'socks4'], 
                                        state='readonly', width=8, font=('Segoe UI', 9))
        proxy_type_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Label(settings_frame2, text="Host:", font=('Segoe UI', 9), fg='black', bg='#f8f8f8').pack(side=tk.LEFT, padx=(0, 5))
        self.proxy_host_var = tk.StringVar(value='127.0.0.1')
        proxy_host_entry = tk.Entry(settings_frame2, textvariable=self.proxy_host_var, width=15, font=('Segoe UI', 9), bg='white', fg='black', relief=tk.FLAT, bd=1)
        proxy_host_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Label(settings_frame2, text="Port:", font=('Segoe UI', 9), fg='black', bg='#f8f8f8').pack(side=tk.LEFT, padx=(0, 5))
        self.proxy_port_var = tk.StringVar(value='10808')
        proxy_port_entry = tk.Entry(settings_frame2, textvariable=self.proxy_port_var, width=6, font=('Segoe UI', 9), bg='white', fg='black', relief=tk.FLAT, bd=1)
        proxy_port_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        preset_btn = tk.Button(settings_frame2, text="v2ray/Hiddify (127.0.0.1:10808)", 
                               command=self.set_v2ray_preset, font=('Segoe UI', 8), 
                               bg='#e8f0fe', fg='#1a73e8', relief=tk.FLAT, cursor='hand2', padx=10, pady=2)
        preset_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        self._set_proxy_fields_state('disabled')
        
        # Settings Row 3 - Controls
        settings_frame3 = tk.Frame(input_inner, bg='#f8f8f8')
        settings_frame3.pack(fill=tk.X, pady=(5, 0))
        
        self.start_btn = tk.Button(settings_frame3, text="Start Test", command=self.start_test, 
                                   font=('Segoe UI', 10, 'bold'), bg='black', fg='white', 
                                   relief=tk.FLAT, cursor='hand2', padx=25, pady=6)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = tk.Button(settings_frame3, text="Stop", command=self.stop_test, 
                                  font=('Segoe UI', 10, 'bold'), bg='#e74c3c', fg='white', 
                                  relief=tk.FLAT, cursor='hand2', padx=25, pady=6, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_btn = tk.Button(settings_frame3, text="Clear", command=self.clear_all, 
                                   font=('Segoe UI', 10, 'bold'), bg='#95a5a6', fg='white', 
                                   relief=tk.FLAT, cursor='hand2', padx=20, pady=6)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        self.progress_label = tk.Label(settings_frame3, text="Ready", font=('Segoe UI', 9, 'bold'), fg='#2ecc71', bg='#f8f8f8')
        self.progress_label.pack(side=tk.LEFT, padx=(10, 0))
        
        self.progress_bar = ttk.Progressbar(settings_frame3, mode='determinate', length=120)
        self.progress_bar.pack(side=tk.LEFT, padx=(10, 0))
        
        # Log Panel
        right_panel = tk.Frame(top_panels, bg='white', width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        log_card = tk.Frame(right_panel, bg='#f8f8f8', relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor='#dddddd')
        log_card.pack(fill=tk.BOTH, expand=True)
        
        log_inner = tk.Frame(log_card, bg='#f8f8f8')
        log_inner.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        log_header = tk.Frame(log_inner, bg='#f8f8f8')
        log_header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(log_header, text="Log", font=('Segoe UI', 10, 'bold'), fg='black', bg='#f8f8f8').pack(side=tk.LEFT)
        
        clear_log_btn = tk.Button(log_header, text="Clear", command=self.clear_log, font=('Segoe UI', 8), bg='#95a5a6', fg='white', relief=tk.FLAT, cursor='hand2', padx=10)
        clear_log_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        save_log_btn = tk.Button(log_header, text="Save", command=self.save_log, font=('Segoe UI', 8), bg='#3498db', fg='white', relief=tk.FLAT, cursor='hand2', padx=10)
        save_log_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(log_inner, height=15, font=('Consolas', 8), bg='#1e1e1e', fg='#d4d4d4', relief=tk.FLAT, bd=1, highlightthickness=1, highlightcolor='#cccccc')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.bind('<Control-c>', self.copy_from_log)
        self.log_text.bind('<Button-3>', self.log_right_click)
        
        self.log_text.tag_configure('info', foreground='#4fc3f7')
        self.log_text.tag_configure('success', foreground='#81c784')
        self.log_text.tag_configure('error', foreground='#e57373')
        self.log_text.tag_configure('warning', foreground='#ffb74d')
    
    def _setup_results_table(self, parent):
        table_frame = tk.Frame(parent, bg='white')
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        
        columns = ('rank', 'site', 'method', 'score', 'grade', 'avg', 'min', 'max', 'jitter', 'p50', 'p95', 'p99', 'loss', 'status')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=10, 
                                 yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        col_config = {
            'rank': {'text': '#', 'width': 35},
            'site': {'text': 'Target', 'width': 140},
            'method': {'text': 'Method', 'width': 65},
            'score': {'text': 'Score', 'width': 55},
            'grade': {'text': 'Grade', 'width': 75},
            'avg': {'text': 'Avg', 'width': 65},
            'min': {'text': 'Min', 'width': 65},
            'max': {'text': 'Max', 'width': 65},
            'jitter': {'text': 'Jitter', 'width': 60},
            'p50': {'text': 'P50', 'width': 55},
            'p95': {'text': 'P95', 'width': 55},
            'p99': {'text': 'P99', 'width': 55},
            'loss': {'text': 'Loss %', 'width': 60},
            'status': {'text': 'Status', 'width': 75}
        }
        
        for col, config in col_config.items():
            self.tree.heading(col, text=config['text'], anchor='center')
            self.tree.column(col, width=config['width'], anchor='center', minwidth=35)
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x.grid(row=1, column=0, sticky='ew')
        self.tree.grid(row=0, column=0, sticky='nsew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background='white', foreground='black', rowheight=26, 
                       fieldbackground='white', font=('Segoe UI', 8))
        style.configure('Treeview.Heading', background='#f0f0f0', foreground='black', font=('Segoe UI', 8, 'bold'))
        
        self.tree.tag_configure('excellent', background='#d4edda')
        self.tree.tag_configure('verygood', background='#d1ecf1')
        self.tree.tag_configure('good', background='#fff3cd')
        self.tree.tag_configure('fair', background='#ffe5d0')
        self.tree.tag_configure('poor', background='#f8d7da')
        self.tree.tag_configure('failed', background='#f5c6cb')
    
    def _setup_footer(self, parent):
        footer_frame = tk.Frame(parent, bg='white')
        footer_frame.pack(fill=tk.X, pady=(6, 0))
        
        self.stats_label = tk.Label(footer_frame, text="Ready to test", font=('Segoe UI', 9), fg='#666666', bg='white')
        self.stats_label.pack(side=tk.LEFT)
        
        export_csv_btn = tk.Button(footer_frame, text="CSV", command=self.export_csv, font=('Segoe UI', 8), bg='white', fg='#666666', relief=tk.FLAT, cursor='hand2')
        export_csv_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        export_json_btn = tk.Button(footer_frame, text="JSON", command=self.export_json, font=('Segoe UI', 8), bg='white', fg='#666666', relief=tk.FLAT, cursor='hand2')
        export_json_btn.pack(side=tk.RIGHT, padx=(0, 5))
    
    def _set_proxy_fields_state(self, state):
        for child in self.sites_text.master.master.winfo_children():
            if isinstance(child, tk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, (tk.Entry, ttk.Combobox)):
                        subchild.config(state=state)
    
    def toggle_proxy(self):
        if self.proxy_var.get():
            self._set_proxy_fields_state('normal')
            self.log_info("✅ Proxy enabled")
        else:
            self._set_proxy_fields_state('disabled')
            PingEngine.clear_proxy()
            self.log_info("✅ Proxy disabled")
    
    def set_v2ray_preset(self):
        self.proxy_var.set(True)
        self.proxy_type_var.set('socks5')
        self.proxy_host_var.set('127.0.0.1')
        self.proxy_port_var.set('10808')
        self._set_proxy_fields_state('normal')
        self.log_info("✅ v2ray/Hiddify preset applied (SOCKS5 127.0.0.1:10808)")
        messagebox.showinfo("Proxy Preset", 
            "✅ v2ray/Hiddify SOCKS5 proxy preset applied!\n\n"
            "Host: 127.0.0.1\n"
            "Port: 10808\n"
            "Type: SOCKS5\n\n"
            "Now select TCP or HTTP method and start test.")
    
    # ============================================================
    # Copy/Paste Functions
    # ============================================================
    
    def select_all(self, event=None):
        self.sites_text.tag_add('sel', '1.0', 'end')
        return 'break'
    
    def paste_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
            if text:
                self.sites_text.delete('1.0', tk.END)
                self.sites_text.insert('1.0', text)
                self.log_info("📋 Pasted from clipboard")
        except:
            messagebox.showinfo('Info', 'Nothing to paste or clipboard is empty')
    
    def paste_text(self, event=None):
        try:
            text = self.root.clipboard_get()
            if text:
                cursor_pos = self.sites_text.index(tk.INSERT)
                self.sites_text.insert(cursor_pos, text)
                return "break"
        except:
            pass
    
    def copy_from_log(self, event=None):
        try:
            selected = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
            return "break"
        except:
            pass
    
    def right_click_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="📋 Paste", command=self.paste_from_clipboard)
        menu.add_command(label="📝 Select All", command=self.select_all)
        menu.add_separator()
        menu.add_command(label="🗑️ Clear", command=lambda: self.sites_text.delete('1.0', tk.END))
        menu.post(event.x_root, event.y_root)
    
    def log_right_click(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="📋 Copy", command=lambda: self.copy_from_log())
        menu.add_command(label="📝 Select All", command=lambda: self.log_text.tag_add('sel', '1.0', 'end'))
        menu.add_separator()
        menu.add_command(label="🗑️ Clear", command=self.clear_log)
        menu.post(event.x_root, event.y_root)
    
    # ============================================================
    # Logging
    # ============================================================
    
    def log(self, message, tag='info'):
        self.log_queue.put((tag, message))
    
    def process_log_queue(self):
        count = 0
        while not self.log_queue.empty() and count < 20:
            tag, message = self.log_queue.get()
            self._append_log(message, tag)
            count += 1
        self.root.after(200, self.process_log_queue)
    
    def _append_log(self, message, tag):
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = f"[{timestamp}] {message}\n"
        
        if len(self.log_lines) >= self.max_log_lines:
            self.log_text.delete('1.0', '2.0')
            self.log_lines.pop(0)
        
        self.log_text.insert(tk.END, entry, tag)
        self.log_text.see(tk.END)
        self.log_lines.append(entry)
    
    def log_info(self, msg): self.log(msg, 'info')
    def log_success(self, msg): self.log(f"✅ {msg}", 'success')
    def log_error(self, msg): self.log(f"❌ {msg}", 'error')
    def log_warning(self, msg): self.log(f"⚠️ {msg}", 'warning')
    
    def clear_log(self):
        self.log_text.delete('1.0', tk.END)
        self.log_lines = []
    
    # ============================================================
    # About & Help
    # ============================================================
    
    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About Network Ping Pro")
        about_window.geometry("480x520")
        about_window.resizable(False, False)
        about_window.configure(bg='white')
        about_window.transient(self.root)
        about_window.grab_set()
        
        about_frame = tk.Frame(about_window, bg='white')
        about_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=25)
        
        tk.Label(about_frame, text="Network Ping Pro", font=('Segoe UI', 22, 'bold'), fg='black', bg='white').pack(pady=(0, 5))
        tk.Label(about_frame, text=f"Version {self.VERSION}", font=('Segoe UI', 10), fg='#666666', bg='white').pack(pady=(0, 15))
        
        tk.Label(about_frame, text="Developer:", font=('Segoe UI', 11, 'bold'), fg='black', bg='white').pack()
        tk.Label(about_frame, text=self.AUTHOR, font=('Segoe UI', 11), fg='#3498db', bg='white').pack(pady=(0, 10))
        
        methods_frame = tk.Frame(about_frame, bg='#f8f8f8', relief=tk.FLAT, bd=1)
        methods_frame.pack(fill=tk.X, pady=(0, 12))
        
        tk.Label(methods_frame, text="🔧 Testing Methods:", font=('Segoe UI', 10, 'bold'), fg='black', bg='#f8f8f8').pack(anchor='w', padx=10, pady=(5, 2))
        tk.Label(methods_frame, text="ICMP - Standard ping (no proxy)", font=('Segoe UI', 9), fg='#333', bg='#f8f8f8').pack(anchor='w', padx=15)
        tk.Label(methods_frame, text="TCP - Real TCP connection (socket)", font=('Segoe UI', 9), fg='#333', bg='#f8f8f8').pack(anchor='w', padx=15)
        tk.Label(methods_frame, text="HTTP - Real HTTP/HTTPS (curl)", font=('Segoe UI', 9), fg='#333', bg='#f8f8f8').pack(anchor='w', padx=15, pady=(0, 5))
        
        tk.Label(about_frame, text="🌐 Connect with me:", font=('Segoe UI', 11, 'bold'), fg='black', bg='white').pack(pady=(5, 8))
        
        links_frame = tk.Frame(about_frame, bg='white')
        links_frame.pack(pady=(0, 12))
        
        link_style = {'font': ('Segoe UI', 9), 'fg': '#3498db', 'bg': 'white', 'cursor': 'hand2', 'relief': tk.FLAT, 'pady': 3}
        
        for text, url in [
            ("🐦 X (Twitter)", "https://x.com/Erffanhub_00"),
            ("🐙 GitHub", "https://github.com/erffanhub-00"),
            ("📄 Gist", "https://gist.github.com/erffanhub-00")
        ]:
            btn = tk.Button(links_frame, text=text, command=lambda u=url: webbrowser.open(u), **link_style)
            btn.pack(fill=tk.X)
        
        close_btn = tk.Button(about_frame, text="Close", command=about_window.destroy, 
                             font=('Segoe UI', 10, 'bold'), bg='black', fg='white', 
                             relief=tk.FLAT, cursor='hand2', padx=20, pady=5)
        close_btn.pack(pady=(5, 0))
    
    def show_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - Network Ping Pro")
        help_window.geometry("550x640")
        help_window.resizable(False, False)
        help_window.configure(bg='white')
        help_window.transient(self.root)
        help_window.grab_set()
        
        help_frame = tk.Frame(help_window, bg='white')
        help_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        tk.Label(help_frame, text="📖 Help & Guide", font=('Segoe UI', 20, 'bold'), fg='black', bg='white').pack(pady=(0, 15))
        
        help_text = scrolledtext.ScrolledText(help_frame, height=22, font=('Segoe UI', 10), bg='#f8f9fa', fg='black', relief=tk.FLAT, bd=1)
        help_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        help_content = """
📌 HOW TO USE:

1. Enter targets (one per line or comma separated)
   Examples:
   • google.com (ICMP)
   • google.com:443 (TCP)
   • https://google.com/test (HTTP)
   • [::1]:8080 (IPv6)

2. Select Testing Method:
   • ICMP - Standard ping (fastest, no proxy)
   • TCP - Real TCP connection test (supports proxy)
   • HTTP - Real HTTP/HTTPS request (supports proxy)

3. Adjust Settings:
   • Pings: Number of tests (1-50)
   • Timeout: Max wait time per test (1-10s)
   • Workers: Concurrent tests (1-20)

4. Proxy Setup (for TCP/HTTP):
   • Enable "Use Proxy"
   • Choose type (http/https/socks5/socks4)
   • Enter host and port
   • Click preset button for v2ray/Hiddify

5. Click "Start Test" to begin

📊 RESULTS EXPLANATION:

• Score: Overall quality (0-100)
• Grade: Excellent / Very Good / Good / Fair / Poor
• Avg: Average response time
• Min/Max: Fastest/slowest response
• Jitter: Variation between responses
• P50/P95/P99: Percentile values
• Loss: Percentage of lost packets
• Status: OK / Failed / Timeout / Refused

⌨️ SHORTCUTS:

• Ctrl+A: Select all targets
• Ctrl+V: Paste from clipboard
• Ctrl+C: Copy from log (when selected)
• Right-click: Context menu

🔧 REQUIREMENTS:

• ICMP: None (built-in ping)
• TCP: None (built-in socket)
• HTTP: curl installed (https://curl.se/windows/)

💡 TIPS:

• For VPN/Proxy users, use TCP or HTTP method
• Higher Pings = more accurate results
• More Workers = faster testing
• Use preset button for v2ray/Hiddify (SOCKS5:10808)
• For accurate TCP tests, specify port (e.g., google.com:443)
"""
        help_text.insert('1.0', help_content)
        help_text.config(state=tk.DISABLED)
        
        close_btn = tk.Button(help_frame, text="Close", command=help_window.destroy, 
                             font=('Segoe UI', 10, 'bold'), bg='black', fg='white', 
                             relief=tk.FLAT, cursor='hand2', padx=25, pady=5)
        close_btn.pack()
    
    # ============================================================
    # Main Test Functions
    # ============================================================
    
    def start_test(self):
        if self.running:
            return
        
        sites_text = self.sites_text.get('1.0', tk.END).strip()
        if not sites_text:
            messagebox.showerror('Error', 'Please enter at least one target')
            return
        
        targets = TargetParser.parse_sites(sites_text)
        if not targets:
            messagebox.showerror('Error', 'No valid targets found')
            return
        
        try:
            count = max(1, min(50, int(self.count_var.get())))
        except:
            count = 10
        
        try:
            timeout = max(1, min(10, float(self.timeout_var.get())))
        except:
            timeout = 3
        
        try:
            workers = max(1, min(20, int(self.concurrent_var.get())))
        except:
            workers = 10
        
        method = self.method_var.get()
        
        if self.proxy_var.get():
            proxy_type = self.proxy_type_var.get()
            proxy_host = self.proxy_host_var.get().strip()
            proxy_port = self.proxy_port_var.get().strip()
            
            if proxy_host and proxy_port:
                try:
                    port = int(proxy_port)
                    PingEngine.set_proxy(proxy_type, proxy_host, port)
                    self.log_info(f"✅ Proxy set: {proxy_type}://{proxy_host}:{proxy_port}")
                except ValueError:
                    messagebox.showerror('Error', 'Invalid proxy port')
                    return
        else:
            PingEngine.clear_proxy()
        
        self.log_info("=" * 40)
        self.log_info(f"🚀 Starting: {len(targets)} targets, {count} pings, Method: {method}")
        if PingEngine.PROXY_TYPE:
            self.log_info(f"🔒 Using proxy: {PingEngine.PROXY_TYPE}://{PingEngine.PROXY_HOST}:{PingEngine.PROXY_PORT}")
        self.log_info("=" * 40)
        
        self.running = True
        self.stop_event.clear()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.clear_btn.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.progress_label.config(text="Starting...", fg='#f39c12')
        
        self.clear_results()
        
        self.current_test_thread = threading.Thread(
            target=self._run_test,
            args=(targets, count, timeout, method, workers)
        )
        self.current_test_thread.daemon = True
        self.current_test_thread.start()
    
    def stop_test(self):
        self.stop_event.set()
        self.log_warning("⏹ Stop requested")
        self.progress_label.config(text="Stopping...", fg='#e74c3c')
        self.stop_btn.config(state=tk.DISABLED)
    
    def _run_test(self, targets, count, timeout, method, workers):
        try:
            results = self._ping_all(targets, count, timeout, method, workers)
            self.root.after(0, self._display_results, results, len(targets))
        except Exception as e:
            self.log_error(f"❌ Error: {str(e)}")
            self.root.after(0, self._show_error, str(e))
    
    def _ping_all(self, targets, count, timeout, method, workers):
        results = []
        total = len(targets)
        completed = 0
        
        def ping_target(target):
            host = target['host']
            if self.stop_event.is_set():
                return PingResult(target=host, success=False, method='Cancelled', status='Cancelled')
            
            return PingEngine.ping_host(target, method, count, timeout, self.stop_event)
        
        with ThreadPoolExecutor(max_workers=min(workers, total)) as executor:
            futures = {executor.submit(ping_target, target): target for target in targets}
            
            for future in as_completed(futures):
                if self.stop_event.is_set():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                target = futures[future]
                try:
                    result = future.result(timeout=timeout+5)
                    result.target = target['host']
                    results.append(result)
                except Exception as e:
                    self.log_error(f"❌ {target['host']}: Error - {str(e)}")
                    results.append(PingResult(target=target['host'], success=False, method='Error', error=str(e)[:50], status='Error'))
                
                completed += 1
                progress = (completed / total) * 100
                self.root.after(0, self._update_progress, progress, completed, total)
        
        return results
    
    def _update_progress(self, progress, completed, total):
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"{completed}/{total}")
    
    def _display_results(self, results, total):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        success_count = 0
        failed_count = 0
        
        for r in results:
            if r.success:
                success_count += 1
            else:
                failed_count += 1
        
        # Sort by score (higher is better)
        successful = [r for r in results if r.success]
        successful_sorted = sorted(successful, key=lambda x: x.score if x.score else 0, reverse=True)
        
        for idx, r in enumerate(successful_sorted, 1):
            r.rank = idx
        
        for r in results:
            if not r.success:
                r.rank = None
        
        final_results = successful_sorted + [r for r in results if not r.success]
        self.results = final_results
        
        for r in final_results:
            rank_display = str(r.rank) if r.rank else '—'
            
            if r.success:
                score_val = f"{r.score:.1f}" if r.score is not None else '0'
                grade_val = r.grade or 'Unknown'
                avg_val = f"{r.avg:.1f}" if r.avg is not None else '—'
                min_val = f"{r.min:.1f}" if r.min is not None else '—'
                max_val = f"{r.max:.1f}" if r.max is not None else '—'
                jitter_val = f"{r.jitter:.1f}" if r.jitter is not None else '—'
                p50_val = f"{r.p50:.1f}" if r.p50 is not None else '—'
                p95_val = f"{r.p95:.1f}" if r.p95 is not None else '—'
                p99_val = f"{r.p99:.1f}" if r.p99 is not None else '—'
                loss_val = f"{r.packet_loss:.1f}" if r.packet_loss is not None else '0'
                status_display = r.status or 'OK'
                method_display = r.method or 'Unknown'
            else:
                score_val = '0'
                grade_val = 'Failed'
                avg_val = '—'
                min_val = '—'
                max_val = '—'
                jitter_val = '—'
                p50_val = '—'
                p95_val = '—'
                p99_val = '—'
                loss_val = '100.0'
                status_display = r.status or 'Failed'
                method_display = r.method or 'Failed'
            
            # Determine tag based on grade
            if r.success and r.grade:
                grade_lower = r.grade.lower()
                if 'excellent' in grade_lower:
                    tag = 'excellent'
                elif 'very good' in grade_lower:
                    tag = 'verygood'
                elif 'good' in grade_lower:
                    tag = 'good'
                elif 'fair' in grade_lower:
                    tag = 'fair'
                else:
                    tag = 'poor'
            else:
                tag = 'failed'
            
            self.tree.insert('', tk.END, values=(
                rank_display, r.target, method_display, score_val, grade_val,
                avg_val, min_val, max_val, jitter_val, p50_val, p95_val, p99_val,
                loss_val, status_display
            ), tags=(tag,))
        
        fastest = successful_sorted[0] if successful_sorted else None
        best_score = successful_sorted[0] if successful_sorted else None
        
        fastest_name = fastest.target if fastest else '—'
        fastest_avg = fastest.avg if fastest else 0
        best_name = best_score.target if best_score else '—'
        best_score_val = best_score.score if best_score else 0
        
        self.stats_label.config(
            text=f"📊 Total: {len(results)} | ✅ Success: {success_count} | ❌ Failed: {failed_count} | 🏆 Fastest: {fastest_name} ({fastest_avg:.1f}ms) | ⭐ Best: {best_name} ({best_score_val:.1f})"
        )
        
        self.log_info("=" * 40)
        self.log_info(f"✅ Done: {len(results)} targets, Success: {success_count}, Failed: {failed_count}")
        self.log_info(f"🏆 Fastest: {fastest_name} ({fastest_avg:.1f}ms)")
        self.log_info(f"⭐ Best: {best_name} ({best_score_val:.1f})")
        self.log_info("=" * 40)
        
        self._reset_ui()
    
    def _reset_ui(self):
        self.running = False
        self.start_btn.config(state=tk.NORMAL, text='Start Test')
        self.stop_btn.config(state=tk.DISABLED)
        self.clear_btn.config(state=tk.NORMAL)
        
        if self.stop_event.is_set():
            self.progress_label.config(text="⏹ Stopped", fg='#e74c3c')
        else:
            self.progress_label.config(text="✅ Done", fg='#2ecc71')
        self.progress_bar['value'] = 100
    
    def _show_error(self, error):
        messagebox.showerror('Error', f'❌ Error: {error}')
        self.log_error(f"❌ Error: {error}")
        self._reset_ui()
        self.progress_label.config(text='❌ Error', fg='#e74c3c')
    
    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results = []
        self.stats_label.config(text="🧹 Cleared")
    
    def clear_all(self):
        self.clear_results()
        self.progress_label.config(text="✅ Ready", fg='#2ecc71')
        self.progress_bar['value'] = 0
        self.log_info("🧹 Cleared")
    
    # ============================================================
    # Export Functions
    # ============================================================
    
    def export_csv(self):
        if not self.results:
            messagebox.showinfo('Info', 'No results to export')
            return
        
        try:
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files', '*.csv')])
            if not file_path:
                return
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Rank', 'Target', 'Method', 'Score', 'Grade', 'Avg', 'Min', 'Max', 'Jitter', 'P50', 'P95', 'P99', 'Loss %', 'Status'])
                
                for r in self.results:
                    writer.writerow([
                        r.rank or '—', r.target, r.method,
                        r.score if r.success else '0',
                        r.grade if r.success else 'Failed',
                        r.avg if r.success else '—',
                        r.min if r.success else '—',
                        r.max if r.success else '—',
                        r.jitter if r.success else '—',
                        r.p50 if r.success else '—',
                        r.p95 if r.success else '—',
                        r.p99 if r.success else '—',
                        r.packet_loss if r.success else '100.0',
                        r.status
                    ])
            
            self.log_success(f"📤 Exported to {file_path}")
            messagebox.showinfo('Success', f'Exported to {file_path}')
        except Exception as e:
            self.log_error(f"Export failed: {e}")
            messagebox.showerror('Error', f'Export failed: {e}')
    
    def export_json(self):
        if not self.results:
            messagebox.showinfo('Info', 'No results to export')
            return
        
        try:
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON files', '*.json')])
            if not file_path:
                return
            
            export_data = {
                'version': self.VERSION,
                'timestamp': datetime.now().isoformat(),
                'total': len(self.results),
                'results': [
                    {
                        'rank': r.rank,
                        'target': r.target,
                        'method': r.method,
                        'score': r.score,
                        'grade': r.grade,
                        'avg': r.avg,
                        'min': r.min,
                        'max': r.max,
                        'jitter': r.jitter,
                        'p50': r.p50,
                        'p95': r.p95,
                        'p99': r.p99,
                        'packet_loss': r.packet_loss,
                        'status': r.status,
                        'error': r.error,
                        'dns_time': r.dns_time,
                        'connect_time': r.connect_time,
                        'http_status': r.http_status
                    } for r in self.results
                ]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.log_success(f"📤 Exported to {file_path}")
            messagebox.showinfo('Success', f'Exported to {file_path}')
        except Exception as e:
            self.log_error(f"Export failed: {e}")
            messagebox.showerror('Error', f'Export failed: {e}')
    
    def save_log(self):
        if not self.log_lines:
            messagebox.showinfo('Info', 'No log to save')
            return
        
        try:
            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(defaultextension='.log', filetypes=[('Log files', '*.log')])
            if not file_path:
                return
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(self.log_lines)
            
            self.log_success(f"📤 Log saved to {file_path}")
            messagebox.showinfo('Success', f'Log saved to {file_path}')
        except Exception as e:
            self.log_error(f"Save log failed: {e}")
            messagebox.showerror('Error', f'Save log failed: {e}')


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == '__main__':
    root = tk.Tk()
    app = NetworkPingPro(root)
    root.mainloop()
