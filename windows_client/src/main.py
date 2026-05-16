"""
main.py - Wireless Mic Client GUI Application
Modern dark-themed Tkinter GUI for receiving audio from Android device.
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import sys
import os
import logging
import webbrowser
from datetime import datetime
import random

# ── Path Setup ─────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.expanduser("~"), "wireless_mic.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("WirelessMic")

# ── Internal Imports ───────────────────────────────────────────────────────────
from audio_server import AudioServer, UDP_PORT
from ip_detector  import get_best_ip, IPChangeMonitor
from system_tray  import TrayIcon

# ── App Version ────────────────────────────────────────────────────────────────
VERSION = "1.0.0"

# ── Colour Palette (Dark Theme) ────────────────────────────────────────────────
CLR = {
    "bg":          "#0F1117",
    "surface":     "#1A1D2E",
    "surface2":    "#252840",
    "border":      "#2E3152",
    "accent":      "#5B6EF5",
    "accent_hover":"#7B8EFF",
    "green":       "#22C55E",
    "red":         "#EF4444",
    "amber":       "#F59E0B",
    "text":        "#E2E8F0",
    "text_muted":  "#64748B",
    "text_dim":    "#94A3B8",
    "meter_bg":    "#1E2235",
    "meter_fill":  "#5B6EF5",
    "meter_peak":  "#EF4444",
}

FONT_FAMILY = "Segoe UI"


# ══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Wireless Mic Client")
        self.geometry("640x520")
        self.minsize(580, 460)
        self.configure(bg=CLR["bg"])
        self.resizable(True, True)

        # State
        self._server:      AudioServer = None
        self._tray:        TrayIcon    = None
        self._ip_monitor:  IPChangeMonitor = None
        self._connected    = False
        self._level        = 0.0
        self._peak         = 0.0
        self._peak_hold    = 0
        self._always_on_top= tk.BooleanVar(value=False)
        self._minimize_tray= tk.BooleanVar(value=True)
        self._use_vbcable  = tk.BooleanVar(value=True)
        self._server_running = False
        self._pin_var      = tk.StringVar(value=f"{random.randint(1000, 9999):04d}")

        # Icon path
        self._icon_path = self._find_asset("icon.ico")
        if self._icon_path:
            try:
                self.iconbitmap(self._icon_path)
            except Exception:
                pass

        self._build_styles()
        self._build_ui()
        self._start_tray()
        self._start_ip_monitor()
        self._update_loop()

        # Start server automatically
        self.after(500, self._start_server)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        logger.info("Wireless Mic Client v%s started", VERSION)

    # ── Style Setup ────────────────────────────────────────────────────────────

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame",       background=CLR["bg"])
        style.configure("Surface.TFrame", background=CLR["surface"])
        style.configure(
            "Accent.TButton",
            background=CLR["accent"], foreground="white",
            font=(FONT_FAMILY, 10, "bold"), relief="flat",
            padding=(14, 8),
        )
        style.map("Accent.TButton",
            background=[("active", CLR["accent_hover"]), ("pressed", "#4A5CE0")],
        )
        style.configure(
            "Stop.TButton",
            background=CLR["red"], foreground="white",
            font=(FONT_FAMILY, 10, "bold"), relief="flat",
            padding=(14, 8),
        )
        style.map("Stop.TButton",
            background=[("active", "#F87171"), ("pressed", "#DC2626")],
        )
        style.configure(
            "Ghost.TButton",
            background=CLR["surface2"], foreground=CLR["text_dim"],
            font=(FONT_FAMILY, 9), relief="flat", padding=(8, 5),
        )
        style.map("Ghost.TButton",
            background=[("active", CLR["border"])],
        )
        style.configure(
            "TCheckbutton",
            background=CLR["bg"], foreground=CLR["text_dim"],
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "TLabel",
            background=CLR["bg"], foreground=CLR["text"],
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Muted.TLabel",
            background=CLR["bg"], foreground=CLR["text_muted"],
            font=(FONT_FAMILY, 9),
        )

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        # ─ Header ─────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CLR["surface"], pady=0)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="📡  Wireless Mic Client",
            bg=CLR["surface"], fg=CLR["text"],
            font=(FONT_FAMILY, 14, "bold"), pady=12, padx=18,
        ).pack(side="left")

        tk.Label(
            hdr, text=f"v{VERSION}",
            bg=CLR["surface"], fg=CLR["text_muted"],
            font=(FONT_FAMILY, 9), pady=12, padx=4,
        ).pack(side="left")

        # Separator
        tk.Frame(self, bg=CLR["border"], height=1).pack(fill="x")

        # ─ Body ───────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=CLR["bg"])
        body.pack(fill="both", expand=True, padx=18, pady=14)
        body.columnconfigure(0, weight=1)

        # IP and PIN Cards
        row0 = tk.Frame(body, bg=CLR["bg"])
        row0.grid(row=0, column=0, sticky="ew")
        row0.columnconfigure(0, weight=2)
        row0.columnconfigure(1, weight=1)

        ip_card = self._card(row0, col=0, padright=6)
        self._build_ip_card(ip_card)

        pin_card = self._card(row0, col=1, padleft=6)
        self._build_pin_card(pin_card)

        # Status + Port row
        row2 = tk.Frame(body, bg=CLR["bg"])
        row2.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        status_card = self._card(row2, col=0, padright=6)
        self._build_status_card(status_card)

        port_card = self._card(row2, col=1, padleft=6)
        self._build_port_card(port_card)

        # Audio Meter
        meter_card = self._card(body, row=2, pady_top=8)
        self._build_meter_card(meter_card)

        # Controls row
        ctrl = tk.Frame(body, bg=CLR["bg"])
        ctrl.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self._build_controls(ctrl)

        # Options row
        opts = tk.Frame(body, bg=CLR["bg"])
        opts.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        self._build_options(opts)

        # Log area
        log_lbl = tk.Label(body, text="Event Log", bg=CLR["bg"], fg=CLR["text_muted"],
                           font=(FONT_FAMILY, 9, "bold"), anchor="w")
        log_lbl.grid(row=5, column=0, sticky="ew", pady=(10, 3))

        self._log_box = scrolledtext.ScrolledText(
            body, height=6, bg=CLR["surface"], fg=CLR["text_dim"],
            font=("Consolas", 8), bd=0, relief="flat",
            insertbackground=CLR["text"],
            selectbackground=CLR["accent"], wrap="word",
        )
        self._log_box.grid(row=6, column=0, sticky="nsew")
        body.rowconfigure(6, weight=1)

        # ─ Footer ─────────────────────────────────────────────────────────────
        tk.Frame(self, bg=CLR["border"], height=1).pack(fill="x")
        footer = tk.Frame(self, bg=CLR["surface"])
        footer.pack(fill="x", pady=0)
        tk.Label(
            footer, text="Open source  •  MIT License  •  github.com/wirelessmic",
            bg=CLR["surface"], fg=CLR["text_muted"], font=(FONT_FAMILY, 8),
            pady=5,
        ).pack(side="left", padx=12)

        self._stats_label = tk.Label(
            footer, text="", bg=CLR["surface"],
            fg=CLR["text_muted"], font=(FONT_FAMILY, 8), pady=5,
        )
        self._stats_label.pack(side="right", padx=12)

    def _card(self, parent, row=None, col=0, padright=0, padleft=0, pady_top=0):
        """Create a rounded surface card frame."""
        f = tk.Frame(parent, bg=CLR["surface"],
                     highlightbackground=CLR["border"], highlightthickness=1)
        kw = dict(sticky="nsew", padx=(padleft, padright), pady=(pady_top, 0))
        if row is not None:
            f.grid(row=row, column=col, **kw)
        else:
            f.grid(row=0, column=col, **kw)
        return f

    def _build_ip_card(self, parent):
        parent.columnconfigure(0, weight=1)
        tk.Label(parent, text="Your PC's IP Address",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 9)).grid(
                     row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(10, 0))

        self._ip_var = tk.StringVar(value=get_best_ip())
        ip_label = tk.Label(
            parent, textvariable=self._ip_var,
            bg=CLR["surface"], fg=CLR["accent"],
            font=(FONT_FAMILY, 22, "bold"), pady=4,
        )
        ip_label.grid(row=1, column=0, sticky="w", padx=16)

        copy_btn = ttk.Button(
            parent, text="⧉ Copy", style="Ghost.TButton",
            command=self._copy_ip,
        )
        copy_btn.grid(row=1, column=1, padx=(0, 8), pady=4, sticky="e")

        refresh_btn = ttk.Button(
            parent, text="↻", style="Ghost.TButton",
            command=self._refresh_ip, width=3,
        )
        refresh_btn.grid(row=1, column=2, padx=(0, 12), pady=4, sticky="e")

        tk.Label(parent, text=f"Open the Android app and enter this IP  •  Port {UDP_PORT}",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 8)).grid(
                     row=2, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 10))

    def _build_pin_card(self, parent):
        parent.columnconfigure(0, weight=1)
        tk.Label(parent, text="Security PIN",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 9)).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))

        pin_entry = tk.Label(
            parent, textvariable=self._pin_var,
            bg=CLR["surface2"], fg=CLR["text"],
            font=(FONT_FAMILY, 22, "bold"), bd=0, width=6,
            justify="center"
        )
        pin_entry.grid(row=1, column=0, sticky="w", padx=14, pady=4)
        
        tk.Label(parent, text="4-digit code",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 8)).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))

    def _build_status_card(self, parent):
        parent.columnconfigure(0, weight=1)
        tk.Label(parent, text="Connection",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 9)).pack(anchor="w", padx=14, pady=(10, 0))

        status_row = tk.Frame(parent, bg=CLR["surface"])
        status_row.pack(fill="x", padx=14, pady=(4, 10))

        self._status_led = tk.Canvas(
            status_row, width=16, height=16,
            bg=CLR["surface"], bd=0, highlightthickness=0,
        )
        self._status_led.pack(side="left")
        self._led_circle = self._status_led.create_oval(2, 2, 14, 14, fill=CLR["red"], outline="")

        self._status_var = tk.StringVar(value="Waiting…")
        tk.Label(status_row, textvariable=self._status_var,
                 bg=CLR["surface"], fg=CLR["text"],
                 font=(FONT_FAMILY, 10, "bold")).pack(side="left", padx=(8, 0))

    def _build_port_card(self, parent):
        parent.columnconfigure(0, weight=1)
        tk.Label(parent, text="UDP Port",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 9)).pack(anchor="w", padx=14, pady=(10, 0))

        tk.Label(parent, text=str(UDP_PORT),
                 bg=CLR["surface"], fg=CLR["text"],
                 font=(FONT_FAMILY, 18, "bold")).pack(anchor="w", padx=14, pady=(4, 10))

    def _build_meter_card(self, parent):
        parent.columnconfigure(1, weight=1)
        tk.Label(parent, text="Audio Level",
                 bg=CLR["surface"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 9)).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self._meter_canvas = tk.Canvas(
            parent, height=20, bg=CLR["meter_bg"],
            bd=0, highlightthickness=0,
        )
        self._meter_canvas.grid(row=0, column=1, sticky="ew", padx=(0, 14), pady=(10, 4))

        self._peak_label = tk.Label(parent, text="PEAK",
                                    bg=CLR["surface"], fg=CLR["text_muted"],
                                    font=(FONT_FAMILY, 7))
        self._peak_label.grid(row=0, column=2, padx=(0, 14), pady=(10, 4))

        tk.Label(parent, text="",
                 bg=CLR["surface"], height=1).grid(row=1, column=0)

        self._meter_canvas.bind("<Configure>", lambda e: self._draw_meter())

    def _build_controls(self, parent):
        self._toggle_btn = ttk.Button(
            parent, text="⏹  Stop Server", style="Stop.TButton",
            command=self._toggle_server,
        )
        self._toggle_btn.pack(side="left")

        ttk.Button(
            parent, text="📋  View Log File", style="Ghost.TButton",
            command=lambda: os.startfile(LOG_FILE),
        ).pack(side="left", padx=(8, 0))

        self._connected_from_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self._connected_from_var,
                 bg=CLR["bg"], fg=CLR["text_muted"],
                 font=(FONT_FAMILY, 9)).pack(side="right")

    def _build_options(self, parent):
        ttk.Checkbutton(
            parent, text="Always on top",
            variable=self._always_on_top,
            command=self._toggle_topmost,
        ).pack(side="left")

        ttk.Checkbutton(
            parent, text="Minimise to tray on close",
            variable=self._minimize_tray,
        ).pack(side="left", padx=(16, 0))

        ttk.Checkbutton(
            parent, text="Route to VB-Cable",
            variable=self._use_vbcable,
            command=self._toggle_vbcable,
        ).pack(side="left", padx=(16, 0))

    # ── Server Control ─────────────────────────────────────────────────────────

    def _start_server(self):
        pin_val = self._pin_var.get().strip()
        self._server = AudioServer(
            pin=pin_val,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_level=self._on_level,
            on_log=self._append_log,
            on_stats=self._on_stats,
            use_vbcable=self._use_vbcable.get(),
        )
        self._server.start()
        self._server_running = True
        self._toggle_btn.configure(text="⏹  Stop Server", style="Stop.TButton")
        if self._tray:
            self._tray.set_server_label("Stop Server")

    def _stop_server(self):
        if self._server:
            self._server.stop()
            self._server = None
        self._server_running = False
        self._toggle_btn.configure(text="▶  Start Server", style="Accent.TButton")
        if self._tray:
            self._tray.set_server_label("Start Server")

    def _toggle_server(self):
        if self._server_running:
            self._stop_server()
        else:
            self._start_server()

    def _toggle_vbcable(self):
        if self._server:
            self._server.use_vbcable = self._use_vbcable.get()

    # ── Callbacks (thread-safe via after()) ────────────────────────────────────

    def _on_connect(self, addr: str):
        def _update():
            self._connected = True
            self._status_var.set("Connected")
            self._status_led.itemconfig(self._led_circle, fill=CLR["green"])
            self._connected_from_var.set(f"📱  {addr}")
            if self._tray:
                self._tray.update_status(True)
                self._tray.notify("Wireless Mic", f"Android connected from {addr}")
        self.after(0, _update)

    def _on_disconnect(self):
        def _update():
            self._connected = False
            self._status_var.set("Disconnected")
            self._status_led.itemconfig(self._led_circle, fill=CLR["red"])
            self._connected_from_var.set("")
            self._level = 0.0
            self._draw_meter()
            if self._tray:
                self._tray.update_status(False)
                self._tray.notify("Wireless Mic", "Device disconnected.")
        self.after(0, _update)

    def _on_level(self, rms: float):
        self._level = rms

    def _on_stats(self, stats: dict):
        def _update():
            recv = stats.get("packets_received", 0)
            drop = stats.get("packets_dropped", 0)
            up   = stats.get("uptime", 0)
            self._stats_label.configure(
                text=f"Recv: {recv}  Drop: {drop}  Up: {up:.0f}s"
            )
        self.after(0, _update)

    def _append_log(self, msg: str):
        def _update():
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_box.insert("end", f"[{ts}] {msg}\n")
            self._log_box.see("end")
        self.after(0, _update)

    # ── UI Helpers ─────────────────────────────────────────────────────────────

    def _draw_meter(self):
        canvas = self._meter_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 2 or h < 2:
            return

        canvas.delete("all")
        canvas.create_rectangle(0, 0, w, h, fill=CLR["meter_bg"], outline="")

        # Peak hold decay
        if self._level >= self._peak:
            self._peak = self._level
            self._peak_hold = 30
        else:
            if self._peak_hold > 0:
                self._peak_hold -= 1
            else:
                self._peak = max(0.0, self._peak - 0.02)

        # Gradient fill (green → yellow → red)
        fill_w = int(w * self._level)
        if fill_w > 0:
            # Green zone
            green_w = min(fill_w, int(w * 0.6))
            canvas.create_rectangle(0, 0, green_w, h, fill="#22C55E", outline="")
            # Amber zone
            if fill_w > green_w:
                amber_w = min(fill_w - green_w, int(w * 0.25))
                canvas.create_rectangle(green_w, 0, green_w + amber_w, h,
                                         fill="#F59E0B", outline="")
                # Red zone
                if fill_w > green_w + amber_w:
                    canvas.create_rectangle(
                        green_w + amber_w, 0, fill_w, h,
                        fill=CLR["red"], outline=""
                    )

        # Peak indicator line
        peak_x = int(w * self._peak)
        if peak_x > 0:
            canvas.create_rectangle(peak_x - 2, 0, peak_x, h,
                                     fill="white", outline="")

        # Tick marks
        for pct in (0.25, 0.5, 0.75):
            x = int(w * pct)
            canvas.create_line(x, h - 4, x, h, fill=CLR["border"], width=1)

    def _update_loop(self):
        """60 fps UI refresh loop for the audio meter."""
        self._draw_meter()
        self.after(16, self._update_loop)

    def _copy_ip(self):
        ip = self._ip_var.get()
        self.clipboard_clear()
        self.clipboard_append(ip)
        self._append_log(f"Copied IP address: {ip}")

    def _refresh_ip(self):
        self._ip_var.set(get_best_ip())

    def _toggle_topmost(self):
        self.attributes("-topmost", self._always_on_top.get())

    # ── IP Monitor ─────────────────────────────────────────────────────────────

    def _start_ip_monitor(self):
        self._ip_monitor = IPChangeMonitor(
            callback=lambda ip: self.after(0, lambda: self._ip_var.set(ip)),
            interval=5.0,
        )
        self._ip_monitor.start()

    # ── System Tray ────────────────────────────────────────────────────────────

    def _start_tray(self):
        icon_path = self._find_asset("icon.ico") or self._find_asset("icon.png")
        self._tray = TrayIcon(
            icon_path=icon_path,
            on_show=self._tray_toggle_visibility,
            on_start_stop=self._toggle_server,
            on_exit=self._on_exit,
        )
        self._tray.start()

    def _tray_toggle_visibility(self):
        if self.winfo_viewable():
            self.withdraw()
        else:
            self.deiconify()
            self.lift()
            self.focus_force()

    # ── Window Events ──────────────────────────────────────────────────────────

    def _on_close(self):
        if self._minimize_tray.get():
            self.withdraw()
            if self._tray:
                self._tray.notify("Wireless Mic", "Minimised to system tray.")
        else:
            self._on_exit()

    def _on_exit(self):
        if self._server_running:
            self._stop_server()
        if self._ip_monitor:
            self._ip_monitor.stop()
        if self._tray:
            self._tray.stop()
        self.destroy()

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def _find_asset(name: str):
        """Search for an asset file relative to the script location."""
        candidates = [
            os.path.join(_HERE, "..", "assets", name),
            os.path.join(_HERE, "assets", name),
            os.path.join(os.path.dirname(sys.executable), "assets", name),
            os.path.join(os.path.dirname(sys.executable), name),
        ]
        for p in candidates:
            if os.path.exists(p):
                return os.path.abspath(p)
        return None


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
