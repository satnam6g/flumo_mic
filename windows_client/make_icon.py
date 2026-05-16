"""
make_icon.py  –  One-time script to convert the PNG icon to .ico
Run once before building:  python make_icon.py
"""
import os, shutil, sys
from pathlib import Path

SRC_PNG = r"C:\Users\LENOVO\.gemini\antigravity\brain\64a01fdc-2fe3-4481-a9d0-a50036a67593\wireless_mic_icon_sq_1778848181831.png"
ASSETS  = Path(__file__).parent / "assets"

def main():
    ASSETS.mkdir(exist_ok=True)
    dst_png = ASSETS / "icon.png"
    dst_ico = ASSETS / "icon.ico"

    # Copy PNG
    if Path(SRC_PNG).exists():
        shutil.copy(SRC_PNG, dst_png)
        print(f"Copied → {dst_png}")
    elif dst_png.exists():
        print(f"Using existing {dst_png}")
    else:
        print("ERROR: No source PNG found. Place icon.png in assets/ manually.")
        sys.exit(1)

    # Convert to ICO
    try:
        from PIL import Image
        img = Image.open(dst_png).convert("RGBA")
        sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
        imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
        imgs[0].save(dst_ico, format="ICO", sizes=sizes, append_images=imgs[1:])
        print(f"Created  → {dst_ico}  ({dst_ico.stat().st_size // 1024} KB)")
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        sys.exit(1)

if __name__ == "__main__":
    main()
