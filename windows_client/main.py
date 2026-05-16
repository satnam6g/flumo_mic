"""
Wireless Microphone - Windows Receiver Client
Redesigned with CustomTkinter
"""

import socket
import threading
import queue
import sys
import time
import math
import random
import hashlib
from collections import defaultdict
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from theme import Colors, Fonts
from widgets import AudioMeter, StatusLED

try:
    import pyaudio
except ImportError:
    print("[ERROR] PyAudio is not installed.")
    sys.exit(1)

# ── Audio Configuration ──────────────────────────────────────────────────────
SAMPLE_RATE = 48000
SAMPLE_WIDTH = 2          # 16-bit = 2 bytes
CHANNELS = 1              # Mono
CHUNK_SIZE = 4800          # bytes per UDP packet (2400 samples = 100ms)
FORMAT = pyaudio.paInt16

# ── Network Configuration ────────────────────────────────────────────────────
UDP_PORT = 55555
SOCKET_TIMEOUT = 1.0

# ── Queue Configuration ─────────────────────────────────────────────────────
MAX_QUEUE_DEPTH = 50

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

import os
def get_asset_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'assets', filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', filename)

class WirelessMicApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure Window
        self.title("Wireless Mic Receiver")
        self.geometry("700x650")
        self.minsize(600, 550)
        self.configure(fg_color=Colors.BG)
        
        try:
            self.iconbitmap(get_asset_path("icon.ico"))
        except Exception:
            pass
        
        # State
        self.running = threading.Event()
        self.is_server_active = False
        self.audio_queue = queue.Queue(maxsize=MAX_QUEUE_DEPTH)
        self.gui_queue = queue.Queue() # For thread-safe GUI updates
        
        self.stats = {
            "packets": 0,
            "bytes": 0,
            "last_time": 0.0,
            "rms": 0.0
        }
        
        self.ip_rates = defaultdict(list)
        self.pin = f"{random.randint(0, 9999):04d}"
        self.aes_key = hashlib.sha256(self.pin.encode('utf-8')).digest()
        
        # Threads
        self.listener_thread = None
        self.player_thread = None
        
        self.setup_ui()
        self.setup_tray()
        
        # Start GUI update loop
        self.after(50, self.process_gui_queue)

    def setup_ui(self):
        # Container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        self.header = ctk.CTkLabel(self.main_container, text="Wireless Mic", font=Fonts.heading(), text_color=Colors.TEXT_PRIMARY)
        self.header.pack(anchor="w", pady=(0, 20))
        
        # IP Card
        self.ip_card = ctk.CTkFrame(self.main_container, fg_color=Colors.SURFACE, corner_radius=12)
        self.ip_card.pack(fill="x", pady=(0, 20), ipady=10)
        
        self.ip_label = ctk.CTkLabel(self.ip_card, text="YOUR PC'S IP ADDRESS", font=Fonts.label(), text_color=Colors.TEXT_SECONDARY)
        self.ip_label.pack(pady=(15, 5))
        
        self.local_ip = get_local_ip()
        self.ip_display = ctk.CTkLabel(self.ip_card, text=self.local_ip, font=Fonts.ip_display(), text_color=Colors.PRIMARY)
        self.ip_display.pack(pady=(0, 15))
        
        # Security Card
        self.sec_card = ctk.CTkFrame(self.main_container, fg_color=Colors.SURFACE, corner_radius=12)
        self.sec_card.pack(fill="x", pady=(0, 20), ipady=10)
        
        self.pin_label = ctk.CTkLabel(self.sec_card, text="SECURITY PIN (ENTER ON PHONE)", font=Fonts.label(), text_color=Colors.TEXT_SECONDARY)
        self.pin_label.pack(pady=(15, 5))
        
        self.pin_display = ctk.CTkLabel(self.sec_card, text=self.pin, font=Fonts.heading(), text_color=Colors.SUCCESS)
        self.pin_display.pack(pady=(0, 15))
        
        # Status Card
        self.status_card = ctk.CTkFrame(self.main_container, fg_color=Colors.SURFACE, corner_radius=12)
        self.status_card.pack(fill="x", pady=(0, 20), ipadx=20, ipady=15)
        
        self.status_row = ctk.CTkFrame(self.status_card, fg_color="transparent")
        self.status_row.pack(fill="x")
        
        self.status_led = StatusLED(self.status_row, size=16, color=Colors.ERROR)
        self.status_led.pack(side="left", padx=(0, 10))
        
        self.status_text = ctk.CTkLabel(self.status_row, text="Disconnected", font=Fonts.body(), text_color=Colors.TEXT_PRIMARY)
        self.status_text.pack(side="left")
        
        self.port_frame = ctk.CTkFrame(self.status_row, fg_color="transparent")
        self.port_frame.pack(side="right")
        self.port_val = ctk.CTkLabel(self.port_frame, text=str(UDP_PORT), font=Fonts.heading(), text_color=Colors.TEXT_PRIMARY)
        self.port_val.pack()
        self.port_lbl = ctk.CTkLabel(self.port_frame, text="UDP Port", font=Fonts.label(), text_color=Colors.TEXT_SECONDARY)
        self.port_lbl.pack()
        
        # Audio Meter
        self.meter_lbl = ctk.CTkLabel(self.main_container, text="AUDIO LEVEL", font=Fonts.label(), text_color=Colors.TEXT_SECONDARY)
        self.meter_lbl.pack(anchor="w", pady=(0, 5))
        self.meter = AudioMeter(self.main_container, width=660, height=30)
        self.meter.pack(fill="x", pady=(0, 20))
        
        # Controls
        self.controls = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.controls.pack(fill="x", pady=(0, 20))
        
        self.btn_start = ctk.CTkButton(self.controls, text="START SERVER", font=Fonts.button(), fg_color=Colors.SUCCESS, hover_color=Colors.SUCCESS_HOVER, command=self.start_server, height=40)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.btn_stop = ctk.CTkButton(self.controls, text="STOP SERVER", font=Fonts.button(), fg_color=Colors.ERROR, hover_color=Colors.ERROR_HOVER, command=self.stop_server, state="disabled", height=40)
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=(10, 0))
        
        # Log Window
        self.log_lbl = ctk.CTkLabel(self.main_container, text="EVENT LOG", font=Fonts.label(), text_color=Colors.TEXT_SECONDARY)
        self.log_lbl.pack(anchor="w", pady=(0, 5))
        
        self.log_box = ctk.CTkTextbox(self.main_container, height=120, fg_color=Colors.SURFACE, text_color=Colors.TEXT_PRIMARY, font=Fonts.log())
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")
        
        self.log_msg("System ready.")
        
    def log_msg(self, msg, tag="INFO"):
        def _log():
            self.log_box.configure(state="normal")
            ts = time.strftime("%H:%M:%S")
            self.log_box.insert("end", f"[{ts}] [{tag}] {msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        # Ensure it runs on the main thread
        self.after(0, _log)

    def process_gui_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if msg["type"] == "rms":
                    self.meter.set_level(msg["value"])
                elif msg["type"] == "status":
                    self.update_status(msg["text"], msg["color"], msg["pulse"])
                elif msg["type"] == "log":
                    self.log_msg(msg["text"], msg["tag"])
        except queue.Empty:
            pass
        
        # If server is active but no packets for 1.5s, update status
        if self.is_server_active and time.time() - self.stats["last_time"] > 1.5:
            if self.status_text.cget("text") == "Receiving Audio...":
                self.update_status("Waiting for connection...", Colors.WARNING, pulse=True)
                self.meter.set_level(0)
                
        self.after(50, self.process_gui_queue)

    def update_status(self, text, color, pulse):
        self.status_text.configure(text=text)
        self.status_led.set_color(color)
        self.status_led.pulse(pulse)

    # ── Server Logic ─────────────────────────────────────────────────────────
    def start_server(self):
        if self.is_server_active: return
        self.is_server_active = True
        self.running.set()
        
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.update_status("Waiting for connection...", Colors.WARNING, pulse=True)
        self.log_msg(f"Starting server on {self.local_ip}:{UDP_PORT}")
        
        self.listener_thread = threading.Thread(target=self.udp_listener, daemon=True)
        self.player_thread = threading.Thread(target=self.audio_player, daemon=True)
        
        self.listener_thread.start()
        self.player_thread.start()

    def stop_server(self):
        if not self.is_server_active: return
        self.is_server_active = False
        self.running.clear()
        
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.update_status("Disconnected", Colors.ERROR, pulse=False)
        self.meter.set_level(0)
        self.log_msg("Server stopped.")

    def udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)
        except OSError:
            pass
        sock.settimeout(SOCKET_TIMEOUT)
        
        try:
            sock.bind(("0.0.0.0", UDP_PORT))
        except OSError as e:
            self.gui_queue.put({"type": "log", "text": f"Bind failed: {e}", "tag": "ERROR"})
            self.running.clear()
            # Stop GUI
            self.after(0, self.stop_server)
            return

        unauth_logged = False
        while self.running.is_set():
            try:
                data, addr = sock.recvfrom(65535)
                now = time.time()
                ip = addr[0]
                
                # DoS Protection: Rate Limiting
                self.ip_rates[ip] = [t for t in self.ip_rates[ip] if now - t < 1.0]
                if len(self.ip_rates[ip]) > 30:
                    continue # Drop packet
                self.ip_rates[ip].append(now)
                
                # Decryption & Authentication
                if len(data) < 16: continue
                iv = data[:16]
                ciphertext = data[16:]
                
                try:
                    cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
                    decryptor = cipher.decryptor()
                    padded_data = decryptor.update(ciphertext) + decryptor.finalize()
                    
                    unpadder = padding.PKCS7(128).unpadder()
                    decrypted_audio = unpadder.update(padded_data) + unpadder.finalize()
                    unauth_logged = False # Reset flag on successful decrypt
                except Exception:
                    if not unauth_logged:
                        self.gui_queue.put({"type": "log", "text": f"Unauthorized access blocked from {ip}", "tag": "SECURITY"})
                        unauth_logged = True
                    continue
                
                # Check if this is a new connection stream
                if now - self.stats["last_time"] > 2.0:
                    self.gui_queue.put({
                        "type": "status", 
                        "text": "Receiving Audio...", 
                        "color": Colors.SUCCESS, 
                        "pulse": True
                    })
                    self.gui_queue.put({"type": "log", "text": f"Secure stream established from {ip}", "tag": "SECURE"})
                
                self.stats["last_time"] = now
                self.stats["packets"] += 1
                
                # Calculate RMS for visualizer
                if self.stats["packets"] % 5 == 0:
                    try:
                        import struct
                        samples = struct.unpack(f"<{len(decrypted_audio)//2}h", decrypted_audio)
                        peak = max(abs(s) for s in samples)
                        level = peak / 32768.0
                        self.gui_queue.put({"type": "rms", "value": level})
                    except Exception:
                        pass
                
                # Enqueue audio
                try:
                    self.audio_queue.put_nowait(decrypted_audio)
                except queue.Full:
                    try: self.audio_queue.get_nowait()
                    except: pass
                    try: self.audio_queue.put_nowait(decrypted_audio)
                    except: pass
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running.is_set():
                    self.gui_queue.put({"type": "log", "text": f"UDP error: {e}", "tag": "ERROR"})
                break
                
        sock.close()

    def audio_player(self):
        pa = pyaudio.PyAudio()
        
        # VB-Cable Fallback Logic
        target_idx = None
        default_idx = None
        
        try:
            default_idx = pa.get_default_output_device_info()['index']
            target_idx = default_idx
        except IOError:
            self.gui_queue.put({"type": "log", "text": "No default audio device found.", "tag": "ERROR"})
            
        # Search for VB-Cable
        for i in range(pa.get_device_count()):
            dev = pa.get_device_info_by_index(i)
            if dev['maxOutputChannels'] > 0:
                if "CABLE Input" in dev['name'] or "VB-Audio" in dev['name']:
                    target_idx = i
                    self.gui_queue.put({"type": "log", "text": f"Found VB-Cable: {dev['name']}", "tag": "AUDIO"})
                    break
        
        if target_idx is None:
            self.running.clear()
            self.after(0, self.stop_server)
            pa.terminate()
            return
            
        try:
            stream = pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                output_device_index=target_idx,
                frames_per_buffer=CHUNK_SIZE // SAMPLE_WIDTH,
            )
        except IOError as e:
            self.gui_queue.put({"type": "log", "text": f"Failed to open audio stream: {e}", "tag": "ERROR"})
            self.running.clear()
            self.after(0, self.stop_server)
            pa.terminate()
            return

        silence = b'\x00' * CHUNK_SIZE
        
        while self.running.is_set():
            try:
                data = self.audio_queue.get(timeout=0.1)
                stream.write(data)
            except queue.Empty:
                try: stream.write(silence)
                except: pass
            except IOError:
                continue
                
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
        pa.terminate()

    # ── System Tray ──────────────────────────────────────────────────────────
    def setup_tray(self):
        # Load the actual icon
        try:
            img = Image.open(get_asset_path("icon.png"))
        except Exception:
            # Fallback
            img = Image.new('RGB', (64, 64), color=(59, 130, 246))
            d = ImageDraw.Draw(img)
            d.ellipse((16, 16, 48, 48), fill=(255, 255, 255))
        
        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window, default=True),
            pystray.MenuItem("Exit", self.quit_app)
        )
        self.tray_icon = pystray.Icon("name", img, "Wireless Mic", menu)
        
        # Start tray in background
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        # Bind close event
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        
    def hide_window(self):
        self.withdraw()
        
    def show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        
    def quit_app(self, icon=None, item=None):
        self.running.clear()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

if __name__ == "__main__":
    app = WirelessMicApp()
    app.mainloop()
