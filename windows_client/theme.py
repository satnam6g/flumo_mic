# theme.py
# Contains color hex codes and font definitions for the Windows client.

class Colors:
    # Backgrounds
    BG = "#0f172a"
    SURFACE = "#1e293b"
    SURFACE_ELEVATED = "#334155"

    # Brand / Primary
    PRIMARY = "#3b82f6"
    PRIMARY_HOVER = "#2563eb"
    SECONDARY = "#8b5cf6"

    # States
    SUCCESS = "#10b981"
    SUCCESS_HOVER = "#059669"
    ERROR = "#ef4444"
    ERROR_HOVER = "#dc2626"
    WARNING = "#f59e0b"

    # Text
    TEXT_PRIMARY = "#f8fafc"
    TEXT_SECONDARY = "#94a3b8"

    # Gradients (CustomTkinter doesn't support linear gradients out of the box, 
    # but we can simulate them by using base colors or drawing them on a canvas in custom widgets)

class Fonts:
    FAMILY = "Segoe UI" # Inter might not be installed, Segoe UI is native to Windows.
    MONO = "Consolas"

    @classmethod
    def ip_display(cls):
        return (cls.MONO, 32, "bold")
    
    @classmethod
    def heading(cls):
        return (cls.FAMILY, 24, "bold")
    
    @classmethod
    def body(cls):
        return (cls.FAMILY, 14)
    
    @classmethod
    def label(cls):
        return (cls.FAMILY, 12, "bold")
    
    @classmethod
    def button(cls):
        return (cls.FAMILY, 14, "bold")
    
    @classmethod
    def log(cls):
        return (cls.MONO, 11)
