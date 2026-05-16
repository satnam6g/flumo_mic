# wireless_mic.spec  –  PyInstaller specification
# Build with:  pyinstaller wireless_mic.spec

import sys, os

block_cipher = None

# Collect all hidden imports needed by PyAudio / pystray
hidden_imports = [
    "pyaudio",
    "pystray",
    "pystray._win32",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "plyer",
    "plyer.platforms.win.notification",
    "queue",
    "threading",
    "socket",
    "struct",
    "logging",
    "subprocess",
    "re",
    "webbrowser",
]

# Data files to bundle
datas = [
    (os.path.join("assets", "icon.ico"),  "assets"),
    (os.path.join("assets", "icon.png"),  "assets"),
]

a = Analysis(
    [os.path.join("src", "main.py")],
    pathex=[os.path.abspath("src")],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "tkinter.test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WirelessMic",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join("assets", "icon.ico"),
    version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WirelessMic",
)
