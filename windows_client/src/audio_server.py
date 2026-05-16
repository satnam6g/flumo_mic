"""
audio_server.py - UDP audio receiver + PyAudio playback backend.
Designed to be driven by the GUI (main.py) via callbacks and threading events.

Audio format: 48000 Hz, 16-bit signed PCM, Mono
"""

import socket
import threading
import queue
import time
import logging
import struct
import hashlib
from typing import Callable, Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# ── Audio Configuration ────────────────────────────────────────────────────────
SAMPLE_RATE    = 48000
CHANNELS       = 1
SAMPLE_WIDTH   = 2          # 16-bit = 2 bytes per sample
CHUNK_SAMPLES  = 2400       # samples per chunk  → 100 ms of audio
CHUNK_BYTES    = CHUNK_SAMPLES * SAMPLE_WIDTH   # 4800 bytes

# ── Network Configuration ──────────────────────────────────────────────────────
UDP_PORT       = 55555
SOCKET_TIMEOUT = 0.5        # seconds

# ── Buffer Configuration ───────────────────────────────────────────────────────
MAX_QUEUE_DEPTH = 50        # ~5 seconds of audio

# Connection timeout: if no packet for this many seconds, mark disconnected
CONN_TIMEOUT = 3.0


def _find_vbcable_index(pa) -> Optional[int]:
    """Return PyAudio device index for VB-Cable Input, or None."""
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info.get("name", "").lower()
        if "cable input" in name or "vb-audio" in name or "vbcable" in name:
            if info.get("maxOutputChannels", 0) > 0:
                return i
    return None


def rms_from_pcm(data: bytes) -> float:
    """Calculate RMS amplitude from 16-bit PCM bytes, normalised to 0.0–1.0."""
    if not data:
        return 0.0
    n = len(data) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", data[:n * 2])
    rms = (sum(s * s for s in samples) / n) ** 0.5
    return min(rms / 32768.0, 1.0)


