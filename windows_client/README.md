# Wireless Mic — Windows Client

> Use your Android phone as a wireless microphone on your Windows PC.  
> Audio streams over Wi-Fi via UDP — zero compression, ultra-low latency.

---

## Project Structure

```
windows_client/
├── src/
│   ├── main.py            ← GUI application (entry point)
│   ├── audio_server.py    ← UDP listener + PyAudio playback backend
│   ├── ip_detector.py     ← Auto IP detection & network change monitoring
│   ├── system_tray.py     ← System tray icon & toast notifications
│   └── requirements.txt   ← Python dependencies
├── installer/
│   ├── wireless_mic_installer.iss  ← Inno Setup 6 script
│   └── firewall_setup.ps1          ← Firewall rule management
├── assets/
│   ├── icon.png           ← App icon (PNG source)
│   └── icon.ico           ← App icon (Windows ICO, auto-generated)
├── vb_cable/
│   ├── VBCABLE_Setup_x64.exe   ← VB-Audio installer (place here manually)
│   └── README.txt
├── build.py               ← Full build automation script
├── make_icon.py           ← One-time icon conversion helper
├── wireless_mic.spec      ← PyInstaller spec file
├── version_info.txt       ← Windows EXE version resource
└── LICENSE.txt
```

---

## System Requirements

| Requirement | Minimum |
|-------------|---------|
| Windows     | 10 version 1809 (build 17763) or Windows 11 |
| Python      | 3.10 or newer (for building only) |
| Architecture | 64-bit (x64) |
| RAM          | 256 MB free |
| Network      | Wi-Fi or Ethernet on the same LAN as the Android device |

---

## Quick Start — Running from Source

### 1. Install Python dependencies

```powershell
cd windows_client
pip install -r src\requirements.txt
```

> **PyAudio on Windows** — If `pip install pyaudio` fails, use:
> ```powershell
> pip install pipwin
> pipwin install pyaudio
> ```

### 2. Run the GUI

```powershell
python src\main.py
```

The app will:
- Auto-detect your LAN IP address
- Start listening on UDP port **55555**
- Open a system tray icon

### 3. Connect the Android app

In the Wireless Mic Android app, enter the IP address shown in the Windows client and tap **Start Streaming**.

---

## Building the Windows Installer

### Prerequisites

| Tool | Download |
|------|----------|
| Python 3.10+ | https://python.org |
| Inno Setup 6 | https://jrsoftware.org/isinfo.php |
| VB-Cable (optional) | https://vb-audio.com/Cable/ |

### Step 1 — Prepare the icon

```powershell
pip install Pillow
python make_icon.py
```

This copies the icon PNG and generates `assets\icon.ico` at all required sizes.

### Step 2 — (Optional) Add VB-Cable installer

