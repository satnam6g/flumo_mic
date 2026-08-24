# Debug Log — Audio not reaching OBS / Snapchat Web

> Goal: Phone streams → Windows client receives → VB-Cable carries it → OBS/browser apps capture it.
> Every change we make gets logged here so we can roll back.

## System state discovered (read-only checks, nothing changed yet)

| Check | Result | Status |
|---|---|---|
| VB-Cable installed | YES — `CABLE Input` (playback side) + `CABLE Output` (recording side) both visible to PyAudio | ✅ |
| Windows mic privacy (`ConsentStore\microphone`) | `Allow` (master + desktop apps) | ✅ |
| Firewall rules "Wireless Microphone Client" | Allow on **Private** profile, Block on Public | ✅ |
| Active network `Lotey'z 2` (Wi-Fi 2) | NetworkCategory = **Private**, PC IP = `192.168.18.109` | ✅ |
| UDP port 55555 at time of check | Nothing bound — client was NOT running | ℹ️ |

## How the audio chain works (for reference)
1. Phone encrypts chunks with key = SHA256(4-digit PIN), sends UDP → PC:55555
2. `audio_server.py` decrypts, computes level meter, queues audio
3. Player thread writes PCM into **CABLE Input** (VB-Cable playback end)
4. Any app that wants the mic must select **CABLE Output** (VB-Cable recording end)

## Suspects (to verify one by one)
1. Are packets actually arriving? (Android "MB sent" proves nothing — UDP send can succeed while firewall drops inbound)
2. Does GUI level meter move when phone talks?
3. In OBS/Snapchat: is the selected microphone exactly **CABLE Output (VB-Audio Virtual Cable)**? (NOT CABLE Input, NOT WO Mic Device, NOT DroidCam Audio — this PC has many virtual mics installed)
4. Browser-level mic permission for snapchat web.

## Test #1 — raw UDP listener on 55555 (40s window)
- Result: **0 packets received** ← chain breaks here, before VB-Cable/OBS are even involved
- Caveat: user may not have started the phone stream during the window → retest needed
- Note: Android app's "MB sent" counter proves only that the phone SENT packets, not that the PC got them (UDP has no delivery guarantee)

## Changes made
(none yet)

## ROOT CAUSES FOUND & FIXED (2026-08-24)

### Cause 1 — Phone was streaming to a dead IP (main bug)
- App had saved `192.168.18.7` (old address); PC is `192.168.18.109`
- UDP gives no delivery feedback, so the Android "MB sent" counter kept climbing → looked like it worked
- **Fixed**: typed correct IP into the app (now saved in prefs). Verified 426 packets arrived at PC.

### Cause 2 — PIN changes on every client launch
- `main.py:90` generates a random PIN each start; phone keeps the old one → decryption fails (`ERROR:WRONG_PIN`)
- **Fixed (for this session)**: set phone PIN to match the client's current PIN (6282)

### Cause 3 (transient during testing) — installed `D:\software\WirelessMic\WirelessMic.exe` was holding UDP 55555
- Any second instance (or test script) gets nothing
- Rule: **run only ONE client at a time**

## VERIFICATION RESULTS
| Test | Result |
|---|---|
| Raw UDP delivery phone→PC (correct IP) | ✅ 426 packets / 2 MB |
| Decryption with matching PIN | ✅ 301/301 packets, RMS 0.0056 |
| Audio inside VB-Cable (CABLE Output) | ✅ max RMS 0.0184, 200/200 frames active — **END-TO-END WORKING** |

## CURRENT STATE
- Phone: STREAMING to 192.168.18.109, PIN 6282
- Windows: installed WirelessMic.exe v1.0.0 running, server on 55555
- Nothing in the repo was modified — all fixes were configuration (IP + PIN on the phone)

## TO USE IN APPS
- OBS: Sources → + → Audio Input Capture → device = **CABLE Output (VB-Audio Virtual Cable)**
- Browser (Snapchat web): site mic permission → allow, then pick **CABLE Output (VB-Audio Virtual Cable)** as microphone
- Windows Settings → System → Sound → Input: **CABLE Output** (if an app just uses "default mic")

## KNOWN FOLLOW-UPS (optional improvements)
1. PIN regenerates every client launch → must retype on phone each time. Could make it persistent/configurable in main.py.
2. Phone IP must be retyped whenever PC's DHCP address changes. Could add mDNS/QR pairing.
3. Wi-Fi latency was 73–358 ms (congested) → may cause choppy audio; 5 GHz recommended.

## Rollback notes
- Killed PID 16152 (WirelessMic.exe) during testing — user relaunched it afterwards, currently running.
- Temp test scripts live in C:\Users\LENOVO\AppData\Local\Temp\opencode\ (udp_test.py, probe.py, e2e_test.py, cable_check.py) — safe to delete.

