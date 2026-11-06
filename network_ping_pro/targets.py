"""Parsing and validation of test targets.

A target may be a hostname, host:port, URL, or [IPv6]:port. Anything
that could be interpreted as a program option (e.g. a host starting
with '-') is rejected, so a targets file can never inject ping options.
"""

import re
import socket
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class TargetParser:
    # Targets dropped by the last parse_sites() call (invalid input).
    last_skipped: List[str] = []

    @staticmethod
    def _valid_host(host: str) -> bool:
        """Reject option-like hosts and invalid characters."""
        if not host or host.startswith('-') or host.startswith('.'):
            return False
        if any(c.isspace() or ord(c) < 32 for c in host):
            return False
        return re.fullmatch(r'[A-Za-z0-9._:-]+', host) is not None

    @staticmethod
    def parse_target(value: str) -> Optional[Dict[str, Any]]:
        try:
            value = value.strip()
            if not value:
                return None

            if value.startswith('['):
                m = re.match(r'\[([0-9a-fA-F:]+)\](?::(\d+))?$', value)
                if not m:
                    return None
                try:
                    socket.inet_pton(socket.AF_INET6, m.group(1))
                except OSError:
                    return None
                port = int(m.group(2)) if m.group(2) else None
                if port is not None and not 1 <= port <= 65535:
                    return None
                return {
                    'host': m.group(1),
                    'port': port,
                    'scheme': None,
                    'path': '/',
                    'query': '',
                    'raw': value,
                }

            parsed = urlparse(value if '://' in value else '//' + value)
            host = parsed.hostname
            if not host or not TargetParser._valid_host(host):
                return None
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                return None

            return {
                'host': host.lower(),
                'port': parsed.port,
                'scheme': parsed.scheme or None,
                'path': parsed.path or '/',
                'query': parsed.query or '',
                'raw': value,
            }
        except Exception:
            return None

    @staticmethod
    def parse_sites(text: str) -> List[Dict[str, Any]]:
        seen = set()
        out: List[Dict[str, Any]] = []
        skipped: List[str] = []
        for chunk in text.replace('،', ',').replace('\n', ',').split(','):
            parsed = TargetParser.parse_target(chunk)
            if not parsed:
                if chunk.strip():
                    skipped.append(chunk.strip())
                continue
            key = (
                parsed['scheme'],
                parsed['host'],
                parsed['port'],
                parsed['path'],
                parsed['query'],
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(parsed)
        TargetParser.last_skipped = skipped
        return out
