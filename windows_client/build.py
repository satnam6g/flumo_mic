"""
build.py  –  Build automation script for Wireless Mic Windows Installer
===========================================================================
Steps:
  1. Check prerequisites (Python, PyInstaller, Inno Setup)
  2. Install Python dependencies
  3. Convert icon PNG → ICO (all sizes)
  4. Run PyInstaller to build WirelessMic.exe
  5. Copy VB-Cable installer(s) to vb_cable/ folder
  6. Run Inno Setup compiler to produce WirelessMic_Setup.exe

Usage:
    python build.py
    python build.py --skip-inno     (skip Inno Setup step)
    python build.py --clean         (clean dist/ and build/ first)
"""

import os
import sys
import shutil
import subprocess
import argparse
import struct
import zlib
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.resolve()
SRC         = ROOT / "src"
ASSETS      = ROOT / "assets"
INSTALLER   = ROOT / "installer"
VB_CABLE    = ROOT / "vb_cable"
DIST        = ROOT / "dist"
BUILD       = ROOT / "build"
DIST_INST   = ROOT / "dist_installer"

INNO_PATHS = [
    r"D:\vs\wo mic app\inno\ISCC.exe",           # custom install location
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def run(cmd, **kw):
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        print(f"[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result


def banner(text):
    line = "═" * (len(text) + 4)
    print(f"\n╔{line}╗")
    print(f"║  {text}  ║")
    print(f"╚{line}╝")


def find_inno() -> Path | None:
    for p in INNO_PATHS:
        if Path(p).exists():
            return Path(p)
    # Try PATH
    found = shutil.which("ISCC")
    return Path(found) if found else None


def make_ico(png_path: Path, ico_path: Path):
    """Convert PNG to multi-size .ico using Pillow."""
    try:
        from PIL import Image
        img = Image.open(png_path).convert("RGBA")
        sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
        imgs = [img.resize(s, Image.LANCZOS) for s in sizes]
        imgs[0].save(ico_path, format="ICO", sizes=sizes,
                     append_images=imgs[1:])
        print(f"  ✓ Created {ico_path}")
    except ImportError:
        print("  ! Pillow not installed — skipping .ico generation.")
        print("    Place icon.ico manually in assets/ before building.")


def create_license():
    license_path = ROOT / "LICENSE.txt"
    if not license_path.exists():
        license_path.write_text(
            "MIT License\n\nCopyright (c) 2025 WirelessMic\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
            "of this software and associated documentation files (the \"Software\"), to deal\n"
            "in the Software without restriction, including without limitation the rights\n"
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
            "copies of the Software, and to permit persons to whom the Software is\n"
            "furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all\n"
            "copies or substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
            "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
            "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.\n",
            encoding="utf-8"
        )
        print(f"  ✓ Created {license_path}")


def create_vbcable_placeholder():
    """Create placeholder README if VB-Cable installers are not present."""
    VB_CABLE.mkdir(exist_ok=True)
    readme = VB_CABLE / "README.txt"
    if not (VB_CABLE / "VBCABLE_Setup_x64.exe").exists():
        readme.write_text(
            "VB-Audio Virtual Cable Installer\n"
            "================================\n\n"
            "Download from: https://vb-audio.com/Cable/\n\n"
            "Place the following files in this folder:\n"
            "  VBCABLE_Setup_x64.exe   (64-bit Windows)\n"
            "  VBCABLE_Setup.exe       (32-bit Windows, optional)\n\n"
            "Then re-run build.py to include them in the installer.\n",
            encoding="utf-8"
        )
        print("  ⚠  VB-Cable installer not found.")
        print(f"     Download from https://vb-audio.com/Cable/")
        print(f"     and place in: {VB_CABLE}")


# ── Build Steps ────────────────────────────────────────────────────────────────

def step_clean():
    banner("Cleaning build artifacts")
    for d in (DIST, BUILD, DIST_INST):
        if d.exists():
            shutil.rmtree(d)
            print(f"  ✓ Removed {d}")


def step_deps():
    banner("Installing Python dependencies")
    req = SRC / "requirements.txt"
    run([sys.executable, "-m", "pip", "install", "-r", str(req), "--upgrade"])


def step_assets():
    banner("Preparing assets")
    ASSETS.mkdir(exist_ok=True)

    png_src = ASSETS / "icon.png"
    ico_dst = ASSETS / "icon.ico"

    # Try to find an icon PNG generated earlier
    if not png_src.exists():
        # Search for any PNG in assets
        pngs = list(ASSETS.glob("*.png"))
        if pngs:
            shutil.copy(pngs[0], png_src)
            print(f"  ✓ Using {pngs[0].name} as icon source")
        else:
            print("  ⚠  No icon PNG found in assets/. Generating a basic fallback.")
            _generate_fallback_png(png_src)

    if not ico_dst.exists():
        make_ico(png_src, ico_dst)


def _generate_fallback_png(path: Path):
    """Generate a minimal PNG without Pillow (pure Python)."""
    try:
        from PIL import Image, ImageDraw
        size = 256
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([0, 0, size-1, size-1], fill=(45, 55, 110, 255))
        draw.rounded_rectangle([80, 30, 176, 140], radius=30, fill="white")
        draw.line([128, 140, 128, 190], fill="white", width=8)
        draw.line([88, 190, 168, 190], fill="white", width=8)
        img.save(path, "PNG")
        print(f"  ✓ Generated fallback icon: {path}")
    except ImportError:
        print("  ⚠  Pillow not available — icon will be missing from build.")


def step_pyinstaller():
    banner("Building with PyInstaller")
    spec = ROOT / "wireless_mic.spec"
    if not spec.exists():
        print(f"[ERROR] Spec file not found: {spec}")
        sys.exit(1)
    run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--clean", "--noconfirm"],
        cwd=ROOT,
    )
    exe = DIST / "WirelessMic" / "WirelessMic.exe"
    if exe.exists():
        print(f"\n  ✓ Built: {exe}")
    else:
        print("[ERROR] WirelessMic.exe not found in dist/")
        sys.exit(1)


def step_copy_vbcable():
    banner("VB-Cable setup")
    create_vbcable_placeholder()


def step_inno(skip: bool):
    banner("Building installer with Inno Setup")
    if skip:
        print("  [SKIPPED] --skip-inno flag set.")
        return

    iscc = find_inno()
    if not iscc:
        print("  ⚠  Inno Setup not found. Skipping installer build.")
        print("     Download from https://jrsoftware.org/isinfo.php")
        return

    create_license()
    iss = INSTALLER / "wireless_mic_installer.iss"

    # Copy firewall script next to .iss for Inno
    fw_src = INSTALLER / "firewall_setup.ps1"
    fw_dst = INSTALLER / "firewall_setup.ps1"
    if fw_src.exists() and fw_src != fw_dst:
        shutil.copy(fw_src, fw_dst)

    DIST_INST.mkdir(exist_ok=True)
    run([str(iscc), str(iss)], cwd=ROOT)

    output = DIST_INST / "WirelessMic_Setup.exe"
    if output.exists():
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"\n  ✓ Installer created: {output}  ({size_mb:.1f} MB)")
    else:
        print("[WARNING] Installer file not found at expected path.")


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build Wireless Mic Windows Installer")
    parser.add_argument("--skip-inno",  action="store_true", help="Skip Inno Setup step")
    parser.add_argument("--clean",      action="store_true", help="Clean build artifacts first")
    parser.add_argument("--deps-only",  action="store_true", help="Only install dependencies")
    args = parser.parse_args()

    banner("Wireless Mic — Build System v1.0.0")
    print(f"  Root: {ROOT}")
    print(f"  Python: {sys.version.split()[0]}")

    if args.clean:
        step_clean()

    step_deps()

    if args.deps_only:
        print("\nDependencies installed. Done.")
        return

    step_assets()
    step_pyinstaller()
    step_copy_vbcable()
    step_inno(skip=args.skip_inno)

    banner("Build Complete!")
    print(f"""
  Outputs:
    App:       dist\\WirelessMic\\WirelessMic.exe
    Installer: dist_installer\\WirelessMic_Setup.exe

  To run the app directly:
    python src\\main.py

  To rebuild:
    python build.py --clean
""")


if __name__ == "__main__":
    main()
