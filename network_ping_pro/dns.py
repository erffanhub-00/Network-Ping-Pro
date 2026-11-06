"""DNS resolution with a timeout guard."""

import socket
import threading
import time
from typing import Any, Dict, Optional, Tuple


class DNSResolver:
    """
    DNS resolver with a timeout guard.

    Note: socket.getaddrinfo() cannot be interrupted mid-call. This
    function uses a daemon thread and joins with a timeout, so from the
    caller's perspective the resolution "gives up" after `timeout` seconds.
    The thread itself may keep running until getaddrinfo returns; it only
    writes its result once, under a lock, so a late write cannot race
    with the caller's read.
    """

    @staticmethod
    def resolve(host: str, timeout: float = 5.0
                ) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """
        Returns (ip, family, elapsed_ms, error).
        family is 'IPv4' or 'IPv6'.
        """
        result: Dict[str, Any] = {'ip': None, 'family': None, 'elapsed': None, 'error': None}
        lock = threading.Lock()

        def worker():
            local: Dict[str, Any] = {'ip': None, 'family': None, 'elapsed': None, 'error': None}
            try:
                start = time.perf_counter()
                infos = socket.getaddrinfo(host, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                elapsed = (time.perf_counter() - start) * 1000
                local['elapsed'] = round(elapsed, 1)

                if not infos:
                    local['error'] = 'No addresses'
                else:
                    chosen = None
                    for info in infos:
                        if info[0] == socket.AF_INET:
                            chosen = info
                            break
                    if chosen is None:
                        chosen = infos[0]

                    local['ip'] = chosen[4][0]
                    local['family'] = 'IPv4' if chosen[0] == socket.AF_INET else 'IPv6'
            except socket.gaierror as e:
                local['error'] = str(e)
            except Exception as e:
                local['error'] = str(e)
            finally:
                with lock:
                    result.update(local)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout)

        if t.is_alive():
            return None, None, None, f'DNS timeout after {timeout}s'

        return result['ip'], result['family'], result['elapsed'], result['error']
