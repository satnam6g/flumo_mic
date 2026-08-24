"""
audio_server.py - UDP audio receiver + PyAudio playback backend. (v2.0)
Driven by the GUI (main.py) via callbacks and threading events.

Audio format : 48000 Hz, 16-bit signed PCM, Mono
Packet v2    : b"WM" + ver(1B)=0x02 + seq(u32 LE) + ts_ms(u32 LE) + IV(16) + AES-CBC ciphertext
Packet v1    : IV(16) + ciphertext                       (legacy, still accepted)
Control      : plain-text "HEARTBEAT" / "CMD:STOP" / "ERROR:WRONG_PIN"

Features: multi-sender mixing, sequence loss/jitter stats, noise gate,
gain, mute, live monitor, WAV recording.
"""

import socket
import threading
import queue
import time
import wave
import struct
import hashlib
import logging
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

# Connection timeout: if no packet for this many seconds, sender is dropped
CONN_TIMEOUT = 3.0

# Noise-gate hold time: keep gate open this long after signal drops below threshold
GATE_HOLD = 0.3

PACKET_MAGIC   = b"WM"
PACKET_VERSION = 2
HEADER_LEN     = 2 + 1 + 4 + 4          # magic + ver + seq + ts


def _find_vbcable_index(pa) -> Optional[int]:
    """Return PyAudio device index for VB-Cable Input, or None."""
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info.get("name", "").lower()
        if "cable input" in name or "vb-audio" in name or "vbcable" in name:
            if info.get("maxOutputChannels", 0) > 0:
                return i
    return None


def _find_monitor_index(pa) -> Optional[int]:
    """Return PyAudio device index of the default output device, or None."""
    try:
        return pa.get_default_output_device_info()["index"]
    except Exception:
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


def apply_gain(data: bytes, gain: float) -> bytes:
    """Multiply 16-bit PCM samples by gain, clipping to int16 range."""
    if gain == 1.0 or not data:
        return data
    n = len(data) // 2
    samples = struct.unpack(f"<{n}h", data[:n * 2])
    peak = 32767.0
    out = bytearray(len(data))
    for i, s in enumerate(samples):
        v = int(s * gain)
        if v > 32767:   v = 32767
        elif v < -32768: v = -32768
        struct.pack_into("<h", out, i * 2, v)
    del peak
    return bytes(out)


def parse_packet(data: bytes):
    """Split raw datagram into (seq, ts_ms, payload). Legacy packets → (None, None, data)."""
    if len(data) >= HEADER_LEN + 16 and data[:2] == PACKET_MAGIC and data[2] == PACKET_VERSION:
        seq = int.from_bytes(data[3:7], "little")
        ts  = int.from_bytes(data[7:11], "little")
        return seq, ts, data[HEADER_LEN:]
    return None, None, data