Download `VBCABLE_Driver_Pack43.zip` from https://vb-audio.com/Cable/  
Extract `VBCABLE_Setup_x64.exe` and place it in the `vb_cable\` folder.

### Step 3 — Build everything

```powershell
python build.py
```

This will:
1. Install all Python dependencies
2. Convert icon to `.ico` format
3. Run **PyInstaller** → `dist\WirelessMic\WirelessMic.exe`
4. Run **Inno Setup** → `dist_installer\WirelessMic_Setup.exe`

### Options

```powershell
python build.py --clean       # Clean dist/ and build/ before building
python build.py --skip-inno   # Build the .exe but not the installer
python build.py --deps-only   # Only install Python dependencies
```

### Output

```
dist_installer\
└── WirelessMic_Setup.exe    ← Single self-contained installer (~25 MB)
```

---

## Installer Features

The `WirelessMic_Setup.exe` installer:

- ✅ Lets the user choose the installation directory
- ✅ Installs **VB-Audio Virtual Cable** silently (if not already present)
- ✅ Creates a **Desktop shortcut** and **Start Menu** entry
- ✅ Adds a **Windows Firewall** inbound rule for UDP port 55555
- ✅ Optional: **Launch on Windows startup**
- ✅ Clean **uninstaller** (removes files, shortcuts, and firewall rules)
- ✅ Smart: detects if VB-Cable is already installed and skips it

---

## GUI Features

| Feature | Description |
|---------|-------------|
| IP Display | Shows your PC's LAN IP in large bold text, auto-updates on network changes |
| Copy IP | One-click copy to clipboard |
| Connection LED | 🟢 green when Android is streaming, 🔴 red when idle |
| Audio Level Meter | Real-time RMS bar with green/amber/red zones and peak hold |
| Start/Stop | Toggle the UDP server without restarting the app |
| Route to VB-Cable | Checkbox to send audio to VB-Audio Cable Input |
| Always on Top | Keep window above other apps |
| Minimise to Tray | Close button minimises instead of quitting |
| System Tray Menu | Right-click: Show/Hide, Start/Stop, Exit |
| Toast Notifications | Connect/disconnect system notifications |
| Event Log | Scrollable log showing all events in the GUI |
| Log File | Persistent log at `%USERPROFILE%\wireless_mic.log` |

---

## Audio Configuration

| Setting | Value |
|---------|-------|
| Sample Rate | 48,000 Hz |
| Bit Depth | 16-bit signed PCM |
| Channels | Mono |
| Packet Size | ~4,800 bytes (100 ms per packet) |
| Protocol | UDP over LAN |
| Port | 55555 |

---

## VB-Audio Virtual Cable

VB-Cable creates a virtual audio device (`CABLE Input`) that appears as a microphone  
to other apps (Discord, OBS, Zoom, Teams, etc.).

When **"Route to VB-Cable"** is checked in the app:
- Audio from your Android phone → VB-Cable Input
- Other apps see VB-Cable Output as a microphone
- Use **Windows Sound settings** to set VB-Cable Output as your input device

If VB-Cable is not installed, audio plays through your default speakers/headphones.

---

## Firewall

The installer automatically adds a firewall rule. To manage it manually:

```powershell
# Add rule (run as Administrator)
powershell -ExecutionPolicy Bypass -File installer\firewall_setup.ps1 -Action Add

# Remove rule
powershell -ExecutionPolicy Bypass -File installer\firewall_setup.ps1 -Action Remove
```

---

## Troubleshooting

### "No audio output device found"
- Check that audio drivers are installed
- Try setting a different default playback device in Windows Sound settings

### "Cannot bind to port 55555"
- Another app is using the port. Stop it or change the port in `audio_server.py`
- Check Windows Firewall isn't blocking the app

### Android app can't connect
1. Make sure both devices are on the **same Wi-Fi network**
2. Double-check the IP address shown in the app
3. Disable VPN on either device
4. Verify the firewall rule is active

### VB-Cable not showing up
- Restart Windows after installing VB-Cable
- Open Device Manager → Sound, video and game controllers
- Look for "VB-Audio Virtual Cable"

### App crashes on start
- Check `%USERPROFILE%\wireless_mic.log` for error details
- Make sure PyAudio is correctly installed: `python -c "import pyaudio; print('OK')"`

### Build fails (PyInstaller)
- Run `python build.py --clean` to start fresh
- Make sure you're using Python 3.10+ (64-bit)
- Install all deps: `pip install -r src\requirements.txt`

---

## Architecture

```
Android App (UDP sender)
        │
        │  Raw PCM audio packets (UDP port 55555)
        ▼
  ┌─────────────┐
  │ UDP Listener │  (Thread 1: udp_listener)
  │  Port 55555  │
  └──────┬──────┘
         │  bytes → queue (max 50 packets)
         ▼
  ┌─────────────┐
  │ Audio Player │  (Thread 2: audio_player)
  │ PyAudio out  │
  └──────┬──────┘
         │
    ┌────┴────────────┐
    │                 │
  Speakers      VB-Cable Input
                (→ Discord/OBS/Zoom)

  ┌───────────────┐
  │   Watchdog    │  (Thread 3: detects timeout, fires disconnect)
  └───────────────┘

  ┌───────────────┐
  │  IP Monitor   │  (Thread 4: polls for network changes every 5s)
  └───────────────┘

  ┌───────────────┐
  │  System Tray  │  (Thread 5: pystray event loop)
  └───────────────┘
```

---

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0   | Initial release — GUI app, UDP backend, VB-Cable support, Inno Setup installer |
