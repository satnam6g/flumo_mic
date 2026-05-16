"""
ip_detector.py - Auto-detects the best LAN IP address for the Wireless Mic client.
Prefers Wi-Fi / Ethernet over loopback. Monitors for network changes.
"""

import socket
import threading
import time
import logging

logger = logging.getLogger(__name__)


def _get_all_ips() -> list[dict]:
    """Return all non-loopback IPv4 addresses with interface hints."""
    import subprocess, re
    results = []

    # Primary method: connect trick to find default outbound IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        results.append({"ip": primary, "priority": 0, "label": "Default Route"})
    except Exception:
        pass

    # Secondary: enumerate all interfaces via hostname resolution
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip.startswith("127.") or ":" in ip:
                continue
            if not any(r["ip"] == ip for r in results):
                results.append({"ip": ip, "priority": 1, "label": "Host Alias"})
    except Exception:
        pass

    # Tertiary: ipconfig parsing for interface labels
    try:
        out = subprocess.check_output(
            ["ipconfig"], text=True, creationflags=0x08000000
        )
        current_adapter = "Unknown"
        for line in out.splitlines():
            line = line.strip()
            if line.endswith(":") and not line.startswith(" "):
                current_adapter = line.rstrip(":")
            match = re.match(r"IPv4 Address[.\s]+:\s+(\d+\.\d+\.\d+\.\d+)", line)
            if match:
                ip = match.group(1)
                if not ip.startswith("127.") and not any(r["ip"] == ip for r in results):
                    results.append({"ip": ip, "priority": 2, "label": current_adapter})
    except Exception:
        pass

    return results


def get_best_ip() -> str:
    """Return the best available LAN IP, preferring default-route IPs."""
    ips = _get_all_ips()
    if not ips:
        return "127.0.0.1"
    ips.sort(key=lambda x: x["priority"])
    return ips[0]["ip"]


def get_all_ips() -> list[str]:
    """Return all non-loopback IPs, deduplicated."""
    seen = set()
    result = []
    for entry in _get_all_ips():
        ip = entry["ip"]
        if ip not in seen:
            seen.add(ip)
            result.append(ip)
    return result or ["127.0.0.1"]


class IPChangeMonitor(threading.Thread):
    """
    Background thread that polls for IP address changes every `interval` seconds.
    Calls `callback(new_ip: str)` when the primary IP changes.
    """

    def __init__(self, callback, interval: float = 5.0):
        super().__init__(daemon=True, name="IPMonitor")
        self._callback = callback
        self._interval = interval
        self._stop_event = threading.Event()
        self._last_ip = get_best_ip()

    def run(self):
        logger.debug("IP monitor started (interval=%.1fs)", self._interval)
        while not self._stop_event.wait(self._interval):
            try:
                current = get_best_ip()
                if current != self._last_ip:
                    logger.info("IP changed: %s → %s", self._last_ip, current)
                    self._last_ip = current
                    try:
                        self._callback(current)
                    except Exception as e:
                        logger.error("IP change callback error: %s", e)
            except Exception as e:
                logger.error("IP monitor error: %s", e)

    def stop(self):
        self._stop_event.set()


if __name__ == "__main__":
    print("All detected IPs:", get_all_ips())
    print("Best IP:", get_best_ip())