class AudioServer:
    """
    Manages UDP listener + PyAudio playback in background threads.
    Supports multiple simultaneous senders (mixed into one stream).

    Provides callbacks for the GUI:
        on_connect(addr: str)
        on_disconnect()
        on_level(rms: float)       # 0.0–1.0 (post-gate)
        on_log(msg: str)
        on_stats(stats: dict)
        on_vbcable_missing()
    """

    def __init__(
        self,
        pin:           str                      = "",
        on_connect:    Callable[[str], None]    = None,
        on_disconnect: Callable[[], None]       = None,
        on_level:      Callable[[float], None]  = None,
        on_log:        Callable[[str], None]    = None,
        on_stats:      Callable[[dict], None]   = None,
        on_vbcable_missing: Callable[[], None]  = None,
    ):
        self._pin           = pin
        self._on_connect    = on_connect    or (lambda a: None)
        self._on_disconnect = on_disconnect or (lambda: None)
        self._on_level      = on_level      or (lambda l: None)
        self._on_log        = on_log        or logger.info
        self._on_stats      = on_stats      or (lambda s: None)
        self._on_vbcable_missing = on_vbcable_missing or (lambda: None)

        self._running       = threading.Event()
        self._audio_queue   = queue.Queue(maxsize=MAX_QUEUE_DEPTH)
        self._connected     = False
        self._last_addr     = ""           # "ip:port" string (primary sender, for STOP)
        self._last_addr_tuple = None
        self._sock          = None

        # ── DSP state ──
        self._dsp_lock      = threading.Lock()
        self._gain          = 1.0
        self._gate_threshold = 0.0         # 0.0 = gate off
        self._mute          = False
        self._monitor       = False

        # ── Multi-sender tracking: addr_tuple → state dict ──
        self._senders       = {}
        self._senders_lock  = threading.Lock()

        # ── Recording state ──
        self._rec_wf        = None         # wave file object
        self._rec_lock      = threading.Lock()
        self._rec_start     = 0.0

        # ── Stats ──
        self._stats_lock    = threading.Lock()
        self._stats         = {
            "packets_received":  0,
            "packets_dropped":   0,
            "packets_played":    0,
            "packets_lost":      0,
            "bytes_received":    0,
            "start_time":        0.0,
            "last_packet_time":  0.0,
            "jitter_ms":         0.0,
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
        with self._senders_lock:
            self._senders.clear()

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
        if self._recording():
            self.stop_recording()
        # Send STOP command to connected Android device(s)
        self._send_stop_to_phone()
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

    # ── DSP setters (thread-safe) ──

    def set_gain(self, gain: float):
        with self._dsp_lock:
            self._gain = max(0.0, min(gain, 4.0))

    def set_noise_gate(self, threshold: float):
        with self._dsp_lock:
            self._gate_threshold = max(0.0, min(threshold, 1.0))

    def set_mute(self, mute: bool):
        with self._dsp_lock:
            self._mute = bool(mute)

    def set_monitor(self, monitor: bool):
        with self._dsp_lock:
            self._monitor = bool(monitor)

    # ── Recording API ──

    def _recording(self) -> bool:
        with self._rec_lock:
            return self._rec_wf is not None

    def start_recording(self, path: str) -> bool:
        with self._rec_lock:
            if self._rec_wf is not None:
                return False
            try:
                self._rec_wf = wave.open(path, "wb")
                self._rec_wf.setnchannels(CHANNELS)
                self._rec_wf.setsampwidth(SAMPLE_WIDTH)
                self._rec_wf.setframerate(SAMPLE_RATE)
                self._rec_start = time.time()
                self._log(f"[REC] Recording to {path}")
                return True
            except Exception as e:
                self._rec_wf = None
                self._log(f"[REC] Failed to start: {e}")
                return False

    def stop_recording(self) -> float:
        """Stop recording, return duration in seconds."""
        with self._rec_lock:
            if self._rec_wf is None:
                return 0.0
            dur = time.time() - self._rec_start
            try:
                self._rec_wf.close()
            except Exception:
                pass
            self._rec_wf = None
            self._log(f"[REC] Saved ({dur:.1f}s)")
            return dur

    def get_stats(self) -> dict:
        with self._stats_lock:
            s = dict(self._stats)
        with self._senders_lock:
            s["senders"] = len(self._senders)
        s["queue_depth"] = self._audio_queue.qsize()
        s["uptime"] = time.time() - s["start_time"] if s["start_time"] else 0
        s["recording"] = self._recording()
        total = s["packets_received"] + s["packets_lost"]
        s["loss_pct"] = (s["packets_lost"] / total * 100.0) if total else 0.0
        return s

    def _send_stop_to_phone(self):
        """Send CMD:STOP to the last connected Android device."""
        if self._last_addr_tuple and self._sock:
            try:
                self._sock.sendto(b"CMD:STOP", self._last_addr_tuple)
                self._log(f"[SYNC] Sent stop command to {self._last_addr_tuple[0]}")
            except Exception:
                pass

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

        self._sock = sock
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

            # Plain-text control messages
            try:
                text = data.decode("utf-8", errors="strict")
                if text == "HEARTBEAT":
                    with self._stats_lock:
                        self._stats["last_packet_time"] = now
                    self._touch_sender(addr, now)
                    continue
                # other text → ignore
                continue
            except (UnicodeDecodeError, ValueError):
                pass

            # ── Header parse (seq/ts) ──
            seq, ts, payload = parse_packet(data)

            # ── Decrypt ──
            if self._pin and len(payload) > 16:
                try:
                    iv = payload[:16]
                    ciphertext = payload[16:]
                    key = hashlib.sha256(self._pin.encode("utf-8")).digest()
                    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
                    decryptor = cipher.decryptor()
                    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
                    unpadder = padding.PKCS7(128).unpadder()
                    data = unpadder.update(padded_data) + unpadder.finalize()
                except Exception:
                    try:
                        sock.sendto(b"ERROR:WRONG_PIN", addr)
                    except Exception:
                        pass
                    continue

            sender_state = self._touch_sender(addr, now)
            self._update_seq_stats(sender_state, seq, ts, now)

            with self._stats_lock:
                self._stats["packets_received"] += 1
                self._stats["bytes_received"] += len(data)
                self._stats["last_packet_time"] = now

            addr_str = f"{addr[0]}:{addr[1]}"
            if not self._connected:
                self._connected = True
                self._last_addr = addr_str
                self._last_addr_tuple = addr
                try:
                    self._on_connect(addr[0])
                except Exception:
                    pass
            elif addr_str == self._last_addr:
                self._last_addr_tuple = addr

            # ── DSP chain: gate → gain → mute ──
            rms = rms_from_pcm(data)
            processed = self._process_pcm(data, sender_state, rms, now)

            # Level meter shows post-gate level
            try:
                self._on_level(rms if processed is not None else 0.0)
            except Exception:
                pass

            if processed is not None:
                # Recording taps the processed stream
                with self._rec_lock:
                    if self._rec_wf is not None:
                        try:
                            self._rec_wf.writeframes(processed)
                        except Exception:
                            pass

                try:
                    self._audio_queue.put_nowait(processed)
                except queue.Full:
                    try:
                        self._audio_queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._audio_queue.put_nowait(processed)
                    except queue.Full:
                        pass
                    with self._stats_lock:
                        self._stats["packets_dropped"] += 1

        self._sock = None
        sock.close()
        self._log("[UDP] Listener stopped.")

    def _touch_sender(self, addr, now) -> dict:
        key = (addr[0], addr[1])
        with self._senders_lock:
            st = self._senders.get(key)
            if st is None:
                st = {"ip": addr[0], "last_seen": now, "last_seq": None,
                      "last_ts": None, "lost": 0, "recv": 0,
                      "jitter": 0.0, "gate_last_above": 0.0}
                self._senders[key] = st
                self._log(f"[UDP] New sender {addr[0]}:{addr[1]} "
                          f"({len(self._senders)} active)")
            else:
                st["last_seen"] = now
            return st

    def _update_seq_stats(self, st: dict, seq, ts, now):
        if seq is None:
            return
        if st["last_seq"] is not None:
            expected = (st["last_seq"] + 1) & 0xFFFFFFFF
            if seq > expected:
                lost = seq - expected
                st["lost"] += lost
                with self._stats_lock:
                    self._stats["packets_lost"] += lost
            # Inter-arrival jitter (simplified RFC3550)
            if st["last_ts"] is not None:
                arrival_d = (now - st["last_seen"]) * 1000.0
                ts_d = float((ts - st["last_ts"]) & 0xFFFFFFFF)
                if 0 < ts_d < 5000:
                    delta = abs(arrival_d - ts_d)
                    st["jitter"] += (delta - st["jitter"]) / 16.0
                    with self._stats_lock:
                        self._stats["jitter_ms"] = round(
                            (st["jitter"]), 1)
        st["last_seq"] = seq
        st["last_ts"] = ts
        st["recv"] += 1

    def _process_pcm(self, data: bytes, st: dict, rms: float, now: float):
        """Gate → gain → mute. Returns processed bytes or None to drop."""
        with self._dsp_lock:
            mute = self._mute
            gain = self._gain
            gate_th = self._gate_threshold

        if mute:
            return None

        if gate_th > 0.0:
            if rms >= gate_th:
                st["gate_last_above"] = now
            elif (now - st["gate_last_above"]) > GATE_HOLD:
                return None  # gated out

        if gain != 1.0:
            data = apply_gain(data, gain)
        return data

    def _audio_player(self):
        try:
            import pyaudio
        except ImportError:
            self._log("[ERROR] PyAudio not installed. pip install pyaudio")
            self._running.clear()
            return

        pa = pyaudio.PyAudio()

        # VB-Cable is REQUIRED — never fall back to speakers
        device_index = _find_vbcable_index(pa)
        if device_index is not None:
            info = pa.get_device_info_by_index(device_index)
            self._log(f"[AUDIO] Using VB-Cable: {info['name']}")
        else:
            self._log("[ERROR] VB-Cable not found! Audio will NOT play through speakers.")
            self._log("[ERROR] Install VB-Audio Virtual Cable from https://vb-audio.com/Cable/")
            self._running.clear()
            pa.terminate()
            try:
                self._on_vbcable_missing()
            except Exception:
                pass
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

        monitor_stream = None
        silence = b"\x00" * CHUNK_BYTES
        self._log("[AUDIO] Playback stream opened.")

        while self._running.is_set():
            # Lazily open/close the monitor stream
            with self._dsp_lock:
                want_monitor = self._monitor
            if want_monitor and monitor_stream is None:
                try:
                    mon_idx = _find_monitor_index(pa)
                    if mon_idx is not None:
                        monitor_stream = pa.open(
                            format=pyaudio.paInt16, channels=CHANNELS,
                            rate=SAMPLE_RATE, output=True,
                            output_device_index=mon_idx,
                            frames_per_buffer=CHUNK_SAMPLES,
                        )
                        self._log("[AUDIO] Monitor ON (default output)")
                except IOError as e:
                    self._log(f"[AUDIO] Monitor open failed: {e}")
                    with self._dsp_lock:
                        self._monitor = False
            elif not want_monitor and monitor_stream is not None:
                try:
                    monitor_stream.stop_stream(); monitor_stream.close()
                except Exception:
                    pass
                monitor_stream = None
                self._log("[AUDIO] Monitor OFF")

            try:
                data = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                try:
                    stream.write(silence)
                    if monitor_stream is not None:
                        monitor_stream.write(silence)
                except IOError:
                    pass
                continue

            try:
                stream.write(data)
                if monitor_stream is not None:
                    try:
                        monitor_stream.write(data)
                    except IOError:
                        pass
                with self._stats_lock:
                    self._stats["packets_played"] += 1
            except IOError as e:
                self._log(f"[AUDIO] Write error: {e}")

        if monitor_stream is not None:
            try:
                monitor_stream.stop_stream(); monitor_stream.close()
            except Exception:
                pass
        stream.stop_stream()
        stream.close()
        pa.terminate()
        self._log("[AUDIO] Playback stopped.")

    def _watchdog(self):
        """Detects sender timeouts; disconnect only when ALL senders are stale."""
        while self._running.is_set():
            time.sleep(1.0)
            now = time.time()
            with self._senders_lock:
                stale = [k for k, st in self._senders.items()
                         if (now - st["last_seen"]) > CONN_TIMEOUT]
                for k in stale:
                    ip = self._senders[k]["ip"]
                    del self._senders[k]
                    self._log(f"[WATCHDOG] Sender {ip} timed out.")
                active = len(self._senders)
            if self._connected and active == 0:
                self._connected = False
                self._log("[WATCHDOG] All senders disconnected.")
                self._send_stop_to_phone()
                try:
                    self._on_disconnect()
                except Exception:
                    pass
                try:
                    self._on_level(0.0)
                except Exception:
                    pass
            # Emit stats every second
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
