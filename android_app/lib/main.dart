import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'dart:isolate';
import 'package:crypto/crypto.dart';
import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

void main() {
  runApp(const WirelessMicApp());
}

// Foreground Task Handler
@pragma('vm:entry-point')
void startCallback() {
  FlutterForegroundTask.setTaskHandler(MyTaskHandler());
}

class MyTaskHandler extends TaskHandler {
  @override
  Future<void> onStart(DateTime timestamp, SendPort? sendPort) async {}
  @override
  Future<void> onEvent(DateTime timestamp, SendPort? sendPort) async {}
  @override
  Future<void> onDestroy(DateTime timestamp, SendPort? sendPort) async {}
  @override
  void onRepeatEvent(DateTime timestamp, SendPort? sendPort) {}
  @override
  void onButtonPressed(String id) {}
  @override
  void onNotificationPressed() {
    FlutterForegroundTask.launchApp();
  }
}

class WirelessMicApp extends StatelessWidget {
  const WirelessMicApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Wireless Mic',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: const MicPage(),
    );
  }
}

class MicPage extends StatefulWidget {
  const MicPage({super.key});

  @override
  State<MicPage> createState() => _MicPageState();
}

class _MicPageState extends State<MicPage> with WidgetsBindingObserver {
  // ── Channels ────────────────────────────────────────────────────────────
  static const _audioStream = EventChannel('com.wirelessmic/audio_stream');
  static const _audioControl = MethodChannel('com.wirelessmic/audio_control');
  static const _launchAction = MethodChannel('com.wirelessmic/launch_action');

  // ── State ───────────────────────────────────────────────────────────────
  final TextEditingController _ipController = TextEditingController();
  final TextEditingController _pinController = TextEditingController();
  bool _isStreaming = false;
  bool _isStarting = false; // Debounce guard
  bool _muted = false;
  bool _autoReconnect = true;
  bool _btMic = false;
  double _gain = 1.0;
  String _status = 'Idle';
  int _packetsSent = 0;
  int _bytesSent = 0;
  int _seq = 0;
  int _sendFailures = 0;
  StreamSubscription? _audioSubscription;
  RawDatagramSocket? _udpSocket;
  SharedPreferences? _prefs;
  Timer? _heartbeatTimer;
  InternetAddress? _targetAddress;

