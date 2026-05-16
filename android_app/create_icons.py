"""
Generates ic_launcher.png at all Android mipmap densities.
Run from the android_app directory:  python create_icons.py
Requires: pip install Pillow
"""
import os
from PIL import Image

SRC = r"C:\Users\LENOVO\.gemini\antigravity\brain\64a01fdc-2fe3-4481-a9d0-a50036a67593\wireless_mic_icon_1778847220803.png"
BASE = r"android\app\src\main\res"

DENSITIES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

img = Image.open(SRC).convert("RGBA")

for folder, size in DENSITIES.items():
    dest_dir = os.path.join(BASE, folder)
    os.makedirs(dest_dir, exist_ok=True)
    resized = img.resize((size, size), Image.LANCZOS)
    out_path = os.path.join(dest_dir, "ic_launcher.png")
    resized.save(out_path, "PNG")
    print(f"  Created {out_path}  ({size}x{size})")

print("\nDone! All mipmap icons created.")