class AudioServer:
    """
    Manages UDP listener + PyAudio playback in background threads.
    Provides callbacks for the GUI:
        on_connect(addr: str)
        on_disconnect()
        on_level(rms: float)       # 0.0–1.0
        on_log(msg: str)
        on_stats(stats: dict)
    """

    def __init__(
        self,
        pin:           str                      = "",
        on_connect:    Callable[[str], None]    = None,
        on_disconnect: Callable[[], None]       = None,
        on_level:      Callable[[float], None]  = None,
        on_log:        Callable[[str], None]    = None,
        on_stats:      Callable[[dict], None]   = None,
        use_vbcable:   bool                     = True,
    ):
        self._pin           = pin
        self._on_connect    = on_connect    or (lambda a: None)
        self._on_disconnect = on_disconnect or (lambda: None)
        self._on_level      = on_level      or (lambda l: None)
        self._on_log        = on_log        or logger.info
        self._on_stats      = on_stats      or (lambda s: None)
        self._use_vbcable   = use_vbcable

        self._running       = threading.Event()
        self._audio_queue   = queue.Queue(maxsize=MAX_QUEUE_DEPTH)
        self._connected     = False
        self._last_addr     = ""

        self._stats_lock    = threading.Lock()
        self._stats         = {
            "packets_received":  0,
            "packets_dropped":   0,
            "packets_played":    0,
            "bytes_received":    0,
            "start_time":        0.0,
            "last_packet_time":  0.0,
        }

        self._listener_thread: Optional[threading.Thread] = None
        self._player_thread:   Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None

    # ── Public API ──────────────────────────────────────────────────────────────

    def start(self):
        if self._running.is_set():
            return
        self._running.set()
        self._stats["start_time"] = time.time()
        self._audio_queue = queue.Queue(maxsize=MAX_QUEUE_DEPTH)

        self._listener_thread = threading.Thread(
            target=self._udp_listener, name="UDPListener", daemon=True
        )
        self._player_thread = threading.Thread(
            target=self._audio_player, name="AudioPlayer", daemon=True
        )
        self._watchdog_thread = threading.Thread(
            target=self._watchdog, name="Watchdog", daemon=True
        )

        self._listener_thread.start()
        self._player_thread.start()
        self._watchdog_thread.start()
        self._log(f"Server started — listening on UDP port {UDP_PORT}")

    def stop(self):
        if not self._running.is_set():
            return
        self._running.clear()
        self._log("Server stopped.")
        if self._connected:
            self._connected = False
            try:
                self._on_disconnect()
            except Exception:
                pass

    def is_running(self) -> bool:
        return self._running.is_set()

    def get_stats(self) -> dict:
        with self._stats_lock:
            s = dict(self._stats)
        s["queue_depth"] = self._audio_queue.qsize()
        s["uptime"] = time.time() - s["start_time"] if s["start_time"] else 0
        return s

    @property
    def use_vbcable(self) -> bool:
        return self._use_vbcable

    @use_vbcable.setter
    def use_vbcable(self, value: bool):
        self._use_vbcable = value

    # ── Internal Threads ───────────────────────────────────────────────────────

    def _udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024)
        except OSError:
            pass
        sock.settimeout(SOCKET_TIMEOUT)

        try:
            sock.bind(("0.0.0.0", UDP_PORT))
        except OSError as e:
            self._log(f"[ERROR] Cannot bind to port {UDP_PORT}: {e}")
            self._running.clear()
            return

        self._log(f"[UDP] Listening on 0.0.0.0:{UDP_PORT}")

        while self._running.is_set():
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError as e:
                if self._running.is_set():
                    self._log(f"[UDP] Socket error: {e}")
                break

            now = time.time()
            
            if self._pin and len(data) > 16:
                try:
                    iv = data[:16]
                    ciphertext = data[16:]
                    key = hashlib.sha256(self._pin.encode('utf-8')).digest()
                    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
                    decryptor = cipher.decryptor()
                    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
                    
                    unpadder = padding.PKCS7(128).unpadder()
                    data = unpadder.update(padded_data) + unpadder.finalize()
                except Exception as e:
                    # Decryption failed (wrong PIN or corrupted)
                    try:
                        sock.sendto(b"ERROR:WRONG_PIN", addr)
                    except Exception:
                        pass
                    continue
                    
            with self._stats_lock:
                self._stats["packets_received"] += 1
                self._stats["bytes_received"] += len(data)
                self._stats["last_packet_time"] = now

            addr_str = f"{addr[0]}:{addr[1]}"
            if not self._connected or addr_str != self._last_addr:
                self._connected = True
                self._last_addr = addr_str
                try:
                    self._on_connect(addr[0])
                except Exception:
                    pass

            # RMS level for meter
            try:
                self._on_level(rms_from_pcm(data))
            except Exception:
                pass

            try:
                self._audio_queue.put_nowait(data)
            except queue.Full:
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._audio_queue.put_nowait(data)
                except queue.Full:
                    pass
                with self._stats_lock:
                    self._stats["packets_dropped"] += 1

        sock.close()
        self._log("[UDP] Listener stopped.")

    def _audio_player(self):
        try:
            import pyaudio
        except ImportError:
            self._log("[ERROR] PyAudio not installed. pip install pyaudio")
            self._running.clear()
            return

        pa = pyaudio.PyAudio()
        device_index = None

        if self._use_vbcable:
            device_index = _find_vbcable_index(pa)
            if device_index is not None:
                info = pa.get_device_info_by_index(device_index)
                self._log(f"[AUDIO] Using VB-Cable: {info['name']}")
            else:
                self._log("[AUDIO] VB-Cable not found — using default output.")

        try:
            default_info = pa.get_default_output_device_info()
            self._log(f"[AUDIO] Output: {default_info['name']} @ {SAMPLE_RATE} Hz")
        except IOError:
            self._log("[ERROR] No audio output device found.")
            self._running.clear()
            pa.terminate()
            return

        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                output_device_index=device_index,
                frames_per_buffer=CHUNK_SAMPLES,
            )
        except IOError as e:
            self._log(f"[ERROR] Failed to open audio stream: {e}")
            self._running.clear()
            pa.terminate()
            return

        silence = b"\x00" * CHUNK_BYTES
        self._log("[AUDIO] Playback stream opened.")

        while self._running.is_set():
            try:
                data = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                try:
                    stream.write(silence)
                except IOError:
                    pass
                continue

            try:
                stream.write(data)
                with self._stats_lock:
                    self._stats["packets_played"] += 1
            except IOError as e:
                self._log(f"[AUDIO] Write error: {e}")

        stream.stop_stream()
        stream.close()
        pa.terminate()
        self._log("[AUDIO] Playback stopped.")

    def _watchdog(self):
        """Detects connection timeout and fires on_disconnect."""
        while self._running.is_set():
            time.sleep(1.0)
            if not self._connected:
                continue
            with self._stats_lock:
                last = self._stats["last_packet_time"]
            if last > 0 and (time.time() - last) > CONN_TIMEOUT:
                self._connected = False
                self._log("[WATCHDOG] Connection timed out.")
                try:
                    self._on_disconnect()
                except Exception:
                    pass
                try:
                    self._on_level(0.0)
                except Exception:
                    pass
            # Emit stats every 2s
            try:
                self._on_stats(self.get_stats())
            except Exception:
                pass

    def _log(self, msg: str):
        logger.debug(msg)
        try:
            self._on_log(msg)
        except Exception:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    srv = AudioServer(
        on_log=print,
        on_connect=lambda a: print(f"Connected: {a}"),
        on_disconnect=lambda: print("Disconnected"),
        on_level=lambda l: print(f"Level: {l:.2f}"),
    )
    srv.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()