  // ── Constants ───────────────────────────────────────────────────────────
  static const int _udpPort = 55555;
  static const int _maxSendFailures = 5;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initPrefs();
    _initForegroundTask();
    _checkLaunchAction();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _checkLaunchAction();
    }
  }

  Future<void> _checkLaunchAction() async {
    try {
      final action = await _launchAction.invokeMethod('popAction');
      if (action == 'start') {
        await _initPrefs(); // make sure fields are loaded
        await Future.delayed(const Duration(milliseconds: 300));
        if (!_isStreaming && !_isStarting) _startStreaming();
      } else if (action == 'stop') {
        if (_isStreaming) _stopStreaming();
      }
    } catch (_) {}
  }

  Future<void> _initPrefs() async {
    _prefs = await SharedPreferences.getInstance();
    final savedIp = _prefs?.getString('last_ip') ?? '';
    final savedPin = _prefs?.getString('last_pin') ?? '';
    _autoReconnect = _prefs?.getBool('auto_reconnect') ?? true;
    _btMic = _prefs?.getBool('bt_mic') ?? false;
    _gain = _prefs?.getDouble('gain') ?? 1.0;
    if (!mounted) return;
    setState(() {
      _ipController.text = savedIp;
      _pinController.text = savedPin;
    });
  }

  void _initForegroundTask() {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'wireless_mic_channel',
        channelName: 'Wireless Mic Service',
        channelDescription: 'Keeps the microphone streaming active in background',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        iconData: const NotificationIconData(
          resType: ResourceType.mipmap,
          resPrefix: ResourcePrefix.ic,
          name: 'launcher',
        ),
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: true,
        playSound: false,
      ),
      foregroundTaskOptions: const ForegroundTaskOptions(
        interval: 5000,
        isOnceEvent: false,
        autoRunOnBoot: false,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _stopStreaming();
    _ipController.dispose();
    _pinController.dispose();
    _heartbeatTimer?.cancel();
    super.dispose();
  }

  // ── Permission Handling ─────────────────────────────────────────────────
  Future<bool> _requestPermissions() async {
    var micStatus = await Permission.microphone.status;
    if (!micStatus.isGranted) {
      micStatus = await Permission.microphone.request();
    }

    if (Platform.isAndroid) {
      if (await Permission.notification.isDenied) {
        await Permission.notification.request();
      }
    }

    // Bluetooth mic needs connect permission on Android 12+
    if (_btMic && Platform.isAndroid) {
      if (await Permission.bluetoothConnect.isDenied) {
        await Permission.bluetoothConnect.request();
      }
    }

    if (micStatus.isPermanentlyDenied) {
      _setStatus('Mic permission denied. Open app settings.');
      openAppSettings();
      return false;
    }

    return micStatus.isGranted;
  }

  // ── QR Scanning ─────────────────────────────────────────────────────────
  Future<void> _scanQr() async {
    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const QrScanPage()),
    );
    if (result == null) return;
    try {
      final data = jsonDecode(result);
      if (data is Map && data['app'] == 'wirelessmic') {
        setState(() {
          _ipController.text = data['ip'] ?? '';
          _pinController.text = (data['pin'] ?? '').toString();
        });
        _setStatus('Paired via QR → ${_ipController.text}');
        _prefs?.setString('last_ip', _ipController.text);
        _prefs?.setString('last_pin', _pinController.text);
      } else {
        _setStatus('QR is not a Wireless Mic code.');
      }
    } catch (_) {
      _setStatus('Could not read that QR code.');
    }
  }

  // ── Audio processing (phone-side gain) ──────────────────────────────────
  Uint8List _applyGain(Uint8List pcm, double gain) {
    if (gain == 1.0) return pcm;
    final n = pcm.length ~/ 2;
    final samples = Int16List.view(pcm.buffer, pcm.offsetInBytes, n);
    final out = Uint8List(pcm.length);
    final outSamples = Int16List.view(out.buffer);
    for (int i = 0; i < n; i++) {
      int v = (samples[i] * gain).round();
      if (v > 32767) v = 32767;
      if (v < -32768) v = -32768;
      outSamples[i] = v;
    }
    return out;
  }

  // ── Start Streaming ────────────────────────────────────────────────────
  Future<void> _startStreaming() async {
    // Debounce guard — prevent double-tap
    if (_isStarting || _isStreaming) return;
    setState(() => _isStarting = true);

    try {
      await _doStartStreaming();
    } finally {
      if (mounted) setState(() => _isStarting = false);
    }
  }

  Future<void> _doStartStreaming() async {
    final ip = _ipController.text.trim();
    final pin = _pinController.text.trim();
    if (ip.isEmpty) {
      _setStatus('Enter the Windows PC IP address.');
      return;
    }
    if (pin.length != 4) {
      _setStatus('Enter exactly 4 digits for the Security PIN.');
      return;
    }

    try {
      _targetAddress = InternetAddress(ip);
    } catch (_) {
      _setStatus('Invalid IP address: $ip');
      return;
    }

    final hasPermission = await _requestPermissions();
    if (!hasPermission) return;

    _prefs?.setString('last_ip', ip);
    _prefs?.setString('last_pin', pin);
    _prefs?.setBool('auto_reconnect', _autoReconnect);
    _prefs?.setBool('bt_mic', _btMic);
    _prefs?.setDouble('gain', _gain);
    _setStatus('Starting secure stream...');

    try {
      await _audioControl.invokeMethod('setInputSource', {'bluetooth': _btMic});
    } catch (_) {}

    if (!await _createSocket()) {
      _setStatus('Failed to create UDP socket.');
      return;
    }

    final aesKey = encrypt.Key(
      Uint8List.fromList(sha256.convert(utf8.encode(pin)).bytes),
    );
    final encrypter = encrypt.Encrypter(encrypt.AES(aesKey, mode: encrypt.AESMode.cbc));
    final random = Random.secure();
    _seq = 0;
    _sendFailures = 0;
    final t0 = DateTime.now();

    if (await FlutterForegroundTask.isRunningService == false) {
      await FlutterForegroundTask.startService(
        notificationTitle: 'Wireless Mic Secure',
        notificationText: 'Encrypted stream to $ip',
        callback: startCallback,
      );
    }

    // Keep screen awake while streaming
    WakelockPlus.enable();

    _audioSubscription = _audioStream.receiveBroadcastStream().listen(
      (dynamic data) {
        if (data is Uint8List && _udpSocket != null) {
          try {
            if (_muted) return;

            // Phone-side gain
            final pcm = _applyGain(data, _gain);

            // Generate IV
            final ivBytes = Uint8List(16);
            for (int i = 0; i < 16; i++) {
              ivBytes[i] = random.nextInt(256);
            }
            final iv = encrypt.IV(ivBytes);

            // Encrypt and build packet: WM header + IV + ciphertext
            final encrypted = encrypter.encryptBytes(pcm, iv: iv);
            final seqBd = ByteData(4)..setUint32(0, _seq & 0xFFFFFFFF, Endian.little);
            final tsBd = ByteData(4)
              ..setUint32(0,
                  DateTime.now().difference(t0).inMilliseconds & 0xFFFFFFFF,
                  Endian.little);
            final payload = BytesBuilder();
            payload.add(utf8.encode('WM'));
            payload.addByte(2); // protocol version
            payload.add(seqBd.buffer.asUint8List());
            payload.add(tsBd.buffer.asUint8List());
            payload.add(iv.bytes);
            payload.add(encrypted.bytes);
            final packet = payload.toBytes();
            _seq++;

            final sent = _udpSocket!.send(packet, _targetAddress!, _udpPort);
            if (sent > 0) {
              _sendFailures = 0;
              _packetsSent++;
              _bytesSent += sent;
              if (_packetsSent % 50 == 0 && mounted) {
                _setStatus('Secure Stream to $ip | ${(_bytesSent / 1024 / 1024).toStringAsFixed(1)} MB');
              }
            }
          } catch (e) {
            _handleSendError(e);
          }
        }
      },
      onError: (e) {
        _setStatus('Stream error: $e');
        _stopStreaming();
      },
    );

    // Start heartbeat — send periodic ping to Windows so it knows we're alive
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 2), (_) {
      if (_udpSocket != null && _isStreaming) {
        try {
          _udpSocket!.send(utf8.encode('HEARTBEAT'), _targetAddress!, _udpPort);
        } catch (_) {}
      }
    });

    setState(() {
      _isStreaming = true;
    });
  }

  Future<bool> _createSocket() async {
    try {
      _udpSocket?.close();
    } catch (_) {}
    try {
      _udpSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      _udpSocket!.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          final datagram = _udpSocket!.receive();
          if (datagram != null) {
            try {
              final msg = utf8.decode(datagram.data);
              if (msg == 'ERROR:WRONG_PIN') {
                _setStatus('Error: Incorrect PIN entered!');
                _stopStreaming();
              } else if (msg == 'CMD:STOP') {
                _setStatus('Windows server disconnected.');
                _stopStreaming();
              }
            } catch (_) {}
          }
        }
      });
      return true;
    } catch (e) {
      _setStatus('Failed to create UDP socket: $e');
      return false;
    }
  }

  Future<void> _handleSendError(Object e) async {
    if (!_autoReconnect) {
      _setStatus('UDP error: $e');
      _stopStreaming();
      return;
    }
    _sendFailures++;
    if (_sendFailures > _maxSendFailures) {
      _setStatus('Connection lost after $_maxSendFailures retries.');
      _stopStreaming();
      return;
    }
    _setStatus('Reconnecting... (attempt $_sendFailures/$_maxSendFailures)');
    await Future.delayed(const Duration(milliseconds: 500));
    await _createSocket();
  }

  // ── Stop Streaming ─────────────────────────────────────────────────────
  Future<void> _stopStreaming() async {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;

    await _audioSubscription?.cancel();
    _audioSubscription = null;

    try {
      await _audioControl.invokeMethod('stop');
    } catch (_) {}

    _udpSocket?.close();
    _udpSocket = null;

    // Release wake lock
    WakelockPlus.disable();

    if (await FlutterForegroundTask.isRunningService) {
      await FlutterForegroundTask.stopService();
    }

    if (mounted) {
      setState(() {
        _isStreaming = false;
      });
      _setStatus('Stopped. Sent $_packetsSent pkts (${(_bytesSent / 1024 / 1024).toStringAsFixed(2)} MB)');
    }
  }

  void _setStatus(String msg) {
    if (mounted) {
      setState(() => _status = msg);
    }
  }

  @override
  Widget build(BuildContext context) {
    return WithForegroundTask(
      child: Scaffold(
        backgroundColor: const Color(0xFF1E1E24),
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: const Text('Wireless Mic', style: TextStyle(color: Colors.white, fontSize: 24)),
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // IP Input + QR scan
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _ipController,
                      enabled: !_isStreaming,
                      keyboardType: TextInputType.number,
                      style: const TextStyle(color: Colors.white, fontSize: 18),
                      decoration: InputDecoration(
                        labelText: 'Windows PC IP Address',
                        labelStyle: const TextStyle(color: Colors.white70),
                        prefixIcon: const Icon(Icons.laptop, color: Colors.white70),
                        suffixIcon: IconButton(
                          icon: const Icon(Icons.qr_code_scanner, color: Colors.white70),
                          onPressed: _isStreaming ? null : _scanQr,
                          tooltip: 'Scan QR on PC',
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderSide: const BorderSide(color: Colors.white30),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderSide: const BorderSide(color: Colors.white, width: 2),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        disabledBorder: OutlineInputBorder(
                          borderSide: const BorderSide(color: Colors.white12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 16),

              // PIN Input
              TextField(
                controller: _pinController,
                enabled: !_isStreaming,
                keyboardType: TextInputType.number,
                maxLength: 4,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(4),
                ],
                obscureText: false,
                style: const TextStyle(color: Colors.white, fontSize: 18, letterSpacing: 8),
                textAlign: TextAlign.center,
                decoration: InputDecoration(
                  labelText: 'Security PIN (From PC)',
                  labelStyle: const TextStyle(color: Colors.white70),
                  prefixIcon: const Icon(Icons.lock, color: Colors.white70),
                  hintText: '0000',
                  hintStyle: const TextStyle(color: Colors.white24, letterSpacing: 8),
                  counterText: '',
                  enabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white30),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white, width: 2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  disabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),

              const SizedBox(height: 12),

              // Mic source + auto-reconnect row
              Row(
                children: [
                  const Icon(Icons.settings_input_component, color: Colors.white54, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButton<bool>(
                      value: _btMic,
                      isExpanded: true,
                      dropdownColor: const Color(0xFF2A2A32),
                      items: const [
                        DropdownMenuItem(value: false, child: Text('Phone Microphone', style: TextStyle(color: Colors.white))),
                        DropdownMenuItem(value: true, child: Text('Bluetooth Headset Mic', style: TextStyle(color: Colors.white))),
                      ],
                      onChanged: _isStreaming
                          ? null
                          : (v) => setState(() => _btMic = v ?? false),
                    ),
                  ),
                ],
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                activeColor: Colors.green,
                title: const Text('Auto-reconnect on drop', style: TextStyle(color: Colors.white70, fontSize: 14)),
                value: _autoReconnect,
                onChanged: _isStreaming
                    ? null
                    : (v) => setState(() => _autoReconnect = v),
              ),

              // Gain slider
              Row(
                children: [
                  const Icon(Icons.volume_up, color: Colors.white54, size: 18),
                  Expanded(
                    child: Slider(
                      value: _gain,
                      min: 0.5,
                      max: 3.0,
                      divisions: 25,
                      activeColor: Colors.blueAccent,
                      label: '${_gain.toStringAsFixed(2)}×',
                      onChanged: (v) => setState(() => _gain = v),
                    ),
                  ),
                  SizedBox(
                    width: 52,
                    child: Text('${_gain.toStringAsFixed(2)}×',
                        style: const TextStyle(color: Colors.white70)),
                  ),
                ],
              ),

              const SizedBox(height: 8),

              // Controls
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.mic, color: Colors.white),
                      label: const Text('Start', style: TextStyle(color: Colors.white, fontSize: 16)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4CAF50),
                        disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        elevation: 0,
                      ),
                      onPressed: (_isStreaming || _isStarting) ? null : _startStreaming,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: Icon(_muted ? Icons.mic_off : Icons.mic, color: Colors.white),
                      label: Text(_muted ? 'Muted' : 'Mute',
                          style: const TextStyle(color: Colors.white, fontSize: 16)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _muted ? const Color(0xFFE67E22) : const Color(0xFF5B6EF5),
                        disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        elevation: 0,
                      ),
                      onPressed: _isStreaming
                          ? () => setState(() => _muted = !_muted)
                          : null,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.stop, color: Colors.white54),
                      label: const Text('Stop', style: TextStyle(color: Colors.white54, fontSize: 16)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.grey.withOpacity(0.5),
                        disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        elevation: 0,
                      ),
                      onPressed: _isStreaming ? _stopStreaming : null,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 24),

              // Status Box
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white30),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _isStreaming ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                          color: _isStreaming ? Colors.green : Colors.white54,
                          size: 16,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          _isStreaming ? 'STREAMING' : 'IDLE',
                          style: TextStyle(
                            color: _isStreaming ? Colors.green : Colors.white,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.1,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _status,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 40),

              // Instructions
              const Text(
                'Instructions:\n'
                '1. Start the Windows receiver\n'
                '2. Scan the QR (or enter IP + PIN manually)\n'
                '3. Tap Start to securely stream audio\n'
                '4. Audio: 48kHz, AES-256 Encrypted UDP',
                style: TextStyle(color: Colors.white54, fontSize: 14, height: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── QR Scanner Page ──────────────────────────────────────────────────────────
class QrScanPage extends StatefulWidget {
  const QrScanPage({super.key});

  @override
  State<QrScanPage> createState() => _QrScanPageState();
}

class _QrScanPageState extends State<QrScanPage> {
  bool _handled = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Scan PC QR Code'),
      ),
      body: MobileScanner(
        onDetect: (capture) {
          if (_handled) return;
          for (final barcode in capture.barcodes) {
            final code = barcode.rawValue;
            if (code != null && code.isNotEmpty) {
              _handled = true;
              Navigator.pop(context, code);
              break;
            }
          }
        },
      ),
    );
  }
}
