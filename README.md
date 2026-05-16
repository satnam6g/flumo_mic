# Wireless Microphone System

A low-latency wireless microphone system that streams audio from an Android device to a Windows PC over Wi-Fi using UDP.

## Architecture

```
Android (Mic) → AudioRecord (Kotlin) → EventChannel → Flutter (UDP Sender)
    ↓ Wi-Fi (UDP port 55555)
Windows (Speaker) → PyAudio → Default Playback Device (VB-Cable)
```

- **Audio Format**: 48000 Hz, 16-bit PCM, Mono, Uncompressed
- **Transport**: UDP over Wi-Fi, port 55555
- **Chunk Size**: ~4800 bytes per packet (~100ms of audio)

---

## Prerequisites

### Android
- Flutter SDK 3.10+ installed and on PATH
- Android SDK with API 30+
- Android device with Android 10+ (USB debugging enabled)
- Device connected to the same Wi-Fi network as the Windows PC

### Windows
- Python 3.10+
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) installed (optional, for routing audio to other apps)
- PyAudio (installed via requirements.txt)

---

## Setup & Run

### Step 1: Windows Client (Receiver)

```bash
cd windows_client
pip install -r requirements.txt
python main.py
```

The client will start listening on UDP port 55555 and print status info.
Use these console commands while running:
- `s` — Show status (packets received, queue depth, etc.)
- `q` — Quit gracefully

**VB-Cable Setup (optional):**
1. Install VB-Audio Virtual Cable from https://vb-audio.com/Cable/
2. Open Windows Sound Settings → Playback → Set "CABLE Input (VB-Audio)" as Default Playback Device
3. In your target app (Discord, OBS, etc.), set input to "CABLE Output (VB-Audio)"

### Step 2: Android App (Sender)

```bash
cd android_app
flutter pub get
flutter run --release
```

On the Android app:
1. Grant microphone permission when prompted
2. Enter the Windows PC's local IP address (e.g., `192.168.1.100`)
3. Tap **Start** to begin streaming
4. Tap **Stop** to stop streaming

### Finding Your Windows IP

Open PowerShell and run:
```powershell
ipconfig | findstr /i "IPv4"
```
Use the IPv4 address on your Wi-Fi adapter (e.g., `192.168.x.x`).

---

## Troubleshooting

| Issue | Solution |
|---|---|
| No audio on Windows | Check that the default playback device is set correctly in Sound Settings |
| Permission denied on Android | Uninstall and reinstall the app, then grant mic permission |
| High latency | Ensure both devices are on the same Wi-Fi network (5GHz preferred) |
| Choppy audio | Reduce distance to router, or check for Wi-Fi congestion |
| PyAudio install fails | On Windows: `pip install pipwin && pipwin install pyaudio` |
| Flutter build fails | Run `flutter doctor` and resolve any issues |

---

## Technical Details

- Buffer size on Android: `AudioRecord.getMinBufferSize() * 2`
- UDP packet size: 4800 bytes (2400 samples × 2 bytes/sample = 100ms at 48kHz)
- Windows queue depth: max 50 packets, drops oldest on overflow
- No compression — raw PCM for minimum latency
