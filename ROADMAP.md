# Wireless Mic — Feature Roadmap

> Last updated: 2026-08-24
> Status: ✅ = shipped in v2.0 | 🔜 = approved, planned next | 💎 = premium candidate

---

## ✅ Current Features (v2.0)

### Streaming Core
- 48kHz/16-bit mono audio over UDP, AES-256-CBC encrypted (PIN-derived key, per-packet IV)
- 4-digit PIN pairing — persistent across launches, with regenerate button
- QR pairing — Windows client shows QR, phone scans → auto-fills IP + PIN
- Heartbeat + 3s watchdog, bidirectional STOP commands, wrong-PIN detection
- Auto-reconnect on network drops (phone recreates socket with retries)
- Multi-phone mixing — several phones stream into one PC simultaneously
- Packet header v2 (sequence + timestamp) → live packet-loss % and jitter stats

### Audio Engine (Windows)
- VB-Cable output only (never speakers), auto-installs VB-Cable driver if missing
- Gain slider (0.5×–3×), Noise Gate (adjustable threshold + 300ms hold), Mute
- Monitor — hear yourself through PC speakers/headphones
- WAV recording with auto-timestamped files → `Music\WirelessMic`
- Level meter with gradient + peak hold
- Live stats: packets, loss %, jitter ms, MB, uptime, connected devices

### Apps & UX (Windows)
- Works with OBS / Discord / Zoom / browsers via "CABLE Output" mic device
- Global hotkeys: Ctrl+Alt+M (mute), Ctrl+Alt+R (record), Ctrl+Alt+S (monitor)
- Auto-start with Windows (registry, per-user)
- System tray with notifications, minimise-to-tray on close
- IP change monitor, copy-IP button, event log + `wireless_mic.log`

### Android App
- Foreground service + CPU wake lock + Wi-Fi lock (streams with screen off)
- QR scanner page, saved IP/PIN
- Microphone source: Phone Mic / Bluetooth Headset (SCO routing)
- Phone-side gain slider + mute button
- Auto-reconnect toggle
- Home-screen widget (Start / Stop) + Quick Settings tile
- Live status box, packet + MB counters

---

## 🔜 Approved — Next Release (v2.1)

| # | Feature | Notes |
|---|---|---|
| 1 | **AI Noise Suppression** | Adaptive spectral suppression (numpy) now; upgrade to RNNoise neural model later |
| 2 | **Compression mode** | µ-law 2× bandwidth saver both ends; real Opus (native libs) as stretch goal |
| 3 | **Auto-Gain Control (AGC)** | Rolling RMS → constant loudness as you move around |
| 4 | **3-Band EQ + presets** | Flat / Voice Boost / Bass Boost / Warm / Bright (biquad filters) |
| 5 | **Voice Effects** | Robot, Deep, High, Reverb — fun/streaming use |
| 6 | **Internet mode / Relay** | Relay server (relay.py) so phone & PC work across networks/mobile data |
| 7 | **Auto-discovery** | PC answers UDP broadcast on port 55556 → phone "Find PC" button, zero typing |
| 9 | **Push-to-talk** | Hold Ctrl+Alt+P (or configurable) to temporarily unmute |
| 14 | **MP3 recording** | lameenc, auto-timestamped names, fallback to WAV |

## 💎 Premium Candidates (later)

- Neural RNNoise suppression (true AI denoise)
- Opus HD mode (native codec both ends)
- Internet relay hosted service (server costs → paid)
- Voice effects packs + custom preset save/load
- Multi-PC simultaneous streaming
- MP3/cloud recording (auto-upload to Drive/Dropbox)
- Custom branding + OBS overlay widget for streamers
- Light theme (palette already in DESIGN_SYSTEM.md)
- Update checker, connection profiles (home/office one-tap switch)

## 🧹 Housekeeping
- Rebuild installer after feature drops: `python build.py` (needs `PYTHONIOENCODING=utf-8`)
- Android release signing: local builds are debug-signed; Play/release builds need a keystore
