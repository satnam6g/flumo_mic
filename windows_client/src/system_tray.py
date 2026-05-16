"""
system_tray.py - System tray icon handler for Wireless Mic Client.
Uses pystray for the tray icon + plyer for toast notifications.
"""

import threading
import logging
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrayIcon:
    """
    Manages the Windows system tray icon.
    Callbacks:
        on_show()     - called when user clicks Show/Hide
        on_start_stop() - called when user clicks Start/Stop
        on_exit()     - called when user clicks Exit
    """

    def __init__(
        self,
        icon_path: Optional[str],
        on_show:       Callable = None,
        on_start_stop: Callable = None,
        on_exit:       Callable = None,
    ):
        self._icon_path    = icon_path
        self._on_show       = on_show       or (lambda: None)
        self._on_start_stop = on_start_stop or (lambda: None)
        self._on_exit       = on_exit       or (lambda: None)
        self._icon          = None
        self._thread        = None
        self._running_label = "Stop Server"
        self._menu          = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Launch tray icon in background thread."""
        self._thread = threading.Thread(
            target=self._run, name="TrayIcon", daemon=True
        )
        self._thread.start()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def update_status(self, connected: bool):
        """Update the tray tooltip to reflect connection state."""
        if self._icon:
            try:
                self._icon.title = (
                    "Wireless Mic — Connected" if connected
                    else "Wireless Mic — Waiting…"
                )
            except Exception:
                pass

    def set_server_label(self, label: str):
        """Change Start/Stop menu label."""
        self._running_label = label
        self._rebuild_menu()

    def notify(self, title: str, message: str):
        """Show a Windows toast notification."""
        try:
            import plyer
            plyer.notification.notify(
                title=title,
                message=message,
                app_name="Wireless Mic",
                timeout=4,
            )
        except Exception:
            logger.debug("Toast notification unavailable: %s - %s", title, message)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _run(self):
        try:
            import pystray
            from PIL import Image as PILImage
        except ImportError:
            logger.warning("pystray/Pillow not installed — tray icon disabled.")
            return

        # Load icon image
        if self._icon_path and os.path.exists(self._icon_path):
            img = PILImage.open(self._icon_path).convert("RGBA")
        else:
            img = self._generate_fallback_icon()

        def on_show(icon, item):
            self._on_show()

        def on_start_stop(icon, item):
            self._on_start_stop()

        def on_exit(icon, item):
            icon.stop()
            self._on_exit()

        menu = pystray.Menu(
            pystray.MenuItem("Show / Hide",  on_show, default=True),
            pystray.MenuItem(lambda item: self._running_label, on_start_stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit),
        )

        self._icon = pystray.Icon(
            name="WirelessMic",
            icon=img,
            title="Wireless Mic — Waiting…",
            menu=menu,
        )
        try:
            self._icon.run()
        except Exception as e:
            logger.error("Tray icon error: %s", e)

    def _rebuild_menu(self):
        """Force menu refresh (pystray rebuilds dynamically via lambdas)."""
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass

    @staticmethod
    def _generate_fallback_icon():
        """Generate a simple microphone icon if no file is found."""
        from PIL import Image as PILImage, ImageDraw
        size = 64
        img = PILImage.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Background circle
        draw.ellipse([0, 0, size - 1, size - 1], fill=(45, 55, 110, 255))
        # Simple mic body
        draw.rounded_rectangle([22, 10, 42, 38], radius=8, fill="white")
        # Stand
        draw.line([32, 38, 32, 52], fill="white", width=3)
        draw.line([22, 52, 42, 52], fill="white", width=3)
        return img
