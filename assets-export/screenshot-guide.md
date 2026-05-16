# Screenshot Guide for Wireless Mic Redesign

## Setup Requirements
- To ensure consistent screenshots, set your display scaling to 100%.
- Ensure you have the `Inter` or `Segoe UI` font installed.

## Windows Client Screenshots
1. **Launch the application:** `python main.py`
2. **Idle State:** Capture the main window before clicking "Start Server". Focus on the dark theme, the "Waiting for connection" status, and the green "START SERVER" button.
3. **Active State:**
   - Click "Start Server".
   - Capture the window while it displays the local IP and the LED indicator is pulsing.
   - Run the Android app and start streaming to see the Audio Meter move and the Event Log populate. Capture this active streaming state.
4. **System Tray:** Open the Windows taskbar overflow menu, capture the new blue microphone icon in the system tray.

## Android App Screenshots
1. **Launch the application:** `flutter run` on a physical device or emulator (Pixel 6/7 recommended).
2. **Permissions:** Capture the microphone and notification permission dialogs if possible.
3. **Idle State:** Capture the main screen showing the IP input field, gradient buttons, and the "How to Connect" expansion tile.
4. **Active State:**
   - Enter the IP and tap "Start".
   - Capture the screen when the green LED indicator is glowing and the button shows the shimmer pulse animation.
5. **Foreground Service Notification:** Pull down the Android notification shade and capture the "Wireless Mic Active" persistent notification.
